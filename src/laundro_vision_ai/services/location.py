import math
from abc import ABC, abstractmethod
from logging import Logger

import requests

from laundro_vision_ai.core.config import get_settings


class MapProvider(ABC):
    def __init__(self, logger: Logger):
        self._logger = logger

    @abstractmethod
    def geocode(self, address: str) -> tuple[float, float]:
        """Converts an address string into (latitude, longitude)."""
        pass

    @abstractmethod
    def enrich_location(self, lat: float, lng: float) -> dict:
        """Performs POI searches and returns the enrichment data dictionary."""
        pass


class MockMapProvider(MapProvider):
    def geocode(self, address: str) -> tuple[float, float]:
        return (25.033964, 121.564472)

    def enrich_location(self, lat: float, lng: float) -> dict:
        return {
            "has_competitor_in_1000m": True,
            "competitors_data": ["Mock Laundry 1"],
            "cvs_mcd_in_200m": ["7-11", "McDonald's"],
            "has_starbucks": False,
        }


class OSMMapProvider(MapProvider):
    def geocode(self, address: str) -> tuple[float, float]:
        headers = {"User-Agent": "LaundroVision/1.0"}
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "limit": 1}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise ValueError(f"Could not geocode address: {address}")
        return float(data[0]["lat"]), float(data[0]["lon"])

    def enrich_location(self, lat: float, lng: float) -> dict:
        query = f"""
        [out:json];
        (
          node(around:1000,{lat},{lng})["shop"="laundry"];
          node(around:200,{lat},{lng})["shop"="convenience"];
          node(around:200,{lat},{lng})["amenity"="fast_food"];
          node(around:200,{lat},{lng})["amenity"="cafe"];
        );
        out tags;
        """
        headers = {"User-Agent": "LaundroVision/1.0"}
        response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, headers=headers)
        response.raise_for_status()
        elements = response.json().get("elements", [])

        competitors = []
        cvs_mcd = []
        has_starbucks = False

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "Unknown")

            if tags.get("shop") == "laundry":
                competitors.append(name)
            elif tags.get("shop") == "convenience":
                cvs_mcd.append(name)
            elif tags.get("amenity") == "fast_food" and ("McDonald" in name or "麥當勞" in name):
                cvs_mcd.append(name)
            elif tags.get("amenity") == "cafe" and ("Starbucks" in name or "星巴克" in name):
                has_starbucks = True

        return {
            "has_competitor_in_1000m": len(competitors) > 0,
            "competitors_data": competitors,
            "cvs_mcd_in_200m": cvs_mcd,
            "has_starbucks": has_starbucks,
        }


def get_map_provider(logger: Logger) -> MapProvider:
    provider = get_settings().MAP_PROVIDER
    if provider == "MOCK":
        return MockMapProvider(logger)
    elif provider == "GOOGLE":
        return GoogleMapProvider(logger)
    return OSMMapProvider(logger)


class GoogleMapProvider(MapProvider):
    def geocode(self, address: str) -> tuple[float, float]:
        settings = get_settings()
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is not set")

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address, "key": api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        self._logger.info(f"Geocode response for '{address}': {data}")

        if data.get("status") != "OK" or not data.get("results"):
            raise ValueError(f"Could not geocode address: {address}")

        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]

    def enrich_location(self, lat: float, lng: float) -> dict:
        settings = get_settings()
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is not set")

        search_nearby_url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName.text",
            "Content-Type": "application/json",
        }

        # 1. Competitors (1000m)
        competitors = []
        payload_laundry = {
            "includedTypes": ["laundry"],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": 1000.0,
                }
            },
        }
        resp_laundry = requests.post(search_nearby_url, headers=headers, json=payload_laundry)
        self._logger.info(f"Competitor search response: {resp_laundry.json()}")
        if resp_laundry.status_code == 200:
            places = resp_laundry.json().get("places", [])
            competitors = [p.get("displayName", {}).get("text") for p in places if p.get("displayName")]

        # 2. CVS (200m)
        cvs_mcd = []
        payload_cvs = {
            "includedTypes": ["convenience_store"],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": 200.0,
                }
            },
        }
        resp_cvs = requests.post(search_nearby_url, headers=headers, json=payload_cvs)
        self._logger.info(f"CVS search response: {resp_cvs.json()}")
        if resp_cvs.status_code == 200:
            places = resp_cvs.json().get("places", [])
            cvs_mcd.extend([p.get("displayName", {}).get("text") for p in places if p.get("displayName")])

        # Calculate bounding box for 200m
        low_rect, high_rect = get_bounding_box(lat, lng, 200.0)

        # 3. McDonald's (200m)
        search_text_url = "https://places.googleapis.com/v1/places:searchText"
        payload_mcd = {
            "textQuery": "McDonald's OR 麥當勞",
            "maxResultCount": 20,
            "locationRestriction": {
                "rectangle": {
                    "low": low_rect,
                    "high": high_rect,
                }
            },
        }
        resp_mcd = requests.post(search_text_url, headers=headers, json=payload_mcd)
        self._logger.info(f"McDonald's search response: {resp_mcd.json()}")
        if resp_mcd.status_code == 200:
            places = resp_mcd.json().get("places", [])
            cvs_mcd.extend([p.get("displayName", {}).get("text") for p in places if p.get("displayName")])

        # 4. Starbucks (200m)
        has_starbucks = False
        payload_sb = {
            "textQuery": "Starbucks OR 星巴克",
            "maxResultCount": 20,
            "locationRestriction": {
                "rectangle": {
                    "low": low_rect,
                    "high": high_rect,
                }
            },
        }
        resp_starbucks = requests.post(search_text_url, headers=headers, json=payload_sb)
        if resp_starbucks.status_code == 200:
            self._logger.info(f"Starbucks search response: {resp_starbucks.json()}")
            places = resp_starbucks.json().get("places", [])
            has_starbucks = len(places) > 0

        return {
            "has_competitor_in_1000m": len(competitors) > 0,
            "competitors_data": competitors,
            "cvs_mcd_in_200m": cvs_mcd,
            "has_starbucks": has_starbucks,
        }


def get_bounding_box(lat: float, lng: float, radius_meters: float) -> tuple[dict, dict]:
    """Calculates a bounding box (low, high) coordinates for a given radius."""
    # Earth's radius in meters
    earth_radius = 6378137.0

    # Coordinate offsets in radians
    d_lat = radius_meters / earth_radius
    d_lng = radius_meters / (earth_radius * math.cos(math.radians(lat)))

    # Offset in degrees
    d_lat_deg = math.degrees(d_lat)
    d_lng_deg = math.degrees(d_lng)

    low = {"latitude": lat - d_lat_deg, "longitude": lng - d_lng_deg}
    high = {"latitude": lat + d_lat_deg, "longitude": lng + d_lng_deg}
    return low, high


def calculate_q1_score(has_starbucks: bool, cvs_mcd: list[str]) -> int:
    if has_starbucks or not cvs_mcd:
        return 1

    has_mcd = any("McDonald" in name or "麥當勞" in name for name in cvs_mcd)
    if has_mcd or len(cvs_mcd) >= 2:
        return 5

    if len(cvs_mcd) == 1:
        return 3

    return 1

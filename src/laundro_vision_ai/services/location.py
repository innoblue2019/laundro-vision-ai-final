from abc import ABC, abstractmethod

import requests

from laundro_vision_ai.core.config import get_settings


class MapProvider(ABC):
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


def get_map_provider() -> MapProvider:
    provider = get_settings().MAP_PROVIDER
    if provider == "MOCK":
        return MockMapProvider()
    elif provider == "GOOGLE":
        return GoogleMapProvider()
    return OSMMapProvider()


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

        if data.get("status") != "OK" or not data.get("results"):
            raise ValueError(f"Could not geocode address: {address}")

        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]

    def enrich_location(self, lat: float, lng: float) -> dict:
        return {}


def calculate_q1_score(has_starbucks: bool, cvs_mcd: list[str]) -> int:
    if has_starbucks or not cvs_mcd:
        return 1

    has_mcd = any("McDonald" in name or "麥當勞" in name for name in cvs_mcd)
    if has_mcd or len(cvs_mcd) >= 2:
        return 5

    if len(cvs_mcd) == 1:
        return 3

    return 1

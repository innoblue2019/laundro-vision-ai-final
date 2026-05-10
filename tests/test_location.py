import os
from unittest.mock import Mock, patch

import pytest
import requests
import responses
import respx
from httpx import Response

from laundro_vision_ai.core.config import Settings
from laundro_vision_ai.services.location import (
    GoogleMapProvider,
    MockMapProvider,
    OSMMapProvider,
    calculate_q1_score,
    get_bounding_box,
    get_map_provider,
)


def test_mock_provider_geocode():
    provider = MockMapProvider(Mock())
    lat, lng = provider.geocode("Taipei")
    assert isinstance(lat, float)
    assert isinstance(lng, float)


def test_mock_provider_enrich():
    provider = MockMapProvider(Mock())
    result = provider.enrich_location(25.0, 121.0)
    assert "has_competitor_in_1000m" in result
    assert result["has_starbucks"] is False


@respx.mock
def test_osm_provider_geocode():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=Response(200, json=[{"lat": "25.0338352", "lon": "121.5644995"}])
    )
    provider = OSMMapProvider(Mock())
    lat, lng = provider.geocode("Taipei 101")
    assert round(lat, 7) == 25.0338352
    assert round(lng, 7) == 121.5644995


@patch("requests.post")
def test_osm_provider_enrich(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "elements": [
            {"tags": {"shop": "laundry", "name": "Wash"}},
            {"tags": {"shop": "convenience", "name": "7-11"}},
            {"tags": {"amenity": "cafe", "name": "Starbucks"}},
        ]
    }
    mock_post.return_value.raise_for_status.return_value = None

    provider = OSMMapProvider(Mock())
    result = provider.enrich_location(25.0, 121.0)
    assert result["has_competitor_in_1000m"] is True
    assert result["competitors_data"] == ["Wash"]
    assert "7-11" in result["cvs_mcd_in_200m"]
    assert result["has_starbucks"] is True


def test_get_map_provider_mock():
    os.environ["MAP_PROVIDER"] = "MOCK"  # Explicitly set for this test
    provider = get_map_provider(Mock())
    assert isinstance(provider, MockMapProvider)


def test_get_map_provider_osm():
    os.environ["MAP_PROVIDER"] = "OSM"  # Explicitly set for this test
    provider = get_map_provider(Mock())
    assert isinstance(provider, OSMMapProvider)


def test_calculate_q1_score():
    assert calculate_q1_score(True, []) == 1
    assert calculate_q1_score(False, []) == 1
    assert calculate_q1_score(False, ["7-11"]) == 3
    assert calculate_q1_score(False, ["7-11", "FamilyMart"]) == 5
    assert calculate_q1_score(False, ["McDonald's"]) == 5


@respx.mock
def test_osm_provider_geocode_no_results():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=Response(200, json=[{"lat": "25.0338352", "lon": "121.5644995"}])
    )
    provider = OSMMapProvider(Mock())
    with pytest.raises(ValueError, match="Could not geocode address"):
        provider.geocode("NonExistent Address")


@patch("requests.get")
def test_osm_provider_geocode_network_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException
    provider = OSMMapProvider(Mock())
    with pytest.raises(requests.exceptions.RequestException):
        provider.geocode("Taipei 101")


@patch("requests.post")
def test_osm_provider_enrich_network_error(mock_post):
    mock_post.side_effect = requests.exceptions.RequestException
    provider = OSMMapProvider(Mock())
    with pytest.raises(requests.exceptions.RequestException):
        provider.enrich_location(25.0, 121.0)


def test_calculate_q1_score_with_starbucks_in_cvs_mcd():
    # Although enrich_location separates Starbucks, testing this branch ensures robustness
    # and covers a potential edge case if data source changes.
    assert calculate_q1_score(False, ["Starbucks Coffee"]) == 3
    assert calculate_q1_score(False, ["McDonald's", "Starbucks Coffee"]) == 5


@responses.activate
def test_google_map_provider_geocode(monkeypatch):
    # Mock settings
    monkeypatch.setattr(
        "laundro_vision_ai.services.location.get_settings", lambda: Settings(GOOGLE_MAPS_API_KEY="test_key")
    )

    provider = GoogleMapProvider(Mock())

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={"results": [{"geometry": {"location": {"lat": 25.033964, "lng": 121.564472}}}], "status": "OK"},
        status=200,
    )

    lat, lng = provider.geocode("Taipei 101")
    assert lat == 25.033964
    assert lng == 121.564472


@patch("requests.post")
def test_osm_provider_enrich_fast_food_not_mcdonalds(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "elements": [
            {"tags": {"amenity": "fast_food", "name": "Burger King"}},
        ]
    }
    mock_post.return_value.raise_for_status.return_value = None

    provider = OSMMapProvider(Mock())
    result = provider.enrich_location(25.0, 121.0)
    assert "Burger King" not in result["cvs_mcd_in_200m"]
    assert result["has_starbucks"] is False


@patch("requests.post")
def test_osm_provider_enrich_cafe_not_starbucks(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "elements": [
            {"tags": {"amenity": "cafe", "name": "Local Cafe"}},
        ]
    }
    mock_post.return_value.raise_for_status.return_value = None

    provider = OSMMapProvider(Mock())
    result = provider.enrich_location(25.0, 121.0)
    assert result["has_starbucks"] is False


@responses.activate
def test_google_map_provider_enrich_location(monkeypatch):
    monkeypatch.setattr(
        "laundro_vision_ai.services.location.get_settings", lambda: Settings(GOOGLE_MAPS_API_KEY="test_key")
    )
    provider = GoogleMapProvider(Mock())

    # Mock nearbysearch for laundry
    responses.add(
        responses.POST,
        "https://places.googleapis.com/v1/places:searchNearby",
        json={"places": [{"displayName": {"text": "Wash & Go"}}]},
        status=200,
        match=[
            responses.matchers.json_params_matcher(
                {
                    "includedTypes": ["laundry"],
                    "maxResultCount": 20,
                    "locationRestriction": {
                        "circle": {"center": {"latitude": 25.0, "longitude": 121.0}, "radius": 1000.0}
                    },
                }
            )
        ],
    )

    # Mock nearbysearch for convenience_store
    responses.add(
        responses.POST,
        "https://places.googleapis.com/v1/places:searchNearby",
        json={"places": [{"displayName": {"text": "7-11"}}]},
        status=200,
        match=[
            responses.matchers.json_params_matcher(
                {
                    "includedTypes": ["convenience_store"],
                    "maxResultCount": 20,
                    "locationRestriction": {
                        "circle": {"center": {"latitude": 25.0, "longitude": 121.0}, "radius": 200.0}
                    },
                }
            )
        ],
    )

    # Mock searchText for McDonald's
    responses.add(
        responses.POST,
        "https://places.googleapis.com/v1/places:searchText",
        json={"places": [{"displayName": {"text": "McDonald's"}}]},
        status=200,
        match=[
            responses.matchers.json_params_matcher(
                {
                    "textQuery": "McDonald's OR 麥當勞",
                    "maxResultCount": 20,
                    "locationRestriction": {
                        "rectangle": {
                            "low": {"latitude": 24.99820336943176, "longitude": 120.99801763750247},
                            "high": {"latitude": 25.00179663056824, "longitude": 121.00198236249753},
                        }
                    },
                }
            )
        ],
    )

    # Mock searchText for Starbucks
    responses.add(
        responses.POST,
        "https://places.googleapis.com/v1/places:searchText",
        json={},  # Equivalent to ZERO_RESULTS in old API
        status=200,
        match=[
            responses.matchers.json_params_matcher(
                {
                    "textQuery": "Starbucks OR 星巴克",
                    "maxResultCount": 20,
                    "locationRestriction": {
                        "rectangle": {
                            "low": {"latitude": 24.99820336943176, "longitude": 120.99801763750247},
                            "high": {"latitude": 25.00179663056824, "longitude": 121.00198236249753},
                        }
                    },
                }
            )
        ],
    )

    result = provider.enrich_location(25.0, 121.0)

    assert result["has_competitor_in_1000m"] is True
    assert result["competitors_data"] == ["Wash & Go"]
    assert result["cvs_mcd_in_200m"] == ["7-11", "McDonald's"]
    assert result["has_starbucks"] is False


def test_get_map_provider_google(monkeypatch):
    monkeypatch.setattr("laundro_vision_ai.services.location.get_settings", lambda: Settings(MAP_PROVIDER="GOOGLE"))
    from laundro_vision_ai.services.location import GoogleMapProvider, get_map_provider

    provider = get_map_provider(Mock())
    assert isinstance(provider, GoogleMapProvider)


def test_get_bounding_box():
    lat, lng = 25.033964, 121.564472
    radius = 200.0
    low, high = get_bounding_box(lat, lng, radius)

    assert "latitude" in low
    assert "longitude" in low
    assert "latitude" in high
    assert "longitude" in high
    assert low["latitude"] < high["latitude"]
    assert low["longitude"] < high["longitude"]

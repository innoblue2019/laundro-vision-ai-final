import os
from unittest.mock import patch

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
    get_map_provider,
)


def test_mock_provider_geocode():
    provider = MockMapProvider()
    lat, lng = provider.geocode("Taipei")
    assert isinstance(lat, float)
    assert isinstance(lng, float)


def test_mock_provider_enrich():
    provider = MockMapProvider()
    result = provider.enrich_location(25.0, 121.0)
    assert "has_competitor_in_1000m" in result
    assert result["has_starbucks"] is False


@respx.mock
def test_osm_provider_geocode():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=Response(200, json=[{"lat": "25.0338352", "lon": "121.5644995"}])
    )
    provider = OSMMapProvider()
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

    provider = OSMMapProvider()
    result = provider.enrich_location(25.0, 121.0)
    assert result["has_competitor_in_1000m"] is True
    assert result["competitors_data"] == ["Wash"]
    assert "7-11" in result["cvs_mcd_in_200m"]
    assert result["has_starbucks"] is True


def test_get_map_provider_mock():
    os.environ["MAP_PROVIDER"] = "MOCK"  # Explicitly set for this test
    provider = get_map_provider()
    assert isinstance(provider, MockMapProvider)


def test_get_map_provider_osm():
    # Default behavior is OSM, so no env var needed
    provider = get_map_provider()
    assert isinstance(provider, OSMMapProvider)


def test_calculate_q1_score():
    assert calculate_q1_score(True, []) == 1
    assert calculate_q1_score(False, []) == 1
    assert calculate_q1_score(False, ["7-11"]) == 3
    assert calculate_q1_score(False, ["7-11", "FamilyMart"]) == 5
    assert calculate_q1_score(False, ["McDonald's"]) == 5


@respx.mock
def test_osm_provider_geocode_no_results():
    respx.get("https://nominatim.openstreetmap.org/search").mock(return_value=Response(200, json=[]))
    provider = OSMMapProvider()
    with pytest.raises(ValueError, match="Could not geocode address"):
        provider.geocode("NonExistent Address")


@patch("requests.get")
def test_osm_provider_geocode_network_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException
    provider = OSMMapProvider()
    with pytest.raises(requests.exceptions.RequestException):
        provider.geocode("Taipei 101")


@patch("requests.post")
def test_osm_provider_enrich_network_error(mock_post):
    mock_post.side_effect = requests.exceptions.RequestException
    provider = OSMMapProvider()
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

    provider = GoogleMapProvider()

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

    provider = OSMMapProvider()
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

    provider = OSMMapProvider()
    result = provider.enrich_location(25.0, 121.0)
    assert result["has_starbucks"] is False

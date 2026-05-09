import os

from laundro_vision_ai.core.config import get_settings


def test_config_defaults():
    settings = get_settings()
    assert settings.MAP_PROVIDER == "OSM"


def test_config_override():
    get_settings.cache_clear()
    os.environ["MAP_PROVIDER"] = "MOCK"
    settings = get_settings()
    assert settings.MAP_PROVIDER == "MOCK"
    del os.environ["MAP_PROVIDER"]

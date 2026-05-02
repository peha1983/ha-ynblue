"""Helper tests for YnBlue."""

from __future__ import annotations

from custom_components.ynblue.helpers import build_entity_id


def test_build_entity_id_returns_canonical_english_ids():
    """Test canonical entity ids are generated from YnBlue unique ids."""

    assert build_entity_id(
        "6728deb3dd733500243dd844_temperature",
        "sensor",
    ) == "sensor.ynblue_water_temperature"
    assert build_entity_id(
        "6728deb3dd733500243dd844_force_measurement",
        "button",
    ) == "button.ynblue_force_measurement"
    assert build_entity_id(
        "6728deb3dd733500243dd844_electrolyser_temp_protection",
        "switch",
    ) == "switch.ynblue_electrolyser_low_temperature_protection"


def test_build_entity_id_returns_none_for_unknown_keys():
    """Test unknown unique ids are ignored by the registry migration."""

    assert build_entity_id("6728deb3dd733500243dd844_unknown_key", "sensor") is None

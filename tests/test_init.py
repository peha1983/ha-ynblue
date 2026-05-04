"""Entity creation tests for YnBlue."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from homeassistant.core import State
from homeassistant.helpers import entity_registry as er

from custom_components.ynblue import binary_sensor, button, light, number, select, sensor, switch
from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.coordinator import YnBlueCoordinator
from custom_components.ynblue.entity import _get_last_good_recorder_state
from custom_components.ynblue.models import YnBlueRuntimeData
from custom_components.ynblue.sensor import SENSOR_DESCRIPTIONS, YnBlueSensor


async def test_platform_setup_creates_core_entities(hass, config_entry, device_payload):
    """Test that the main platforms expose the expected entities."""

    device_payload["date_mqtt_connection"] = 1_777_733_547_424
    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )
    config_entry.runtime_data = runtime

    created_entities = []

    await sensor.async_setup_entry(hass, config_entry, created_entities.extend)
    await number.async_setup_entry(hass, config_entry, created_entities.extend)
    await select.async_setup_entry(hass, config_entry, created_entities.extend)
    await button.async_setup_entry(hass, config_entry, created_entities.extend)

    unique_ids = {entity.unique_id for entity in created_entities}

    assert f"{device_payload['id']}_temperature" in unique_ids
    assert f"{device_payload['id']}_last_cloud_contact" in unique_ids
    assert f"{device_payload['id']}_pool_volume" in unique_ids
    assert f"{device_payload['id']}_filter_mode" in unique_ids
    assert f"{device_payload['id']}_request_snapshot" in unique_ids


async def test_port_entities_are_created_before_snapshot_sections_arrive(hass, config_entry, device_payload):
    """Test that port entities are created from functionality flags alone."""

    partial_payload = deepcopy(device_payload)
    partial_payload.pop("light", None)
    partial_payload.pop("RGBLight", None)
    partial_payload.pop("robot", None)
    partial_payload.pop("swimJet", None)

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({partial_payload["id"]: partial_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )
    config_entry.runtime_data = runtime

    created_entities = []

    await light.async_setup_entry(hass, config_entry, created_entities.extend)
    await switch.async_setup_entry(hass, config_entry, created_entities.extend)
    await button.async_setup_entry(hass, config_entry, created_entities.extend)

    unique_ids = {entity.unique_id for entity in created_entities}

    assert f"{partial_payload['id']}_light" in unique_ids
    assert f"{partial_payload['id']}_rgb_light" in unique_ids
    assert f"{partial_payload['id']}_robot" in unique_ids
    assert f"{partial_payload['id']}_swim_jet" in unique_ids
    assert f"{partial_payload['id']}_cycle_rgb_program" in unique_ids


async def test_registered_entities_are_recreated_when_only_metadata_is_available(hass, config_entry, device_payload):
    """Test that previously known entities are recreated after an offline restart."""

    metadata_only_payload = {
        "id": device_payload["id"],
        "name": device_payload["name"],
        "isConnected": False,
        "functionalities": deepcopy(device_payload["functionalities"]),
    }

    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "ynblue",
        f"{device_payload['id']}_temperature",
        config_entry=config_entry,
    )
    registry.async_get_or_create(
        "number",
        "ynblue",
        f"{device_payload['id']}_pool_volume",
        config_entry=config_entry,
    )

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: metadata_only_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )
    config_entry.runtime_data = runtime

    created_entities = []

    await sensor.async_setup_entry(hass, config_entry, created_entities.extend)
    await number.async_setup_entry(hass, config_entry, created_entities.extend)
    await binary_sensor.async_setup_entry(hass, config_entry, created_entities.extend)

    unique_ids = {entity.unique_id for entity in created_entities}

    assert f"{device_payload['id']}_temperature" in unique_ids
    assert f"{device_payload['id']}_pool_volume" in unique_ids
    assert f"{device_payload['id']}_online" in unique_ids


async def test_sensor_uses_restored_state_when_live_section_is_missing(hass, config_entry, device_payload):
    """Test that restored values are exposed while the device is offline."""

    metadata_only_payload = {
        "id": device_payload["id"],
        "name": device_payload["name"],
        "isConnected": False,
        "functionalities": deepcopy(device_payload["functionalities"]),
    }

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: metadata_only_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )

    entity = YnBlueSensor(runtime, device_payload["id"], SENSOR_DESCRIPTIONS[0])
    entity._restored_state = "20.875"
    entity._restored_attributes = {"sensor_status": True}

    assert entity.available is True
    assert entity.native_value == 20.875
    assert entity.extra_state_attributes == {"sensor_status": True}


async def test_dynamic_sensor_unit_is_restored_when_live_data_is_missing(hass, config_entry, device_payload):
    """Test that dynamic sensor units fall back to the last Home Assistant state."""

    metadata_only_payload = {
        "id": device_payload["id"],
        "name": device_payload["name"],
        "isConnected": False,
        "functionalities": deepcopy(device_payload["functionalities"]),
    }

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: metadata_only_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )

    entity = YnBlueSensor(runtime, device_payload["id"], SENSOR_DESCRIPTIONS[2])
    entity._restored_state = "650"
    entity._restored_attributes = {"unit_of_measurement": "mV"}

    assert entity.native_value == 650.0
    assert entity.native_unit_of_measurement == "mV"


async def test_timestamp_sensor_uses_restored_datetime_when_live_data_is_missing(hass, config_entry, device_payload):
    """Test that timestamp sensors restore a parsed datetime value."""

    metadata_only_payload = {
        "id": device_payload["id"],
        "name": device_payload["name"],
        "isConnected": False,
        "functionalities": deepcopy(device_payload["functionalities"]),
    }

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: metadata_only_payload})
    runtime = YnBlueRuntimeData(
        api=api,
        coordinator=coordinator,
        hub=SimpleNamespace(available=True),
    )

    entity = YnBlueSensor(runtime, device_payload["id"], SENSOR_DESCRIPTIONS[-1])
    entity._restored_state = "2026-05-02T14:52:27+02:00"

    assert entity.native_value is not None
    assert entity.native_value.isoformat() == "2026-05-02T14:52:27+02:00"


async def test_recorder_fallback_skips_unavailable_states(hass):
    """Test that recorder fallback returns the last useful state."""

    with patch(
        "homeassistant.components.recorder.history.get_last_state_changes",
        return_value={
            "sensor.ynblue_water_temperature": [
                State("sensor.ynblue_water_temperature", "21.2"),
                State("sensor.ynblue_water_temperature", "unavailable"),
            ]
        },
    ):
        state = _get_last_good_recorder_state(hass, "sensor.ynblue_water_temperature")

    assert state is not None
    assert state.state == "21.2"

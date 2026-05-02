"""Entity creation tests for YnBlue."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from custom_components.ynblue import button, light, number, select, sensor, switch
from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.coordinator import YnBlueCoordinator
from custom_components.ynblue.models import YnBlueRuntimeData


async def test_platform_setup_creates_core_entities(hass, config_entry, device_payload):
    """Test that the main platforms expose the expected entities."""

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

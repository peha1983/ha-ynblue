"""Runtime tests for the YnBlue hub."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.coordinator import YnBlueCoordinator
from custom_components.ynblue.hub import YnBlueHub


async def test_hub_process_message_updates_state(hass, config_entry, device_payload):
    """Test MQTT state parsing."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._mqtt_connected.set()

    await hub.async_process_message(
        f"/YnBlue/{device_payload['id']}/data/json/measured",
        '{"data":{"temperature":{"measured":24.5,"status":true},"pH":{"measured":7.2,"sensorStatus":true}}}',
    )

    device = coordinator.get_device(device_payload["id"])
    assert device is not None
    assert device["temperature"]["measured"] == 24.5
    assert device["pH"]["measured"] == 7.2


async def test_pool_volume_command_payload(hass, config_entry, device_payload):
    """Test the pool volume payload format."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with patch.object(hub, "async_publish", AsyncMock()) as async_publish:
        await hub.async_set_pool_volume(device_payload["id"], 42)

    async_publish.assert_awaited_once_with(
        f"/YnBlue/{device_payload['id']}/system/poolVolume",
        {"poolVolume": 42},
    )


async def test_request_snapshot_uses_live_mqtt_when_available(hass, config_entry, device_payload):
    """Test that snapshot requests stay on the existing MQTT session once the hub is connected."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    hub._mqtt_client = object()  # type: ignore[assignment]
    hub._mqtt_connected.set()

    with patch.object(hub, "async_publish", AsyncMock()) as async_publish:
        await hub.async_request_snapshot(device_payload["id"])

    async_publish.assert_awaited_once_with(
        f"/YnBlue/{device_payload['id']}/json/all",
        {"state": True},
    )


async def test_request_snapshot_merges_fetched_snapshot(hass, config_entry, device_payload):
    """Test that the dedicated snapshot fetch updates the coordinator data."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: {"id": device_payload["id"]}})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    snapshot = {
        "system": {"poolVolume": 21},
        "temperature": {"measured": 20.875},
        "pH": {"measured": 7.4},
    }

    with (
        patch.object(api, "async_ensure_auth", AsyncMock(return_value="Bearer token")),
        patch.object(hass, "async_add_executor_job", AsyncMock(return_value=snapshot)),
    ):
        await hub.async_request_snapshot(device_payload["id"])

    device = coordinator.get_device(device_payload["id"])
    assert device is not None
    assert device["system"]["poolVolume"] == 21
    assert device["temperature"]["measured"] == 20.875
    assert device["pH"]["measured"] == 7.4
    assert device["isConnected"] is True

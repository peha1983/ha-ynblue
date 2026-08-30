"""Runtime tests for the YnBlue hub."""

from __future__ import annotations

import logging
import time
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.const import WARNING_REPEAT_INTERVAL
from custom_components.ynblue.coordinator import YnBlueCoordinator
from custom_components.ynblue.exceptions import YnBlueApiError, YnBlueCommandError, YnBlueMqttError
from custom_components.ynblue.hub import YnBlueHub, _fetch_snapshot_payload


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

    await hub.async_process_message(
        f"/YnBlue/{device_payload['id']}/data/json/measured",
        '{"data":{"temperature":{"measured":24.5,"status":true},"pH":{"measured":7.2,"sensorStatus":true}}}',
    )

    device = coordinator.get_device(device_payload["id"])
    assert device is not None
    assert device["temperature"]["measured"] == 24.5
    assert device["pH"]["measured"] == 7.2


async def test_pool_volume_command_payload(hass, config_entry, device_payload):
    """Test that pool volume commands publish the expected payload and confirm state."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._last_snapshot_success[device_payload["id"]] = time.monotonic()

    with (
        patch.object(hub, "async_publish", AsyncMock()) as async_publish,
        patch.object(
            hub,
            "_async_request_snapshot_locked",
            AsyncMock(return_value={"system": {"poolVolume": 42}}),
        ) as async_snapshot,
    ):
        await hub.async_set_pool_volume(device_payload["id"], 42)

    async_publish.assert_awaited_once_with(
        f"/YnBlue/{device_payload['id']}/system/poolVolume",
        {"poolVolume": 42},
    )
    async_snapshot.assert_awaited_once_with(device_payload["id"])


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


async def test_start_registers_periodic_refresh_listener(hass, config_entry, device_payload):
    """Test that polling is scheduled through Home Assistant's interval helper."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with patch.object(
        hub,
        "async_refresh_now",
        AsyncMock(),
    ), patch(
        "custom_components.ynblue.hub.async_track_time_interval",
        return_value=lambda: None,
    ) as async_track_time_interval:
        await hub.async_start()

    async_track_time_interval.assert_called_once()
    assert async_track_time_interval.call_args.args[1] == hub._async_handle_periodic_refresh
    assert hub.available is True


async def test_startup_keeps_entities_available_when_device_is_offline(hass, config_entry, device_payload):
    """Test that startup succeeds without snapshot traffic when the controller is offline."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data(
        {
            device_payload["id"]: {
                "id": device_payload["id"],
                "isConnected": False,
                "functionalities": device_payload["functionalities"],
            }
        }
    )
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with patch.object(hub, "async_request_snapshot", AsyncMock()) as async_request_snapshot, patch(
        "custom_components.ynblue.hub.async_track_time_interval",
        return_value=lambda: None,
    ):
        await hub.async_start()
        await hub.async_stop()

    device = coordinator.get_device(device_payload["id"])
    assert device is not None
    assert hub.available is False
    assert device["isConnected"] is False
    async_request_snapshot.assert_not_awaited()


async def test_refresh_requests_snapshot_after_online_transition(hass, config_entry, device_payload):
    """Test that a device returning online triggers an immediate snapshot refresh."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._last_known_connectivity[device_payload["id"]] = False

    with patch.object(hub, "async_request_snapshot", AsyncMock()) as async_request_snapshot:
        await hub.async_refresh_now(refresh_metadata=False)

    async_request_snapshot.assert_awaited_once_with(device_payload["id"])


async def test_offline_commands_are_rejected(hass, config_entry, device_payload):
    """Test that mutating commands fail closed while the controller is offline."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    offline_payload = dict(device_payload)
    offline_payload["isConnected"] = False

    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: offline_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with pytest.raises(YnBlueCommandError):
        await hub.async_set_pool_volume(device_payload["id"], 42)


async def test_ph_mode_command_uses_regulation_toggle_payload(hass, config_entry, device_payload):
    """Test that pH mode changes use the regulation payload, not manual injection."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._last_snapshot_success[device_payload["id"]] = time.monotonic()

    with (
        patch.object(hub, "async_publish", AsyncMock()) as async_publish,
        patch.object(
            hub,
            "_async_request_snapshot_locked",
            AsyncMock(return_value={"pH": {"mode": 1, "target": 7.4}}),
        ),
    ):
        await hub.async_set_ph_mode(device_payload["id"], 1)

    async_publish.assert_awaited_once_with(
        f"/YnBlue/{device_payload['id']}/pH/mode",
        {"mode": "1", "value": "7.40"},
    )


async def test_startup_logs_snapshot_failures_but_stays_running(hass, config_entry, device_payload):
    """Test that an online startup tolerates snapshot failures and keeps the runtime active."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with patch.object(
        hub,
        "async_request_snapshot",
        AsyncMock(side_effect=YnBlueMqttError("controller offline")),
    ) as async_request_snapshot:
        await hub.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="startup")

    assert hub.available is True
    async_request_snapshot.assert_awaited_once_with(device_payload["id"])


async def test_snapshot_failures_use_backoff(hass, config_entry, device_payload):
    """Test that repeated snapshot failures back off instead of hammering the broker."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with patch.object(
        hub,
        "async_request_snapshot",
        AsyncMock(side_effect=YnBlueMqttError("timed out")),
    ) as async_request_snapshot:
        await hub.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="periodic")
        await hub.async_refresh_now(refresh_metadata=False, reason="periodic")

    async_request_snapshot.assert_awaited_once_with(device_payload["id"])


async def test_refresh_uses_cached_metadata_when_api_times_out(hass, config_entry, device_payload, caplog):
    """Test that metadata timeouts do not stop snapshot refreshes once devices are known."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with (
        patch.object(
            coordinator,
            "async_refresh_metadata",
            AsyncMock(
                side_effect=YnBlueApiError(
                    f"YnBlue request timed out for /ynblue/{device_payload['id']}"
                )
            ),
        ),
        patch.object(hub, "async_request_snapshot", AsyncMock()) as async_request_snapshot,
    ):
        await hub.async_refresh_now(force_snapshot=True, reason="periodic")

    assert "using cached device data" in caplog.text
    assert device_payload["id"] not in caplog.text
    async_request_snapshot.assert_awaited_once_with(device_payload["id"])


async def test_metadata_warnings_are_throttled_and_recovery_is_logged(
    hass, config_entry, device_payload, caplog
):
    """Test metadata warnings are deduplicated without hiding recovery."""

    caplog.set_level(logging.INFO, logger="custom_components.ynblue.hub")
    sensitive_id = device_payload["id"]
    error = YnBlueApiError(f"YnBlue request timed out for /ynblue/{sensitive_id}")
    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({sensitive_id: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with (
        patch.object(
            coordinator,
            "async_refresh_metadata",
            AsyncMock(side_effect=[error, error, error, {}]),
        ),
        patch.object(hub, "async_request_snapshot", AsyncMock()),
    ):
        await hub.async_refresh_now(force_snapshot=True)
        await hub.async_refresh_now(force_snapshot=True)

        assert hub._metadata_warning_state is not None
        hub._metadata_warning_state.last_logged_at -= (
            WARNING_REPEAT_INTERVAL.total_seconds() + 1
        )
        await hub.async_refresh_now(force_snapshot=True)
        await hub.async_refresh_now(force_snapshot=True)

    warnings = [record.message for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "1 similar warning(s) suppressed" in warnings[-1]
    assert "metadata refresh recovered" in caplog.text
    assert hub._metadata_warning_state is None
    assert sensitive_id not in caplog.text


async def test_snapshot_warnings_are_throttled_and_device_id_is_redacted(
    hass, config_entry, device_payload, caplog
):
    """Test repeated snapshot warnings retain signal without leaking controller IDs."""

    caplog.set_level(logging.INFO, logger="custom_components.ynblue.hub")
    sensitive_id = device_payload["id"]
    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({sensitive_id: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._last_known_connectivity[sensitive_id] = False

    with patch.object(
        hub,
        "async_request_snapshot",
        AsyncMock(side_effect=YnBlueMqttError(f"timed out for {sensitive_id}")),
    ):
        await hub.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="periodic")
        await hub.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="periodic")

        state = hub._snapshot_warning_states[sensitive_id]
        state.last_logged_at -= WARNING_REPEAT_INTERVAL.total_seconds() + 1
        await hub.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="periodic")

    hub._log_snapshot_recovery(sensitive_id)

    warnings = [record.message for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert warnings[0].startswith("Could not fetch a YnBlue snapshot for controller 1")
    assert "1 similar warning(s) suppressed" in warnings[-1]
    assert "snapshot refresh recovered for controller 1" in caplog.text
    assert "back online" in caplog.text
    assert sensitive_id not in caplog.text


def test_snapshot_helper_wraps_connect_timeout():
    """Test that low-level MQTT connect timeouts become YnBlueMqttError."""

    with patch("custom_components.ynblue.hub.mqtt.Client") as mqtt_client:
        mqtt_client.return_value.connect.side_effect = TimeoutError("timed out")

        with pytest.raises(YnBlueMqttError, match="Could not connect for a YnBlue snapshot"):
            _fetch_snapshot_payload("device-id", "Bearer token")


async def test_stale_snapshot_rejects_commands(hass, config_entry, device_payload):
    """Test that commands fail closed when no fresh live snapshot is available."""

    api = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({device_payload["id"]: device_payload})
    hub = YnBlueHub(hass, config_entry, coordinator, api)

    with pytest.raises(YnBlueCommandError):
        await hub.async_set_pool_volume(device_payload["id"], 42)

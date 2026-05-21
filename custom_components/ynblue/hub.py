"""Runtime hub for YnBlue state refreshes and commands."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import queue
import ssl
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any

import paho.mqtt.client as mqtt
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .client import YnBlueApiClient
from .const import (
    CHEMICAL_MODE_OPTIONS,
    COMMAND_SETTLE_DELAY,
    ELECTROLYSER_PROTECTION_OPTIONS,
    FILTER_MODE_OPTIONS,
    FORCE_MEASUREMENT_SETTLE_DELAY,
    FORCE_MEASUREMENT_TOGGLE_DELAY,
    HEATER_MODE_OPTIONS,
    INITIAL_SNAPSHOT_DELAY,
    METADATA_REFRESH_INTERVAL,
    MQTT_CONNECT_TIMEOUT,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PATH,
    MQTT_PORT,
    MQTT_USERNAME,
    PH_MODE_OPTIONS,
    RESTART_RECOVERY_DELAY,
    SNAPSHOT_REFRESH_INTERVAL,
    SNAPSHOT_RESPONSE_TIMEOUT,
    SNAPSHOT_RETRY_BACKOFF_INITIAL,
    SNAPSHOT_RETRY_BACKOFF_MAX,
    SNAPSHOT_STALE_INTERVAL,
)
from .coordinator import YnBlueCoordinator
from .exceptions import (
    YnBlueAuthError,
    YnBlueCommandError,
    YnBlueMqttError,
    YnBlueValidationError,
)
from .helpers import deep_merge_dict, get_nested_value, set_nested_value

_LOGGER = logging.getLogger(__name__)


class YnBlueHub:
    """Coordinate periodic refreshes and validated write operations."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: YnBlueCoordinator,
        api: YnBlueApiClient,
    ) -> None:
        """Initialize the hub."""

        self.hass = hass
        self.config_entry = config_entry
        self.coordinator = coordinator
        self.api = api
        self._runtime_ready = asyncio.Event()
        self._start_lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()
        self._device_locks: dict[str, asyncio.Lock] = {}
        self._cancel_periodic_refresh: Any | None = None
        self._cancel_delayed_refreshes: list[Callable[[], None]] = []
        self._stopped = False
        self._started = False
        self._last_snapshot_success: dict[str, float] = {}
        self._last_snapshot_attempt: dict[str, float] = {}
        self._last_known_connectivity: dict[str, bool] = {}
        self._snapshot_failures: dict[str, int] = {}

    @property
    def available(self) -> bool:
        """Return whether the runtime is active."""

        return self._runtime_ready.is_set()

    async def async_start(self) -> None:
        """Start the YnBlue runtime."""

        async with self._start_lock:
            if self._started:
                return

            self._stopped = False
            await self.async_refresh_now(force_snapshot=True, refresh_metadata=False, reason="startup")
            self._runtime_ready.set()
            self._cancel_periodic_refresh = async_track_time_interval(
                self.hass,
                self._async_handle_periodic_refresh,
                METADATA_REFRESH_INTERVAL,
            )
            self._started = True

    async def async_stop(self) -> None:
        """Stop the YnBlue runtime."""

        self._stopped = True
        self._runtime_ready.clear()

        if self._cancel_periodic_refresh is not None:
            self._cancel_periodic_refresh()
            self._cancel_periodic_refresh = None

        for cancel_refresh in self._cancel_delayed_refreshes:
            cancel_refresh()
        self._cancel_delayed_refreshes.clear()

        self._started = False

    async def async_reconnect(self) -> None:
        """Refresh metadata and force a fresh snapshot cycle."""

        await self.async_refresh_now(force_snapshot=True, reason="manual_reconnect")

    def device_data_is_fresh(self, device_id: str) -> bool:
        """Return whether the latest live snapshot is still considered fresh."""

        last_success = self._last_snapshot_success.get(device_id)
        if last_success is None:
            return False
        return time.monotonic() - last_success <= SNAPSHOT_STALE_INTERVAL.total_seconds()

    def is_device_online(self, device_id: str) -> bool:
        """Return whether the controller is online and yielding fresh live data."""

        device = self.coordinator.get_device(device_id)
        if device is None or not bool(device.get("isConnected")):
            return False
        return self.device_data_is_fresh(device_id)

    def get_snapshot_age_minutes(self, device_id: str) -> float | None:
        """Return the age of the latest successful live snapshot in minutes."""

        last_success = self._last_snapshot_success.get(device_id)
        if last_success is None:
            return None
        return (time.monotonic() - last_success) / 60

    async def async_refresh_now(
        self,
        *,
        force_snapshot: bool = False,
        refresh_metadata: bool = True,
        reason: str = "manual",
    ) -> None:
        """Refresh coordinator metadata and device snapshots."""

        async with self._refresh_lock:
            if self._stopped:
                return

            if refresh_metadata:
                try:
                    await self.coordinator.async_refresh_metadata()
                except YnBlueAuthError:
                    await self._async_start_reauth()
                    raise

            self._prune_removed_devices()
            await self._async_refresh_due_snapshots(force_snapshot=force_snapshot, reason=reason)
            self._runtime_ready.set()

    async def async_request_snapshot(self, device_id: str) -> None:
        """Request a fresh state snapshot for one device."""

        async with self._async_device_lock(device_id):
            await self._async_request_snapshot_locked(device_id)

    async def async_restart_device(self, device_id: str) -> None:
        """Restart the YnBlue controller."""

        async with self._async_device_lock(device_id):
            self._require_online_device(device_id)
            try:
                await self.async_publish(f"/YnBlue/{device_id}/system/restart", {"state": True})
            except YnBlueMqttError as err:
                raise YnBlueCommandError(f"Could not restart YnBlue controller {device_id}") from err

            self._last_snapshot_success.pop(device_id, None)
            self._last_known_connectivity[device_id] = False
            existing = self.coordinator.get_device(device_id) or {}
            self.coordinator.async_update_device(
                device_id,
                deep_merge_dict(existing, {"isConnected": False}),
            )

        self._cancel_delayed_refreshes.append(
            async_call_later(
                self.hass,
                RESTART_RECOVERY_DELAY,
                lambda _now: self.hass.async_create_background_task(
                    self._async_run_delayed_refresh(f"restart_recovery:{device_id}"),
                    f"ynblue_restart_recovery_{device_id}",
                ),
            )
        )

    async def async_force_measurement(self, device_id: str) -> None:
        """Trigger a manual measurement pulse and refresh the resulting state."""

        async with self._async_device_lock(device_id):
            self._require_online_device(device_id)
            try:
                await self.async_publish(f"/YnBlue/{device_id}/system/forceMeasurement", {"state": True})
                await asyncio.sleep(FORCE_MEASUREMENT_TOGGLE_DELAY)
                await self.async_publish(f"/YnBlue/{device_id}/system/forceMeasurement", {"state": False})
                await asyncio.sleep(FORCE_MEASUREMENT_SETTLE_DELAY)
                await self._async_request_snapshot_locked(device_id)
            except YnBlueMqttError as err:
                raise YnBlueCommandError(f"Could not complete a forced measurement for {device_id}") from err

    async def async_set_pool_volume(self, device_id: str, value: float) -> None:
        """Update the pool volume."""

        self._validate_range("pool volume", value, minimum=1, maximum=500)
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/system/poolVolume",
            {"poolVolume": value},
            expected_state={"system": {"poolVolume": value}},
        )

    async def async_set_filter_mode(self, device_id: str, section: str, mode: int) -> None:
        """Update the filter mode."""

        self._validate_mode("filter mode", mode, FILTER_MODE_OPTIONS)
        filter_data = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        payload: dict[str, Any] = {"mode": mode}
        if mode == 4:
            payload["param1"] = _first_or_full(filter_data.get("durationSwitchOn"))
            payload["param2"] = _first_or_full(filter_data.get("duration"))
            duration_vs = filter_data.get("durationVs")
            if duration_vs is not None:
                payload["param3"] = _first_or_full(duration_vs)

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/{section}/mode",
            payload,
            expected_state={section: {"mode": mode}},
        )

    async def async_set_heater_mode(self, device_id: str, section: str, mode: int) -> None:
        """Update the heater mode."""

        self._validate_mode("heater mode", mode, HEATER_MODE_OPTIONS)
        heater = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        payload: dict[str, Any] = {"mode": mode}
        if mode == 1:
            payload["param1"] = heater.get("target", 25)
            payload["param2"] = heater.get("meteoTempOffset", 0)
        else:
            payload["param1"] = 0
            payload["param2"] = 0

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/{section}/mode",
            payload,
            expected_state={section: {"mode": mode}},
        )

    async def async_set_heater_target(self, device_id: str, section: str, target: float) -> None:
        """Update the heater target temperature."""

        self._validate_range("heater target", target, minimum=0, maximum=40)
        heater = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        mode = int(heater.get("mode", 0))
        payload = {
            "mode": mode,
            "param1": target if mode == 1 else 0,
            "param2": heater.get("meteoTempOffset", 0) if mode == 1 else 0,
        }
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/{section}/mode",
            payload,
            expected_state={section: {"target": target}},
        )

    async def async_set_chemical_mode(self, device_id: str, mode: int) -> None:
        """Update the chemical dosing mode."""

        self._validate_mode("chemical mode", mode, CHEMICAL_MODE_OPTIONS)
        chemical = get_nested_value(self.coordinator.get_device(device_id), "chemical", default={}) or {}
        target = float(chemical.get("target", 650))
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/chemical/mode",
            {"mode": mode, "value": target},
            expected_state={"chemical": {"mode": mode}},
        )

    async def async_set_chemical_target(self, device_id: str, value: float) -> None:
        """Update the chemical target."""

        chemical = get_nested_value(self.coordinator.get_device(device_id), "chemical", default={}) or {}
        maximum = 1000 if chemical.get("sensorType") == 1 else 5
        self._validate_range("chemical target", value, minimum=0, maximum=maximum)
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/chemical/mode",
            {"mode": int(chemical.get("mode", 0)), "value": value},
            expected_state={"chemical": {"target": value}},
        )

    async def async_set_ph_mode(self, device_id: str, mode: int) -> None:
        """Enable or disable automatic pH regulation."""

        self._validate_mode("pH mode", mode, PH_MODE_OPTIONS)
        ph = get_nested_value(self.coordinator.get_device(device_id), "pH", default={}) or {}
        target = float(ph.get("target", 7.2))
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/pH/mode",
            {"mode": str(mode), "value": f"{target:.2f}"},
            expected_state={"pH": {"mode": mode}},
        )

    async def async_stop_ph_injection(self, device_id: str) -> None:
        """Stop the current manual pH injection."""

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/pH/mode",
            {"mode": 2, "value": 0},
            post_delay=COMMAND_SETTLE_DELAY,
        )

    async def async_inject_ph(self, device_id: str) -> None:
        """Start a 1L manual pH injection."""

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/pH/mode",
            {"mode": 2, "value": 1},
            post_delay=COMMAND_SETTLE_DELAY,
        )

    async def async_set_ph_target(self, device_id: str, value: float) -> None:
        """Update the pH target."""

        self._validate_range("pH target", value, minimum=3, maximum=10)
        ph = get_nested_value(self.coordinator.get_device(device_id), "pH", default={}) or {}
        mode = 1 if int(ph.get("mode", 0)) == 1 else 0
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/pH/mode",
            {"mode": str(mode), "value": f"{value:.2f}"},
            expected_state={"pH": {"target": value}},
        )

    async def async_set_electrolyser_temp_protection(self, device_id: str, enabled: bool) -> None:
        """Toggle electrolyser low-temperature protection."""

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/electrolyser/tempProtection",
            {"mode": bool(enabled)},
            expected_state={"electrolyser": {"tempProtection": bool(enabled)}},
        )

    async def async_set_electrolyser_protection_mode(self, device_id: str, mode: int) -> None:
        """Set the electrolyser protection mode."""

        self._validate_mode("electrolyser protection mode", mode, ELECTROLYSER_PROTECTION_OPTIONS)
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/electrolyser/protectionMode",
            {"mode": mode},
            expected_state={"electrolyser": {"protectionMode": mode}},
        )

    async def async_set_port_state(self, device_id: str, section: str, enabled: bool) -> None:
        """Toggle a simple on/off port-based output."""

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/{section}/state",
            {"state": bool(enabled)},
            expected_state={section: {"state": bool(enabled)}},
        )

    async def async_cycle_rgb(self, device_id: str) -> None:
        """Cycle the RGB light program."""

        rgb_light = get_nested_value(self.coordinator.get_device(device_id), "RGBLight", default={}) or {}
        next_state = not bool(rgb_light.get("state"))
        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/RGBLight/changeRGB",
            {"state": next_state},
        )

    async def async_reset_consumption(self, device_id: str, section: str) -> None:
        """Reset a consumption counter and refresh state afterward."""

        await self._async_execute_command(
            device_id,
            f"/YnBlue/{device_id}/{section}/consoReset",
            {},
        )

    async def async_publish(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        """Publish a JSON message to YnBlue over a short-lived MQTT session."""

        if not topic.startswith("/YnBlue/"):
            raise YnBlueValidationError("Refusing to publish outside the YnBlue topic namespace")

        token = await self.api.async_ensure_auth()
        await self.hass.async_add_executor_job(
            _publish_ephemeral_message,
            topic,
            json.dumps(payload),
            token,
            retain,
        )

    async def async_process_message(self, topic: str, payload: str) -> None:
        """Parse and apply a state update from a YnBlue MQTT payload."""

        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            _LOGGER.debug("Discarding invalid YnBlue MQTT payload for %s", topic)
            return

        if not topic.startswith("/YnBlue/"):
            return

        parts = topic.split("/")
        if len(parts) < 4:
            return
        device_id = parts[2]
        body = message.get("data", message)

        if topic.endswith("/connected_ack"):
            state = str(body.get("state", "")).lower() == "true"
            self.coordinator.async_update_device(device_id, {"isConnected": state})
            self._last_known_connectivity[device_id] = state
            return

        if topic.endswith("/notification_ack"):
            return

        if "/data/json/" not in topic:
            return

        section_path = topic.split("/data/json/", maxsplit=1)[1]
        if not isinstance(body, dict):
            return

        updates = (
            dict(body)
            if section_path in {"all", "measured"}
            else set_nested_value(section_path.split("/"), body)
        )

        updates["isConnected"] = True
        existing = self.coordinator.get_device(device_id) or {}
        self.coordinator.async_update_device(device_id, deep_merge_dict(existing, updates))
        self._last_known_connectivity[device_id] = True
        self._last_snapshot_success[device_id] = time.monotonic()

    async def _async_handle_periodic_refresh(self, _now: Any) -> None:
        """Refresh metadata and due snapshots on the Home Assistant scheduler."""

        if self._stopped:
            return

        try:
            await self.async_refresh_now(reason="periodic")
        except YnBlueAuthError:
            await self._async_start_reauth()
        except Exception:
            _LOGGER.exception("Unexpected error while refreshing YnBlue state")

    async def _async_refresh_due_snapshots(self, *, force_snapshot: bool, reason: str) -> None:
        """Refresh any online devices whose snapshots are due."""

        now = time.monotonic()
        due_devices: list[str] = []

        for device_id, device in self.coordinator.data.items():
            is_connected = bool(device.get("isConnected"))
            was_connected = self._last_known_connectivity.get(device_id)
            self._last_known_connectivity[device_id] = is_connected

            if was_connected is True and not is_connected:
                _LOGGER.info("YnBlue device %s is currently offline", device_id)
            elif was_connected is False and is_connected:
                _LOGGER.info("YnBlue device %s is back online", device_id)

            if not is_connected:
                continue

            if force_snapshot or was_connected is not True or self._snapshot_due(device_id, now):
                due_devices.append(device_id)

        for device_id in due_devices:
            try:
                await self.async_request_snapshot(device_id)
            except YnBlueMqttError as err:
                self._last_snapshot_attempt[device_id] = time.monotonic()
                self._snapshot_failures[device_id] = self._snapshot_failures.get(device_id, 0) + 1
                _LOGGER.warning(
                    "Could not fetch the YnBlue %s snapshot for %s: %s",
                    reason,
                    device_id,
                    err,
                )

    async def _async_request_snapshot_locked(self, device_id: str) -> dict[str, Any]:
        """Fetch and merge a full snapshot while holding the device lock."""

        self._require_known_device(device_id)
        self._last_snapshot_attempt[device_id] = time.monotonic()
        token = await self.api.async_ensure_auth()
        snapshot = await self.hass.async_add_executor_job(_fetch_snapshot_payload, device_id, token)
        snapshot["isConnected"] = True
        existing = self.coordinator.get_device(device_id) or {}
        merged = deep_merge_dict(existing, snapshot)
        self.coordinator.async_update_device(device_id, merged)
        self._last_snapshot_success[device_id] = time.monotonic()
        self._last_known_connectivity[device_id] = True
        self._snapshot_failures.pop(device_id, None)
        return snapshot

    async def _async_execute_command(
        self,
        device_id: str,
        topic: str,
        payload: dict[str, Any],
        *,
        expected_state: Mapping[str, Any] | None = None,
        post_delay: float = COMMAND_SETTLE_DELAY,
    ) -> dict[str, Any]:
        """Publish a command, refresh state, and verify the resulting snapshot."""

        async with self._async_device_lock(device_id):
            self._require_online_device(device_id)
            try:
                await self.async_publish(topic, payload)

                if post_delay > 0:
                    await asyncio.sleep(post_delay)

                snapshot = await self._async_request_snapshot_locked(device_id)
            except YnBlueMqttError as err:
                raise YnBlueCommandError(f"Could not confirm YnBlue command for {device_id}") from err

            if expected_state is not None and not _subset_matches(snapshot, expected_state):
                raise YnBlueCommandError(
                    f"YnBlue command to {topic} did not produce the expected device state"
                )
            return snapshot

    async def _async_run_delayed_refresh(self, reason: str) -> None:
        """Run a forced refresh after a scheduled grace delay."""

        if self._stopped:
            return

        try:
            await self.async_refresh_now(force_snapshot=True, reason=reason)
        except YnBlueAuthError:
            await self._async_start_reauth()
        except Exception:
            _LOGGER.exception("Delayed YnBlue refresh failed after %s", reason)

    async def _async_start_reauth(self) -> None:
        """Start Home Assistant reauthentication."""

        progress = self.hass.config_entries.flow.async_progress_by_handler(self.config_entry.domain)
        if any(flow["context"].get("entry_id") == self.config_entry.entry_id for flow in progress):
            return
        await self.hass.config_entries.flow.async_init(
            self.config_entry.domain,
            context={"source": SOURCE_REAUTH, "entry_id": self.config_entry.entry_id},
            data=self.config_entry.data,
        )

    def _prune_removed_devices(self) -> None:
        """Drop cached runtime state for devices that no longer exist."""

        current_ids = set(self.coordinator.data)
        for cache in (
            self._device_locks,
            self._last_snapshot_success,
            self._last_snapshot_attempt,
            self._last_known_connectivity,
            self._snapshot_failures,
        ):
            for device_id in tuple(cache):
                if device_id not in current_ids:
                    cache.pop(device_id, None)

    def _snapshot_due(self, device_id: str, now: float) -> bool:
        """Return whether the next periodic snapshot is due."""

        failures = self._snapshot_failures.get(device_id, 0)
        last_attempt = self._last_snapshot_attempt.get(device_id)
        last_success = self._last_snapshot_success.get(device_id)
        if failures > 0 and last_attempt is not None:
            return now - last_attempt >= self._snapshot_retry_delay(failures)
        if last_success is None:
            return True
        return now - last_success >= SNAPSHOT_REFRESH_INTERVAL.total_seconds()

    @staticmethod
    def _snapshot_retry_delay(failures: int) -> float:
        """Return the next retry delay in seconds for repeated snapshot failures."""

        exponent = max(0, failures - 1)
        delay = SNAPSHOT_RETRY_BACKOFF_INITIAL.total_seconds() * (2**exponent)
        return min(delay, SNAPSHOT_RETRY_BACKOFF_MAX.total_seconds())

    def _async_device_lock(self, device_id: str) -> asyncio.Lock:
        """Return the per-device operation lock."""

        return self._device_locks.setdefault(device_id, asyncio.Lock())

    def _require_known_device(self, device_id: str) -> dict[str, Any]:
        """Return the current device payload or raise."""

        device = self.coordinator.get_device(device_id)
        if device is None:
            raise YnBlueValidationError(f"Unknown YnBlue device: {device_id}")
        return device

    def _require_online_device(self, device_id: str) -> dict[str, Any]:
        """Return the current device payload when the controller is online."""

        device = self._require_known_device(device_id)
        if not bool(device.get("isConnected")):
            raise YnBlueCommandError(
                "The YnBlue controller is currently offline, so this command cannot be confirmed safely"
            )
        if not self.device_data_is_fresh(device_id):
            raise YnBlueCommandError(
                "The YnBlue controller has not provided a fresh live snapshot recently, so this command "
                "cannot be confirmed safely"
            )
        return device

    @staticmethod
    def _validate_mode(label: str, mode: int, options: Mapping[int, str]) -> None:
        """Validate a numeric mode value against a known mapping."""

        if mode not in options:
            raise YnBlueValidationError(f"Unsupported {label}: {mode}")

    @staticmethod
    def _validate_range(label: str, value: float, *, minimum: float, maximum: float) -> None:
        """Validate that a numeric value falls within a supported range."""

        if value < minimum or value > maximum:
            raise YnBlueValidationError(
                f"{label.capitalize()} must be between {minimum} and {maximum}"
            )


def _build_tls_context() -> ssl.SSLContext:
    """Create a TLS context for the YnBlue MQTT WebSocket connection."""

    return ssl.create_default_context()


def _disconnect_client(client: mqtt.Client) -> None:
    """Stop and disconnect the Paho client loop."""

    try:
        client.disconnect()
    finally:
        client.loop_stop()


def _publish_message(client: mqtt.Client, topic: str, payload: str, retain: bool) -> None:
    """Publish a message and fail if Paho reports an error."""

    info = client.publish(topic, payload, retain=retain)
    try:
        info.wait_for_publish()
    except RuntimeError as err:
        raise YnBlueMqttError(f"Failed to publish MQTT message to {topic}: {err}") from err
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        raise YnBlueMqttError(f"Failed to publish MQTT message to {topic}: rc={info.rc}")


def _fetch_snapshot_payload(device_id: str, token: str) -> dict[str, Any]:
    """Fetch a full snapshot over a short-lived MQTT connection."""

    topic = f"/YnBlue/{device_id}/data/json/all"
    request_topic = f"/YnBlue/{device_id}/json/all"
    response_queue: queue.Queue[str] = queue.Queue(maxsize=1)
    connected = threading.Event()
    connect_error: list[str] = []

    def on_connect(
        client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        result_code: int,
    ) -> None:
        if result_code != mqtt.MQTT_ERR_SUCCESS:
            connect_error.append(str(result_code))
            connected.set()
            return
        client.subscribe(topic)
        connected.set()

    def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = msg.payload.decode("utf-8")
        except UnicodeDecodeError as err:
            connect_error.append(f"Invalid snapshot payload encoding: {err}")
            return
        if response_queue.full():
            return
        response_queue.put_nowait(payload)

    client = mqtt.Client(
        client_id=_build_client_id("ha_snapshot", device_id),
        transport="websockets",
        protocol=mqtt.MQTTv311,
    )
    client.tls_set_context(_build_tls_context())
    client.username_pw_set(MQTT_USERNAME, token)
    client.ws_set_options(path=MQTT_PATH)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()

    try:
        if not connected.wait(MQTT_CONNECT_TIMEOUT):
            raise YnBlueMqttError("Timed out waiting for the YnBlue snapshot MQTT connection")
        if connect_error:
            raise YnBlueMqttError(f"Could not connect for a YnBlue snapshot: {connect_error[-1]}")

        time.sleep(INITIAL_SNAPSHOT_DELAY)
        _publish_message(client, request_topic, json.dumps({"state": True}), False)

        try:
            raw_payload = response_queue.get(timeout=SNAPSHOT_RESPONSE_TIMEOUT)
        except queue.Empty as err:
            raise YnBlueMqttError("Timed out waiting for the YnBlue snapshot payload") from err

        message = json.loads(raw_payload)
    except json.JSONDecodeError as err:
        raise YnBlueMqttError("Received invalid JSON in the YnBlue snapshot payload") from err
    finally:
        _disconnect_client(client)

    body = message.get("data", message)
    if not isinstance(body, dict):
        raise YnBlueMqttError("Received an invalid YnBlue snapshot structure")
    return dict(body)


def _publish_ephemeral_message(topic: str, payload: str, token: str, retain: bool) -> None:
    """Publish a command over a short-lived MQTT connection."""

    connected = threading.Event()
    connect_error: list[str] = []

    def on_connect(
        _client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        result_code: int,
    ) -> None:
        if result_code != mqtt.MQTT_ERR_SUCCESS:
            connect_error.append(str(result_code))
        connected.set()

    device_id = topic.split("/")[2] if topic.startswith("/YnBlue/") else "unknown"
    client = mqtt.Client(
        client_id=_build_client_id("ha_command", device_id),
        transport="websockets",
        protocol=mqtt.MQTTv311,
    )
    client.tls_set_context(_build_tls_context())
    client.username_pw_set(MQTT_USERNAME, token)
    client.ws_set_options(path=MQTT_PATH)
    client.on_connect = on_connect
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()

    try:
        if not connected.wait(MQTT_CONNECT_TIMEOUT):
            raise YnBlueMqttError("Timed out waiting for the YnBlue command MQTT connection")
        if connect_error:
            raise YnBlueMqttError(f"Could not connect for a YnBlue command publish: {connect_error[-1]}")

        time.sleep(INITIAL_SNAPSHOT_DELAY)
        _publish_message(client, topic, payload, retain)
    finally:
        _disconnect_client(client)


def _build_client_id(prefix: str, device_id: str) -> str:
    """Build a unique MQTT client identifier."""

    return f"{prefix}_{device_id[:8]}_{uuid.uuid4().hex[:8]}"


def _first_or_full(value: Any) -> Any:
    """Return the first item for single-schedule lists, otherwise the original value."""

    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _subset_matches(actual: Any, expected: Any) -> bool:
    """Return whether the expected subset matches the actual snapshot payload."""

    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return False
        return all(key in actual and _subset_matches(actual[key], value) for key, value in expected.items())

    if isinstance(expected, bool):
        return bool(actual) is expected

    if isinstance(expected, int | float) and isinstance(actual, int | float | str):
        try:
            return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=0.05)
        except (TypeError, ValueError):
            return False

    return actual == expected

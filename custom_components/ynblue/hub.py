"""MQTT runtime hub for YnBlue."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import ssl
import threading
import time
from datetime import timedelta
from typing import Any

import paho.mqtt.client as mqtt
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.core import HomeAssistant

from .client import YnBlueApiClient
from .const import (
    AUTH_REFRESH_FALLBACK,
    ELECTROLYSER_PROTECTION_OPTIONS,
    INITIAL_SNAPSHOT_DELAY,
    MQTT_CONNECT_TIMEOUT,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PATH,
    MQTT_PORT,
    MQTT_USERNAME,
    SNAPSHOT_RESPONSE_TIMEOUT,
)
from .coordinator import YnBlueCoordinator
from .exceptions import YnBlueAuthError, YnBlueMqttError
from .helpers import deep_merge_dict, get_nested_value, set_nested_value

_LOGGER = logging.getLogger(__name__)


class YnBlueHub:
    """Own the MQTT connection and write operations."""

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
        self._mqtt_client: mqtt.Client | None = None
        self._mqtt_connected = asyncio.Event()
        self._start_lock = asyncio.Lock()
        self._stopped = False
        self._started = False
        self._token_refresh_task: asyncio.Task[None] | None = None
        self._reconnecting = False

    @property
    def available(self) -> bool:
        """Return whether the MQTT connection is available."""

        return self._mqtt_connected.is_set()

    async def async_start(self) -> None:
        """Start the MQTT connection."""

        async with self._start_lock:
            if self._started:
                return

            self._stopped = False
            await self._async_prime_snapshots()
            self._mqtt_connected.set()
            self._started = True

    async def async_stop(self) -> None:
        """Stop the MQTT runtime."""

        self._stopped = True
        self._mqtt_connected.clear()

        if self._token_refresh_task is not None:
            self._token_refresh_task.cancel()
            self._token_refresh_task = None

        if self._mqtt_client is not None:
            client = self._mqtt_client
            self._mqtt_client = None
            await self.hass.async_add_executor_job(_disconnect_client, client)

        self._started = False

    async def async_reconnect(self) -> None:
        """Refresh the current YnBlue snapshot state."""

        if self._reconnecting or self._stopped:
            return

        self._reconnecting = True
        try:
            self._mqtt_connected.clear()
            await self._async_prime_snapshots()
            self._mqtt_connected.set()
        finally:
            self._reconnecting = False

    async def _async_connect(self, token: str) -> None:
        """Create and connect the MQTT client."""

        self._mqtt_connected.clear()
        client_id = f"ha_{self.config_entry.entry_id[:8]}"
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            transport="websockets",
            protocol=mqtt.MQTTv311,
        )
        tls_context = await self.hass.async_add_executor_job(_build_tls_context)
        client.tls_set_context(tls_context)
        client.username_pw_set(MQTT_USERNAME, token)
        client.ws_set_options(path=MQTT_PATH)
        client.reconnect_delay_set(min_delay=1, max_delay=60)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        self._mqtt_client = client
        _LOGGER.debug("Connecting to YnBlue MQTT at %s:%s", MQTT_HOST, MQTT_PORT)
        try:
            await self.hass.async_add_executor_job(_connect_client, client)
        except OSError as err:
            self._mqtt_client = None
            raise YnBlueMqttError(f"Could not connect to YnBlue MQTT: {err}") from err

        try:
            async with asyncio.timeout(MQTT_CONNECT_TIMEOUT):
                await self._mqtt_connected.wait()
        except TimeoutError as err:
            await self.hass.async_add_executor_job(_disconnect_client, client)
            self._mqtt_client = None
            raise YnBlueMqttError("Timed out waiting for the YnBlue MQTT connection") from err

    async def _async_refresh_loop(self) -> None:
        """Refresh the JWT before it expires."""

        while not self._stopped:
            wait_seconds = self.api.seconds_until_expiry
            if wait_seconds is None:
                delay = AUTH_REFRESH_FALLBACK
            else:
                delay = timedelta(seconds=max(300, min(wait_seconds - 300, AUTH_REFRESH_FALLBACK.total_seconds())))

            try:
                await asyncio.sleep(delay.total_seconds())
                if self._stopped:
                    return
                old_token = self.api.token
                await self.api.async_ensure_auth()
                if self.api.token != old_token:
                    await self.async_reconnect()
            except asyncio.CancelledError:
                raise
            except YnBlueAuthError:
                await self._async_start_reauth()
                return
            except Exception:
                _LOGGER.exception("Unexpected error while refreshing the YnBlue JWT")

    async def async_request_snapshot(self, device_id: str) -> None:
        """Request a fresh all-in-one state snapshot from YnBlue."""

        if self.available and self._mqtt_client is not None:
            await self.async_publish(f"/YnBlue/{device_id}/json/all", {"state": True})
            return

        token = await self.api.async_ensure_auth()
        snapshot = await self.hass.async_add_executor_job(_fetch_snapshot_payload, device_id, token)
        snapshot["isConnected"] = True
        existing = self.coordinator.get_device(device_id) or {}
        self.coordinator.async_update_device(device_id, deep_merge_dict(existing, snapshot))

    async def async_restart_device(self, device_id: str) -> None:
        """Restart the YnBlue controller."""

        await self.async_publish(f"/YnBlue/{device_id}/system/restart", {"state": True})

    async def async_force_measurement(self, device_id: str) -> None:
        """Trigger a manual measurement pulse."""

        await self.async_publish(f"/YnBlue/{device_id}/system/forceMeasurement", {"state": True})
        await asyncio.sleep(1)
        await self.async_publish(f"/YnBlue/{device_id}/system/forceMeasurement", {"state": False})

    async def async_set_pool_volume(self, device_id: str, value: float) -> None:
        """Update the pool volume."""

        await self.async_publish(f"/YnBlue/{device_id}/system/poolVolume", {"poolVolume": value})

    async def async_set_filter_mode(self, device_id: str, section: str, mode: int) -> None:
        """Update the filter mode."""

        filter_data = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        payload: dict[str, Any] = {"mode": mode}
        if mode == 4:
            payload["param1"] = _first_or_full(filter_data.get("durationSwitchOn"))
            payload["param2"] = _first_or_full(filter_data.get("duration"))
            duration_vs = filter_data.get("durationVs")
            if duration_vs is not None:
                payload["param3"] = _first_or_full(duration_vs)

        await self.async_publish(f"/YnBlue/{device_id}/{section}/mode", payload)

    async def async_set_heater_mode(self, device_id: str, section: str, mode: int) -> None:
        """Update the heater mode."""

        heater = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        payload: dict[str, Any] = {"mode": mode}
        if mode == 1:
            payload["param1"] = heater.get("target", 25)
            payload["param2"] = heater.get("meteoTempOffset", 0)
        else:
            payload["param1"] = 0
            payload["param2"] = 0
        await self.async_publish(f"/YnBlue/{device_id}/{section}/mode", payload)

    async def async_set_heater_target(self, device_id: str, section: str, target: float) -> None:
        """Update the heater target temperature."""

        heater = get_nested_value(self.coordinator.get_device(device_id), section, default={}) or {}
        mode = int(heater.get("mode", 0))
        payload = {
            "mode": mode,
            "param1": target if mode == 1 else 0,
            "param2": heater.get("meteoTempOffset", 0) if mode == 1 else 0,
        }
        await self.async_publish(f"/YnBlue/{device_id}/{section}/mode", payload)

    async def async_set_chemical_mode(self, device_id: str, mode: int) -> None:
        """Update the chemical dosing mode."""

        chemical = get_nested_value(self.coordinator.get_device(device_id), "chemical", default={}) or {}
        await self.async_publish(
            f"/YnBlue/{device_id}/chemical/mode",
            {"mode": mode, "value": chemical.get("target", 650)},
        )

    async def async_set_chemical_target(self, device_id: str, value: float) -> None:
        """Update the chemical target."""

        chemical = get_nested_value(self.coordinator.get_device(device_id), "chemical", default={}) or {}
        await self.async_publish(
            f"/YnBlue/{device_id}/chemical/mode",
            {"mode": int(chemical.get("mode", 0)), "value": value},
        )

    async def async_set_ph_mode(self, device_id: str, mode: int) -> None:
        """Update the pH mode."""

        ph = get_nested_value(self.coordinator.get_device(device_id), "pH", default={}) or {}
        if mode == 2:
            await self.async_publish(f"/YnBlue/{device_id}/pH/mode", {"mode": 2, "value": 1})
            return

        await self.async_publish(
            f"/YnBlue/{device_id}/pH/mode",
            {
                "mode": str(mode),
                "value": f"{float(ph.get('target', 7.2)):.2f}",
            },
        )

    async def async_stop_ph_injection(self, device_id: str) -> None:
        """Stop the current manual pH injection."""

        await self.async_publish(f"/YnBlue/{device_id}/pH/mode", {"mode": 2, "value": 0})

    async def async_inject_ph(self, device_id: str) -> None:
        """Start a 1L manual pH injection."""

        await self.async_publish(f"/YnBlue/{device_id}/pH/mode", {"mode": 2, "value": 1})

    async def async_set_ph_target(self, device_id: str, value: float) -> None:
        """Update the pH target."""

        ph = get_nested_value(self.coordinator.get_device(device_id), "pH", default={}) or {}
        mode = 1 if int(ph.get("mode", 0)) == 1 else 0
        await self.async_publish(
            f"/YnBlue/{device_id}/pH/mode",
            {"mode": str(mode), "value": f"{value:.2f}"},
        )

    async def async_set_electrolyser_temp_protection(self, device_id: str, enabled: bool) -> None:
        """Toggle electrolyser low temperature protection."""

        await self.async_publish(
            f"/YnBlue/{device_id}/electrolyser/tempProtection",
            {"mode": bool(enabled)},
        )

    async def async_set_electrolyser_protection_mode(self, device_id: str, mode: int) -> None:
        """Set the electrolyser protection mode."""

        if mode not in ELECTROLYSER_PROTECTION_OPTIONS:
            raise ValueError(f"Unsupported electrolyser protection mode: {mode}")
        await self.async_publish(
            f"/YnBlue/{device_id}/electrolyser/protectionMode",
            {"mode": mode},
        )

    async def async_set_port_state(self, device_id: str, section: str, enabled: bool) -> None:
        """Toggle a simple on/off port-based output."""

        await self.async_publish(f"/YnBlue/{device_id}/{section}/state", {"state": enabled})

    async def async_cycle_rgb(self, device_id: str) -> None:
        """Cycle the RGB light program."""

        rgb_light = get_nested_value(self.coordinator.get_device(device_id), "RGBLight", default={}) or {}
        next_state = not bool(rgb_light.get("state"))
        await self.async_publish(f"/YnBlue/{device_id}/RGBLight/changeRGB", {"state": next_state})

    async def async_reset_consumption(self, device_id: str, section: str) -> None:
        """Reset a consumption counter."""

        await self.async_publish(f"/YnBlue/{device_id}/{section}/consoReset", {"state": True})

    async def async_publish(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        """Publish a JSON message to YnBlue over a short-lived MQTT session."""

        token = await self.api.async_reauthenticate()
        await self.hass.async_add_executor_job(
            _publish_ephemeral_message,
            topic,
            json.dumps(payload),
            token,
            retain,
        )

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """Handle MQTT connect callbacks."""

        if reason_code.is_failure:
            _LOGGER.error("YnBlue MQTT connect failed: %s", reason_code)
            self.hass.loop.call_soon_threadsafe(self._mqtt_connected.clear)
            return

        _LOGGER.info("YnBlue MQTT connected for entry %s", self.config_entry.entry_id)
        for topic in _subscription_topics(self.coordinator.data.keys()):
            client.subscribe(topic)

        self.hass.loop.call_soon_threadsafe(self._mqtt_connected.set)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        """Handle MQTT disconnect callbacks."""

        _LOGGER.warning("YnBlue MQTT disconnected: %s", reason_code)
        self.hass.loop.call_soon_threadsafe(self._mqtt_connected.clear)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming MQTT messages."""

        try:
            payload = msg.payload.decode("utf-8")
        except UnicodeDecodeError:
            _LOGGER.debug("Discarding non-UTF8 YnBlue MQTT payload for %s", msg.topic)
            return
        self.hass.add_job(self.async_process_message, msg.topic, payload)

    async def async_process_message(self, topic: str, payload: str) -> None:
        """Parse and apply a state update."""

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
            return

        if topic.endswith("/notification_ack"):
            return

        if "/data/json/" not in topic:
            return

        section_path = topic.split("/data/json/", maxsplit=1)[1]
        updates: dict[str, Any]
        if section_path == "all" or section_path == "measured":
            if not isinstance(body, dict):
                return
            updates = dict(body)
        else:
            if not isinstance(body, dict):
                return
            updates = set_nested_value(section_path.split("/"), body)

        updates["isConnected"] = True
        existing = self.coordinator.get_device(device_id) or {}
        self.coordinator.async_update_device(device_id, deep_merge_dict(existing, updates))

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

    async def _async_prime_snapshots(self) -> None:
        """Populate coordinator state with fresh snapshots during startup."""

        for device_id in self.coordinator.data:
            await self.async_request_snapshot(device_id)


def _connect_client(client: mqtt.Client) -> None:
    """Connect and start the Paho client loop."""

    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()


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
        client_id=f"ha_snapshot_{device_id[:8]}",
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

    client = mqtt.Client(
        client_id="ha_command_session",
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


def _subscription_topics(device_ids: Any) -> list[str]:
    """Build the MQTT subscription list for all known devices."""

    topics: list[str] = []
    suffixes = [
        "data/json/all",
        "data/json/system",
        "data/json/temperature",
        "data/json/localTime",
        "data/json/filter",
        "data/json/filter2",
        "data/json/electrolyser",
        "data/json/ozon",
        "data/json/light",
        "data/json/light2",
        "data/json/RGBLight",
        "data/json/switch",
        "data/json/switch2",
        "data/json/robot",
        "data/json/swimJet",
        "data/json/heater",
        "data/json/solarHeater",
        "data/json/chemical",
        "data/json/chemical/calibration",
        "data/json/chemical/injection",
        "data/json/chemical/injectionExtra",
        "data/json/chemical/injectionExtra2",
        "data/json/ORP",
        "data/json/ampero",
        "data/json/waterLevel",
        "data/json/waterLevel2",
        "data/json/pH",
        "data/json/pH/calibration",
        "data/json/pH/injection",
        "data/json/meteo",
        "data/json/measured",
        "data/json/lora",
        "data/json/fountain",
        "connected_ack",
        "notification_ack",
    ]
    for device_id in device_ids:
        for suffix in suffixes:
            topics.append(f"/YnBlue/{device_id}/{suffix}")
    return topics


def _first_or_full(value: Any) -> Any:
    """Return the first item for single-schedule lists, otherwise the original value."""

    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value

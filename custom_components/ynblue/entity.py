"""Shared entity helpers for YnBlue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER
from .coordinator import YnBlueCoordinator
from .helpers import get_nested_value
from .models import YnBlueRuntimeData

ExistsFn = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True, kw_only=True)
class YnBlueDescriptionMixin:
    """Shared entity description callbacks."""

    exists_fn: ExistsFn = lambda _device: True


class YnBlueEntity(CoordinatorEntity[YnBlueCoordinator], RestoreEntity):
    """Base entity for YnBlue."""

    _attr_has_entity_name = True

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        key: str,
        exists_fn: ExistsFn | None = None,
    ) -> None:
        """Initialize the base entity."""

        super().__init__(runtime_data.coordinator)
        self.runtime_data = runtime_data
        self.device_id = device_id
        self._exists_fn = exists_fn or (lambda _device: True)
        self._attr_unique_id = f"{device_id}_{key}"
        self._restored_state: str | None = None
        self._restored_attributes: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the previous entity state if Home Assistant has one."""

        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            recorder_state = await _async_get_last_good_recorder_state(self.hass, self.entity_id)
            if recorder_state is not None:
                last_state = recorder_state
        if last_state is None:
            return

        self._restored_state = last_state.state
        self._restored_attributes = dict(last_state.attributes)

    @property
    def device_data(self) -> dict[str, Any] | None:
        """Return the current device payload."""

        return self.runtime_data.coordinator.get_device(self.device_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""

        device = self.device_data
        if device is None:
            return self.has_restored_state
        return self._exists_fn(device) or self.has_restored_state

    @property
    def has_current_data(self) -> bool:
        """Return whether the current device payload satisfies the entity shape."""

        device = self.device_data
        return device is not None and self._exists_fn(device)

    @property
    def has_restored_state(self) -> bool:
        """Return whether a useful state was restored from the previous Home Assistant run."""

        return self.restored_state_value is not None

    @property
    def restored_state_value(self) -> str | None:
        """Return the restored state if it represents useful data."""

        if self._restored_state in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return self._restored_state

    @property
    def restored_attributes(self) -> dict[str, Any] | None:
        """Return restored attributes from the previous Home Assistant run."""

        if self._restored_attributes is None:
            return None
        return dict(self._restored_attributes)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return the Home Assistant device info."""

        device = self.device_data or {}
        system = device.get("system", {})
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": system.get("name") or device.get("name") or self.device_id,
            "manufacturer": MANUFACTURER,
            "model": f"YnBlue HW {device.get('hardwareVersion', 'unknown')}",
            "sw_version": ".".join(
                part
                for part in (
                    str(device.get("softwareVersion", "")),
                    str(device.get("softwareRevision", "")),
                )
                if part
            )
            or None,
            "serial_number": str(device.get("serialNumber")) if device.get("serialNumber") is not None else None,
        }

    def get_value(self, *path: str, default: Any = None) -> Any:
        """Convenience wrapper for nested value access."""

        return get_nested_value(self.device_data, *path, default=default)

    def get_restored_number(self) -> float | None:
        """Return the restored state parsed as a number."""

        restored = self.restored_state_value
        if restored is None:
            return None
        try:
            return float(restored)
        except ValueError:
            return None

    def get_restored_bool(self) -> bool | None:
        """Return the restored state parsed as a boolean."""

        restored = self.restored_state_value
        if restored is None:
            return None
        if restored == STATE_ON:
            return True
        if restored == STATE_OFF:
            return False
        return None

    def get_restored_datetime(self):
        """Return the restored state parsed as a datetime."""

        restored = self.restored_state_value
        if restored is None:
            return None
        return dt_util.parse_datetime(restored)


def _get_last_good_recorder_state(hass: HomeAssistant, entity_id: str) -> State | None:
    """Return the latest recorder state that is not unavailable or unknown."""

    try:
        from homeassistant.components.recorder import history
    except ImportError:
        return None

    try:
        states = history.get_last_state_changes(hass, 10, entity_id).get(entity_id.lower(), [])
    except Exception:
        return None

    for state in reversed(states):
        if state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return state
    return None


async def _async_get_last_good_recorder_state(hass: HomeAssistant, entity_id: str) -> State | None:
    """Fetch the last good recorder state on the recorder executor when available."""

    try:
        from homeassistant.components.recorder import get_instance
    except ImportError:
        return await hass.async_add_executor_job(_get_last_good_recorder_state, hass, entity_id)

    return await get_instance(hass).async_add_executor_job(_get_last_good_recorder_state, hass, entity_id)

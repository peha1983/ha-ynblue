"""Shared entity helpers for YnBlue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import YnBlueCoordinator
from .helpers import get_nested_value
from .models import YnBlueRuntimeData

ExistsFn = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True, kw_only=True)
class YnBlueDescriptionMixin:
    """Shared entity description callbacks."""

    exists_fn: ExistsFn = lambda _device: True


class YnBlueEntity(CoordinatorEntity[YnBlueCoordinator]):
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

    @property
    def device_data(self) -> dict[str, Any] | None:
        """Return the current device payload."""

        return self.runtime_data.coordinator.get_device(self.device_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""

        device = self.device_data
        return self.runtime_data.hub.available and device is not None and self._exists_fn(device)

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

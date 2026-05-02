"""Coordinator for YnBlue device state."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import YnBlueApiClient
from .const import DOMAIN
from .helpers import deep_merge_dict


class YnBlueCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Store YnBlue account and device state."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: YnBlueApiClient,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self.api = api
        super().__init__(hass, logger=logging.getLogger(__name__), name=DOMAIN)

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Refresh account metadata from YnBlue."""
        devices = await self.api.async_get_devices()

        existing = self.data if isinstance(self.data, dict) else {}
        merged_devices: dict[str, dict[str, Any]] = {}
        for device in devices:
            device_id = device["id"]
            previous = existing.get(device_id, {})
            merged_devices[device_id] = deep_merge_dict(previous, device)

        return merged_devices

    @callback
    def async_update_device(self, device_id: str, updates: dict[str, Any]) -> None:
        """Merge new state for a single device and notify listeners."""

        current = deepcopy(self.data) if isinstance(self.data, dict) else {}
        current_device = current.get(device_id, {})
        current[device_id] = deep_merge_dict(current_device, updates)
        self.async_set_updated_data(current)

    @callback
    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Return the stored device payload."""

        if not isinstance(self.data, dict):
            return None
        return self.data.get(device_id)

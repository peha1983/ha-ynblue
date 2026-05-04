"""Diagnostics support for YnBlue."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import REDACT_CONFIG
from .models import YnBlueRuntimeData

DEVICE_REDACTIONS = {
    "id",
    "latitude",
    "longitude",
    "registrationString",
    "serialNumber",
    "ssid",
}


async def async_get_config_entry_diagnostics(_hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    devices = {
        device_id: async_redact_data(device, DEVICE_REDACTIONS)
        for device_id, device in runtime.coordinator.data.items()
    }
    return {
        "entry": async_redact_data(dict(entry.data), REDACT_CONFIG),
        "devices": devices,
        "hub_available": runtime.hub.available,
    }

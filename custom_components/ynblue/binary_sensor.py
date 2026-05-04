"""Binary sensor platform for YnBlue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import YnBlueEntity
from .helpers import feature_enabled, should_create_entity
from .models import YnBlueRuntimeData

ValueFn = Callable[[dict[str, Any]], bool]
ExistsFn = Callable[[dict[str, Any]], bool]
AttrsFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, kw_only=True)
class YnBlueBinarySensorDescription(BinarySensorEntityDescription):
    """YnBlue binary sensor description."""

    value_fn: ValueFn
    exists_fn: ExistsFn = lambda _device: True
    attrs_fn: AttrsFn | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[YnBlueBinarySensorDescription, ...] = (
    YnBlueBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: bool(device.get("isConnected")),
    ),
    YnBlueBinarySensorDescription(
        key="filter_running",
        translation_key="filter_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        exists_fn=lambda device: "filter" in device,
        value_fn=lambda device: bool(device["filter"].get("state")),
        attrs_fn=lambda device: {"mode": device["filter"].get("mode")},
    ),
    YnBlueBinarySensorDescription(
        key="heater_running",
        translation_key="heater_running",
        device_class=BinarySensorDeviceClass.HEAT,
        exists_fn=lambda device: "heater" in device,
        value_fn=lambda device: bool(device["heater"].get("state")),
        attrs_fn=lambda device: {"mode": device["heater"].get("mode")},
    ),
    YnBlueBinarySensorDescription(
        key="electrolyser_running",
        translation_key="electrolyser_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        exists_fn=lambda device: "electrolyser" in device,
        value_fn=lambda device: bool(device["electrolyser"].get("state")),
        attrs_fn=lambda device: {"mode": device["electrolyser"].get("mode")},
    ),
    YnBlueBinarySensorDescription(
        key="ph_sensor_problem",
        translation_key="ph_sensor_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=lambda device: "pH" in device,
        value_fn=lambda device: not bool(device["pH"].get("sensorStatus")),
    ),
    YnBlueBinarySensorDescription(
        key="chemical_sensor_problem",
        translation_key="chemical_sensor_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        exists_fn=lambda device: "chemical" in device and device["chemical"].get("sensorType", 0) != 0,
        value_fn=lambda device: not bool(device["chemical"].get("sensorStatus")),
    ),
    YnBlueBinarySensorDescription(
        key="meteo_available",
        translation_key="meteo_available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        exists_fn=lambda device: feature_enabled(device, "meteo") and "meteo" in device,
        value_fn=lambda device: bool(device["meteo"].get("status")),
    ),
    YnBlueBinarySensorDescription(
        key="force_measurement_active",
        translation_key="force_measurement_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        exists_fn=lambda device: "system" in device and "forceMeasurement" in device["system"],
        value_fn=lambda device: bool(device["system"].get("forceMeasurement")),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue binary sensors."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueBinarySensor] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in BINARY_SENSOR_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueBinarySensor(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueBinarySensor(YnBlueEntity, BinarySensorEntity):
    """Representation of a YnBlue binary sensor."""

    entity_description: YnBlueBinarySensorDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueBinarySensorDescription,
    ) -> None:
        """Initialize the entity."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def is_on(self) -> bool | None:
        """Return the current state."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.value_fn(self.device_data)
        return self.get_restored_bool()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""

        if self.has_current_data and self.device_data is not None and self.entity_description.attrs_fn is not None:
            return self.entity_description.attrs_fn(self.device_data)
        return self.restored_attributes

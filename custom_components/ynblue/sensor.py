"""Sensor platform for YnBlue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import YnBlueEntity
from .models import YnBlueRuntimeData

ValueFn = Callable[[dict[str, Any]], Any]
ExistsFn = Callable[[dict[str, Any]], bool]
AttrsFn = Callable[[dict[str, Any]], dict[str, Any]]
UnitFn = Callable[[dict[str, Any]], str | None]


@dataclass(frozen=True, kw_only=True)
class YnBlueSensorEntityDescription(SensorEntityDescription):
    """YnBlue sensor description."""

    value_fn: ValueFn
    exists_fn: ExistsFn = lambda _device: True
    attrs_fn: AttrsFn | None = None
    unit_fn: UnitFn | None = None


SENSOR_DESCRIPTIONS: tuple[YnBlueSensorEntityDescription, ...] = (
    YnBlueSensorEntityDescription(
        key="temperature",
        translation_key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["temperature"]["measured"],
        exists_fn=lambda device: "temperature" in device,
        attrs_fn=lambda device: {
            "sensor_status": device["temperature"].get("status"),
            "measured_epoch": device["temperature"].get("measuredEpoch"),
            "offset": device["temperature"].get("offset"),
        },
    ),
    YnBlueSensorEntityDescription(
        key="ph_measured",
        translation_key="ph_measured",
        native_unit_of_measurement="pH",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["pH"]["measured"],
        exists_fn=lambda device: "pH" in device,
        attrs_fn=lambda device: {
            "target": device["pH"].get("target"),
            "sensor_status": device["pH"].get("sensorStatus"),
            "status": device["pH"].get("status"),
            "liquid_level_alert": device["pH"].get("liquidLevelAlert"),
        },
    ),
    YnBlueSensorEntityDescription(
        key="chemical_measured",
        translation_key="chemical_measured",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["chemical"]["measured"],
        exists_fn=lambda device: "chemical" in device and device["chemical"].get("sensorType", 0) != 0,
        unit_fn=lambda device: "mV" if device["chemical"].get("sensorType") == 1 else "ppm",
        attrs_fn=lambda device: {
            "target": device["chemical"].get("target"),
            "sensor_status": device["chemical"].get("sensorStatus"),
            "status": device["chemical"].get("status"),
            "estimated": device["chemical"].get("estimated"),
            "global_mode": device["chemical"].get("globalMode"),
        },
    ),
    YnBlueSensorEntityDescription(
        key="chemical_estimated",
        translation_key="chemical_estimated",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["chemical"]["estimated"],
        exists_fn=lambda device: "chemical" in device and device["chemical"].get("sensorType", 0) != 0,
        unit_fn=lambda device: "mV" if device["chemical"].get("sensorType") == 1 else "ppm",
    ),
    YnBlueSensorEntityDescription(
        key="ph_tank_level",
        translation_key="ph_tank_level",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["pH"]["liquidLevel"],
        exists_fn=lambda device: "pH" in device,
        attrs_fn=lambda device: {
            "max_level": device["pH"].get("liquidLevelMax"),
            "alert_level": device["pH"].get("liquidLevelAlert"),
            "total_consumption": device["pH"].get("liquidConso"),
            "last_day_consumption": device["pH"].get("liquidLastDay"),
        },
    ),
    YnBlueSensorEntityDescription(
        key="chemical_tank_level",
        translation_key="chemical_tank_level",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["chemical"]["liquidLevel"],
        exists_fn=lambda device: "chemical" in device,
        attrs_fn=lambda device: {
            "max_level": device["chemical"].get("liquidLevelMax"),
            "alert_level": device["chemical"].get("liquidLevelAlert"),
            "total_consumption": device["chemical"].get("liquidConso"),
            "last_day_consumption": device["chemical"].get("liquidLastDay"),
        },
    ),
    YnBlueSensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["wifi"]["rssi"],
        exists_fn=lambda device: "wifi" in device,
        attrs_fn=lambda device: {"ssid": device["wifi"].get("ssid")},
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue sensors from a config entry."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    entities: list[YnBlueSensor] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in SENSOR_DESCRIPTIONS:
            if description.exists_fn(device):
                entities.append(YnBlueSensor(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueSensor(YnBlueEntity, SensorEntity):
    """Representation of a YnBlue sensor."""

    entity_description: YnBlueSensorEntityDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit of measurement."""

        if self.entity_description.unit_fn is not None and self.device_data is not None:
            return self.entity_description.unit_fn(self.device_data)
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        """Return the native value."""

        if self.device_data is None:
            return None
        return self.entity_description.value_fn(self.device_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity-specific attributes."""

        if self.device_data is None or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.device_data)

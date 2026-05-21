"""Sensor platform for YnBlue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SNAPSHOT_STALE_INTERVAL
from .entity import YnBlueEntity
from .helpers import should_create_entity
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
    requires_fresh_snapshot: bool = False


SENSOR_DESCRIPTIONS: tuple[YnBlueSensorEntityDescription, ...] = (
    YnBlueSensorEntityDescription(
        key="temperature",
        translation_key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["temperature"]["measured"],
        exists_fn=lambda device: "temperature" in device,
        requires_fresh_snapshot=True,
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
        requires_fresh_snapshot=True,
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
        requires_fresh_snapshot=True,
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
        requires_fresh_snapshot=True,
        unit_fn=lambda device: "mV" if device["chemical"].get("sensorType") == 1 else "ppm",
    ),
    YnBlueSensorEntityDescription(
        key="ph_tank_level",
        translation_key="ph_tank_level",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device["pH"]["liquidLevel"],
        exists_fn=lambda device: "pH" in device,
        requires_fresh_snapshot=True,
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
        requires_fresh_snapshot=True,
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
        requires_fresh_snapshot=True,
        attrs_fn=lambda device: {"ssid": device["wifi"].get("ssid")},
    ),
    YnBlueSensorEntityDescription(
        key="last_cloud_contact",
        translation_key="last_cloud_contact",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: _datetime_from_milliseconds(device["date_mqtt_connection"]),
        exists_fn=lambda device: "date_mqtt_connection" in device and device["date_mqtt_connection"] is not None,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue sensors from a config entry."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueSensor] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in SENSOR_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueSensor(runtime, device_id, description))
    async_add_entities(entities)
    async_add_entities([YnBlueLiveDataAgeSensor(runtime, device_id) for device_id in runtime.coordinator.data])


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
    def requires_fresh_snapshot(self) -> bool:
        """Return whether the sensor depends on fresh live snapshot data."""

        return self.entity_description.requires_fresh_snapshot

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit of measurement."""

        if self.entity_description.unit_fn is not None and self.has_current_data and self.device_data is not None:
            return self.entity_description.unit_fn(self.device_data)
        restored_unit = (self.restored_attributes or {}).get("unit_of_measurement")
        if isinstance(restored_unit, str):
            return restored_unit
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        """Return the native value."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.value_fn(self.device_data)

        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            restored_datetime = self.get_restored_datetime()
            if restored_datetime is not None:
                return restored_datetime

        restored_number = self.get_restored_number()
        if restored_number is not None:
            return restored_number
        return self.restored_state_value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity-specific attributes."""

        if self.has_current_data and self.device_data is not None and self.entity_description.attrs_fn is not None:
            return self.entity_description.attrs_fn(self.device_data)
        return self.restored_attributes


def _datetime_from_milliseconds(value: Any) -> datetime:
    """Return a timezone-aware datetime from a millisecond Unix timestamp."""

    return datetime.fromtimestamp(float(value) / 1000, tz=UTC)


class YnBlueLiveDataAgeSensor(YnBlueEntity, SensorEntity):
    """Diagnostic sensor for live data freshness."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "live_data_age_minutes"

    def __init__(self, runtime_data: YnBlueRuntimeData, device_id: str) -> None:
        """Initialize the diagnostic sensor."""

        super().__init__(runtime_data, device_id, "live_data_age_minutes")

    @property
    def native_value(self) -> float | None:
        """Return the age of the latest successful live snapshot in minutes."""

        age_fn = getattr(self.runtime_data.hub, "get_snapshot_age_minutes", None)
        if callable(age_fn):
            age = age_fn(self.device_id)
            if age is not None:
                return round(age, 1)
        return self.get_restored_number()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return freshness attributes for diagnostics."""

        fresh_fn = getattr(self.runtime_data.hub, "device_data_is_fresh", None)
        is_fresh = bool(fresh_fn(self.device_id)) if callable(fresh_fn) else None
        return {
            "fresh": is_fresh,
            "stale_after_minutes": round(SNAPSHOT_STALE_INTERVAL.total_seconds() / 60),
        }

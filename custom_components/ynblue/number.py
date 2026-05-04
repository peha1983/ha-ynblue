"""Number platform for YnBlue."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import YnBlueEntity
from .helpers import should_create_entity
from .models import YnBlueRuntimeData

ValueFn = Callable[[dict[str, Any]], float]
ExistsFn = Callable[[dict[str, Any]], bool]
SetFn = Callable[[YnBlueRuntimeData, str, float], Awaitable[None]]
MinFn = Callable[[dict[str, Any]], float]
MaxFn = Callable[[dict[str, Any]], float]
AttrsFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, kw_only=True)
class YnBlueNumberDescription(NumberEntityDescription):
    """YnBlue number description."""

    value_fn: ValueFn
    set_fn: SetFn
    exists_fn: ExistsFn = lambda _device: True
    min_fn: MinFn | None = None
    max_fn: MaxFn | None = None
    attrs_fn: AttrsFn | None = None


NUMBER_DESCRIPTIONS: tuple[YnBlueNumberDescription, ...] = (
    YnBlueNumberDescription(
        key="pool_volume",
        translation_key="pool_volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        native_step=1,
        mode=NumberMode.BOX,
        native_min_value=1,
        native_max_value=500,
        exists_fn=lambda device: "system" in device and "poolVolume" in device["system"],
        value_fn=lambda device: float(device["system"]["poolVolume"]),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_pool_volume(device_id, value),
    ),
    YnBlueNumberDescription(
        key="ph_target",
        translation_key="ph_target",
        native_unit_of_measurement="pH",
        native_step=0.1,
        mode=NumberMode.SLIDER,
        native_min_value=3,
        native_max_value=10,
        exists_fn=lambda device: "pH" in device and "target" in device["pH"],
        value_fn=lambda device: float(device["pH"]["target"]),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_ph_target(device_id, value),
        attrs_fn=lambda device: {"current_mode": device["pH"].get("mode")},
    ),
    YnBlueNumberDescription(
        key="chemical_target",
        translation_key="chemical_target",
        native_step=1,
        mode=NumberMode.BOX,
        exists_fn=lambda device: "chemical" in device and "target" in device["chemical"],
        value_fn=lambda device: float(device["chemical"]["target"]),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_chemical_target(device_id, value),
        min_fn=lambda _device: 0,
        max_fn=lambda device: 1000 if device["chemical"].get("sensorType") == 1 else 5,
        attrs_fn=lambda device: {"sensor_type": device["chemical"].get("sensorType")},
    ),
    YnBlueNumberDescription(
        key="heater_target",
        translation_key="heater_target",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        native_min_value=0,
        native_max_value=40,
        exists_fn=lambda device: "heater" in device and "target" in device["heater"],
        value_fn=lambda device: float(device["heater"]["target"]),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_heater_target(device_id, "heater", value),
        attrs_fn=lambda device: {"current_mode": device["heater"].get("mode")},
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue numbers."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueNumber] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in NUMBER_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueNumber(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueNumber(YnBlueEntity, NumberEntity):
    """Representation of a YnBlue number entity."""

    entity_description: YnBlueNumberDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueNumberDescription,
    ) -> None:
        """Initialize the entity."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.value_fn(self.device_data)
        return self.get_restored_number()

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""

        if self.entity_description.min_fn is not None and self.has_current_data and self.device_data is not None:
            return self.entity_description.min_fn(self.device_data)
        return float(self.entity_description.native_min_value or 0)

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""

        if self.entity_description.max_fn is not None and self.has_current_data and self.device_data is not None:
            return self.entity_description.max_fn(self.device_data)
        if self.entity_description.key == "chemical_target":
            sensor_type = (self.restored_attributes or {}).get("sensor_type")
            return 1000.0 if sensor_type == 1 else 5.0
        return float(self.entity_description.native_max_value or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""

        if self.has_current_data and self.device_data is not None and self.entity_description.attrs_fn is not None:
            return self.entity_description.attrs_fn(self.device_data)
        return self.restored_attributes

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value."""

        await self.entity_description.set_fn(self.runtime_data, self.device_id, value)

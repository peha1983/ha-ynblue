"""Select platform for YnBlue."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CHEMICAL_MODE_OPTIONS,
    ELECTROLYSER_PROTECTION_OPTIONS,
    FILTER_MODE_OPTIONS,
    HEATER_MODE_OPTIONS,
    PH_MODE_OPTIONS,
)
from .entity import YnBlueEntity
from .helpers import feature_enabled, is_port_enabled, should_create_entity
from .models import YnBlueRuntimeData

ExistsFn = Callable[[dict], bool]
ValueFn = Callable[[dict], int]
SetFn = Callable[[YnBlueRuntimeData, str, int], Awaitable[None]]


def _feature_with_port(feature: str, section: str | None = None) -> ExistsFn:
    """Return an exists function for a port-based functionality."""

    section_name = section or feature
    return lambda device: feature_enabled(device, feature) and (
        section_name not in device or is_port_enabled(device, section_name)
    )


@dataclass(frozen=True, kw_only=True)
class YnBlueSelectDescription(SelectEntityDescription):
    """YnBlue select description."""

    exists_fn: ExistsFn
    value_fn: ValueFn
    set_fn: SetFn
    options_map: dict[int, str]


SELECT_DESCRIPTIONS: tuple[YnBlueSelectDescription, ...] = (
    YnBlueSelectDescription(
        key="filter_mode",
        translation_key="filter_mode",
        exists_fn=_feature_with_port("filter"),
        value_fn=lambda device: int(device.get("filter", {}).get("mode", 0)),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_filter_mode(device_id, "filter", value),
        options=list(FILTER_MODE_OPTIONS.values()),
        options_map=FILTER_MODE_OPTIONS,
    ),
    YnBlueSelectDescription(
        key="heater_mode",
        translation_key="heater_mode",
        exists_fn=_feature_with_port("heater"),
        value_fn=lambda device: int(device.get("heater", {}).get("mode", 0)),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_heater_mode(device_id, "heater", value),
        options=list(HEATER_MODE_OPTIONS.values()),
        options_map=HEATER_MODE_OPTIONS,
    ),
    YnBlueSelectDescription(
        key="chemical_mode",
        translation_key="chemical_mode",
        exists_fn=lambda device: "chemical" in device,
        value_fn=lambda device: int(device["chemical"].get("mode", 0)),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_chemical_mode(device_id, value),
        options=list(CHEMICAL_MODE_OPTIONS.values()),
        options_map=CHEMICAL_MODE_OPTIONS,
    ),
    YnBlueSelectDescription(
        key="ph_mode",
        translation_key="ph_mode",
        exists_fn=lambda device: "pH" in device,
        value_fn=lambda device: int(device["pH"].get("mode", 0)),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_ph_mode(device_id, value),
        options=list(PH_MODE_OPTIONS.values()),
        options_map=PH_MODE_OPTIONS,
    ),
    YnBlueSelectDescription(
        key="electrolyser_protection_mode",
        translation_key="electrolyser_protection_mode",
        exists_fn=lambda device: "electrolyser" in device and "protectionMode" in device["electrolyser"],
        value_fn=lambda device: int(device["electrolyser"].get("protectionMode", 0)),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_electrolyser_protection_mode(device_id, value),
        options=list(ELECTROLYSER_PROTECTION_OPTIONS.values()),
        options_map=ELECTROLYSER_PROTECTION_OPTIONS,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue selects."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueSelect] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in SELECT_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueSelect(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueSelect(YnBlueEntity, SelectEntity):
    """Representation of a YnBlue select entity."""

    entity_description: YnBlueSelectDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueSelectDescription,
    ) -> None:
        """Initialize the entity."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.options_map.get(self.entity_description.value_fn(self.device_data))

        restored = self.restored_state_value
        if restored in self.entity_description.options:
            return restored
        return None

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""

        inverse = {label: key for key, label in self.entity_description.options_map.items()}
        await self.entity_description.set_fn(self.runtime_data, self.device_id, inverse[option])

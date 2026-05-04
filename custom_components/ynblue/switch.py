"""Switch platform for YnBlue."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import YnBlueEntity
from .helpers import feature_enabled, is_port_enabled, should_create_entity
from .models import YnBlueRuntimeData

ExistsFn = Callable[[dict], bool]
ValueFn = Callable[[dict], bool]
SetFn = Callable[[YnBlueRuntimeData, str, bool], Awaitable[None]]


def _feature_with_port(feature: str, section: str | None = None) -> ExistsFn:
    """Return an exists function for a port-based functionality."""

    section_name = section or feature
    return lambda device: feature_enabled(device, feature) and (
        section_name not in device or is_port_enabled(device, section_name)
    )


@dataclass(frozen=True, kw_only=True)
class YnBlueSwitchDescription(SwitchEntityDescription):
    """YnBlue switch description."""

    exists_fn: ExistsFn
    value_fn: ValueFn
    set_fn: SetFn


SWITCH_DESCRIPTIONS: tuple[YnBlueSwitchDescription, ...] = (
    YnBlueSwitchDescription(
        key="robot",
        translation_key="robot",
        exists_fn=_feature_with_port("robot"),
        value_fn=lambda device: bool(device.get("robot", {}).get("state")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "robot", value),
    ),
    YnBlueSwitchDescription(
        key="swim_jet",
        translation_key="swim_jet",
        exists_fn=_feature_with_port("swimJet"),
        value_fn=lambda device: bool(device.get("swimJet", {}).get("state")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "swimJet", value),
    ),
    YnBlueSwitchDescription(
        key="fountain",
        translation_key="fountain",
        exists_fn=_feature_with_port("fountain"),
        value_fn=lambda device: bool(device.get("fountain", {}).get("state")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "fountain", value),
    ),
    YnBlueSwitchDescription(
        key="aux_switch",
        translation_key="aux_switch",
        exists_fn=_feature_with_port("switch"),
        value_fn=lambda device: bool(device.get("switch", {}).get("state")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "switch", value),
    ),
    YnBlueSwitchDescription(
        key="aux_switch_2",
        translation_key="aux_switch_2",
        exists_fn=_feature_with_port("switch2"),
        value_fn=lambda device: bool(device.get("switch2", {}).get("state")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "switch2", value),
    ),
    YnBlueSwitchDescription(
        key="electrolyser_temp_protection",
        translation_key="electrolyser_temp_protection",
        exists_fn=lambda device: "electrolyser" in device and "tempProtection" in device["electrolyser"],
        value_fn=lambda device: bool(device["electrolyser"].get("tempProtection")),
        set_fn=lambda runtime, device_id, value: runtime.hub.async_set_electrolyser_temp_protection(device_id, value),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue switches."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueSwitch] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in SWITCH_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueSwitch(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueSwitch(YnBlueEntity, SwitchEntity):
    """Representation of a YnBlue switch entity."""

    entity_description: YnBlueSwitchDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueSwitchDescription,
    ) -> None:
        """Initialize the entity."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.value_fn(self.device_data)
        return self.get_restored_bool()

    async def async_turn_on(self, **_kwargs) -> None:
        """Turn the switch on."""

        await self.entity_description.set_fn(self.runtime_data, self.device_id, True)

    async def async_turn_off(self, **_kwargs) -> None:
        """Turn the switch off."""

        await self.entity_description.set_fn(self.runtime_data, self.device_id, False)

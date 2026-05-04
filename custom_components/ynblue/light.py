"""Light platform for YnBlue."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.light import ColorMode, LightEntity, LightEntityDescription
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
class YnBlueLightDescription(LightEntityDescription):
    """YnBlue light description."""

    exists_fn: ExistsFn
    value_fn: ValueFn
    set_fn: SetFn


LIGHT_DESCRIPTIONS: tuple[tuple[str, YnBlueLightDescription], ...] = (
    (
        "light",
        YnBlueLightDescription(
            key="light",
            translation_key="light",
            exists_fn=_feature_with_port("light"),
            value_fn=lambda device: bool(device.get("light", {}).get("state")),
            set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "light", value),
        ),
    ),
    (
        "light2",
        YnBlueLightDescription(
            key="light2",
            translation_key="light2",
            exists_fn=_feature_with_port("light2"),
            value_fn=lambda device: bool(device.get("light2", {}).get("state")),
            set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "light2", value),
        ),
    ),
    (
        "RGBLight",
        YnBlueLightDescription(
            key="rgb_light",
            translation_key="rgb_light",
            exists_fn=_feature_with_port("RGBLight"),
            value_fn=lambda device: bool(device.get("RGBLight", {}).get("state")),
            set_fn=lambda runtime, device_id, value: runtime.hub.async_set_port_state(device_id, "RGBLight", value),
        ),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue lights."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueLight] = []
    for device_id, device in runtime.coordinator.data.items():
        for section, description in LIGHT_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueLight(runtime, device_id, section, description))
    async_add_entities(entities)


class YnBlueLight(YnBlueEntity, LightEntity):
    """Representation of a YnBlue light."""

    entity_description: YnBlueLightDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        section: str,
        description: YnBlueLightDescription,
    ) -> None:
        """Initialize the light."""

        self.section = section
        self.entity_description = description
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    @property
    def is_on(self) -> bool | None:
        """Return whether the light is on."""

        if self.has_current_data and self.device_data is not None:
            return self.entity_description.value_fn(self.device_data)
        return self.get_restored_bool()

    async def async_turn_on(self, **_kwargs) -> None:
        """Turn the light on."""

        await self.entity_description.set_fn(self.runtime_data, self.device_id, True)

    async def async_turn_off(self, **_kwargs) -> None:
        """Turn the light off."""

        await self.entity_description.set_fn(self.runtime_data, self.device_id, False)

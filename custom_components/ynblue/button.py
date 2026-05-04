"""Button platform for YnBlue."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import YnBlueEntity
from .helpers import feature_enabled, is_port_enabled, should_create_entity
from .models import YnBlueRuntimeData

ExistsFn = Callable[[dict], bool]
PressFn = Callable[[YnBlueRuntimeData, str], Awaitable[None]]


def _feature_with_port(feature: str, section: str | None = None) -> ExistsFn:
    """Return an exists function for a port-based functionality."""

    section_name = section or feature
    return lambda device: feature_enabled(device, feature) and (
        section_name not in device or is_port_enabled(device, section_name)
    )


@dataclass(frozen=True, kw_only=True)
class YnBlueButtonDescription(ButtonEntityDescription):
    """YnBlue button description."""

    exists_fn: ExistsFn
    press_fn: PressFn


BUTTON_DESCRIPTIONS: tuple[YnBlueButtonDescription, ...] = (
    YnBlueButtonDescription(
        key="request_snapshot",
        translation_key="request_snapshot",
        exists_fn=lambda _device: True,
        press_fn=lambda runtime, device_id: runtime.hub.async_request_snapshot(device_id),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YnBlueButtonDescription(
        key="force_measurement",
        translation_key="force_measurement",
        exists_fn=lambda device: "system" in device and "forceMeasurement" in device["system"],
        press_fn=lambda runtime, device_id: runtime.hub.async_force_measurement(device_id),
    ),
    YnBlueButtonDescription(
        key="restart_controller",
        translation_key="restart_controller",
        exists_fn=lambda _device: True,
        press_fn=lambda runtime, device_id: runtime.hub.async_restart_device(device_id),
        entity_category=EntityCategory.CONFIG,
    ),
    YnBlueButtonDescription(
        key="cycle_rgb_program",
        translation_key="cycle_rgb_program",
        exists_fn=_feature_with_port("RGBLight"),
        press_fn=lambda runtime, device_id: runtime.hub.async_cycle_rgb(device_id),
    ),
    YnBlueButtonDescription(
        key="inject_ph",
        translation_key="inject_ph",
        exists_fn=lambda device: "pH" in device,
        press_fn=lambda runtime, device_id: runtime.hub.async_inject_ph(device_id),
    ),
    YnBlueButtonDescription(
        key="stop_ph_injection",
        translation_key="stop_ph_injection",
        exists_fn=lambda device: "pH" in device,
        press_fn=lambda runtime, device_id: runtime.hub.async_stop_ph_injection(device_id),
    ),
    YnBlueButtonDescription(
        key="reset_filter_consumption",
        translation_key="reset_filter_consumption",
        exists_fn=lambda device: "filter" in device,
        press_fn=lambda runtime, device_id: runtime.hub.async_reset_consumption(device_id, "filter"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YnBlueButtonDescription(
        key="reset_ph_consumption",
        translation_key="reset_ph_consumption",
        exists_fn=lambda device: "pH" in device,
        press_fn=lambda runtime, device_id: runtime.hub.async_reset_consumption(device_id, "pH"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    YnBlueButtonDescription(
        key="reset_chemical_consumption",
        translation_key="reset_chemical_consumption",
        exists_fn=lambda device: "chemical" in device,
        press_fn=lambda runtime, device_id: runtime.hub.async_reset_consumption(device_id, "chemical"),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YnBlue buttons."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    registry = er.async_get(_hass)
    registered_unique_ids = {
        registry_entry.unique_id for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    entities: list[YnBlueButton] = []
    for device_id, device in runtime.coordinator.data.items():
        for description in BUTTON_DESCRIPTIONS:
            if should_create_entity(
                device,
                device_id=device_id,
                key=description.key,
                exists_fn=description.exists_fn,
                registered_unique_ids=registered_unique_ids,
            ):
                entities.append(YnBlueButton(runtime, device_id, description))
    async_add_entities(entities)


class YnBlueButton(YnBlueEntity, ButtonEntity):
    """Representation of a YnBlue button."""

    entity_description: YnBlueButtonDescription

    def __init__(
        self,
        runtime_data: YnBlueRuntimeData,
        device_id: str,
        description: YnBlueButtonDescription,
    ) -> None:
        """Initialize the button."""

        self.entity_description = description
        super().__init__(runtime_data, device_id, description.key, description.exists_fn)

    async def async_press(self) -> None:
        """Press the button."""

        await self.entity_description.press_fn(self.runtime_data, self.device_id)

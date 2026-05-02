"""The YnBlue integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_LANGUAGE, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import YnBlueApiClient
from .const import DEFAULT_LANGUAGE, DOMAIN, PLATFORMS
from .coordinator import YnBlueCoordinator
from .exceptions import YnBlueApiError, YnBlueAuthError, YnBlueMqttError
from .helpers import build_entity_id
from .hub import YnBlueHub
from .models import YnBlueRuntimeData

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(_hass: HomeAssistant, _config: dict) -> bool:
    """Set up the YnBlue component."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up YnBlue from a config entry."""

    api = YnBlueApiClient(
        async_get_clientsession(hass),
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        language=entry.data.get(CONF_LANGUAGE, hass.config.language or DEFAULT_LANGUAGE),
    )
    coordinator = YnBlueCoordinator(hass, entry, api)

    try:
        await coordinator.async_config_entry_first_refresh()
        hub = YnBlueHub(hass, entry, coordinator, api)
        await hub.async_start()
    except YnBlueAuthError as err:
        raise ConfigEntryAuthFailed from err
    except (YnBlueApiError, YnBlueMqttError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = YnBlueRuntimeData(api=api, coordinator=coordinator, hub=hub)
    await _async_prepare_entity_registry(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a YnBlue config entry."""

    runtime: YnBlueRuntimeData = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await runtime.hub.async_stop()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after updates."""

    await hass.config_entries.async_reload(entry.entry_id)


async def _async_prepare_entity_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Normalize existing YnBlue entity ids and enable the full entity set."""

    registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    for registry_entry in registry_entries:
        entity_domain = registry_entry.entity_id.split(".", maxsplit=1)[0]
        target_entity_id = build_entity_id(registry_entry.unique_id, entity_domain)
        update_kwargs: dict[str, object] = {}

        if registry_entry.disabled_by is not None:
            update_kwargs["disabled_by"] = None
        if target_entity_id is not None and registry_entry.entity_id != target_entity_id:
            update_kwargs["new_entity_id"] = target_entity_id

        if not update_kwargs:
            continue

        try:
            registry.async_update_entity(registry_entry.entity_id, **update_kwargs)
        except ValueError as err:
            _LOGGER.warning(
                "Could not update entity registry entry %s to %s: %s",
                registry_entry.entity_id,
                target_entity_id,
                err,
            )

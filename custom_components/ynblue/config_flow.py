"""Config flow for YnBlue."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_LANGUAGE, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import YnBlueApiClient
from .const import DEFAULT_LANGUAGE, DOMAIN
from .exceptions import YnBlueApiError, YnBlueAuthError

_LOGGER = logging.getLogger(__name__)


async def _validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input."""

    client = YnBlueApiClient(
        async_get_clientsession(hass),
        email=user_input[CONF_EMAIL],
        password=user_input[CONF_PASSWORD],
        language=user_input.get(CONF_LANGUAGE, hass.config.language or DEFAULT_LANGUAGE),
    )
    account = await client.async_validate_credentials()
    return {
        "title": f"{account.get('firstName', '').strip()} {account.get('name', '').strip()}".strip()
        or user_input[CONF_EMAIL],
        "unique_id": account.get("id") or user_input[CONF_EMAIL].strip().lower(),
        "email": user_input[CONF_EMAIL].strip().lower(),
    }


class YnBlueConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YnBlue."""

    VERSION = 1
    MINOR_VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_EMAIL] = user_input[CONF_EMAIL].strip().lower()
            user_input.setdefault(CONF_LANGUAGE, self.hass.config.language or DEFAULT_LANGUAGE)
            try:
                info = await _validate_input(self.hass, user_input)
            except YnBlueAuthError:
                errors["base"] = "invalid_auth"
            except YnBlueApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during YnBlue config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_EMAIL: info["email"],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start the reauthentication flow."""

        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm reauthentication."""

        assert self._reauth_entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            payload = {
                CONF_EMAIL: self._reauth_entry.data[CONF_EMAIL],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_LANGUAGE: self._reauth_entry.data.get(
                    CONF_LANGUAGE, self.hass.config.language or DEFAULT_LANGUAGE
                ),
            }
            try:
                await _validate_input(self.hass, payload)
            except YnBlueAuthError:
                errors["base"] = "invalid_auth"
            except YnBlueApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during YnBlue reauth flow")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"email": self._reauth_entry.data[CONF_EMAIL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: ConfigEntry) -> None:
        """YnBlue currently has no options flow."""

        return None

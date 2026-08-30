"""Tests for the YnBlue config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.ynblue.config_flow import YnBlueConfigFlow
from custom_components.ynblue.exceptions import YnBlueApiError, YnBlueAuthError


async def test_user_flow_creates_entry(hass):
    """Test the standard user flow."""

    flow = YnBlueConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    with patch(
        "custom_components.ynblue.config_flow._validate_input",
        AsyncMock(return_value={"title": "Patrick Huebler", "unique_id": "user-1", "email": "patrick@example.com"}),
    ):
        result = await flow.async_step_user({CONF_EMAIL: "patrick@example.com", CONF_PASSWORD: "secret"})

    assert result["type"] == "create_entry"
    assert result["title"] == "Patrick Huebler"
    assert result["data"][CONF_EMAIL] == "patrick@example.com"


async def test_user_flow_reports_invalid_credentials(hass):
    """Test authentication failures remain visible in the config flow."""

    flow = YnBlueConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    with patch(
        "custom_components.ynblue.config_flow._validate_input",
        AsyncMock(side_effect=YnBlueAuthError("invalid credentials")),
    ):
        result = await flow.async_step_user({CONF_EMAIL: "patrick@example.com", CONF_PASSWORD: "wrong"})

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_reports_cloud_timeout(hass):
    """Test REST timeouts remain visible as connection failures in the config flow."""

    flow = YnBlueConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    with patch(
        "custom_components.ynblue.config_flow._validate_input",
        AsyncMock(side_effect=YnBlueApiError("YnBlue request timed out for /user/login")),
    ):
        result = await flow.async_step_user({CONF_EMAIL: "patrick@example.com", CONF_PASSWORD: "secret"})

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_updates_password(hass, config_entry):
    """Test the reauthentication flow."""

    config_entry.add_to_hass(hass)
    flow = YnBlueConfigFlow()
    flow.hass = hass
    flow.context = {"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id}

    with (
        patch(
            "custom_components.ynblue.config_flow._validate_input",
            AsyncMock(return_value={"title": "Patrick"}),
        ),
        patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)) as async_reload,
    ):
        await flow.async_step_reauth(config_entry.data)
        result = await flow.async_step_reauth_confirm({CONF_PASSWORD: "new-secret"})

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    async_reload.assert_awaited_once_with(config_entry.entry_id)

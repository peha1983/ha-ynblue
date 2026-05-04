"""Exceptions for the YnBlue integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class YnBlueError(Exception):
    """Base error for YnBlue."""


class YnBlueAuthError(YnBlueError):
    """Raised when YnBlue authentication fails."""


class YnBlueApiError(YnBlueError):
    """Raised when the YnBlue API returns an unexpected response."""


class YnBlueMqttError(YnBlueError):
    """Raised when the YnBlue MQTT connection fails."""


class YnBlueCommandError(HomeAssistantError, YnBlueError):
    """Raised when a YnBlue command could not be completed safely."""


class YnBlueValidationError(HomeAssistantError, YnBlueError):
    """Raised when invalid YnBlue command input is supplied."""

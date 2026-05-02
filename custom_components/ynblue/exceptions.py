"""Exceptions for the YnBlue integration."""

from __future__ import annotations


class YnBlueError(Exception):
    """Base error for YnBlue."""


class YnBlueAuthError(YnBlueError):
    """Raised when YnBlue authentication fails."""


class YnBlueApiError(YnBlueError):
    """Raised when the YnBlue API returns an unexpected response."""


class YnBlueMqttError(YnBlueError):
    """Raised when the YnBlue MQTT connection fails."""

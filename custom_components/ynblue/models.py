"""Runtime models for the YnBlue integration."""

from __future__ import annotations

from dataclasses import dataclass

from .client import YnBlueApiClient
from .coordinator import YnBlueCoordinator
from .hub import YnBlueHub


@dataclass
class YnBlueRuntimeData:
    """Runtime objects stored on the config entry."""

    api: YnBlueApiClient
    coordinator: YnBlueCoordinator
    hub: YnBlueHub

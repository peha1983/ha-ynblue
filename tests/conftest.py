"""Shared test fixtures for the YnBlue integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from homeassistant.const import CONF_EMAIL, CONF_LANGUAGE, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.ynblue.const import DEFAULT_LANGUAGE, DOMAIN  # noqa: E402


@pytest.fixture(name="device_payload")
def fixture_device_payload() -> dict[str, Any]:
    """Return the sample YnBlue device payload."""

    path = Path(__file__).parent / "fixtures" / "device.json"
    return json.loads(path.read_text())


@pytest.fixture(name="config_entry")
def fixture_config_entry() -> MockConfigEntry:
    """Return a mocked config entry."""

    return MockConfigEntry(
        domain=DOMAIN,
        title="YnBlue",
        data={
            CONF_EMAIL: "patrick@example.com",
            CONF_PASSWORD: "secret",
            CONF_LANGUAGE: DEFAULT_LANGUAGE,
        },
        unique_id="test-user-id",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""

    yield

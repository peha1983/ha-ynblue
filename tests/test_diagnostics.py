"""Diagnostics tests for YnBlue."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.ynblue.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redact_account_and_device_secrets(hass, config_entry, device_payload):
    """Test diagnostics redact sensitive account and device fields."""

    config_entry.runtime_data = SimpleNamespace(
        coordinator=SimpleNamespace(
            data={
                device_payload["id"]: device_payload,
            }
        ),
        hub=SimpleNamespace(available=True),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["entry"]["email"] == "**REDACTED**"
    assert list(diagnostics["devices"]) == ["controller_1"]
    assert device_payload["id"] not in diagnostics["devices"]
    redacted_device = next(iter(diagnostics["devices"].values()))
    assert redacted_device["id"] == "**REDACTED**"
    assert redacted_device["system"]["latitude"] == "**REDACTED**"
    assert redacted_device["system"]["serialNumber"] == "**REDACTED**"
    assert redacted_device["wifi"]["ssid"] == "**REDACTED**"

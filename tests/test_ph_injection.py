"""Regression tests for manual pH injection confirmation."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.const import SNAPSHOT_STALE_INTERVAL
from custom_components.ynblue.coordinator import YnBlueCoordinator
from custom_components.ynblue.exceptions import YnBlueApiError, YnBlueCommandError, YnBlueMqttError
from custom_components.ynblue.hub import YnBlueHub

DEVICE_ID = "test-controller"
ACTIONS = [
    pytest.param("async_inject_ph", 1, True, id="start"),
    pytest.param("async_stop_ph_injection", 0, False, id="stop"),
]


@pytest.fixture(name="hub")
def fixture_hub(hass, config_entry, monkeypatch):
    """Provide an online controller with a fresh snapshot and no command delay."""

    api = YnBlueApiClient(session=None, email="test@example.com", password="test-password")
    coordinator = YnBlueCoordinator(hass, config_entry, api)
    coordinator.async_set_updated_data({DEVICE_ID: {"id": DEVICE_ID, "isConnected": True, "filter": {"state": True}}})
    hub = YnBlueHub(hass, config_entry, coordinator, api)
    hub._last_snapshot_success[DEVICE_ID] = time.monotonic()
    monkeypatch.setattr("custom_components.ynblue.hub.COMMAND_SETTLE_DELAY", 0)
    return hub


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
async def test_ph_injection_confirms_reported_state(hub, action, value, expected):
    """Accept a command only when the returned snapshot confirms its requested state."""

    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(
            hub,
            "_async_request_snapshot_locked",
            AsyncMock(return_value={"pH": {"injection": {"state": expected}}}),
        ) as snapshot,
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": value})
    snapshot.assert_awaited_once_with(DEVICE_ID)


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
@pytest.mark.parametrize("response", ["opposite", "missing_ph", "missing_injection", "missing_state"])
async def test_ph_injection_rejects_unconfirmed_state_without_resending(hub, action, value, expected, response):
    """A contradictory or incomplete response must not be reported as success or retried."""

    snapshots = {
        "opposite": {"pH": {"injection": {"state": not expected}}},
        "missing_ph": {},
        "missing_injection": {"pH": {}},
        "missing_state": {"pH": {"injection": {}}},
    }
    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock(return_value=snapshots[response])) as snapshot,
        pytest.raises(YnBlueCommandError, match="expected device state"),
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": value})
    snapshot.assert_awaited_once_with(DEVICE_ID)


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
@pytest.mark.parametrize("reported", [None, "true", "false", 0, 1, {}, []])
async def test_ph_injection_rejects_non_boolean_confirmation(hub, action, value, expected, reported):
    """Truthiness must not turn a malformed injection state into confirmed dosing."""

    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(
            hub,
            "_async_request_snapshot_locked",
            AsyncMock(return_value={"pH": {"injection": {"state": reported}}}),
        ),
        pytest.raises(YnBlueCommandError, match="expected device state"),
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": value})


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
@pytest.mark.parametrize("failure", [YnBlueMqttError, YnBlueApiError])
async def test_ph_injection_publish_failure_does_not_resend(hub, action, value, expected, failure):
    """A failed publish must not retry a potentially delivered dosing command."""

    with (
        patch.object(hub, "async_publish", AsyncMock(side_effect=failure("test failure"))) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock()) as snapshot,
        pytest.raises(YnBlueCommandError, match="Could not confirm"),
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": value})
    snapshot.assert_not_awaited()


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
@pytest.mark.parametrize("failure", [YnBlueMqttError, YnBlueApiError])
async def test_ph_injection_confirmation_failure_does_not_resend(hub, action, value, expected, failure):
    """An ambiguous transport failure after sending the command must never repeat a dose."""

    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock(side_effect=failure("test failure"))) as snapshot,
        pytest.raises(YnBlueCommandError, match="Could not confirm"),
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": value})
    snapshot.assert_awaited_once_with(DEVICE_ID)


@pytest.mark.parametrize(("action", "value", "expected"), ACTIONS)
@pytest.mark.parametrize("condition", ["offline", "stale", "never_received"])
async def test_ph_injection_safety_guard_prevents_publish(hub, action, value, expected, condition):
    """Preserve the existing online and freshness checks for both pH commands."""

    if condition == "offline":
        hub.coordinator.async_update_device(DEVICE_ID, {"isConnected": False})
        message = "currently offline"
    else:
        if condition == "stale":
            hub._last_snapshot_success[DEVICE_ID] = time.monotonic() - SNAPSHOT_STALE_INTERVAL.total_seconds() - 1
        else:
            hub._last_snapshot_success.clear()
        message = "fresh live snapshot"

    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock()) as snapshot,
        pytest.raises(YnBlueCommandError, match=message),
    ):
        await getattr(hub, action)(DEVICE_ID)

    publish.assert_not_awaited()
    snapshot.assert_not_awaited()


@pytest.mark.parametrize("filter_state", [False, None, "true", "false", 0, 1])
async def test_ph_injection_requires_confirmed_controller_filtration(hub, filter_state):
    """An external pump or an ambiguous state cannot stand in for YnBlue filtration."""

    hub.coordinator.async_update_device(DEVICE_ID, {"filter": {"state": filter_state}})
    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock()) as snapshot,
        pytest.raises(YnBlueCommandError, match="does not report running filtration"),
    ):
        await hub.async_inject_ph(DEVICE_ID)

    publish.assert_not_awaited()
    snapshot.assert_not_awaited()


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"chemical": {"injection": {"state": True}}}, "chemical injection is active"),
        ({"chemical": {"injectionExtra": {"state": True}}}, "chemical injection is active"),
        ({"pH": {"injection": {"state": True}}}, "already active"),
    ],
)
async def test_ph_injection_does_not_overlap_active_dosing(hub, updates, message):
    """Reject an overlapping start without publishing another dose."""

    hub.coordinator.async_update_device(DEVICE_ID, updates)
    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        pytest.raises(YnBlueCommandError, match=message),
    ):
        await hub.async_inject_ph(DEVICE_ID)

    publish.assert_not_awaited()


async def test_ph_injection_precondition_is_checked_inside_device_lock(hub):
    """A state change while waiting for another command must be checked before publishing."""

    lock = hub._async_device_lock(DEVICE_ID)
    await lock.acquire()
    with patch.object(hub, "async_publish", AsyncMock()) as publish:
        task = asyncio.create_task(hub.async_inject_ph(DEVICE_ID))
        await asyncio.sleep(0)
        hub.coordinator.async_update_device(DEVICE_ID, {"filter": {"state": False}})
        lock.release()
        with pytest.raises(YnBlueCommandError, match="does not report running filtration"):
            await task

    publish.assert_not_awaited()


async def test_concurrent_ph_starts_publish_only_one_dose(hub):
    """A queued start must see the first start's confirmed state and reject another dose."""

    async def confirm_start(device_id):
        await asyncio.sleep(0)
        snapshot = {"pH": {"injection": {"state": True}}}
        hub.coordinator.async_update_device(device_id, snapshot)
        return snapshot

    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(hub, "_async_request_snapshot_locked", AsyncMock(side_effect=confirm_start)),
    ):
        results = await asyncio.gather(
            hub.async_inject_ph(DEVICE_ID), hub.async_inject_ph(DEVICE_ID), return_exceptions=True
        )

    assert results[0] is None
    assert isinstance(results[1], YnBlueCommandError)
    assert "already active" in str(results[1])
    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": 1})


async def test_stop_ph_injection_does_not_require_running_filtration(hub):
    """A dosing stop must remain possible when filtration has stopped or another dose is active."""

    hub.coordinator.async_update_device(
        DEVICE_ID,
        {"filter": {"state": False}, "chemical": {"injection": {"state": True}}},
    )
    with (
        patch.object(hub, "async_publish", AsyncMock()) as publish,
        patch.object(
            hub, "_async_request_snapshot_locked", AsyncMock(return_value={"pH": {"injection": {"state": False}}})
        ),
    ):
        await hub.async_stop_ph_injection(DEVICE_ID)

    publish.assert_awaited_once_with(f"/YnBlue/{DEVICE_ID}/pH/mode", {"mode": 2, "value": 0})

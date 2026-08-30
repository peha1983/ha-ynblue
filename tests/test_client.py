"""Client tests for YnBlue API error handling."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.exceptions import YnBlueApiError


async def test_validate_credentials_does_not_reacquire_auth_lock():
    """Test credential validation releases the auth lock before loading the account."""

    client = YnBlueApiClient(
        session=None,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )

    async def login() -> None:
        client._set_token("Bearer token")

    account = {"id": "user-1", "firstName": "Patrick", "name": "Huebler"}
    with (
        patch.object(client, "_async_login", side_effect=login) as async_login,
        patch.object(client, "_async_request_json", AsyncMock(return_value=account)) as async_request,
    ):
        result = await asyncio.wait_for(client.async_validate_credentials(), timeout=1.0)

    assert result == account
    async_login.assert_awaited_once_with()
    async_request.assert_awaited_once_with("GET", "/user/", auth_required=True)


async def test_request_json_wraps_timeout_errors():
    """Test that REST timeouts become YnBlueApiError instead of raw asyncio errors."""

    session = SimpleNamespace(request=lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError()))
    client = YnBlueApiClient(
        session=session,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )

    with pytest.raises(YnBlueApiError, match="timed out"):
        await client._async_request_json("GET", "/user/")


async def test_request_errors_redact_device_id_from_api_path():
    """Test controller identifiers never appear in surfaced REST errors."""

    sensitive_id = "controller-secret-123"
    session = SimpleNamespace(request=lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError()))
    client = YnBlueApiClient(
        session=session,  # type: ignore[arg-type]
        email="patrick@example.com",
        password="secret",
    )

    with pytest.raises(YnBlueApiError) as error_info:
        await client._async_request_json("GET", f"/ynblue/{sensitive_id}")

    assert "/ynblue/[redacted]" in str(error_info.value)
    assert sensitive_id not in str(error_info.value)

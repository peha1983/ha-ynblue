"""Client tests for YnBlue API error handling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.ynblue.client import YnBlueApiClient
from custom_components.ynblue.exceptions import YnBlueApiError


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

"""Async REST client for YnBlue."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import API_BASE_URL, AUTH_REFRESH_MARGIN, DEFAULT_LANGUAGE
from .exceptions import YnBlueApiError, YnBlueAuthError

_LOGGER = logging.getLogger(__name__)


class YnBlueApiClient:
    """Async client for the YnBlue cloud API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        email: str,
        password: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._email = email
        self._password = password
        self._language = language or DEFAULT_LANGUAGE
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._account: dict[str, Any] | None = None
        self._auth_lock = asyncio.Lock()

    @property
    def email(self) -> str:
        """Return the configured email address."""
        return self._email

    @property
    def language(self) -> str:
        """Return the configured language."""
        return self._language

    @property
    def token(self) -> str | None:
        """Return the cached bearer token."""
        return self._token

    @property
    def seconds_until_expiry(self) -> float | None:
        """Return the remaining JWT lifetime in seconds."""
        if self._token_expires_at is None:
            return None
        return max(0.0, (self._token_expires_at - datetime.now(UTC)).total_seconds())

    async def async_validate_credentials(self) -> dict[str, Any]:
        """Validate credentials and return the account payload."""
        async with self._auth_lock:
            await self._async_login()
            account = await self.async_get_account(force_refresh=True)
        return account

    async def async_ensure_auth(self) -> str:
        """Ensure a valid token is available and return it."""
        async with self._auth_lock:
            if self._token is None:
                await self._async_login()
                return self._token or ""

            if self._token_expires_at is None:
                return self._token

            if self._token_expires_at - datetime.now(UTC) > AUTH_REFRESH_MARGIN:
                return self._token

            try:
                await self._async_refresh_token()
            except YnBlueAuthError:
                _LOGGER.debug("JWT refresh failed, falling back to full login")
                await self._async_login()
            return self._token or ""

    async def async_reauthenticate(self) -> str:
        """Force a fresh login and return the new JWT."""

        async with self._auth_lock:
            await self._async_login()
            return self._token or ""

    async def async_get_account(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return the YnBlue account payload."""
        await self.async_ensure_auth()
        if self._account is not None and not force_refresh:
            return self._account

        self._account = await self._async_request_json("GET", "/user/", auth_required=True)
        return self._account

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return the full YnBlue device list for the current account."""
        account = await self.async_get_account(force_refresh=True)
        ynblues = account.get("ynblues", [])
        if not isinstance(ynblues, list):
            raise YnBlueApiError("Unexpected account payload: ynblues is not a list")

        tasks = []
        for ynblue in ynblues:
            device_id = ynblue.get("id")
            if device_id:
                tasks.append(self.async_get_device(device_id, device_stub=ynblue))

        return await asyncio.gather(*tasks)

    async def async_get_device(
        self,
        device_id: str,
        *,
        device_stub: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the full metadata for a single device."""
        metadata = await self._async_request_json("GET", f"/ynblue/{device_id}", auth_required=True)
        merged = dict(device_stub or {})
        merged.update(metadata)
        return merged

    async def _async_login(self) -> None:
        """Authenticate with YnBlue and cache the token."""
        payload = {
            "email": self._email.strip().lower(),
            "password": self._password,
            "language": self._language,
        }
        data = await self._async_request_json("POST", "/user/login", json_payload=payload)
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise YnBlueAuthError("Login succeeded without a valid token")

        self._set_token(token)
        self._account = None

    async def _async_refresh_token(self) -> None:
        """Refresh the cached JWT token."""
        data = await self._async_request_json("GET", "/user/update/jwt", auth_required=True)
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise YnBlueAuthError("JWT refresh succeeded without a valid token")

        self._set_token(token)

    def _set_token(self, token: str) -> None:
        """Cache the token and decoded expiry."""
        self._token = token
        self._token_expires_at = _decode_jwt_expiry(token)

    async def _async_request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        auth_required: bool = False,
    ) -> dict[str, Any]:
        """Perform an HTTP request and return parsed JSON."""

        headers: dict[str, str] = {}
        if auth_required:
            if self._token is None:
                raise YnBlueAuthError("No JWT available for authenticated request")
            headers["Authorization"] = self._token

        try:
            async with self._session.request(
                method,
                f"{API_BASE_URL}{path}",
                json=json_payload,
                headers=headers,
                timeout=20,
            ) as response:
                text = await response.text()
                if response.status in (401, 403):
                    raise YnBlueAuthError(f"YnBlue auth failed for {path}: {response.status}")
                if response.status >= 400:
                    raise YnBlueApiError(f"YnBlue API error for {path}: {response.status} {text[:300]}")

                try:
                    data = json.loads(text)
                except json.JSONDecodeError as err:
                    raise YnBlueApiError(f"Invalid JSON from YnBlue for {path}") from err
        except TimeoutError as err:
            raise YnBlueApiError(f"YnBlue request timed out for {path}") from err
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise YnBlueAuthError("YnBlue authentication failed") from err
            raise YnBlueApiError(f"YnBlue request failed for {path}") from err
        except ClientError as err:
            raise YnBlueApiError(f"YnBlue request failed for {path}: {err}") from err

        if not isinstance(data, dict):
            raise YnBlueApiError(f"Unexpected JSON payload for {path}: expected an object")
        return data


def _decode_jwt_expiry(token: str) -> datetime | None:
    """Decode the JWT exp claim without verifying the signature."""

    raw_token = token.removeprefix("Bearer ").strip()
    parts = raw_token.split(".")
    if len(parts) != 3:
        return None

    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
        data = json.loads(decoded.decode("utf-8"))
        exp = data.get("exp")
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(exp, int):
        return None
    return datetime.fromtimestamp(exp, tz=UTC)

"""Minimal async TransIP REST API (v6) client.

Only implements what this integration needs: generating an access token from
a Key Pair (login + RSA private key) and reading/patching DNS entries.
"""
from __future__ import annotations

import base64
import json
import logging
import secrets
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant

from .const import (
    API_AUTH_PATH,
    API_BASE_URL,
    API_DNS_PATH,
    API_TEST_PATH,
    TOKEN_EXPIRATION_TIME,
    TOKEN_LABEL,
)

_LOGGER = logging.getLogger(__name__)


class TransIPApiError(Exception):
    """Raised when the TransIP API returns an error response."""


class TransIPAuthError(TransIPApiError):
    """Raised when authentication with TransIP fails."""


def _sign_body(private_key_pem: str, body: bytes) -> str:
    """Sign a request body with the RSA private key (blocking, run in executor)."""
    # Imported here so the (relatively heavy) cryptography import only happens
    # when actually needed, and to keep this function trivially offloadable.
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
    except ValueError as err:
        raise TransIPAuthError(f"Invalid private key: {err}") from err

    signature = private_key.sign(body, padding.PKCS1v15(), hashes.SHA512())
    return base64.b64encode(signature).decode("utf-8")


class TransIPClient:
    """Thin async wrapper around the TransIP REST API v6."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        login: str,
        private_key: str,
    ) -> None:
        self._hass = hass
        self._session = session
        self._login = login
        self._private_key = private_key

    async def async_get_token(self) -> str:
        """Request a fresh access token using the configured Key Pair."""
        nonce = secrets.token_hex(16)
        body_dict = {
            "login": self._login,
            "nonce": nonce,
            "read_only": False,
            "expiration_time": TOKEN_EXPIRATION_TIME,
            # TransIP rejects creating a new token whose label matches
            # another still-active token. We request a fresh token every
            # coordinator cycle (tokens live 30 min, cycles run more often),
            # so the label must be unique per request to avoid a 401
            # "label is already used in another active access token".
            "label": f"{TOKEN_LABEL}-{nonce[:12]}",
            # global_key=True: token is not restricted to a whitelisted IP.
            # Required here because the whole point of this integration is
            # that our own external IP is not stable.
            "global_key": True,
        }
        body_bytes = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")

        signature = await self._hass.async_add_executor_job(
            _sign_body, self._private_key, body_bytes
        )

        try:
            async with self._session.post(
                f"{API_BASE_URL}{API_AUTH_PATH}",
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Signature": signature,
                },
            ) as resp:
                text = await resp.text()
                if resp.status != 201 and resp.status != 200:
                    raise TransIPAuthError(
                        f"Authentication failed ({resp.status}): {text}"
                    )
                data = json.loads(text) if text else {}
        except aiohttp.ClientError as err:
            raise TransIPAuthError(f"Error contacting TransIP API: {err}") from err

        token = data.get("token")
        if not token:
            raise TransIPAuthError("TransIP API did not return an access token")
        return token

    async def async_test_token(self, token: str) -> bool:
        """Verify a token works by calling the api-test endpoint."""
        async with self._session.get(
            f"{API_BASE_URL}{API_TEST_PATH}",
            headers=_auth_headers(token),
        ) as resp:
            return resp.status == 200

    async def async_list_domains(self, token: str) -> list[str]:
        """Return the names of all domains in this TransIP account."""
        async with self._session.get(
            f"{API_BASE_URL}/domains", headers=_auth_headers(token)
        ) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise TransIPApiError(f"Failed to fetch domains ({resp.status}): {text}")
            data = json.loads(text)
        return sorted(d["name"] for d in data.get("domains", []) if "name" in d)

    async def async_list_dns_entries(
        self, token: str, domain: str
    ) -> list[dict[str, Any]]:
        """Return all DNS entries for a domain."""
        url = f"{API_BASE_URL}{API_DNS_PATH.format(domain=domain)}"
        async with self._session.get(url, headers=_auth_headers(token)) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise TransIPApiError(
                    f"Failed to fetch DNS entries for '{domain}' "
                    f"({resp.status}): {text}"
                )
            data = json.loads(text)
        return data.get("dnsEntries", [])

    async def async_patch_dns_entry(
        self, token: str, domain: str, dns_entry: dict[str, Any]
    ) -> None:
        """Update the content of a single existing DNS entry."""
        url = f"{API_BASE_URL}{API_DNS_PATH.format(domain=domain)}"
        body = json.dumps({"dnsEntry": dns_entry}).encode("utf-8")
        async with self._session.patch(
            url,
            data=body,
            headers={**_auth_headers(token), "Content-Type": "application/json"},
        ) as resp:
            if resp.status != 204:
                text = await resp.text()
                raise TransIPApiError(
                    f"Failed to update DNS entry for '{domain}' "
                    f"({resp.status}): {text}"
                )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

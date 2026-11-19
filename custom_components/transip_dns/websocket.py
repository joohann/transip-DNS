"""Websocket API the panel talks to.

Every command is admin only: these read and write DNS configuration.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .api import TransIPApiError
from .const import (
    CONF_LOGIN,
    CONF_RECORDS,
    DOMAIN,
    WS_DOMAINS,
    WS_INFO,
    WS_REFRESH,
    WS_SET_OPTIONS,
    WS_SET_RECORDS,
)
from .coordinator import TransipDnsCoordinator
from .panel_data import ValidationError, build_info, validate_options, validate_records

_LOGGER = logging.getLogger(__name__)

COMMANDS_KEY = f"{DOMAIN}_ws_registered"


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Register the panel's websocket commands once."""
    if hass.data.get(COMMANDS_KEY):
        return
    websocket_api.async_register_command(hass, ws_info)
    websocket_api.async_register_command(hass, ws_domains)
    websocket_api.async_register_command(hass, ws_set_records)
    websocket_api.async_register_command(hass, ws_set_options)
    websocket_api.async_register_command(hass, ws_refresh)
    hass.data[COMMANDS_KEY] = True


def _entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return hass.config_entries.async_entries(DOMAIN)


def _coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> tuple[ConfigEntry, TransipDnsCoordinator]:
    """Resolve the entry the panel is asking about.

    Without an entry_id the first configured account is used, which is what
    opening the panel straight from the sidebar should do.
    """
    entries = _entries(hass)
    if not entries:
        raise LookupError("no_entries")

    entry = entries[0]
    if entry_id is not None:
        entry = next((e for e in entries if e.entry_id == entry_id), None)
        if entry is None:
            raise LookupError("unknown_entry")

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        raise LookupError("entry_not_loaded")
    return entry, coordinator


def _notify_targets(hass: HomeAssistant) -> list[str]:
    return sorted(hass.services.async_services().get("notify", {}))


def _handle_lookup_error(connection: websocket_api.ActiveConnection, msg_id: int, err: LookupError) -> None:
    connection.send_error(msg_id, str(err), f"TransIP DNS: {err}")


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): WS_INFO, vol.Optional("entry_id"): str}
)
@callback
def ws_info(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Everything the panel needs to render itself."""
    try:
        entry, coordinator = _coordinator(hass, msg.get("entry_id"))
    except LookupError as err:
        _handle_lookup_error(connection, msg["id"], err)
        return

    last_exception = (
        str(coordinator.last_exception) if coordinator.last_exception else None
    )
    payload = build_info(
        entry_id=entry.entry_id,
        title=entry.title,
        login=entry.data.get(CONF_LOGIN, ""),
        options=dict(entry.options),
        data=coordinator.data,
        ip_history=coordinator.ip_history,
        record_history=coordinator.record_history,
        notify_targets=_notify_targets(hass),
        last_update_success=coordinator.last_update_success,
        last_exception=last_exception,
    )
    payload["entries"] = [
        {"entry_id": e.entry_id, "title": e.title} for e in _entries(hass)
    ]
    connection.send_result(msg["id"], payload)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): WS_DOMAINS, vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_domains(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The domain names in the TransIP account, for the record editor."""
    try:
        _entry, coordinator = _coordinator(hass, msg.get("entry_id"))
    except LookupError as err:
        _handle_lookup_error(connection, msg["id"], err)
        return

    try:
        token = await coordinator.client.async_get_token()
        domains = await coordinator.client.async_list_domains(token)
    except TransIPApiError as err:
        _LOGGER.warning("Could not fetch domain list from TransIP: %s", err)
        connection.send_result(msg["id"], {"domains": [], "error": str(err)})
        return

    connection.send_result(msg["id"], {"domains": domains, "error": None})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SET_RECORDS,
        vol.Optional("entry_id"): str,
        vol.Required("records"): list,
    }
)
@callback
def ws_set_records(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Replace the record list. The entry reloads itself afterwards."""
    try:
        entry, _coordinator = _coordinator(hass, msg.get("entry_id"))
    except LookupError as err:
        _handle_lookup_error(connection, msg["id"], err)
        return

    try:
        records = validate_records(msg["records"])
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return

    options = dict(entry.options)
    options[CONF_RECORDS] = records
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"records": records})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SET_OPTIONS,
        vol.Optional("entry_id"): str,
        vol.Required("options"): dict,
    }
)
@callback
def ws_set_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Store a partial options update. The entry reloads itself afterwards."""
    try:
        entry, _coordinator = _coordinator(hass, msg.get("entry_id"))
    except LookupError as err:
        _handle_lookup_error(connection, msg["id"], err)
        return

    try:
        changes = validate_options(msg["options"])
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return

    options = dict(entry.options)
    options.update(changes)
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"options": options})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): WS_REFRESH, vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_refresh(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Check the external IP right now instead of waiting for the interval."""
    try:
        _entry, coordinator = _coordinator(hass, msg.get("entry_id"))
    except LookupError as err:
        _handle_lookup_error(connection, msg["id"], err)
        return

    await coordinator.async_refresh()
    connection.send_result(
        msg["id"],
        {
            "last_update_success": coordinator.last_update_success,
            "error": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
    )

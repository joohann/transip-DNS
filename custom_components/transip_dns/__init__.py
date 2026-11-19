"""The TransIP Dynamic DNS integration.

Watches your external IP address and, whenever it changes, updates the
matching A/AAAA DNS records on TransIP via their REST API (using a Key Pair
for authentication, configured through the config flow).

Optionally it registers a panel that takes over the gear button on the
integration page; see frontend.py.
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from . import frontend as panel_frontend
from . import websocket as panel_websocket
from .const import (
    ATTR_ENABLED,
    ATTR_ENTRY_ID,
    CONF_PANEL_ENABLED,
    CONF_PANEL_SIDEBAR,
    DEFAULT_PANEL_ENABLED,
    DEFAULT_PANEL_SIDEBAR,
    DOMAIN,
    SERVICE_REFRESH,
    SERVICE_SET_PANEL_ENABLED,
)
from .coordinator import TransipDnsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]
SERVICES_KEY = f"{DOMAIN}_services_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TransIP Dynamic DNS from a config entry."""
    coordinator = TransipDnsCoordinator(hass, entry)
    await coordinator.async_load_history()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await panel_frontend.async_register_assets(hass)
    panel_websocket.async_register_commands(hass)
    _async_register_services(hass)
    _async_sync_panel(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    The panel is deliberately left alone here: an options change reloads the
    entry, and tearing the panel down in between would pull the page out from
    under whoever is looking at it. Setup syncs it again right after.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the panel once the last account is gone."""
    _async_sync_panel(hass)


@callback
def _async_sync_panel(hass: HomeAssistant) -> None:
    """Register or remove the panel to match the current options."""
    entries = hass.config_entries.async_entries(DOMAIN)
    wanted = any(
        e.options.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED) for e in entries
    )
    in_sidebar = any(
        e.options.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED)
        and e.options.get(CONF_PANEL_SIDEBAR, DEFAULT_PANEL_SIDEBAR)
        for e in entries
    )

    if wanted:
        panel_frontend.async_register_panel(hass, in_sidebar=in_sidebar)
    else:
        panel_frontend.async_remove_panel(hass)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the services, once per Home Assistant start.

    set_panel_enabled is the way back in if the panel itself ever fails to
    load: call it from Developer tools and the gear button returns to the
    options dialog.
    """
    if hass.data.get(SERVICES_KEY):
        return

    def _entries(call: ServiceCall) -> list[ConfigEntry]:
        entry_id = call.data.get(ATTR_ENTRY_ID)
        entries = hass.config_entries.async_entries(DOMAIN)
        if entry_id:
            return [e for e in entries if e.entry_id == entry_id]
        return entries

    async def _async_refresh(call: ServiceCall) -> None:
        for entry in _entries(call):
            coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if coordinator is not None:
                await coordinator.async_request_refresh()

    async def _async_set_panel_enabled(call: ServiceCall) -> None:
        enabled = call.data[ATTR_ENABLED]
        for entry in _entries(call):
            options = dict(entry.options)
            options[CONF_PANEL_ENABLED] = enabled
            hass.config_entries.async_update_entry(entry, options=options)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        _async_refresh,
        schema=vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PANEL_ENABLED,
        _async_set_panel_enabled,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENABLED): cv.boolean,
                vol.Optional(ATTR_ENTRY_ID): cv.string,
            }
        ),
    )
    hass.data[SERVICES_KEY] = True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options (records, interval, panel) change."""
    await hass.config_entries.async_reload(entry.entry_id)

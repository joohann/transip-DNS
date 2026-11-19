"""Static assets and panel registration for the TransIP DNS panel.

The panel is registered with ``config_panel_domain``, which makes the gear
button on the integration page open this panel instead of the options flow
dialog. Whether it is registered at all is an option, so switching it off
hands the gear back to the options flow.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    INTEGRATION_NAME,
    PANEL_ASSET_BASE,
    PANEL_ELEMENT,
    PANEL_FOLDER,
    PANEL_ICON,
    PANEL_JS_NAME,
    PANEL_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

ASSETS_KEY = f"{DOMAIN}_assets_registered"
PANEL_KEY = f"{DOMAIN}_panel_registered"


def _panel_dir() -> Path:
    return Path(__file__).parent / PANEL_FOLDER


def _asset_version() -> str:
    """Cache buster so a changed panel file is not served from cache."""
    try:
        return str(int((_panel_dir() / PANEL_JS_NAME).stat().st_mtime))
    except OSError:
        return "0"


async def async_register_assets(hass: HomeAssistant) -> None:
    """Serve the panel folder. Safe to call for every config entry."""
    if hass.data.get(ASSETS_KEY):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_ASSET_BASE,
                str(_panel_dir()),
                # The panel is a small hand written file that people may edit
                # in place; long lived cache headers would hide that.
                cache_headers=False,
            )
        ]
    )
    hass.data[ASSETS_KEY] = True
    _LOGGER.debug("Panel assets served from %s", PANEL_ASSET_BASE)


@callback
def async_register_panel(hass: HomeAssistant, *, in_sidebar: bool) -> None:
    """Register (or update) the panel."""
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=INTEGRATION_NAME if in_sidebar else None,
        sidebar_icon=PANEL_ICON if in_sidebar else None,
        frontend_url_path=PANEL_URL_PATH,
        require_admin=True,
        config_panel_domain=DOMAIN,
        show_in_sidebar=in_sidebar,
        update=True,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT,
                "module_url": f"{PANEL_ASSET_BASE}/{PANEL_JS_NAME}?v={_asset_version()}",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
    )
    hass.data[PANEL_KEY] = True


@callback
def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the panel, handing the gear button back to the options flow."""
    if not hass.data.get(PANEL_KEY):
        return
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    hass.data[PANEL_KEY] = False

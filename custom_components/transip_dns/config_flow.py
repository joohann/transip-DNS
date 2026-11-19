"""Config flow for the TransIP Dynamic DNS integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import TransIPApiError, TransIPAuthError, TransIPClient
from .const import (
    CONF_DOMAIN_NAME,
    CONF_LOGIN,
    CONF_NOTIFY_EVENT,
    CONF_NOTIFY_PERSISTENT,
    CONF_NOTIFY_TARGETS,
    CONF_PANEL_ENABLED,
    CONF_PANEL_SIDEBAR,
    CONF_PRIVATE_KEY,
    CONF_RECORD_NAME,
    CONF_RECORD_TYPE,
    CONF_RECORDS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NOTIFY_EVENT,
    DEFAULT_NOTIFY_PERSISTENT,
    DEFAULT_NOTIFY_TARGETS,
    DEFAULT_PANEL_ENABLED,
    DEFAULT_PANEL_SIDEBAR,
    DEFAULT_RECORD_NAME,
    DEFAULT_RECORD_TYPE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MIN_UPDATE_INTERVAL_MINUTES,
    RECORD_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_credentials(
    hass: HomeAssistant, login: str, private_key: str
) -> list[str]:
    """Try to obtain and use a token. Raises TransIPAuthError on failure.

    Returns the list of domain names in the account (best effort - an empty
    list is returned if fetching domains fails, the domain field then just
    falls back to free text entry).
    """
    session = async_get_clientsession(hass)
    client = TransIPClient(hass, session, login, private_key)
    token = await client.async_get_token()
    if not await client.async_test_token(token):
        raise TransIPAuthError("Token was issued but api-test call failed")
    try:
        return await client.async_list_domains(token)
    except TransIPApiError as err:
        _LOGGER.warning("Could not fetch domain list from TransIP: %s", err)
        return []


async def _fetch_domains(hass: HomeAssistant, login: str, private_key: str) -> list[str]:
    """Fetch the account's domain names, best effort (empty list on failure)."""
    try:
        session = async_get_clientsession(hass)
        client = TransIPClient(hass, session, login, private_key)
        token = await client.async_get_token()
        return await client.async_list_domains(token)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not fetch domain list from TransIP: %s", err)
        return []


def _list_notify_targets(hass: HomeAssistant) -> list[str]:
    """Return all registered notify.* service names (e.g. 'mobile_app_iphone')."""
    services = hass.services.async_services().get("notify", {})
    return sorted(services.keys())


def _record_schema(
    defaults: dict[str, Any] | None = None, domains: list[str] | None = None
) -> vol.Schema:
    defaults = defaults or {}
    if domains:
        domain_field = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=domains,
                mode=selector.SelectSelectorMode.DROPDOWN,
                custom_value=True,
            )
        )
    else:
        domain_field = str

    return vol.Schema(
        {
            vol.Required(
                CONF_DOMAIN_NAME, default=defaults.get(CONF_DOMAIN_NAME, "")
            ): domain_field,
            vol.Required(
                CONF_RECORD_NAME,
                default=defaults.get(CONF_RECORD_NAME, DEFAULT_RECORD_NAME),
            ): str,
            vol.Required(
                CONF_RECORD_TYPE,
                default=defaults.get(CONF_RECORD_TYPE, DEFAULT_RECORD_TYPE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECORD_TYPES, mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required("add_another", default=False): bool,
        }
    )


class TransipDnsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TransIP Dynamic DNS."""

    VERSION = 1

    def __init__(self) -> None:
        self._login: str | None = None
        self._private_key: str | None = None
        self._records: list[dict[str, str]] = []
        self._domains: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}
        login_default = ""
        if user_input is not None:
            login_default = user_input[CONF_LOGIN]
            self._login = user_input[CONF_LOGIN].strip()
            self._private_key = user_input[CONF_PRIVATE_KEY].strip()
            try:
                self._domains = await _validate_credentials(
                    self.hass, self._login, self._private_key
                )
            except TransIPAuthError as err:
                _LOGGER.debug("TransIP auth validation failed: %s", err)
                errors["base"] = "auth_failed"
                description_placeholders["error_detail"] = str(err)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating TransIP credentials")
                errors["base"] = "unknown"
                description_placeholders["error_detail"] = str(err)
            else:
                await self.async_set_unique_id(self._login)
                self._abort_if_unique_id_configured()
                return await self.async_step_record()

        schema = vol.Schema(
            {
                vol.Required(CONF_LOGIN, default=login_default): str,
                vol.Required(CONF_PRIVATE_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_record(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            add_another = user_input.pop("add_another")
            self._records.append(
                {
                    CONF_DOMAIN_NAME: user_input[CONF_DOMAIN_NAME].strip().lower(),
                    CONF_RECORD_NAME: user_input[CONF_RECORD_NAME].strip(),
                    CONF_RECORD_TYPE: user_input[CONF_RECORD_TYPE],
                }
            )
            if add_another:
                return await self.async_step_record()

            return self.async_create_entry(
                title=f"TransIP DNS ({self._login})",
                data={
                    CONF_LOGIN: self._login,
                    CONF_PRIVATE_KEY: self._private_key,
                },
                options={
                    CONF_RECORDS: self._records,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL_MINUTES,
                },
            )

        return self.async_show_form(
            step_id="record",
            data_schema=_record_schema(domains=self._domains),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "TransipDnsOptionsFlow":
        return TransipDnsOptionsFlow()


class TransipDnsOptionsFlow(config_entries.OptionsFlow):
    """Manage DNS records and update interval after initial setup.

    Note: this intentionally does NOT set self.config_entry in __init__.
    Recent Home Assistant versions manage config_entry themselves (it's
    exposed as a property backed by the entry registry); assigning to it
    manually causes a crash (500) when the options flow is opened.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, str]] | None = None

    def _ensure_records(self) -> list[dict[str, str]]:
        if self._records is None:
            self._records = list(self.config_entry.options.get(CONF_RECORDS, []))
        return self._records

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        self._ensure_records()
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "add_record",
                "remove_record",
                "interval",
                "notifications",
                "panel",
            ],
        )

    async def async_step_add_record(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        self._ensure_records()
        if user_input is not None:
            add_another = user_input.pop("add_another")
            self._records.append(
                {
                    CONF_DOMAIN_NAME: user_input[CONF_DOMAIN_NAME].strip().lower(),
                    CONF_RECORD_NAME: user_input[CONF_RECORD_NAME].strip(),
                    CONF_RECORD_TYPE: user_input[CONF_RECORD_TYPE],
                }
            )
            if add_another:
                return await self.async_step_add_record()
            return self._save()

        domains = await _fetch_domains(
            self.hass,
            self.config_entry.data[CONF_LOGIN],
            self.config_entry.data[CONF_PRIVATE_KEY],
        )
        return self.async_show_form(
            step_id="add_record", data_schema=_record_schema(domains=domains)
        )

    async def async_step_remove_record(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        self._ensure_records()
        if not self._records:
            return self._save()

        labels = {
            str(i): f"{r[CONF_RECORD_NAME]}.{r[CONF_DOMAIN_NAME]} ({r[CONF_RECORD_TYPE]})"
            for i, r in enumerate(self._records)
        }

        if user_input is not None:
            to_remove = set(user_input.get("records", []))
            self._records = [
                r for i, r in enumerate(self._records) if str(i) not in to_remove
            ]
            return self._save()

        schema = vol.Schema(
            {
                vol.Required("records", default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in labels.items()
                        ],
                        multiple=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_record", data_schema=schema)

    async def async_step_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self._save(update_interval=user_input[CONF_UPDATE_INTERVAL])

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL_MINUTES,
                        max=1440,
                        step=1,
                        unit_of_measurement="minutes",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(step_id="interval", data_schema=schema)

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self._save(
                notify_persistent=user_input[CONF_NOTIFY_PERSISTENT],
                notify_event=user_input[CONF_NOTIFY_EVENT],
                notify_targets=user_input.get(CONF_NOTIFY_TARGETS, []),
            )

        targets = _list_notify_targets(self.hass)
        current_targets = [
            t
            for t in self.config_entry.options.get(
                CONF_NOTIFY_TARGETS, DEFAULT_NOTIFY_TARGETS
            )
            # keep previously chosen targets in the list even if the
            # notify service briefly isn't registered yet at startup
            if t not in targets
        ] + targets

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NOTIFY_PERSISTENT,
                    default=self.config_entry.options.get(
                        CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT
                    ),
                ): bool,
                vol.Required(
                    CONF_NOTIFY_EVENT,
                    default=self.config_entry.options.get(
                        CONF_NOTIFY_EVENT, DEFAULT_NOTIFY_EVENT
                    ),
                ): bool,
                vol.Optional(
                    CONF_NOTIFY_TARGETS,
                    default=self.config_entry.options.get(
                        CONF_NOTIFY_TARGETS, DEFAULT_NOTIFY_TARGETS
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=current_targets,
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_panel(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Turn the panel on or off.

        With the panel on, the gear button on the integration page opens the
        panel instead of this dialog, so this is the last screen you see
        until you switch it off again from the panel itself.
        """
        if user_input is not None:
            return self._save(
                panel_enabled=user_input[CONF_PANEL_ENABLED],
                panel_sidebar=user_input[CONF_PANEL_SIDEBAR],
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PANEL_ENABLED,
                    default=self.config_entry.options.get(
                        CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED
                    ),
                ): bool,
                vol.Required(
                    CONF_PANEL_SIDEBAR,
                    default=self.config_entry.options.get(
                        CONF_PANEL_SIDEBAR, DEFAULT_PANEL_SIDEBAR
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="panel", data_schema=schema)

    def _save(
        self,
        update_interval: int | None = None,
        notify_persistent: bool | None = None,
        notify_event: bool | None = None,
        notify_targets: list[str] | None = None,
        panel_enabled: bool | None = None,
        panel_sidebar: bool | None = None,
    ) -> config_entries.FlowResult:
        options = dict(self.config_entry.options)
        options[CONF_RECORDS] = self._records
        if update_interval is not None:
            options[CONF_UPDATE_INTERVAL] = update_interval
        if notify_persistent is not None:
            options[CONF_NOTIFY_PERSISTENT] = notify_persistent
        if notify_event is not None:
            options[CONF_NOTIFY_EVENT] = notify_event
        if notify_targets is not None:
            options[CONF_NOTIFY_TARGETS] = notify_targets
        if panel_enabled is not None:
            options[CONF_PANEL_ENABLED] = panel_enabled
        if panel_sidebar is not None:
            options[CONF_PANEL_SIDEBAR] = panel_sidebar
        return self.async_create_entry(title="", data=options)

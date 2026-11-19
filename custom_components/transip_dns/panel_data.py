"""Validation and payload building for the panel.

Pure data handling, no Home Assistant imports, so the rules the panel is held
to can be unit tested without a running Home Assistant.
"""
from __future__ import annotations

from typing import Any

from . import history as history_mod
from .const import (
    CONF_DOMAIN_NAME,
    CONF_NOTIFY_EVENT,
    CONF_NOTIFY_PERSISTENT,
    CONF_NOTIFY_TARGETS,
    CONF_PANEL_ENABLED,
    CONF_PANEL_SIDEBAR,
    CONF_RECORD_NAME,
    CONF_RECORD_TYPE,
    CONF_RECORDS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NOTIFY_EVENT,
    DEFAULT_NOTIFY_PERSISTENT,
    DEFAULT_NOTIFY_TARGETS,
    DEFAULT_PANEL_ENABLED,
    DEFAULT_PANEL_SIDEBAR,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    HISTORY_LENGTH,
    INTEGRATION_NAME,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
    RECORD_TYPES,
)


class ValidationError(ValueError):
    """Raised when the panel sends something that cannot be stored."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def record_key(domain: str, name: str, record_type: str) -> str:
    """Stable identity of a managed record, used as dict key everywhere."""
    return f"{domain}|{name}|{record_type}"


def validate_record(raw: Any) -> dict[str, str]:
    """Normalise one record coming from the panel."""
    if not isinstance(raw, dict):
        raise ValidationError("invalid_record", "Record must be an object")

    domain = str(raw.get(CONF_DOMAIN_NAME, "")).strip().lower().rstrip(".")
    name = str(raw.get(CONF_RECORD_NAME, "")).strip()
    record_type = str(raw.get(CONF_RECORD_TYPE, "")).strip().upper()

    if not domain or "." not in domain:
        raise ValidationError("invalid_domain", f"Not a domain name: {domain!r}")
    if not name:
        raise ValidationError("invalid_name", "Record name may not be empty")
    if record_type not in RECORD_TYPES:
        raise ValidationError("invalid_type", f"Unsupported record type: {record_type!r}")

    return {
        CONF_DOMAIN_NAME: domain,
        CONF_RECORD_NAME: name,
        CONF_RECORD_TYPE: record_type,
    }


def validate_records(raw: Any) -> list[dict[str, str]]:
    """Normalise the full record list, dropping exact duplicates."""
    if not isinstance(raw, list):
        raise ValidationError("invalid_records", "Records must be a list")

    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        record = validate_record(item)
        key = record_key(
            record[CONF_DOMAIN_NAME], record[CONF_RECORD_NAME], record[CONF_RECORD_TYPE]
        )
        if key in seen:
            continue
        seen.add(key)
        records.append(record)
    return records


def validate_options(raw: Any) -> dict[str, Any]:
    """Normalise a partial options update coming from the panel.

    Only keys that are present are returned, so the panel can save one
    section without touching the others.
    """
    if not isinstance(raw, dict):
        raise ValidationError("invalid_options", "Options must be an object")

    options: dict[str, Any] = {}

    if CONF_UPDATE_INTERVAL in raw:
        try:
            interval = int(raw[CONF_UPDATE_INTERVAL])
        except (TypeError, ValueError) as err:
            raise ValidationError("invalid_interval", "Interval must be a number") from err
        if not MIN_UPDATE_INTERVAL_MINUTES <= interval <= MAX_UPDATE_INTERVAL_MINUTES:
            raise ValidationError(
                "invalid_interval",
                f"Interval must be between {MIN_UPDATE_INTERVAL_MINUTES} and "
                f"{MAX_UPDATE_INTERVAL_MINUTES} minutes",
            )
        options[CONF_UPDATE_INTERVAL] = interval

    for key in (CONF_NOTIFY_PERSISTENT, CONF_NOTIFY_EVENT, CONF_PANEL_ENABLED, CONF_PANEL_SIDEBAR):
        if key in raw:
            if not isinstance(raw[key], bool):
                raise ValidationError("invalid_boolean", f"{key} must be true or false")
            options[key] = raw[key]

    if CONF_NOTIFY_TARGETS in raw:
        targets = raw[CONF_NOTIFY_TARGETS]
        if not isinstance(targets, list):
            raise ValidationError("invalid_targets", "Notify targets must be a list")
        cleaned: list[str] = []
        for target in targets:
            name = str(target).strip()
            if name and name not in cleaned:
                cleaned.append(name)
        options[CONF_NOTIFY_TARGETS] = cleaned

    if CONF_RECORDS in raw:
        options[CONF_RECORDS] = validate_records(raw[CONF_RECORDS])

    return options


def public_options(options: dict[str, Any]) -> dict[str, Any]:
    """The options as the panel sees them, with every default filled in."""
    return {
        CONF_RECORDS: list(options.get(CONF_RECORDS, [])),
        CONF_UPDATE_INTERVAL: options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
        ),
        CONF_NOTIFY_PERSISTENT: options.get(
            CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT
        ),
        CONF_NOTIFY_EVENT: options.get(CONF_NOTIFY_EVENT, DEFAULT_NOTIFY_EVENT),
        CONF_NOTIFY_TARGETS: list(
            options.get(CONF_NOTIFY_TARGETS, DEFAULT_NOTIFY_TARGETS)
        ),
        CONF_PANEL_ENABLED: options.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED),
        CONF_PANEL_SIDEBAR: options.get(CONF_PANEL_SIDEBAR, DEFAULT_PANEL_SIDEBAR),
    }


def build_records_state(
    options: dict[str, Any],
    data: dict[str, Any] | None,
    record_history: dict[str, Any],
) -> list[dict[str, Any]]:
    """One row per configured record, merged with its last known result."""
    results = (data or {}).get("records", {})
    rows: list[dict[str, Any]] = []
    for record in options.get(CONF_RECORDS, []):
        key = record_key(
            record[CONF_DOMAIN_NAME], record[CONF_RECORD_NAME], record[CONF_RECORD_TYPE]
        )
        result = results.get(key, {})
        rows.append(
            {
                "key": key,
                CONF_DOMAIN_NAME: record[CONF_DOMAIN_NAME],
                CONF_RECORD_NAME: record[CONF_RECORD_NAME],
                CONF_RECORD_TYPE: record[CONF_RECORD_TYPE],
                "ip": result.get("ip"),
                "status": result.get("status"),
                "error": result.get("error"),
                "last_updated": result.get("last_updated"),
                "history": history_mod.state(record_history, key),
            }
        )
    return rows


def build_info(
    *,
    entry_id: str,
    title: str,
    login: str,
    options: dict[str, Any],
    data: dict[str, Any] | None,
    ip_history: dict[str, Any],
    record_history: dict[str, Any],
    notify_targets: list[str],
    last_update_success: bool,
    last_exception: str | None = None,
) -> dict[str, Any]:
    """The complete payload the panel renders itself from."""
    opts = public_options(options)
    return {
        "entry_id": entry_id,
        "title": title,
        "login": login,
        "name": INTEGRATION_NAME,
        "options": opts,
        "limits": {
            "min_interval": MIN_UPDATE_INTERVAL_MINUTES,
            "max_interval": MAX_UPDATE_INTERVAL_MINUTES,
            "record_types": list(RECORD_TYPES),
            "history_length": HISTORY_LENGTH,
        },
        "notify_targets": list(notify_targets),
        "state": {
            "last_update_success": last_update_success,
            "error": last_exception,
            "ipv4": history_mod.state(ip_history, "ipv4"),
            "ipv6": history_mod.state(ip_history, "ipv6"),
            "records": build_records_state(opts, data, record_history),
        },
    }

"""IP history bookkeeping.

Deliberately free of Home Assistant imports: this is plain data handling so
it can be unit tested on its own.

Stored shape (one dict per address family and per DNS record):

    {
        "current": "84.26.113.7",
        "previous": "84.26.98.212",
        "changed_at": "2026-11-14T04:12:00+00:00",
        "changes": [{"from": "...", "to": "...", "at": "..."}, ...],
    }

``changes`` is newest first and capped at ``limit`` entries.
"""
from __future__ import annotations

from typing import Any

Entry = dict[str, Any]
History = dict[str, Entry]


def _entry(history: History, key: str) -> Entry:
    entry = history.setdefault(key, {})
    entry.setdefault("changes", [])
    return entry


def record_change(
    history: History,
    key: str,
    new_value: str | None,
    now: str,
    limit: int,
) -> bool:
    """Store ``new_value`` as the current value for ``key``.

    The value it replaces becomes ``previous`` and is prepended to the change
    log. Returns True when something actually changed, so the caller knows it
    has to persist. A ``None`` value is ignored: not knowing an address is not
    the same as the address having changed.
    """
    if new_value is None:
        return False

    entry = _entry(history, key)
    current = entry.get("current")
    if current == new_value:
        return False

    if current:
        entry["previous"] = current
        entry["changed_at"] = now
        changes = entry["changes"]
        changes.insert(0, {"from": current, "to": new_value, "at": now})
        del changes[limit:]
    elif not entry.get("changed_at"):
        # First time we ever saw an address: remember when, so the panel can
        # show "unchanged since" instead of an empty field.
        entry["changed_at"] = now

    entry["current"] = new_value
    return True


def state(history: History, key: str) -> Entry:
    """Return the public view of one history entry, always fully populated."""
    entry = history.get(key, {})
    return {
        "current": entry.get("current"),
        "previous": entry.get("previous"),
        "changed_at": entry.get("changed_at"),
        "changes": list(entry.get("changes", [])),
    }


def trim(history: History, limit: int) -> None:
    """Cap every change log, for when the configured limit is lowered."""
    for entry in history.values():
        changes = entry.get("changes")
        if changes:
            del changes[limit:]

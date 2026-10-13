"""Persistent call logging for Yealink/SIP action events."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CALL_STORAGE_KEY_PREFIX,
    CALL_STORAGE_VERSION,
    EVENT_CALL_FINALIZED,
)
from .phone import to_e164

_LOGGER = logging.getLogger(__name__)


class CallLogManager:
    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        coordinator,
        max_entries: int,
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.max_entries = max_entries
        self._store: Store[dict[str, Any]] = Store(
            hass,
            CALL_STORAGE_VERSION,
            f"{CALL_STORAGE_KEY_PREFIX}.{entry_id}",
            private=True,
        )
        self.entries: list[dict[str, Any]] = []
        self.active_calls: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        self.entries = list(raw.get("entries", []))[: self.max_entries]

        active_calls = raw.get("active_calls")
        if isinstance(active_calls, dict):
            self.active_calls = active_calls
        else:
            # Migration from 0.4.x single-active-call storage.
            legacy_active = raw.get("active")
            if isinstance(legacy_active, dict):
                key = self._key(str(legacy_active.get("call_id") or ""))
                self.active_calls = {key: legacy_active}

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "entries": self.entries[: self.max_entries],
                "active_calls": self.active_calls,
            }
        )
        self.coordinator.async_update_listeners()

    @property
    def unread_missed_count(self) -> int:
        return sum(
            1
            for item in self.entries
            if item.get("status") == "missed"
            and not item.get("seen", False)
        )

    @property
    def last_entry(self) -> dict[str, Any] | None:
        return self.entries[0] if self.entries else None

    def _key(self, call_id: str) -> str:
        call_id = str(call_id or "").strip()
        return call_id or f"no-call-id:{uuid.uuid4()}"

    def _lookup_name(self, remote: str) -> tuple[str, str]:
        e164 = to_e164(remote, self.coordinator.country_code)
        name = self.coordinator.lookup(remote) or e164 or "Unbekannter Anrufer"
        return e164, name

    def _own_number(self, active_user: str, local: str) -> str:
        return (
            to_e164(active_user, self.coordinator.country_code)
            or to_e164(local, self.coordinator.country_code)
        )

    def _resolve_active_key(self, call_id: str) -> str | None:
        call_id = str(call_id or "").strip()
        if call_id and call_id in self.active_calls:
            return call_id

        if len(self.active_calls) == 1:
            return next(iter(self.active_calls))

        if call_id:
            return None

        if len(self.active_calls) > 1:
            _LOGGER.warning(
                "Ignoring ambiguous call event without call_id; "
                "%d active calls exist",
                len(self.active_calls),
            )
        return None

    async def async_event(
        self,
        event: str,
        *,
        remote: str = "",
        local: str = "",
        active_user: str = "",
        call_id: str = "",
    ) -> dict[str, Any] | None:
        now = dt_util.utcnow()
        call_id = str(call_id or "").strip()

        if event in ("ringing", "calling"):
            key = call_id or self._key("")
            remote_number, remote_name = self._lookup_name(remote)
            direction = "incoming" if event == "ringing" else "outgoing"

            # Repeated event for the same call updates rather than duplicates it.
            existing = self.active_calls.get(key)
            if existing:
                if remote:
                    existing["remote_number"] = remote_number
                    existing["remote_name"] = remote_name
                if active_user or local:
                    existing["own_number"] = self._own_number(active_user, local)
                existing["status"] = event
            else:
                self.active_calls[key] = {
                    "id": str(uuid.uuid4()),
                    "call_id": call_id,
                    "direction": direction,
                    "remote_number": remote_number,
                    "remote_name": remote_name,
                    "own_number": self._own_number(active_user, local),
                    "started_at": now.isoformat(),
                    "connected_at": None,
                    "ended_at": None,
                    "status": event,
                    "seen": direction != "incoming",
                }

            await self._async_save()
            return None

        if event == "connected":
            key = self._resolve_active_key(call_id)
            if key is None:
                # Create a recoverable call if the start event was missed.
                key = call_id or self._key("")
                remote_number, remote_name = self._lookup_name(remote)
                self.active_calls[key] = {
                    "id": str(uuid.uuid4()),
                    "call_id": call_id,
                    "direction": "unknown",
                    "remote_number": remote_number,
                    "remote_name": remote_name,
                    "own_number": self._own_number(active_user, local),
                    "started_at": now.isoformat(),
                    "connected_at": None,
                    "ended_at": None,
                    "status": "connected",
                    "seen": True,
                }

            active = self.active_calls[key]
            if remote and not active.get("remote_number"):
                number, name = self._lookup_name(remote)
                active["remote_number"] = number
                active["remote_name"] = name

            if active_user or local:
                active["own_number"] = (
                    self._own_number(active_user, local)
                    or active.get("own_number", "")
                )
            if call_id:
                active["call_id"] = call_id
            if not active.get("connected_at"):
                active["connected_at"] = now.isoformat()
            active["status"] = "connected"

            await self._async_save()
            return None

        if event == "idle":
            key = self._resolve_active_key(call_id)
            if key is None:
                return None

            active = self.active_calls.pop(key)
            active["ended_at"] = now.isoformat()

            connected_at = active.get("connected_at")
            direction = active.get("direction")

            if direction == "incoming" and not connected_at:
                active["status"] = "missed"
                active["seen"] = False
            elif connected_at:
                active["status"] = "completed"
                active["seen"] = True
            elif direction == "outgoing":
                active["status"] = "cancelled"
                active["seen"] = True
            else:
                active["status"] = "ended"
                active["seen"] = True

            if connected_at:
                try:
                    start = datetime.fromisoformat(connected_at)
                    end = datetime.fromisoformat(active["ended_at"])
                    active["duration_seconds"] = max(
                        0,
                        int((end - start).total_seconds()),
                    )
                except (TypeError, ValueError):
                    active["duration_seconds"] = None
            else:
                active["duration_seconds"] = 0

            finalized = dict(active)
            self.entries.insert(0, finalized)
            self.entries = self.entries[: self.max_entries]
            await self._async_save()

            self.hass.bus.async_fire(
                EVENT_CALL_FINALIZED,
                finalized,
            )
            return finalized

        return None

    async def async_mark_missed_seen(self) -> None:
        changed = False
        for item in self.entries:
            if item.get("status") == "missed" and not item.get("seen", False):
                item["seen"] = True
                changed = True
        if changed:
            await self._async_save()

    async def async_clear(self) -> None:
        self.entries = []
        await self._async_save()

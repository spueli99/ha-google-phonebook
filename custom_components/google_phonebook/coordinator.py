"""Google People contact coordinator."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONTACT_STORAGE_KEY_PREFIX,
    CONTACT_STORAGE_VERSION,
    DOMAIN,
    GOOGLE_PEOPLE_CONNECTIONS_URL,
    UPDATE_INTERVAL,
)
from .phone import normalize_phone

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PhonebookData:
    contacts: dict[str, str]
    contact_count: int
    last_sync: datetime | None


class GooglePhonebookCoordinator(DataUpdateCoordinator[PhonebookData]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
        country_code: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._oauth_session = oauth_session
        self.country_code = country_code
        self.call_log = None
        self._store: Store[dict[str, Any]] = Store(
            hass,
            CONTACT_STORAGE_VERSION,
            f"{CONTACT_STORAGE_KEY_PREFIX}.{entry_id}",
            private=True,
        )

    async def async_load_cache(self) -> PhonebookData | None:
        raw = await self._store.async_load()
        if not raw:
            return None

        last_sync = None
        if raw.get("last_sync"):
            with contextlib.suppress(TypeError, ValueError):
                last_sync = datetime.fromisoformat(raw["last_sync"])

        contacts = {
            str(number): str(name)
            for number, name in raw.get("contacts", {}).items()
        }
        return PhonebookData(contacts, len(contacts), last_sync)

    async def _async_update_data(self) -> PhonebookData:
        await self._oauth_session.async_ensure_token_valid()
        token = self._oauth_session.token.get("access_token")
        if not token:
            raise UpdateFailed("OAuth token contains no access_token")

        session = async_get_clientsession(self.hass)
        headers = {"Authorization": f"Bearer {token}"}
        contacts: dict[str, str] = {}
        page_token: str | None = None

        try:
            while True:
                params: dict[str, str | int] = {
                    "personFields": "names,phoneNumbers",
                    "pageSize": 500,
                }
                if page_token:
                    params["pageToken"] = page_token

                async with session.get(
                    GOOGLE_PEOPLE_CONNECTIONS_URL,
                    headers=headers,
                    params=params,
                    timeout=30,
                ) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise UpdateFailed(
                            f"Google People API HTTP {response.status}: "
                            f"{body[:200]}"
                        )
                    payload = await response.json()

                for person in payload.get("connections", []):
                    names = person.get("names") or []
                    phones = person.get("phoneNumbers") or []
                    if not names or not phones:
                        continue

                    name = (names[0].get("displayName") or "").strip()
                    if not name:
                        continue

                    for item in phones:
                        number = normalize_phone(
                            item.get("value"),
                            self.country_code,
                        )
                        if number:
                            contacts[number] = name

                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"Error fetching Google contacts: {err}"
            ) from err

        now = dt_util.utcnow()
        data = PhonebookData(contacts, len(contacts), now)
        await self._store.async_save(
            {
                "contacts": contacts,
                "last_sync": now.isoformat(),
            }
        )
        return data

    def lookup(self, phone_number: str) -> str | None:
        if not self.data:
            return None
        normalized = normalize_phone(
            phone_number,
            self.country_code,
        )
        if not normalized:
            return None
        return self.data.contacts.get(normalized)

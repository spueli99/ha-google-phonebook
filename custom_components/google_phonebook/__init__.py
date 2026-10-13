"""Google Phonebook integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers import entity_registry as er

from .call_log import CallLogManager
from .const import (
    ATTR_ACTIVE_USER,
    ATTR_CALL_ID,
    ATTR_EVENT,
    ATTR_LOCAL,
    ATTR_NAME_ENTITY,
    ATTR_NUMBER_ENTITY,
    ATTR_PHONE_NUMBER,
    ATTR_REMOTE,
    CONF_CALL_LOG_MAX_ENTRIES,
    CONF_COUNTRY_CODE,
    DEFAULT_CALL_LOG_MAX_ENTRIES,
    DEFAULT_COUNTRY_CODE,
    DOMAIN,
    PLATFORMS,
    SERVICE_CALL_EVENT,
    SERVICE_CLEAR_CALL_LOG,
    SERVICE_LOOKUP,
    SERVICE_LOOKUP_AND_SET,
    SERVICE_MARK_MISSED_SEEN,
)
from .coordinator import GooglePhonebookCoordinator
from .phone import normalize_phone, to_e164


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass,
            entry,
        )
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(
        hass,
        entry,
        implementation,
    )

    country_code = str(
        entry.options.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE)
    )
    coordinator = GooglePhonebookCoordinator(
        hass,
        entry.entry_id,
        oauth_session,
        country_code,
    )

    cached = await coordinator.async_load_cache()
    if cached is not None:
        coordinator.async_set_updated_data(cached)

    await coordinator.async_config_entry_first_refresh()

    coordinator.call_log = CallLogManager(
        hass,
        entry.entry_id,
        coordinator,
        int(
            entry.options.get(
                CONF_CALL_LOG_MAX_ENTRIES,
                DEFAULT_CALL_LOG_MAX_ENTRIES,
            )
        ),
    )
    await coordinator.call_log.async_load()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass, coordinator)
    return True


async def _async_options_updated(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _get_loaded_coordinator(
    hass: HomeAssistant,
) -> GooglePhonebookCoordinator:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            entry.state is ConfigEntryState.LOADED
            and isinstance(
                getattr(entry, "runtime_data", None),
                GooglePhonebookCoordinator,
            )
        ):
            return entry.runtime_data
    raise RuntimeError("Google Phonebook is not loaded")


async def _async_set_input_text(
    hass: HomeAssistant,
    entity_id: str,
    value: str,
) -> None:
    registry = er.async_get(hass)
    registry_entry = registry.async_get(entity_id)
    if registry_entry is None or registry_entry.domain != "input_text":
        raise ValueError(f"{entity_id} is not a valid input_text entity")

    await hass.services.async_call(
        "input_text",
        "set_value",
        {"entity_id": entity_id, "value": value},
        blocking=True,
    )


def _async_register_services(
    hass: HomeAssistant,
    coordinator: GooglePhonebookCoordinator,
) -> None:
    if not hass.services.has_service(DOMAIN, SERVICE_LOOKUP):
        async def async_lookup(call: ServiceCall) -> dict[str, object]:
            phone_number = str(call.data[ATTR_PHONE_NUMBER])
            name = coordinator.lookup(phone_number)
            return {
                "phone_number": phone_number,
                "normalized_number": normalize_phone(
                    phone_number,
                    coordinator.country_code,
                ),
                "e164_number": to_e164(
                    phone_number,
                    coordinator.country_code,
                ),
                "found": name is not None,
                "name": name or "",
            }

        hass.services.async_register(
            DOMAIN,
            SERVICE_LOOKUP,
            async_lookup,
            schema=vol.Schema(
                {vol.Required(ATTR_PHONE_NUMBER): vol.Coerce(str)}
            ),
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_LOOKUP_AND_SET):
        async def async_lookup_and_set(
            call: ServiceCall,
        ) -> dict[str, object]:
            phone_number = str(call.data[ATTR_PHONE_NUMBER])
            number_entity = str(call.data[ATTR_NUMBER_ENTITY])
            name_entity = str(call.data[ATTR_NAME_ENTITY])

            e164 = to_e164(phone_number, coordinator.country_code)
            name = coordinator.lookup(phone_number)
            display_name = name or e164 or "Unbekannter Anrufer"

            await _async_set_input_text(hass, number_entity, e164)
            await _async_set_input_text(hass, name_entity, display_name)

            return {
                "phone_number": phone_number,
                "normalized_number": normalize_phone(
                    phone_number,
                    coordinator.country_code,
                ),
                "e164_number": e164,
                "found": name is not None,
                "name": name or "",
                "display_name": display_name,
            }

        hass.services.async_register(
            DOMAIN,
            SERVICE_LOOKUP_AND_SET,
            async_lookup_and_set,
            schema=vol.Schema(
                {
                    vol.Required(ATTR_PHONE_NUMBER): vol.Coerce(str),
                    vol.Required(ATTR_NUMBER_ENTITY): vol.Coerce(str),
                    vol.Required(ATTR_NAME_ENTITY): vol.Coerce(str),
                }
            ),
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CALL_EVENT):
        async def async_call_event(
            call: ServiceCall,
        ) -> dict[str, object]:
            event = str(call.data[ATTR_EVENT])
            finalized = await coordinator.call_log.async_event(
                event,
                remote=str(call.data.get(ATTR_REMOTE, "") or ""),
                local=str(call.data.get(ATTR_LOCAL, "") or ""),
                active_user=str(
                    call.data.get(ATTR_ACTIVE_USER, "") or ""
                ),
                call_id=str(call.data.get(ATTR_CALL_ID, "") or ""),
            )
            return {
                "event": event,
                "finalized": finalized is not None,
                "call": finalized or {},
            }

        hass.services.async_register(
            DOMAIN,
            SERVICE_CALL_EVENT,
            async_call_event,
            schema=vol.Schema(
                {
                    vol.Required(ATTR_EVENT): vol.In(
                        ["ringing", "calling", "connected", "idle"]
                    ),
                    vol.Optional(ATTR_REMOTE, default=""): vol.Coerce(str),
                    vol.Optional(ATTR_LOCAL, default=""): vol.Coerce(str),
                    vol.Optional(
                        ATTR_ACTIVE_USER,
                        default="",
                    ): vol.Coerce(str),
                    vol.Optional(ATTR_CALL_ID, default=""): vol.Coerce(str),
                }
            ),
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_MARK_MISSED_SEEN):
        async def async_mark_seen(call: ServiceCall) -> None:
            coordinator = _get_loaded_coordinator(hass)
            await coordinator.call_log.async_mark_missed_seen()

        hass.services.async_register(
            DOMAIN,
            SERVICE_MARK_MISSED_SEEN,
            async_mark_seen,
            schema=vol.Schema({}),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_CALL_LOG):
        async def async_clear_log(call: ServiceCall) -> None:
            coordinator = _get_loaded_coordinator(hass)
            await coordinator.call_log.async_clear()

        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_CALL_LOG,
            async_clear_log,
            schema=vol.Schema({}),
        )


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        other_loaded = any(
            other.entry_id != entry.entry_id
            and other.state is ConfigEntryState.LOADED
            for other in hass.config_entries.async_entries(DOMAIN)
        )
        if not other_loaded:
            for service in (
                SERVICE_LOOKUP,
                SERVICE_LOOKUP_AND_SET,
                SERVICE_CALL_EVENT,
                SERVICE_MARK_MISSED_SEEN,
                SERVICE_CLEAR_CALL_LOG,
            ):
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

    return unload_ok

"""Config flow and options for Google Phonebook."""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    CONF_CALL_LOG_MAX_ENTRIES,
    CONF_CALL_LOG_SENSOR_ENTRIES,
    CONF_COUNTRY_CODE,
    DEFAULT_CALL_LOG_MAX_ENTRIES,
    DEFAULT_CALL_LOG_SENSOR_ENTRIES,
    DEFAULT_COUNTRY_CODE,
    DOMAIN,
    GOOGLE_SCOPE,
)

_LOGGER = logging.getLogger(__name__)


def _country_code(value: str) -> str:
    result = re.sub(r"\D", "", value)
    if not result:
        raise vol.Invalid("country_code")
    return result


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        return {
            "scope": GOOGLE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()

    async def async_oauth_create_entry(
        self,
        data: dict[str, Any],
    ) -> FlowResult:
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Google Phonebook",
            data=data,
            options={
                CONF_COUNTRY_CODE: DEFAULT_COUNTRY_CODE,
                CONF_CALL_LOG_MAX_ENTRIES: DEFAULT_CALL_LOG_MAX_ENTRIES,
                CONF_CALL_LOG_SENSOR_ENTRIES: DEFAULT_CALL_LOG_SENSOR_ENTRIES,
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return GooglePhonebookOptionsFlow()


class GooglePhonebookOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            max_entries = user_input[CONF_CALL_LOG_MAX_ENTRIES]
            sensor_entries = min(
                user_input[CONF_CALL_LOG_SENSOR_ENTRIES],
                max_entries,
            )
            return self.async_create_entry(
                title="",
                data={
                    CONF_COUNTRY_CODE: user_input[CONF_COUNTRY_CODE],
                    CONF_CALL_LOG_MAX_ENTRIES: max_entries,
                    CONF_CALL_LOG_SENSOR_ENTRIES: sensor_entries,
                },
            )

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_COUNTRY_CODE,
                    default=current.get(
                        CONF_COUNTRY_CODE,
                        DEFAULT_COUNTRY_CODE,
                    ),
                ): vol.All(str, _country_code),
                vol.Required(
                    CONF_CALL_LOG_MAX_ENTRIES,
                    default=current.get(
                        CONF_CALL_LOG_MAX_ENTRIES,
                        DEFAULT_CALL_LOG_MAX_ENTRIES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=1000)),
                vol.Required(
                    CONF_CALL_LOG_SENSOR_ENTRIES,
                    default=current.get(
                        CONF_CALL_LOG_SENSOR_ENTRIES,
                        DEFAULT_CALL_LOG_SENSOR_ENTRIES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=50)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

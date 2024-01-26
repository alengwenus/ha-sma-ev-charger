"""Config flow for SMA EV Charger integration."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pysmaev.core import SmaEvCharger
from pysmaev.exceptions import (
    SmaEvChargerAuthenticationError,
    SmaEvChargerConnectionError,
)

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_BASE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SSL, default=True): cv.boolean,
        vol.Optional(CONF_VERIFY_SSL, default=False): cv.boolean,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])

    protocol = "https" if data[CONF_SSL] else "http"
    url = f"{protocol}://{data[CONF_HOST]}"
    evcharger = SmaEvCharger(session, url, data[CONF_USERNAME], data[CONF_PASSWORD])

    errors: dict[str, str] = {}
    device_info: dict[str, str] = {}
    try:
        await evcharger.open()
    except SmaEvChargerConnectionError:
        errors[CONF_BASE] = "cannot_connect"
    except SmaEvChargerAuthenticationError:
        errors[CONF_BASE] = "invalid_auth"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        errors[CONF_BASE] = "unknown"
    else:
        device_info = await evcharger.device_info()

    await evcharger.close()
    return device_info, errors


class SmaEvChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA EV Charger."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow for this handler."""
        return SmaEvChargerOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        device_info, errors = await validate_input(self.hass, user_input)

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        await self.async_set_unique_id(device_info["serial"])
        self._abort_if_unique_id_configured(updates=user_input)
        return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

    async def async_step_reauth(self, user_input: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()


class SmaEvChargerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for SMA EV Charger."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize SMA EV Charger options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the SMA EV Charger options."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, self.config_entry.data
                ),
            )

        _, errors = await validate_input(self.hass, user_input)

        if errors:
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_USER_DATA_SCHEMA, self.config_entry.data
                ),
                errors=errors,
            )

        data = self.config_entry.data.copy()
        data.update(user_input)
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)
        await self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.config_entry.entry_id)
        )
        return self.async_create_entry(title="", data={})

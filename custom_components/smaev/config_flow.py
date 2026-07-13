"""Config flow for SMA EV Charger integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import pysmaev.core
import pysmaev.exceptions
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_BASE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[dict[str, str], str | None]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])

    protocol = "https" if data[CONF_SSL] else "http"
    url = f"{protocol}://{data[CONF_HOST]}"
    evcharger = pysmaev.core.SmaEvCharger(
        session, url, data[CONF_USERNAME], data[CONF_PASSWORD]
    )

    errors: dict[str, str] = {}
    serial: str | None = None
    try:
        await evcharger.open()
        device_info = await evcharger.device_info()
        serial = device_info["serial"]
    except pysmaev.exceptions.SmaEvChargerConnectionError:
        errors[CONF_BASE] = "cannot_connect"
    except pysmaev.exceptions.SmaEvChargerAuthenticationError:
        errors[CONF_BASE] = "invalid_auth"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        errors[CONF_BASE] = "unknown"

    await evcharger.close()
    return errors, serial


class SmaEvChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA EV Charger."""

    VERSION = 1
    MINOR_VERSION = 0

    _config_data: dict[str, str]
    _reconfigure_data: dict[str, str]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        self._config_data = {}
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                }
            )
            errors, serial = await validate_input(self.hass, user_input)
            if not errors:
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                self._config_data.update(user_input)
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=self._config_data
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the reconfigure step."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()
        self._reconfigure_data = reconfigure_entry.data.copy()

        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                }
            )
            self._reconfigure_data = user_input
            errors, _ = await validate_input(self.hass, user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data=self._reconfigure_data
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, self._reconfigure_data
            ),
            errors=errors,
        )

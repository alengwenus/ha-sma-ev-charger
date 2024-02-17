"""Provides device actions for SMA EV Charger."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_TYPE,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from . import DOMAIN
from .const import SERVICE_RESTART

ACTION_TYPES = {"restart"}

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
    }
)


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device actions for SMA EV Charger devices."""
    device_registry = dr.async_get(hass)
    registry_device = device_registry.async_get(device_id)
    if registry_device is None:
        return []

    actions = []

    base_action = {
        CONF_DEVICE_ID: device_id,
        CONF_DOMAIN: DOMAIN,
    }

    actions.append({**base_action, CONF_TYPE: "restart"})

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Context | None
) -> None:
    """Execute a device action."""
    service_data = {ATTR_DEVICE_ID: config[CONF_DEVICE_ID]}

    if config[CONF_TYPE] == "restart":
        service = SERVICE_RESTART

    await hass.services.async_call(
        DOMAIN, service, service_data, blocking=True, context=context
    )

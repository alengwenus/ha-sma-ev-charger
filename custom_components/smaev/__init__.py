"""The SMA EV Charger integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pysmaev.core
import pysmaev.exceptions

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import async_generate_entity_id, EntityDescription
from homeassistant.helpers.device_registry import DeviceInfo


from .const import (
    DOMAIN,
    SMAEV_CHANNELS,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_MEASUREMENT,
    SMAEV_OBJECT,
    SMAEV_PARAMETER,
)
from .coordinator import SmaEvChargerCoordinator
from .services import async_setup_services, async_unload_services


PLATFORMS: list[Platform] = [
    Platform.DATETIME,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMA EV Charger from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    protocol = "https" if entry.data[CONF_SSL] else "http"
    url = f"{protocol}://{entry.data[CONF_HOST]}"

    session = async_get_clientsession(hass, verify_ssl=entry.data[CONF_VERIFY_SSL])
    evcharger = pysmaev.core.SmaEvCharger(
        session, url, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    try:
        await evcharger.open()
        smaev_device_info = await evcharger.device_info()
    except pysmaev.exceptions.SmaEvChargerConnectionError as exc:
        raise ConfigEntryNotReady from exc
    except pysmaev.exceptions.SmaEvChargerAuthenticationError as exc:
        raise ConfigEntryAuthFailed from exc

    if TYPE_CHECKING:
        assert entry.unique_id

    device_info = DeviceInfo(
        configuration_url=url,
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer=smaev_device_info["manufacturer"],
        model=smaev_device_info["model"],
        name=smaev_device_info["name"],
        hw_version=smaev_device_info["serial"],
        sw_version=smaev_device_info["sw_version"],
    )

    measurement_channels = await evcharger.get_measurement_channels()
    parameter_channels = await evcharger.get_parameter_channels()

    coordinator = SmaEvChargerCoordinator(hass, entry, evcharger)

    hass.data[DOMAIN][entry.entry_id] = {
        SMAEV_OBJECT: evcharger,
        SMAEV_DEVICE_INFO: device_info,
        SMAEV_COORDINATOR: coordinator,
        SMAEV_CHANNELS: {
            SMAEV_MEASUREMENT: measurement_channels,
            SMAEV_PARAMETER: parameter_channels,
        },
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register Integration-wide Services:
    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        evcharger_data = hass.data[DOMAIN].pop(entry.entry_id)
        await evcharger_data[SMAEV_OBJECT].close()

    if not hass.data[DOMAIN]:
        async_unload_services(hass)

    return unload_ok


def generate_smaev_entity_id(
    hass: HomeAssistant,
    config_entry,
    entity_id_format: str,
    entity_description: EntityDescription,
    suffix: bool = True,
):
    """Generate a common formatted entity_id for SMA EV Charger entities."""
    device_info = hass.data[DOMAIN][config_entry.entry_id][SMAEV_DEVICE_INFO]
    return async_generate_entity_id(
        entity_id_format,
        "_".join(
            [
                *(
                    elem
                    for identifier in device_info["identifiers"]
                    for elem in identifier
                ),
                entity_description.key,
            ]
        ),
        current_ids=None if suffix else [],
        hass=hass,
    )

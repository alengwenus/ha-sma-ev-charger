"""The SMA EV Charger integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription, async_generate_entity_id

from .const import (
    DOMAIN,
    SMAEV_MEASUREMENT,
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


@dataclass
class SmaEvChargerRuntimeData:
    """Data for SMA EV Charger config entry."""

    evcharger: pysmaev.core.SmaEvCharger
    device_info: DeviceInfo
    coordinator: SmaEvChargerCoordinator
    channels: dict[str, list[str]]


type SmaEvChargerConfigEntry = ConfigEntry[SmaEvChargerRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: SmaEvChargerConfigEntry
) -> bool:
    """Set up SMA EV Charger from a config entry."""

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

    device_info = DeviceInfo(
        configuration_url=url,
        identifiers={(DOMAIN, smaev_device_info["serial"])},
        manufacturer=smaev_device_info["manufacturer"],
        model=smaev_device_info["model"],
        name=smaev_device_info["name"],
        hw_version=smaev_device_info["serial"],
        sw_version=smaev_device_info["sw_version"],
    )

    measurement_channels = await evcharger.get_measurement_channels()
    parameter_channels = await evcharger.get_parameter_channels()

    coordinator = SmaEvChargerCoordinator(hass, entry, evcharger)

    entry.runtime_data = SmaEvChargerRuntimeData(
        evcharger=evcharger,
        device_info=device_info,
        coordinator=coordinator,
        channels={
            SMAEV_MEASUREMENT: measurement_channels,
            SMAEV_PARAMETER: parameter_channels,
        },
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register Integration-wide Services:
    async_setup_services(hass)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SmaEvChargerConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.evcharger.close()

    if not hass.config_entries.async_loaded_entries(DOMAIN):
        # Unload services if there are no more config entries for this domain.
        async_unload_services(hass)

    return unload_ok


def generate_smaev_entity_id(
    hass: HomeAssistant,
    config_entry: SmaEvChargerConfigEntry,
    entity_id_format: str,
    entity_description: EntityDescription,
    suffix: bool = True,
) -> str:
    """Generate a common formatted entity_id for SMA EV Charger entities."""
    device_info = config_entry.runtime_data.device_info
    return async_generate_entity_id(
        entity_id_format,
        "_".join(
            [
                *(
                    elem
                    for identifier in device_info.get("identifiers", [])
                    for elem in identifier
                ),
                entity_description.key,
            ]
        ),
        current_ids=None if suffix else [],
        hass=hass,
    )

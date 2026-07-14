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
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
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


@callback
def _async_migrate_entity_unique_ids(
    hass: HomeAssistant,
    entry: SmaEvChargerConfigEntry,
    serial: str,
) -> None:
    """Migrate entity unique IDs from 'None-<key>' to '<serial>-<key>'.

    Affects entries that were created before the config flow set unique_id.
    """
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if not entity_entry.unique_id.startswith("None-"):
            continue
        new_unique_id = f"{serial}{entity_entry.unique_id[4:]}"
        # Skip if target unique_id is already in use
        if (
            entity_registry.async_get_entity_id(
                entity_entry.domain, entity_entry.platform, new_unique_id
            )
            is not None
        ):
            _LOGGER.warning(
                "Cannot migrate entity %s: unique_id '%s' already taken",
                entity_entry.entity_id,
                new_unique_id,
            )
            continue
        entity_registry.async_update_entity(
            entity_entry.entity_id, new_unique_id=new_unique_id
        )


async def async_migrate_entry(
    hass: HomeAssistant, entry: SmaEvChargerConfigEntry
) -> bool:
    """Migrate old config entries to the current version."""
    _LOGGER.debug(
        "Migrating config entry %s from version %s.%s",
        entry.entry_id,
        entry.version,
        entry.minor_version,
    )

    if entry.version == 1 and entry.minor_version < 1:
        # v1.0 → v1.1: set unique_id to device serial and migrate entity unique IDs
        protocol = "https" if entry.data[CONF_SSL] else "http"
        url = f"{protocol}://{entry.data[CONF_HOST]}"
        session = async_get_clientsession(hass, verify_ssl=entry.data[CONF_VERIFY_SSL])
        evcharger = pysmaev.core.SmaEvCharger(
            session, url, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
        try:
            await evcharger.open()
            device_info = await evcharger.device_info()
        except (
            pysmaev.exceptions.SmaEvChargerConnectionError,
            pysmaev.exceptions.SmaEvChargerAuthenticationError,
        ):
            _LOGGER.exception(
                "Migration of config entry %s failed: could not connect to device",
                entry.entry_id,
            )
            return False
        finally:
            await evcharger.close()

        serial: str = device_info["serial"]
        _async_migrate_entity_unique_ids(hass, entry, serial)
        hass.config_entries.async_update_entry(entry, unique_id=serial, minor_version=1)
        _LOGGER.debug(
            "Migration of config entry %s to version 1.1 successful (serial: %s)",
            entry.entry_id,
            serial,
        )

    return True


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

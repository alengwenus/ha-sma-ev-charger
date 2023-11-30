"""The SMA EV Charger integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from pysmaev.core import (
    SmaEvCharger,
    SmaEvChargerAuthenticationException,
    SmaEvChargerConnectionException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_MEASUREMENT,
    SMAEV_OBJECT,
    SMAEV_PARAMETER,
)

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
    evcharger = SmaEvCharger(
        session, url, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    try:
        await evcharger.open()
        smaev_device_info = await evcharger.device_info()
    except SmaEvChargerConnectionException as exc:
        raise ConfigEntryNotReady from exc
    except SmaEvChargerAuthenticationException as exc:
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

    coordinator = SmaEvChargerCoordinator(hass, entry, evcharger)

    hass.data[DOMAIN][entry.entry_id] = {
        SMAEV_OBJECT: evcharger,
        SMAEV_DEVICE_INFO: device_info,
        SMAEV_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        evcharger = hass.data[DOMAIN][entry.entry_id][SMAEV_OBJECT]
        await evcharger.close()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SmaEvChargerCoordinator(DataUpdateCoordinator):
    """SmaEvCharger coordinator."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, evcharger: SmaEvCharger
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass, _LOGGER, name="smaev", update_interval=timedelta(seconds=interval)
        )
        self.evcharger = evcharger

    async def _async_update_data(self):
        """Fetch data from SmaEvCharger."""
        data = {}
        try:
            data[SMAEV_MEASUREMENT] = await self.evcharger.request_measurements()
            data[SMAEV_PARAMETER] = await self.evcharger.request_parameters()
        except SmaEvChargerConnectionException as exc:
            raise UpdateFailed(exc) from exc

        if not all((data[SMAEV_MEASUREMENT], data[SMAEV_PARAMETER])):
            raise UpdateFailed("No valid data received.")

        return data

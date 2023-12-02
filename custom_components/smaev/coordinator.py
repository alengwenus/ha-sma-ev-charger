"""DataUpdateCoordinator for the SMA EV Charger integration."""
from datetime import timedelta
import logging

from pysmaev.core import (
    SmaEvCharger,
    SmaEvChargerConnectionException,
    SmaEvChargerAuthenticationException
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    SMAEV_MEASUREMENT,
    SMAEV_PARAMETER,
    SMAEV_COORDINATOR,
)


_LOGGER = logging.getLogger(__name__)


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
        if self.evcharger.is_closed:
            try:
                await self.evcharger.open()
            except SmaEvChargerConnectionException:
                raise UpdateFailed("Connection to device lost.")
            except SmaEvChargerAuthenticationException as exc:
                raise ConfigEntryAuthFailed from exc


        data = {}
        try:
            data[SMAEV_MEASUREMENT] = await self.evcharger.request_measurements()
            data[SMAEV_PARAMETER] = await self.evcharger.request_parameters()
        except SmaEvChargerConnectionException as exc:
            raise UpdateFailed(exc) from exc

        if not all((data[SMAEV_MEASUREMENT], data[SMAEV_PARAMETER])):
            raise UpdateFailed("No valid data received.")

        return data


@callback
def async_get_coordinator_by_device_id(
    hass: HomeAssistant, device_id: str
) -> SmaEvChargerCoordinator:
    """Get the LaMetric coordinator for this device ID."""
    device_registry = dr.async_get(hass)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ValueError(f"Unknown SMA EV Charger device ID: {device_id}")

    for entry_id in device_entry.config_entries:
        if (
            (entry := hass.config_entries.async_get_entry(entry_id))
            and entry.domain == DOMAIN
            and entry.entry_id in hass.data[DOMAIN]
        ):
            coordinator: SmaEvChargerCoordinator = hass.data[DOMAIN][entry.entry_id][
                SMAEV_COORDINATOR
            ]
            return coordinator

    raise ValueError(f"No coordinator for device ID: {device_id}")

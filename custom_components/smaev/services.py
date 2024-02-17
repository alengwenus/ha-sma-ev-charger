"""Service calls for SMA EV Charger."""
import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from pysmaev.const import SmaEvChargerParameters

from .const import DOMAIN, SERVICE_RESTART
from .coordinator import async_get_coordinator_by_device_id

SERVICE_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)

SERVICE_RESTART_SCHEMA = SERVICE_BASE_SCHEMA


@callback
def async_setup_services(hass: HomeAssistant) -> bool:
    """Set up services for the SMA EV Charger integration."""

    async def _async_service_reset(call: ServiceCall) -> None:
        """Reset SMA EV Charger device."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )
        evcharger = coordinator.evcharger
        channel = "Parameter.Sys.DevRstr"
        await evcharger.set_parameter(SmaEvChargerParameters.EXECUTE, channel)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART,
        _async_service_reset,
        schema=SERVICE_RESTART_SCHEMA,
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for the SMA EV Charger integration."""
    if hass.data[DOMAIN]:
        # There is still another config entry for this domain, don't remove services.
        return

    existing_services = hass.services.async_services().get(DOMAIN)
    if not existing_services or SERVICE_RESTART not in existing_services:
        return

    hass.services.async_remove(domain=DOMAIN, service=SERVICE_RESTART)

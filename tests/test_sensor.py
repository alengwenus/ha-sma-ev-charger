"""Test for the SMA EV Charger sensor platform."""

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.sensor import ENTITY_ID_FORMAT, SENSOR_DESCRIPTIONS


async def test_setup_smaev_sensor(hass: HomeAssistant, entry, evcharger):
    """Test the setup of sensor."""
    for description in SENSOR_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state
        assert state.state == STATE_UNKNOWN
        assert (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == description.native_unit_of_measurement
        )
        assert state.attributes.get(ATTR_DEVICE_CLASS) == description.device_class

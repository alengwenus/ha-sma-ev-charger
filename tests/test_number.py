"""Test for the SMA EV Charger number platform."""
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.number import ENTITY_ID_FORMAT, NUMBER_DESCRIPTIONS


async def test_setup_smaev_number(hass: HomeAssistant, entry, evcharger):
    """Test the setup of number."""
    for description in NUMBER_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN
        assert (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == description.native_unit_of_measurement
        )
        assert state.attributes.get(ATTR_DEVICE_CLASS) == description.device_class

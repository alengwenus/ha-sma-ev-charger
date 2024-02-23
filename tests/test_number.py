"""Test for the SMA EV Charger number platform."""
from functools import partial

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from custom_components.smaev.number import ENTITY_ID_FORMAT, NUMBER_DESCRIPTIONS

from .conftest import get_entity_ids_and_descriptions

entity_items = partial(
    get_entity_ids_and_descriptions,
    entity_id_format=ENTITY_ID_FORMAT,
    entity_descriptions=NUMBER_DESCRIPTIONS,
)


async def test_setup_smaev_number(hass: HomeAssistant, entry, evcharger):
    """Test the setup of number."""
    for entity_id, description in entity_items(hass, entry):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN
        assert (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == description.native_unit_of_measurement
        )
        assert state.attributes.get(ATTR_DEVICE_CLASS) == description.device_class

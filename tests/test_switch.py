"""Test for the SMA EV Charger switch platform."""
from functools import partial

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev.switch import ENTITY_ID_FORMAT, SWITCH_DESCRIPTIONS

from .conftest import get_entity_ids_and_descriptions

entity_items = partial(
    get_entity_ids_and_descriptions,
    entity_id_format=ENTITY_ID_FORMAT,
    entity_descriptions=SWITCH_DESCRIPTIONS,
)


async def test_setup_smaev_switch(hass: HomeAssistant, entry, evcharger):
    """Test the setup of switch."""
    for entity_id, _ in entity_items(hass, entry):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

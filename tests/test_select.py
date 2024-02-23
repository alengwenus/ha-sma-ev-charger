"""Test for the SMA EV Charger select platform."""
from functools import partial

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev.select import ENTITY_ID_FORMAT, SELECT_DESCRIPTIONS

from .conftest import get_entity_ids_and_descriptions

entity_items = partial(
    get_entity_ids_and_descriptions,
    entity_id_format=ENTITY_ID_FORMAT,
    entity_descriptions=SELECT_DESCRIPTIONS,
)


async def test_setup_smaev_select(hass: HomeAssistant, entry, evcharger):
    """Test the setup of select."""
    for entity_id, _ in entity_items(hass, entry):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

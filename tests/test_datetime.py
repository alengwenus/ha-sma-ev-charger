"""Test for the SMA EV Charger datetime platform."""
from functools import partial

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev.datetime import DATETIME_DESCRIPTIONS, ENTITY_ID_FORMAT

from .conftest import get_entity_ids_and_descriptions

entity_items = partial(
    get_entity_ids_and_descriptions,
    entity_id_format=ENTITY_ID_FORMAT,
    entity_descriptions=DATETIME_DESCRIPTIONS,
)


async def test_setup_smaev_datetime(hass: HomeAssistant, entry, evcharger):
    """Test the setup of datetime."""
    for entity_id, _ in entity_items(hass, entry):
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

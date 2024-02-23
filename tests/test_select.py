"""Test for the SMA EV Charger select platform."""
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.select import ENTITY_ID_FORMAT, SELECT_DESCRIPTIONS


async def test_setup_smaev_select(hass: HomeAssistant, entry, evcharger):
    """Test the setup of select."""
    for description in SELECT_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

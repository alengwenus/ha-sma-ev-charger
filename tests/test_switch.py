"""Test for the SMA EV Charger switch platform."""
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.switch import ENTITY_ID_FORMAT, SWITCH_DESCRIPTIONS


async def test_setup_smaev_switch(hass: HomeAssistant, entry, evcharger):
    """Test the setup of switch."""
    for description in SWITCH_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

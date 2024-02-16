"""Test for the SMA EV Charger datetime platform."""
from unittest.mock import patch

import pysmaev.core

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.datetime import DATETIME_DESCRIPTIONS, ENTITY_ID_FORMAT

from .conftest import MockSmaEvCharger


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_setup_smaev_datetime(hass: HomeAssistant, entry):
    """Test the setup of datetime."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for description in DATETIME_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

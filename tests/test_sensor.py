"""Test for the SMA EV Charger sensor platform."""
from unittest.mock import patch

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.sensor import SENSOR_DESCRIPTIONS, ENTITY_ID_FORMAT


async def test_setup_smaev_sensor(hass: HomeAssistant, entry, device_info):
    """Test the setup of sensor."""
    entry.add_to_hass(hass)
    with (
        patch("pysmaev.core.SmaEvCharger.open"),
        patch("pysmaev.core.SmaEvCharger.device_info", return_value=device_info),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    for description in SENSOR_DESCRIPTIONS:
        if not description.entity_registry_enabled_default:
            continue
        entity_id = generate_smaev_entity_id(
            hass, entry, ENTITY_ID_FORMAT, description, suffix=False
        )

        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

"""Test for the SMA EV Charger sensor platform."""
from datetime import timedelta
from functools import partial

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.smaev.const import DEFAULT_SCAN_INTERVAL
from custom_components.smaev.sensor import ENTITY_ID_FORMAT, SENSOR_DESCRIPTIONS

from .conftest import get_entity_ids_and_descriptions

entity_items = partial(
    get_entity_ids_and_descriptions,
    entity_id_format=ENTITY_ID_FORMAT,
    entity_descriptions=SENSOR_DESCRIPTIONS,
)


async def test_setup_smaev_sensor(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the setup of sensor."""
    for entity_id, description in entity_items(hass, entry):
        state = hass.states.get(entity_id)
        assert state
        assert state.state == STATE_UNKNOWN
        assert (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == description.native_unit_of_measurement
        )
        assert state.attributes.get(ATTR_DEVICE_CLASS) == description.device_class


async def test_entity_attributes(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, entry, evcharger
) -> None:
    """Test the attributes of an entity."""
    for entity_id, description in entity_items(hass, entry):
        entity = entity_registry.async_get(entity_id)
        assert entity
        assert entity.unique_id == f"{entry.unique_id}-{description.key}"


async def test_status_change(
    hass: HomeAssistant, entry, evcharger, channel_values
) -> None:
    """Test sensor changes its state on coordinator update."""
    # Make the coordinator refresh data.
    async_fire_time_changed(
        hass, utcnow() + timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1)
    )
    await hass.async_block_till_done()

    for entity_id, description in entity_items(hass, entry):
        value = channel_values[description.channel]
        value = description.value_mapping.get(value, value)

        state = hass.states.get(entity_id)
        assert state.state == str(value)


async def test_unload_config_entry(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the sensor is removed when the config entry is unloaded."""
    items = entity_items(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)

    for entity_id, _ in items:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

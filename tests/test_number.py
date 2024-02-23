"""Test for the SMA EV Charger number platform."""
from functools import partial

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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


async def test_entity_attributes(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, entry, evcharger
) -> None:
    """Test the attributes of an entity."""
    for entity_id, description in entity_items(hass, entry):
        entity = entity_registry.async_get(entity_id)
        assert entity
        assert entity.unique_id == f"{entry.unique_id}-{description.key}"


async def test_unload_config_entry(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the number is removed when the config entry is unloaded."""
    items = entity_items(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)

    for entity_id, _ in items:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

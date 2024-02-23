"""Test for the SMA EV Charger select platform."""
from functools import partial

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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


async def test_entity_attributes(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, entry, evcharger
) -> None:
    """Test the attributes of an entity."""
    for entity_id, description in entity_items(hass, entry):
        entity = entity_registry.async_get(entity_id)
        assert entity
        assert entity.unique_id == f"{entry.unique_id}-{description.key}"


async def test_unload_config_entry(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the select is removed when the config entry is unloaded."""
    items = entity_items(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)

    for entity_id, _ in items:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

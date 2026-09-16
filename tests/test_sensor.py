"""Test for the SMA EV Charger sensor platform."""

import logging
from datetime import timedelta

import pytest
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

from custom_components.smaev import generate_smaev_entity_id
from custom_components.smaev.const import DEFAULT_SCAN_INTERVAL, SMAEV_MEASUREMENT
from custom_components.smaev.sensor import (
    ENTITY_ID_FORMAT,
    SENSOR_DESCRIPTIONS,
    async_setup_entry,
)


def get_entity_ids_and_descriptions(hass, entry) -> tuple:
    """Return a list with (entity_id, entity_description)."""
    items = [
        (
            generate_smaev_entity_id(
                hass, entry, ENTITY_ID_FORMAT, description, suffix=False
            ),
            description,
        )
        for description in SENSOR_DESCRIPTIONS
        if description.entity_registry_enabled_default
    ]
    return items


async def test_setup_smaev_sensor(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the setup of sensor."""
    for entity_id, description in get_entity_ids_and_descriptions(hass, entry):
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
    for entity_id, description in get_entity_ids_and_descriptions(hass, entry):
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

    for entity_id, description in get_entity_ids_and_descriptions(hass, entry):
        value = channel_values[description.channel]
        value = description.value_mapping.get(value, value)

        state = hass.states.get(entity_id)
        assert state.state == str(value)


async def test_unload_config_entry(hass: HomeAssistant, entry, evcharger) -> None:
    """Test the sensor is removed when the config entry is unloaded."""
    items = get_entity_ids_and_descriptions(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)

    for entity_id, _ in items:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("missing_channel", "missing_key", "expected_level"),
    [
        ("Measurement.GridMs.Hz", "grid_frequency", logging.DEBUG),
        (
            "Measurement.Metering.GridMs.TotWIn.ChaSta",
            "charging_station_power",
            logging.WARNING,
        ),
        (None, None, None),
    ],
)
async def test_optional_channel_logging(
    hass: HomeAssistant,
    entry,
    evcharger,
    caplog: pytest.LogCaptureFixture,
    missing_channel,
    missing_key,
    expected_level,
) -> None:
    """Only an explicitly optional missing channel is logged at DEBUG."""
    if missing_channel is not None:
        entry.runtime_data.channels[SMAEV_MEASUREMENT].remove(missing_channel)

    caplog.clear()
    entities = []
    with caplog.at_level(logging.DEBUG, logger="custom_components.smaev.sensor"):
        await async_setup_entry(hass, entry, entities.extend)

    assert {entity.entity_description.key for entity in entities} == {
        description.key
        for description in SENSOR_DESCRIPTIONS
        if description.key != missing_key
    }
    records = [
        record
        for record in caplog.records
        if record.name == "custom_components.smaev.sensor"
    ]
    if missing_channel is None:
        assert not records
    else:
        assert len(records) == 1
        assert records[0].levelno == expected_level
        assert missing_channel in records[0].getMessage()
        if expected_level == logging.DEBUG:
            assert "Elevated rights" not in records[0].getMessage()

    if missing_key != "grid_frequency":
        frequency = next(
            entity
            for entity in entities
            if entity.entity_description.key == "grid_frequency"
        )
        assert not frequency.entity_description.entity_registry_enabled_default

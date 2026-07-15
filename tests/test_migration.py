"""Tests for SMA EV Charger config entry migration."""

from unittest.mock import patch

import pysmaev.core
import pysmaev.exceptions
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import smaev

from .conftest import CONFIG_DATA, DEVICE_INFO, MockSmaEvCharger

SERIAL = DEVICE_INFO["serial"]


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_migration_v1_0_to_v1_1(
    hass: HomeAssistant, entry1_0: MockConfigEntry
) -> None:
    """A v1.0 entry is migrated: unique_id set, entity unique IDs updated."""
    entry1_0.add_to_hass(hass)

    # Pre-populate entity registry with the old "None-<key>" unique IDs
    entity_registry = er.async_get(hass)
    old_unique_id = f"{None}-charging_session_energy"
    entity_entry = entity_registry.async_get_or_create(
        "sensor",
        smaev.DOMAIN,
        old_unique_id,
        config_entry=entry1_0,
    )

    assert await hass.config_entries.async_setup(entry1_0.entry_id)
    await hass.async_block_till_done()

    assert entry1_0.state == ConfigEntryState.LOADED

    # Config entry must now carry the serial as unique_id
    assert entry1_0.unique_id == SERIAL
    assert entry1_0.minor_version == 1

    # Entity unique ID must have been rewritten
    migrated = entity_registry.async_get(entity_entry.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{SERIAL}-charging_session_energy"

    # The old unique ID must no longer exist
    assert (
        entity_registry.async_get_entity_id("sensor", smaev.DOMAIN, old_unique_id)
        is None
    )


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_migration_v1_0_skips_already_migrated_entities(
    hass: HomeAssistant, entry1_0: MockConfigEntry
) -> None:
    """Entities that don't start with 'None-' are left untouched."""
    entry1_0.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    already_correct_unique_id = f"{SERIAL}-charging_session_energy"
    entity_entry = entity_registry.async_get_or_create(
        "sensor",
        smaev.DOMAIN,
        already_correct_unique_id,
        config_entry=entry1_0,
    )

    assert await hass.config_entries.async_setup(entry1_0.entry_id)
    await hass.async_block_till_done()

    assert entry1_0.state == ConfigEntryState.LOADED
    assert entry1_0.unique_id == SERIAL

    # Entity with already-correct unique ID must remain unchanged
    unchanged = entity_registry.async_get(entity_entry.entity_id)
    assert unchanged is not None
    assert unchanged.unique_id == already_correct_unique_id


@pytest.mark.parametrize(
    "error",
    [
        pysmaev.exceptions.SmaEvChargerConnectionError,
        pysmaev.exceptions.SmaEvChargerAuthenticationError,
    ],
)
async def test_migration_v1_0_connection_failure(
    hass: HomeAssistant, entry1_0: MockConfigEntry, error: type[Exception]
) -> None:
    """Migration returns False and entry is not loaded when device is unreachable."""
    entry1_0.add_to_hass(hass)

    with patch.object(pysmaev.core.SmaEvCharger, "open", side_effect=error):
        assert not await hass.config_entries.async_setup(entry1_0.entry_id)
        await hass.async_block_till_done()

    assert entry1_0.state == ConfigEntryState.MIGRATION_ERROR
    # unique_id must remain None — migration was not completed
    assert entry1_0.unique_id is None
    assert entry1_0.minor_version == 0


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_migration_v1_0_collision_skipped(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture, entry1_0: MockConfigEntry
) -> None:
    """An entity whose target unique_id is already taken is skipped with a warning."""
    entry1_0.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Entity to migrate
    old_entity = entity_registry.async_get_or_create(
        "sensor",
        smaev.DOMAIN,
        "None-charging_session_energy",
        config_entry=entry1_0,
    )
    # Blocker: another entry already owns the target unique_id
    other_entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title="other",
        unique_id=SERIAL,
        version=1,
        minor_version=1,
        data={**CONFIG_DATA, "host": "10.0.0.2"},
        options={},
    )
    other_entry.add_to_hass(hass)
    entity_registry.async_get_or_create(
        "sensor",
        smaev.DOMAIN,
        f"{SERIAL}-charging_session_energy",
        config_entry=other_entry,
    )

    assert await hass.config_entries.async_setup(entry1_0.entry_id)
    await hass.async_block_till_done()

    assert entry1_0.state == ConfigEntryState.LOADED
    assert entry1_0.unique_id == SERIAL

    # The old entity must still have its original unique_id (could not be migrated)
    not_migrated = entity_registry.async_get(old_entity.entity_id)
    assert not_migrated is not None
    assert not_migrated.unique_id == "None-charging_session_energy"

    # A warning must have been logged
    assert "already taken" in caplog.text


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_migration_not_triggered_for_v1_1_entry(hass: HomeAssistant) -> None:
    """A v1.1 entry does not trigger migration."""
    entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title=CONFIG_DATA["host"],
        unique_id=SERIAL,
        version=1,
        minor_version=1,
        data=CONFIG_DATA,
        options={},
    )
    entry.add_to_hass(hass)

    with patch.object(
        smaev, "async_migrate_entry", wraps=smaev.async_migrate_entry
    ) as mock_migrate:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_migrate.assert_not_called()
    assert entry.state == ConfigEntryState.LOADED
    assert entry.unique_id == SERIAL

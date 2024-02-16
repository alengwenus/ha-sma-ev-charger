"""Test init of SMA EV Charger integration."""
import pytest
from unittest.mock import patch

import pysmaev.core
import pysmaev.exceptions

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from custom_components import smaev

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import CONFIG_DATA, MockSmaEvCharger


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_async_setup_entry(hass: HomeAssistant, entry) -> None:
    """Test a successful setup entry and unload of entry."""
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(smaev.DOMAIN)) == 1
    assert entry.state == ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.data.get(smaev.DOMAIN)


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_async_setup_multiple_entries(hass: HomeAssistant) -> None:
    """Test a successful setup entry and unload of entry."""
    entries = [
        MockConfigEntry(
            domain=smaev.DOMAIN,
            title=host,
            unique_id=f"123456789{idx}",
            data={**CONFIG_DATA, "host": host},
            options={},
        )
        for idx, host in enumerate(("192.168.2.100", "192.168.2.101"))
    ]

    for entry in entries:
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.LOADED

    assert len(hass.config_entries.async_entries(smaev.DOMAIN)) == 2

    for entry in entries:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.NOT_LOADED

    assert not hass.data.get(smaev.DOMAIN)


@pytest.mark.parametrize(
    "error",
    [
        pysmaev.exceptions.SmaEvChargerConnectionError,
        pysmaev.exceptions.SmaEvChargerAuthenticationError,
    ],
)
async def test_async_setup_entry_raises_error(
    hass: HomeAssistant, entry, error
) -> None:
    """Test that an authentication error is handled properly."""
    entry.add_to_hass(hass)

    with patch.object(pysmaev.core.SmaEvCharger, "open", side_effekt=error):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_ERROR

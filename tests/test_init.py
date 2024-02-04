"""Test init of SMA EV Charger integration."""
import pytest
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST
from homeassistant.config_entries import ConfigEntryState
from custom_components import smaev

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import CONFIG_DATA


async def test_async_setup_entry(hass: HomeAssistant, device_info) -> None:
    """Test a successful setup entry and unload of entry."""
    entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title=CONFIG_DATA[CONF_HOST],
        unique_id="1234567890",
        data=CONFIG_DATA,
        options={},
    )

    entry.add_to_hass(hass)
    with (
        patch("pysmaev.core.SmaEvCharger.open"),
        patch("pysmaev.core.SmaEvCharger.device_info", return_value=device_info),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.config_entries.async_entries(smaev.DOMAIN)) == 1
    assert entry.state == ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.data.get(smaev.DOMAIN)


async def test_async_setup_multiple_entries(hass: HomeAssistant, device_info) -> None:
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

    with (
        patch("pysmaev.core.SmaEvCharger.open"),
        patch("pysmaev.core.SmaEvCharger.device_info", return_value=device_info),
    ):
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
    "error", [smaev.SmaEvChargerConnectionError, smaev.SmaEvChargerAuthenticationError]
)
async def test_async_setup_entry_raises_error(hass: HomeAssistant, error) -> None:
    """Test that an authentication error is handled properly."""
    entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title=CONFIG_DATA[CONF_HOST],
        unique_id="1234567890",
        data=CONFIG_DATA,
        options={},
    )
    with patch.object(smaev.SmaEvCharger, "open", side_effekt=error):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_ERROR

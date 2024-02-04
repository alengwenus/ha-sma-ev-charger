"""Test init of SMA EV Charger integration."""
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST
from homeassistant.config_entries import ConfigEntryState
from custom_components import smaev

from pytest_homeassistant_custom_component.common import MockConfigEntry


CONFIG_DATA = {
    "host": "192.168.2.100",
    "username": "Test",
    "password": "Tester1234&",
    "ssl": True,
    "verify_ssl": False,
}


async def test_async_setup_entry(hass: HomeAssistant, device_info) -> None:
    """Test a successful setup entry and unload of entry."""
    entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title=CONFIG_DATA[CONF_HOST],
        unique_id="serial",
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

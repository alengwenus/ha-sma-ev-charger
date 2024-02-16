"""Tests for the SMA EV Charger config flow."""
from unittest.mock import patch

import pytest

import pysmaev.core
import pysmaev.exceptions

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_BASE
from homeassistant.core import HomeAssistant

from custom_components import smaev
from custom_components.smaev.config_flow import SmaEvChargerConfigFlow, validate_input

from .conftest import CONFIG_DATA, MockSmaEvCharger, DEVICE_INFO


async def test_show_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    flow = SmaEvChargerConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_step_user(hass):
    """Test for user step."""
    data = CONFIG_DATA.copy()
    result = await hass.config_entries.flow.async_init(
        smaev.DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == CONFIG_DATA[CONF_HOST]
    assert result["data"] == CONFIG_DATA


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_step_user_existing_host(hass, entry):
    """Test for user defined host already exists."""
    entry.add_to_hass(hass)

    data = entry.data.copy()
    result = await hass.config_entries.flow.async_init(
        smaev.DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("error", "errors"),
    [
        (pysmaev.exceptions.SmaEvChargerConnectionError, {CONF_BASE: "cannot_connect"}),
        (
            pysmaev.exceptions.SmaEvChargerAuthenticationError,
            {CONF_BASE: "invalid_auth"},
        ),
        (Exception, {CONF_BASE: "unknown"}),
    ],
)
async def test_step_user_error(hass, error, errors):
    """Test for error in user step is handled correctly."""
    with patch("pysmaev.core.SmaEvCharger.open", side_effect=error):
        data = CONFIG_DATA.copy()
        result = await hass.config_entries.flow.async_init(
            smaev.DOMAIN, context={"source": config_entries.SOURCE_USER}, data=data
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == errors


@patch.object(pysmaev.core, "SmaEvCharger", MockSmaEvCharger)
async def test_options_flow(hass, entry):
    """Test config flow options."""
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    user_input = CONFIG_DATA.copy()

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert all(value == entry.data[key] for key, value in user_input.items())


@pytest.mark.parametrize(
    ("error", "errors"),
    [
        (pysmaev.exceptions.SmaEvChargerConnectionError, {CONF_BASE: "cannot_connect"}),
        (
            pysmaev.exceptions.SmaEvChargerAuthenticationError,
            {CONF_BASE: "invalid_auth"},
        ),
        (Exception, {CONF_BASE: "unknown"}),
    ],
)
async def test_options_flow_errors(hass, entry, error, errors):
    """Test config flow options."""
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    user_input = CONFIG_DATA.copy()

    with patch("pysmaev.core.SmaEvCharger.open", side_effect=error):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == errors


async def test_validate_connection(hass: HomeAssistant):
    """Test the connection validation."""
    data = CONFIG_DATA.copy()

    with patch("pysmaev.core.SmaEvCharger", MockSmaEvCharger) as mock:
        result = await validate_input(hass, data=data)

    assert mock.open.is_called
    assert mock.device_info.is_called
    assert result == (DEVICE_INFO, {})


@pytest.mark.parametrize(
    ("error", "errors"),
    [
        (pysmaev.exceptions.SmaEvChargerConnectionError, {CONF_BASE: "cannot_connect"}),
        (
            pysmaev.exceptions.SmaEvChargerAuthenticationError,
            {CONF_BASE: "invalid_auth"},
        ),
        (Exception, {CONF_BASE: "unknown"}),
    ],
)
async def test_validate_connection_raises_error(hass: HomeAssistant, error, errors):
    """Test the connection validation."""
    data = CONFIG_DATA.copy()

    with patch("pysmaev.core.SmaEvCharger.open", side_effect=error):
        result = await validate_input(hass, data=data)

    assert result == ({}, errors)

"""Fixtures for testing."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pysmaev.core
import pytest
from homeassistant.const import CONF_HOST

from custom_components import smaev

# Tests in the dev enviromentment use the pytest_homeassistant_custom_component instead of
# a cloned HA core repo for a simple and clean structure. To still test against a HA core
# clone (e.g. the dev branch for which no pytest_homeassistant_custom_component exists
# because HA does not publish dev snapshot packages), set the HA_CLONE env variable.
if "HA_CLONE" in os.environ:
    # Rewire the testing package to the cloned test modules. See the test `Dockerfile`
    # for setup details.
    sys.modules["pytest_homeassistant_custom_component"] = __import__("tests")

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable use of custom_components."""
    yield


CONFIG_DATA = {
    "host": "192.168.2.100",
    "username": "Test",
    "password": "Tester1234&",
    "ssl": True,
    "verify_ssl": False,
}


DEVICE_INFO = {
    "name": "SMA EV Charger 22",
    "serial": "1234567890",
    "model": "EVC22-3AC-10",
    "manufacturer": "SMA",
    "sw_version": "1.2.23.R",
}


MEASUREMENTS = json.loads(
    (Path(__file__).parent / Path("fixtures/measurements.json")).read_text()
)
PARAMETERS = json.loads(
    (Path(__file__).parent / Path("fixtures/parameters.json")).read_text()
)


class MockSmaEvCharger(pysmaev.core.SmaEvCharger):
    """Mocked SmaEvCharger."""

    open = AsyncMock()
    request_measurements = AsyncMock(return_value=MEASUREMENTS)
    request_parameters = AsyncMock(return_value=PARAMETERS)

    device_info = AsyncMock(return_value=DEVICE_INFO)


@pytest.fixture(name="entry")
def create_entry():
    """Return mock entry."""
    entry = MockConfigEntry(
        domain=smaev.DOMAIN,
        title=CONFIG_DATA[CONF_HOST],
        unique_id="1234567890",
        data=CONFIG_DATA,
        options={},
    )
    return entry

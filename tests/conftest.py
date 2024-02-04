"""Fixtures for testing."""
import os
import sys

import pytest

# Tests in the dev enviromentment use the pytest_homeassistant_custom_component instead of
# a cloned HA core repo for a simple and clean structure. To still test against a HA core
# clone (e.g. the dev branch for which no pytest_homeassistant_custom_component exists
# because HA does not publish dev snapshot packages), set the HA_CLONE env variable.
if "HA_CLONE" in os.environ:
    # Rewire the testing package to the cloned test modules. See the test `Dockerfile`
    # for setup details.
    sys.modules["pytest_homeassistant_custom_component"] = __import__("tests")


@pytest.fixture(name="device_info")
def device_info():
    """Return device info."""
    return {
        "name": "SMA EV Charger 22",
        "serial": "1234567890",
        "model": "EVC22-3AC-10",
        "manufacturer": "SMA",
        "sw_version": "1.2.23.R",
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable use of custom_components."""
    yield

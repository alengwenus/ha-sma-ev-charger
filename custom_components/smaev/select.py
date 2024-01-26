"""Select platform for SMA EV Charger integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import TYPE_CHECKING

from pysmaev.const import SmaEvChargerParameters
from pysmaev.exceptions import SmaEvChargerChannelError
from pysmaev.helpers import get_parameters_channel

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_PARAMETER,
    SMAEV_POSSIBLE_VALUES,
    SMAEV_VALUE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmaEvChargerSelectEntityDescription(SelectEntityDescription):
    """Describes SMA EV Charger select entities."""

    type: str = ""
    channel: str = ""
    value_mapping: dict = field(default_factory=dict)


SELECT_DESCRIPTIONS: tuple[SmaEvChargerSelectEntityDescription, ...] = (
    SmaEvChargerSelectEntityDescription(
        key="operating_mode_of_charge_session",
        translation_key="operating_mode_of_charge_session",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.ActChaMod",
        value_mapping={
            SmaEvChargerParameters.BOOST_CHARGING: "boost_charging",
            SmaEvChargerParameters.OPTIMIZED_CHARGING: "optimized_charging",
            SmaEvChargerParameters.SETPOINT_CHARGING: "setpoint_charging",
            SmaEvChargerParameters.CHARGE_STOP: "charge_stop",
        },
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSelectEntityDescription(
        key="led_brightness",
        translation_key="led_brightness",
        type=SMAEV_PARAMETER,
        channel="Parameter.Sys.DevSigBri",
        value_mapping={
            SmaEvChargerParameters.LED_LOW: "low",
            SmaEvChargerParameters.LED_AVERAGE: "average",
            SmaEvChargerParameters.LED_HIGH: "high",
        },
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA EV Charger select entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = data[SMAEV_COORDINATOR]
    device_info = data[SMAEV_DEVICE_INFO]

    if TYPE_CHECKING:
        assert config_entry.unique_id

    entities = []

    for entity_description in SELECT_DESCRIPTIONS:
        entities.append(
            SmaEvChargerSelect(
                coordinator, config_entry.unique_id, device_info, entity_description
            )
        )

    async_add_entities(entities)


class SmaEvChargerSelect(CoordinatorEntity, SelectEntity):
    """Representation of a SMA EV Charger select entity."""

    entity_description: SmaEvChargerSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_unique_id: str,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerSelectEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry_unique_id}-{self.entity_description.key}"
        self._attr_options = []
        self._attr_current_option = None

        self.inv_value_mapping = {
            value: key for key, value in self.entity_description.value_mapping.items()
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            channel = get_parameters_channel(
                self.coordinator.data[SMAEV_PARAMETER],
                self.entity_description.channel,
            )
        except SmaEvChargerChannelError:
            return

        possible_values = channel[SMAEV_POSSIBLE_VALUES]
        value = channel[SMAEV_VALUE]
        options = [
            self.entity_description.value_mapping[possible_value]
            for possible_value in possible_values
        ]
        if options != self._attr_options:
            self._attr_options = options
            async_call_later(self.hass, 0, self.force_refresh)
        else:
            self._attr_current_option = self.entity_description.value_mapping[value]
        super()._handle_coordinator_update()

    def force_refresh(self, _: datetime):
        """Call coordinator update handle."""
        self._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        """Update to the EV charger."""
        evcharger = self.coordinator.evcharger
        await evcharger.set_parameter(
            self.inv_value_mapping[option],
            self.entity_description.channel,
        )
        await self.coordinator.async_request_refresh()

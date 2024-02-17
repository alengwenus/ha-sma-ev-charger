"""Select platform for SMA EV Charger integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.components.select import (
    ENTITY_ID_FORMAT,
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from pysmaev.const import SmaEvChargerParameters
from pysmaev.helpers import get_parameters_channel

from . import generate_smaev_entity_id
from .const import (
    DOMAIN,
    SMAEV_CHANNELS,
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
        if entity_description.channel in data[SMAEV_CHANNELS][entity_description.type]:
            entities.append(
                SmaEvChargerSelect(
                    hass, coordinator, config_entry, device_info, entity_description
                )
            )
        else:
            _LOGGER.warning(
                "Channel '%s' is not accessible. Elevated rights might be required.",
                entity_description.channel,
            )

    async_add_entities(entities)


class SmaEvChargerSelect(CoordinatorEntity, SelectEntity):
    """Representation of a SMA EV Charger select entity."""

    entity_description: SmaEvChargerSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerSelectEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = (hass,)
        self.config_entry = config_entry
        self.entity_description = entity_description
        self.entity_id = generate_smaev_entity_id(
            hass, config_entry, ENTITY_ID_FORMAT, entity_description
        )

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry.unique_id}-{self.entity_description.key}"
        self._attr_options = []
        self._attr_current_option = None

        self.inv_value_mapping = {
            value: key for key, value in self.entity_description.value_mapping.items()
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        channel = get_parameters_channel(
            self.coordinator.data[SMAEV_PARAMETER],
            self.entity_description.channel,
        )

        possible_values = channel[SMAEV_POSSIBLE_VALUES]
        value = channel[SMAEV_VALUE]
        options = [
            self.entity_description.value_mapping[possible_value]
            for possible_value in possible_values
        ]
        if options != self._attr_options:
            self._attr_options = options
            self.hass.async_create_task(self.force_refresh())
        else:
            self._attr_current_option = self.entity_description.value_mapping[value]
        super()._handle_coordinator_update()

    async def force_refresh(self):
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

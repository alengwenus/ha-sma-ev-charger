"""Switch platform for SMA EV Charger integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any

from pysmaev.const import SmaEvChargerParameters
from pysmaev.exceptions import SmaEvChargerChannelError
from pysmaev.helpers import get_parameters_channel

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_PARAMETER,
    SMAEV_VALUE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmaEvChargerSwitchEntityDescription(SwitchEntityDescription):
    """Describes SMA EV Charger switch entities."""

    type: str = ""
    channel: str = ""
    value_mapping: dict = field(default_factory=dict)


SWITCH_DESCRIPTIONS: tuple[SmaEvChargerSwitchEntityDescription, ...] = (
    SmaEvChargerSwitchEntityDescription(
        key="manual_charging_release",
        translation_key="manual_charging_release",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.ChrgApv",
        value_mapping={
            SmaEvChargerParameters.CHARGING_LOCK: False,
            SmaEvChargerParameters.CHARGING_RELEASE: True,
        },
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSwitchEntityDescription(
        key="full_charge_disconnect",
        translation_key="full_charge_disconnect",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.StpWhenFl",
        value_mapping={
            SmaEvChargerParameters.YES: True,
            SmaEvChargerParameters.NO: False,
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

    for entity_description in SWITCH_DESCRIPTIONS:
        entities.append(
            SmaEvChargerSwitch(
                hass, coordinator, config_entry, device_info, entity_description
            )
        )

    async_add_entities(entities)


class SmaEvChargerSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a SMA EV Charger switch entity."""

    entity_description: SmaEvChargerSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerSwitchEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entity_description = entity_description
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_description.key, hass=hass
        )

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry.unique_id}-{self.entity_description.key}"
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

        value = channel[SMAEV_VALUE]
        self._attr_is_on = self.entity_description.value_mapping.get(value, value)
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Update to the EV charger."""
        evcharger = self.coordinator.evcharger
        await evcharger.set_parameter(
            self.inv_value_mapping[True],
            self.entity_description.channel,
        )
        self._attr_is_on = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Update to the EV charger."""
        evcharger = self.coordinator.evcharger
        await evcharger.set_parameter(
            self.inv_value_mapping[False],
            self.entity_description.channel,
        )
        self._attr_is_on = False
        await self.coordinator.async_request_refresh()

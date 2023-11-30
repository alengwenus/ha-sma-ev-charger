"""Number platform for SMA EV Charger integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import TYPE_CHECKING

from pysmaev.helpers import get_parameters_channel

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfTime
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
    SMAEV_DEFAULT_MAX,
    SMAEV_DEFAULT_MIN,
    SMAEV_DEVICE_INFO,
    SMAEV_MAX_VALUE,
    SMAEV_MIN_VALUE,
    SMAEV_PARAMETER,
    SMAEV_VALUE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmaEvChargerNumberEntityDescription(NumberEntityDescription):
    """Describes SMA EV Charger number entities."""

    type: str = ""
    channel: str = ""


NUMBER_DESCRIPTIONS: tuple[SmaEvChargerNumberEntityDescription, ...] = (
    SmaEvChargerNumberEntityDescription(
        key="standby_charge_disconnect",
        translation_key="standby_charge_disconnect",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.StpWhenFlTm",
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmaEvChargerNumberEntityDescription(
        key="duration_charge_session",
        translation_key="duration_charge_session",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.Plan.DurTmm",
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerNumberEntityDescription(
        key="energy_charge_session",
        translation_key="energy_charge_session",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.Plan.En",
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA EV Charger number entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = data[SMAEV_COORDINATOR]
    device_info = data[SMAEV_DEVICE_INFO]

    if TYPE_CHECKING:
        assert config_entry.unique_id

    entities = []

    for entity_description in NUMBER_DESCRIPTIONS:
        entities.append(
            SmaEvChargerNumber(
                coordinator, config_entry.unique_id, device_info, entity_description
            )
        )

    async_add_entities(entities)


class SmaEvChargerNumber(CoordinatorEntity, NumberEntity):
    """Representation of a SMA EV Charger number entity."""

    entity_description: SmaEvChargerNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_unique_id: str,
        device_info: DeviceInfo,
        entity_desscription: SmaEvChargerNumberEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_desscription

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry_unique_id}-{self.entity_description.key}"
        self._attr_native_min_value = SMAEV_DEFAULT_MIN
        self._attr_native_max_value = SMAEV_DEFAULT_MAX

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        channel = get_parameters_channel(
            self.coordinator.data[SMAEV_PARAMETER],
            self.entity_description.channel,
        )

        min_value = channel.get(SMAEV_MIN_VALUE)
        max_value = channel.get(SMAEV_MAX_VALUE)
        value = int(float(channel[SMAEV_VALUE]))
        if (
            (min_value is not None)
            and (max_value is not None)
            and (
                (min_value != self._attr_native_min_value)
                or (max_value != self._attr_native_max_value)
            )
        ):
            self._attr_native_min_value = min_value
            self._attr_native_max_value = max_value
            async_call_later(self.hass, 0, self.force_refresh)
        else:
            self._attr_native_value = value
        super()._handle_coordinator_update()

    def force_refresh(self, _: datetime):
        """Call coordinator update handle."""
        self._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Update to the EV charger."""
        evcharger = self.coordinator.evcharger
        await evcharger.set_parameter(f"{value:.0f}", self.entity_description.channel)
        await self.coordinator.async_request_refresh()

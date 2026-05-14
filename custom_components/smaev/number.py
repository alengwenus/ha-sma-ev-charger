"""Number platform for SMA EV Charger integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from homeassistant.components.number import (
    ENTITY_ID_FORMAT,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from pysmaev.helpers import expect_type, get_parameters_channel

from . import SmaEvChargerConfigEntry, generate_smaev_entity_id
from .const import (
    SMAEV_DEFAULT_MAX,
    SMAEV_DEFAULT_MIN,
    SMAEV_MAX_VALUE,
    SMAEV_MIN_VALUE,
    SMAEV_PARAMETER,
    SMAEV_VALUE,
)
from .coordinator import SmaEvChargerCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
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
        native_step=0.1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerNumberEntityDescription(
        key="charge_current_limit",
        translation_key="charge_current_limit",
        type=SMAEV_PARAMETER,
        channel="Parameter.Inverter.AcALim",
        native_step=0.001,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_registry_enabled_default=False,
    ),
    SmaEvChargerNumberEntityDescription(
        key="charge_power_limit",
        translation_key="charge_power_limit",
        type=SMAEV_PARAMETER,
        channel="Parameter.Inverter.WMaxIn",
        native_step=1,
        mode=NumberMode.BOX,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: SmaEvChargerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA EV Charger number entities."""
    device_info = config_entry.runtime_data.device_info
    channels = config_entry.runtime_data.channels

    if TYPE_CHECKING:
        assert config_entry.unique_id

    entities: list[SmaEvChargerNumber] = []

    for entity_description in NUMBER_DESCRIPTIONS:
        if entity_description.channel in channels[entity_description.type]:
            entities.append(
                SmaEvChargerNumber(hass, config_entry, device_info, entity_description)
            )
        else:
            _LOGGER.warning(
                "Channel '%s' is not accessible. Elevated rights might be required.",
                entity_description.channel,
            )

    async_add_entities(entities)


class SmaEvChargerNumber(CoordinatorEntity, NumberEntity):
    """Representation of a SMA EV Charger number entity."""

    coordinator: SmaEvChargerCoordinator
    entity_description: SmaEvChargerNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SmaEvChargerConfigEntry,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerNumberEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(config_entry.runtime_data.coordinator)
        self.hass = hass
        self.config_entry = config_entry
        self.entity_description = entity_description
        self.entity_id = generate_smaev_entity_id(
            hass, config_entry, ENTITY_ID_FORMAT, entity_description
        )

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry.unique_id}-{self.entity_description.key}"
        self._attr_native_min_value = SMAEV_DEFAULT_MIN
        self._attr_native_max_value = SMAEV_DEFAULT_MAX
        self._attr_native_step = entity_description.native_step or 1

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        channel = get_parameters_channel(
            self.coordinator.data[SMAEV_PARAMETER],
            self.entity_description.channel,
        )

        min_value = channel.get(SMAEV_MIN_VALUE)
        max_value = channel.get(SMAEV_MAX_VALUE)
        value = float(expect_type(str, channel[SMAEV_VALUE]))
        if self.native_step == 1:
            value = int(value)
        if (
            (min_value is not None)
            and (max_value is not None)
            and (
                (min_value != self._attr_native_min_value)
                or (max_value != self._attr_native_max_value)
            )
        ):
            self._attr_native_min_value = cast(float, min_value)
            self._attr_native_max_value = cast(float, max_value)
            self.hass.async_create_task(self.force_refresh())
        else:
            self._attr_native_value = value
        super()._handle_coordinator_update()

    async def force_refresh(self) -> None:
        """Call coordinator update handle."""
        self._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        """Update to the EV charger."""
        if self.native_step == 1:
            value = int(value)
        evcharger = self.coordinator.evcharger
        await evcharger.set_parameter(f"{value}", self.entity_description.channel)
        await self.coordinator.async_request_refresh()

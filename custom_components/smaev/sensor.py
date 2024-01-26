"""Sensor platform for SMA EV Charger integration."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING

from pysmaev.const import SmaEvChargerMeasurements
from pysmaev.exceptions import SmaEvChargerChannelError
from pysmaev.helpers import get_measurements_channel, get_parameters_channel

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_MEASUREMENT,
    SMAEV_PARAMETER,
    SMAEV_VALUE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmaEvChargerSensorEntityDescription(SensorEntityDescription):
    """Describes SMA EV Charger sensor entities."""

    type: str = ""
    channel: str = ""
    value_mapping: dict = field(default_factory=dict)


SENSOR_DESCRIPTIONS: tuple[SmaEvChargerSensorEntityDescription, ...] = (
    SmaEvChargerSensorEntityDescription(
        key="charging_session_energy",
        translation_key="charging_session_energy",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.ChaSess.WhIn",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="position_of_rotary_switch",
        translation_key="position_of_rotary_switch",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Chrg.ModSw",
        value_mapping={
            SmaEvChargerMeasurements.SMART_CHARGING: "smart_charging",
            SmaEvChargerMeasurements.BOOST_CHARGING: "boost_charging",
        },
        device_class=SensorDeviceClass.ENUM,
        options=["smart_charging", "boost_charging"],
        entity_registry_enabled_default=True,
    ),
    *(
        SmaEvChargerSensorEntityDescription(
            key=f"grid_current_phase_l{load}",
            translation_key=f"grid_current_phase_l{load}",
            type=SMAEV_MEASUREMENT,
            channel=f"Measurement.GridMs.A.phs{phase}",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            state_class=SensorStateClass.MEASUREMENT,
            device_class=SensorDeviceClass.CURRENT,
            entity_registry_enabled_default=False,
        )
        for phase, load in (("A", 1), ("B", 2), ("C", 3))
    ),
    *(
        SmaEvChargerSensorEntityDescription(
            key=f"grid_voltage_phase_l{load}",
            translation_key=f"grid_voltage_phase_l{load}",
            type=SMAEV_MEASUREMENT,
            channel=f"Measurement.GridMs.PhV.phs{phase}",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            state_class=SensorStateClass.MEASUREMENT,
            device_class=SensorDeviceClass.VOLTAGE,
            entity_registry_enabled_default=False,
        )
        for phase, load in (("A", 1), ("B", 2), ("C", 3))
    ),
    SmaEvChargerSensorEntityDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.GridMs.Hz",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    SmaEvChargerSensorEntityDescription(
        key="charging_station_power",
        translation_key="charging_station_power",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Metering.GridMs.TotWIn.ChaSta",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="charging_station_meter_reading",
        translation_key="charging_station_meter_reading",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Metering.GridMs.TotWhIn.ChaSta",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="charging_session_status",
        translation_key="charging_session_status",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Operation.EVeh.ChaStt",
        value_mapping={
            SmaEvChargerMeasurements.NOT_CONNECTED: "not_connected",
            SmaEvChargerMeasurements.SLEEP_MODE: "sleep_mode",
            SmaEvChargerMeasurements.ACTIVE_MODE: "active_mode",
            SmaEvChargerMeasurements.STATION_LOCKED: "station_locked",
        },
        device_class=SensorDeviceClass.ENUM,
        options=["not_connected", "sleep_mode", "active_mode", "station_locked"],
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="connected_vehicle_status",
        translation_key="connected_vehicle_status",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Operation.EVeh.Health",
        value_mapping={
            SmaEvChargerMeasurements.OK: "ok",
            SmaEvChargerMeasurements.WARNING: "warning",
            SmaEvChargerMeasurements.ALARM: "alarm",
            SmaEvChargerMeasurements.OFF: "off",
        },
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "warning", "alarm", "off"],
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="charging_station_status",
        translation_key="charging_station_status",
        type=SMAEV_MEASUREMENT,
        channel="Measurement.Operation.Health",
        value_mapping={
            SmaEvChargerMeasurements.OK: "ok",
            SmaEvChargerMeasurements.WARNING: "warning",
            SmaEvChargerMeasurements.ALARM: "alarm",
            SmaEvChargerMeasurements.OFF: "off",
        },
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "warning", "alarm", "off"],
        entity_registry_enabled_default=True,
    ),
    SmaEvChargerSensorEntityDescription(
        key="mac_address",
        translation_key="mac_address",
        type=SMAEV_PARAMETER,
        channel="Parameter.Nameplate.MacId",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SmaEvChargerSensorEntityDescription(
        key="wifi_mac_address",
        translation_key="wifi_mac_address",
        type=SMAEV_PARAMETER,
        channel="Parameter.Nameplate.WlMacId",
        entity_registry_enabled_default=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA EV Charger sensors."""
    data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = data[SMAEV_COORDINATOR]
    device_info = data[SMAEV_DEVICE_INFO]

    if TYPE_CHECKING:
        assert config_entry.unique_id

    entities = []

    for entity_description in SENSOR_DESCRIPTIONS:
        entities.append(
            SmaEvChargerSensor(
                coordinator, config_entry.unique_id, device_info, entity_description
            )
        )

    async_add_entities(entities)


class SmaEvChargerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SMA EV Charger sensor."""

    entity_description: SmaEvChargerSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_unique_id: str,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry_unique_id}-{self.entity_description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            if self.entity_description.type == SMAEV_MEASUREMENT:
                channel = get_measurements_channel(
                    self.coordinator.data[SMAEV_MEASUREMENT],
                    self.entity_description.channel,
                )
                value = channel[0][SMAEV_VALUE]
            else:  # SMAEV_PARAMETER
                channel = get_parameters_channel(
                    self.coordinator.data[SMAEV_PARAMETER],
                    self.entity_description.channel,
                )
                value = channel[SMAEV_VALUE]
        except SmaEvChargerChannelError:
            return

        value = self.entity_description.value_mapping.get(value, value)

        self._attr_native_value = value
        super()._handle_coordinator_update()

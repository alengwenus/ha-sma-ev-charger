"""DateTime platform for SMA EV Charger integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING

from pysmaev.helpers import get_parameters_channel

from homeassistant.components.datetime import (
    ENTITY_ID_FORMAT,
    DateTimeEntity,
    DateTimeEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import generate_smaev_entity_id
from .const import (
    DOMAIN,
    SMAEV_COORDINATOR,
    SMAEV_DEVICE_INFO,
    SMAEV_PARAMETER,
    SMAEV_VALUE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmaEvChargerDateTimeEntityDescription(DateTimeEntityDescription):
    """Describes SMA EV Charger datetime entities."""

    type: str = ""
    channel: str = ""


DATETIME_DESCRIPTIONS: tuple[SmaEvChargerDateTimeEntityDescription] = (
    SmaEvChargerDateTimeEntityDescription(
        key="end_charging_process",
        translation_key="end_charging_process",
        type=SMAEV_PARAMETER,
        channel="Parameter.Chrg.Plan.StopTm",
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

    for entity_description in DATETIME_DESCRIPTIONS:
        entities.append(
            SmaEvChargerDateTime(
                hass, coordinator, config_entry, device_info, entity_description
            )
        )

    async_add_entities(entities)


class SmaEvChargerDateTime(CoordinatorEntity, DateTimeEntity):
    """Representation of a SMA EV Charger datetime entity."""

    entity_description: SmaEvChargerDateTimeEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        device_info: DeviceInfo,
        entity_description: SmaEvChargerDateTimeEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.entity_description = entity_description
        self.entity_id = generate_smaev_entity_id(
            hass, config_entry, ENTITY_ID_FORMAT, entity_description
        )

        self._attr_device_info = device_info
        self._attr_unique_id = f"{config_entry.unique_id}-{self.entity_description.key}"
        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        channel = get_parameters_channel(
            self.coordinator.data[SMAEV_PARAMETER],
            self.entity_description.channel,
        )

        self._attr_native_value = datetime.fromtimestamp(
            int(channel[SMAEV_VALUE]), tz=UTC
        )
        super()._handle_coordinator_update()

    async def async_set_value(self, value: datetime) -> None:
        """Update to the EV charger."""
        evcharger = self.coordinator.evcharger
        timestamp = int(value.timestamp())
        await evcharger.set_parameter(timestamp, self.entity_description.channel)
        await self.coordinator.async_request_refresh()

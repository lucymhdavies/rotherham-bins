"""Sensors for upcoming Rotherham bin collections."""

from __future__ import annotations

from datetime import date
import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Collection
from .const import (
    ATTR_ADDRESS,
    ATTR_BIN_TYPE,
    ATTR_COLLECTIONS,
    ATTR_DAYS_UNTIL,
    ATTR_LOCAL_AUTHORITY,
    ATTR_POSTCODE,
    ATTR_PREMISE_ID,
    CONF_ADDRESS,
    CONF_LOCAL_AUTHORITY,
    CONF_POSTCODE,
    CONF_PREMISE_ID,
    DOMAIN,
    NAME,
)
from .coordinator import RotherhamBinsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the next-collection and per-bin sensors."""
    coordinator: RotherhamBinsCoordinator = entry.runtime_data
    bin_types = sorted({collection.bin_type for collection in coordinator.data or []})
    entities: list[SensorEntity] = [RotherhamBinsNextSensor(coordinator, entry)]
    entities.extend(RotherhamBinsTypeSensor(coordinator, entry, bin_type) for bin_type in bin_types)
    async_add_entities(entities)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class RotherhamBinsSensorBase(SensorEntity):
    """Shared entity behavior."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: RotherhamBinsCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(entry.data[CONF_PREMISE_ID]))},
            "name": entry.title,
            "manufacturer": NAME,
        }

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose the source property and compact upcoming schedule."""
        collections = self.coordinator.data or []
        return {
            ATTR_ADDRESS: self.entry.data[CONF_ADDRESS],
            ATTR_POSTCODE: self.entry.data[CONF_POSTCODE],
            ATTR_PREMISE_ID: self.entry.data[CONF_PREMISE_ID],
            ATTR_LOCAL_AUTHORITY: self.entry.data[CONF_LOCAL_AUTHORITY],
            ATTR_COLLECTIONS: [
                {"date": item.collection_date.isoformat(), "bin_type": item.bin_type}
                for item in collections[:10]
            ],
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class RotherhamBinsNextSensor(RotherhamBinsSensorBase):
    """The next collection of any bin type."""

    _attr_name = "Next collection"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator: RotherhamBinsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data[CONF_PREMISE_ID]}_next"

    @property
    def native_value(self) -> date | None:
        return self.coordinator.data[0].collection_date if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attributes = super().extra_state_attributes
        if self.coordinator.data:
            next_collection = self.coordinator.data[0]
            attributes[ATTR_BIN_TYPE] = next_collection.bin_type
            attributes[ATTR_DAYS_UNTIL] = (next_collection.collection_date - date.today()).days
        return attributes


class RotherhamBinsTypeSensor(RotherhamBinsSensorBase):
    """The next collection for one bin type."""

    def __init__(self, coordinator: RotherhamBinsCoordinator, entry: ConfigEntry, bin_type: str) -> None:
        super().__init__(coordinator, entry)
        self.bin_type = bin_type
        self._attr_name = f"{bin_type.title()} collection"
        self._attr_icon = "mdi:trash-can"
        self._attr_unique_id = f"{entry.data[CONF_PREMISE_ID]}_{_slug(bin_type)}"

    @property
    def _next_collection(self) -> Collection | None:
        return next((item for item in self.coordinator.data or [] if item.bin_type == self.bin_type), None)

    @property
    def native_value(self) -> date | None:
        collection = self._next_collection
        return collection.collection_date if collection else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attributes = super().extra_state_attributes
        collection = self._next_collection
        if collection:
            attributes[ATTR_BIN_TYPE] = collection.bin_type
            attributes[ATTR_DAYS_UNTIL] = (collection.collection_date - date.today()).days
        return attributes

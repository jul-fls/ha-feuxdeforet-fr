"""Binary sensor platform for Feux de Foret."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROXIMITY_RADIUS_KM,
    DEFAULT_PROXIMITY_RADIUS_KM,
    DEVICE_ID,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import FeuxDeForetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up proximity alert binary sensor."""
    async_add_entities([FeuxDeForetNearbyFireBinarySensor(entry.runtime_data.coordinator)])


class FeuxDeForetNearbyFireBinarySensor(
    CoordinatorEntity[FeuxDeForetCoordinator], BinarySensorEntity
):
    """Report whether an active fire is within the configured radius."""

    _attr_has_entity_name = True
    _attr_translation_key = "nearby_fire"
    _attr_icon = "mdi:fire"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: FeuxDeForetCoordinator) -> None:
        """Initialize the proximity alert."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_nearby_fire"

    @property
    def is_on(self) -> bool:
        """Return whether one or more fires are nearby."""
        return bool(self.coordinator.data.nearby_fire_ids)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return aggregate device information."""
        return {
            "identifiers": {(DOMAIN, DEVICE_ID)},
            "manufacturer": MANUFACTURER,
            "name": DEVICE_NAME,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return proximity details."""
        radius_km = float(
            self.coordinator.entry.options.get(
                CONF_PROXIMITY_RADIUS_KM, DEFAULT_PROXIMITY_RADIUS_KM
            )
        )
        return {
            "radius_km": radius_km,
            "fire_count": len(self.coordinator.data.nearby_fire_ids),
            "fire_ids": self.coordinator.data.nearby_fire_ids,
        }

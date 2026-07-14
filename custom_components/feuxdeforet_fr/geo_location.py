"""Geo-location platform for Feux de Foret fires."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CREATE_FIRE_GEOLOCATIONS,
    DOMAIN,
)
from .coordinator import FeuxDeForetCoordinator
from .models import FireFeature


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up dynamic fire geo-location entities."""
    if not entry.options.get(CONF_CREATE_FIRE_GEOLOCATIONS, True):
        return

    coordinator = entry.runtime_data.coordinator
    known_ids: set[str] = set()

    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if (
            registry_entry.entity_id.startswith("geo_location.")
            and registry_entry.device_id is not None
        ):
            entity_registry.async_update_entity(
                registry_entry.entity_id, device_id=None
            )

    @callback
    def async_add_new_fires() -> None:
        entities: list[FeuxDeForetFireLocation] = []
        for fire_id in sorted(coordinator.data.fires):
            if fire_id not in known_ids:
                known_ids.add(fire_id)
                entities.append(FeuxDeForetFireLocation(coordinator, fire_id))
        if entities:
            async_add_entities(entities)

    async_add_new_fires()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_fires))


class FeuxDeForetFireLocation(
    CoordinatorEntity[FeuxDeForetCoordinator], GeolocationEvent
):
    """Geo-location entity for one fire point."""

    _attr_has_entity_name = False
    _attr_source = DOMAIN
    _attr_icon = "mdi:fire-alert"

    def __init__(self, coordinator: FeuxDeForetCoordinator, fire_id: str) -> None:
        """Initialize the fire location."""
        super().__init__(coordinator)
        self.fire_id = fire_id
        self._attr_unique_id = f"{DOMAIN}_fire_{fire_id}"

    @property
    def available(self) -> bool:
        """Return if this fire is still present in the latest payload."""
        return super().available and self.fire_id in self.coordinator.data.fires

    @property
    def name(self) -> str | None:
        """Return the fire name."""
        fire = self._fire
        return fire.name if fire is not None else f"Feu {self.fire_id}"

    @property
    def state(self) -> str | None:
        """Return a useful state instead of unknown."""
        fire = self._fire
        if fire is None:
            return None
        if fire.status == "eteint":
            return fire.status
        return fire.state or fire.status or "cartographie"

    @property
    def latitude(self) -> float | None:
        """Return latitude."""
        fire = self._fire
        return fire.latitude if fire is not None else None

    @property
    def longitude(self) -> float | None:
        """Return longitude."""
        fire = self._fire
        return fire.longitude if fire is not None else None

    @property
    def distance(self) -> float | None:
        """Distance is computed by Home Assistant/map consumers."""
        return None

    @property
    def external_id(self) -> str:
        """Return external id."""
        return self.fire_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return fire attributes."""
        fire = self._fire
        if fire is None:
            return {"fire_id": self.fire_id, "removed_from_latest_payload": True}
        return {
            "fire_id": fire.id,
            "status": fire.status,
            "raw_status": fire.properties.get("statut"),
            "state": fire.state,
            "municipality": fire.municipality,
            "department_name": fire.department_name,
            "department_code": fire.department_code,
            "department_slug": fire.department_slug,
            "region_slug": fire.region_slug,
            "url": fire.url,
            "properties": fire.properties,
        }

    @property
    def _fire(self) -> FireFeature | None:
        """Return the current fire feature if it still exists."""
        return self.coordinator.data.fires.get(self.fire_id)

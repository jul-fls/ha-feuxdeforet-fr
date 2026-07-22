"""Geo-location platform for Feux de Foret fires."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CREATE_FIRE_GEOLOCATIONS,
    DOMAIN,
)
from .coordinator import FeuxDeForetCoordinator
from .helpers import distance_km, is_displayable_fire_location
from .models import FireFeature


def _remove_stale_registry_entries(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    entry_id: str,
    current_fire_ids: set[str],
    removing_entity_ids: set[str] | None = None,
) -> None:
    """Remove legacy fire entities that are no longer displayable."""
    removing_entity_ids = removing_entity_ids or set()
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry_id
    ):
        if not registry_entry.unique_id.startswith(f"{DOMAIN}_fire_"):
            continue
        fire_id = registry_entry.unique_id.removeprefix(f"{DOMAIN}_fire_")
        if (
            fire_id in current_fire_ids
            or registry_entry.entity_id in removing_entity_ids
        ):
            continue
        hass.states.async_remove(registry_entry.entity_id)
        entity_registry.async_remove(registry_entry.entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up dynamic fire geo-location entities."""
    if not entry.options.get(CONF_CREATE_FIRE_GEOLOCATIONS, True):
        return

    coordinator = entry.runtime_data.coordinator
    known_entities: dict[str, FeuxDeForetFireLocation] = {}
    displayable_fire_ids = {
        fire_id
        for fire_id, fire in coordinator.data.fires.items()
        if is_displayable_fire_location(fire)
    }

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
    if coordinator.data.geojson is not None:
        _remove_stale_registry_entries(
            hass, entity_registry, entry.entry_id, displayable_fire_ids
        )

    @callback
    def async_sync_fires() -> None:
        if coordinator.data.geojson is None:
            return
        current_fire_ids = {
            fire_id
            for fire_id, fire in coordinator.data.fires.items()
            if is_displayable_fire_location(fire)
        }
        entities: list[FeuxDeForetFireLocation] = []
        for fire_id in sorted(current_fire_ids):
            if fire_id not in known_entities:
                entity = FeuxDeForetFireLocation(coordinator, fire_id)
                known_entities[fire_id] = entity
                entities.append(entity)
        if entities:
            async_add_entities(entities)

        removing_entity_ids: set[str] = set()
        for fire_id, entity in list(known_entities.items()):
            if fire_id in current_fire_ids:
                continue
            if entity.entity_id:
                hass.states.async_remove(entity.entity_id)
                removing_entity_ids.add(entity.entity_id)
                hass.async_create_task(entity.async_remove(force_remove=True))
            known_entities.pop(fire_id, None)

        _remove_stale_registry_entries(
            hass,
            entity_registry,
            entry.entry_id,
            current_fire_ids,
            removing_entity_ids,
        )

    async_sync_fires()
    entry.async_on_unload(coordinator.async_add_listener(async_sync_fires))


class FeuxDeForetFireLocation(
    CoordinatorEntity[FeuxDeForetCoordinator], GeolocationEvent
):
    """Geo-location entity for one fire point."""

    _attr_has_entity_name = False
    _attr_source = DOMAIN
    _attr_icon = "mdi:fire"
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

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
        """Return distance from the configured Home Assistant location."""
        fire = self._fire
        if fire is None:
            return None
        return round(
            distance_km(
                self.coordinator.hass.config.latitude,
                self.coordinator.hass.config.longitude,
                fire.latitude,
                fire.longitude,
            ),
            2,
        )

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

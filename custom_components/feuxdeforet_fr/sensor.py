"""Sensor platform for Feux de Foret."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CREATE_DEPARTMENT_SENSORS,
    CONF_CREATE_REGION_SENSORS,
    DEVICE_ID,
    DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import FeuxDeForetCoordinator
from .models import ZoneCount


def _empty_attrs(coordinator: FeuxDeForetCoordinator) -> dict[str, Any]:
    """Return no extra attributes."""
    return {}


@dataclass(frozen=True, kw_only=True)
class FeuxDeForetSensorDescription(SensorEntityDescription):
    """Describe a Feux de Foret sensor."""

    display_name: str
    value_fn: Callable[[FeuxDeForetCoordinator], Any]
    attrs_fn: Callable[[FeuxDeForetCoordinator], dict[str, Any]] = _empty_attrs


NATIONAL_SENSORS: tuple[FeuxDeForetSensorDescription, ...] = (
    FeuxDeForetSensorDescription(
        key="current_fires",
        display_name="Feux en cours",
        icon="mdi:fire-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_24h",
        display_name="Feux sur 24h",
        icon="mdi:fire-clock",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_24h"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_7d",
        display_name="Feux sur 7 jours",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_7d"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_30d",
        display_name="Feux sur 30 jours",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_30d"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_year",
        display_name="Feux cette année",
        icon="mdi:calendar-fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_year"),
    ),
    FeuxDeForetSensorDescription(
        key="weak_risk_zones",
        display_name="Zones risque faible",
        icon="mdi:map-marker-radius-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "weak_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="moderate_risk_zones",
        display_name="Zones risque modéré",
        icon="mdi:map-marker-radius",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "moderate_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="high_risk_zones",
        display_name="Zones risque élevé",
        icon="mdi:map-marker-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "high_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="very_high_risk_zones",
        display_name="Zones risque très élevé",
        icon="mdi:map-marker-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "very_high_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="extreme_risk_zones",
        display_name="Zones risque extrême",
        icon="mdi:map-marker-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "extreme_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="mapped_fires",
        display_name="Feux cartographiés",
        icon="mdi:map-marker-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: len(coordinator.data.fires),
        attrs_fn=lambda coordinator: {
            "fire_ids": sorted(coordinator.data.fires),
            "geojson_available": coordinator.data.geojson is not None,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Feux de Foret sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        FeuxDeForetNationalSensor(coordinator, description)
        for description in NATIONAL_SENSORS
    ]

    if entry.options.get(CONF_CREATE_REGION_SENSORS, True):
        entities.extend(
            FeuxDeForetZoneSensor(coordinator, "region", zone_key)
            for zone_key in sorted(coordinator.data.region_counts)
        )

    if entry.options.get(CONF_CREATE_DEPARTMENT_SENSORS, True):
        entities.extend(
            FeuxDeForetZoneSensor(coordinator, "department", zone_key)
            for zone_key in sorted(coordinator.data.department_counts)
        )

    async_add_entities(entities)


class FeuxDeForetBaseSensor(CoordinatorEntity[FeuxDeForetCoordinator], SensorEntity):
    """Base Feux de Foret sensor."""

    _attr_has_entity_name = False

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, DEVICE_ID)},
            "manufacturer": MANUFACTURER,
            "name": DEVICE_NAME,
        }


class FeuxDeForetNationalSensor(FeuxDeForetBaseSensor):
    """National aggregate sensor."""

    entity_description: FeuxDeForetSensorDescription

    def __init__(
        self,
        coordinator: FeuxDeForetCoordinator,
        description: FeuxDeForetSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.display_name
        self._attr_unique_id = f"{DOMAIN}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self.entity_description.attrs_fn(self.coordinator)


class FeuxDeForetZoneSensor(FeuxDeForetBaseSensor):
    """Fire count sensor for a region or department."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: FeuxDeForetCoordinator,
        zone_type: str,
        zone_key: str,
    ) -> None:
        """Initialize the zone sensor."""
        super().__init__(coordinator)
        self.zone_type = zone_type
        self.zone_key = zone_key
        self._attr_unique_id = f"{DOMAIN}_{zone_type}_{zone_key}_fires"
        self._attr_name = self._build_name()
        self._attr_icon = (
            "mdi:map" if self.zone_type == "region" else "mdi:map-marker-radius"
        )

    @property
    def native_value(self) -> int:
        """Return active fire count for the zone."""
        return self._zone.active_count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return zone details."""
        zone = self._zone
        return {
            "zone_type": self.zone_type,
            "zone_key": zone.key,
            "zone_name": zone.name,
            "url": zone.url,
            "total_mapped_fires": zone.count,
            "active_fires": zone.active_count,
            "by_status": zone.by_status,
        }

    @property
    def entity_category(self) -> EntityCategory | None:
        """Hide empty department sensors from primary dashboards by default."""
        if self.zone_type == "department" and self.native_value == 0:
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def _zone(self) -> ZoneCount:
        """Return the current zone count."""
        zones = (
            self.coordinator.data.region_counts
            if self.zone_type == "region"
            else self.coordinator.data.department_counts
        )
        return zones[self.zone_key]

    def _build_name(self) -> str:
        """Build a readable zone sensor name."""
        prefix = "Région" if self.zone_type == "region" else "Département"
        return f"{prefix} {self._zone.name} - feux actifs"


def _stats_value(coordinator: FeuxDeForetCoordinator, attr: str) -> int | None:
    """Read a stats attribute safely."""
    stats = coordinator.data.stats
    return getattr(stats, attr, None) if stats is not None else None

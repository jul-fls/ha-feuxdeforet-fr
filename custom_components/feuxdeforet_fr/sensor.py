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

    value_fn: Callable[[FeuxDeForetCoordinator], Any]
    attrs_fn: Callable[[FeuxDeForetCoordinator], dict[str, Any]] = _empty_attrs


NATIONAL_SENSORS: tuple[FeuxDeForetSensorDescription, ...] = (
    FeuxDeForetSensorDescription(
        key="current_fires",
        translation_key="current_fires",
        icon="mdi:fire-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_24h",
        translation_key="fires_24h",
        icon="mdi:fire-clock",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_24h"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_7d",
        translation_key="fires_7d",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_7d"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_30d",
        translation_key="fires_30d",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_30d"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_year",
        translation_key="fires_year",
        icon="mdi:calendar-fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_year"),
    ),
    FeuxDeForetSensorDescription(
        key="weak_risk_zones",
        translation_key="weak_risk_zones",
        icon="mdi:map-marker-radius",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "weak_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="moderate_risk_zones",
        translation_key="moderate_risk_zones",
        icon="mdi:map-marker-radius",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "moderate_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="high_risk_zones",
        translation_key="high_risk_zones",
        icon="mdi:map-marker-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "high_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="very_high_risk_zones",
        translation_key="very_high_risk_zones",
        icon="mdi:map-marker-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "very_high_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="extreme_risk_zones",
        translation_key="extreme_risk_zones",
        icon="mdi:map-marker-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "extreme_risk_zones"),
    ),
    FeuxDeForetSensorDescription(
        key="mapped_fires",
        translation_key="mapped_fires",
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

    _attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "france")},
            "manufacturer": MANUFACTURER,
            "name": "Feux de Foret France",
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

    _attr_icon = "mdi:map-marker-radius"
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
        self._attr_translation_key = f"{zone_type}_fires"

    @property
    def translation_placeholders(self) -> dict[str, str]:
        """Return translation placeholders."""
        return {"zone": self._zone.name}

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


def _stats_value(coordinator: FeuxDeForetCoordinator, attr: str) -> int | None:
    """Read a stats attribute safely."""
    stats = coordinator.data.stats
    return getattr(stats, attr, None) if stats is not None else None

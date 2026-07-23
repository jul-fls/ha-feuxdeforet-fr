"""Sensor platform for Feux de Foret."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
from .helpers import absolute_url
from .models import FireFeature, HomeFire, ZoneCount


def _empty_attrs(coordinator: FeuxDeForetCoordinator) -> dict[str, Any]:
    """Return no extra attributes."""
    return {}


@dataclass(frozen=True, kw_only=True)
class FeuxDeForetSensorDescription(SensorEntityDescription):
    """Describe a Feux de Foret sensor."""

    value_fn: Callable[[FeuxDeForetCoordinator], Any]
    attrs_fn: Callable[[FeuxDeForetCoordinator], dict[str, Any]] = _empty_attrs
    available_after_failure: bool = False


NATIONAL_SENSORS: tuple[FeuxDeForetSensorDescription, ...] = (
    FeuxDeForetSensorDescription(
        key="last_successful_update",
        translation_key="last_successful_update",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.last_successful_update,
        attrs_fn=lambda coordinator: {
            "update_success": coordinator.data_fresh,
            "last_refresh_error": coordinator.last_refresh_error,
            "poll_interval_seconds": int(coordinator.update_interval.total_seconds()),
        },
        available_after_failure=True,
    ),
    FeuxDeForetSensorDescription(
        key="current_fires",
        translation_key="current_fires",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published"),
    ),
    FeuxDeForetSensorDescription(
        key="fires_24h",
        translation_key="fires_24h",
        icon="mdi:clock-outline",
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
        icon="mdi:calendar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: _stats_value(coordinator, "valid_published_year"),
    ),
    FeuxDeForetSensorDescription(
        key="weak_risk_zones",
        translation_key="weak_risk_zones",
        icon="mdi:map-marker-radius-outline",
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
        icon="mdi:map-marker-alert-outline",
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
    FeuxDeForetSensorDescription(
        key="recent_fires",
        translation_key="recent_fires",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: len(coordinator.data.home_fires),
        attrs_fn=lambda coordinator: {
            "fires": [
                _home_fire_attributes(fire)
                for fire in coordinator.data.home_fires
            ]
        },
    ),
    FeuxDeForetSensorDescription(
        key="latest_fire_report",
        translation_key="latest_fire_report",
        icon="mdi:fire",
        value_fn=lambda coordinator: _latest_fire_title(coordinator),
        attrs_fn=lambda coordinator: (
            _home_fire_attributes(coordinator.data.home_fires[0])
            if coordinator.data.home_fires
            else {}
        ),
    ),
    FeuxDeForetSensorDescription(
        key="latest_news",
        translation_key="latest_news",
        icon="mdi:newspaper",
        value_fn=lambda coordinator: _latest_article_title(coordinator),
        attrs_fn=lambda coordinator: _latest_article_attributes(coordinator),
    ),
    FeuxDeForetSensorDescription(
        key="nearest_fire_distance",
        translation_key="nearest_fire_distance",
        icon="mdi:map-marker-radius",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda coordinator: (
            round(coordinator.data.nearest_fire_distance_km, 2)
            if coordinator.data.nearest_fire_distance_km is not None
            else None
        ),
        attrs_fn=lambda coordinator: _nearest_fire_attributes(coordinator),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Feux de Foret sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator

    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if (
            registry_entry.unique_id.startswith(f"{DOMAIN}_department_")
            and registry_entry.entity_category is EntityCategory.DIAGNOSTIC
        ):
            entity_registry.async_update_entity(
                registry_entry.entity_id, entity_category=None
            )

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
        self._attr_unique_id = f"{DOMAIN}_{description.key}"

    @property
    def available(self) -> bool:
        """Keep the last successful update visible after a refresh failure."""
        if self.entity_description.available_after_failure:
            return self.entity_description.value_fn(self.coordinator) is not None
        return super().available

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
        self._attr_translation_key = f"{zone_type}_fires"
        self._attr_translation_placeholders = {"zone": self._zone.name}
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


def _home_fire_attributes(fire: HomeFire) -> dict[str, Any]:
    """Return recorder-friendly homepage fire attributes."""
    return {
        "id": fire.id,
        "title": fire.title,
        "municipality": fire.municipality,
        "department_code": fire.department_code,
        "date": fire.date_iso,
        "time_ago": fire.time_ago,
        "in_progress": fire.in_progress,
        "url": fire.url,
        "thumbnail": fire.thumbnail,
    }


def _latest_fire_title(coordinator: FeuxDeForetCoordinator) -> str | None:
    """Return the latest homepage fire title within HA's state length limit."""
    if not coordinator.data.home_fires:
        return None
    return coordinator.data.home_fires[0].title[:255]


def _latest_article_title(coordinator: FeuxDeForetCoordinator) -> str | None:
    """Return the latest article title within HA's state length limit."""
    home = coordinator.data.home
    if home is None or not home.articles:
        return None
    return home.articles[0].title[:255]


def _latest_article_attributes(
    coordinator: FeuxDeForetCoordinator,
) -> dict[str, Any]:
    """Return useful latest article metadata."""
    home = coordinator.data.home
    if home is None or not home.articles:
        return {}
    article = home.articles[0]
    return {
        "id": article.id,
        "title": article.title,
        "excerpt": article.excerpt,
        "category": article.category.name if article.category else None,
        "date": article.date_iso,
        "reading_time_minutes": article.reading_time,
        "url": absolute_url(article.url),
        "thumbnail": absolute_url(article.thumbnail_large or article.thumbnail),
    }


def _nearest_fire_attributes(
    coordinator: FeuxDeForetCoordinator,
) -> dict[str, Any]:
    """Return metadata for the nearest active fire."""
    fire_id = coordinator.data.nearest_fire_id
    fire: FireFeature | None = (
        coordinator.data.fires.get(fire_id) if fire_id is not None else None
    )
    if fire is None:
        return {}
    return {
        "fire_id": fire.id,
        "name": fire.name,
        "status": fire.status,
        "state": fire.state,
        "municipality": fire.municipality,
        "department_name": fire.department_name,
        "department_code": fire.department_code,
        "latitude": fire.latitude,
        "longitude": fire.longitude,
        "url": fire.url,
    }

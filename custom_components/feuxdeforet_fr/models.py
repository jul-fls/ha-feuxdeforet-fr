"""Internal data models for Feux de Foret."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class FireFeature:
    """One fire feature displayed as a Home Assistant geo-location."""

    id: str
    latitude: float
    longitude: float
    status: str | None
    state: str | None
    url: str | None
    department_slug: str | None
    region_slug: str | None
    municipality: str | None
    department_name: str | None
    department_code: str | None
    display_name: str
    perimeter_count: int
    properties: dict[str, Any]

    @property
    def name(self) -> str:
        """Return a stable friendly name."""
        return self.display_name


@dataclass(frozen=True, slots=True)
class ZoneCount:
    """Computed fire count for a region or department."""

    key: str
    name: str
    url: str
    count: int
    active_count: int
    by_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HomeFire:
    """Recent fire summary exposed by the homepage endpoint."""

    id: str
    title: str
    municipality: str | None
    department_code: str | None
    url: str | None
    date_iso: str | None
    time_ago: str | None
    in_progress: bool
    thumbnail: str | None


@dataclass(frozen=True, slots=True)
class FeuxDeForetData:
    """All data fetched by one coordinator refresh."""

    stats: Any | None
    regions: tuple[Any, ...]
    home: Any | None
    home_fires: tuple[HomeFire, ...]
    geojson: dict[str, Any] | None
    fires: dict[str, FireFeature]
    region_counts: dict[str, ZoneCount]
    department_counts: dict[str, ZoneCount]
    nearest_fire_id: str | None
    nearest_fire_distance_km: float | None
    nearby_fire_ids: tuple[str, ...]
    unmatched_fire_ids: tuple[str, ...]

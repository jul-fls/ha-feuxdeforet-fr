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
class FeuxDeForetData:
    """All data fetched by one coordinator refresh."""

    stats: Any | None
    regions: tuple[Any, ...]
    home: Any | None
    geojson: dict[str, Any] | None
    fires: dict[str, FireFeature]
    region_counts: dict[str, ZoneCount]
    department_counts: dict[str, ZoneCount]

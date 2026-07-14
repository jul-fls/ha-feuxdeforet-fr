"""Pure helpers for Feux de Foret payload processing."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from math import asin, cos, radians, sin, sqrt
from typing import Any

from .models import FireFeature, HomeFire, ZoneCount

PUBLISHED_STATUS = "valide_publie"
STATUS_LABELS = {"cloture": "eteint"}
_FIRE_SLUG_SUFFIX = re.compile(r"-\d{2}-\d{2}-\d{4}-\d+$")
_DEPARTMENT_CODE_SUFFIX = re.compile(r"-(\d{2,3}|2a|2b)$", re.IGNORECASE)
BASE_URL = "https://feuxdeforet.fr"


def extract_geojson_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the actual GeoJSON object from the API response envelope."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        return data
    if payload.get("type") == "FeatureCollection":
        return payload
    return None


def features_from_geojson(
    payload: dict[str, Any] | None,
    department_to_region: dict[str, str],
    department_names: dict[str, str] | None = None,
) -> dict[str, FireFeature]:
    """Convert a GeoJSON payload to keyed fire features."""
    geojson = extract_geojson_payload(payload)
    if geojson is None:
        return {}

    parsed_fires = [
        parsed
        for feature in geojson.get("features", [])
        if (
            parsed := feature_from_geojson_feature(
                feature, department_to_region, department_names or {}
            )
        )
        is not None
    ]
    label_counts = Counter(fire.display_name for fire in parsed_fires)

    fires: dict[str, FireFeature] = {}
    for fire in parsed_fires:
        display_name = fire.display_name
        if label_counts[display_name] > 1:
            display_name = f"{display_name} #{fire.id}"
        fires[fire.id] = replace(fire, display_name=display_name)
    return fires


def feature_from_geojson_feature(
    feature: dict[str, Any],
    department_to_region: dict[str, str],
    department_names: dict[str, str],
) -> FireFeature | None:
    """Parse a single GeoJSON feature."""
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    properties = feature.get("properties") or {}
    fire_id = properties.get("id")
    if not isinstance(coordinates, list) or len(coordinates) < 2 or fire_id is None:
        return None

    longitude = float(coordinates[0])
    latitude = float(coordinates[1])
    url = properties.get("url")
    url_department_slug = department_slug_from_url(url)
    department_slug = canonical_department_slug(url_department_slug)
    department_key = department_match_key(department_slug)
    department_name = department_names.get(department_key)
    municipality = municipality_from_url(url)
    department_code = department_code_from_slug(url_department_slug)
    display_name = fire_display_name(
        fire_id=str(fire_id),
        municipality=municipality,
        department_name=department_name,
        department_code=department_code,
        fallback=department_slug or department_to_region.get(department_key),
    )
    return FireFeature(
        id=str(fire_id),
        latitude=latitude,
        longitude=longitude,
        status=normalize_status(properties.get("statut")),
        state=str(properties.get("etat")) if properties.get("etat") else None,
        url=str(url) if url else None,
        department_slug=department_slug,
        region_slug=department_to_region.get(department_key),
        municipality=municipality,
        department_name=department_name,
        department_code=department_code,
        display_name=display_name,
        properties=dict(properties),
    )


def department_slug_from_url(url: object) -> str | None:
    """Extract a department slug from a feuxdeforet.fr URL."""
    parts = url_parts(url)
    if not parts:
        return None
    return parts[0]


def municipality_from_url(url: object) -> str | None:
    """Extract a readable municipality name from a fire URL."""
    parts = url_parts(url)
    if len(parts) < 2:
        return None
    municipality_slug = _FIRE_SLUG_SUFFIX.sub("", parts[1])
    return title_from_slug(municipality_slug)


def department_code_from_slug(slug: str | None) -> str | None:
    """Extract the department code from a department slug."""
    if not slug:
        return None
    match = _DEPARTMENT_CODE_SUFFIX.search(slug)
    return match.group(1).upper() if match else None


def canonical_department_slug(slug: str | None) -> str | None:
    """Remove the department code appended to fire URL slugs."""
    if not slug:
        return None
    return _DEPARTMENT_CODE_SUFFIX.sub("", slug)


def department_match_key(slug: str | None) -> str:
    """Return a key tolerant of API and fire URL slug punctuation differences."""
    canonical_slug = canonical_department_slug(slug) or ""
    return re.sub(r"[^a-z0-9]", "", canonical_slug.lower())


def normalize_status(status: object) -> str | None:
    """Return a user-facing status while preserving unknown API values."""
    if status is None or status == "":
        return None
    raw_status = str(status)
    return STATUS_LABELS.get(raw_status, raw_status)


def absolute_url(url: object) -> str | None:
    """Return an absolute feuxdeforet.fr URL."""
    if not isinstance(url, str) or not url:
        return None
    if url.startswith(("https://", "http://")):
        return url
    return f"{BASE_URL}/{url.lstrip('/')}"


def home_fires_from_data(home: Any | None) -> tuple[HomeFire, ...]:
    """Parse recent fires retained in HomeData.raw by the client library."""
    raw = getattr(home, "raw", None)
    if not isinstance(raw, dict):
        return ()

    fires: list[HomeFire] = []
    raw_fires = raw.get("feux", [])
    if not isinstance(raw_fires, list):
        return ()
    for payload in raw_fires:
        if not isinstance(payload, dict) or payload.get("id") is None:
            continue
        fires.append(
            HomeFire(
                id=str(payload["id"]),
                title=str(payload.get("title") or ""),
                municipality=(
                    str(payload["commune"]) if payload.get("commune") else None
                ),
                department_code=(
                    str(payload["dept"]) if payload.get("dept") else None
                ),
                url=absolute_url(payload.get("url")),
                date_iso=(
                    str(payload["dateIso"]) if payload.get("dateIso") else None
                ),
                time_ago=(
                    str(payload["timeAgo"]) if payload.get("timeAgo") else None
                ),
                in_progress=bool(payload.get("enCours")),
                thumbnail=absolute_url(payload.get("thumbnail")),
            )
        )
    return tuple(fires)


def distance_km(
    latitude: float,
    longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    """Return great-circle distance between two WGS84 points in kilometers."""
    earth_radius_km = 6371.0088
    lat1 = radians(latitude)
    lat2 = radians(target_latitude)
    delta_lat = lat2 - lat1
    delta_lon = radians(target_longitude - longitude)
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(haversine))


def fire_proximity(
    fires: dict[str, FireFeature],
    latitude: float,
    longitude: float,
    radius_km: float,
) -> tuple[str | None, float | None, tuple[str, ...]]:
    """Return nearest active fire and active fire IDs within a radius."""
    distances = {
        fire.id: distance_km(latitude, longitude, fire.latitude, fire.longitude)
        for fire in fires.values()
        if is_active_fire(fire)
    }
    if not distances:
        return None, None, ()
    nearest_id = min(distances, key=distances.__getitem__)
    nearby_ids = tuple(
        fire_id
        for fire_id, distance in sorted(distances.items(), key=lambda item: item[1])
        if distance <= radius_km
    )
    return nearest_id, distances[nearest_id], nearby_ids


def url_parts(url: object) -> list[str]:
    """Return normalized path parts from an absolute or relative URL."""
    if not isinstance(url, str) or not url:
        return []
    path = url.split("feuxdeforet.fr", 1)[-1]
    return [part for part in path.split("/") if part]


def title_from_slug(slug: str | None) -> str | None:
    """Convert a slug to a readable French-ish title."""
    if not slug:
        return None
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def fire_display_name(
    *,
    fire_id: str,
    municipality: str | None,
    department_name: str | None,
    department_code: str | None,
    fallback: str | None,
) -> str:
    """Build the HA friendly fire entity name."""
    if municipality and department_name and department_code:
        return f"Feu de {municipality} - {department_name} ({department_code})"
    if municipality and department_name:
        return f"Feu de {municipality} - {department_name}"
    if municipality and department_code:
        return f"Feu de {municipality} - {department_code}"
    if municipality:
        return f"Feu de {municipality}"
    if fallback:
        return f"Feu {fire_id} - {title_from_slug(fallback) or fallback}"
    return f"Feu {fire_id}"


def is_active_fire(fire: FireFeature) -> bool:
    """Return whether a fire should count as active/current."""
    return fire.status == PUBLISHED_STATUS


def build_department_to_region(regions: tuple[Any, ...]) -> dict[str, str]:
    """Build a department slug to region slug lookup."""
    mapping: dict[str, str] = {}
    for region in regions:
        for department in region.departments:
            mapping[department_match_key(department.slug)] = region.slug
    return mapping


def build_department_names(regions: tuple[Any, ...]) -> dict[str, str]:
    """Build a normalized department slug to official name lookup."""
    return {
        department_match_key(department.slug): department.name
        for region in regions
        for department in region.departments
    }


def build_region_counts(
    regions: tuple[Any, ...], fires: dict[str, FireFeature]
) -> dict[str, ZoneCount]:
    """Build one fire count per region."""
    counts: dict[str, ZoneCount] = {}
    for region in regions:
        region_fires = [
            fire for fire in fires.values() if fire.region_slug == region.slug
        ]
        counts[region.slug] = zone_count_from_fires(
            key=region.slug,
            name=region.name,
            url=region.url,
            fires=region_fires,
        )
    return counts


def build_department_counts(
    regions: tuple[Any, ...], fires: dict[str, FireFeature]
) -> dict[str, ZoneCount]:
    """Build one fire count per department."""
    counts: dict[str, ZoneCount] = {}
    for region in regions:
        for department in region.departments:
            department_key = department_match_key(department.slug)
            department_fires = [
                fire
                for fire in fires.values()
                if department_match_key(fire.department_slug) == department_key
            ]
            counts[department.slug] = zone_count_from_fires(
                key=department.slug,
                name=department.name,
                url=department.url,
                fires=department_fires,
            )
    return counts


def zone_count_from_fires(
    *,
    key: str,
    name: str,
    url: str,
    fires: list[FireFeature],
) -> ZoneCount:
    """Build a zone count from fire features."""
    statuses = Counter(fire.status or "unknown" for fire in fires)
    return ZoneCount(
        key=key,
        name=name,
        url=url,
        count=len(fires),
        active_count=sum(1 for fire in fires if is_active_fire(fire)),
        by_status=dict(statuses),
    )

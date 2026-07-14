"""Pure helpers for Feux de Foret payload processing."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from typing import Any

from .models import FireFeature, ZoneCount

ACTIVE_STATES = {"attaque", "en_cours", "actif", "non_maitrise"}
PUBLISHED_STATUS = "valide_publie"
_FIRE_SLUG_SUFFIX = re.compile(r"-\d{2}-\d{2}-\d{4}-\d+$")
_DEPARTMENT_CODE_SUFFIX = re.compile(r"-(\d{2,3}|2a|2b)$", re.IGNORECASE)


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
) -> dict[str, FireFeature]:
    """Convert a GeoJSON payload to keyed fire features."""
    geojson = extract_geojson_payload(payload)
    if geojson is None:
        return {}

    parsed_fires = [
        parsed
        for feature in geojson.get("features", [])
        if (parsed := feature_from_geojson_feature(feature, department_to_region))
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
    department_slug = department_slug_from_url(url)
    municipality = municipality_from_url(url)
    department_code = department_code_from_slug(department_slug)
    display_name = fire_display_name(
        fire_id=str(fire_id),
        municipality=municipality,
        department_code=department_code,
        fallback=department_slug or department_to_region.get(department_slug or ""),
    )
    return FireFeature(
        id=str(fire_id),
        latitude=latitude,
        longitude=longitude,
        status=str(properties.get("statut")) if properties.get("statut") else None,
        state=str(properties.get("etat")) if properties.get("etat") else None,
        url=str(url) if url else None,
        department_slug=department_slug,
        region_slug=department_to_region.get(department_slug or ""),
        municipality=municipality,
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
    department_code: str | None,
    fallback: str | None,
) -> str:
    """Build the HA friendly fire entity name."""
    if municipality and department_code:
        return f"Feu de {municipality} - {department_code}"
    if municipality:
        return f"Feu de {municipality}"
    if fallback:
        return f"Feu {fire_id} - {title_from_slug(fallback) or fallback}"
    return f"Feu {fire_id}"


def is_active_fire(fire: FireFeature) -> bool:
    """Return whether a fire should count as active/current."""
    return fire.status == PUBLISHED_STATUS and (
        fire.state in ACTIVE_STATES or fire.state is None
    )


def build_department_to_region(regions: tuple[Any, ...]) -> dict[str, str]:
    """Build a department slug to region slug lookup."""
    mapping: dict[str, str] = {}
    for region in regions:
        for department in region.departments:
            mapping[department.slug] = region.slug
    return mapping


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
            department_fires = [
                fire
                for fire in fires.values()
                if fire.department_slug == department.slug
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

"""Diagnostics support for Feux de Foret."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator
    data = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "options": dict(entry.options),
        },
        "stats_available": data.stats is not None,
        "regions": len(data.regions),
        "mapped_fires": len(data.fires),
        "unmatched_fire_ids": data.unmatched_fire_ids,
        "nearby_fire_ids": data.nearby_fire_ids,
        "nearest_fire_id": data.nearest_fire_id,
        "nearest_fire_distance_km": data.nearest_fire_distance_km,
        "region_counts": {
            key: {
                "name": value.name,
                "count": value.count,
                "active_count": value.active_count,
                "by_status": value.by_status,
            }
            for key, value in data.region_counts.items()
        },
        "home": {
            "articles": len(data.home.articles) if data.home is not None else 0,
            "recent_fires": len(data.home_fires),
            "latest_article_id": (
                data.home.articles[0].id
                if data.home is not None and data.home.articles
                else None
            ),
            "latest_fire_id": data.home_fires[0].id if data.home_fires else None,
        },
        "geojson_available": data.geojson is not None,
    }

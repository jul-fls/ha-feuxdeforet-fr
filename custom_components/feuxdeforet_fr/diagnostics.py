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
        "region_counts": {
            key: {
                "name": value.name,
                "count": value.count,
                "active_count": value.active_count,
                "by_status": value.by_status,
            }
            for key, value in data.region_counts.items()
        },
        "home_articles": len(data.home.articles) if data.home is not None else 0,
        "geojson_available": data.geojson is not None,
    }

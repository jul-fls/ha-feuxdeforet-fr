"""Data coordinator for Feux de Foret."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pyfeuxdeforet_fr import FeuxDeForetClient

from .const import (
    CONF_POLL_INTERVAL,
    CONF_PROXIMITY_RADIUS_KM,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PROXIMITY_RADIUS_KM,
    DOMAIN,
    GEOJSON_NONCE,
    MIN_POLL_INTERVAL,
    REGIONS_REFRESH_INTERVAL,
)
from .helpers import (
    build_department_counts,
    build_department_names,
    build_department_to_region,
    build_region_counts,
    features_from_geojson,
    fire_proximity,
    home_fires_from_data,
)
from .models import FeuxDeForetData

_LOGGER = logging.getLogger(__name__)


class FeuxDeForetCoordinator(DataUpdateCoordinator[FeuxDeForetData]):
    """Fetch all Feux de Foret data with one shared polling loop."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: FeuxDeForetClient,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = client
        self._regions: tuple[Any, ...] | None = None
        self._regions_refreshed_at: datetime | None = None
        poll_interval = int(
            entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=max(MIN_POLL_INTERVAL, poll_interval)),
            always_update=False,
        )

    async def _async_update_data(self) -> FeuxDeForetData:
        """Fetch data from feuxdeforet.fr."""
        try:
            async with asyncio.timeout(30):
                regions, stats, home, geojson = await asyncio.gather(
                    self._async_get_regions(),
                    self.client.get_stats(),
                    self.client.get_home(),
                    self.client.get_geojson(
                        last_update=self._geojson_last_update(),
                        nonce=GEOJSON_NONCE,
                        headers={
                            "Accept": "application/geo+json, application/json",
                            "Referer": "https://feuxdeforet.fr/fdf/cartographie/",
                        },
                    ),
                )
        except TimeoutError as err:
            raise UpdateFailed("Timed out fetching feuxdeforet.fr data") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching feuxdeforet.fr data: {err}") from err

        if regions is None:
            raise UpdateFailed("Missing regions payload from feuxdeforet.fr")

        department_to_region = build_department_to_region(regions)
        department_names = build_department_names(regions)
        fires = features_from_geojson(
            geojson, department_to_region, department_names
        )
        radius_km = float(
            self.entry.options.get(
                CONF_PROXIMITY_RADIUS_KM, DEFAULT_PROXIMITY_RADIUS_KM
            )
        )
        nearest_id, nearest_distance, nearby_ids = fire_proximity(
            fires,
            self.hass.config.latitude,
            self.hass.config.longitude,
            radius_km,
        )
        unmatched_fire_ids = tuple(
            sorted(
                fire.id
                for fire in fires.values()
                if fire.url is not None and fire.region_slug is None
            )
        )
        if geojson is not None:
            self._update_unmatched_fire_issue(unmatched_fire_ids)
        return FeuxDeForetData(
            stats=stats,
            regions=regions,
            home=home,
            home_fires=home_fires_from_data(home),
            geojson=geojson,
            fires=fires,
            region_counts=build_region_counts(regions, fires),
            department_counts=build_department_counts(regions, fires),
            nearest_fire_id=nearest_id,
            nearest_fire_distance_km=nearest_distance,
            nearby_fire_ids=nearby_ids,
            unmatched_fire_ids=unmatched_fire_ids,
        )

    async def _async_get_regions(self) -> tuple[Any, ...] | None:
        """Return cached regions, refreshing the mostly-static data daily."""
        now = dt_util.utcnow()
        if (
            self._regions is not None
            and self._regions_refreshed_at is not None
            and now - self._regions_refreshed_at < REGIONS_REFRESH_INTERVAL
        ):
            return self._regions

        try:
            regions = await self.client.get_regions()
        except Exception:
            if self._regions is None:
                raise
            _LOGGER.warning("Unable to refresh regions; keeping the cached metadata")
            return self._regions
        if regions is not None:
            self._regions = regions
            self._regions_refreshed_at = now
        return self._regions

    def _update_unmatched_fire_issue(self, fire_ids: tuple[str, ...]) -> None:
        """Create a repair issue when the upstream zone format is no longer mapped."""
        if fire_ids:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "unmatched_fires",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="unmatched_fires",
                translation_placeholders={"count": str(len(fire_ids))},
            )
            return
        ir.async_delete_issue(self.hass, DOMAIN, "unmatched_fires")

    @staticmethod
    def _geojson_last_update() -> str:
        """Return the frontend-style last_update parameter for this refresh."""
        refresh_time = dt_util.start_of_local_day() - timedelta(days=1)
        return refresh_time.replace(microsecond=0).isoformat()

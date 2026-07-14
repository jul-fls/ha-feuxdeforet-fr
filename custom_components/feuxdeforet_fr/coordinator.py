"""Data coordinator for Feux de Foret."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pyfeuxdeforet_fr import FeuxDeForetClient

from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    GEOJSON_NONCE,
    MIN_POLL_INTERVAL,
)
from .helpers import (
    build_department_counts,
    build_department_names,
    build_department_to_region,
    build_region_counts,
    features_from_geojson,
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
                    self.client.get_regions(),
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
        return FeuxDeForetData(
            stats=stats,
            regions=regions,
            home=home,
            geojson=geojson,
            fires=fires,
            region_counts=build_region_counts(regions, fires),
            department_counts=build_department_counts(regions, fires),
        )

    @staticmethod
    def _geojson_last_update() -> str:
        """Return the frontend-style last_update parameter for this refresh."""
        refresh_time = dt_util.start_of_local_day() - timedelta(days=1)
        return refresh_time.replace(microsecond=0).isoformat()

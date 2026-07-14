"""The Feux de Foret integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyfeuxdeforet_fr import FeuxDeForetClient

from .const import DOMAIN, PLATFORMS, SERVICE_REFRESH
from .coordinator import FeuxDeForetCoordinator

_LOGGER = logging.getLogger(__name__)


type FeuxDeForetConfigEntry = ConfigEntry[FeuxDeForetRuntimeData]


@dataclass(slots=True)
class FeuxDeForetRuntimeData:
    """Runtime data stored on the config entry."""

    coordinator: FeuxDeForetCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level services."""
    hass.data.setdefault(DOMAIN, {})

    async def async_handle_refresh(call: ServiceCall) -> None:
        """Refresh all configured Feux de Foret coordinators."""
        for entry_data in hass.data.get(DOMAIN, {}).values():
            coordinator = entry_data.coordinator
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, async_handle_refresh)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FeuxDeForetConfigEntry) -> bool:
    """Set up Feux de Foret from a config entry."""
    session = async_get_clientsession(hass)
    client = FeuxDeForetClient(session=session)
    coordinator = FeuxDeForetCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = FeuxDeForetRuntimeData(coordinator=coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FeuxDeForetConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

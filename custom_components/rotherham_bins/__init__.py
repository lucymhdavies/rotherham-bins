"""Rotherham Bins Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RotherhamBinsApi
from .const import CONF_PREMISE_ID, DOMAIN, PLATFORMS
from .coordinator import RotherhamBinsCoordinator

type RotherhamBinsConfigEntry = ConfigEntry[RotherhamBinsCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: RotherhamBinsConfigEntry) -> bool:
    """Set up Rotherham Bins from a config entry."""
    api = RotherhamBinsApi(async_get_clientsession(hass))
    coordinator = RotherhamBinsCoordinator(hass, api, entry.data[CONF_PREMISE_ID])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, [Platform(platform) for platform in PLATFORMS])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RotherhamBinsConfigEntry) -> bool:
    """Unload a Rotherham Bins config entry."""
    return await hass.config_entries.async_unload_platforms(entry, [Platform(platform) for platform in PLATFORMS])

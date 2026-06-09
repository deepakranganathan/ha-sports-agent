"""Sports Team Agent integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SportsAgentCoordinator
from .teams_sync import async_write_teams_json

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def _async_setup_coordinator(hass: HomeAssistant) -> SportsAgentCoordinator:
    """Create or refresh the shared schedules coordinator."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinator = domain_data.get("coordinator")
    if coordinator is None:
        coordinator = SportsAgentCoordinator(hass)
        domain_data["coordinator"] = coordinator
        await coordinator.async_config_entry_first_refresh()
    else:
        await coordinator.async_request_refresh()
    return coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sports Team Agent from a config entry."""
    await _async_setup_coordinator(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_write_teams_json(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await async_write_teams_json(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry and refresh teams.json."""
    await async_write_teams_json(hass)

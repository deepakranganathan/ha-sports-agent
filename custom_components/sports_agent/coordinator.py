"""Coordinator that reads schedule data written by the add-on."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONFIG_SUBDIR, DOMAIN, SCHEDULES_FILENAME, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class SportsAgentCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Read schedules.json produced by the Sports Team Agent add-on."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._schedules_path = (
            Path(hass.config.path(CONFIG_SUBDIR)) / SCHEDULES_FILENAME
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self.hass.async_add_executor_job(self._read_schedules)
        except json.JSONDecodeError as err:
            raise UpdateFailed(f"Invalid schedules.json: {err}") from err

    def _read_schedules(self) -> dict[str, dict[str, Any]]:
        if not self._schedules_path.is_file():
            return {}
        raw = json.loads(self._schedules_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise UpdateFailed("schedules.json must be a JSON object")
        return raw

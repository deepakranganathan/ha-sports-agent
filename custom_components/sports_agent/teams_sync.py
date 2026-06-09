"""Sync integration config entries to teams.json for the add-on."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLED,
    CONF_EMOJI,
    CONF_ID,
    CONF_KICKOFF_LABEL,
    CONF_MATCH_DAY_LABEL,
    CONF_MATCH_PHRASE,
    CONF_NAME,
    CONF_NEWS_FOCUS,
    CONF_SPORT,
    CONFIG_SUBDIR,
    DOMAIN,
    TEAMS_FILENAME,
)

_LOGGER = logging.getLogger(__name__)


def config_dir(hass: HomeAssistant) -> Path:
    """Return the shared /config/sports_agent directory."""
    return Path(hass.config.path(CONFIG_SUBDIR))


def _entry_to_team(entry: ConfigEntry) -> dict[str, Any]:
    data = entry.data
    news_focus = data.get(CONF_NEWS_FOCUS, [])
    if isinstance(news_focus, str):
        news_focus = [part.strip() for part in news_focus.split(",") if part.strip()]
    return {
        CONF_ID: data[CONF_ID],
        CONF_NAME: data[CONF_NAME],
        CONF_SPORT: data[CONF_SPORT],
        CONF_EMOJI: data.get(CONF_EMOJI, "🏟️"),
        CONF_ENABLED: data.get(CONF_ENABLED, True),
        CONF_NEWS_FOCUS: list(news_focus),
        CONF_MATCH_PHRASE: data.get(CONF_MATCH_PHRASE, "{name} vs {opponent}"),
        CONF_MATCH_DAY_LABEL: data.get(CONF_MATCH_DAY_LABEL, "Match Day"),
        CONF_KICKOFF_LABEL: data.get(CONF_KICKOFF_LABEL, "Kickoff"),
    }


async def async_write_teams_json(hass: HomeAssistant) -> None:
    """Write all configured teams to teams.json for the add-on worker."""
    entries = hass.config_entries.async_entries(DOMAIN)
    teams = [_entry_to_team(entry) for entry in entries]
    payload = {"teams": teams}
    target = config_dir(hass) / TEAMS_FILENAME

    def _write() -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    await hass.async_add_executor_job(_write)
    _LOGGER.debug("Wrote %d team(s) to %s", len(teams), target)

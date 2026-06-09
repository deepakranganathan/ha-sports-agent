"""Schedule sensors for Sports Team Agent teams."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ID, CONF_NAME, CONF_SPORT, DOMAIN, SPORT_ICONS
from .coordinator import SportsAgentCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up schedule sensor for a team config entry."""
    coordinator: SportsAgentCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([TeamScheduleSensor(coordinator, entry)])


class TeamScheduleSensor(CoordinatorEntity[SportsAgentCoordinator], SensorEntity):
    """Sensor showing upcoming fixtures for one team."""

    _attr_has_entity_name = True
    _attr_name = "Schedule"

    def __init__(
        self, coordinator: SportsAgentCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        team_id = entry.data[CONF_ID]
        self._attr_unique_id = f"{team_id}_schedule"
        self._attr_translation_key = "schedule"

    @property
    def team_id(self) -> str:
        """Return the configured team id."""
        return self._entry.data[CONF_ID]

    @property
    def team_data(self) -> dict[str, Any]:
        """Return schedule payload for this team."""
        return self.coordinator.data.get(self.team_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this team."""
        sport = self._entry.data[CONF_SPORT]
        return DeviceInfo(
            identifiers={(DOMAIN, self.team_id)},
            name=self._entry.data[CONF_NAME],
            manufacturer="Sports Team Agent",
            model=sport.title(),
        )

    @property
    def icon(self) -> str:
        """Return sport-specific icon."""
        return SPORT_ICONS.get(
            self._entry.data[CONF_SPORT], "mdi:calendar-clock"
        )

    @property
    def native_value(self) -> str | None:
        """Return next match summary."""
        value = self.team_data.get("state")
        if value is None:
            return "Waiting for add-on"
        return str(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return fixture list and metadata."""
        data = self.team_data
        return {
            "team_id": self.team_id,
            "team_name": self._entry.data[CONF_NAME],
            "sport": self._entry.data[CONF_SPORT],
            "fixture_count": data.get("fixture_count", 0),
            "fixtures": data.get("fixtures", []),
            "next_opponent": data.get("next_opponent"),
            "next_kickoff_utc": data.get("next_kickoff_utc"),
            "next_competition": data.get("next_competition"),
            "last_updated": data.get("last_updated"),
        }

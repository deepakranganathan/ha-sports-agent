"""Config flow for Sports Team Agent."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ENABLED,
    CONF_EMOJI,
    CONF_ID,
    CONF_KICKOFF_LABEL,
    CONF_MATCH_DAY_LABEL,
    CONF_MATCH_PHRASE,
    CONF_NAME,
    CONF_NEWS_FOCUS,
    CONF_PRESET,
    CONF_SPORT,
    DEFAULT_EMOJI,
    DEFAULT_KICKOFF_LABEL,
    DEFAULT_MATCH_DAY_LABEL,
    DEFAULT_MATCH_PHRASE,
    DOMAIN,
    PRESET_CUSTOM,
    SPORT_CRICKET,
    SPORT_FOOTBALL,
    TEAM_ID_PATTERN,
    TEAM_PRESETS,
)
from .teams_sync import async_write_teams_json

PRESET_OPTIONS = [
    *[
        selector.SelectOptionDict(value=preset_id, label=str(preset[CONF_NAME]))
        for preset_id, preset in TEAM_PRESETS.items()
    ],
    selector.SelectOptionDict(value=PRESET_CUSTOM, label="Custom team"),
]

SPORT_OPTIONS = [
    selector.SelectOptionDict(value=SPORT_FOOTBALL, label="Football"),
    selector.SelectOptionDict(value=SPORT_CRICKET, label="Cricket"),
]

STEP_PRESET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PRESET): selector.SelectSelector(
            selector.SelectSelectorConfig(options=PRESET_OPTIONS)
        ),
    }
)


def _team_form_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    news_focus = defaults.get(CONF_NEWS_FOCUS, [])
    if isinstance(news_focus, list):
        news_focus = ", ".join(news_focus)
    return vol.Schema(
        {
            vol.Required(CONF_ID, default=defaults.get(CONF_ID, "")): str,
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(CONF_SPORT, default=defaults.get(CONF_SPORT, SPORT_FOOTBALL)): selector.SelectSelector(
                selector.SelectSelectorConfig(options=SPORT_OPTIONS)
            ),
            vol.Optional(CONF_EMOJI, default=defaults.get(CONF_EMOJI, DEFAULT_EMOJI)): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(
                CONF_NEWS_FOCUS,
                default=news_focus,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT, multiline=True
                )
            ),
            vol.Optional(
                CONF_MATCH_PHRASE,
                default=defaults.get(CONF_MATCH_PHRASE, DEFAULT_MATCH_PHRASE),
            ): str,
            vol.Optional(
                CONF_MATCH_DAY_LABEL,
                default=defaults.get(CONF_MATCH_DAY_LABEL, DEFAULT_MATCH_DAY_LABEL),
            ): str,
            vol.Optional(
                CONF_KICKOFF_LABEL,
                default=defaults.get(CONF_KICKOFF_LABEL, DEFAULT_KICKOFF_LABEL),
            ): str,
            vol.Optional(CONF_ENABLED, default=defaults.get(CONF_ENABLED, True)): bool,
        }
    )


def _normalize_team_data(data: dict[str, Any]) -> dict[str, Any]:
    team_id = str(data[CONF_ID]).strip().lower()
    if not re.fullmatch(TEAM_ID_PATTERN, team_id):
        raise ValueError(
            "Team id must be lowercase letters, numbers, and hyphens only "
            "(e.g. liverpool-fc)."
        )
    name = str(data[CONF_NAME]).strip()
    if not name:
        raise ValueError("Team name is required.")

    news_focus = data.get(CONF_NEWS_FOCUS, "")
    if isinstance(news_focus, str):
        news_focus = [part.strip() for part in news_focus.split(",") if part.strip()]

    match_phrase = str(data.get(CONF_MATCH_PHRASE, DEFAULT_MATCH_PHRASE)).strip()
    match_phrase = match_phrase.replace("{name}", name)

    return {
        CONF_ID: team_id,
        CONF_NAME: name,
        CONF_SPORT: data[CONF_SPORT],
        CONF_EMOJI: str(data.get(CONF_EMOJI, DEFAULT_EMOJI)).strip() or DEFAULT_EMOJI,
        CONF_NEWS_FOCUS: news_focus,
        CONF_MATCH_PHRASE: match_phrase,
        CONF_MATCH_DAY_LABEL: str(
            data.get(CONF_MATCH_DAY_LABEL, DEFAULT_MATCH_DAY_LABEL)
        ).strip()
        or DEFAULT_MATCH_DAY_LABEL,
        CONF_KICKOFF_LABEL: str(
            data.get(CONF_KICKOFF_LABEL, DEFAULT_KICKOFF_LABEL)
        ).strip()
        or DEFAULT_KICKOFF_LABEL,
        CONF_ENABLED: bool(data.get(CONF_ENABLED, True)),
    }


class SportsAgentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sports Team Agent."""

    VERSION = 1

    def __init__(self) -> None:
        self._preset: str = PRESET_CUSTOM
        self._team_defaults: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Choose a preset team or custom setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            preset = user_input[CONF_PRESET]
            if preset == PRESET_CUSTOM:
                self._preset = PRESET_CUSTOM
                self._team_defaults = {}
                return await self.async_step_team()
            self._preset = preset
            self._team_defaults = dict(TEAM_PRESETS[preset])
            return await self.async_step_team()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_PRESET_SCHEMA,
            errors=errors,
        )

    async def async_step_team(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure team details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                team_data = _normalize_team_data(user_input)
            except ValueError as err:
                errors["base"] = str(err)
            else:
                await self.async_set_unique_id(team_data[CONF_ID])
                self._abort_if_unique_id_configured()
                result = self.async_create_entry(title=team_data[CONF_NAME], data=team_data)
                await async_write_teams_json(self.hass)
                return result

        return self.async_show_form(
            step_id="team",
            data_schema=_team_form_schema(self._team_defaults),
            errors=errors,
            description_placeholders={
                "preset": "custom" if self._preset == PRESET_CUSTOM else self._preset
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SportsAgentOptionsFlow:
        """Return the options flow handler."""
        return SportsAgentOptionsFlow(config_entry)


class SportsAgentOptionsFlow(config_entries.OptionsFlow):
    """Edit an existing team."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit team settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                team_data = _normalize_team_data(
                    {**self._config_entry.data, **user_input, CONF_ID: self._config_entry.data[CONF_ID]}
                )
            except ValueError as err:
                errors["base"] = str(err)
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=team_data
                )
                await async_write_teams_json(self.hass)
                return self.async_create_entry(title="", data={})

        defaults = dict(self._config_entry.data)
        news_focus = defaults.get(CONF_NEWS_FOCUS, [])
        if isinstance(news_focus, list):
            news_focus = ", ".join(news_focus)
        options_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
                vol.Required(
                    CONF_SPORT, default=defaults.get(CONF_SPORT, SPORT_FOOTBALL)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SPORT_OPTIONS)
                ),
                vol.Optional(
                    CONF_EMOJI, default=defaults.get(CONF_EMOJI, DEFAULT_EMOJI)
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_NEWS_FOCUS, default=news_focus): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT, multiline=True
                    )
                ),
                vol.Optional(
                    CONF_MATCH_PHRASE,
                    default=defaults.get(CONF_MATCH_PHRASE, DEFAULT_MATCH_PHRASE),
                ): str,
                vol.Optional(
                    CONF_MATCH_DAY_LABEL,
                    default=defaults.get(CONF_MATCH_DAY_LABEL, DEFAULT_MATCH_DAY_LABEL),
                ): str,
                vol.Optional(
                    CONF_KICKOFF_LABEL,
                    default=defaults.get(CONF_KICKOFF_LABEL, DEFAULT_KICKOFF_LABEL),
                ): str,
                vol.Optional(
                    CONF_ENABLED, default=defaults.get(CONF_ENABLED, True)
                ): bool,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )

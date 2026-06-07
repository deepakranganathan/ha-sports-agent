"""Team registry loaded from teams.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEAMS_FILE = PROJECT_ROOT / "teams.json"
FIXTURE_WINDOW_DAYS = 14


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    sport: str
    emoji: str
    enabled: bool
    news_focus: tuple[str, ...]
    match_phrase: str
    match_day_label: str
    kickoff_label: str

    @property
    def ha_tag(self) -> str:
        return f"{self.id.replace('-', '_')}_daily_news"

    @property
    def ha_group(self) -> str:
        return self.id.replace("-", "_")

    def news_system_instruction(self) -> str:
        focus = ", ".join(self.news_focus)
        return (
            f"You are a {self.name} news assistant ({self.sport}). "
            "Search for the latest news and produce a concise daily briefing. "
            f"Focus on: {focus}. "
            "Be factual, concise, and well-structured. Use bullet points. "
            "Always end with the next upcoming match or fixture details if available."
        )

    def news_user_prompt(self, today: str) -> str:
        return (
            f"Search the web and give me a {self.name} daily news summary for {today}. "
            f"Include the latest {self.sport} news relevant to the team."
        )

    def fixtures_system_instruction(self) -> str:
        return (
            f"You are a fixture data extractor for {self.name} ({self.sport}). "
            "Search for upcoming matches or fixtures. "
            "Respond ONLY with a valid JSON array. No preamble, no markdown fences. "
            "Each element must have exactly these keys: "
            "opponent (string), kickoff_utc (ISO8601 UTC datetime string), competition (string). "
            f"Include only fixtures in the next {FIXTURE_WINDOW_DAYS} days. Return [] if none found."
        )

    def fixtures_user_prompt(self, today: str) -> str:
        return (
            f"Search for {self.name} upcoming {self.sport} fixtures after {today}. "
            "Return valid JSON array only."
        )

    def briefing_title(self) -> str:
        return f"{self.emoji} {self.name} Daily Briefing"

    def match_day_title(self) -> str:
        return f"{self.emoji} {self.name} {self.match_day_label}!"

    def pre_match_title(self) -> str:
        return f"{self.emoji} {self.kickoff_label} in 15 Minutes!"


def _parse_team(raw: dict[str, object]) -> Team:
    news_focus = raw.get("news_focus", [])
    if not isinstance(news_focus, list):
        raise ValueError(f"Team {raw.get('id')}: news_focus must be a list")
    return Team(
        id=str(raw["id"]),
        name=str(raw["name"]),
        sport=str(raw["sport"]),
        emoji=str(raw.get("emoji", "🏟️")),
        enabled=bool(raw.get("enabled", True)),
        news_focus=tuple(str(item) for item in news_focus),
        match_phrase=str(raw.get("match_phrase", "{name} vs {opponent}")).replace(
            "{name}", str(raw["name"])
        ),
        match_day_label=str(raw.get("match_day_label", "Match Day")),
        kickoff_label=str(raw.get("kickoff_label", "Kickoff")),
    )


def load_teams() -> list[Team]:
    """Load all teams from teams.json."""
    data = json.loads(TEAMS_FILE.read_text())
    teams_raw = data.get("teams", [])
    if not isinstance(teams_raw, list):
        raise ValueError("teams.json: 'teams' must be a list")
    return [_parse_team(item) for item in teams_raw]


def active_teams(selected: tuple[str, ...] = ()) -> list[Team]:
    """Return teams to run, filtered by TEAMS env var and/or CLI selection."""
    teams = load_teams()
    by_id = {team.id: team for team in teams}

    if selected:
        missing = [team_id for team_id in selected if team_id not in by_id]
        if missing:
            known = ", ".join(sorted(by_id))
            raise ValueError(f"Unknown team(s): {', '.join(missing)}. Known: {known}")
        return [by_id[team_id] for team_id in selected if by_id[team_id].enabled]

    env_filter = os.environ.get("TEAMS", "").strip()
    if env_filter:
        ids = [part.strip() for part in env_filter.split(",") if part.strip()]
        return active_teams(tuple(ids))

    return [team for team in teams if team.enabled]

"""
Sports Team Daily Agent
-----------------------
- Fetches daily news via Gemini API (with Google Search) for configured teams
- Fetches upcoming fixtures and schedules Home Assistant notifications:
    • 8:00 AM on match day
    • 15 minutes before start

Run via cron, Docker, or systemd. See README.md for setup.
"""

import os
import sys
import json
import logging
import requests
import click
from typing import Any, Protocol, cast
from google.genai import Client, types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from pathlib import Path

from teams import PROJECT_ROOT, Team, active_teams, load_teams

SCHEDULES_FILE = Path(
    os.environ.get("SCHEDULES_JSON_PATH", "/config/sports_agent/schedules.json")
)


def _load_dotenv() -> None:
    """Load .env from the project root into os.environ (does not override existing vars)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


def _resolve_ha_credentials() -> tuple[str, str]:
    """Prefer explicit HA_URL/HA_TOKEN; fall back to Supervisor proxy in add-ons."""
    url = os.environ.get("HA_URL", "").strip()
    token = os.environ.get("HA_TOKEN", "").strip()
    supervisor = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if token and url:
        return url, token
    if supervisor:
        return url or "http://supervisor/core", supervisor
    return url or "http://homeassistant.local:8123", token


HA_URL, HA_TOKEN = _resolve_ha_credentials()
HA_NOTIFY = os.environ.get("HA_NOTIFY_SERVICE", "notify.mobile_app_deepak_phone")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TIMEZONE = os.environ.get("TIMEZONE", "America/Chicago")
NEWS_MAX_OUTPUT_TOKENS = int(os.environ.get("NEWS_MAX_OUTPUT_TOKENS", "4096"))
FIXTURE_MAX_OUTPUT_TOKENS = int(os.environ.get("FIXTURE_MAX_OUTPUT_TOKENS", "1024"))
NOTIFY_MAX_CHARS = int(os.environ.get("NOTIFY_MAX_CHARS", "1024"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("sports_agent")

_client: Client | None = None


def get_client() -> Client:
    """Return the Gemini client, creating it on first use."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise click.ClickException(
                "GEMINI_API_KEY is not set. Add it to .env or export it in your shell."
            )
        _client = Client(api_key=api_key)
    return _client


class _GeminiModels(Protocol):
    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse: ...


def _generate_content(
    *,
    model: str,
    contents: str,
    config: types.GenerateContentConfig,
) -> types.GenerateContentResponse:
    """Call Gemini; Protocol narrows the SDK's partially-typed generate_content."""
    models: _GeminiModels = cast(_GeminiModels, get_client().models)
    return models.generate_content(model=model, contents=contents, config=config)


def _extract_response_text(response: types.GenerateContentResponse) -> str:
    """Return model text and warn if the response hit token limits."""
    if response.candidates:
        finish = response.candidates[0].finish_reason
        if finish is not None and "MAX_TOKENS" in str(finish):
            log.warning(
                "Gemini response truncated (finish_reason=%s). "
                "Increase NEWS_MAX_OUTPUT_TOKENS if needed.",
                finish,
            )
    return (response.text or "").strip()


def _gemini_web_search(
    user_prompt: str,
    system_instruction: str,
    *,
    max_output_tokens: int,
) -> str:
    """Call Gemini with Google Search grounding and return response text."""
    response = _generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return _extract_response_text(response)


def _today_strings() -> tuple[str, str]:
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.strftime("%B %d, %Y"), now.strftime("%Y-%m-%d")


def _yesterday_long() -> str:
    yesterday = datetime.now(ZoneInfo(TIMEZONE)) - timedelta(days=1)
    return yesterday.strftime("%B %d, %Y")


def _ha_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def ha_notify(title: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Fire a Home Assistant notification via REST API."""
    url = f"{HA_URL}/api/services/{HA_NOTIFY.replace('.', '/', 1)}"
    payload: dict[str, Any] = {"title": title, "message": message}
    if data:
        payload["data"] = data
    try:
        r = requests.post(url, headers=_ha_headers(), json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"HA notification sent: {title}")
    except Exception as e:
        log.error(f"HA notification failed: {e}")


def fetch_news_summary(team: Team) -> str:
    """Use Gemini with Google Search to get today's news summary for a team."""
    log.info("Fetching news for %s via Gemini...", team.name)
    today_long, _ = _today_strings()

    summary = _gemini_web_search(
        user_prompt=team.news_user_prompt(today_long, _yesterday_long()),
        system_instruction=team.news_system_instruction(),
        max_output_tokens=NEWS_MAX_OUTPUT_TOKENS,
    )
    return summary if summary else "No news summary available."


def send_news_notification(team: Team, summary: str) -> str:
    """Push a news summary to Home Assistant."""
    short = (
        summary[:NOTIFY_MAX_CHARS] + "..."
        if len(summary) > NOTIFY_MAX_CHARS
        else summary
    )
    ha_notify(
        title=team.briefing_title(),
        message=short,
        data={"tag": team.ha_tag, "group": team.ha_group},
    )
    return summary


def send_daily_news(team: Team) -> str:
    """Morning routine: fetch news + send HA notification."""
    summary = fetch_news_summary(team)
    send_news_notification(team, summary)
    log.info("Daily news notification sent for %s.", team.name)
    return summary


def run_news_adhoc(teams: list[Team], *, notify: bool) -> None:
    """Fetch today's news; print to stdout and optionally notify HA."""
    for index, team in enumerate(teams):
        if index:
            print()
        if len(teams) > 1:
            print(f"=== {team.name} ===")
        summary = fetch_news_summary(team)
        print(summary)
        if notify:
            send_news_notification(team, summary)
            log.info("News notification sent for %s.", team.name)


def fetch_fixtures(team: Team) -> list[dict[str, str]]:
    """Use Gemini with Google Search to extract upcoming fixtures for a team."""
    log.info("Fetching fixtures for %s via Gemini...", team.name)
    _, today_short = _today_strings()

    raw = _gemini_web_search(
        user_prompt=team.fixtures_user_prompt(today_short),
        system_instruction=team.fixtures_system_instruction(),
        max_output_tokens=FIXTURE_MAX_OUTPUT_TOKENS,
    )

    try:
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        fixtures = cast(list[dict[str, str]], json.loads(raw))
        log.info("Parsed %d upcoming fixtures for %s.", len(fixtures), team.name)
        return fixtures
    except json.JSONDecodeError as e:
        log.error(
            "Failed to parse fixtures JSON for %s: %s\nRaw: %s", team.name, e, raw
        )
        return []


def _fixture_rows(team: Team, fixtures: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize fixture dicts with local kickoff times for HA attributes."""
    tz = ZoneInfo(TIMEZONE)
    rows: list[dict[str, str]] = []
    for fixture in fixtures:
        try:
            kickoff_utc = datetime.fromisoformat(fixture["kickoff_utc"])
            if kickoff_utc.tzinfo is None:
                kickoff_utc = kickoff_utc.replace(tzinfo=ZoneInfo("UTC"))
            kickoff_local = kickoff_utc.astimezone(tz)
            opponent = fixture.get("opponent", "Unknown")
            competition = fixture.get("competition", "")
            rows.append(
                {
                    "opponent": opponent,
                    "competition": competition,
                    "kickoff_utc": kickoff_utc.isoformat(),
                    "kickoff_local": kickoff_local.strftime("%Y-%m-%d %I:%M %p"),
                    "matchup": team.match_phrase.format(opponent=opponent),
                }
            )
        except Exception as e:
            log.error("Error parsing fixture for %s: %s — %s", team.name, fixture, e)
    rows.sort(key=lambda row: row["kickoff_utc"])
    return rows


def _schedule_payload(team: Team, fixtures: list[dict[str, str]]) -> dict[str, Any]:
    """Build schedule payload for one team."""
    rows = _fixture_rows(team, fixtures)
    now_iso = datetime.now(ZoneInfo(TIMEZONE)).isoformat()

    if rows:
        next_row = rows[0]
        state = (
            f"{next_row['matchup']} — {next_row['kickoff_local']} "
            f"({next_row['competition']})".strip()
        )
        next_kickoff_utc = next_row["kickoff_utc"]
        next_opponent = next_row["opponent"]
        next_competition = next_row["competition"]
    else:
        state = "No upcoming matches"
        next_kickoff_utc = None
        next_opponent = None
        next_competition = None

    return {
        "state": state,
        "team_id": team.id,
        "team_name": team.name,
        "sport": team.sport,
        "fixture_count": len(rows),
        "fixtures": rows,
        "next_opponent": next_opponent,
        "next_kickoff_utc": next_kickoff_utc,
        "next_competition": next_competition,
        "last_updated": now_iso,
    }


def write_schedules_file(schedules: dict[str, dict[str, Any]]) -> None:
    """Write schedule data for the HA integration to read."""
    try:
        SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULES_FILE.write_text(
            json.dumps(schedules, indent=2) + "\n", encoding="utf-8"
        )
        log.info("Wrote schedules for %d team(s) to %s", len(schedules), SCHEDULES_FILE)
    except OSError as e:
        log.error("Failed to write schedules file %s: %s", SCHEDULES_FILE, e)


def schedule_match_notifications(
    scheduler: BlockingScheduler, team: Team, fixtures: list[dict[str, str]]
) -> None:
    """Schedule match-day and pre-start notifications for a team."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    match_line = team.match_phrase

    for fixture in fixtures:
        try:
            kickoff_utc = datetime.fromisoformat(fixture["kickoff_utc"])
            if kickoff_utc.tzinfo is None:
                kickoff_utc = kickoff_utc.replace(tzinfo=ZoneInfo("UTC"))
            kickoff_local = kickoff_utc.astimezone(tz)

            opponent = fixture.get("opponent", "Unknown")
            competition = fixture.get("competition", "")
            matchup = match_line.format(opponent=opponent)
            time_label = kickoff_local.strftime("%I:%M %p")

            match_day_8am = kickoff_local.replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            if match_day_8am > now:
                scheduler.add_job(
                    ha_notify,
                    trigger=DateTrigger(run_date=match_day_8am, timezone=tz),
                    args=[
                        team.match_day_title(),
                        f"{matchup} today — {competition}.\n"
                        f"{team.kickoff_label} at {time_label} local time. {team.emoji}",
                    ],
                    id=f"{team.id}_matchday_{kickoff_local.date()}_{opponent}_8am",
                    replace_existing=True,
                )
                log.info(
                    "Scheduled 8AM notification for %s vs %s on %s",
                    team.name,
                    opponent,
                    match_day_8am,
                )

            pre_match = kickoff_local - timedelta(minutes=15)
            if pre_match > now:
                scheduler.add_job(
                    ha_notify,
                    trigger=DateTrigger(run_date=pre_match, timezone=tz),
                    args=[
                        team.pre_match_title(),
                        f"{matchup} — {competition} starts at {time_label}. "
                        f"Get ready! {team.emoji}",
                    ],
                    id=f"{team.id}_matchday_{kickoff_local.date()}_{opponent}_15min",
                    replace_existing=True,
                )
                log.info(
                    "Scheduled 15-min notification for %s vs %s at %s",
                    team.name,
                    opponent,
                    pre_match,
                )

        except Exception as e:
            log.error("Error scheduling fixture for %s: %s — %s", team.name, fixture, e)


def refresh_fixtures(
    scheduler: BlockingScheduler,
    team: Team,
    schedules: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Refresh fixtures for one team and reschedule match notifications."""
    fixtures = fetch_fixtures(team)
    payload = _schedule_payload(team, fixtures)
    if schedules is not None:
        schedules[team.id] = payload
    else:
        write_schedules_file({team.id: payload})
    if fixtures:
        schedule_match_notifications(scheduler, team, fixtures)
    else:
        log.warning("No upcoming fixtures found for %s.", team.name)


def refresh_all_fixtures(scheduler: BlockingScheduler) -> None:
    """Refresh fixtures for all active teams."""
    schedules: dict[str, dict[str, Any]] = {}
    for team in active_teams():
        refresh_fixtures(scheduler, team, schedules)
    write_schedules_file(schedules)


def run_scheduler() -> None:
    """Start the scheduled agent for all active teams."""
    teams = active_teams()
    if not teams:
        raise click.ClickException(
            "No active teams configured. Add teams via the Sports Team Agent integration."
        )

    tz = ZoneInfo(TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    for team in teams:
        scheduler.add_job(
            send_daily_news,
            trigger=CronTrigger(hour=7, minute=30, timezone=tz),
            args=[team],
            id=f"{team.id}_daily_news",
            replace_existing=True,
        )
        log.info("Scheduled daily news at 7:30 AM for %s", team.name)

    scheduler.add_job(
        refresh_all_fixtures,
        trigger=CronTrigger(hour=6, minute=0, timezone=tz),
        args=[scheduler],
        id="daily_fixture_refresh",
        replace_existing=True,
    )
    log.info("Scheduled fixture refresh at 6:00 AM")

    log.info("Running initial fixture refresh...")
    refresh_all_fixtures(scheduler)

    team_names = ", ".join(team.name for team in teams)
    log.info("Sports agent started for: %s. Press Ctrl+C to stop.", team_names)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Sports agent stopped.")


def _resolve_teams(team_ids: tuple[str, ...]) -> list[Team]:
    try:
        teams = active_teams(team_ids)
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    if not teams:
        raise click.ClickException("No enabled teams matched your selection.")
    return teams


@click.group()
def cli() -> None:
    """Sports team agent — news briefings and match notifications."""


@cli.command()
def run() -> None:
    """Start the scheduled agent for all active teams (default)."""
    run_scheduler()


@cli.command("list-teams")
def list_teams_cmd() -> None:
    """List configured teams and whether they are active."""
    env_filter = os.environ.get("TEAMS", "").strip()
    active_ids = {team.id for team in active_teams()}
    for team in load_teams():
        if team.id in active_ids:
            status = "active"
        elif not team.enabled:
            status = "disabled"
        elif env_filter:
            status = "filtered out by TEAMS"
        else:
            status = "inactive"
        click.echo(f"{team.id}: {team.name} ({team.sport}) [{status}]")


@cli.command()
@click.option(
    "--team",
    "-t",
    "team_ids",
    multiple=True,
    help="Team id from teams.json (repeatable). Default: all active teams.",
)
@click.option(
    "--notify",
    is_flag=True,
    help="Also push summaries to Home Assistant",
)
def news(team_ids: tuple[str, ...], notify: bool) -> None:
    """Fetch today's news summary and print to stdout."""
    run_news_adhoc(_resolve_teams(team_ids), notify=notify)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("run")
    cli()

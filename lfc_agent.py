"""
LFC Daily Agent
---------------
- Fetches daily Liverpool FC news via Gemini API (with Google Search)
- Fetches upcoming LFC fixtures
- Schedules Home Assistant notifications:
    • 8:00 AM on match day
    • 15 minutes before kickoff

Run via cron or as a systemd service. See README.md for setup.
"""

import os
import json
import logging
import requests
from typing import Any, Protocol, cast
from google.genai import Client, types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

############################################################################
# Config
############################################################################
HA_URL        = os.environ.get("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN      = os.environ.get("HA_TOKEN", "")          # Long-lived HA token
HA_NOTIFY     = os.environ.get("HA_NOTIFY_SERVICE", "notify.mobile_app_deepak_phone")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL  = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TIMEZONE      = os.environ.get("TIMEZONE", "America/Chicago")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("lfc_agent")

client = Client(api_key=GEMINI_KEY)


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
    models: _GeminiModels = cast(_GeminiModels, client.models)
    return models.generate_content(model=model, contents=contents, config=config)


def _gemini_web_search(user_prompt: str, system_instruction: str) -> str:
    """Call Gemini with Google Search grounding and return response text."""
    response = _generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=1024,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return (response.text or "").strip()

############################################################################
# Home Assistant Notifications
############################################################################

def ha_notify(title: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Fire a Home Assistant notification via REST API."""
    url = f"{HA_URL}/api/services/{HA_NOTIFY.replace('.', '/', 1)}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"title": title, "message": message}
    if data:
        payload["data"] = data
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"HA notification sent: {title}")
    except Exception as e:
        log.error(f"HA notification failed: {e}")

############################################################################
# News Summary
############################################################################

def fetch_lfc_news_summary() -> str:
    """Use Gemini with Google Search to get today's LFC news summary."""
    log.info("Fetching LFC news via Gemini...")
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%B %d, %Y")

    summary = _gemini_web_search(
        user_prompt=(
            f"Search the web and give me a Liverpool FC daily news summary for {today}. "
            "Include any recent match results, transfer news, injuries, and the next fixture."
        ),
        system_instruction=(
            "You are a Liverpool FC news assistant. Your job is to search for the latest "
            "Liverpool FC news and produce a concise daily briefing. "
            "Focus on: match results, injuries, transfers, manager quotes, and upcoming fixtures. "
            "Be factual, concise, and well-structured. Use bullet points. "
            "Always end with the next upcoming match details if available."
        ),
    )

    return summary if summary else "No news summary available."


def send_daily_news():
    """Morning routine: fetch news + send HA notification."""
    summary = fetch_lfc_news_summary()
    # Truncate for phone notification (keep it readable)
    short = summary[:500] + "..." if len(summary) > 500 else summary
    ha_notify(
        title="🔴 LFC Daily Briefing",
        message=short,
        data={"tag": "lfc_daily_news", "group": "lfc"}
    )
    log.info("Daily news notification sent.")
    return summary


############################################################################
# Fixture Fetcher
############################################################################

def fetch_lfc_fixtures() -> list[dict[str, str]]:
    """
    Use Gemini with Google Search to extract upcoming LFC fixtures.
    Returns a list of dicts: [{opponent, kickoff_utc, competition}, ...]
    """
    log.info("Fetching LFC fixtures via Gemini...")
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")

    raw = _gemini_web_search(
        user_prompt=(
            f"Search for Liverpool FC upcoming fixtures after {today}. "
            "Return valid JSON array only."
        ),
        system_instruction=(
            "You are a fixture data extractor. Search for Liverpool FC upcoming fixtures. "
            "Respond ONLY with a valid JSON array. No preamble, no markdown fences. "
            "Each element must have exactly these keys: "
            "opponent (string), kickoff_utc (ISO8601 UTC datetime string), competition (string). "
            "Include only matches in the next 14 days. Return [] if none found."
        ),
    )

    try:
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        fixtures = cast(list[dict[str, str]], json.loads(raw))
        log.info(f"Parsed {len(fixtures)} upcoming fixtures.")
        return fixtures
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse fixtures JSON: {e}\nRaw: {raw}")
        return []


def schedule_match_notifications(
    scheduler: BlockingScheduler, fixtures: list[dict[str, str]]
) -> None:
    """
    For each fixture, schedule:
      1. A 8:00 AM notification on match day
      2. A 15-min-before kickoff notification
    """
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)

    for fixture in fixtures:
        try:
            kickoff_utc = datetime.fromisoformat(fixture["kickoff_utc"])
            if kickoff_utc.tzinfo is None:
                kickoff_utc = kickoff_utc.replace(tzinfo=ZoneInfo("UTC"))
            kickoff_local = kickoff_utc.astimezone(tz)

            opponent    = fixture.get("opponent", "Unknown")
            competition = fixture.get("competition", "")

            # ── 8 AM match day notification ──────────────────────────────────
            match_day_8am = kickoff_local.replace(hour=8, minute=0, second=0, microsecond=0)
            if match_day_8am > now:
                scheduler.add_job(
                    ha_notify,
                    trigger=DateTrigger(run_date=match_day_8am, timezone=tz),
                    args=[
                        f"⚽ LFC Match Day!",
                        f"Liverpool vs {opponent} today — {competition}.\n"
                        f"Kickoff at {kickoff_local.strftime('%I:%M %p')} local time. YNWA! 🔴"
                    ],
                    id=f"matchday_{kickoff_local.date()}_{opponent}_8am",
                    replace_existing=True
                )
                log.info(f"Scheduled 8AM notification for {opponent} on {match_day_8am}")

            # ── 15-min before kickoff notification ───────────────────────────
            pre_match = kickoff_local - timedelta(minutes=15)
            if pre_match > now:
                scheduler.add_job(
                    ha_notify,
                    trigger=DateTrigger(run_date=pre_match, timezone=tz),
                    args=[
                        f"🔴 Kickoff in 15 Minutes!",
                        f"Liverpool vs {opponent} — {competition} starts at "
                        f"{kickoff_local.strftime('%I:%M %p')}. Get ready! YNWA! 🏆"
                    ],
                    id=f"matchday_{kickoff_local.date()}_{opponent}_15min",
                    replace_existing=True
                )
                log.info(f"Scheduled 15-min notification for {opponent} at {pre_match}")

        except Exception as e:
            log.error(f"Error scheduling fixture {fixture}: {e}")


def refresh_fixtures(scheduler: BlockingScheduler):
    """Refresh fixtures every day and reschedule match notifications."""
    fixtures = fetch_lfc_fixtures()
    if fixtures:
        schedule_match_notifications(scheduler, fixtures)
    else:
        log.warning("No upcoming fixtures found.")


def main():
    """Main entry point."""
    tz = ZoneInfo(TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Daily news at 7:30 AM
    scheduler.add_job(
        send_daily_news,
        trigger=CronTrigger(hour=7, minute=30, timezone=tz),
        id="daily_lfc_news",
        replace_existing=True
    )
    log.info("Scheduled daily news at 7:30 AM")

    # Refresh fixtures daily at 6:00 AM (before any match-day notifications)
    scheduler.add_job(
        lambda: refresh_fixtures(scheduler),
        trigger=CronTrigger(hour=6, minute=0, timezone=tz),
        id="daily_fixture_refresh",
        replace_existing=True
    )
    log.info("Scheduled fixture refresh at 6:00 AM")

    # Run fixture refresh immediately on startup
    log.info("Running initial fixture refresh...")
    refresh_fixtures(scheduler)

    log.info("LFC Agent started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("LFC Agent stopped.")


if __name__ == "__main__":
    main()

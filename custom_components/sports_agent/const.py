"""Constants for the Sports Team Agent integration."""

DOMAIN = "sports_agent"

CONF_ENABLED = "enabled"
CONF_EMOJI = "emoji"
CONF_ID = "id"
CONF_KICKOFF_LABEL = "kickoff_label"
CONF_MATCH_DAY_LABEL = "match_day_label"
CONF_MATCH_PHRASE = "match_phrase"
CONF_NAME = "name"
CONF_NEWS_FOCUS = "news_focus"
CONF_PRESET = "preset"
CONF_SPORT = "sport"

PRESET_CUSTOM = "custom"

SPORT_FOOTBALL = "football"
SPORT_CRICKET = "cricket"

DEFAULT_EMOJI = "🏟️"
DEFAULT_KICKOFF_LABEL = "Kickoff"
DEFAULT_MATCH_DAY_LABEL = "Match Day"
DEFAULT_MATCH_PHRASE = "{name} vs {opponent}"

CONFIG_SUBDIR = "sports_agent"
TEAMS_FILENAME = "teams.json"
SCHEDULES_FILENAME = "schedules.json"

UPDATE_INTERVAL_SECONDS = 300

TEAM_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

SPORT_ICONS = {
    SPORT_FOOTBALL: "mdi:soccer",
    SPORT_CRICKET: "mdi:cricket",
}

TEAM_PRESETS: dict[str, dict[str, object]] = {
    "liverpool-fc": {
        CONF_ID: "liverpool-fc",
        CONF_NAME: "Liverpool FC",
        CONF_SPORT: SPORT_FOOTBALL,
        CONF_EMOJI: "⚽",
        CONF_NEWS_FOCUS: [
            "match results",
            "injuries",
            "transfers",
            "manager quotes",
            "upcoming fixtures",
        ],
        CONF_MATCH_PHRASE: "Liverpool vs {opponent}",
        CONF_MATCH_DAY_LABEL: "Match Day",
        CONF_KICKOFF_LABEL: "Kickoff",
    },
    "india-cricket": {
        CONF_ID: "india-cricket",
        CONF_NAME: "India men's cricket team",
        CONF_SPORT: SPORT_CRICKET,
        CONF_EMOJI: "🏏",
        CONF_NEWS_FOCUS: [
            "recent match and series results",
            "injury and squad updates",
            "selection and captaincy news",
            "upcoming fixtures and series schedule",
        ],
        CONF_MATCH_PHRASE: "India vs {opponent}",
        CONF_MATCH_DAY_LABEL: "Match Day",
        CONF_KICKOFF_LABEL: "Start",
    },
    "argentina-football": {
        CONF_ID: "argentina-football",
        CONF_NAME: "Argentina football team",
        CONF_SPORT: SPORT_FOOTBALL,
        CONF_EMOJI: "⚽",
        CONF_NEWS_FOCUS: [
            "recent match and series results",
            "injury and squad updates",
            "selection and captaincy news",
            "upcoming fixtures and series schedule",
        ],
        CONF_MATCH_PHRASE: "Argentina vs {opponent}",
        CONF_MATCH_DAY_LABEL: "Match Day",
        CONF_KICKOFF_LABEL: "Start",
    },
}

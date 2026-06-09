#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Sports Team Agent..."

export GEMINI_API_KEY="$(bashio::config 'gemini_api_key')"
export HA_NOTIFY_SERVICE="$(bashio::config 'ha_notify_service')"
export TIMEZONE="$(bashio::config 'timezone')"
export GEMINI_MODEL="$(bashio::config 'gemini_model')"

# homeassistant_api: true — SUPERVISOR_TOKEN works against the Core API proxy
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"

SHARED_DIR="/config/sports_agent"
TEAMS_JSON="${SHARED_DIR}/teams.json"
SCHEDULES_JSON="${SHARED_DIR}/schedules.json"

mkdir -p "${SHARED_DIR}"

if ! bashio::fs.file_exists "${TEAMS_JSON}"; then
  cp /app/teams.default.json "${TEAMS_JSON}"
  bashio::log.info "Created default teams.json at ${TEAMS_JSON}"
  bashio::log.info "Install the Sports Team Agent integration to manage teams in the UI"
fi

export TEAMS_JSON_PATH="${TEAMS_JSON}"
export SCHEDULES_JSON_PATH="${SCHEDULES_JSON}"

if [ -z "${GEMINI_API_KEY}" ]; then
  bashio::log.fatal "gemini_api_key is required — set it in the add-on Configuration tab"
fi

cd /app || exit 1
exec python3 src/sports_agent.py run

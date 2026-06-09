# Sports Team Agent

Get daily sports briefings and match-day push notifications on your phone through Home Assistant.

## Features

- **7:30 AM daily briefing** per enabled team (match update + news)
- **8:00 AM match-day reminder** on fixture days
- **15-minute pre-kickoff alert**
- **6:00 AM fixture refresh** (next 14 days)
- **Schedule sensors** — one entity per team via the custom integration

## Setup

### 1. Install the add-on

**Settings → Add-ons → Sports Team Agent** — set Gemini API key, timezone, and notify service.

### 2. Install the integration

Copy `custom_components/sports_agent` into your HA `config/custom_components/` folder, then restart Home Assistant.

### 3. Add teams in the UI

1. **Settings → Devices & services → Add integration**
2. Search **Sports Team Agent**
3. Pick a preset (Liverpool, India cricket, Argentina) or **Custom team**
4. Repeat for each team you want to follow

The integration writes `/config/sports_agent/teams.json` for the add-on. Restart the add-on after adding teams.

### 4. Schedule entities

Each team appears as a device with a **Schedule** sensor, e.g.:

- `sensor.liverpool_fc_schedule`

Sensors update when the add-on refreshes fixtures (on start and daily at 6:00 AM).

## Add-on configuration

| Option | Required | Description |
| --- | --- | --- |
| Gemini API key | Yes | From [Google AI Studio](https://aistudio.google.com/apikey) |
| Timezone | Yes | Your local IANA timezone |
| Notify service | Yes | e.g. `notify.mobile_app_pixel_8` |
| Gemini model | No | Default `gemini-2.5-flash` |

Teams are **not** configured on the add-on tab — use the integration UI.

## Editing or removing teams

- **Settings → Devices & services → Sports Team Agent → Configure** on a team device
- Or delete the integration entry to remove a team

## Authentication

This add-on uses `homeassistant_api: true`, so it talks to Home Assistant through the Supervisor proxy. You do **not** need a long-lived access token.

## Logs

**Settings → Add-ons → Sports Team Agent → Log**

## Support

[GitHub repository](https://github.com/deepakranganathan/ha-sports-agent)

# Sports Team Agent

Get daily sports briefings and match-day push notifications on your phone through Home Assistant.

## Features

- **7:30 AM daily briefing** per enabled team (match update + news)
- **8:00 AM match-day reminder** on fixture days
- **15-minute pre-kickoff alert**
- **6:00 AM fixture refresh** (next 14 days)

Built-in teams: Liverpool FC, India cricket, Argentina football. Edit `teams.json` to customize.

## Configuration

| Option | Required | Description |
| --- | --- | --- |
| Gemini API key | Yes | From [Google AI Studio](https://aistudio.google.com/apikey) |
| Timezone | Yes | Your local IANA timezone |
| Notify service | Yes | e.g. `notify.mobile_app_pixel_8` |
| Teams filter | No | Comma-separated ids; empty = all enabled teams |
| Gemini model | No | Default `gemini-2.5-flash` |

### Finding your notify service

1. **Developer Tools → Services**
2. Search `notify`
3. Use the full name, e.g. `notify.mobile_app_your_phone`

## Customizing teams

On first start the add-on copies a default `teams.json` into its data folder (`/data/teams.json`).

To edit teams:

1. Install **Studio Code Server** or **SSH & Web Terminal**
2. Open the add-on data directory, or browse to `addon_configs/sports_agent` if you mapped addon config
3. Edit `teams.json` and restart the add-on

Team ids must match the `id` field in `teams.json` (e.g. `liverpool-fc`, `india-cricket`).

## Authentication

This add-on uses `homeassistant_api: true`, so it talks to Home Assistant through the Supervisor proxy (`http://supervisor/core`). You do **not** need to create a long-lived access token.

## Logs

**Settings → Add-ons → Sports Team Agent → Log** shows scheduler activity and notification results.

## Support

[GitHub repository](https://github.com/deepakranganathan/ha-sports-agent)

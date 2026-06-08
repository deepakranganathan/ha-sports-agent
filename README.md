# Sports Team Agent

Home Assistant add-on that delivers daily sports briefings and match-day push notifications via Gemini.

## Install

1. In HA: **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add `https://github.com/deepakranganathan/ha-sports-agent`
3. Refresh the store, install **Sports Team Agent**, and start it
4. Set your **Gemini API key**, **timezone**, and **notify service** on the Configuration tab

### Local install (no GitHub)

Copy the `sports_agent/` folder into your HA `addons` share, then install from **Local add-ons**.

## Documentation

See [sports_agent/DOCS.md](sports_agent/DOCS.md) for configuration, team customization, and logs.

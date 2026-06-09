# Sports Team Agent

Home Assistant add-on + custom integration for daily sports briefings, match alerts, and schedule sensors.

## Install

### Add-on

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add `https://github.com/deepakranganathan/ha-sports-agent`
3. Install **Sports Team Agent**, set Gemini API key / timezone / notify service, and start it

### Integration (team management UI)

Copy the integration into Home Assistant:

```bash
# From your HA config directory (Samba, SSH, or Studio Code Server)
cp -r custom_components/sports_agent /config/custom_components/
```

Restart Home Assistant, then:

1. **Settings → Devices & services → Add integration**
2. Search **Sports Team Agent**
3. Add each team (preset or custom)

The integration syncs teams to `/config/sports_agent/teams.json` for the add-on worker.

## Documentation

- [sports_agent/DOCS.md](sports_agent/DOCS.md) — add-on configuration and logs
- Integration UI — add, edit, and remove teams under **Devices & services**

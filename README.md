# Announcement Maker (Home Assistant add-on)

Build AI-written voice announcements (weather, news, welcome home, roasts, whatever) by tapping checkboxes. The add-on writes the Home Assistant script and pushes it straight into HA.

## Install
1. Home Assistant: **Settings > Add-ons > Add-on Store > three dots > Repositories**, add `https://github.com/YOURNAME/ha-announcement-maker`.
2. Install **Announcement Maker**, open the **Configuration** tab, fill in your entities (see `DOCS.md`), save, start.
3. Open **Announcements** in the sidebar.

Requires an `ai_task` entity (Gemini, OpenAI, etc.) and a TTS engine. Alexa speakers need the `alexa_media` custom integration.

## Auth
By default the add-on uses the Supervisor API, so no token is needed. If your install refuses that, create a long-lived token (Profile > Security) and put it in `ha_token`.

See `examples/jon-options.yaml` for a fully filled-in config.

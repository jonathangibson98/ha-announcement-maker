# Announcement Maker (Home Assistant add-on)

Build AI-written voice announcements (weather, news, welcome home, roasts, whatever) by tapping checkboxes. The add-on writes the Home Assistant script and pushes it straight into HA.

## Install
1. Home Assistant: **Settings > Add-ons > Add-on Store > three dots > Repositories**, add `https://github.com/YOURNAME/ha-announcement-maker`.
2. Install and start **Announcement Maker**, then open **Announcements** in the sidebar.
3. Tap **Settings** inside the app. Every field is a searchable picker filtered to the right type (calendar.* for calendars, ai_task.* for AI Task, etc). **Auto-fill empty** fills anything with only one match.

Requires an `ai_task` entity (Gemini, OpenAI, etc.) and a TTS engine. Alexa speakers need the `alexa_media` custom integration.

## Auth
By default the add-on uses the Supervisor API, so no token is needed. If your install refuses that, create a long-lived token (Profile > Security) and put it in `ha_token`.

Settings has Export/Import (JSON). See `examples/jon-settings.json` for a filled-in example you can paste into Import.

# Announcement Maker

All setup happens inside the app on the **Settings** tab, not in this Configuration tab.

- Each field is a search box limited to the right entity type. Tap one, pick an entity, it becomes a chip. Tap the chip to remove it.
- **Auto-fill empty** fills single-choice fields that only have one match.
- **Custom sources** cover anything else: label, entity, optional attribute (concerts, sports, PS5...).
- **Export / Import** moves your settings as JSON.
- Required to generate: AI Task, text-to-speech engine, main speaker.
- Personality dropdown (optional) needs an input_select with options `Hype`, `Roast`, `Sweetie Pie`.

The only add-on options are `ha_token`, `ha_url` and `helper_ai_task_entity`. Leave them blank unless Push to Home Assistant fails with the default Supervisor access.

## Tabs

- **Create:** pick data, personality, then type **What should it do?** in plain words (for example: "look at the weather for the week, but only if my work calendar has something on"). Calendar events are grouped by calendar, so the AI can tell your work calendar from the others.
- **Helper:** (1) describe what you want and the AI writes the instructions and ticks the data it needs; (2) test an entity and add it as a custom source.
- **Settings:** your entities, notify targets, styles, custom sources.

Phone notifications: entities (`notify.jon`) and services (`notify.mobile_app_*`, shown as "service") both work, and you can type an id that isn't listed.

To use a different AI Task for the helpers, set `helper_ai_task_entity` in the add-on Configuration tab. Blank means the main AI Task.

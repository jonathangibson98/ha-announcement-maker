# Announcement Maker

Every option is optional except `ai_task_entity`, `tts_entity` and `speaker`. A checkbox only shows in the app if its entity is set.

| Option | What it is |
|---|---|
| `ai_task_entity` | AI Task entity that writes the text, e.g. `ai_task.gemini_pro_ai_task` |
| `tts_entity` | TTS engine, e.g. `tts.home_assistant_cloud` |
| `speaker` | Main media player for speech (volume and "finished talking" are tracked on it) |
| `alexa_targets` | Extra Alexa devices (needs `alexa_media`) |
| `notify_targets` | notify entities for the phone banner |
| `music_players` | Players to pause while talking; the first one is resumed |
| `talking_flag` | Optional input_boolean turned on while speaking |
| `personality_select` | Optional input_select with options `Hype`, `Roast`, `Sweetie Pie` |
| `household_context` | Free text about who lives with you, pets, friends |
| `combined_info_entity` / `_attribute` | Optional entity (and attribute) holding more context text |
| `locations_entity` | Sensor whose attributes are name: location. Blank = use `person.*` |
| `weather_entity`, `inside_temp_entity` | Weather and indoor temp |
| `news_entity` | Sensor with an `entries` attribute (feedparser style) |
| `calendar_entities` | Calendars to read for the next 7 days |
| `todo_entity` | To-do list entity |
| `trash_entity` | Entity that is `on` when pickup is tomorrow |
| `custom_sources` | Anything else: `label`, `entity`, optional `attribute` |
| `hype_style`, `roast_style`, `sweet_style` | Default personality text |
| `ha_token`, `ha_url` | Only if the Supervisor API doesn't work for you |

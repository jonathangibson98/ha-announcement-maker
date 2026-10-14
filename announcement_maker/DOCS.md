# Announcement Maker

All setup happens inside the app on the **Settings** tab, not in this Configuration tab.

- Each field is a search box limited to the right entity type. Tap one, pick an entity, it becomes a chip. Tap the chip to remove it.
- **Auto-fill empty** fills single-choice fields that only have one match.
- **Custom sources** cover anything else: label, entity, optional attribute (concerts, sports, PS5...).
- **Export / Import** moves your settings as JSON.
- Required to generate: AI Task, text-to-speech engine, main speaker.
- Personality dropdown (optional) needs an input_select with options `Hype`, `Roast`, `Sweetie Pie`.

The only add-on options are `ha_token` and `ha_url`. Leave them blank unless Push to Home Assistant fails with the default Supervisor access.

## AI source helper

On the Settings tab, pick any entity, type what you want from it ("days left until the concert"), and tap **Test it**. Your AI Task reads the entity and suggests a label and attribute, shows a live preview, and **Add as custom source** fills it in for you. Set a separate AI Task for the helper in that section, or leave it blank to use the main one. Tap **Save settings** afterward.

# Settings

A script's settings come from the account file's `script.settings` object. A script can declare them with a schema, which checks them before login, fills in defaults, and writes missing ones into the account file.

- [Where settings come from](#where-settings-come-from)
- [SettingsBag](#settingsbag)
- [SettingDef](#settingdef)
- [Schemas](#schemas)
- [Saved settings: `settings_store`](#saved-settings-settings_store)
- [Global settings](#global-settings)
- [Account file keys the client reads](#account-file-keys-the-client-reads)

## Where settings come from

```jsonc
// accounts/alice.jsonc
{
    "username": "alice",
    "password": "...",
    "script": {
        "file": "examples/power_miner.py",
        "progressReportMinutes": 20,
        "settings": {
            "Power miner": { "rocks": ["Copper", "Tin"], "radius": 10 },
            "laps": 10
        }
    }
}
```

- A script with `BOT = define_bot(name=...)` reads only the object under its name: `script.settings["Power miner"]` above. One account file can so keep the settings of several bots.
- A script without `BOT` reads the whole `script.settings` object: `settings.laps` above.

Both read them as the builtin `settings`; a bot also has them as `self.settings`.

## `SettingsBag`

The type of `settings`.

| Member | Gives |
|---|---|
| `settings.<key>` | The value. A key that isn't there raises `AttributeError` |
| `settings.get(key, default=None)` | The value, or `default` |
| `key in settings` | Whether the key is there |
| `settings.bool(key, fallback=False)` | The value when it's a `bool`, else `fallback` |
| `settings.num(key, fallback=0)` | The value when it's an `int` or `float` (not a `bool`), else `fallback` |
| `settings.str(key, fallback='')` | The value when it's a `str`, else `fallback` |
| `settings.list(key, fallback=None)` | The value when it's a `list`, else `fallback`, or `[]` when that's `None` |
| `settings.tile(key, fallback)` | The value when it's a [`Tile`](geometry.md#tile), else `fallback`. Only a schema's `'tile'` setting becomes a `Tile` |
| `settings.raw()` | A shallow copy of the values, as a `dict` |

Keys are used as the account file writes them, case included.

## `SettingDef`

```python
SettingDef(type=None, default=None, label=None, min=None, max=None, help=None, options=None, option_labels=None, group=None,
           show_if=None, step=None, color=None, options_from=None, csv_toggle=None)
```

One declared setting. `type` is required, and must be one of the types below, or `ValueError`.

| Parameter | Meaning |
|---|---|
| `type` | `'boolean'`, `'number'`, `'string'`, `'string[]'` or `'tile'` |
| `default` | The value when the account file leaves the setting out. `None` means no default: the setting reads as `None` |
| `label`, `help`, `group` | Text for people reading the schema |
| `min`, `max` | Bounds for a `'number'`, both included |
| `options` | The allowed values of a `'string'`, or of each item of a `'string[]'` |
| `option_labels` | A `dict` of option to display text, for your own use |
| `show_if` | `{'key': name, 'any_of': [values]}`: the setting matters only while the setting `name` has one of the values, as rs2b0t's panel shows it. Nothing hides settings here, so it documents the schema; but `name` must be in the same schema, or loading fails with `ValueError` |
| `step`, `color`, `options_from`, `csv_toggle` | Only shape rs2b0t's panel. They're kept so its schemas port unchanged |

All fields are attributes of the same names.

### What each type accepts

| Type | Accepts | Reads as |
|---|---|---|
| `'boolean'` | `true` or `false` | `bool` |
| `'number'` | Any number, within `min` and `max` | `int` or `float` |
| `'string'` | A string; one of `options` when given, matched without regard to case, or `''`, which leaves it unset as a panel's blank choice does | `str`, in the schema's spelling of the option |
| `'string[]'` | A list of strings, or one comma-separated string | `list` of `str`, each matched to `options` as above |
| `'tile'` | `[x, z]`, `[x, z, level]`, `"x,z"`, `"x,z,level"` or `{"x": ..., "z": ..., "level": ...}`. A missing level is 0 | [`Tile`](geometry.md#tile) |

A default goes through the same check, so `SettingDef('tile', [3286, 3366])` reads as `Tile(3286, 3366, 0)`.

## Schemas

A schema is a `dict` of setting name to `SettingDef`. Give it as `define_bot(settings_schema=...)`, or, for a script without `BOT`, as a module-level `SETTINGS_SCHEMA`.

```python
SETTINGS = {
    'rocks': SettingDef('string[]', ['Copper', 'Tin'], options=['Copper', 'Tin', 'Iron'], label='Rocks to mine'),
    'centre': SettingDef('tile', [3286, 3366], label='The mine'),
    'radius': SettingDef('number', 10, min=1, max=30),
    'drop': SettingDef('boolean', True),
    'style': SettingDef('string', 'Strength', options=['Attack', 'Strength', 'Defence']),
}

BOT = define_bot(name='Power miner', create=PowerMiner, settings_schema=SETTINGS)
```

When the script loads, before any login:

1. A declared setting the account file lacks takes its default.
2. A value of the wrong type, a number out of bounds, or a string not among `options` stops the run with a `ValueError` naming the setting, such as `settings["Power miner"].radius must be at most 30`. The value itself isn't quoted, since settings can hold secrets.
3. A setting the schema doesn't declare draws a warning, since it's probably misspelled. For a `BOT`, so does a value beside the bots' objects in `script.settings` rather than inside its own.
4. For a `BOT` only, declared settings with a default that its object in the account file lacks are written into the file with their defaults, keeping the file's comments and layout. Values already there are never changed. A new script's first run so shows every setting, ready to edit.

A schema entry that isn't a `SettingDef`, or a schema that isn't a `dict`, raises `TypeError`.

### Reusable schema parts

`PERIODIC_BANK_SETTINGS` is a schema fragment for [periodic banking](bank.md#periodic-banking); merge it into your own:

```python
SETTINGS = {'radius': SettingDef('number', 8)}
for key, definition in PERIODIC_BANK_SETTINGS.items():
    SETTINGS[key] = definition
```

## Saved settings: `settings_store`

rs2b0t's `SettingsStore`. A script saves a value for the next run, and it's written into the account file, under `script.settings["<namespace>"]`, at the end of the script's step. The file's comments and layout are kept; an existing value is replaced in place. A namespace is a bot's name, `Global`, or one a bot keeps for itself, such as `Loadouts`.

```python
settings_store.save('Fighter', 'style', 'range')      # script.settings["Fighter"].style
style = settings_store.saved('Fighter', 'style')      # 'range', or None when nothing is saved
```

| Member | Does |
|---|---|
| `save(name, key, value)` | Saves a `bool`, number, string, list, `Tile` (as `[x, z, level]`) or `dict` of them. `ValueError` without a name and key |
| `saved(name, key)` | What was saved there, as the account file holds it (a tile as a list), or `None` |
| `resolve(name, schema)` | A `dict` of each schema setting: the namespace's value when it's valid, else for a [Global](#global-settings) key the Global value, else the default, as rs2b0t falls back |
| `display_string(name, key, definition)` | The value as rs2b0t's panel shows it: `'true'`, `'1,2,0'`, `'a, b'` |
| `on_change(listener)` | Calls `listener(name, key, value)` after each save, until the returned function is called |
| `global_bag()` | The [Global settings](#global-settings), resolved, as a `SettingsBag` |

The bot's own `self.settings` were read when it started; saving doesn't change them. A script reloaded on save sees what it saved.

## Global settings

rs2b0t's account-wide settings, in the account file's `script.settings["Global"]`. They're checked like a bot's, before login, and read through `settings_store.global_bag()`.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `lamp_skill` | string | `'strength'` | The skill a genie lamp trains, unless the bot's `lamp_skill()` chooses |
| `bank_common_junk` | boolean | `true` | Bank gems, fruit, beer, kebabs and caskets |
| `clue_duel_partner` | string | `''` | An account running the duel arena as a clue helper; empty finds a player in the lobby |
| `use_zanaris_bank` | boolean | `false` | Let the walker and `banking.open` use the Zanaris bank (needs Lost City) |
| `use_mage_bank` | boolean | `false` | Let them use the Mage Arena bank, which crosses deep Wilderness |
| `nav_teleports` | boolean | `false` | Let world walks plan teleports the backpack can pay for |
| `nav_path_stall_ticks` | number, 1 to 60 | 5 | Ticks without moving before a walk plans again |
| `nav_path_deviation` | number, 1 to 40 | 10 | How far off its route a walk may get before it plans again |

```jsonc
"settings": {
    "Global": { "use_mage_bank": true, "lamp_skill": "mining" },
    "Miner": { "rocks": ["Iron"] }
}
```

## Account file keys the client reads

These sit beside `script` in the account file and change what the client does around the script.

| Key | Default | Meaning |
|---|---|---|
| `script.file` | | The script, relative to `scripting.scriptsDirectory` (`scripts/`) |
| `script.settings` | `{}` | The settings object |
| `script.progressReportMinutes` | 0 (off) | Minutes between [progress reports](console-and-messages.md#progress-reports), 1 to 1440 |
| `randomEvents` | `true` | Whether the client [answers random events](upkeep.md#random-events) for the script |
| `stallMinutes` | 10 | Minutes without progress before the [stall guard](upkeep.md#the-stall-guard) steps in; 0 turns it off |
| `runAuto` | `true` | Whether the [run manager](upkeep.md#the-run-manager) turns run back on |
| `runEnergyMin` | 20 | The energy at which it does |

And in `client.jsonc`, under `scripting`:

| Key | Default | Meaning |
|---|---|---|
| `callTimeoutMs` | 1000 | How long one call into a script may run, in milliseconds; 0 disables the watchdog |
| `killGraceSeconds` | 30 | How long after `on_kill_signal` the account logs out anyway |
| `progressDirectory` | `progress` | Where progress reports are written |

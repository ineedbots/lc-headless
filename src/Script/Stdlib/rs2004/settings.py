"""Script settings: a schema of typed settings, checked against the account file before login, and the bag a
script reads them from. Modelled on rs2b0t's runtime/Settings.ts (MIT, see thirdparty/rs2b0t), but a
value that doesn't fit its schema is an error rather than quietly replaced by the default.

settings_store is rs2b0t's SettingsStore: values a script saves, by namespace and key, written into the account
file's script.settings["<namespace>"]. The Global namespace holds rs2b0t's account-wide settings."""

import _core
from rs2004.geometry import Tile

__all__ = ['SettingDef', 'SettingsBag', 'settings_store', 'GLOBAL_SETTINGS']

TYPES = ('boolean', 'number', 'string', 'string[]', 'tile')


class SettingDef:
    """One setting: its type ('boolean', 'number', 'string', 'string[]' or 'tile') and its default, with an
    optional range for numbers and a list of allowed values for strings. show_if ({'key': ..., 'any_of':
    [...]}) names the setting it depends on, as rs2b0t's panel shows it; step, color, options_from and
    csv_toggle only shape rs2b0t's panel, and are kept so its schemas port unchanged."""

    # Every parameter has a default so each can be given by keyword, which pocketpy allows only then.
    def __init__(self, type=None, default=None, label=None, min=None, max=None, help=None, options=None, option_labels=None, group=None,
                 show_if=None, step=None, color=None, options_from=None, csv_toggle=None):
        if type not in TYPES:
            raise ValueError(f'a setting type must be one of {", ".join(TYPES)}')
        self.type = type
        self.default = default
        self.label = label
        self.min = min
        self.max = max
        self.help = help
        self.options = options
        self.option_labels = option_labels
        self.group = group
        self.show_if = show_if
        self.step = step
        self.color = color
        self.options_from = options_from
        self.csv_toggle = csv_toggle

    def __repr__(self):
        return f'SettingDef({repr(self.type)}, {repr(self.default)})'


class SettingsBag:
    """The settings a script runs with. Read them as attributes (settings.rock), with get(), or with rs2b0t's
    typed getters, which return the fallback when the value isn't of their type."""

    _values = None

    def __init__(self, values):
        self._values = values

    def __getattr__(self, name):
        values = self._values
        if values is not None and name in values:
            return values[name]
        raise AttributeError(f"the script's settings have no {repr(name)}")

    def get(self, key, default=None):
        return self._values.get(key, default)

    def __contains__(self, key):
        return key in self._values

    def bool(self, key, fallback=False):
        value = self._values.get(key)
        return value if isinstance(value, bool) else fallback

    def num(self, key, fallback=0):
        value = self._values.get(key)
        return value if _is_number(value) else fallback

    def str(self, key, fallback=''):
        value = self._values.get(key)
        return value if isinstance(value, str) else fallback

    def list(self, key, fallback=None):
        value = self._values.get(key)
        if isinstance(value, list):
            return value
        return [] if fallback is None else fallback

    def tile(self, key, fallback):
        value = self._values.get(key)
        return value if isinstance(value, Tile) else fallback

    def raw(self):
        return {key: value for key, value in self._values.items()}

    def __repr__(self):
        return f'SettingsBag({self._values})'


def _is_number(value):
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)


def _parse_tile(value):
    if isinstance(value, Tile):
        return value
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(',')]
        if len(parts) not in (2, 3):
            return None
        numbers = []
        for part in parts:
            try:
                numbers.append(int(part))
            except Exception:
                return None
        return Tile(numbers[0], numbers[1], numbers[2] if len(numbers) == 3 else 0)
    if isinstance(value, list) and len(value) in (2, 3):
        for part in value:
            if not isinstance(part, int) or isinstance(part, bool):
                return None
        return Tile(value[0], value[1], value[2] if len(value) == 3 else 0)
    if isinstance(value, dict) and 'x' in value and 'z' in value:
        return Tile(value['x'], value['z'], value.get('level', 0))
    return None


def _match_option(definition, text):
    for option in definition.options:
        if option.lower() == text.lower():
            return option
    return None


def _check(key, definition, value, parent):
    """The value as the script reads it, or raises ValueError naming the setting. Messages don't quote the
    value, as config errors don't, since settings can hold secrets."""
    where = f'{parent}.{key}'
    kind = definition.type
    if kind == 'boolean':
        if not isinstance(value, bool):
            raise ValueError(f'{where} must be true or false')
        return value

    if kind == 'number':
        if not _is_number(value):
            raise ValueError(f'{where} must be a number')
        if definition.min is not None and value < definition.min:
            raise ValueError(f'{where} must be at least {definition.min}')
        if definition.max is not None and value > definition.max:
            raise ValueError(f'{where} must be at most {definition.max}')
        return value

    if kind == 'string':
        if not isinstance(value, str):
            raise ValueError(f'{where} must be a string')
        # A blank string is unset, as a panel's empty choice is, which a bot reads as "use the fallback".
        if definition.options and value != '':
            option = _match_option(definition, value)
            if option is None:
                raise ValueError(f'{where} must be one of: {", ".join(definition.options)}')
            return option
        return value

    if kind == 'string[]':
        if isinstance(value, str):
            value = [part.strip() for part in value.split(',') if part.strip()]
        if not isinstance(value, list):
            raise ValueError(f'{where} must be a list of strings')
        result = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f'{where} must be a list of strings')
            if definition.options:
                option = _match_option(definition, item)
                if option is None:
                    raise ValueError(f'{where} may only hold: {", ".join(definition.options)}')
                item = option
            result.append(item)
        return result

    tile = _parse_tile(value)
    if tile is None:
        raise ValueError(f'{where} must be a tile: [x, z], [x, z, level] or "x,z,level"')
    return tile


def _check_show_if(key, definition, schema):
    show_if = definition.show_if
    if show_if is None:
        return
    if not isinstance(show_if, dict) or not isinstance(show_if.get('key'), str) or not isinstance(show_if.get('any_of'), list):
        raise TypeError(f"settings schema entry {repr(key)}'s show_if must be a dict of 'key', a setting, and 'any_of', a list of its values")
    if show_if['key'] not in schema:
        raise ValueError(f"settings schema entry {repr(key)}'s show_if names {repr(show_if['key'])}, which the schema lacks")


def apply_schema(bag, schema, where='settings'):
    """Checks the bag's values against the schema, in place: each declared setting is checked and takes
    its default when missing. Returns warnings for settings the schema doesn't declare. Messages name each
    setting from where, the bag's place in the account file."""
    if schema is None:
        return []
    if not isinstance(schema, dict):
        raise TypeError(f'a settings schema must be a dict, not {type(schema).__name__}')

    values = bag._values
    for key, definition in schema.items():
        if not isinstance(definition, SettingDef):
            raise TypeError(f'settings schema entry {repr(key)} must be a SettingDef')
        _check_show_if(key, definition, schema)
        if key in values:
            values[key] = _check(key, definition, values[key], where)
        else:
            values[key] = _check(key, definition, definition.default, where) if definition.default is not None else None

    # A script without BOT reads the whole script.settings, where the Global namespace isn't its own.
    return [f"has {where}.{key}, which its settings schema doesn't declare" for key in values if key not in schema and not (where == 'settings' and key == GLOBAL)]


def bot_settings_path(name):
    """Where a define_bot script's settings are in the account file's script.settings: under its name."""
    return f'settings["{name}"]'


def select_bot_settings(bag, name):
    """Narrows the bag, in place, to the object under the bot's name, so one account file can keep the
    settings of several define_bot scripts. Returns a warning for settings outside any such object, which
    no define_bot script reads."""
    values = bag._values
    own = values.get(name)
    if own is None:
        own = {}
    elif not isinstance(own, dict):
        raise ValueError(f'{bot_settings_path(name)} must be an object')

    bag._values = own
    stray = [f'settings.{key}' for key, value in values.items() if not isinstance(value, dict)]
    if not stray:
        return []
    return [f'ignores {", ".join(stray)}: a define_bot script reads only {bot_settings_path(name)}']


def schema_defaults(schema):
    """The schema's defaults as an account file holds them, with tiles as [x, z, level]. Settings without a
    default are left out."""
    defaults = {}
    for key, definition in (schema or {}).items():
        default = definition.default
        if default is None:
            continue
        if isinstance(default, Tile):
            default = [default.x, default.z, default.level]
        elif isinstance(default, tuple):
            default = list(default)
        defaults[key] = default
    return defaults


GLOBAL = 'Global'

LAMP_SKILLS = [
    'attack', 'strength', 'ranged', 'magic', 'defence', 'hitpoints', 'prayer', 'agility', 'herblore', 'thieving',
    'crafting', 'runecraft', 'mining', 'smithing', 'fishing', 'cooking', 'firemaking', 'woodcutting', 'fletching',
]

# rs2b0t's account-wide settings that matter headlessly (its GLOBAL_SETTINGS_CORE and NAV_SETTINGS), kept in
# script.settings["Global"]. runAuto and runEnergyMin are the account file's own keys instead, as before.
GLOBAL_SETTINGS = {
    'lamp_skill': SettingDef('string', 'strength', 'Genie lamp skill', options=LAMP_SKILLS, help='the skill a genie lamp trains, unless the bot chooses'),
    'bank_common_junk': SettingDef('boolean', True, 'Bank gems, fruit, beer, kebabs and caskets'),
    'clue_duel_partner': SettingDef('string', '', 'Clue duel partner', help='an account running Duel Arena as a clue helper; empty finds a player in the lobby'),
    'use_zanaris_bank': SettingDef('boolean', False, 'Allow the Zanaris bank', help='needs Lost City, and starting inside the city'),
    'use_mage_bank': SettingDef('boolean', False, 'Allow the Mage Arena bank', help='reaching it crosses deep Wilderness and slashes two webs'),
    'nav_teleports': SettingDef('boolean', False, 'Nav teleports', help='let world walks plan spell and jewellery teleports the backpack can pay for'),
    'nav_path_stall_ticks': SettingDef('number', 5, 'Path stall repath (ticks)', 1, 60),
    'nav_path_deviation': SettingDef('number', 10, 'Path deviation repath (tiles)', 1, 40),
}


def _json_value(value):
    """The value as the account file holds it: tiles as [x, z, level]."""
    if isinstance(value, Tile):
        return [value.x, value.z, value.level]
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    if isinstance(value, dict):
        return {key: _json_value(v) for key, v in value.items()}
    return value


def _display(definition, value):
    """A value as rs2b0t's panel shows it, as text."""
    if isinstance(value, Tile):
        return f'{value.x},{value.z},{value.level}'
    if definition.type == 'tile' and isinstance(value, list):
        return ','.join([str(v) for v in value])
    if isinstance(value, list):
        return ', '.join([str(v) for v in value])
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return '' if value is None else str(value)


class SettingsStore:
    """rs2b0t's SettingsStore: values saved by namespace and key, which outlast the run. A namespace is the
    object under its name in the account file's script.settings: a bot's name, Global, or one a bot keeps for
    itself, such as Loadouts. save() writes the value into the account file at the end of the step, keeping
    the file's comments; saved() reads it back."""

    def __init__(self):
        self._values = {}
        self._listeners = []

    def load(self, values):
        """The account file's script.settings, as the runtime loads the bot."""
        import json
        self._values = json.loads(json.dumps(values)) if isinstance(values, dict) else {}

    def saved(self, name, key):
        """The value saved under the namespace and key, or None."""
        namespace = self._values.get(name)
        if not isinstance(namespace, dict):
            return None
        return namespace.get(key)

    def save(self, name, key, value):
        """Saves a value: a bool, number, string, list or tile, or a dict of them."""
        if not isinstance(name, str) or not name or not isinstance(key, str) or not key:
            raise ValueError('settings_store.save needs a namespace and a key')
        import json
        value = _json_value(value)
        text = json.dumps(value)
        namespace = self._values.get(name)
        if not isinstance(namespace, dict):
            namespace = {}
            self._values[name] = namespace
        namespace[key] = json.loads(text)
        _core.save_setting(name, key, text)
        for listener in list(self._listeners):
            try:
                listener(name, key, value)
            except Exception:
                pass

    def on_change(self, listener):
        """Calls listener(name, key, value) after each save, until the returned function is called."""
        self._listeners.append(listener)

        def unsubscribe():
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _winning(self, name, key, definition):
        """(value, its SettingDef) as rs2b0t resolves them: the namespace's saved value, else Global's for a
        Global key, else None."""
        value = self.saved(name, key)
        if value is not None:
            return value, definition
        if name != GLOBAL and key in GLOBAL_SETTINGS:
            return self.saved(GLOBAL, key), GLOBAL_SETTINGS[key]
        return None, definition

    def resolve(self, name, schema):
        """The namespace's settings by the schema: each one saved and valid, or else its default, as rs2b0t
        falls back."""
        resolved = {}
        for key, definition in schema.items():
            value, used = self._winning(name, key, definition)
            if value is not None:
                try:
                    resolved[key] = _check(key, used, value, name)
                    continue
                except ValueError:
                    pass
            resolved[key] = None if used.default is None else _check(key, used, used.default, name)
        return resolved

    def display_string(self, name, key, definition):
        value, used = self._winning(name, key, definition)
        return _display(used, used.default if value is None else value)

    def global_bag(self):
        """The Global settings, resolved."""
        return SettingsBag(self.resolve(GLOBAL, GLOBAL_SETTINGS))


settings_store = SettingsStore()

"""Script settings: a schema of typed settings, checked against the account file before login, and the bag a
script reads them from. Modelled on rs2b0t's runtime/Settings.ts (MIT, see thirdparty/rs2b0t), but a
value that doesn't fit its schema is an error rather than quietly replaced by the default."""

from rs2004.geometry import Tile

__all__ = ['SettingDef', 'SettingsBag']

TYPES = ('boolean', 'number', 'string', 'string[]', 'tile')


class SettingDef:
    """One setting: its type ('boolean', 'number', 'string', 'string[]' or 'tile') and its default, with an
    optional range for numbers and a list of allowed values for strings."""

    # Every parameter has a default so each can be given by keyword, which pocketpy allows only then.
    def __init__(self, type=None, default=None, label=None, min=None, max=None, help=None, options=None, option_labels=None, group=None):
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


def _check(key, definition, value):
    """The value as the script reads it, or raises ValueError naming the setting. Messages don't quote the
    value, as config errors don't, since settings can hold secrets."""
    where = f'settings.{key}'
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
        if definition.options:
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


def apply_schema(bag, schema):
    """Checks the bag's values against the schema, in place: each declared setting is checked and takes
    its default when missing. Returns warnings for settings the schema doesn't declare."""
    if schema is None:
        return []
    if not isinstance(schema, dict):
        raise TypeError(f'a settings schema must be a dict, not {type(schema).__name__}')

    values = bag._values
    for key, definition in schema.items():
        if not isinstance(definition, SettingDef):
            raise TypeError(f'settings schema entry {repr(key)} must be a SettingDef')
        if key in values:
            values[key] = _check(key, definition, values[key])
        else:
            values[key] = _check(key, definition, definition.default) if definition.default is not None else None

    return [f"has settings.{key}, which its settings schema doesn't declare" for key in values if key not in schema]

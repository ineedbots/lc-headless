"""AccountLeveler's mutable TypeScript records, including dictionaries indexed by item or skill."""

class Record:
    def __init__(self, fields):
        self._data = {}
        for key, value in fields.items():
            if isinstance(value, list) and any([isinstance(entry, dict) for entry in value]):
                value = [Record(entry) if isinstance(entry, dict) else entry for entry in value]
            self[key] = Record(value) if isinstance(value, dict) else value

    def __getattr__(self, key):
        if key.startswith('__'):
            raise AttributeError(key)
        return None

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        self._data[key] = value
        setattr(self, key, value)

    def get(self, key, default=None):
        value = getattr(self, key, None)
        return default if value is None else value

    def keys(self):
        return list(self._data.keys())

    @property
    def _fields(self):
        fields = {key: getattr(self, key) for key in self._data}
        for key in dir(self):
            if not key.startswith('_') and key not in fields:
                value = getattr(self, key)
                if not callable(value):
                    fields[key] = value
        return fields

    def items(self):
        return [(key, getattr(self, key)) for key in self._data]

    def values(self):
        return [getattr(self, key) for key in self._data]

    def pop(self, key, default=None):
        if key not in self._data:
            return default
        value = getattr(self, key)
        self._data.pop(key)
        setattr(self, key, None)
        return value

    def __contains__(self, key):
        return key in self._data

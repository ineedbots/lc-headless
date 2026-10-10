"""A table entry with its fields as attributes, where a field the entry doesn't set reads as None."""


class Record:
    def __init__(self, fields):
        self._fields = fields
        for key, value in fields.items():
            if isinstance(value, dict):
                value = Record(value)
            setattr(self, key, value)

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return None

    def get(self, key, default=None):
        value = self._fields.get(key)
        return default if value is None else getattr(self, key)

    def keys(self):
        return list(self._fields.keys())

    def __repr__(self):
        name = self._fields.get('name')
        return f'Record({repr(name)})' if name is not None else f'Record({self._fields})'


def records(table):
    return [Record(entry) for entry in table]

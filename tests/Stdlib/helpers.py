"""Shared by the standard library's Python tests."""


def raises(error, call):
    """Calls call(), which must raise error, and returns the message."""
    try:
        call()
    except error as e:
        return str(e)
    raise AssertionError(f'expected {error.__name__}')


class FakeModule:
    """Stands in for a script's module: give it loop, on_* functions, BOT or SETTINGS_SCHEMA."""

    def __init__(self, **attributes):
        for name, value in attributes.items():
            setattr(self, name, value)

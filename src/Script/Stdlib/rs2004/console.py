"""Commands typed into the client's console. A script adds its own with console.command(name, handler,
help), or self.command(...) in a bot, which lasts until the bot stops. Typing the name calls the handler with
a Command on the script's next pass, once the player is placed; "@<account> <name> ..." sends it to one
account only."""

__all__ = ['console', 'Command']

# The client's own commands, which a script can't add. AccountRunner handles them.
RESERVED = ('help', 'status', 'quit', 'exit', 'loglevel')

# Each command's help by name, '' for none. The host reads it to route lines and list the commands, so it's
# only ever changed in place.
commands = {}
_handlers = {}


class Command:
    """A console line for this script: its name, text (the rest of the line, trimmed) and args (text split
    at whitespace)."""

    def __init__(self, name, text, args):
        self.name = name
        self.text = text
        self.args = args

    def __repr__(self):
        return f'Command({repr(self.name)}, {repr(self.text)})'


class Console:
    def command(self, name, handler, help=None):
        """Calls handler(command) each time the command is typed, until the returned function is called. The
        name is one word, matched in any case. The handler can't wait: set a flag and do the work in loop()."""
        if not isinstance(name, str) or not name:
            raise ValueError('a console command needs a name')
        key = name.lower()
        if ' ' in key or '\t' in key or key.startswith('@'):
            raise ValueError(f'{repr(name)} is not a console command name; use one word, not starting with @')
        if key in RESERVED:
            raise ValueError(f"{repr(name)} is the client's own console command")
        if key in _handlers:
            raise ValueError(f'the console command {repr(name)} was already added')
        if not callable(handler):
            raise TypeError('a console command handler must be callable')
        if help is not None and not isinstance(help, str):
            raise TypeError('a console command help must be a str')

        commands[key] = help or ''
        _handlers[key] = handler

        def remove():
            if _handlers.get(key) is handler:
                del _handlers[key]
                del commands[key]

        return remove

    def remove(self, name):
        """Removes a command, if it was added."""
        key = name.lower()
        if key in _handlers:
            del _handlers[key]
            del commands[key]

    def names(self):
        """The commands added, sorted."""
        return sorted(_handlers.keys())


console = Console()


def handler(name):
    """The command's handler, or None once it has been removed."""
    return _handlers.get(name)

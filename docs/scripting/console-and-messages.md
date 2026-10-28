# Console commands, messages between scripts and progress reports

## Console commands

The client reads each line typed into its console while it runs. In a terminal, it keeps a `> ` prompt on the bottom line and prints log lines above it, so they never run into what you're typing. The left and right arrows, Home, End, Backspace and Delete edit the line, Ctrl+U and Ctrl+K clear it before and after the cursor, and Up and Down go back through the last 100 lines entered. The terminal needs to understand VT100 codes, as the Windows 10 and later console, Windows Terminal and Linux terminals do. When the input is piped in instead, lines are read as they come, with no prompt.

In a terminal, log lines are colored by level: verbose cyan, info in the terminal's own color, warnings yellow and errors red. Output redirected to a file stays plain, and setting `NO_COLOR` turns the colors off. `--raw-console` turns off the colors, the prompt and console input altogether, and `client.logFile` in `client.jsonc` appends every log line to a file too, as plain text.

A script can add its own commands.

### `console.command(name, handler, help=None)`

Calls `handler(command)` each time the command is typed, until removed. Returns a function that removes it.

- `name` is one word, matched without regard to case, not starting with `@`. The client's own commands (`help`, `status`, `quit`, `exit`, `loglevel`, `say`) and the standard library's (`pause`, `resume`) can't be added. A bad name, or a name already added, raises `ValueError`.
- `handler` must be callable, or `TypeError`. It receives a [`Command`](#command).
- `help` is a line shown by the `help` command; a non-string raises `TypeError`.

```python
def set_laps(command):
    global lap_limit
    if command.args:
        lap_limit = int(command.args[0])
    log('logging out after', lap_limit, 'laps')

console.command('laps', set_laps, 'Logs out after the laps given')
```

A command added at module level lasts as long as the script. In a bot, `self.command(name, handler, help=None)` adds one that's removed when the bot stops.

### Other members

| Member | Does |
|---|---|
| `console.remove(name)` | Removes a command, if it was added |
| `console.names()` | The commands this script added, sorted |

### `Command`

| Field | Meaning |
|---|---|
| `name` | The command's name, lower case |
| `text` | The rest of the line, trimmed |
| `args` | `text` split at whitespace |

### How lines are routed

- A line without `@` goes to every running script that added the command. `@<account> <line>` goes only to that account, named by its account file or its username, in any case. A name no running script has added draws a warning.
- The handler runs on the script's next pass, once the player is placed, so a line typed while the account logs in or reconnects waits until it's back.
- Like a hook, a handler can't wait: one that returns a generator stops the script with `TypeError`. An exception in it stops the script too, so check `args` before using them.

### Built-in commands

Use `@<account>` to target applicable built-in commands too: `@mule status`, `@mule help`, `@mule say hi` or `@mule quit`. An account quit before its login turn never logs in. `loglevel` always applies to the whole process.

| Command | Does |
|---|---|
| `help` | Lists the commands, including every running script's |
| `status` | One line per account: logging in, in game and where, reconnecting or finished, and its script's state |
| `quit`, `exit` | As Ctrl+C: each script gets `on_kill_signal`; typing it again logs every account out at once |
| `loglevel [verbose\|info\|warning\|error]` | Shows or sets the log level of every account |
| `say <text>` | Says the text in public chat from every account in game, cut to 80 characters |
| `pause` | Every script has it: stops stepping the bot, dropping its step in progress, and calls `on_pause`. Upkeep goes on, so a paused account still answers random events and keeps its run on, and the stall guard waits. `@<account> pause` pauses one |
| `resume` | Calls `on_resume`, and `loop()` starts afresh |

## Messages between scripts

Accounts in the same process can message each other's scripts.

### `send_bot_message(username, message)`

Sends `message` to the script of the account with that username (as in its account file, in any case). That script's `on_bot_message(sender, message)` hook, and `bot_message` subscribers, receive it with the sender's username.

```python
# The worker
send_bot_message(settings.mule, {'want': 'trade', 'items': [[995, 1000]]})

# The mule
def on_bot_message(sender, message):
    if message['want'] == 'trade':
        log(sender, 'wants to trade')
```

- `message` is copied as JSON: a `dict` with string keys, a `list`, a `str`, a number, a `bool` or `None`, nested to any depth, up to 64 KiB. Tuples arrive as lists. Anything else raises `TypeError`.
- **Returns** `True` once queued. `False` means the receiver can't take it now: its script has stopped or has no `on_bot_message`, or 100 of its messages are already waiting.
- A username no account in the process has raises `ValueError`.
- Messages arrive in the order sent, on the receiver's next pass, and wait while it logs in or reconnects. A script can message itself; a message sent while handling one arrives on the next pass.

## Progress reports

Set `script.progressReportMinutes` in the account file (1 to 1440) and define `on_progress_report()`, returning a `dict`:

```python
def on_progress_report():
    return {'Kills': kills, 'Bones': inventory.count('Bones')}
```

That many minutes after `on_start`, and every that many minutes after, the client calls it, appends the result as a table to `progress/<account>.txt` (the folder is `scripting.progressDirectory`), and logs it on one line. Each run starts the file afresh.

```
Progress at 2026-10-08T14:20:00Z, 1h 20m after the script started
+-------+-------+
| Name  | Value |
+-------+-------+
| Kills | 10    |
| Bones | 42    |
+-------+-------+
```

- Names and values are shown with `str()`, in the dict's order.
- Returning anything but a `dict` stops the script with `TypeError`.
- A report that falls due while the account is reconnecting waits until it's back.

For a complete script with commands and messages, see [`walker.py`](../../scripts/examples/walker.py).

# Scripting API

How to write Python scripts that drive the headless client. A script is a `.py` file in the scripts folder; each account file names the script it runs. The API is rs2b0t's bot API in Python's style: facades for the game's nouns, queries that find things, and bots that wait with `yield from` where rs2b0t awaits. The design behind it is in [ScriptingDesign.md](ScriptingDesign.md), and [BotApiDesign.md](BotApiDesign.md) plans the rest of rs2b0t's abilities, phase by phase.

## Quick start

1. Copy `accounts/example.jsonc.sample` to `accounts/<name>.jsonc` and fill in the username and password. The file name becomes the account's name in log lines.
2. Point `script.file` at a script, relative to `scripts/`, such as `examples/chicken_killer.py`.
3. Run `rs2004-headless client.jsonc` to run every enabled file in `accounts/`, logging them in `scripting.loginIntervalSeconds` apart, or add `--account accounts/<name>.jsonc` to run just that one. One process runs up to 16 scripted accounts.

An account file can have its own `server` section, with the same keys as `client.jsonc`'s, to log that account into a different world.

Ctrl+C asks each script to finish (see `on_kill_signal`). A second Ctrl+C logs every account out at once, and one more closes any connection whose logout the server is still refusing. The exit code is 0 when every account logged out cleanly and no script failed.

A dropped connection is restored automatically, with up to 10 attempts over about four minutes, so a server restart doesn't end a run. Each account reconnects on its own and the others keep playing. A first login is retried the same way when the server can't take it yet, for example "already logged in" after a crash.

A script is a bot, as in rs2b0t's API: either a class set with `BOT = define_bot(...)`, or a module-level `loop()` with `on_*` hooks, which runs as a `LoopingBot`. It finds things with queries, acts on what it finds, and returns how long to wait before `loop()` runs again:

```python
def on_start():
    log('Starting at', game.tile())

def loop():
    if game.in_combat():
        return 600          # the next server tick

    chicken = npcs.query().name('Chicken').within(8).where(lambda npc: not npc.in_combat).nearest()
    if chicken is not None and chicken.interact('Attack'):
        # Wait until the fight starts, or 3 seconds.
        yield from execution.delay_until(lambda: game.in_combat(), 3000)

def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()
```

The same as a bot, with its settings declared, and tasks chosen in priority order:

```python
class Fighter(TaskBot):
    def on_start(self):
        self.add(
            Task(lambda: game.in_combat(), lambda: None, label='fight'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def attack(self):
        target = npcs.query().name(self.settings.npc).within(8).where(lambda npc: not npc.in_combat).nearest()
        if target is not None and target.interact('Attack'):
            yield from execution.delay_ticks(2)

BOT = define_bot(name='Fighter', create=Fighter, settings_schema={'npc': SettingDef('string', 'Chicken')})
```

`scripts/examples/` has complete scripts:
- `chicken_killer.py` is a `TaskBot` that fights, loots and logs out.
- `power_miner.py` is a `LoopingBot` that mines and drops the ore.
- `walker.py` is a module-level script that walks a loop of tiles, optionally for a set number of laps, telling a partner account about each one.

All three make progress reports.

For working on a script, `--watch` reloads it whenever you save it, and `--debugger` lets VS Code debug it (see [Working on a script](#working-on-a-script)).

## How scripts run

- The module body runs once, before login. Use it for constants, classes and `BOT`. Game functions return empty values at that point, and actions fail, since there's no session yet. Once it has run, the client makes the bot and checks its settings (see [Settings](#settings)), so a broken script or a bad setting stops the run before any login.
- `on_start()` runs once the player is first placed in the world. After that, on every pass of the main loop the client:
  1. calls the hooks and subscribers for everything that arrived since the last pass (events first, then chat messages, then messages from other scripts);
  2. calls `on_tick` if a server tick passed;
  3. calls `on_progress_report` if a report is due;
  4. steps the bot's `loop()` if what it's waiting for has happened.
- What `loop()` returns says how long to wait, as rs2b0t reads it: `600` means the next server tick, `0` the next pass, and any other number that many milliseconds. `None`, or no return at all, uses the bot's `loop_delay`, which is 600; a bot can set `loop_cadence` to `{'kind': 'frame'}`, `{'kind': 'server_tick', 'ticks': n}` or `{'kind': 'time', 'ms': n}` instead.
- Everything runs on one thread, shared by every account in the process. Each call into the script may run for at most `scripting.callTimeoutMs` (1000 ms by default) before it's stopped with `TimeoutError`. `time.sleep()` raises an error: wait with `execution` instead.
- An uncaught exception, or a `loop()` that returns or yields something it can't, stops the script. The client calls `on_stop`, logs the traceback, and logs the account out, unless it's running with `--watch`.
- Objects such as `Npc` are snapshots taken when the query ran. `valid()` asks whether one is still there; keep an NPC's `index` to find it again with `npcs.get(index)`.
- Actions queue packets and return at once; their effects show up in the state over the next ticks. Actions on a target that's no longer in view, or that has no such option, return `False`. A wrong argument type raises `TypeError`, and a value out of range (an option outside 1 to 5, say) raises `ValueError`.
- Names, options and scenery come from the server's cache, which the client loads at startup from `client.cacheDirectory`. They're exactly as the cache has them, case included.
- `log(*args)` writes at Info level and `debug(*args)` at Verbose level; `print()` also goes to the log. Each line carries the account's name.

### Waiting

Where rs2b0t awaits, a script writes `yield from`. `loop()`, a task's `execute()` and `on_start()` may be generators; each wait in `execution` is one too, and gives back its result:

| Wait | Gives |
|---|---|
| `execution.delay(ms)` | Nothing, after `ms` milliseconds |
| `execution.delay_ticks(n)` | Nothing, after `n` server ticks |
| `execution.delay_until(cond, timeout_ms=6000)` | `True` as soon as `cond()` holds, checked now and after every update from the server; `False` at the timeout |
| `execution.delay_until_ticks(cond, max_ticks)` | The same, checked once a tick |
| `execution.note_progress()` | Not a wait: reports progress the stall guard can't see, such as a finished trade |

```python
def loop():
    raw = inventory.first('Raw shrimps')
    stove = locs.query().name('Range').within(3).nearest()
    raw.use_on(stove)
    cooked = yield from execution.delay_until(lambda: inventory.count('Shrimps') > 0, 5000)
    if not cooked:
        log('The range did nothing')
```

- A generator can also `yield` a number of milliseconds itself; unlike a return, a yielded 600 is wall-clock time.
- A wait resumes on the first pass after what it waits for, not on a poll, so `delay_until` sees a change the pass after the packet that made it arrives.
- Hooks run as usual while `loop()` waits. Each resume is a separate call, so `scripting.callTimeoutMs` applies to each stretch between waits, not the whole generator. A reload with `--watch` starts it over.
- Hooks themselves can't wait: one that's a generator is an error. Set a flag and do the work in `loop()`.

### Bots

Mirroring rs2b0t's bot classes:

| Class | Does |
|---|---|
| `LoopingBot` | Override `loop()`. A script without `BOT` is one, made of its module's `loop()` and hooks |
| `TaskBot` | `self.add(*tasks)` in `on_start`, highest priority first. Each loop runs the `execute()` of the first task whose `validate()` holds. A task is a `Task(validate, execute, label=None)` of two callables, or a `Task` subclass that overrides both; either may be a generator. `active_task_name` is the running task's label |
| `TreeBot` | Override `root()`, returning a `BranchTask` (`validate()`, `success()`, `failure()`) or a `LeafTask` (`execute()`); each loop walks the tree to a leaf and runs it |

Every bot has `settings`, `loop_delay`, `loop_cadence`, `log(*args)`, `on(event, callback)` (a subscription that ends with the bot), `request_finish(reason)` (stops the script, leaving the account logged in, with `reason` passed to `on_stop`), and the hooks it defines as methods. `define_bot(name=..., create=..., description=None, version=None, category=None, tags=None, settings_schema=None)` describes it; `create` is the class, or a function that makes the bot.

### Settings

The account file's `script.settings` object becomes the global `settings`, and the bot's `self.settings`. Read its keys as attributes (`settings.loot_goal`), with `settings.get('key', default)`, or with rs2b0t's typed getters, `bool(key)`, `num(key)`, `str(key)`, `list(key)` and `tile(key, fallback)`, which return the fallback when the value isn't of their type. `'key' in settings` checks for one.

A script can declare its settings with a schema: `settings_schema=` in `define_bot`, or a module-level `SETTINGS_SCHEMA`. It maps each key to a `SettingDef(type, default, label=None, min=None, max=None, help=None, options=None, option_labels=None, group=None)`, where type is `'boolean'`, `'number'`, `'string'`, `'string[]'` or `'tile'`. Then, before login:

- a setting the account file leaves out takes its default;
- a value of the wrong type, a number outside `min` and `max`, or a string not in `options` stops the run, naming the setting. Options match without regard to case and become the schema's spelling;
- a `'string[]'` may be a list or a comma-separated string, and a `'tile'` may be `[x, z]`, `[x, z, level]`, `"x,z,level"` or `{"x": ..., "z": ..., "level": ...}`. A tile setting reads as a `Tile`;
- a setting the schema doesn't declare draws a warning, since it's probably misspelled.

### Imports

`import name` loads the client's standard library first: the `rs2004` package, whose public names are already in builtins, so scripts don't import it. Then `scripts/name.py`, then `scripts/lib/name.py`; packages (folders with `__init__.py`) work too. pocketpy's own modules (`math`, `random`, `json`, `time`, `collections`, ...) are available. Nothing else is searched, and pip packages can't be used.

### Python dialect

Scripts run on pocketpy 2.2, a subset of Python 3. The differences you're likely to hit:

- `try` has no `finally` or `else`.
- Generator expressions don't exist; use list comprehensions.
- A class has at most one base class.
- Ints are 64-bit, and `bool` isn't a kind of `int`.
- A parameter can be passed by keyword only when it has a default value, and a default value must be a literal (`timeout=6000`, not `timeout=TIMEOUT`).
- An attribute set on an instance doesn't replace a method of its class; give the instance a differently named attribute and call it from the method.
- In unpacking, a starred name must come last (`first, *rest = items`), and only lists and tuples unpack.
- Tuples can't be added together, `dict(another_dict)` doesn't copy, and `dict.setdefault` and `str.isdigit` don't exist.
- There's no `re` module.

## The world

### Queries

`npcs`, `players`, `locs` (scenery) and `ground_items` each have `query()`, which starts a chain of filters, as rs2b0t's does:

```python
guard = npcs.query().name('Guard').action('Pickpocket').within(3).nearest()
oak = locs.query().name('Oak').within(6).nearest()
coins = ground_items.query().name('Coins').within(12).nearest()
```

| Filter | Keeps |
|---|---|
| `name(*names)` | Any of the names, matched whole without regard to case. A list works too; a thing whose type has no name never matches |
| `id(*ids)` | Any of the ids |
| `action(action)` | Things that offer the option, matched without regard to case |
| `within(dist)` | Things within `dist` tiles of you |
| `within_of(origin, dist)` | Things within `dist` tiles of another tile, such as a camp's centre |
| `inside(area)` | Things inside an `Area`, or a dict of `min_x`, `max_x`, `min_z` and `max_z` |
| `layer(layer)` | Scenery in one layer, a `LAYER_*` constant |
| `reachable()` | Things a walk can reach, by the same rule the matching interaction walks by |
| `where(predicate)` | Things for which `predicate(thing)` is true |

A chain ends with `results()`, `nearest()`, `nearest_prefer_local(radius)` (the nearest among those within `radius` of you, when there are any), `first()`, `exists()` or `count()`. Results are in the server's order, scenery nearest first. "Nearest" counts tiles, not steps, and a tie goes to the first. Names, ids and `within` narrow the search in the client; the other filters test each result in Python.

Also:
- `npcs.all()`, `npcs.get(index)` (the NPC with that index now, or `None`), and `npcs.nearest(count=1)`, a list;
- `players.all()` and `players.local()`, you as a `Player`;
- `locs.at(tile, layer=None)`: the scenery on a tile now, the server's change or else the cache's. Without a layer, it's the first in layer order, preferring scenery that's there to a removed one.

### Things

Each is a snapshot of when it was found: its fields don't change, and `valid()` asks whether it's still there. All have `tile()`, `distance()` (Chebyshev tiles from you, with another level counting as very far) and `actions()` (the options its menu shows).

| Class | Fields | Methods |
|---|---|---|
| `Npc` | `index`, `id`, `name`, `level` (combat level, 0 for none), `size`, `in_combat`, `health` and `max_health` (0 until a hit shows them), `animation` (-1 for none), `moving`, `target` (`('npc' or 'player', index)` or `None`) | `interact(action)`, `valid()`, `targets_me()`, `targets_another_player()`, `network_tile()` |
| `Player` | `index`, `name` (`None` until its appearance arrives), `combat_level`, then as `Npc` from `in_combat` on | `interact(action)`, `valid()`, `targets_me()` |
| `Loc` | `id` (-1 when the server removed it), `name`, `shape`, `angle`, `layer`, `changed` (`False` as the cache has it, `True` for the server's changes) | `interact(action)`, `interact_via(points, action)`, `valid()` |
| `GroundItem` | `id`, `name`, `count` | `interact(action)`, `valid()` |

- `interact(action)` takes the option's text, matched without regard to case, or its number from 1 to 5. It walks there first, routing around walls and scenery as the webclient does, then uses the option. It returns `False`, sending nothing, when the thing has no such option or has gone. Ground items offer "Take" where their type has nothing in that slot, as the menu does.
- `loc.interact_via(points, action)` walks your `(x, z)` waypoints, each in a straight line, instead of a route.
- `in_combat` means a hit within the last 8 ticks: 2004 has no combat-state packet.
- Names and options come from the server's cache, loaded at startup from `client.cacheDirectory`, exactly as it has them.

## Items

`inventory` is the backpack:
- `items()`: an `InvItem` per occupied slot;
- `first(name)`, `contains(name)`, `count(name)` (the total across stacks and slots), and `count_by_id(id)`;
- `used()`, `free()` and `is_full()`.

Names match whole, without regard to case.

`equipment` is what you wear:
- `items()` and `contains(name)`;
- `equip(name)` (Wield, Wear or Equip, whichever the item has) and `unequip(name)`. Both wait until the item has moved, so use them with `yield from`; they give `True` when it did.

An `InvItem` has `id`, `name`, `count`, `slot`, `noted` and `com` (the inventory it's in), and:
- `actions()`. Inventory items offer "Drop" where their type has nothing there;
- `interact(action)`, such as `item.interact('Eat')`;
- `use_on(target)`, with another `InvItem`, an `Npc`, a `Player`, a `Loc` or a `GroundItem`.

## You and the game

| Facade | Functions |
|---|---|
| `game` | `ingame()`, `tile()` (`None` before you're placed), `energy()` (run energy, 0 to 100), `run_enabled()`, `set_run(on)`, `weight()`, `in_combat()`, `animating()`, `moving()`, `tick()` (server ticks since login), `my_name()`, `combat_level()` |
| `skills` | `level(name)` (base), `effective(name)` (boosted or drained), `xp(name)`, `index(name)` (-1 for a name that isn't a skill), `hp_fraction()`. Names are lower-case: `'attack'`, `'woodcutting'`, `'runecraft'`; an unknown one raises `ValueError` |
| `direct_navigator` | Walking within the loaded area: `walk(dest, run=False)` (one routed walk; `False` when the tile is in view but can't be reached, and a tile beyond the loaded area is walked to in a straight line), `walk_to(dest, radius=2, timeout_ms=45000, run=False)` (a wait: walks, clicking again when it stalls, until within `radius`), `walk_path(points, run=False)` (up to 25 waypoints, each leg straight), `reachable(dest)`, `path(dest)` (the waypoints a walk would send), `destination()` |
| `chat` | `say(text)`, `send_pm(name, text)`, `command(text)` (a `::command` for staff accounts, such as `command('tele 0,50,51,30,34')`) |
| `friends`, `ignores` | `list()` (friends as `[(name, world)]`, world 0 when offline), `add(name)`, `remove(name)` |
| `reader` | Raw reads, for what no facade covers yet: `varp(id)`, `pid()`, `main_modal()`, `side_modal()`, `chat_modal()` (-1 for none), `interface_open(id)`, `component_text(com)`, `count_dialog_open()`, `inventory(com)` (any inventory the server sends, such as `BANK`), `npc_type(id)`, `item_type(id)`, `loc_type(id)` |

A destination is a `Tile`, or an `(x, z)` pair on your level.

`npc_type`, `item_type` and `loc_type` return the cache's definitions, or `None` for an id it doesn't have:
- `NpcType`: `id`, `name`, `examine`, `ops` (five strings, `None` where the menu has nothing), `size`, `combat_level`.
- `ItemType`: the same, plus `inventory_ops`, `stackable`, `members`, `value`, and `note_of` (`None`, or the id of the item a banknote is a note of).
- `LocType`: the same, plus `width`, `length`, `blocks_walk` and `blocks_projectiles`.

## Control

- `log(*args)` writes at Info level and `debug(*args)` at Verbose level; `print()` also goes to the log. Each line carries the account's name.
- `stop_script()` stops calling the script; the account stays logged in and idles. A bot's `request_finish(reason)` does the same with a reason.
- `stop_account()` stops the script and logs the account out.
- `send_bot_message(username, message)` sends a message to another account's script in this process (see [Messages between scripts](#messages-between-scripts)).

## Interfaces and magic, for now

Until the phases that replace them ([BotApiDesign.md](BotApiDesign.md) §14), these take component ids, which stay constants in scripts:
- `click_button(com)` clicks an interface button;
- `continue_dialogue()` continues a "click here to continue" dialogue;
- `answer_count(value)` answers an amount prompt;
- `close_interfaces()` closes the open ones;
- `inv_button(item, op)` clicks an option, as a number, on an item in an interface inventory, such as the bank's withdraw options;
- `move_item(com, from_slot, to_slot)` swaps two slots;
- `cast_on_npc`, `cast_on_player`, `cast_on_loc`, `cast_on_ground_item` and `cast_on_item(spell, target)` cast the spell whose spellbook button component is `spell`. `cast_on_loc` takes `spell, id, x, z`.

The bank's main modal is 5292.

## Events and hooks

Every event has one name. A bot hears it through a hook, a function or method named `on_<event>`, or by subscribing: `events.on(name, callback)`, which returns a function that ends the subscription, or `self.on(name, callback)` in a bot, which ends when the bot stops. Hooks and subscribers that aren't there cost nothing. A script that defines an `on_` function the client doesn't know about gets a warning when it loads, which catches typos.

The events rs2b0t has pass one payload object, an `Event` with an attribute per field:

| Event | Payload | Happens when |
|---|---|---|
| `tick` | `tick` | A server tick passed |
| `chat_message` | `type` (`'game'`, `'public'`, `'private'`, `'trade_request'` or `'duel_request'`), `username` (`None` for a game message), `text` | Any line arrived in the chat box |
| `skill_xp` | `skill`, `name` (such as `'woodcutting'`), `xp`, `delta` | A skill gained experience |
| `skill_level` | `skill`, `name`, `level`, `previous` | A skill's base level changed |
| `inventory_changed` | `slot`, `id`, `name`, `count`, `previous_id`, `previous_count` | A backpack slot changed; one event per slot, with an empty slot's id -1 |
| `varp_changed` | `index`, `value`, `previous` | A player variable was set |
| `script_finish` | `reason` | The script stopped, after `on_stop` |

The rest pass their values:

| Event | Arguments | Happens when |
|---|---|---|
| `server_message` | `msg` | A game message arrived |
| `private_message` | `sender`, `msg` | A private message arrived |
| `trade_request`, `duel_request` | `name` | A player wants to trade or duel |
| `npc_spawned`, `npc_despawned` | `npc` | An NPC came into view or left it. A despawned NPC is its last snapshot, so `npc.hp == 0` means it died |
| `npc_damaged` | `npc`, `damage` | An NPC took a hit. `npc` is `None` if it has already left view |
| `player_spawned`, `player_despawned`, `player_damaged` | `player` (and `damage`) | The same, for other players |
| `damaged` | `damage` | You took a hit |
| `ground_item_spawned`, `ground_item_despawned`, `ground_item_changed` | `item` (and `previous_count`) | An item appeared, went, or had its stack count changed |
| `loc_changed` | `loc` | Scenery was added, changed or removed |
| `interface_changed` | | An interface opened or closed |
| `system_update` | `seconds` | The server announced a restart |
| `disconnect`, `reconnect` | | The connection dropped; it came back and the player is placed again. After a server restart the reconnect is a fresh login, so the state starts over, much as at login |
| `kill_signal` | | Ctrl+C was pressed. Call `stop_account()` once it's safe; after `scripting.killGraceSeconds` the account logs out anyway |
| `bot_message` | `sender`, `message` | Another script in this process sent this one a message (see [Messages between scripts](#messages-between-scripts)) |

A bot's lifecycle has hooks too, but no subscribers:

| Hook | Called when |
|---|---|
| `on_start()` | Once, when the player is first placed after login. One that's a generator runs before the first `loop()` |
| `on_stop(reason)` | Once, when the script stops: after `stop_script()`, `stop_account()`, `request_finish(reason)` or an error, or when the account logs out for a reason of its own, such as Ctrl+C. It can't wait |
| `on_progress_report()` | A progress report is due; return a `dict` (see [Progress reports](#progress-reports)) |

Events only report what the server said. When the map rebuilds, or an area falls out of view, things vanish from the state without a despawn event, so check what's in view rather than keeping your own copy.

## Progress reports

Set `script.progressReportMinutes` in the account file (1 to 1440) and define `on_progress_report()`, returning a `dict`:

```python
def on_progress_report():
    return {'Kills': kills, 'Bones': inventory.count('Bones')}
```

That many minutes after `on_start`, and every that many minutes after that, the client calls it, appends the result as a table to `progress/<account>.txt`, and logs it on one line. The folder is `scripting.progressDirectory` in `client.jsonc`, and each run starts the file afresh.

```
Progress at 2026-10-08T14:20:00Z, 1h 20m after the script started
+-------+-------+
| Name  | Value |
+-------+-------+
| Kills | 10    |
| Bones | 42    |
+-------+-------+
```

Names and values are shown with `str()`, in the dict's order. Returning anything but a `dict` is a script error. A report that falls due while the account is reconnecting waits until it's back.

## Messages between scripts

`send_bot_message(username, message)` sends `message` to the script of another account in the same process, named by the username in its account file, in any case. That script's `on_bot_message(sender, message)` receives it with the sender's username:

```python
# The worker's script
send_bot_message(settings.mule, {'want': 'trade', 'items': [[995, 1000]]})

# The mule's script
def on_bot_message(sender, message):
    if message['want'] == 'trade':
        log(sender, 'wants to trade')
```

- The message is copied as JSON, so it can be a dict with string keys, a list, a string, a number, a bool or `None`, nested as deep as you like, up to 64 KiB. Tuples arrive as lists. Anything else raises `TypeError`.
- It returns `True` once the message is queued. `False` means the receiver can't take it now: its script has stopped or doesn't define `on_bot_message`, or 100 of its messages are already waiting. A username that no account in the process has raises `ValueError`.
- Messages arrive in the order sent, on the receiver's next pass, and wait while it logs in or reconnects. A script can message itself; a message sent while handling one arrives on the next pass.

## Working on a script

### Reloading on save

`--watch` reloads a script whenever you save it, or a module it imports, without logging out:

```
rs2004-headless client.jsonc --account accounts/<name>.jsonc --watch
```

- The new code starts fresh: its globals are new, `on_start()` runs again, and events from before the save are skipped. Messages already queued for it are kept.
- If a save breaks the script, or the script fails later, the account stays logged in and idle until the next save, so a typo doesn't cost a login. The traceback is logged as usual. A script that can't load at startup still stops the run before any login.
- A change to the account file, such as new settings, needs a restart.

### Debugging in VS Code

`--debugger` lets VS Code debug one account's script, with breakpoints, stepping, the call stack, variables, and a debug console that can call the API (`game.tile()`, say).

1. Install VS Code's pocketpy extension (`pocketpy.pocketpy`).
2. Add an attach configuration to `.vscode/launch.json`. `sourceFolder` must be the scripts folder, or breakpoints aren't hit:

   ```json
   {
       "type": "pocketpy",
       "request": "attach",
       "name": "Attach to rs2004-headless",
       "host": "127.0.0.1",
       "port": 6110,
       "sourceFolder": "${workspaceFolder}/scripts"
   }
   ```

3. Run `rs2004-headless client.jsonc --account accounts/<name>.jsonc --debugger`. It loads the script, then waits with "Waiting for VS Code's pocketpy debugger to attach on 127.0.0.1:6110".
4. Start that configuration in VS Code. The account logs in once the debugger has attached.

pocketpy's debugger brings some limits:

- While the script is paused, the whole process is paused, and the server hears nothing from the client. A long pause may end in a reconnect.
- `scripting.callTimeoutMs` doesn't apply while the debugger is attached.
- An uncaught exception stops in the debugger and stays there.
- Stopping the debug session ends the process at once, without logging out. To log out cleanly, press Ctrl+C in the client first.
- Breakpoints work in the script and in modules beside it in `scripts/`, but not in modules imported from `scripts/lib/`.
- `--debugger` needs `--account`, and can't be combined with `--watch`.

## Constants

- **Inventories:** `INVENTORY`, `EQUIPMENT`, `BANK` and `BANK_INVENTORY` (your backpack while the bank is open), plus `INVENTORY_SIZE`. Their values come from the server's cache. Use them with `reader.inventory(com)` and the interface functions.
- **Skills:** `ATTACK`, `DEFENCE`, `STRENGTH`, `HITPOINTS`, `RANGED`, `PRAYER`, `MAGIC`, `COOKING`, `WOODCUTTING`, `FLETCHING`, `FISHING`, `FIREMAKING`, `CRAFTING`, `SMITHING`, `MINING`, `HERBLORE`, `AGILITY`, `THIEVING`, `RUNECRAFT`: the indexes `skills.index(name)` and the skill events give.
- **Scenery layers:** `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`.
- **Combat:** `COMBAT_TICKS`.

## Limits

- **Interfaces are numbers,** until phase 3 of [BotApiDesign.md](BotApiDesign.md). The cache's interface definitions are read only to find a few components, so ids such as the bank's stay constants in scripts, and `inv_button` takes option numbers.
- **Walking stays in the loaded area,** until phase 6. A tile beyond it is walked to in a straight line.
- **"Nearest" counts tiles.** A query's `nearest()` measures in tiles, not steps, so with `reachable()` the nearest target that can be reached may still be a long walk round.

## Editor support

`scripts/typings/__builtins__.pyi` declares everything above for Pylance and Pyright, and the repository's `pyrightconfig.json` points them at it. So opening either the repository or the `scripts` folder gives completion and type checks in scripts.

## Porting from rs2b0t

This API is rs2b0t's, in Python's style, so a bot translates mostly line by line:

| TypeScript | Python |
|---|---|
| `class Miner extends LoopingBot { loop() {...} }` | `class Miner(LoopingBot): def loop(self): ...` |
| `export default defineBot({ name: 'Miner', create: () => new Miner() })` | `BOT = define_bot(name='Miner', create=Miner)` |
| `await Execution.delayUntil(() => Inventory.isFull(), 3000)` | `yield from execution.delay_until(lambda: inventory.is_full(), 3000)` |
| `Npcs.query().name('Guard').within(3).nearest()` | `npcs.query().name('Guard').within(3).nearest()` |
| `npc.inCombat`, `item.useOn(range)` | `npc.in_combat`, `item.use_on(range)` |
| `this.settings.str('rock', 'Copper rocks')` | `self.settings.str('rock', 'Copper rocks')` |
| `this.on('skill.xp', e => ...)` | `self.on('skill_xp', lambda e: ...)` |
| `Game.tile()?.x` | `game.tile().x if game.tile() else None` |

- Facades are lower-case (`Npcs` is `npcs`, `GroundItems` is `ground_items`), and camelCase is snake_case. A name that's a Python keyword gains a trailing underscore.
- What rs2b0t has that's here so far: bots, `Execution`, settings, events, `Tile` and `Area`, the entity facades and their query, `Inventory`, `Equipment`, `InvItem`, `Skills`, `Game`'s basics, `DirectNavigator` and `reader`. [BotApiDesign.md](BotApiDesign.md) plans the rest, phase by phase.
- Differences:
    - a thing's `interact` walks to it first, as the webclient's does;
    - `npc.level` is its combat level, and every thing's level of the map is `thing.tile().level`;
    - `chat_message`'s `type` is a name (`'game'`, `'public'` and so on) rather than the webclient's number;
    - a setting that doesn't fit its schema is an error before login rather than quietly the default.

## Porting from plutonium

`loop`, `settings` and `log` work much the same way, and so do most hooks. The differences:

- `loop()`'s return is read as rs2b0t reads it: 600 waits for the next server tick, 0 for the next pass, and anything else that many milliseconds.
- `on_npc_damaged(npc, damage)` and `on_player_damaged(player, damage)` take the entity first. plutonium's take the damage first, so a ported hook gets its arguments swapped without any error.
- `on_chat_message(msg, from_name)` becomes `on_chat_message(e)`, with `e.username` and `e.text`, and `on_private_message(msg, from_name)` becomes `on_private_message(sender, msg)`. `on_server_tick(tick)` becomes `on_tick(e)`, with `e.tick`.
- `on_load` and `on_init` become `on_start`, which runs once, and `on_reconnect`, which runs each time the player is placed again after a dropped connection.
- `on_progress_report` and `send_bot_message` work as in plutonium, with two differences. A message is copied as JSON, so it can't carry objects. A full queue makes `send_bot_message` return `False` instead of raising.

Coordinates differ between RSC and 2004, so every tile in a script changes. An `Area.rectangular(a, b)` takes any two opposite corners.

| plutonium | Here |
|---|---|
| `get_x()`, `get_z()`, `at(x, z)`, `distance_to(x, z)` | `game.tile()`, `game.tile().distance_to((x, z)) == 0`, `game.tile().distance_to((x, z))` |
| `in_rect(...)`, `point_in_rect(...)`, `point_in_polygon(...)` | `Area.rectangular(a, b).contains(tile)`, `Area.polygon(points).contains(tile)` |
| `walk_path_to(x, z)`, `walk_to(x, z)` | `direct_navigator.walk((x, z))`, within the loaded area for now |
| `calculate_path_to(x, z)` | `direct_navigator.path((x, z))`, the waypoints, within the loaded area. There's no path object |
| `get_my_player()` | `players.local()` |
| `get_nearest_npc_by_id(ids, in_combat=False, ...)`, `get_nearest_npc_by_id_in_rect(...)` | `npcs.query().id(ids).where(lambda n: not n.in_combat).nearest()`, with `.inside(area)` |
| `get_nearest_object_by_id`, `get_objects` | `locs.query().id(...).nearest()`, `locs.query().results()` |
| `get_nearest_wall_object_by_id`, `get_wall_objects` | The same, with `.layer(LAYER_WALL)` |
| `get_object_from_coords(x, z)`, `get_wall_object_from_coords(x, z)` | `locs.at((x, z))`, `locs.at((x, z), LAYER_WALL)` |
| `get_nearest_ground_item_by_id(...)`, `is_ground_item_at(id, x, z)` | `ground_items.query().id(...).nearest()`, `...within_of((x, z), 0).exists()` |
| `at_object(obj)`, `at_object2(obj)`, and the wall object versions | `loc.interact(1)`, `loc.interact(2)`, or the option's text |
| `attack_npc(npc)`, `talk_to_npc(npc)`, `thieve_npc(npc)` | `npc.interact('Attack')`, `npc.interact('Talk-to')`, `npc.interact('Pickpocket')` |
| `pickup_item(item)` | `item.interact('Take')` |
| `trade_player(player)`, `follow_player(player)` | `player.interact('Trade with')`, `player.interact('Follow')` |
| `use_item(item)`, `drop_item(item)` | `item.interact('Eat')` (or the item's option), `item.interact('Drop')` |
| `use_item_with_item`, `use_item_on_object`, `use_item_on_npc` and the rest | `item.use_on(target)` |
| `get_inventory_items()`, `get_inventory_item_by_id(id)`, `get_inventory_item_except(ids)` | `inventory.items()`, then a comprehension: `[i for i in inventory.items() if i.id == id]` |
| `get_inventory_count_by_id(id)`, `has_inventory_item(id)` | `inventory.count_by_id(id)`, `inventory.count_by_id(id) > 0` |
| `get_total_inventory_count()`, `get_empty_slots()` | `inventory.used()`, `inventory.free()` |
| `equip_item(item)`, `unequip_item(item)`, `is_inventory_item_equipped(id)` | `yield from equipment.equip(name)`, `yield from equipment.unequip(name)`, `equipment.contains(name)` |
| `get_max_stat(id)`, `get_current_stat(id)`, `get_experience(id)`, `get_hp_percent()` | `skills.level(name)`, `skills.effective(name)`, `skills.xp(name)`, `skills.hp_fraction()` |
| `get_item_name(id)` | `reader.item_type(id).name` |
| `in_combat()`, `is_skilling()` | `game.in_combat()`, `game.animating()` |
| `send_chat_message(text)`, `send_private_message(name, text)` | `chat.say(text)`, `chat.send_pm(name, text)` |
| `get_friends()`, `get_ignored()`, `add_friend(name)` and the rest | `friends.list()`, `ignores.list()`, `friends.add(name)` and so on |
| `cast_on_self(spell)` | `click_button(spell)`, since 2004 casts those spells from the spellbook button |
| `random(min, max)` | `random.randint(min, max)`, after `import random` |
| `set_autologin(False)` then `logout()` | `stop_account()` |

Not here yet:
- walking beyond the loaded area;
- helpers for the bank, shops, trades, dialogue options and skills' make menus (Make 1, 5, 10 and X), combat style, prayers and quests;
- logging out and back in;
- hooks for dying, NPCs' overhead text and projectiles;
- character design.

[BotApiDesign.md](BotApiDesign.md) plans all of them; until then the interface ones take component ids. Fatigue, sleeping, the sleepword and raw packets don't exist.

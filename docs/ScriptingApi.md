# Scripting API

How to write Python scripts that drive the headless client. A script is a `.py` file in the scripts folder; each account file names the script it runs. The design behind it is in [ScriptingDesign.md](ScriptingDesign.md), and [BotApiDesign.md](BotApiDesign.md) plans where it's going: rs2b0t's bot API, in Python's style. Its first phase, the runtime (bots, waits, settings schemas and events), is here; the rest of this page still describes the flat functions it will replace.

## Quick start

1. Copy `accounts/example.jsonc.sample` to `accounts/<name>.jsonc` and fill in the username and password. The file name becomes the account's name in log lines.
2. Point `script.file` at a script, relative to `scripts/`, such as `examples/chicken_killer.py`.
3. Run `rs2004-headless client.jsonc` to run every enabled file in `accounts/`, logging them in `scripting.loginIntervalSeconds` apart, or add `--account accounts/<name>.jsonc` to run just that one. One process runs up to 16 scripted accounts.

An account file can have its own `server` section, with the same keys as `client.jsonc`'s, to log that account into a different world.

Ctrl+C asks each script to finish (see `on_kill_signal`). A second Ctrl+C logs every account out at once, and one more closes any connection whose logout the server is still refusing. The exit code is 0 when every account logged out cleanly and no script failed.

A dropped connection is restored automatically, with up to 10 attempts over about four minutes, so a server restart doesn't end a run. Each account reconnects on its own and the others keep playing. A first login is retried the same way when the server can't take it yet, for example "already logged in" after a crash.

A script is a bot, as in rs2b0t's API: either a class set with `BOT = define_bot(...)`, or a module-level `loop()` with `on_*` hooks, which runs as a `LoopingBot`. `loop()` returns how long to wait before it's called again:

```python
def on_start():
    log('Starting at', get_x(), get_z())

def loop():
    if in_combat():
        return 600          # the next server tick

    chicken = get_nearest_npc_by_name('Chicken', radius=8, in_combat=False)
    if chicken is not None:
        attack_npc(chicken)
        # Wait until the fight starts, or 3 seconds.
        yield from execution.delay_until(lambda: in_combat(), 3000)

def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()
```

The same as a bot, with its settings declared, and tasks chosen in priority order:

```python
class Fighter(TaskBot):
    def on_start(self):
        self.add(
            Task(lambda: in_combat(), lambda: None, label='fight'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def attack(self):
        chicken = get_nearest_npc_by_name(self.settings.npc, radius=8, in_combat=False)
        if chicken is not None and attack_npc(chicken):
            yield from execution.delay_ticks(2)

BOT = define_bot(name='Fighter', create=Fighter, settings_schema={'npc': SettingDef('string', 'Chicken')})
```

`scripts/examples/` has complete scripts: `chicken_killer.py` is a `TaskBot` that fights, loots and logs out, and `walker.py` is a module-level script that walks a loop of tiles, optionally for a set number of laps, telling a partner account about each one. Both make progress reports.

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
- Objects such as `Npc` are snapshots taken when the function returned. Keep the `index` to look one up again later with `get_npc(index)`.
- Actions queue packets and return at once; their effects show up in the state over the next ticks. Actions on a target that's no longer in view return `False`. A wrong argument type raises `TypeError`, and a value out of range (an option outside 1 to 5, say) raises `ValueError`.
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
    raw = get_inventory_item_by_name('Raw shrimps')
    use_item_on_loc(raw, RANGE, 3212, 3215)
    cooked = yield from execution.delay_until(lambda: get_inventory_count_by_name('Shrimps') > 0, 5000)
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

## Objects

| Class | Attributes |
|---|---|
| `Npc` | `index`, `id` (NPC type), `name` (`None` when the type has none or isn't in the cache), `combat_level` (`None` when the menu shows none), `size`, `x`, `z`, `level`, `animation` (-1 for none), `hp` and `max_hp` (`None` until a hit reveals them), `last_hit_tick`, `target` (`('npc' or 'player', index)` or `None`); methods `is_moving()` and `in_combat()` |
| `Player` | `index`, `name` (`None` until its appearance arrives), `combat_level`, then the same position, health, target and methods as `Npc` |
| `GroundItem` | `id`, `name`, `count`, `x`, `z`, `level` |
| `Loc` | `id` (-1 when the server removed the scenery), `name`, `x`, `z`, `level`, `shape`, `angle`, `layer` (a `LAYER_*` constant), `changed` (`False` for scenery as the cache has it, `True` for the server's changes) |
| `Item` | `id`, `name`, `count`, `slot`, `com` (the inventory component, such as `INVENTORY`) |
| `NpcType` | `id`, `name`, `examine`, `ops` (five strings, `None` where the menu has nothing), `size`, `combat_level` |
| `ItemType` | `id`, `name`, `examine`, `ops` (on the ground), `inventory_ops`, `stackable`, `members`, `value`, `note_of` (`None`, or the id of the item a banknote is a note of) |
| `LocType` | `id`, `name`, `examine`, `ops`, `width`, `length`, `blocks_walk`, `blocks_projectiles` |

`in_combat()`, for an entity or for yourself, means it was hit within the last `COMBAT_TICKS` (8) ticks. 2004 has no combat-state packet, so this is an approximation; `last_hit_tick` is there for a different window. Positions are absolute tile coordinates. Functions that take `x, z` use your current level.

## Functions

### You

| Function | Returns |
|---|---|
| `get_x()`, `get_z()`, `get_level()`, `get_position()` | Your tile; `get_position()` is `(x, z)` |
| `get_pid()`, `get_name()`, `get_combat_level()` | Your player index, display name and combat level |
| `get_run_energy()`, `get_weight()`, `is_running()` | Run energy (0 to 100), weight in kg, whether run mode is on |
| `is_moving()`, `get_walk_destination()` | Whether you're walking; the `(x, z)` you last walked toward, or `None` once you arrive or the walk ends. A walk the server never starts, because the first step is blocked, ends after three ticks without movement |
| `in_combat()` | Whether you were hit within the last 8 ticks |
| `get_local_player()` | You, as a `Player` |
| `get_current_stat(stat)`, `get_max_stat(stat)`, `get_experience(stat)` | A stat's current level, base level and experience; `stat` is a constant such as `WOODCUTTING` |
| `get_hp()`, `get_max_hp()`, `get_hp_percent()` | Hitpoints now, at full, and as a whole percentage |
| `get_tick()` | The number of server ticks since login |

### Distances

Distances count tiles in the larger of the two directions.

| Function | Returns |
|---|---|
| `distance_to(x, z)` | Tiles from you to the tile |
| `distance(x1, z1, x2, z2)` | Tiles between two tiles |
| `in_radius_of(x, z, radius)` | Whether you're within `radius` tiles of the tile |
| `in_rect(x, z, width, height)` | Whether you're in the rectangle whose south-west corner is `(x, z)` |
| `at(x, z)` | Whether you're on the tile |

### NPCs, players, the ground and scenery

`ids` takes one id, a list of ids, or `None` for any. `names` takes one name or a list, matched without regard to case; a type with no name never matches. `radius` limits the search to that many tiles from you, on your level. "Nearest" counts tiles, not steps, and ties go to the first in the server's order. `reachable=True` skips targets the client can't find a route to, by the same rule the matching interaction walks by.

| Function | Returns |
|---|---|
| `get_npcs(ids=None, radius=None)` | Every matching `Npc` in view, in the server's order |
| `get_nearest_npc_by_id(ids=None, radius=None, in_combat=None, reachable=False)` | The nearest matching `Npc` or `None`; `in_combat=False` skips NPCs being fought |
| `get_nearest_npc_by_name(names, radius=None, in_combat=None, reachable=False)` | The same, matching names |
| `get_npc(index)` | The `Npc` with that index, if it's still in view |
| `get_players(radius=None)`, `get_player_by_name(name)` | Other players in view; one by name, or `None` |
| `get_ground_items(ids=None, radius=None)` | `GroundItem`s you can see |
| `get_nearest_ground_item_by_id(ids=None, radius=None, reachable=False)`, `get_nearest_ground_item_by_name(names, radius=None, reachable=False)` | The nearest matching `GroundItem` or `None` |
| `get_loc_at(x, z, layer=None)` | The scenery on the tile now: the server's change, or else the cache's. Without a layer, the first in layer order, preferring scenery that's there to a removed one. Decoration with no name, no option and nothing to walk into isn't kept |
| `get_locs(ids=None, radius=None, layer=None)` | Every `Loc` on your level in the area the server has loaded, nearest first, leaving out removed ones |
| `get_nearest_loc_by_id(ids=None, radius=None, layer=None, reachable=False)`, `get_nearest_loc_by_name(names, radius=None, layer=None, reachable=False)` | The nearest matching `Loc`, or `None` |

### Types

| Function | Returns |
|---|---|
| `get_npc_type(id)`, `get_item_type(id)`, `get_loc_type(id)` | The `NpcType`, `ItemType` or `LocType`, or `None` for an id the cache doesn't have |

### Inventories and interfaces

| Function | Returns |
|---|---|
| `get_inventory(com=INVENTORY)` | The `Item`s in an inventory's occupied slots; `BANK` and `EQUIPMENT` work too while the server sends them |
| `get_equipment()` | Your worn `Item`s |
| `get_inventory_count_by_id(ids, com=INVENTORY)`, `get_inventory_count_by_name(names, com=INVENTORY)` | The total count of matching items |
| `get_inventory_item_by_id(ids, com=INVENTORY)`, `get_inventory_item_by_name(names, com=INVENTORY)` | The first matching `Item`, or `None` |
| `get_empty_slots()`, `is_inventory_full()` | Free backpack slots out of `INVENTORY_SIZE` (28) |
| `get_main_modal()`, `get_side_modal()`, `get_chat_modal()` | The open interface ids, -1 for none; the bank is main modal 5292 |
| `is_interface_open(id)`, `is_count_dialog_open()` | Whether an interface or the "enter amount" dialog is open |
| `get_component_text(com)` | Text the server set on a component, or `None` |
| `get_varp(id)` | A player variable; for example `get_varp(173)` is 1 while running |
| `get_friends()`, `get_ignores()` | `[(name, world)]` and `[name]` |

### Actions

`op` is the option number, 1 to 5, in the order the right-click menu lists them, or the option's text, matched without regard to case: `interact_npc(npc, 'Pickpocket')`. Ground items also offer "Take" as op 3, and inventory items "Drop" as op 5, where their type has nothing there, as the menu does. Text that matches no option raises `ValueError`, listing the options there are.

The server walks each waypoint in a straight line, so walks and interactions find a route around walls and scenery first, as the webclient does, and send its turning points. An interaction with no route still sends its option, and the server walks as far as it can.

| Function | Does |
|---|---|
| `walk_to(x, z, run=False)` | Walks a route to the tile, or to the reachable tile beside it with the fewest steps. Returns `False`, and doesn't walk, when the tile is in view but can't be reached. A tile beyond the loaded area is walked to in a straight line |
| `walk_path(points, run=False)` | Walks through up to 25 `(x, z)` waypoints, each leg in a straight line, without routing |
| `is_reachable(x, z)` | Whether a walk can end on the tile |
| `find_path(x, z)` | The `(x, z)` waypoints `walk_to` would send, or `None` without a route |
| `interact_npc(npc, op)`, `talk_to_npc(npc)`, `attack_npc(npc)` | Walks to the NPC and uses an option: talk-to is 1, attack is 2. `npc` is an `Npc` or its index |
| `interact_player(player, op)` | The same, for a player; text matches the options the server set, such as "Follow" |
| `interact_loc(loc, op)`, `interact_loc(id, x, z, op)` | Walks to the scenery and uses an option; a `Loc` stands in for `id, x, z` |
| `interact_loc_via(points, id, x, z, op)` | The same, walking your waypoints instead of a route |
| `interact_ground_item(item, op)`, `take_ground_item(item)` | Uses an option on a `GroundItem`; take is 3 |
| `item_op(item, op)`, `drop_item(item)` | Uses an option on an inventory `Item`; drop is 5 |
| `inv_button(item, op)` | Clicks an option on an item in an interface inventory, such as the bank's withdraw options. Its options come from the interface, which the client doesn't decode, so `op` is a number |
| `move_item(com, from_slot, to_slot)` | Swaps two slots |
| `use_item_on_npc / _player / _loc / _ground_item / _item(item, target)` | Uses an `Item` on something; `_loc` takes `id, x, z` |
| `cast_on_npc / _player / _loc / _ground_item / _item(spell, target)` | Casts the spell whose spellbook button component is `spell` |
| `click_button(com)`, `continue_dialogue()`, `answer_count(value)`, `close_interfaces()` | Clicks an interface button; continues a "click here to continue" dialogue; answers an amount prompt; closes open interfaces |
| `set_run(run)` | Turns run mode on or off |
| `say(text)`, `send_pm(name, text)`, `command(text)` | Public chat, a private message, and `::command` for staff accounts (for example `command('tele 0,50,51,30,34')`) |
| `add_friend(name)`, `remove_friend(name)`, `add_ignore(name)`, `remove_ignore(name)` | Friends and ignore lists |
| `stop_script()` | Stops calling the script; the account stays logged in and idles |
| `stop_account()` | Stops the script and logs the account out |
| `send_bot_message(username, message)` | Sends a message to another account's script in this process (see [Messages between scripts](#messages-between-scripts)) |

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
    return {'Kills': kills, 'Bones': get_inventory_count_by_id(526)}
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

`--debugger` lets VS Code debug one account's script, with breakpoints, stepping, the call stack, variables, and a debug console that can call the API (`get_x()`, say).

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

- **Inventories:** `INVENTORY`, `EQUIPMENT`, `BANK` and `BANK_INVENTORY` (your backpack while the bank is open), plus `INVENTORY_SIZE`. Their values come from the server's cache.
- **Stats:** `ATTACK`, `DEFENCE`, `STRENGTH`, `HITPOINTS`, `RANGED`, `PRAYER`, `MAGIC`, `COOKING`, `WOODCUTTING`, `FLETCHING`, `FISHING`, `FIREMAKING`, `CRAFTING`, `SMITHING`, `MINING`, `HERBLORE`, `AGILITY`, `THIEVING`, `RUNECRAFT`.
- **Scenery layers:** `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`.
- **Combat:** `COMBAT_TICKS`.

## Limits

- **Interfaces are numbers.** The cache's interface definitions are read only to find the logout button, so component ids, such as the bank's, stay constants in scripts, and `inv_button` takes option numbers.
- **"Nearest" counts tiles.** The `get_nearest_*` functions measure in tiles, not steps, so with `reachable=True` the nearest target that can be reached may still be a long walk round.

## Editor support

`scripts/typings/__builtins__.pyi` declares everything above for Pylance and Pyright, and the repository's `pyrightconfig.json` points them at it. So opening either the repository or the `scripts` folder gives completion and type checks in scripts.

## Porting from plutonium

`loop`, `settings` and `log` work much the same way, and so do most hooks. The differences:

- `loop()`'s return is read as rs2b0t reads it: 600 waits for the next server tick, 0 for the next pass, and anything else that many milliseconds.
- `on_npc_damaged(npc, damage)` and `on_player_damaged(player, damage)` take the entity first. plutonium's take the damage first, so a ported hook gets its arguments swapped without any error.
- `on_chat_message(msg, from_name)` becomes `on_chat_message(e)`, with `e.username` and `e.text`, and `on_private_message(msg, from_name)` becomes `on_private_message(sender, msg)`. `on_server_tick(tick)` becomes `on_tick(e)`, with `e.tick`.
- `on_load` and `on_init` become `on_start`, which runs once, and `on_reconnect`, which runs each time the player is placed again after a dropped connection.
- `on_progress_report` and `send_bot_message` work as in plutonium, with two differences. A message is copied as JSON, so it can't carry objects. A full queue makes `send_bot_message` return `False` instead of raising.

Coordinates differ between RSC and 2004, so every tile in a script changes. `in_rect(x, z, width, height)` takes the south-west corner, with the width going east and the height going north; plutonium's took the north-west corner in RSC's coordinates.

Calls with another name or form:

| plutonium | Here |
|---|---|
| `walk_path_to(x, z)` | `walk_to(x, z)`. It routes only inside the area the server has loaded (see [Limits](#limits)) |
| `calculate_path_to(x, z)` | `find_path(x, z)`, the waypoints `walk_to` would send, inside the loaded area. There's no path object |
| `get_item_name(id)` | `get_item_type(id).name` |
| `get_my_player()` | `get_local_player()` |
| `get_nearest_object_by_id`, `get_objects` | `get_nearest_loc_by_id`, `get_locs` |
| `get_nearest_wall_object_by_id`, `get_wall_objects` | The same, with `layer=LAYER_WALL` |
| `get_object_from_coords(x, z)`, `get_wall_object_from_coords(x, z)` | `get_loc_at(x, z)`, `get_loc_at(x, z, LAYER_WALL)` |
| `at_object(obj)`, `at_object2(obj)`, and the wall object versions | `interact_loc(loc, 1)`, `interact_loc(loc, 2)` |
| `pickup_item(item)` | `take_ground_item(item)` |
| `use_item(item)` | `item_op(item, op)` with the option's text, such as `'Eat'` |
| `use_item_with_item`, `use_item_on_object`, `use_item_on_wall_object` | `use_item_on_item`, `use_item_on_loc` |
| `thieve_npc(npc)` | `interact_npc(npc, 'Pickpocket')` |
| `trade_player(player)`, `follow_player(player)` | `interact_player(player, 'Trade with')`, `interact_player(player, 'Follow')` |
| `cast_on_self(spell)` | `click_button(spell)`, since 2004 casts those spells from the spellbook button |
| `get_inventory_items()` | `get_inventory()` |
| `get_total_inventory_count()` | `INVENTORY_SIZE - get_empty_slots()` |
| `has_inventory_item(id)` | `get_inventory_item_by_id(id) is not None` |
| `is_inventory_item_equipped(id)` | `get_inventory_item_by_id(id, com=EQUIPMENT) is not None` |
| `send_chat_message(text)`, `send_private_message(name, text)` | `say(text)`, `send_pm(name, text)` |
| `get_ignored()` | `get_ignores()` |
| `is_skilling()` | `get_local_player().animation != -1` |
| `random(min, max)` | `random.randint(min, max)`, after `import random` |
| `set_autologin(False)` then `logout()` | `stop_account()` |

Not here yet: walking beyond the loaded area; helpers for the bank, shops, trades, dialogue options and skills' make menus (Make 1, 5, 10 and X), combat style, prayers and quests; logging out and back in; hooks for dying, NPCs' overhead text and projectiles; and character design. Until then the interface ones take component ids as constants. [BotApiDesign.md](BotApiDesign.md) plans all of them, and replaces this API with one modelled on rs2b0t's, so this table will be rewritten for it.

Fatigue, sleeping, the sleepword and raw packets don't exist.

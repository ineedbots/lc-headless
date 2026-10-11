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
- A function can read the variables of the function it's defined in, but not of one further out. A lambda inside a nested function that uses the outer function's parameter fails, or quietly gets a builtin of the same name, such as `id`; copy the value into a local of the nested function first.
- `match` is a keyword, so it can't name a variable or parameter. Where rs2b0t's functions take `match`, ours take `text` or `name`.

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
- `actions()`, as the right-click menu shows them. In the backpack these are the item's own, with "Drop" where its type has nothing there. In the bank, a shop, the worn equipment and other interfaces they're the inventory's, such as "Withdraw 5" or "Remove";
- `interact(action)`, such as `item.interact('Eat')` or `item.interact('Withdraw 5')`;
- `use_on(target)`, with another `InvItem`, an `Npc`, a `Player`, a `Loc` or a `GroundItem`.

## You and the game

| Facade | Functions |
|---|---|
| `game` | `ingame()`, `tile()` (`None` before you're placed), `energy()` (run energy, 0 to 100), `run_enabled()`, `set_run(on)`, `weight()`, `in_combat()`, `animating()`, `moving()`, `tick()` (server ticks since login), `my_name()`, `combat_level()`, `appearance_screen_open()`, `set_appearance(female, kits, colours)` |
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
- `relog(delay_seconds=0)` logs the account out, waits, and logs it back in, with the script still loaded. `loop()` and the hooks wait meanwhile; `on_disconnect` is called at the logout and `on_reconnect` once the player is placed again, and a wait in progress carries on. It retries the logout as `stop_account()` does, through 10 seconds after combat. Ctrl+C during the wait ends the account logged out.
- `game.set_appearance(female, kits, colours)` saves a character design and accepts it, as on a new account's design screen: 7 body kits (head, jaw, torso, arms, hands, legs, feet, as identity kit ids) and 5 colours (hair, torso, legs, feet, skin). `False` when `game.appearance_screen_open()` isn't true. The server checks the design and ignores one it doesn't allow; the engine's default man is `(False, [0, 10, 18, 26, 33, 36, 42], [0, 0, 0, 0, 0])`.
- `send_bot_message(username, message)` sends a message to another account's script in this process (see [Messages between scripts](#messages-between-scripts)).

## Walking across the world

```python
arrived = yield from traversal.walk_resilient(Tile(3253, 3420, 0), 2)
```

`traversal` walks anywhere on the map: through doors and gates, up and down stairs and ladders, over the Al Kharid toll, onto ships and through the other crossings rs2b0t knows. The route comes from a search over the whole map, which the client builds from the cache at startup, together with rs2b0t's walker data in `client.navDirectory`. The walker then follows the route as rs2b0t's does:
- it finds where you are on the route and clicks the furthest tile ahead the client can walk to;
- it takes each hop once it reaches the tile before it;
- it plans again when the world disagrees: a door that won't open, a stall, or a step off the route.

| Function | Returns or does |
|---|---|
| `walk_to(dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None)` | Walks to within `radius` of `dest` and gives `True` on arrival, or when the route ends as close as it can get. `timeout_ms` defaults to 5 minutes |
| `walk_resilient(dest, radius=2, attempts=None, timeout_ms=None, ...)` | `walk_to` behind rs2b0t's escalation ladder. A failed walk is followed by a walk within the loaded area, then a step to unstick, then a pause, before planning again. It gives up after `attempts` passes without progress, or once a fresh search finds no route at all |
| `last_outcome`, `last_reason` | How the last walk ended: `'arrived'`, `'closest'` (as near as the route goes), `'blocked'`, `'budget'`, `'failed'`, `'unreachable'` or `'interrupted'`, and why a search failed |
| `remaining` | Route tiles left on the walk in progress |
| `request_repath(reason=None)` | Plans the walk in progress again at its next step |
| `route_cost(start, dest, max_expansions=300000)` | The cost of the route a walk would plan, without walking it, or `None` when there's none, as past a gate the account can't open |
| `try_nearby_door(log=None)` | Opens a shut door or gate beside you |
| `teleports_enabled()` | Whether walks use teleports unless told otherwise. They don't, as in rs2b0t |

- **Requirements.** A route's hops are checked against the account: skills, quests, the coins for a toll or fare, items to use, and members' areas. A hop the account can't make isn't planned. So without 10 coins, a walk into Al Kharid goes round rather than through the toll gate.
- **Teleports.** These are off by default. Pass `**NAV_WITH_TELES` to plan spell teleports the backpack has the runes for, or `**NAV_PURE_WALK` to walk.
- **Policy.** `policy` is a dict of `use_teleports`, `use_ships`, `use_shortcuts`, `allow_teleport_ids` and `deny_teleport_ids`.
- **Avoided zones.** `avoid_zones` are areas a route never enters, though it may leave one it starts in. They're ids from rs2b0t's catalog, such as `'white-wolf-mountain'`, or dicts of `min_x`, `max_x`, `min_z`, `max_z` and optionally `level`. Draynor's jail guards are avoided automatically below combat level 51.
- **Banks.** `nearest_bank(tile)`, `nearest_banks(tile)` and `nearest_reachable_bank(tile)` rank rs2b0t's known banks, leaving out those the account can't use. `banking.open()` walks to the nearest reachable one when none is in the area.

## Reach

`reach` is the last mile: walk to a stand, use something, and when a door is in the way, open it and try again. Each function is a generator that gives `'done'` once `expect()` holds, `'retry'` when it doesn't yet, and `'unreachable'` when the stand or the target can't be reached and no door explains it.

```python
status = yield from reach.loc_op('Crate', 'Search', Tile(3208, 3210), lambda: game_messages.saw_since(mark, 'You search the crate'))
status = yield from reach.npc_dialog('Cook', Tile(3208, 3210))
```

- `loc_op(name, op, near, expect, within=10, id=None, expect_ms=12000, refused=None, log=None)` walks to `near`, then uses `op` on the nearest loc of that name with that option within `within` tiles. `id` picks one when the name is shared. When the server answers "I can't reach that!", reach opens the door in front, or closes an open one that's swung across the way, and tries again. `refused` is a game message that says the op can't run yet, so it isn't retried.
- `npc_dialog(name, near, open_ms=15000, log=None)` walks to `near` and talks to the NPC until a dialogue opens. An NPC can wander, which can put the server's verdict off for good, so the scene within `PROBE_RADIUS` (10) tiles is searched for the door first.
- `entity_op(find, op, expect, open_when_unreachable=False, expect_ms=5000, what=None, log=None)` uses `op` on whatever `find()` gives.

A door is a wall loc named "door" or "gate" with an Open option; an open one has a Close option. `is_openable_barrier(name, actions)`, `is_open_barrier_leaf(name, actions)`, `open_op(actions)`, `close_op(actions)`, `talk_op(actions)` and `toward_dest(door, here, dest)` are the rules it uses.

Reach walks to `near` within the loaded area, so `near` must be reachable from where you are: reach opens the door between the stand and the target, not doors on the way to the stand. Use `traversal` to get there first.

`game_messages` tells what the server said after an action:
- `mark()`;
- `since(mark)`, each a `GameMessage` with `seq` and `text`;
- `saw_since(mark, pattern)` and `first_since(mark, pattern)`;
- `recent(limit=8)`, newest first.

A pattern is text, matched as part of the message without regard to case, or a callable given the text. `CANT_REACH` and `WRONG_SIDE` are two. It covers the last 100 messages.

`direct_navigator.last_outcome` says how the last `walk_to` ended: `'arrived'`, `'unreachable'` or `'timeout'`.

## Dialogues and make menus

`chat_dialog` is the chat box: dialogue pages, choices and make menus. Each is recognised by its shape, not its ids.

```python
while chat_dialog.can_continue():
    yield from chat_dialog.continue_()
yield from chat_dialog.choose_option('Yes')
yield from chat_dialog.make_x('Long Bow', 27)
```

| Function | Returns or does |
|---|---|
| `is_open()` | A chat box interface is open |
| `can_continue()` | A "Click here to continue" is showing and hasn't been clicked yet. The webclient sends one click per page, and so do we |
| `continue_()` | Clicks it, and waits for the next page or the end |
| `texts()` | The chat box's lines, such as the speaker's name and what they say, without colour tags |
| `options()` | The choices on offer |
| `choose_option(text=None)` | Chooses the first option containing `text`, or the first option, and waits for what comes next |
| `is_make_menu()`, `make_products()` | Whether a make menu is open, and its products' names |
| `products()` | The products as `MakeProduct`s |
| `make(name=None)` | Makes as many of the first product whose name contains `name` as one button makes without asking: "all" where there's such a button, otherwise the largest count |
| `make_one(name=None)` | Clicks its "1" button |
| `make_x(name, count)` | Clicks its "X" button and answers the count dialog with `count` |
| `is_main_make_panel()`, `main_make_products()` | The same for make panels, such as the anvil and gold jewellery, which are inventories whose options make things |
| `make_from_panel(name, op=None)` | Uses option `op`, such as `'Make 5'`, or the first, on the panel product |
| `make_from_panel_max(name)` | Uses the option that makes the most |

Each one that waits is a generator, so use it with `yield from`. It gives `True` once the server has opened, closed or changed an interface in answer, and `False` when the server didn't answer within 3 seconds, or there was nothing to click.

What counts as what:
- **Options** are the chat box's text buttons, as `multi2` to `multi5` have them.
- **Make menus** are stacks of buttons over each product, one button per amount, all the same size and in the same place. Fletching's "Make 1" to "Make X", the furnace's "Smelt 1 @lre@Bronze" and the tanner's "Tan all" are all make menus. A stack in the chat box makes a chat box make menu, or else a stack in the main interface, as the tanner's is.
- **A product's name** is the text the player reads on its buttons, without line breaks or colour tags, such as "Oak Long Bow" or "Soft leather: 1 gp". A product with no text is named by the item drawn over it, and failing that, by what follows the amount in its buttons' options. Matching is by part of the name, or of the item's name, without regard to case.

A `MakeProduct` has `name`, `item` (the item drawn over it, or `None`), `item_name`, and `amounts`, what its buttons make. These are counts, `MAKE_X` for the button that asks and `MAKE_ALL` for one that makes all. `button(amount)` gives that button's component, and `largest()` gives the one `make` uses.

`modals` is the main interface, such as the bank, a shop or the anvil:
- `main()` is its id, or -1, and `is_open()` says whether there is one;
- `close()` closes it and waits for it to go, and `close_if_open()` does so only when one is open.

## The bank

```python
opened = yield from banking.open()
if opened:
    yield from bank.deposit_all_matching(deposit_all_except(['Bronze pickaxe']))
    yield from bank.withdraw_x('Lobster', 10)
    yield from bank.close()
```

`bank` is the bank interface. Its items are `InvItem`s whose actions are the bank's options, "Withdraw 1" to "Withdraw X". The backpack items beside the bank have the deposit options. Options match without regard to case, and a hyphen counts as a space, so rs2b0t's `'Withdraw-1'` works too.

| Function | Returns or does |
|---|---|
| `is_open()`, `ready()` | The bank is open, and it is open with its items sent |
| `wait_ready(timeout_ms=4000)` | Waits for the items |
| `items()`, `side_items()` | The bank's items, and the backpack's beside it |
| `count(name)`, `count_by_id(id)` | How many of the item the bank holds |
| `withdraw(name, op='Withdraw 1')`, `withdraw_by_id(id, op='Withdraw 1')` | Uses the option once, without waiting |
| `withdraw_x(name, count)` | Withdraws `count`, or all there is. It uses Withdraw 1, 5 or 10 when one fits, and otherwise X and the count dialog. Then it waits for the items to land |
| `withdraw_x_by_id(id, count, lands_as_id=None)` | The same by id. In note mode the backpack gets the note, which has a different id; give that as `lands_as_id` |
| `withdraw_load(name)` | Fills the backpack: Withdraw All, or else X for the free slots |
| `set_note_mode(on)` | Withdraws as notes or as items. Opening the bank resets this to items |
| `deposit(name, op='Deposit 1')` | Uses the option once, without waiting |
| `deposit_inventory()` | Deposits everything |
| `deposit_all_matching(matches)` | Deposits each stack for which `matches(name, id)` holds, waiting for each to go |
| `open_nearest(booth_name='Bank booth', op='Use-quickly')` | Opens the nearest booth in the area, stepping beside it if a try from here fails, and continuing a dialogue that comes first |
| `open_booth(stand, booth_name='Bank booth', op='Use-quickly')` | The same, walking to `stand` if a try from here fails |
| `open_nearest_access(access)` | Opens a bank by its access: `{'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': ..., 'op': ...}}` |
| `open_npc_access(access)` | Opens a bank through a banker: `{'name': 'Banker', 'op': 'Bank', 'choose': None}`, where `choose` is the dialogue option to pick |
| `close(timeout_ms=3000)` | Closes the bank so the backpack's own options work again |

Each function that waits is a generator.

`banking` handles the trip:
- `open(stand=None, booth_name='Bank booth', booth_op='Use-quickly', destination=None, ...)` opens a booth in the area, or else a banker with a "Bank" option. Failing those, it walks to `stand` and opens the booth there, or walks to `destination` (one of `bank_locations()`) or else the nearest reachable known bank, and opens that.
- `bank_nearest(deposit, common_junk=True, return_to=None, after_deposit=None, ...)` opens a bank, deposits what `deposit(name)` picks plus common junk, runs `after_deposit()`, and walks back to `return_to`.

rs2b0t's deposit rules come with it:
- `deposit_all_except(keep)` deposits every named item except those in `keep`, matching the whole name without regard to case;
- `deposit_matcher(own, include_common)`;
- `matches_common_bank_loot(name, id=-1)`, which covers gems, strange fruit, beer, kebabs and the random-event casket (`COMMON_BANK_LOOT`, `RANDOM_EVENT_CASKET_ID`);
- `is_disposable_gather_junk(name, id=-1)`.

For banking every so often:
- `parse_bank_strategy(label)` and `should_bank_now(strategy, state)`;
- `PERIODIC_BANK_SETTINGS`, a schema to merge into a script's;
- `PeriodicBank(strategy, items_threshold, minutes_threshold, count_loot, deposit, ...)`, a `Task` that does it.

## Shops and trades

`shop` is a shop's interface. Nothing in it walks, so be near the keeper first. Names match whole, without regard to case.
- `is_open()`, and `open(npc_name)`, which trades with the nearest keeper of that name and waits for the shop.
- `stock()`: the shop's items, as `InvItem`s.
- `buy(name, n)` and `buy_by_id(id, n)` give how many they bought. They click 10s, then 5s, then 1s, five clicks a tick, because the engine runs no more than that, and wait for each batch to land.
- `sell(name, n, pick=None)` and `sell_all(name, pick=None)` give how many they sold. `pick(item)` chooses among stacks with that name, such as the noted one.
- `close()`.

2004 shows no prices; a shop only tells you one in a "Value" message.

`trade` is a trade with another player. Both players ask, then both accept the offer, then both confirm it. Moving or fighting closes the trade, so keep one task on it until it's done.
- `request(player_name)` asks the nearest player of that name to trade.
- `active()`, `on_offer_screen()` and `on_confirm_screen()`.
- `partner()` is the other player's name, from the offer screen's "Trading With:".
- `my_offer()` and `their_offer()` are `InvItem`s, on either screen.
- `status()` is the screen's own lines. `their_accepted()` says whether the other player has accepted, and `waiting()` whether you have and they haven't.
- `offer(item_name, n, pick=None)` offers `n`, never more, using Offer 1, 5 or 10 when one fits and Offer X otherwise, and waits for the items to show. `offer_all(item_name, pick=None)` offers the whole stack.
- `remove_all()` takes your offer back.
- `accept()` clicks Accept on whichever screen is open, and `decline()` declines and waits for the trade to close.

A trade request from another player comes as a `chat_message` event whose `type` is `'trade_request'`.

Neither looks for ids. A shop is the main interface's inventory that offers "Buy 1", beside a backpack that offers "Sell 1". The trade offer screen holds your offer, which offers "Remove", beside theirs. The confirm screen lists the two offers as text, with yours on the left.

## Interfaces

`interfaces` reads the game's interfaces as the player sees them: the cache's components, with what the server has set on them (text, colour, hiding, position) taking the cache's place. It's what the coming dialogue, bank, shop and trade facades are built on, and it reaches any interface they don't cover.

```python
interfaces.click_text('Accept')                      # the trade screen's Accept, wherever its button is
options = [c.text for c in interfaces.find(button='ok', root=reader.chat_modal())]
```

| Function | Returns or does |
|---|---|
| `component(id)` | A `Component`, or `None` for an id the cache doesn't have |
| `root(id)` | The interface's components, from its root down, in drawing order |
| `open()` | The ids of the open interfaces: the main, side and chat modals, the overlay, and each tab's |
| `tab(n)` | The interface in side tab `n`, 0 to 14, or -1 |
| `find(text=None, button=None, root=None)` | Visible components with that text (whole, without regard to case) and button type, where each is given, in the open interfaces or only in `root`'s |
| `click(id)` | Clicks the component as its button type says: `IF_BUTTON` for an Ok, Toggle or Select button, a resume for a Continue button, and closing the interface for a Close button. `False` when it isn't visible; a component that isn't such a button raises `ValueError` |
| `click_text(text, root=None)` | Clicks the button under the visible text, as a player clicking on the words would; trade's "Accept", for one, is a label over an unlabelled button. `False` when there's no such text, or no button under it |

A `Component` is a snapshot. Its fields:
- `id`, `root` (its interface) and `layer` (the layer it's in, or `None` for a root);
- `type`: `'layer'`, `'inv'`, `'rect'`, `'text'`, `'graphic'`, `'model'` or `'invtext'`;
- `button`: `None`, `'ok'`, `'target'`, `'close'`, `'toggle'`, `'select'` or `'continue'`, and `button_text`, its menu option;
- `text`, `colour`, `hidden` and `visible` (in an open interface, with nothing above it hidden);
- `options`: an inventory's five, `None` where empty;
- `target_verb` and `target_name`: a spell button's, such as "Cast on" and "Wind strike";
- `x` and `y` from its interface's corner, `width`, `height`, and `children` (ids);
- `item`: the object the server set it to show, such as a make menu's product or a strange box's shape, or `None`;
- `varp` and `value`: the varp a Select or Toggle button's condition reads and the value it compares with. That's what the button sets, such as varp 43, the combat mode, set to 1.

`component.click()` clicks it.

An item in an interface inventory moves with `item.move_to(slot)`, as rearranging the bank does.

## The side tabs

`quests` is the quest list:
- `all()` gives `Quest`s, each with `name`, `status` and `com` (the row's button);
- `status(name)` is `'not_started'`, `'in_progress'` or `'complete'`, read from the row's colour (red, yellow or green), or `'unknown'` when there's no such row;
- `points()` is the quest points;
- `journal(name)` opens the quest's journal and gives its lines. It's a generator.

The engine sends nothing more about a quest's progress.

`prayer` handles the prayers, named as `PRAYER_NAMES` has them, such as `'protect from melee'`:
- `points()`, `max()`, `full()`;
- `known(name)`, and `available(name)`, which means your level is high enough and you have points left;
- `active(name)`;
- `set(name, on)`, a generator that waits for the server to agree;
- `clear()`, which turns every prayer off.

A prayer's button is its place among the prayer tab's toggle buttons. Whether it's on is the varp that button reads.

`special` is the special attack:
- `energy()`, from 0 to 1000 (`SA_MAX_ENERGY`), and `armed()`;
- `wielded()`, the weapon's name;
- `cost(weapon_name)`, from rs2b0t's table, or `None`, and `ready(weapon_name)`;
- `bar_component()`, the combat tab's "Use Special Attack" bar, or -1 when the weapon has none;
- `arm()`, a generator. Arming is one-shot: the next attack spends it.

`game` also has the combat tab's styles:
- `combat_mode()` and `combat_styles()`. The styles are `(mode, label)` pairs such as `(1, '(Aggressive)')`: the Select buttons that set the combat mode, each with the label drawn level with it. So they follow whatever weapon is wielded.
- `set_combat_style(style)` and `has_combat_style(style)` take `'attack'`, `'strength'`, `'controlled'` or `'defence'`, or the labels' words, such as `'aggressive'`. A weapon without the style falls back to its last defensive one; `combat_style_resolution(style)` and `combat_style_mode(style)` say what that is. `set_combat_style` also takes a mode number, as does `set_combat_mode(mode)`. The ranged styles are modes, and `parse_range_style(name)` gives them.
- `auto_retaliate_on()` and `set_auto_retaliate(on)`.
- `attacked_by_player()`: you're in combat and facing a player.

And the spellbook, by name:
- `cast_on_npc(spell, npc)`, `cast_on_player(spell, player)`, `cast_on_loc(spell, loc)`, `cast_on_ground_item(spell, item)` and `cast_on_item(spell, item)`, such as `game.cast_on_item('High level alchemy', item)`. The spell is the magic tab's target button that names it. Each gives `False` when the spellbook has no such spell.
- `teleport(name)`, such as `game.teleport('Varrock')`, clicks the "Cast Varrock teleport" button. It returns once the click is sent, so check the arrival yourself.

`autocast` is a staff's autocasting:
- `armed()`;
- `staff_tab_attached()`, which is true when the combat tab is a staff's;
- `arm(spell, log=None)`, a generator that chooses the spell from `AUTOCAST_SPELLS` and turns autocasting on.

## Random events

While a script runs, the client answers random events for it. Once a server tick it asks `random_events` whether one needs answering. When one does, the bot's step in progress is dropped, the solver runs until it's done, and `loop()` starts afresh, as it does after a reconnect. `on_start` isn't interrupted.

| Event | What's done |
|---|---|
| The genie, drunken dwarf, mysterious old man, sandwich lady and frog | Talks to it and goes through the dialogue |
| A lamp in the backpack | Rubs it for `lamp_skill()`'s skill |
| A strange box in the backpack | Reads the question and clicks the part's colour or shape |
| The mime's stage | Copies each emote he performs, by his animation |
| The maze | Opens the doors on the route to the centre, which it reads from the cache's map, then touches the shrine |
| The strange plant | Picks its fruit while it can be picked |
| A hostile event (swarm, river troll, rock golem, zombie, shade, watchman, tree spirit) that has hit you | Runs 20 tiles away until it's gone, then walks back. It chases until you're 15 from where it appeared |
| The gas chest, smoking rocks and whirlpools | Steps away and waits a minute |
| An ent you're chopping | Steps off it |
| A tool whose head flew off | Picks the head up and fixes the tool, wielding it again if it was worn |
| Fishing gear knocked out of your hands | Picks it back up |

A script chooses with these, as module-level functions or methods on its bot:
- `ignored_randoms()`: event names to leave alone, such as `['drunken dwarf']`;
- `grind_targets()`: NPC names you fight on purpose, which are never taken for a hostile event;
- `lamp_skill()`: the skill the lamp's experience goes to, `'strength'` unless you say otherwise.

An event NPC that's following another player is left alone. An event that isn't over after 4 tries is ignored for 45 seconds, except the maze, the mime, a box and a lamp, which hold you or can't be dropped, so they're tried again. `"randomEvents": false` in the account file turns all of this off.

`random_events.detect()` gives the waiting event, with `kind` and `name`, or `None`; `yield from random_events.handle(event)` answers one. A script with the guardian off can call them itself.

## Catalogs and behaviours

rs2b0t's world catalogs, its planners and its reusable tasks are in `rs2004.catalogs`, which a script imports:

```python
from rs2004.catalogs import pickaxe_req, has_all_tools, resolve_mining_location, ContinueDialog

camp = resolve_mining_location('Use Closest', game.tile())
if not has_all_tools([pickaxe_req()], skills.level, inventory.count):
    ...
```

| Part | What's there |
|---|---|
| Tools | `PICKAXES` and `AXES` (best first, with their skill and Attack levels), `TINDERBOX` and the other tools, `pickaxe_req()`, `axe_req()`, `exact_tool(name)`, `best_pickaxe`, `best_axe`, `has_all_tools`, `tool_restock_plan`, `tools_needing_equip`, `best_held_tool_names` and the rest |
| Getting tools | Bob, Nurmof, Gerrant and Harry with their shop prices; `plan_gather_tool_acquire`, `plan_pickaxe_acquire`, `plan_axe_acquire` (buy at Bob's or smith from a bar), `plan_broken_tool_repair`, `plan_fishing_gear_buys`, `fishing_gear_shop_cart`, `can_fund_plan`, `acquire_keep_names`, and `walk_to_tool_vendor` (a wait, through Nurmof's trapdoor) |
| Fishing and mining | `FISHING_METHODS` with their gear, `spot_matches_method`, `fishing_restock_plan`; `ROCK_TYPES` by ore, `resolve_rock_ids`, `rock_tier_by_id`, `GAS_ROCK_IDS` |
| Gathering camps | `FISHING_LOCATIONS`, `MINING_LOCATIONS` and `WOODCUTTING_LOCATIONS`, with their options for a setting and resolvers (`'Use Closest'`, `'Auto'`, a name, or None for freeform); `booth_fields`; `pick_bucket_nearest` and `pick_nearest_prefer_local` for choosing a rock or tree |
| Other tables | Cow fields and the Al Kharid toll, runecrafting routes, pickpocket targets, herbs, walk destinations, cooking ranges and the cook location by each bank, fire spots and logs, and the shop database (`shop_db()`, `shops_selling(item)`) |
| Combat | Food heals and when to eat (`should_eat_food`, `should_hold_eat` and `AttackClock`, so a bite doesn't cost a swing), super and ranging potions (`planned_potions`, `potion_to_sip`), `combat_keep_names`, `bury_one_in_fight` |
| Loadouts | A script's `loadouts` setting (a list of `{name, worn, carry}`) and `loadout`, which names one: `selected_loadout`, `food_of`, `gear_of`, `weapon_of`, `supplies_of`, `script_food` |
| Trading partners | `parse_partner_list`, `is_configured_partner`, `decide_receiver_offer_screen`, `decide_giver_offer_screen`, `count_offer_by_name`, and the mule roles |
| Tasks | `ContinueDialog`, `DeathRecovery` (from the death event), `AcquireTask` with `ItemNeed`s from a shop or the ground, `create_return_to_anchor_task`, the leash helpers, and `sustain`. `PeriodicBank` is the bank's, and takes a `destination` too |

A table entry is a `Record`: its fields are attributes, and one it doesn't set reads as `None`. Item, NPC and scenery names are the 289 cache's, and a test checks every name the tables use against it. `reader.item_ids(name)`, `npc_ids(name)` and `loc_ids(name)` look a name up in the cache.

The data comes from rs2b0t through `tools/catalogs/export_rs2b0t.ts`, run with Bun against an rs2b0t checkout, which writes `rs2004/catalogs/_data.py` and `_shops.py`.

`scripts/examples` has three of rs2b0t's bots translated with them: `miner.py` (the mining side of GatheringBot), `cow_killer.py` (ChickenKiller's CowKiller, in melee) and `bank_fletcher.py` (BankFletcher, less its cut+string mode).

## Upkeep

Two of rs2b0t's runtime services run for every script, once a server tick, beside the random event guardian:

- **The run manager** turns run back on once energy reaches the account's `runEnergyMin` (20), when its `runAuto` is on (it is by default). It leaves run alone while a main interface is open, since clicking run makes the server close it, unless you're being hit, when any energy will do. `run_manager.override(run_auto=None, energy_min=None)` replaces the config's choices for this script; the last call wins as a whole, and one with neither goes back to the config's.
- **The stall guard** watches for progress: a change of tile, any experience, or `execution.note_progress()`. After the account's `stallMinutes` (10) without any, it walks back to the bot's `recovery_anchor()` (a module-level function or a bot method that gives a `Tile`) when that's more than 8 tiles away or on another level, and otherwise restarts the bot: `on_stop` with "the stall guard restarted the bot", then `BOT`'s `create()` makes a new one and `on_start` runs again. A module's globals stay as they were. It tries once, then not again for 15 minutes. Time the account spends logged out, and time a random event takes, isn't a stall. `stallMinutes: 0` turns it off.

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
| `death` | | Your hitpoints fell to 0. The server empties them before it says "Oh dear you are dead!" |
| `npc_say` | `npc`, `text` | An NPC said something over its head. `npc` is `None` if it has already left view |
| `projectile` | `projectile` | A projectile was launched in the loaded area: a `Projectile` with `spotanim`, `source()` and `destination()` (tiles), `target` (`('npc' or 'player', index)`, or `None` for one aimed at the ground), `start_delay` and `end_delay` (in the client's 20 ms cycles), `tick` and `targets_me()` |

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

- **`direct_navigator` stays in the loaded area.** A tile beyond it is walked to in a straight line. `traversal` walks anywhere.
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
- What rs2b0t has that's here so far: bots, `Execution`, settings, events, `Tile` and `Area`, the entity facades and their query, `Inventory`, `Equipment`, `InvItem`, `Skills`, `Game`, `DirectNavigator`, the web walker (`Traversal`, `WalkExecutor` and their crossings), `Reach`, `GameMessages`, `reader`, `ChatDialog`, `Modals`, `Bank`, `Banking` and its deposit rules, `PeriodicBank`, `Shop`, `Trade`, `Quests`, `Prayer`, `Special`, the combat styles, `Autocast`, the `RandomEventGuardian` with its solvers, the `RunManager`, the `StallGuard` with the supervisor's watchdog, and the catalogs and behaviours (`rs2004.catalogs`). [BotApiDesign.md](BotApiDesign.md) plans the rest, phase by phase.
- Differences:
    - a thing's `interact` walks to it first, as the webclient's does;
    - `npc.level` is its combat level, and every thing's level of the map is `thing.tile().level`;
    - `chat_message`'s `type` is a name (`'game'`, `'public'` and so on) rather than the webclient's number;
    - a setting that doesn't fit its schema is an error before login rather than quietly the default;
    - `match` is a Python keyword, so `chooseOption(match)` is `choose_option(text)`, and `make(match)` is `make(name)`;
    - `ChatDialog.continue()` is `chat_dialog.continue_()`.

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
| `walk_path_to(x, z)`, `walk_to(x, z)` | `yield from traversal.walk_resilient(Tile(x, z), 2)`, anywhere; `direct_navigator.walk((x, z))` for one click in the loaded area |
| `calculate_path_to(x, z)` | `direct_navigator.path((x, z))`, the waypoints, within the loaded area. `traversal` plans its own routes; there's no path object |
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
| `cast_on_self(spell)` | `game.teleport(name)` for a teleport, or `interfaces.click_text(...)` on the spellbook button |
| `cast_on_npc(spell, npc)` and the other casts | `game.cast_on_npc('Wind strike', npc)` and so on, by the spell's name |
| `is_bank_open()`, `deposit(id, amount)`, `withdraw(id, amount)` | `bank.is_open()`, `yield from bank.deposit_all_matching(...)`, `yield from bank.withdraw_x(name, amount)` |
| `is_option_menu()`, `answer(i)` | `chat_dialog.options()`, `yield from chat_dialog.choose_option(text)` |
| `get_quests()`, `is_prayer_enabled(p)`, `enable_prayer(p)` | `quests.all()`, `prayer.active(name)`, `yield from prayer.set(name, True)` |
| `get_combat_style()`, `set_combat_style(n)` | `game.combat_mode()`, `game.set_combat_style(style)` |
| `is_shop_open()`, `buy_shop_item(id, n)` | `shop.is_open()`, `yield from shop.buy_by_id(id, n)` |
| `is_trade_offer_screen()`, `accept_trade_offer()`, `is_recipient_trade_accepted()` | `trade.on_offer_screen()`, `trade.accept()`, `trade.their_accepted()` |
| `random(min, max)` | `random.randint(min, max)`, after `import random` |
| `set_autologin(False)` then `logout()` | `stop_account()` |
| `logout()` with autologin, `disconnect_for(s)` | `relog(s)` |
| `on_death()`, `on_npc_message(npc, msg)`, `on_npc_projectile(...)` | `on_death()`, `on_npc_say(npc, text)`, `on_projectile(projectile)` |
| `is_appearance_screen()`, `send_appearance_update(...)` | `game.appearance_screen_open()`, `game.set_appearance(female, kits, colours)` |

Fatigue, sleeping, the sleepword and raw packets don't exist.

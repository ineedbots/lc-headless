# Scripting API

How to write Python scripts that drive the headless client. A script is a `.py` file in the scripts folder; each account file names the script it runs. The design behind it is in [ScriptingDesign.md](ScriptingDesign.md).

## Quick start

1. Copy `accounts/example.jsonc.sample` to `accounts/<name>.jsonc` and fill in the username and password. The file name becomes the account's name in log lines.
2. Point `script.file` at a script, relative to `scripts/`, such as `examples/chicken_killer.py`.
3. Run `rs2004-headless client.jsonc` to run every enabled file in `accounts/`, logging them in `scripting.loginIntervalSeconds` apart, or add `--account accounts/<name>.jsonc` to run just that one. One process runs up to 16 scripted accounts.

An account file can have its own `server` section, with the same keys as `client.jsonc`'s, to log that account into a different world.

Ctrl+C asks each script to finish (see `on_kill_signal`). A second Ctrl+C logs every account out at once, and one more closes any connection whose logout the server is still refusing. The exit code is 0 when every account logged out cleanly and no script failed.

A dropped connection is restored automatically, with up to 10 attempts over about four minutes, so a server restart doesn't end a run. Each account reconnects on its own and the others keep playing. A first login is retried the same way when the server can't take it yet, for example "already logged in" after a crash.

A script needs one function, `loop()`, which returns how many milliseconds to wait before it's called again:

```python
CHICKEN = 41

def on_start():
    log('Starting at', get_x(), get_z())

def loop():
    if in_combat():
        return 600

    chicken = get_nearest_npc_by_id(CHICKEN, radius=8, in_combat=False)
    if chicken is not None:
        attack_npc(chicken)
        return 1200

    return 600

def on_server_message(msg):
    if msg.startswith('Oh dear'):
        stop_account()
```

`scripts/examples/` has complete scripts: `chicken_killer.py` fights, loots and logs out, and `walker.py` walks a loop of tiles, optionally for a set number of laps, telling a partner account about each one. Both make progress reports.

For working on a script, `--watch` reloads it whenever you save it, and `--debugger` lets VS Code debug it (see [Working on a script](#working-on-a-script)).

## How scripts run

- The module body runs once, before login. Use it for constants and settings. Game functions return empty values at that point, and actions fail, since there's no session yet.
- `on_start()` runs once the player is first placed in the world. After that, on every pass of the main loop the client:
  1. calls the hooks for everything that arrived since the last pass (events first, then chat messages, then messages from other scripts);
  2. calls `on_server_tick` if a tick passed;
  3. calls `on_progress_report` if a report is due;
  4. calls `loop()` if its delay is up.

  A game tick is 600 ms, so delays of 600 or more are typical; 0 means "as soon as possible".
- Everything runs on one thread, shared by every account in the process. Each call into the script may run for at most `scripting.callTimeoutMs` (1000 ms by default) before it's stopped with `TimeoutError`. `time.sleep()` raises an error: return a delay from `loop()` instead.
- `loop()` can be a generator instead, for a task that takes several steps. Each `yield` is a delay, as a return would be, and the generator carries on from there once it's up; `return 600` ends it and waits that long before `loop()` is called again, even before the first `yield`, and a bare `return` or reaching the end calls it again on the next pass. Hooks run as usual while it waits:

  ```python
  def loop():
      if in_combat():
          return 600
      walk_to(3222, 3218)
      yield 3000
      chicken = get_nearest_npc_by_id(CHICKEN, radius=8, in_combat=False)
      if chicken is not None:
          attack_npc(chicken)
          yield 1200
      while in_combat():
          yield 600
      return 1200
  ```

  Each resume is a separate call, so `scripting.callTimeoutMs` applies to each stretch between yields, not the whole generator. A reload with `--watch` starts it over.
- An uncaught exception, or a `loop()` that returns or yields anything but an int of 0 or more, stops the script. The client logs the traceback and logs the account out, unless it's running with `--watch`.
- Objects such as `Npc` are snapshots taken when the function returned. Keep the `index` to look one up again later with `get_npc(index)`.
- Actions queue packets and return at once; their effects show up in the state over the next ticks. Actions on a target that's no longer in view return `False`. A wrong argument type raises `TypeError`, and a value out of range (an option outside 1 to 5, say) raises `ValueError`.
- Names, options and scenery come from the server's cache, which the client loads at startup from `client.cacheDirectory`. They're exactly as the cache has them, case included.
- `log(*args)` writes at Info level and `debug(*args)` at Verbose level; `print()` also goes to the log. Each line carries the account's name.

### Settings

The account file's `script.settings` object becomes the global `settings`. Read its keys as attributes (`settings.loot_goal`), or with `settings.get('key', default)`; `'key' in settings` checks for one. Keys keep the spelling they have in the file.

### Imports

`import name` loads `scripts/name.py`, then `scripts/lib/name.py`; packages (folders with `__init__.py`) work too. pocketpy's own modules (`math`, `random`, `json`, `time`, `collections`, ...) are available. Nothing else is searched, and pip packages can't be used.

### Python dialect

Scripts run on pocketpy 2.2, a subset of Python 3. The differences you're likely to hit:

- `try` has no `finally` or `else`.
- Generator expressions don't exist; use list comprehensions.
- A class has at most one base class.
- Ints are 64-bit.
- In unpacking, a starred name must come last (`first, *rest = items`).
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

## Hooks

Define any of these to be told when something happens. Hooks that aren't defined cost nothing. A script that defines an `on_` function the client doesn't know about gets a warning when it loads, which catches typos.

| Hook | Called when |
|---|---|
| `on_start()` | Once, when the player is first placed after login |
| `on_server_tick(tick)` | A server tick passed |
| `on_server_message(msg)` | A game message arrived |
| `on_chat_message(msg, sender)`, `on_private_message(msg, sender)` | Public or private chat arrived |
| `on_trade_request(name)`, `on_duel_request(name)` | A player wants to trade or duel |
| `on_npc_spawned(npc)`, `on_npc_despawned(npc)` | An NPC came into view or left it. A despawned NPC is its last snapshot, so `npc.hp == 0` means it died |
| `on_npc_damaged(npc, damage)` | An NPC took a hit. `npc` is `None` if it has already left view |
| `on_player_spawned(player)`, `on_player_despawned(player)`, `on_player_damaged(player, damage)` | The same, for other players |
| `on_damaged(damage)` | You took a hit |
| `on_ground_item_spawned(item)`, `on_ground_item_despawned(item)`, `on_ground_item_changed(item, previous_count)` | An item appeared, went, or had its stack count changed |
| `on_loc_changed(loc)` | Scenery was added, changed or removed |
| `on_inventory_changed(com)`, `on_stat_changed(stat)`, `on_varp_changed(varp, value)` | An inventory, stat or player variable changed |
| `on_interface_changed()` | An interface opened or closed |
| `on_system_update(seconds)` | The server announced a restart |
| `on_disconnect()`, `on_reconnect()` | The connection dropped; it came back and the player is placed again. After a server restart the reconnect is a fresh login, so the state starts over, much as at login |
| `on_kill_signal()` | Ctrl+C was pressed. Call `stop_account()` once it's safe; after `scripting.killGraceSeconds` the account logs out anyway |
| `on_progress_report()` | A progress report is due; return a `dict` (see [Progress reports](#progress-reports)) |
| `on_bot_message(sender, message)` | Another script in this process sent this one a message (see [Messages between scripts](#messages-between-scripts)) |

Hooks only report what the server said. When the map rebuilds, or an area falls out of view, things vanish from the state without a despawn hook, so check what's in view rather than keeping your own copy.

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

`loop`, `settings` and `log` work the same way, and so do most hooks. The differences:

- `on_npc_damaged(npc, damage)` and `on_player_damaged(player, damage)` take the entity first. plutonium's take the damage first, so a ported hook gets its arguments swapped without any error.
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

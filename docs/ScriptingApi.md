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

`scripts/examples/` has complete scripts: `chicken_killer.py` fights, loots and logs out, and `walker.py` walks a loop of tiles, optionally for a set number of laps.

## How scripts run

- The module body runs once, before login. Use it for constants and settings. Game functions return empty values at that point, and actions fail, since there's no session yet.
- `on_start()` runs once the player is first placed in the world. After that, on every pass of the main loop the client:
  1. calls the hooks for everything that arrived since the last pass (events first, then chat messages);
  2. calls `on_server_tick` if a tick passed;
  3. calls `loop()` if its delay is up.

  A game tick is 600 ms, so delays of 600 or more are typical; 0 means "as soon as possible".
- Everything runs on one thread, shared by every account in the process. Each call into the script may run for at most `scripting.callTimeoutMs` (1000 ms by default) before it's stopped with `TimeoutError`. `time.sleep()` raises an error: return a delay from `loop()` instead.
- An uncaught exception, or a `loop()` that returns anything but an int of 0 or more, stops the script. The client logs the traceback and logs the account out.
- Objects such as `Npc` are snapshots taken when the function returned. Keep the `index` to look one up again later with `get_npc(index)`.
- Actions queue packets and return at once; their effects show up in the state over the next ticks. Actions on a target that's no longer in view return `False`. A wrong argument type raises `TypeError`, and a value out of range (an option outside 1 to 5, say) raises `ValueError`.
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
| `Npc` | `index`, `id` (NPC type), `x`, `z`, `level`, `animation` (-1 for none), `hp` and `max_hp` (`None` until a hit reveals them), `last_hit_tick`, `target` (`('npc' or 'player', index)` or `None`); methods `is_moving()` and `in_combat()` |
| `Player` | `index`, `name` (`None` until its appearance arrives), `combat_level`, then the same position, health, target and methods as `Npc` |
| `GroundItem` | `id`, `count`, `x`, `z`, `level` |
| `Loc` | `id` (-1 when the server removed the scenery), `x`, `z`, `level`, `shape`, `angle`, `layer` (a `LAYER_*` constant) |
| `Item` | `id`, `count`, `slot`, `com` (the inventory component, such as `INVENTORY`) |

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

### NPCs, players and the ground

`ids` takes one id, a list of ids, or `None` for any. `radius` limits the search to that many tiles from you, on your level.

| Function | Returns |
|---|---|
| `get_npcs(ids=None, radius=None)` | Every matching `Npc` in view, in the server's order |
| `get_nearest_npc_by_id(ids=None, radius=None, in_combat=None)` | The nearest matching `Npc` or `None`; `in_combat=False` skips NPCs being fought |
| `get_npc(index)` | The `Npc` with that index, if it's still in view |
| `get_players(radius=None)`, `get_player_by_name(name)` | Other players in view; one by name, or `None` |
| `get_ground_items(ids=None, radius=None)`, `get_nearest_ground_item_by_id(ids=None, radius=None)` | `GroundItem`s you can see |
| `get_loc_at(x, z, layer=None)` | The scenery at the tile, if the server has changed it (see Limits) |

### Inventories and interfaces

| Function | Returns |
|---|---|
| `get_inventory(com=INVENTORY)` | The `Item`s in an inventory's occupied slots; `BANK` and `EQUIPMENT` work too while the server sends them |
| `get_equipment()` | Your worn `Item`s |
| `get_inventory_count_by_id(ids, com=INVENTORY)` | The total count of matching items |
| `get_inventory_item_by_id(ids, com=INVENTORY)` | The first matching `Item`, or `None` |
| `get_empty_slots()`, `is_inventory_full()` | Free backpack slots out of `INVENTORY_SIZE` (28) |
| `get_main_modal()`, `get_side_modal()`, `get_chat_modal()` | The open interface ids, -1 for none; the bank is main modal 5292 |
| `is_interface_open(id)`, `is_count_dialog_open()` | Whether an interface or the "enter amount" dialog is open |
| `get_component_text(com)` | Text the server set on a component, or `None` |
| `get_varp(id)` | A player variable; for example `get_varp(173)` is 1 while running |
| `get_friends()`, `get_ignores()` | `[(name, world)]` and `[name]` |

### Actions

`op` is the option number, 1 to 5, in the order the right-click menu lists them.

| Function | Does |
|---|---|
| `walk_to(x, z, run=False)` | Walks to the tile in a straight line |
| `walk_path(points, run=False)` | Walks through up to 25 `(x, z)` waypoints, each leg in a straight line |
| `interact_npc(npc, op)`, `talk_to_npc(npc)`, `attack_npc(npc)` | Walks to the NPC and uses an option: talk-to is 1, attack is 2. `npc` is an `Npc` or its index |
| `interact_player(player, op)` | The same, for a player |
| `interact_loc(id, x, z, op)`, `interact_loc_via(points, id, x, z, op)` | Uses an option on scenery; `_via` walks waypoints there first |
| `interact_ground_item(item, op)`, `take_ground_item(item)` | Uses an option on a `GroundItem`; take is 3 |
| `item_op(item, op)`, `drop_item(item)` | Uses an option on an inventory `Item`; drop is 5 |
| `inv_button(item, op)` | Clicks an option on an item in an interface inventory, such as the bank's withdraw options |
| `move_item(com, from_slot, to_slot)` | Swaps two slots |
| `use_item_on_npc / _player / _loc / _ground_item / _item(item, target)` | Uses an `Item` on something; `_loc` takes `id, x, z` |
| `cast_on_npc / _player / _loc / _ground_item / _item(spell, target)` | Casts the spell whose spellbook button component is `spell` |
| `click_button(com)`, `continue_dialogue()`, `answer_count(value)`, `close_interfaces()` | Clicks an interface button; continues a "click here to continue" dialogue; answers an amount prompt; closes open interfaces |
| `set_run(run)` | Turns run mode on or off |
| `say(text)`, `send_pm(name, text)`, `command(text)` | Public chat, a private message, and `::command` for staff accounts (for example `command('tele 0,50,51,30,34')`) |
| `add_friend(name)`, `remove_friend(name)`, `add_ignore(name)`, `remove_ignore(name)` | Friends and ignore lists |
| `stop_script()` | Stops calling the script; the account stays logged in and idles |
| `stop_account()` | Stops the script and logs the account out |

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

Hooks only report what the server said. When the map rebuilds, or an area falls out of view, things vanish from the state without a despawn hook, so check what's in view rather than keeping your own copy.

## Constants

- **Inventories:** `INVENTORY`, `EQUIPMENT`, `BANK` and `BANK_INVENTORY` (your backpack while the bank is open), plus `INVENTORY_SIZE`.
- **Stats:** `ATTACK`, `DEFENCE`, `STRENGTH`, `HITPOINTS`, `RANGED`, `PRAYER`, `MAGIC`, `COOKING`, `WOODCUTTING`, `FLETCHING`, `FISHING`, `FIREMAKING`, `CRAFTING`, `SMITHING`, `MINING`, `HERBLORE`, `AGILITY`, `THIEVING`, `RUNECRAFT`.
- **Scenery layers:** `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`.
- **Combat:** `COMBAT_TICKS`.

## Limits

The client only knows what the server sends, with no game cache behind it, so:

- **No pathfinding.** The server walks each waypoint in a straight line and stops at the first obstacle. Interactions walk toward their target the same way, so an item behind a fence can't be taken. Pass waypoints around obstacles with `walk_path` or `interact_loc_via`, and give up on targets that don't respond (`chicken_killer.py` shows one way).
- **Scenery the server never changed is unknown.** Doors, trees and bank booths in their original state aren't in the state, so scripts supply the loc id and tile, for example `interact_loc(1530, 3218, 3218, 1)`.
- **Ids only.** NPCs and items have numbers, not names or option text. The engine's content (or a cache viewer) gives the ids.

## Editor support

`scripts/typings/__builtins__.pyi` declares everything above for Pylance and Pyright, and the repository's `pyrightconfig.json` points them at it. So opening either the repository or the `scripts` folder gives completion and type checks in scripts.

## Porting from plutonium

- `loop`, `settings`, `log` and the `on_*` hooks work the same way.
- `at_object(obj)` becomes `interact_loc(id, x, z, 1)`, with the id and tile written into the script.
- `walk_path_to`, `is_reachable` and `calculate_path_to` have no equivalent yet.
- Fatigue, sleeping, the option menu and other RSC-only calls don't exist.

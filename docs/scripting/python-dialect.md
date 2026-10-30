# Python, imports, tools and porting

## The Python dialect

Scripts run on pocketpy 2.2, a subset of Python 3. Most everyday Python works; these differences are the ones scripts hit.

### Syntax

- `match` is a keyword, so it can't name a variable or parameter. Where rs2b0t's functions take `match`, these take `text` or `name`.
- `try` has no `finally` and no `else`.
- Generator expressions don't exist: write `any([x for x in xs])`, not `any(x for x in xs)`.
- `yield from` may only be a statement, or the right side of an assignment. Not `if (yield from wait()):`; write `ok = yield from wait()` then `if ok:`.
- In unpacking, a starred name must come last (`first, *rest = items`), and only lists and tuples unpack.
- Strings side by side aren't joined, f-strings included: `'a' 'b'` is an error. Join them with `+`.
- A parenthesised import can't have a trailing comma.
- Avoid chained comparisons such as `a < b < c`; write `a < b and b < c`.

### Functions and classes

- A parameter can be passed by keyword only when it has a default value, and a default must be a literal: `timeout=6000`, not `timeout=TIMEOUT`.
- A function can read the variables of the function it's defined in, but not of one further out. A lambda inside a nested function that uses the outer function's variable fails, or quietly gets a builtin of the same name, such as `id` or `min`. Copy the value into a local of the nested function first.
- Classes must be defined at module level, not inside a function.
- A class has at most one base class.
- A class that defines `__eq__` must define `__ne__` too.
- An attribute set on an instance doesn't replace a method of its class. Give the instance a differently named attribute and call it from the method (as [`Task`](script-structure.md#taskbot-and-task) does).

### Types and the library

- Ints are 64-bit, and `bool` isn't a kind of `int`.
- Tuples can't be added together.
- `dict(another_dict)` doesn't copy; use `{k: v for k, v in d.items()}`. `dict.setdefault`, `str.isdigit` and `str.capitalize` don't exist.
- `x in range(...)` doesn't work; compare the bounds.
- There's no `re` module.
- `time.sleep()` raises `RuntimeError`. Wait with [`execution`](waiting.md).
- Sets, dict ordering, `**kwargs`, `isinstance(x, (A, B))` and f-strings do work.

## Imports

`import name` looks, in order:

1. The client's standard library, the `rs2004` package. Its public names are already builtins, so scripts don't import it, except for [`rs2004.catalogs`](catalogs.md).
2. `scripts/name.py`, then `scripts/lib/name.py`. Packages (folders with `__init__.py`) work too.
3. pocketpy's own modules: `math`, `random`, `json`, `time`, `collections` and so on.

Nothing else is searched, and pip packages can't be used.

```python
import random
from rs2004.catalogs import FOOD_OPTIONS
import my_helpers           # scripts/my_helpers.py or scripts/lib/my_helpers.py
```

## Working on a script

### Reloading on save

```
rs2004-headless client.jsonc --account accounts/<name>.jsonc --watch
```

`--watch` reloads the script whenever you save it, or a module it imports, without logging out. The new code starts fresh: new globals, `on_start()` again, and events from before the save skipped (queued bot messages are kept). If a save breaks the script, or it fails later, the account stays logged in and idle until the next save. A script that cannot load at startup still stops the run before any login. A change to the account file needs a restart.

### Debugging in VS Code

`--debugger` lets VS Code debug one account's script, with breakpoints, stepping, variables and a debug console that can call the API.

1. Install VS Code's pocketpy extension (`pocketpy.pocketpy`).
2. Add to `.vscode/launch.json`:

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

3. Run `rs2004-headless client.jsonc --account accounts/<name>.jsonc --debugger`, then start the configuration. The account logs in once the debugger attaches.

While paused, the whole process is paused and the server hears nothing, so a long pause may end in a reconnect. `scripting.callTimeoutMs` doesn't apply under the debugger. Breakpoints work in `scripts/` but not `scripts/lib/`. `sourceFolder` must point at the scripts directory or breakpoints are not hit. An uncaught exception stops in the debugger. Stopping the debug session ends the process immediately without logging out; press Ctrl+C in the client first for a clean logout. `--debugger` needs `--account` and can't be combined with `--watch` or `--profile`.

### Script profiling

Use `--profile` to record Python line timings, optionally with `--watch`. See [Script profiling](../Running.md#script-profiling) for report paths, source snapshots, viewing reports and timing limitations.

### Editor support

`scripts/typings/__builtins__.pyi` and `scripts/typings/rs2004/catalogs/__init__.pyi` declare the API for Pylance and Pyright, and the repository's `pyrightconfig.json` points them there. Opening the repository or the `scripts` folder gives completion and type checks.

## Revisions

`game.revision()` gives the server's revision. Branch on it where content differs.

- **289** is what the catalogs and walker data were built from.
- **274** plays as 289, but anything added after 274 doesn't exist, and some map squares differ, so a few walker routes cross scenery 274 doesn't have. It supports membership, server-provided player options and drag-insert. Public chat has only the wave and scroll effects, as on 225.
- **225** doesn't say whether the world is members, so `traversal` plans as on a free world. Its player menu is fixed (`Duel-with`, `Attack`, `Follow`, `Trade with`); player option 5 raises `ValueError`. Ids added after 225 don't exist.

## Porting from rs2b0t

The API is rs2b0t's, in Python's style, so a bot translates mostly line by line.

| rs2b0t quest module | Python module |
|---|---|
| `api/ai/quests/defs/druidicritual.ts` | `rs2004.quests.defs.druidicritual` |
| `api/ai/quests/defs/monksfriend.ts` | `rs2004.quests.defs.monksfriend` |

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

- Facades are lower case (`Npcs` is `npcs`, `GroundItems` is `ground_items`) and camelCase becomes snake_case. A name that's a Python keyword gains a trailing underscore: `ChatDialog.continue()` is `chat_dialog.continue_()`.
- A thing's `interact` walks to it first, as the game's client does.
- `npc.level` is its combat level; a thing's floor is `thing.tile().level`.
- `chat_message`'s `type` is a name (`'game'`, `'public'` and so on), not the webclient's number.
- A setting that doesn't fit its schema is an error before login rather than quietly the default.
- `chooseOption(match)` is `choose_option(text)`, and `make(match)` is `make(name)`.

The ported API includes bots, `Execution`, settings, events, `Tile` and `Area`, the entity facades and their query, `Inventory`, `Equipment`, `InvItem`, `Skills`, `Game`, `DirectNavigator`, the web walker (`Traversal`, `WalkExecutor` and their crossings), `Reach`, `GameMessages`, `reader`, `ChatDialog`, `Modals`, `Bank`, `Banking` and its deposit rules, `PeriodicBank`, `Shop`, `Trade`, `Quests`, `Prayer`, `Special`, the combat styles, `Autocast`, the `RandomEventGuardian` with its solvers, the `RunManager`, the `StallGuard` with the supervisor's watchdog, `RecoveryHints`, `EventSignal`, `SettingsStore` with the `Global` settings, `ScriptActivity`, the catalogs and behaviours (`rs2004.catalogs`), the clue engine (`rs2004.clues`), and the quest engine with its first quests (`rs2004.quests`). [BotApiParityDesign.md](../design/BotApiParityDesign.md) plans the rest, phase by phase. See the [ported bot table](catalogs.md#ported-bots) for script filenames.

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

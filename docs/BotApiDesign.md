# Bot API Design

Plan for a script API with the abilities of rs2b0t's bot API, written the way Python is: rs2b0t's facades, query builder, bot classes, world walker, random-event guardian and catalogs, with snake_case names, and generators where rs2b0t awaits. The client hasn't been released, so this replaces today's flat API ([ScriptingApi.md](ScriptingApi.md)) outright; nothing keeps the old names. plutonium-rsc's abilities are a subset of rs2b0t's, and its scripts port through a table in ScriptingApi.md. rs2b0t's quest and clue engines are left for a later project. The work comes in nine phases after a docs fix (§14). Code style follows [CONVENTIONS.md](CONVENTIONS.md). It extends the interface decoding in [CacheDesign.md](CacheDesign.md) §6, the paths in CacheDesign §10–11, and the runtime, events and API in [ScriptingDesign.md](ScriptingDesign.md) §3–6, whose naming rule it replaces.

Reference sources:

- `rs2b0t/packages/rs2b0t-api/index.d.ts`: the public API, every facade, class and catalog this design mirrors
- `rs2b0t/docs/reference/api-*.md`: what each facade does, and its gotchas
- `rs2b0t/src/bot/api/`: the facades' implementations, and the reusable behaviours bundled bots share (`tasks/`, `sustain/`, `combat/`, `loadout/`, `walking/Reach.ts`)
- `rs2b0t/src/bot/event/webwalk/` and `docs/reference/nav-*.md`, `transports-2004.md`: the world walker, and its data in `webwalk/data/` (`doors.json`, `stairEdges.json`, `transports.json`, `specialCrossings.ts`, `dangerZones.ts`), `travelCatalog.ts` and `teleportCatalog.ts`
- `rs2b0t/src/bot/runtime/`: `randomevents/` (the guardian and its solvers), `StallGuard.ts`, `RunManager.ts`, `Settings.ts`, `defineBot.ts`
- `rs2b0t/src/bot/data/`: the catalogs
- `rs2b0t/LICENSE`: MIT. Ported code and data keep its notice (§2)
- `plutonium-rsc/script.go`: plutonium's names, for its porting table
- `289server/webclient/src/config/IfType.ts` and `client/Client.ts` (`addComponentOptions`): the interface format, default button texts, and which button a click hits
- `289server/content/scripts/`: the interfaces and scripts each helper drives, named where they're used below; `macro events/` for the random events
- pocketpy 2.2.0 `src/compiler/compiler.c` (`compile_yield_from`) and `src/interpreter/generator.c`: `yield from` evaluates to the inner generator's return value, and generators have `__next__` only, no `send`, `throw` or `close`

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Shape | rs2b0t's: facades named after game nouns (`npcs`, `inventory`, `bank`, `chat_dialog`, `traversal`), a chainable `query()` for entities, and entities with methods (`npc.interact('Attack')`, `item.use_on(range)`). An rs2b0t bot translates to Python mostly by renaming (§3) |
| Names | camelCase becomes snake_case. A facade object is lower-case (`Npcs` is `npcs`, `ChatDialog` is `chat_dialog`, `GroundItems` is `ground_items`); classes keep CapWords (`Tile`, `LoopingBot`). A name that's a Python keyword gains a trailing underscore, as PEP 8 suggests (`chat_dialog.continue_()`) |
| Waiting | Where rs2b0t `await`s, a script writes `yield from`. A call that waits is a generator, and its result is the generator's return value: `ok = yield from bank.withdraw_x('Feather', 100)`. pocketpy has no `send`, so results come back by `return` only |
| Two layers | A C++ core (`ScriptApi`, bound as the private `_core` module) holds the state, fast searches, the interface model, packets and path search. A Python standard library, embedded in the executable, holds the facades, waits, bots, walker, random-event solvers and catalogs. Those are mostly sequencing (open, wait, check, retry), which reads best as generators and ports from rs2b0t's TypeScript line by line. This replaces ScriptingDesign §2's rule that all game logic is C++ |
| Bots | rs2b0t's `LoopingBot`, `TaskBot` and `TreeBot`. A script that only defines `loop()` and hooks is a `LoopingBot` |
| Settings | rs2b0t's typed schema. A script declares types, defaults, ranges and options, and the account file's settings are checked against it before login |
| Events | rs2b0t's event bus (`events.on`, `bot.on`), with its events and ours under one set of names. A hook is a bot method or module function named `on_<event>` |
| Walking | rs2b0t's walker: A* over the cache's collision plus a graph of doors, stairs, ladders, ships and other transports from rs2b0t's data, across levels, with requirements, special crossings, stuck recovery and optional teleports |
| Random events | rs2b0t's guardian and solvers, run by the host between bot steps |
| Catalogs | rs2b0t's data tables and planners, and its shared script behaviours, as stdlib modules |
| Interface ids | Found in the cache by what it says about them, as `CacheLoader` finds the bank and the run buttons (CacheDesign §6). Nothing is tied to the 289 content's numbering |
| Not ported | What a headless client has no use for: paint and the HUD, the camera, the bot panel and its map picker, the multibox wall, scene-build and render state, and browser artifacts such as bank snapshot generations. Also rs2b0t's quest and clue engines and its market price books, for now |

Rejected:

- **Flat functions** (today's `get_nearest_npc`, `interact_npc`) or keyword filters (`npcs.nearest(name=..., within=3)`). Either reads fine in Python, but rs2b0t's 52 bots and its manual would then need rethinking rather than translating.
- **async/await.** pocketpy has no event loop, and generators with `yield from` already give the same shape.
- **The whole library in C++.** The walker's executor, the solvers and the bank flows are long chains of wait-and-check steps. In C++ each would be a state machine; in Python each is a function, close to rs2b0t's.
- **Python files in `scripts/lib`** for the library. It would version separately from the client it needs. Embedding keeps the two in step.
- **Baking rs2b0t's collision pack.** It's built from an engine's map files; this client already reads the same collision from the cache.

---

## 2. Layers and layout

```
src/
├── Script/
│   ├── ScriptApi.hpp/.cpp      the core: state, searches, interfaces, packets, path search (bound as _core)
│   ├── ScriptBindings.cpp      binds _core and loads the stdlib into builtins; the prelude shrinks phase by phase
│   ├── ScriptHost.cpp          drives a bot: steps, waits, events, the random-event guardian, stall guard
│   ├── Stdlib.hpp/.cpp         finds an embedded stdlib file by path
│   └── Stdlib/rs2004/          the Python standard library, embedded at build time
│       ├── _runtime.py         the host's side: loading the bot, its steps, events and end
│       ├── bot.py              AbstractBot, LoopingBot, Task, TaskBot, TreeBot, define_bot
│       ├── settings.py         SettingDef, SettingsBag, schema checks
│       ├── events.py           the event bus, payloads, the names the host checks
│       ├── execution.py        delays and waits
│       ├── geometry.py         Tile, Area
│       ├── entities.py         Npc, Player, Loc, GroundItem, EntityQuery, npcs, players, locs, ground_items
│       ├── items.py            InvItem, inventory, equipment
│       ├── game.py             game, skills, reader, chat, friends, ignores, direct_navigator; later prayer, special, magic
│       ├── bank.py             bank, banking, deposit matchers
│       ├── ui.py               chat_dialog, shop, trade, quests, interfaces
│       ├── walking/            traversal, reach, the executor and crossings
│       ├── randomevents/       the guardian and solvers
│       └── catalogs/           data tables, planners and behaviours (§12)
├── Game/
│   ├── InterfaceView.hpp/.cpp  the cache's components merged with what the server set (§6)
│   └── Map/
│       ├── CollisionMap.hpp/.cpp   size becomes a constructor argument
│       ├── SquareCollision.hpp/.cpp  a square's collision, shared by WorldMap and WalkMap
│       ├── WalkMap.hpp/.cpp        the whole world's walkable directions, built once from the cache (§9)
│       ├── NavGraph.hpp/.cpp       doors, stairs, transports and teleports from data/nav (§9)
│       └── WorldPathFinder.hpp/.cpp  A* over WalkMap and NavGraph (§9)
cmake/EmbedStdlib.cmake         turns Stdlib/**/*.py into a generated source of byte arrays
data/nav/                       rs2b0t's walker data, with its license (§9)
third_party/rs2b0t/LICENSE      rs2b0t's MIT notice, for the ported code and data
tools/nav/convert_rs2b0t.py     one-off: rs2b0t's TypeScript data tables to JSON
scripts/typings/                the stubs, for the whole library
scripts/examples/               rewritten bots (§14)
tests/Stdlib/                   Python tests, run in a VM by tests/Script/StdlibTests.cpp (§13)
```

- **The core** keeps today's `ScriptApi` and grows with each phase. Its bindings move, phase by phase, into one private builtin module, `_core`, which only the stdlib imports. Scripts never see it. Phase 1 put the runtime's needs there (`step_time`, `tick`, `note_progress`); the flat API stays in builtins until phase 2 replaces it.
- **The stdlib** is the `rs2004` package in `src/Script/Stdlib/`. `cmake/EmbedStdlib.cmake` embeds each file as a byte array, since MSVC limits a string literal to 64 KB, and regenerates them when a `.py` file changes. The import callback resolves `rs2004` before `scripts/` and `scripts/lib/`, so a script can't shadow it, and its files aren't watched with the script's. A failure in the stdlib carries its own file and line, as a script's does.
- **Builtins.** At startup each VM imports the stdlib's public modules and puts their names in `builtins`, as the API is today, so scripts need no imports. Catalogs, which have hundreds of names, stay in their module: `from rs2004.catalogs import nearest_bank`.
- **Ported code** keeps rs2b0t's MIT notice. Each ported module names the rs2b0t file it came from, which is also where a reader goes to compare behaviour.
- **pocketpy's dialect** constrains the stdlib as it does scripts (ScriptingApi.md, Python dialect). The ones that shaped phase 1:
    - a parameter takes a keyword only when it has a default, so every parameter a script might name has one (`define_bot(name=None, create=None, ...)`, `SettingDef(type=None, default=None, ...)`);
    - a default must be a literal;
    - an instance attribute doesn't override a class's method, so `Task` keeps its callables as `_validate` and `_execute`;
    - generators have only `__next__`, so the runtime drives them with `next` and reads a return value from `StopIteration.value`.

---

## 3. Translating an rs2b0t bot

| TypeScript | Python |
|---|---|
| `class Miner extends LoopingBot { loop() {...} }` | `class Miner(LoopingBot): def loop(self): ...` |
| `await Execution.delayUntil(() => Inventory.isFull(), 3000)` | `yield from execution.delay_until(lambda: inventory.is_full(), 3000)` |
| `Npcs.query().name('Guard').within(3).nearest()` | `npcs.query().name('Guard').within(3).nearest()` |
| `await item.interact('Bury')` | `item.interact('Bury')`, or `yield from` when the call waits (§5) |
| `this.settings.str('rock', 'Copper rocks')` | `self.settings.str('rock', 'Copper rocks')` |
| `this.on('skill.xp', e => ...)` | `self.on('skill_xp', lambda e: ...)` |
| `Game.tile()?.x` | `t = game.tile()`, then `t.x if t else None` |
| `export default defineBot({...})` | `BOT = define_bot(...)` |

The stubs in `scripts/typings` mark every generator `-> Generator[..., None, T]`, so Pylance shows where `yield from` is needed.

---

## 4. Phase 1: the runtime (done)

### Steps and waits

The host steps the bot through `_runtime.step()`, which runs `loop()`, or resumes the generator it returned, until it waits, and hands back how:

| Step result | The host steps it again |
|---|---|
| `('ms', n)` | After `n` milliseconds |
| `('update', n)` | After the next pump that decoded a packet (`GameState_s::updateCount` moved), or after `n` milliseconds when `n` ≥ 0, whichever is first |
| `('ticks', n)` | Once the server tick has moved on `n`, or started over with a fresh login |

What `loop()` returns is read as rs2b0t's `resolveLoopCadence` reads it: 0 is the next pass, 600 the next server tick, and anything else milliseconds. `None` uses the bot's `loop_delay` (600) or its `loop_cadence` (`{'kind': 'frame'}`, `{'kind': 'server_tick', 'ticks': n}` or `{'kind': 'time', 'ms': n}`). What a generator yields isn't resolved that way: an `int` is milliseconds, and the waits yield `execution.Update(timeout_ms)` and `execution.Ticks(n)`.

`execution` mirrors rs2b0t's `Execution`:

| Function | Returns |
|---|---|
| `delay(ms)`, `delay_ticks(n)` | Nothing, once the time has passed |
| `delay_until(cond, timeout_ms=6000)` | `True` as soon as `cond()` holds, checked now and after each update; `False` at the timeout |
| `delay_until_ticks(cond, max_ticks)` | The same, checked once a tick |
| `note_progress()` | Tells the stall guard (§11) about work it can't see |

Waits measure time from the host's step time (`ScriptApi::SetStepTime`, `_core.step_time()`), so a test that steps the host with made-up times controls them. Each resume is a separate call into Python, so `scripting.callTimeoutMs` bounds each stretch between yields, as before.

### Bots

| Class | Does |
|---|---|
| `AbstractBot` | `loop_delay`, `loop_cadence`, `settings`, `log(*args)`, `on(event, cb)`, `request_finish(reason)`, `grind_targets()`, `ignored_randoms()`, and the hooks a subclass defines |
| `LoopingBot` | `loop()` returns a delay, or `None`, or is a generator |
| `TaskBot` | `add(*tasks)` in `on_start`, highest priority first. Each step runs the `execute()` of the first task whose `validate()` holds; either may be a generator. `Task(validate, execute, label)` makes one of two callables |
| `TreeBot` | `root()` returns a `BranchTask` (`validate()`, `success()`, `failure()`) or a `LeafTask` (`execute()`); each step walks the tree to a leaf and runs it |

- A script sets `BOT = define_bot(name=..., create=Miner, description=None, version=None, category=None, tags=None, settings_schema=None)`. Without `BOT`, its module-level `loop()`, `on_*` functions and `SETTINGS_SCHEMA` act as a `LoopingBot`. A script with neither `BOT` nor `loop()` fails before login.
- An `on_start()` that's a generator runs as the bot's first step, and `loop()` follows on the next pass.
- `on_stop(reason)` runs once: after `stop_script()`, `stop_account()`, `request_finish(reason)` (whose reason wins) or a script error, and when `Account` logs out or fails for a reason of its own, such as Ctrl+C (`ScriptHost::Finish`). Then `script_finish` fires and the bot's subscriptions end. It can't wait.
- rs2b0t's `on_pause` and `on_resume` have nothing to call them headlessly, and `on_paint` gives way to progress reports, which stay as they are.

### Settings

`settings_schema` maps each key to a `SettingDef(type, default, label=None, min=None, max=None, help=None, options=None, option_labels=None, group=None)`. The type is `'boolean'`, `'number'`, `'string'`, `'string[]'` or `'tile'`, as rs2b0t's.

- At load, the account file's `script.settings` is checked against the schema. A wrong type, a number out of range, or a value not in `options` fails that account before login, naming the key, where rs2b0t quietly falls back to the default. Missing keys take their defaults, and keys the schema doesn't know draw a warning.
- `self.settings` is a `SettingsBag` with rs2b0t's getters (`bool`, `num`, `str`, `list`, `tile`, `raw`), and keeps attribute access (`settings.rock`).

### Events

Every event has one name, used by `events.on(name, cb)`, `bot.on(name, cb)` (removed when the bot stops) and the `on_<name>` hook. rs2b0t's events pass one payload, an `Event` with its fields as attributes; the others pass their values, as hooks did before:

| Event | Passes | From |
|---|---|---|
| `tick` | `Event`: tick | rs2b0t; was `on_server_tick(tick)` |
| `chat_message` | `Event`: type (`'game'`, `'public'`, `'private'`, `'trade_request'`, `'duel_request'`), username, text | rs2b0t's `ChatLine`, with names where it has the webclient's type numbers; was `on_chat_message(msg, sender)` |
| `skill_xp` | `Event`: skill, name, xp, delta | rs2b0t; with `skill_level`, replaces `on_stat_changed(stat)` |
| `skill_level` | `Event`: skill, name, level, previous | rs2b0t |
| `inventory_changed` | `Event`: slot, id, name, count, previous_id, previous_count | rs2b0t: the backpack, one event per changed slot; was `on_inventory_changed(com)` for any inventory |
| `varp_changed` | `Event`: index, value, previous | rs2b0t |
| `script_finish` | `Event`: reason | rs2b0t, though there it's how a bot asks to stop; here `request_finish` does that |
| `server_message`, `private_message`, `trade_request`, `duel_request` | values, the sender first | before |
| `npc_spawned`, `npc_despawned`, `npc_damaged`, `player_spawned`, `player_despawned`, `player_damaged`, `damaged`, `ground_item_spawned`, `ground_item_despawned`, `ground_item_changed`, `loc_changed`, `interface_changed`, `system_update`, `disconnect`, `reconnect`, `kill_signal`, `bot_message` | values | before |

`start`, `stop` and `progress_report` are hooks without subscribers. `death`, `npc_say` and `projectile` come in phase 8 (§11). Callbacks run between steps and can't wait, as rs2b0t's fire mid-frame: they set flags, and `loop()` does the work.

The host skips an event nobody listens to before converting anything: the stdlib keeps `_listening`, the names with a hook or subscriber, and the host reads it in place. Another account's `send_bot_message` reads it from inside its own VM, so the read puts the caller's VM back.

### Geometry

`Tile(x, z, level=0)` with `distance_to` (Chebyshev, plus 1,000,000 across levels, as rs2b0t's), `translate`, `equals`, `==`, and `Tile.from_tile(t)`. `Area.rectangular(a, b)`, `Area.circular(center, radius)` and `Area.polygon(points, level=0)` (plutonium's), with `contains(tile)` and `get_random_tile()`. An area holds tiles on one level.

### Done when

- [x] `tests/Stdlib` runs, and covers the waits, the three bot classes, settings checks and the events' arguments.
- [x] The examples are rewritten (`chicken_killer.py` as a `TaskBot` with a settings schema; `walker.py` stays the minimal module-level bot) and run against the local engine: the chicken killer fought, looted with `delay_until` confirming each pickup, reported progress and logged out at its goal.
- [x] `delay_until` resumes on the pump after the state changes, not on the next poll (`ScriptHostTests`).

---

## 5. Phase 2: entities, items and the game (done)

Every flat function moved into `_core`, and the facades below sit on it, in `rs2004/entities.py`, `items.py` and `game.py`. Calls that only send a packet return a bool at once; calls that wait for the outcome are generators.

| Facade | Python | Notes |
|---|---|---|
| `npcs`, `players`, `locs`, `ground_items` | `query()`; `npcs.all()`, `npcs.nearest(count=1)`; `players.all()` | Ours: `npcs.get(index)`, `players.local()` and `locs.at(tile, layer=None)` |
| `EntityQuery` | `name(*names)`, `action(action)`, `within(dist)`, `within_of(origin, dist)`, `inside(area)`, `where(pred)`, then `results()`, `nearest()`, `nearest_prefer_local(prefer_radius)`, `first()`, `exists()`, `count()` | Ours: `id(*ids)`, `layer(layer)` and `reachable()`. Names, ids, `within`'s radius and the layer go to the core's search (`SearchFilter_s`, which gained names for every kind); the other filters run in Python on the results. `inside` takes an `Area` or rs2b0t's `{minX, ...}` |
| `Npc` | `name`, `id`, `level`, `index`, `size`, `in_combat`, `health`; `tile()`, `network_tile()`, `distance()`, `actions()`, `valid()`, `targets_me()`, `targets_another_player()`, `interact(action)` | Also `max_health`, `animation`, `moving` and `target`. `level` is the combat level, as rs2b0t's |
| `Player` | `name`, `index`, `in_combat`, `combat_level`; `tile()`, `distance()`, `actions()`, `targets_me()`, `interact(action)`, `valid()` | `actions()` are the options the server set (`ScriptApi::GetPlayerMenu`) |
| `Loc`, `GroundItem` | `name`, `id` (and `count`); `tile()`, `distance()`, `actions()`, `interact(action)`, `valid()` | `Loc` also has `shape`, `angle`, `layer`, `changed` and `interact_via(points, action)` |
| `inventory` | `items()`, `first(name)`, `contains(name)`, `count(name)`, `count_by_id(id)`, `used()`, `free()`, `is_full()` | They read the backpack itself, which the server keeps sending while the bank is open; rs2b0t reads the bank's side panel because the webclient hides the backpack then |
| `InvItem` | `name`, `id`, `slot`, `count`, `noted`; `actions()`, `interact(action)`, `use_on(target)` | Also `com`. `use_on` takes an `InvItem`, `Loc`, `Npc`, `Player` or `GroundItem` |
| `equipment` | `items()`, `contains(name)`, `equip(name)`, `unequip(name)` | `equip` and `unequip` are generators that wait for the item to move |
| `skills` | `index(name)`, `level(name)`, `effective(name)`, `xp(name)`, `hp_fraction()` | Names are lower-case, as rs2b0t's; an unknown one raises `ValueError` |
| `game` | `ingame()`, `tile()`, `energy()`, `run_enabled()`, `set_run(on)`, `weight()`, `in_combat()`, `animating()`, `tick()`, `my_name()` | Also `moving()` and `combat_level()`. `ingame()` covers rs2b0t's `scene_ready()` too: the player is placed |
| `direct_navigator` | `walk(dest)`, `walk_to(dest, radius=2, timeout_ms=45000)` | rs2b0t's same-scene walking, moved here from phase 6 because scripts need to walk meanwhile. Also `walk_path(points)`, `reachable(dest)`, `path(dest)` and `destination()` |
| `reader` | `varp(id)` and the other raw reads | Here too: the modal ids, component text, the count dialog, any inventory by component, and the cache's types |

How the objects are built:
- `PyConvert` builds them as instances of the stdlib's classes, found in builtins by name, as it built the prelude's.
- A thing's tile is kept in private `_x`, `_z` and `_plane` fields, which `tile()` reads. A public `level` would clash with rs2b0t's `npc.level`.
- Its menu is a private `_ops` list, from `ScriptApi::GetNpcMenu`, `GetLocMenu`, `GetGroundItemMenu` and `GetItemMenu`, which add the "Take" and "Drop" the menu shows.
- `interact(action)` matches the text against `_ops` and returns `False` without sending when it isn't there, as rs2b0t's `interact` does; the core's text matching, which raised `ValueError`, stays for `_core` callers.
- Reachability for `reachable()` is `ScriptApi::CanReachEntity`, `CanReachGroundItem` and `CanReachLoc`.

Kept from before because rs2b0t has nothing public for them:
- `chat.say(text)`, `chat.send_pm(name, text)` and `chat.command(text)`;
- `friends` and `ignores`, with `list()`, `add(name)` and `remove(name)`;
- `send_bot_message`, `stop_script`, `stop_account`, `log` and `debug`.

Until phases 3 and 4 replace them, scripts keep the interface and magic functions that take component ids, bound in builtins as well as `_core` (`BUILTIN_FUNCTIONS` in `ScriptBindings.cpp`):
- `click_button`, `continue_dialogue`, `answer_count` and `close_interfaces`;
- `inv_button` and `move_item`;
- the five `cast_on_*`.

- **Done when:**
    - [x] The entity, item and game tests pass (`ScriptBindingsTests`, rewritten for the facades).
    - [x] A fighter that loots runs against the local engine: the chicken killer, now on the facades, fought, picked up its bones and logged out at its goal. It doesn't eat yet, since eating well needs phase 9's `sustain`.
    - [x] A power-miner runs against the local engine: the new `scripts/examples/power_miner.py` mined copper and tin at Varrock, counted its ores from `skill_xp`, and logged out at its goal. The 289 content answers mining without a pickaxe with a message box (`~mesbox`), not a game message, so the miner checks for a pickaxe itself until phase 4's `chat_dialog` can read one.

---

## 6. Phase 3: interfaces from the cache (done)

The foundation for phase 4. Before it, `InterfaceDecoder` read every component but kept a few fields, and `CacheLoader` kept only the ids it looked for.

### Decoding

`InterfaceDecoder` keeps:
- each layer's children with their signed x and y;
- the hide flag, text and colour;
- the button text, defaulted as `IfType.ts` does: "Ok" for Ok, "Select" for Toggle and Select, and "Continue" for Continue;
- a Target button's verb and target name (`actionverb` "Cast on" and `action` "Wind strike" in `magic.if`), which name the spells.

`GameCache_s::components` keeps the whole table (`IfComponent_s`), keyed by id, and `FindComponent(id)` looks one up. Each component has two ids above it:
- `root`, its interface: the id the cache's run marker gives, which the server opens;
- `parent`, the layer that lists it among its children, filled in after decoding; `None` for a root, and for a component no layer lists.

The 289 cache has 11,942 components. Kept as `std::string`s, they take an estimated 5 MB, which is shared by every account in the process. Moving their strings into the cache's `TextPool`, and keeping options only on inventories, is left until memory matters.

### InterfaceView

`InterfaceView` merges the cache's components with what the server set (`Interfaces_s`):

- **Effective values.** Text, colour and the hidden flag are the server's where it set them, else the cache's.
- **Visibility.** A component is visible when its root is open (the main, side, chat or overlay modal, or a tab) and nothing above it is hidden.
- **Positions.** x and y from the interface's corner: each layer's child offset, or the position the server moved it to (`IF_SETPOSITION`), less the layer's scroll position.
- **Finding text.** Visible text components whose whole text matches, without regard to case, in the open interfaces or in one root's.
- **`ButtonAt`.** The button a click on a component's centre hits: the last one in child order under that point, as the webclient's `addComponentOptions` lists every button under the mouse and a click takes the last.

### Clicking

`GameActions::ClickComponent` sends what the webclient sends:

| Button | Sends |
|---|---|
| Ok, Toggle, Select | `IF_BUTTON` |
| Continue | `RESUME_PAUSEBUTTON` |
| Close | `CLOSE_MODAL` |

A Target button raises `ValueError`, since it needs a target (phase 4's magic), and so does a component that isn't a button. A click on a component that isn't visible returns `False` without sending.

Interface inventories take an option's text as well as its number: `inv_button(item, 'Withdraw 5')` finds it among the inventory component's options.

### Script API

`interfaces.component(id)`, `interfaces.root(id)`, `interfaces.find(text=None, button=None, root=None)`, `interfaces.click(id)`, `interfaces.click_text(text, root=None)` and `interfaces.tab(n)`. They return `Component` snapshots with id, type, button, button text, text, colour, hidden, visible, options, layer, children and position. rs2b0t keeps this layer internal; it's public here as the escape hatch the facades are built on. `interfaces.open()` lists the open roots. The core functions behind them are `get_component`, `get_interface`, `find_components`, `get_open_interfaces`, `get_tab_interface`, `click_component` and `click_text`.

The other component-id functions (`continue_dialogue`, `answer_count`, `close_interfaces`, `click_button`, `move_item` and `cast_on_*`) stay until phase 4's facades replace them.

- **Done when:**
    - [x] The decoder, `InterfaceView` and real-cache tests pass (CacheDesign §15.8). Against the real cache, trademain's "Accept" label hits the rect under it, and multi2's two options are their own Ok buttons.
    - [x] `click_text('Accept')` on a test trade screen sends `IF_BUTTON` for the rect under the text (`ScriptHostTests`, through `FakeGameServer`).

---

## 7. Phase 4: dialogue, make menus, bank, shop, trade and tabs

Every facade here is rs2b0t's, and each helper that waits is a generator. Where an interface has to be recognised, it's by shape, as follows.

### chat_dialog

`is_open()`, `can_continue()`, `continue_()`, `options()`, `choose_option(match=None)`, `texts()`, `is_make_menu()`, `make_products()`, `make(match=None)`, `make_one(match=None)`, `make_x(match, count)`, `is_main_make_panel()`, `main_make_products()`, `make_from_panel(match, op=None)` and `make_from_panel_max(match)`.

- **Options** are the visible Text components with an Ok button and text in the open chat modal, in child order. The engine's `p_choice2` to `p_choice5` set them on `multi2` to `multi5`, and `multiobj2` (cooking's karambwan choice) works the same way. A button sharing its rectangle with another isn't an option. `choose_option` matches by substring, as rs2b0t's does.
- **Chat make menus** are groups of two or more Ok buttons with one rectangle, one button per amount:
    - `skill_multi2` to `skill_multi5`: fletching, spinning, pottery, glass, leather, silver crafting and armour-making, with "Make 1", "Make 5", "Make 10" and "Make X".
    - The furnace's `smelting`: "Smelt 1 @lre@Bronze" … "Smelt X @lre@Bronze".
    - A product's name is its text without line breaks or colour tags (`\n\n\n\nOak Long Bow`, `\n\n\n\n@blu@Silver sickle`), or else what follows the colour tag in its button text.
- **Main make panels** are of two kinds:
    - Stacked groups in the main modal: the tanner's "Tan 1" … "Tan all @lre@Soft Leathers".
    - Inventories whose options are one verb with amounts: the anvil's "Make", "Make 5" and "Make 10", and gold jewellery's. Jewellery fills its slots with invisible placeholders (`invis_ring1`) and draws each product as an object over its slot, so a slot's product is that object.
    - The bank, shop and trade inventories, though shaped alike, are left out.
- **Make X**: `make_x` clicks "X", waits for the count dialog (`skill_multi2` and the furnace call `p_countdialog` after the click), answers it, and waits for the menu to close, as rs2b0t's does. Phase 4 checks against the engine the largest count the dialog takes, and that each skill stops cleanly when the materials run out first.

### bank and banking

- **`bank`:** `is_open()`, `ready()`, `wait_ready(timeout_ms=None)`, `set_note_mode(on)`, `items()` (`BankItem`: slot, id, name, count, ops, com), `count(name)`, `count_by_id(id)`, `withdraw(name, op=None)`, `withdraw_by_id(id, op=None)`, `withdraw_x(name, count)`, `withdraw_x_by_id(id, count, lands_as_id=None)`, `withdraw_load(name)`, `deposit(name, op=None)`, `deposit_inventory()`, `deposit_all_matching(match)`, `open_booth(stand, booth_name, op)`, `open_nearest(booth_name, op)`, `open_nearest_access(access)` and `close(timeout_ms=None)`. Also `withdraw_op(ops, amount)`.
- **`banking`:** `open(stand=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, destination=None, prefer_nearby=True, nearby_radius=NEARBY_BANK_RADIUS)` and `bank_nearest(deposit, common_junk=True, destination=None, return_to=None, booth_name=..., booth_op=..., after_deposit=None)`, with rs2b0t's open rules. Until phase 6 they open banks already in the scene; walking to a distant bank arrives with the walker.
- **Deposit helpers:** `deposit_all_except(keep)`, `deposit_matcher(own, include_common)`, `matches_common_bank_loot(name, id=None)`, `COMMON_BANK_LOOT`, `RANDOM_EVENT_CASKET_ID`, `PERIODIC_BANK_SETTINGS`, `parse_bank_strategy(label)` and `should_bank_now(strategy, state)`.
- **Ids:** the bank is the existing `bankComponent` and `bankInventoryComponent`. The deposit and withdraw generators wait for the inventory update that follows, so rs2b0t's snapshot-generation calls have no counterpart.

### shop and trade

- **`shop`:** `is_open()`, `open(npc_name)`, `stock()` (`ShopItem`: name, count, slot), `buy(name, n)` and `buy_by_id(id, n)`, which return the units bought, `sell(name, n)`, `sell_all(name)` and `close()`. Buying adds up 10s, 5s and 1s. The engine runs 5 user packets a tick and keeps the rest, so `buy` waits for each batch to land before counting.
- **`trade`:** `active()`, `on_offer_screen()`, `on_confirm_screen()`, `partner()` (from the offer screen's "Trading With:" text, as `trade.rs2` sets it), `my_offer()`, `their_offer()` (`TradeItem`: id, name, count), `request(player_name)`, `offer_all(item_name, pick=None)`, `offer(item_name, n, pick=None)`, `remove_all()`, `accept()` (`click_text('Accept')` on whichever screen is open) and `decline()`.
- **Ids,** found at load as `bankInventoryComponent` is, each by the inventory's options:
    - the shop's stock: "Value", "Buy 1";
    - the backpack beside it: "Value", "Sell 1";
    - your offer: "Remove";
    - their offer: the other inventory in that layer;
    - the backpack beside the trade: "Offer";
    - the confirm screen's two inventories, in id order. Phase 4 checks against `trade.rs2` that `tradeconfirm:inv1` is yours.

### quests, prayer, special, combat and magic

| Facade | Python | Found by |
|---|---|---|
| `quests` | `all()`, `status(name)` (`'not_started'`, `'in_progress'`, `'complete'` or `'unknown'`), `points()`, `journal(name)` | The quest tab's Ok buttons with text; status from the colour the server set (red, yellow, green), as rs2b0t reads it. `points()` is varp 101 |
| `prayer` | `points()`, `max()`, `full()`, `known(name)`, `available(name)`, `active(name)`, `set(name, on)`, `clear()` | The prayer tab's Toggle buttons in child order, each with its own varp; names and levels from a table in `prayer.if`'s order |
| `special` | `energy()`, `armed()`, `wielded()`, `cost(weapon_name)`, `ready(weapon_name)`, `bar_component()`, `arm()` | The combat tab's Ok button "Use @gre@Special Attack"; energy and armed are varps 300 and 301 (`sa_energy`, `sa_attack`), checked in phase 4; costs from a weapon table |
| `game` (combat) | `combat_mode()`, `combat_styles()`, `combat_style_mode(style)`, `has_combat_style(style)`, `set_combat_style(style)`, `set_combat_mode(mode)`, `combat_style_resolution(style)`, `auto_retaliate_on()`, `set_auto_retaliate(on)`, `attacked_by_player()` | The combat tab's Select buttons push varp 43 (`com_mode`) with their mode; their labels ("Accurate", "Aggressive", "Controlled", "Defensive") resolve a style, as rs2b0t's do |
| `game` (magic) | `cast_on_npc(spell, npc)`, `cast_on_loc(spell, loc)`, `cast_on_item(spell, item)`, `teleport(name)` | A targeted spell is the Target button whose target name matches ("Wind strike"); a teleport or other self-cast is the Ok button whose text, without its colour tag, does ("Cast @gre@Varrock teleport") |
| `autocast` | `armed()`, `staff_tab_attached()`, `arm(spell)` | The staff combat tab and its spell choices, as rs2b0t's `Autocast` |

- **Done when:** the tests pass, and against the local engine scripts:
    - bank with `deposit_all_except` and `withdraw_x`;
    - fletch 27 longbows with `chat_dialog.make_x('Long Bow', 27)`;
    - smelt with `make('Bronze')`;
    - buy with `shop.buy` and trade both ways between two accounts;
    - set a combat style by name, toggle a prayer, and cast a spell and a teleport by name.

---

## 8. Phase 5: reach

rs2b0t's `Reach` is the shared last-mile primitive: walk to a stand, then use a loc or talk to an NPC, and when the server answers that it can't reach, open the blocking door and try again. Its result is `'done'`, `'retry'` or `'unreachable'`. Ported as `reach.loc_op(...)`, `reach.npc_dialog(...)` and `reach.entity_op(...)`, with its rules: for a loc, the server's "I can't reach that!" decides; for an NPC, the scene is probed within `PROBE_RADIUS`, because a wandering NPC postpones the server's verdict indefinitely. It lands before the walker because banking and shopping use it at short range.

---

## 9. Phase 6: walking across levels

### WalkMap

A world-scale route needs collision beyond the build area, which the cache has. `WalkMap` holds, for every tile of every square on every level, one byte: the eight directions a player can step out of it, by the webclient's rules. That's 534 squares × 4 levels × 4,096 tiles, about 8.7 MB, built once at startup from the cache by `SquareCollision`, the code `WorldMap` uses, and shared read-only by every account. The flags for one square need its neighbours' edges, so the build works a square at a time with a one-tile margin. Phase 6 measures the build time. If it's too slow at startup, squares are built the first time a search reaches them; the process has one thread, so that needs no lock. Closed doors are walls in it, as the cache has them; the door graph crosses them.

### NavGraph

`data/nav/` holds rs2b0t's walker data. rs2b0t's MIT notice is kept in `third_party/rs2b0t/`.

| File | Holds | Source |
|---|---|---|
| `doors.json` | Openable doors and gates, and the tiles each joins | rs2b0t `webwalk/data/doors.json` |
| `stairEdges.json` | Stairs and ladders: from, to (another level), the loc and its action | rs2b0t `webwalk/data/stairEdges.json` |
| `transports.json` | Ships, gangplanks, portals, shortcuts and dungeon links, with requirements | rs2b0t `webwalk/data/transports.json` |
| `travel.json`, `crossings.json`, `teleports.json`, `danger_zones.json` | Spirit trees, gliders, carts, levers; tolls, fares, dialogue and quest unlocks; spell and jewellery teleports; avoidable areas | Converted from rs2b0t's `travelCatalog.ts`, `specialCrossings.ts`, `teleportCatalog.ts` and `dangerZones.ts` by `tools/nav/convert_rs2b0t.py`, once, and committed |

`NavGraph` loads them at startup next to the cache and is shared the same way. An edge's requirements (skills, quests, items, coins, members) are checked against the account's state at search time: a live search fails closed, as rs2b0t's does. The data was built for 289-era content. An edge that disagrees with the server (a loc missing, a door that won't open) is avoided and the route searched again, rather than trusted.

### WorldPathFinder

- **Search.** A* over `WalkMap`, with `NavGraph`'s edges as extra moves and a Chebyshev heuristic. It switches to Dijkstra when long edges (teleports, ships) are in play, as rs2b0t's does.
- **Snapping.** It snaps the start and the goal to a walkable tile with a way out, as rs2b0t's `snapWalkable` and `goalCandidates` do.
- **Options.** It takes rs2b0t's: `max_expansions`, `avoid_doors`, `avoid_zones` (catalog ids or rectangles), and the teleport policy.
- **Result.** Waypoints, each carrying its transport when it's a crossing, plus the cost and the nodes expanded. It fails with a reason.
- **Speed.** Searches run on the main thread. The node budget keeps each one bounded, and phase 6 measures the long ones (Lumbridge to Catherby; into a dungeon) and sets the default budget from them.

### The executor

`traversal` ports rs2b0t's `WalkExecutor`, its `exec/` crossings, `walkLadder` and `arrival`, as stdlib generators over the core's searches, entity actions and the local route the webclient would take:

- **`traversal`:**
    - `walk_to(dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None)`;
    - `walk_resilient(dest, radius, attempts=None, timeout_ms=None, scene_radius=None, max_budget=None, ...)`;
    - `remaining()`, `teleports_enabled()` and `request_repath(reason=None)`;
    - `NAV_PURE_WALK` and `NAV_WITH_TELES`, passed with `**`.
- **`direct_navigator`** came early, in phase 2 (§5).
- **Behaviour,** as rs2b0t documents it:
    - **Following:** locate the player on the route (the corridor snap), click the furthest reachable tile, and re-path when the world disagrees.
    - **Doors:** check the crossing itself, not the door's state; skip doors already open; open double doors from the outside.
    - **Transports:** stairs, ladders, ships with their fares and landing tiles, gliders, spirit trees, carts, and the essence mine's same-origin exit.
    - **Special crossings:** tolls and dialogue choices, and walking to a quest's NPC to unlock a gate.
    - **Getting stuck:** the escalation ladder, reporting `'arrived'`, `'closest'`, `'budget'`, `'failed'` or `'interrupted'`.
    - **Arrival:** beside a destination you can't stand on (a booth, a furnace) counts as arrived.
- **Teleports** are off by default, as in rs2b0t (`scripting.navTeleports` in `client.jsonc`, or per walk). When on, they're used only if the backpack holds the runes or the jewellery.
- `banking.open` gains walking to the nearest known bank (`catalogs.BANK_LOCATIONS`, phase 9 data that moves forward to here).

### Done when

- `WalkMap`, `NavGraph` and `WorldPathFinder` tests pass, including requirements failing closed, `avoid_zones`, and a route that changes level.
- rs2b0t's pure follow-geometry tests (`test/event/webwalk/followMath.test.ts`, `dangerZones.test.ts`) are ported to `tests/Stdlib` and pass.
- The timings are recorded here.
- Against the local engine, `walk_resilient` takes an account:
    - from Lumbridge to Varrock east bank;
    - up Lumbridge castle's stairs to its bank;
    - through the Al Kharid toll gate, paying;
    - across to Karamja by ship.

---

## 10. Phase 7: random events

rs2b0t's `RandomEventGuardian` and solvers, ported to `rs2004/randomevents/`. The host runs the guardian after each pump.

- **Detection.** An event NPC near the player, using rs2b0t's tables:
    - talking events: the genie, drunken dwarf, mysterious old man, sandwich lady and frog;
    - the strange plant;
    - hostile events by id: river troll, swarm, rock golem, zombie, shade, watchman and tree spirit;
    - skill events: the gas chest, the whirlpool fishing spots and the ent.

  An event is skipped when it faces another player (rs2b0t's `eventNpcTargetsAnotherPlayer`), when the bot lists it in `ignored_randoms()`, or, for a hostile one, when it's in `grind_targets()`.
- **Handling.** The guardian takes over: the bot's step in progress is dropped, the solver runs to completion, and `loop()` starts afresh. Bots are already written to be re-entered, and a walk that was interrupted re-plans.
- **Solvers,** ported from rs2b0t:
    - talk to a talking event and accept;
    - rub the genie's lamp, choosing the skill from a setting;
    - pick the strange plant;
    - flee a hostile event only once it has really hit (a visible, positive hit), then come back;
    - the mime, the strange box and the maze;
    - for the gas chest, whirlpool and ent, step away or switch target.
- The 289 content's `macro events/` scripts are the reference for what each event expects, and the source for any event rs2b0t doesn't cover.
- `scripting.randomEvents` (on by default) turns the guardian off for an account.
- **Done when:** the solvers' pure parts have tests (the maze route, the mime's emote for each animation, the strange box's answer), and against the local engine, events spawned with the engine's staff commands are each handled while a script runs.

---

## 11. Phase 8: runtime upkeep and lifecycle

- **Stall guard.** rs2b0t's `StallGuard`: with no tile change and no xp for `scripting.stallMinutes` (10 by default), it walks back to `recovery_anchor()` when that's 8 or more tiles away, or else restarts the bot. `execution.note_progress()` reports work it can't see, such as a completed trade.
- **Run manager.** Turns run back on when energy reaches a threshold: `scripting.runAuto` and `scripting.runEnergyMin` in `client.jsonc`, and `run_manager.override(run_auto=None, energy_min=None)` for one script, as rs2b0t's.
- **Relog.** `relog(delay_seconds=0)`: logs out by the retrying logout `Account::LogOut` uses, waits, logs back in, keeps the script loaded, and raises `reconnect` once the player is placed.
- **Events:**
    - `death`: Hitpoints' current level falls from above 0 to 0, which `death.rs2` does before "Oh dear you are dead!";
    - `npc_say` (npc, text): from `NpcInfoDecoder`'s `MASK_SAY`;
    - `projectile` (a `Projectile`: spotanim, source, destination, target): from `MAP_PROJANIM`.
- **Character design.** `game.appearance_screen_open()` (a component with `ClientCode_e::AcceptDesign` in the main modal) and `game.set_appearance(female, kits, colours)` (`IdkSaveDesign`).
- **Done when:** the stall guard, run manager, relog and event tests pass, and `relog(5)` comes back on the local engine with the bot carrying on.

---

## 12. Phase 9: catalogs and behaviours

Ported to `rs2004/catalogs/` with rs2b0t's names in snake_case, and imported as `from rs2004.catalogs import ...`:

| Group | Contents |
|---|---|
| Banks | `BANK_LOCATIONS`, `bank_distance`, `nearest_bank`, `nearest_usable_bank`, `bank_unlocked`, `resolve_bank_open_route` |
| Tools | `PICKAXES`, `AXES`, `TINDERBOX` … `NEEDLE`, the `*_req` builders, `best_pickaxe`, `best_axe`, `best_from_tiers`, `tool_restock_plan` and the rest of `api-catalogs.md`'s list |
| Tool acquisition | The vendors and shop costs, `plan_gather_tool_acquire`, `plan_pickaxe_acquire`, `plan_axe_acquire`, `plan_broken_tool_repair`, the fishing-gear planners, `can_fund_plan` and the rest |
| Item needs | `held`, `has_all` and `AcquireTask` |
| Gathering | `GatheringLocation`, `resolve_gathering_location`, and the fishing, mining and woodcutting locations, with their options and resolvers |
| Fishing and mining | `FISHING_METHODS`, gear helpers, `ROCK_TYPES`, `resolve_rock_ids`, the gas rock and whirlpool ids |
| Other tables | Walk destinations, pickpocket targets, cow locations, rune routes, cooking ranges and locations, fire spots, herbs and the shop database |
| Behaviours | `tasks` (`ContinueDialog`, `DeathRecovery`, `PeriodicBank`, `create_return_to_anchor_task`), `sustain`, the combat potion plans, `loadout` and the partner-trade policy helpers |

The planners are pure, so their rs2b0t tests port with them. Item and object names are as the 289 cache has them; a table entry that names something the cache lacks fails a test, not a script.

- **Done when:** the ported tests pass, and the end-to-end bots below run.

---

## 13. Tests

- **C++,** as ScriptingDesign §11 sets out: the interface decoding and `InterfaceView`; `WalkMap`, `NavGraph` and `WorldPathFinder`; the new events; relog. The optional real-cache tests (CacheDesign §15.8) cover the rules that find components, and routes over the real map.
- **Python.** `tests/Stdlib/test_*.py` run inside a VM from the test executable:
    - pure logic directly: the query builder, settings, the planners, the maze, and rs2b0t's ported tests;
    - facades against a `FakeGameServer` session, as `ScriptBindingsTests` does today.

  Each test module is a function per case, with plain `assert`s, since pocketpy has no unittest.
- **Smoke,** against the local engine: each phase's "Done when".

---

## 14. Implementation order

0. **Docs.**
    - Work: this document, and the porting sections of ScriptingApi.md and ScriptingDesign §6.
    - Done when: the porting table names the swapped damage hooks and every rename that exists today.
1. **The runtime** (§4). Done.
2. **Entities, items and the game** (§5). Done; ScriptingApi.md is rewritten for the new shape, and grows with each later phase.
3. **Interfaces from the cache** (§6). Done.
4. **Dialogue, make menus, bank, shop, trade and tabs** (§7).
5. **Reach** (§8).
6. **Walking across levels** (§9).
7. **Random events** (§10).
8. **Runtime upkeep and lifecycle** (§11).
9. **Catalogs and behaviours** (§12).

Each phase's "Done when" is in its section. The end-to-end check translates three of rs2b0t's bundled bots into `scripts/examples/`, each running for 30 minutes without a script error, through banking trips and whatever random events come:
- `Miner`: gathering, banking, catalogs and tools;
- `CowKiller`: combat, loot and periodic banking;
- `BankFletcher`: make menus and Make X.

The ScriptingApi.md porting tables then map every rs2b0t export this design covers, and every name in plutonium's `script.go`, to its Python name, or mark it not ported, with the reason.

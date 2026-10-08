# Scripting Design

Plan for running Python scripts that drive the headless client, modelled on plutonium-rsc's scripting. A script defines `loop()`, which returns how many milliseconds to wait before it is called again, plus optional `on_*` hooks for things that happen in game. It reads the game through a flat set of global functions and acts through them too. One process runs several accounts, each with its own client and its own isolated interpreter. Code style follows [CONVENTIONS.md](../CONVENTIONS.md).

Reference sources:

- `plutonium-rsc/script.go`: gpython embedding, hook lookup, the `settings` object, progress reports
- `plutonium-rsc/SCRIPTING.md`, `API.md`: the script-facing model and function names
- `plutonium-rsc/scripts/*.py`: real scripts (`paladins.py` uses most of the model)
- pocketpy v2.2.0: `include/pocketpy/pocketpy.h` (C API), <https://pocketpy.github.io/features/differences/> (language gaps)

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Interpreter | pocketpy 2.2.0, a Python 3 interpreter written in C11 for embedding. It's the closest match to plutonium's gpython: a Python subset, nothing to ship beside the exe, and several isolated VMs per process |
| Binding | pocketpy's C API (`py_bind`, `py_newtype`, `py_bindproperty`), wrapped in a few small C++ helpers. The surface is flat functions plus a handful of read-only classes, which the C API handles directly |
| Dependency | A vcpkg overlay port in `ports/pocketpy`, pinned to v2.2.0 and built as a static C library with `PK_ENABLE_WATCHDOG=1`. The registry's `pocketpy` port is 1.4.6, the old C++17 line. The C code then builds inside vcpkg, so our targets stay `CXX`-only and our `/W4 /WX` never sees it. The port patches `export.h` twice: `PK_API` loses `dllexport`, so the executable doesn't export pocketpy's functions, and `PK_INLINE` loses `__forceinline`, because without `dllexport` MSVC would emit no callable copy of public functions such as `py_retval`. A unity build keeps the library's internal calls inlined |
| Script model | plutonium's: `loop()` returns a delay in milliseconds, and `on_*` hooks are called as events arrive. Both run on the main thread, between pumps |
| Threads | One. pocketpy's current VM is process-global and switched with `py_switchvm`, so every call into Python switches to that account's VM first. `PK_ENABLE_THREADS` stays off |
| Accounts | Several per process, one VM each. pocketpy has 16 VM slots, so one process runs at most 16 accounts; more accounts means more processes |
| API location | Each VM's `builtins` module. Helper modules a script imports then see the API too, without plutonium's re-injection into every submodule |
| Values | Query functions return copies as Python objects (`Npc`, `Player`, `GroundItem`, `Loc`, `Item`). The classes are defined by a short Python prelude that runs in each VM's `builtins`, and `PyConvert` creates instances with their fields set as attributes, so methods such as `in_combat()` are plain Python. An object is a snapshot that stays valid after the entity is gone; actions look the entity up again by index |
| Actions | Return `True` when packets were queued, and `False` when the target is no longer tracked. Bad arguments (a wrong type, an option outside 1–5) raise `TypeError` or `ValueError` |
| Events | Decoders append typed events to a log in `GameState_s`, numbered like `messages`. After each pump, the script host dispatches the ones it hasn't seen yet |
| Runaway scripts | Each call into Python runs under pocketpy's watchdog (`scripting.callTimeoutMs`, 1000 ms by default). Overrunning raises `TimeoutError` in the script, which counts as a script error. `time.sleep` is replaced with a function that raises, because it would stall every account |
| Script errors | An uncaught exception in `loop()` or a hook, or a non-integer return from `loop()`, logs the traceback, stops that account's script and logs that account out. Other accounts carry on |
| Shutdown | The first Ctrl+C calls `on_kill_signal()` on each script that defines it, and logs the others out. A script with the hook keeps running until it calls `stop_account()` or `scripting.killGraceSeconds` runs out. A second Ctrl+C logs everyone out at once, and one during a logout that the server is still refusing closes that connection without waiting. Accounts whose login hasn't started yet never start |
| Config | `client.jsonc` keeps the process-wide settings and gains a `scripting` section. Accounts move to `accounts/*.jsonc`, one file per account, holding the credentials, the script and its settings. This is a breaking change: the `account` section leaves `client.jsonc`, and a config that still has one gets a warning saying where it went. `ConfigFile` parses account files too (`LoadAccount`, `ParseAccount`), so they share its comment handling, error paths and rule that no message quotes a value |
| Logout | `GameClient::Logout` clicks the logout button again every 2 s until the server agrees, because the server refuses a logout during combat and for 10 s after it. Accounts allow 30 s |
| Settings | An account file's `script.settings` object becomes the `settings` global, read by attribute (`settings.npc_ids`). Its keys are passed through unchanged, so script authors write them in Python's snake_case |
| Imports | Host-controlled through pocketpy's `importfile` callback: `import x` loads `scripts/x.py`, then `scripts/lib/x.py`. Nothing else is searched |
| Output | `log()`, `debug()` and `print` go to the account's logger, whose lines carry the account name |
| Trust | Scripts are your own code, so the VM is not a sandbox. pocketpy's `os` module stays, because `PK_ENABLE_OS` also gates the debugger |
| Editor support | `scripts/__builtins__.pyi` declares the API, so Pylance and Pyright know the injected names and complete them |

Rejected:

- **CPython 3.14 with pybind11.** Full Python, but python314.dll and the standard library would ship beside the exe. Running several accounts per process needs sub-interpreters, which many compiled packages (numpy, for one) refuse, and nothing stops a runaway script without extra work.
- **An out-of-process control API.** Scripts would be ordinary Python processes talking to the client over a local WebSocket. That gives the full ecosystem, but every call is a round trip, all state has to be serialized, and each account needs two processes. It can come later as a second front end over the same `ScriptApi`.
- **pocketpy's pybind11-compatible layer.** It implements part of pybind11 on top of the C API. That's more template machinery than a flat API needs, and the C API is the documented surface that the watchdog and VM switching belong to.
- **A thread per account.** Blocking login and reconnect would only stall their own account. But pocketpy would need `PK_ENABLE_THREADS`, anything shared between accounts (bot messages, the logger sink) would need locks, and one loop was the chosen model. The blocking calls become non-blocking instead (§8).
- **Diffing snapshots to find events.** It would copy the whole state on every pump and miss anything that came and went between two pumps. Decoders already know exactly what changed.
- **Blocking-style scripts** (`walk_to(...)`, then `wait_until(...)`). They need a coroutine or a thread per script, and plutonium's scripts port line by line only to the loop model.
- **Copying pocketpy's amalgamated `pocketpy.c` into the repo.** CONVENTIONS §3 declares every dependency in `vcpkg.json`, and 1.3 MB of C would sit inside our warning flags. The overlay port keeps it a normal vcpkg dependency.
- **Exposing `GameState_s` wholesale as nested Python objects.** That's a large surface that would change whenever the state does. Flat functions and small value classes, as plutonium uses, keep scripts stable.

---

## 2. Layout

```
rs2004-headless/
├── vcpkg.json                      gains "pocketpy"
├── vcpkg-configuration.json        new: "overlay-ports": ["ports"]
├── ports/pocketpy/                 overlay port: vcpkg.json, portfile.cmake, CMakeLists.txt, usage
├── accounts/
│   └── example.jsonc.sample        committed; real account files are git-ignored
├── pyrightconfig.json              points Pylance and Pyright at scripts/typings
├── scripts/
│   ├── typings/__builtins__.pyi    API declarations for editors
│   ├── lib/                        shared helper modules
│   └── examples/                   walker.py, chicken_killer.py
├── docs/
│   ├── ScriptingDesign.md          this file
│   └── ScriptingApi.md             the script author's reference, like plutonium's API.md
├── src/
│   ├── Script/
│   │   ├── ScriptRuntime.hpp/.cpp  py_initialize/py_finalize, the 16 VM slots, the import and print callbacks
│   │   ├── ScriptVm.hpp/.cpp       owns one VM slot: run a module, call a function under the watchdog
│   │   ├── ScriptError.hpp         a script failed: compile error, exception, timeout, bad return
│   │   ├── PyConvert.hpp/.cpp      static: C++ values to Python objects, and argument parsing
│   │   ├── ScriptApi.hpp/.cpp      binding-neutral queries and actions over GameState_s and GameActions
│   │   ├── ScriptBindings.hpp/.cpp static: the prelude, constants and functions in a VM's builtins
│   │   ├── ScriptHost.hpp/.cpp     one account's script: load, schedule loop(), dispatch events, handle errors
│   │   └── BotMessenger.hpp/.cpp   messages between the scripts in one process (§12)
│   ├── Core/
│   │   ├── ConfigFile.hpp/.cpp     also loads and validates accounts/*.jsonc
│   │   └── FileWatcher.hpp/.cpp    notices when a script's files change, for --watch (§12)
│   ├── Accounts/
│   │   ├── Account.hpp/.cpp        GameClient + ScriptHost + named logger, and its lifecycle
│   │   ├── AccountRunner.hpp/.cpp  the main loop over every account, and Ctrl+C
│   │   └── ProgressReportFile.hpp/.cpp  writes progress reports (§12)
│   └── Game/State/
│       └── GameEvent_s.hpp         new: the event variant
└── tests/
    ├── Game/TestWorld.hpp/.cpp     the world the fake server sends on login, shared by client, host and account tests
    ├── Script/                     runtime, API, bindings and host tests, and a check that the examples load
    └── Accounts/                   account and runner tests
```

- `ScriptApi` holds all game logic the API needs, such as nearest-NPC filters and inventory counts, in plain C++. `ScriptBindings` only converts arguments and results. A later control server or another language binds the same `ScriptApi`.
- Each `py_CFunction` thunk catches every C++ exception and turns it into a Python exception. A C++ exception must never unwind through pocketpy's C frames.
- A thunk finds its `ScriptApi` in a table indexed by the current VM slot, which `ScriptBindings::Bind` fills and `Unbind` clears. `py_getvmctx()` holds the `ScriptVm`, for the print and import callbacks.

---

## 3. Runtime

### Initialization

`py_initialize` runs once per process, and `py_finalize` can't be undone. `ScriptRuntime` is therefore created once, by `Application`, before any account. Constructing a second one is a bug (assert). The test executable keeps one for the whole run, through a function-local static in a test helper.

`ScriptRuntime` hands out VM slots 0–15. A slot is returned with `py_resetvm`, so the next account starts from a fresh VM. Asking for a 17th slot throws `ScriptError` naming the 16-account limit.

### Per VM, when a slot is taken

`ScriptVm` does steps 1–4 itself; `ScriptHost` does the rest.

1. `py_setvmctx(vm)`, so callbacks and bound functions find their `ScriptVm`.
2. `py_callbacks()`: `importfile` resolves inside `scripts/` and `scripts/lib/` only, packages included; `print` and `flush` write to the account's logger, one line per log entry.
3. Bind `log(*args)` (Info) and `debug(*args)` (Verbose) into `builtins`.
4. Replace `time.sleep` with a function that raises `RuntimeError`, telling the script to return a delay from `loop()` instead.
5. Bind the constants and the API functions into `builtins`, then run the prelude there, which defines the classes (`ScriptBindings`).
6. Set `settings` in `builtins` from the account file.
7. Execute the script as module `__main__`. A compile error, or an exception at module level, fails the account before it logs in.
8. Look up `loop` (required) and every `on_*` hook the script defines (optional).

### Calls

`ScriptVm::Call(function, args)` switches to the slot, starts the watchdog, calls, stops the watchdog, and checks the result:

- If the call raised, `py_formatexc()` becomes the `ScriptError` message, with the traceback, and `py_clearexc` resets the VM.
- If the call ran past `callTimeoutMs`, the result is a `TimeoutError` traceback, and it's handled the same way.

The watchdog only counts Python bytecode. Time spent inside our own C++ functions doesn't trip it.

Confirmed in Phase 1:

- Names bound into `builtins` reach modules a script imports, including those in `scripts/lib/`. Tested.
- `py_newtype` registers a type in one VM only. Tested.
- The watchdog's deadline lives in each VM's own state, as `py_watchdog_begin` in pocketpy's `pkpy.c` shows. It measures `clock()`, which is wall time on Windows and CPU time on Linux; a runaway loop trips both.
- `time.sleep` is replaced per VM, and `from time import sleep` gets the replacement too. Tested.
- An idle VM costs about 1.1 MB of private memory, and one that has loaded plutonium's `paladins.py` about the same (Release build). Sixteen accounts come to roughly 18 MB, plus about 3 MB for the runtime.
- A failed call leaves the VM's stack as it was, over 20,000 failures in a row. Tested.

---

## 4. Script model

```python
CHICKEN = 41

def on_start():
    log("Starting at", get_x(), get_z())

def loop():
    if in_combat():
        return 600

    chicken = get_nearest_npc_by_id(CHICKEN, radius=10)
    if chicken is not None:
        attack_npc(chicken)
        return 1200

    return 600

def on_server_message(msg):
    if msg.startswith("Oh dear"):
        stop_account()
```

### Lifecycle

| Hook | When |
|---|---|
| module body | Once, at load, before login. Use it only for definitions and constants: the API can't be called yet |
| `on_start()` | Once, after the first placement (the first `PLAYER_INFO` after login) |
| `loop()` | Whenever its delay has passed, while in game and placed. It must return an `int` of milliseconds (≥ 0) |
| `on_*` event hooks | After each pump, in event order, before `loop()` |
| `on_disconnect()` / `on_reconnect()` | The connection dropped / a reconnect succeeded. `loop()` and the event hooks pause in between |
| `on_kill_signal()` | Once, on the first Ctrl+C |
| `on_progress_report()` | Every `script.progressReportMinutes`; returns a `dict` written as a table (§12) |
| `on_bot_message(sender, message)` | Another script in the process sent this one a message (§12) |

Each account does this on every pass of the main loop:

1. `GameClient::Pump(0ms)`.
2. Dispatch new events in sequence order. `on_server_tick` is called at most once per pass, with the current tick.
3. If the account is in game and placed, and `loop()`'s delay has passed, call `loop()` and schedule the next call.
4. `GameClient::Flush()`, so the packets `loop()` queued leave now rather than on the next pump.

Hooks see the state as it stands after the whole pump, not as it was when the event happened. A removed entity is passed as its last snapshot.

`stop_script()` stops calling the script but stays logged in, so the account just idles. `stop_account()` stops the script and logs the account out.

---

## 5. Events

`GameState_s` gains an event log next to `messages`. The event types live in `src/Game/State/GameEvent_s.hpp`. `Stat_s` moved to its own header so the event can carry it.

```cpp
using GameEventData = std::variant<NpcAdded_s, NpcRemoved_s, NpcHit_s, PlayerAdded_s, PlayerRemoved_s,
    PlayerHit_s, LocalHit_s, GroundItemAdded_s, GroundItemRemoved_s, GroundItemCountChanged_s,
    LocChanged_s, InventoryChanged_s, StatChanged_s, VarpChanged_s, ModalChanged_s, RebootStarted_s>;

struct GameEvent_s
{
    u64 sequence = 0;
    u64 tick = 0;
    GameEventData data;
};

// in GameState_s
static constexpr std::size_t MAX_EVENTS = 1024;
u64 eventCount = 0;
std::deque<GameEvent_s> events;
[[nodiscard]] std::vector<const GameEvent_s*> GetEventsAfter(u64 sequence) const;
```

| Event | Emitted by | Hook |
|---|---|---|
| `NpcAdded_s` / `NpcRemoved_s` (with the `Npc_s`) | `NpcInfoDecoder` | `on_npc_spawned(npc)` / `on_npc_despawned(npc)` |
| `NpcHit_s` (index, `Hit_s`) | `NpcInfoDecoder` | `on_npc_damaged(npc, damage)` |
| `PlayerAdded_s` / `PlayerRemoved_s` (with the `Player_s`) | `PlayerInfoDecoder` | `on_player_spawned(player)` / `on_player_despawned(player)` |
| `PlayerHit_s` (index, `Hit_s`) / `LocalHit_s` (`Hit_s`) | `PlayerInfoDecoder` | `on_player_damaged(player, damage)` / `on_damaged(damage)` |
| `GroundItemAdded_s` / `GroundItemRemoved_s` (with the `GroundItem_s`) | `ZoneDecoder` (`OBJ_ADD`, `OBJ_REVEAL` / `OBJ_DEL`) | `on_ground_item_spawned(item)` / `on_ground_item_despawned(item)` |
| `GroundItemCountChanged_s` (the item, previous count) | `ZoneDecoder` (`OBJ_COUNT`) | `on_ground_item_changed(item, previous_count)` |
| `LocChanged_s` (the `LocChange_s`) | `ZoneDecoder` (`LOC_ADD_CHANGE`, `LOC_DEL`) | `on_loc_changed(loc)` |
| `InventoryChanged_s` (com) | `ServerPacketDecoder` (`UPDATE_INV_FULL`, `_PARTIAL`, `_STOP_TRANSMIT`) | `on_inventory_changed(com)` |
| `StatChanged_s` (stat, previous and current `Stat_s`) | `ServerPacketDecoder` | `on_stat_changed(stat)` |
| `VarpChanged_s` (varp, previous, value) | `ServerPacketDecoder` | `on_varp_changed(varp, value)` |
| `ModalChanged_s` (main, side and chat modal after the change) | `ServerPacketDecoder` (`IF_OPEN*`, `IF_CLOSE`, `P_COUNTDIALOG`) | `on_interface_changed()` |
| `RebootStarted_s` (ticks) | `ServerPacketDecoder` | `on_system_update(seconds)` |
| messages (existing log) | existing | `on_server_message(msg)`, `on_chat_message(msg, sender)`, `on_private_message(msg, sender)`, `on_trade_request(name)`, `on_duel_request(name)` |

Rules:

- Events describe what the server said. Zone resets, rebuilds and pruning of inactive zones change the state silently and emit nothing. An `OBJ_DEL` for an item that isn't tracked emits nothing either. The state is the truth, and scripts should query it rather than mirror it from events.
- An info packet's events come in three groups: removals, then additions, then hits, each in packet order. An entity counts as removed when the server removes it explicitly, and also when it's tracked past the count the server sends. An added entity's event carries it after its extended blocks, so a new player has its appearance and a new NPC its first animation.
- Events are recorded even when a value didn't change, such as a varp sent with the value it already had.
- The log keeps the newest `MAX_EVENTS`. The host dispatches after every pump, so it can only fall behind if a single pump decodes more than that. If a gap shows up in the sequence numbers, the host logs a warning saying how many events were dropped.
- A fresh login resets `GameState_s`, so sequence numbers start again at 1; a reconnect keeps them. The host notices the restart through `GetLoginCount()` (§8).
- Other C++ code can read the same log through `GetEventsAfter`, as it already does with `GetMessagesAfter`.

---

## 6. Python API

The initial surface. Names follow plutonium wherever 2004 has the same concept; where it doesn't (fatigue, sleeping), the function doesn't exist. Coordinates are absolute `x`/`z`, as plutonium uses, and functions that take a tile assume the player's level.

### Classes (read-only snapshots)

| Class | Attributes and methods |
|---|---|
| `Npc` | `index`, `id` (type), `x`, `z`, `level`, `animation`, `hp`, `max_hp` (both `None` until a hit reveals them), `last_hit_tick`, `target` (`(kind, index)` or `None`), `is_moving()`, `in_combat()` |
| `Player` | `index`, `name`, `combat_level`, `x`, `z`, `level`, `animation`, `hp`, `max_hp`, `last_hit_tick`, `target`, `is_moving()`, `in_combat()` |
| `GroundItem` | `id`, `count`, `x`, `z`, `level` |
| `Loc` | `id` (`-1` when the server removed it), `x`, `z`, `level`, `shape`, `angle`, `layer`. Only scenery the server has changed is known (§10) |
| `Item` | `id`, `count`, `slot`, `com` (the inventory component) |

`in_combat()` means a hit within the last 8 ticks. 2004 has no combat-state packet, so `last_hit_tick` is there for scripts that want a different window.

### Queries

| Group | Functions |
|---|---|
| Local player | `get_x()`, `get_z()`, `get_level()`, `get_pid()`, `get_name()`, `get_combat_level()`, `get_run_energy()`, `get_weight()`, `get_tick()`, `is_moving()`, `get_walk_destination()`, `in_combat()`, `get_local_player()` |
| Stats | `get_current_stat(id)`, `get_max_stat(id)`, `get_experience(id)`, `get_hp()`, `get_max_hp()`, `get_hp_percent()` |
| Area | `distance_to(x, z)`, `distance(x1, z1, x2, z2)`, `in_radius_of(x, z, radius)`, `in_rect(x, z, width, height)`, `at(x, z)` |
| NPCs | `get_npcs(ids=None, radius=None)`, `get_nearest_npc_by_id(ids=None, radius=None, in_combat=None)`, `get_npc(index)` |
| Players | `get_players(radius=None)`, `get_player_by_name(name)` |
| Ground items | `get_ground_items(ids=None, radius=None)`, `get_nearest_ground_item_by_id(ids, radius=None)` |
| Scenery | `get_loc_at(x, z, layer=None)` (changed scenery only) |
| Inventory | `get_inventory(com=INVENTORY)`, `get_inventory_count_by_id(ids, com=INVENTORY)`, `get_inventory_item_by_id(ids, com=INVENTORY)`, `get_empty_slots()`, `is_inventory_full()`, `get_equipment()` |
| Interfaces | `get_main_modal()`, `get_side_modal()`, `get_chat_modal()`, `is_interface_open(id)`, `get_component_text(com)`, `is_count_dialog_open()` |
| Varps | `get_varp(id)` |
| Social | `get_friends()`, `get_ignores()` |

`ids` takes one int or a list of ints, like plutonium's `ids=` arguments.

### Actions

| Group | Functions |
|---|---|
| Walking | `walk_to(x, z, run=False)`, `walk_path(points, run=False)` (up to 25 `(x, z)` waypoints, each walked in a straight line) |
| NPCs | `interact_npc(npc, op)`, `talk_to_npc(npc)` (op 1), `attack_npc(npc)` (op 2) |
| Players | `interact_player(player, op)` |
| Scenery | `interact_loc(id, x, z, op)`, `interact_loc_via(points, id, x, z, op)` |
| Ground items | `interact_ground_item(item, op)`, `take_ground_item(item)` (op 3) |
| Items | `item_op(item, op)`, `inv_button(item, op)`, `drop_item(item)` (op 5), `move_item(com, from_slot, to_slot)` |
| Use and cast | `use_item_on_npc / _player / _loc / _ground_item / _item(...)`, `cast_on_npc / _player / _loc / _ground_item / _item(spell_com, ...)` |
| Interfaces | `click_button(com)`, `continue_dialogue()`, `answer_count(n)`, `close_interfaces()` |
| Chat | `say(text)`, `send_pm(name, text)`, `command(text)`, `add_friend(name)`, `remove_friend(name)`, `add_ignore(name)`, `remove_ignore(name)` |
| Control | `log(*args)`, `debug(*args)`, `stop_script()`, `stop_account()`, `send_bot_message(username, message)` (§12) |

The option numbers behind the conveniences and the component constants were checked against the engine in `289server/content`: `[opnpc2,_]` starts player combat, `[opobj3,...]` and `[opheld5,...]` handlers override take and drop, and `interface.pack` gives `inventory:inv` 3214, `wornitems:wear` 1688, `bank_main:inv` 5382, `bank_side:inv` 2006 and `controls:com_4`/`com_5` 152/153 for run off and on (varp 173 `option_run`). The engine's stat order is 0 to 17 as listed, then 20 for Runecraft.

### Constants

`INVENTORY`, `EQUIPMENT`, the stat IDs (`ATTACK`, `DEFENCE`, ... `RUNECRAFT`), and `LAYER_WALL`, `LAYER_WALL_DECOR`, `LAYER_GROUND`, `LAYER_GROUND_DECOR`.

### Porting from plutonium

- `loop`, `settings`, `log` and the `on_*` hooks behave the same.
- `at_object(obj)` becomes `interact_loc(id, x, z, 1)`. Scenery the server never changed isn't known, so the script supplies the ID and the tile.
- `walk_path_to`, `is_reachable` and `calculate_path_to` need a collision map, which doesn't exist yet. Use `walk_to` with waypoints.
- Fatigue, sleeping and the option menu are RSC-only and have no equivalent.

---

## 7. Accounts and config

### `client.jsonc`

The `account` section moves out. A new `scripting` section is added:

```jsonc
"scripting": {
    "accountsDirectory": "accounts",
    "scriptsDirectory": "scripts",
    "callTimeoutMs": 1000,
    "pollIntervalMs": 10,
    "loginIntervalSeconds": 2,
    "killGraceSeconds": 30,
    "progressDirectory": "progress"
}
```

`ConfigDesign.md` and `ConfigFile` change to match. Its `Validate` no longer requires credentials, and it checks the new ranges instead.

### `accounts/<name>.jsonc`

```jsonc
{
    "username": "test",
    "password": "…",
    "enabled": true,
    "script": {
        "file": "examples/chicken_killer.py",
        "progressReportMinutes": 20,
        "settings": {
            "npc_ids": [41],
            "eat_below": 5
        }
    }
}
```

- `ConfigFile::LoadAccount` reads it with the same nlohmann setup as `client.jsonc`, so it has the same comment support, error paths and no secrets in messages. The account's name is the file name without `.jsonc`.
- A missing `script`, or an empty `file`, means the account just idles and logs a state summary every 10 s. That's today's smoke test.
- `settings` may be any JSON object. It travels as JSON text, and the prelude's `json.loads` turns it into a `Settings` object with each key as an attribute, plus `get()` and `in`.
- `accounts/*.jsonc` is git-ignored; `accounts/example.jsonc.sample` is committed.

### Command line

`rs2004-headless [client.jsonc] [--account accounts/test.jsonc] [--watch] [--debugger]`. Without `--account`, every enabled file in `accountsDirectory` runs. `--watch` and `--debugger` are for working on scripts (§12). Two files with the same username (ignoring case) are refused before any login, since the server would only kick one of them.

### Another world

An account file can carry its own `server` section, with the same keys as `client.jsonc`'s, to log that account into a different world. The rest of `client.jsonc` still applies.

---

## 8. Main loop and the non-blocking client

`AccountRunner::Run()`:

```
load every account file; compile every script            (any failure stops startup, before a login)
start logins one at a time, loginIntervalSeconds apart
until every account has finished:
    for each account: Step(now)                          (§4: pump, events, loop(), flush)
    handle Ctrl+C                                        (§1 Shutdown)
    wait min(pollIntervalMs, time until the earliest loop() is due)
```

`GameClient` doesn't wait unless its caller lets it:

- `BeginLogin()` opens the connection and returns. `ClientStatus_e::Connecting` covers the handshake, which `Pump` advances as bytes arrive. `LoginHandshake` is a step machine with an `Advance` method that sends each request when its turn comes and reads each response once it has all arrived. A refusal is read even when the server closes the connection straight after it, so the error names the status rather than the close.
- A dropped connection starts a reconnect from `Pump`. A login that fails with a retryable status (such as 5, "already logged in", after a crash) or a connection error is retried the same way. There are up to `connectAttempts` (10) attempts. The waits between them double from `retryDelay` (2 s) up to `maxRetryDelay` (30 s), roughly four minutes in all, enough for a server restart. Wrong credentials and other final statuses fail at once. A reconnect that gives up throws `ConnectionLostError`, and a login that gives up rethrows its last error.
- `RequestLogout()` clicks the logout button and returns. `Pump` clicks it again every 2 s, because the server refuses during combat and for 10 s after it, and disconnects at the deadline (30 s for accounts) if the server never agrees. A logout requested while connecting abandons the login.
- IXWebSocket waits up to about 300 ms for a peer's reply when an open connection closes. So `Disconnect` sets the closing socket aside and starts any next attempt on a fresh one, and later pumps free closed sockets once they report `Closed`. Without this, a login timing out against a stalled server stalled every account for 300 ms.
- `GetLoginCount()` rises on each successful login or reconnect, so the host can tell a reconnect happened. `on_reconnect` waits until the player is placed again, because a reconnect after a restart becomes a fresh login that resets the state.
- The blocking `Login()` and `Logout(timeout)` remain as wrappers that pump until done, for the tests and single-account tools.

`Account::Step` never throws: a failed login, a connection that can't be restored or a desync logs an error and finishes that account as failed, and the others carry on. `AccountRunner::Run` returns true only when every account that started logged out cleanly, which `Application` turns into the exit code.

The 10 ms poll is simple and costs almost nothing next to 600 ms ticks. A shared wake signal across all sockets can replace it later if it ever matters.

---

## 9. Changes to existing code

| Where | Change | Phase |
|---|---|---|
| `GameState_s`, decoders | The event log (§5); `Stat_s` moves to `Stat_s.hpp` | 2 |
| `Logger` | An optional name shown on each line, for per-account loggers that share one sink | 3 |
| `ConfigFile`, `ConfigDesign.md` | Remove `account`, add `scripting` | 3 |
| `Application`, `main` | Builds `ScriptRuntime` and an `AccountRunner` over every enabled account, or the one named by `--account`; the smoke-test summary moves into `Account` | 3, 4 |
| `GameClient` | Takes the account's credentials as a constructor argument; `GetLoginCount()`; the logout button is clicked again every 2 s until the server agrees | 3 |
| `GameClient`, `LoginHandshake` | Non-blocking login, reconnect and logout, retried logins, and sockets closed without waiting (§8). `reconnectAttempts` and `reconnectDelay` became `connectAttempts`, `retryDelay` and `maxRetryDelay` | 4 |
| `ServerPacketDecoder`, `GameState_s` | A walk ends when the player hasn't moved for three ticks after the request (`walkRequestTick`), because the engine sends `UNSET_MAP_FLAG` only for a walk that moved. Before this, a walk blocked at its first step left `is_moving()` true for good | 4 |
| `ConfigFile` | An account file's optional `server` section | 4 |
| `.gitignore` | `accounts/*.jsonc` | 3 |
| Tests | `TempFolder` and `TestWorld` became shared helpers; `LogCapture` records each entry's logger name | 1, 3 |
| Tests | `LoopbackPort::IsFree` probes a port with an exclusive bind before a test server takes it. IXWebSocket's server sets `SO_REUSEADDR`, which on Windows let two test servers listen on one port, so a client could reach the wrong one. This was also why socket tests failed under `ctest -j`, which now passes | 4 |
| Tests | `FakeGameServer` can stall a login (`SetStalled`) and ignore logout clicks (`SetIgnoreLogout`). Its mutex is recursive, because IXWebSocket can deliver a Close inside `sendBinary` on the sending thread; with a plain mutex that re-entry threw on an IXWebSocket thread and killed the test process about half the time in Release. `WebSocketClient` doesn't hold its lock while sending, so the client never had this problem | 4 |
| `ConfigFile` | `scripting.progressDirectory` and an account file's `script.progressReportMinutes` | 5 |
| `ScriptVm` | Records the files it runs and imports (`GetFiles`); `CallBuiltin` calls a prelude function, such as `_report_rows`, which turns a report into text; `LoadJson`; `WaitForDebugger` | 5 |
| `ScriptHost` | Holds its VM in an `optional` so `--watch` can replace it; progress reports, bot messages and reloads (§12) | 5 |
| `ScriptApi`, `ScriptBindings` | `SendBotMessage` and `send_bot_message` | 5 |
| `Account`, `AccountRunner` | `AccountOptions_s` (the client options, `watchScripts`, `waitForDebugger`) replaces the `GameClientOptions_s` parameter. Accounts register with the runner's `BotMessenger` and write progress reports through `ProgressReportFile`. A failed script doesn't log a watched account out | 5 |
| `Application`, `main` | `ParseCommandLine` reads `--watch` and `--debugger` into `CommandLine_s`; the Ctrl+C handler is installed after the scripts load, so Ctrl+C still works while waiting for the debugger | 5 |
| `.gitignore` | `progress/` | 5 |
| Tests | `TempFolder::RewriteFile` moves a file's modification time on, so watcher tests don't depend on the file system clock's resolution | 5 |

---

## 10. Limits

- **Packet-only world.** There's no collision map, so no pathfinding or reachability checks. Static scenery (doors, trees, bank booths) is only known once the server changes it, so scripts supply loc IDs and tiles. NPCs and items are numeric IDs with no names or option text. A cache-backed provider would lift all of this, and it's a separate plan.
- **16 accounts per process**, from pocketpy's VM slots.
- **pocketpy is a subset of Python.** The gaps script authors will hit:
    - no `finally` or `else` on `try`;
    - no generator expressions (list comprehensions work);
    - single inheritance only;
    - ints are 64-bit;
    - a starred target must come last;
    - no `re`, and no pip packages;
    - `import` only finds `scripts/` and `scripts/lib/`.

  `ScriptingApi.md` lists these for script authors.
- **One slow script delays everyone**, up to `callTimeoutMs`. This is the cost of a single thread, and the watchdog bounds it.

---

## 11. Test plan

Unit tests run without a network. Anything that sends packets uses the existing `FakeGameServer`. One `ScriptRuntime` serves the whole test executable.

- **Runtime:**
    - Two VMs don't share globals.
    - A 17th slot throws.
    - A reset slot starts clean.
    - `print` reaches the right account's logger.
    - Imports resolve from `scripts/` then `scripts/lib/`, and a missing module raises `ImportError`.
    - A compile error names the file and the line.
    - A traceback is captured into `ScriptError`.
    - `while True: pass` trips the watchdog.
    - `time.sleep` raises.
- **Conversion:** nested JSON settings, the 64-bit int bounds, and attribute access on `settings`.
- **Events:** each decoder emits the expected events, and sequence numbers keep counting across the bound. A zone reset emits nothing.
- **ScriptApi**, in C++ against fixture states:
    - nearest and filter selection, ties and radius edges;
    - inventory counts;
    - an action on an untracked NPC returns `False`;
    - actions queue exactly the packets that `GameActions` sends.
- **Bindings**, as Python snippets against a `FakeGameServer` session:
    - `get_x() == 3200`;
    - `attack_npc(get_nearest_npc_by_id(50))` makes the server receive MOVE_OPCLICK and OPNPC2;
    - wrong argument types raise `TypeError`.
- **ScriptHost**, with an injected clock:
    - `loop()` runs at the returned delay;
    - a non-int return stops the script;
    - hooks run in sequence order, and hooks a script doesn't define are skipped;
    - an exception logs and logs out;
    - `on_kill_signal` and the grace deadline;
    - `on_reconnect` after a dropped connection.
- **Runner:**
    - two accounts on two fake servers;
    - a server that stalls the handshake doesn't delay the other account's `loop()`;
    - the second Ctrl+C logs everyone out.
- **Extras:**
    - `FileWatcher`: a change counts once it has held still for a check; a change undone in time doesn't count; deleting and creating files do count.
    - `ProgressReportFile`: the table's exact text, the one-line summary, starting afresh then appending, creating the folder, and an unwritable path.
    - `BotMessenger`: case-insensitive delivery, a receiver turning a message down, unknown and unregistered usernames.
    - `ScriptHost`:
        - reports at the interval, in the script's order;
        - a report that isn't a dict is a script error;
        - a warning when reports are asked for but the script has no hook;
        - messages sent, received and copied as JSON;
        - the size limit, the 100-message queue, and scripts that can't take messages;
        - a reload after a change to the script or a module it imports;
        - a change that can't load, and a script that failed, both waiting for the next change.
    - `Account`: a watched account stays logged in while its script is broken, and takes bot messages under its username until it goes away.
    - `AccountRunner`: two accounts exchange messages over real connections, and a message to an account without a script returns `False`.
    - `Application::ParseCommandLine`: the flags, and the combinations it refuses.
- **Smoke**, against the local engine: run the example scripts, including one that walks, attacks and picks up loot. Then run two accounts at once.

---

## 12. Extras

Phase 5 adds four things, each independent of the others.

### Progress reports

plutonium's progress reports, kept in a file per account.

- An account file's `script.progressReportMinutes` (1–1440; 0 or leaving it out turns reports off) sets how often the host calls `on_progress_report()`. The first call comes that long after `on_start`. A report that falls due while the account is reconnecting waits until the player is placed again.
- The hook returns a `dict`. Each key and value goes through `str()`, and the rows keep the dict's order, so the script decides it. Returning anything else is a script error, as a bad return from `loop()` is.
- `Account` appends the report to `<scripting.progressDirectory>/<account>.txt` (`progress` by default) as a table under a UTC timestamp and the time since `on_start`. The first report of a run starts the file afresh. The same rows go to the account's log as one line. A file that can't be written is a warning, not an error.
- If `progressReportMinutes` is set but the script has no `on_progress_report`, loading warns.

```
Progress at 2026-10-08T14:20:00Z, 1h 20m after the script started
+-------+-------+
| Name  | Value |
+-------+-------+
| Kills | 10    |
| Bones | 42    |
+-------+-------+
```

### Bot messages

Scripts in one process can send each other messages, as plutonium's can.

- `send_bot_message(username, message)` queues `message` for the script of the account with that username, ignoring case, and returns `True`. It returns `False` when that account's script isn't running, doesn't define `on_bot_message`, or already has 100 messages waiting. A username that no account in the process has raises `ValueError`, because that's a mistake in the script or its settings rather than a passing state.
- The receiver's `on_bot_message(sender, message)` gets the sender's username and a copy of the message. Each VM has its own heap, so messages travel as JSON: a message is anything `json.dumps` accepts (dicts with string keys, lists, tuples, which arrive as lists, strings, numbers, booleans and `None`), up to 64 KiB of JSON. Anything else raises `TypeError` in the sender.
- Messages arrive on the receiver's next step, in the order sent, after game events and chat and before `on_server_tick` and `loop()`. Like other hooks, they wait while the receiver logs in or reconnects. A message sent while handling one is delivered on the receiver's next step, so two scripts can't keep each other busy within one pass.
- pocketpy's registers (`py_r0()` and the rest) belong to the current VM. The host therefore names a register only after switching to the receiver's VM; naming one first put a message into the sender's register, which only the runner test, with two VMs, caught.
- `BotMessenger` maps each username to a receiver function. `AccountRunner` owns it, and every `Account` registers itself, with or without a script, so an account without one is known but never takes a message. `ScriptApi::SendBotMessage` sends through it under the account's own username.

### Reloading on change

`--watch` reloads an account's script when its files change, for working on a script against a live account.

- `ScriptVm` records every file it loads: the script, and each module it imports from `scripts/` or `scripts/lib/`. Every 500 ms the host compares their modification times with those at load. Once a change has held still for one check, the host reloads, so an editor that saves in several writes causes one reload.
- A reload throws the VM away and loads the script into a fresh one with the same settings. The new script starts as any script does: `on_start` runs on the next step if the player is placed, and `loop()` right after. Events, chat and ticks from before the reload are skipped; bot messages already queued are kept. The account stays logged in throughout.
- While watching, a script that fails, whether a reload can't load it or it fails later, leaves the account logged in and idle until its files change again, instead of logging it out, so fixing a typo doesn't cost a login. A script that can't load at startup still stops the run before any login. `stop_account()` still logs out, and after `stop_script()` the account idles until the next change.
- Only the script's files are watched. A change to the account file, such as new settings, needs a restart.

### Debugger

`--debugger` lets VS Code's pocketpy extension debug one account's script, with breakpoints, stepping, the call stack and variables.

- It needs `--account`, naming an account with a script. Before running the script, the host calls `py_debugger_waitforattach("127.0.0.1", 6110)`, which waits for VS Code to attach. `Application` installs its Ctrl+C handler only after the scripts have loaded, so Ctrl+C still ends the process during the wait.
- The attach configuration's `sourceFolder` is the scripts folder. The extension sends breakpoint paths relative to it, and pocketpy matches them against the script's file name, which is relative to the scripts folder too.
- pocketpy's debugger belongs to the whole process, which brings limits that `ScriptingApi.md` lists:
    - A paused script pauses the process. The server hears nothing from the client meanwhile, so a long pause may end in a reconnect.
    - pocketpy turns the watchdog off while a debugger is attached.
    - An uncaught exception stops in the debugger and stays stopped, because pocketpy never returns from it.
    - Ending the debug session ends the process at once (pocketpy calls `exit`), without logging out.
    - A module imported from `scripts/lib/` carries its import name as its file name, so breakpoints in it aren't hit.
- `--watch` and `--debugger` can't be combined, because a reload would replace the VM the debugger traces.
- There's no automated test. Once a debugger attaches, pocketpy treats the whole process as debugged for good, which would turn off the watchdog and stop on the exceptions in every later test. It was checked by hand with a small DAP client instead.

---

## 13. Implementation order

1. **pocketpy and the runtime.**
    - Work: the overlay port, `vcpkg-configuration.json`, `ScriptRuntime`, `ScriptVm`, `ScriptError`, and the Phase 1 checks listed in §3.
    - Done when: the runtime tests pass on both presets, a test script's `log()` reaches the logger, and the watchdog stops an endless loop.
2. **Events.**
    - Work: `GameEvent_s`, the log in `GameState_s`, and emitting from the decoders.
    - Done when: the event tests pass and the existing 113 tests still pass.
3. **One scripted account.**
    - Work: `PyConvert`, `ScriptApi`, `ScriptBindings`, `ScriptHost`, `Account`, the config changes, the named logger, the example scripts, `__builtins__.pyi` and `ScriptingApi.md`. It also covers checking the option numbers and component IDs against the engine.
    - Done when: `--account accounts/test.jsonc` runs an example script against the local engine that walks, attacks an NPC and picks up its drop, and a script error logs a traceback and logs out cleanly.
4. **Many accounts.**
    - Work: `AccountRunner`, the non-blocking `GameClient` (§8), and Ctrl+C with `on_kill_signal`.
    - Done when: the runner tests pass, and two accounts run their scripts side by side on the local engine. Restarting the server makes both reconnect without blocking each other.
5. **Extras** (§12).
    - Work: progress reports to `progress/<account>.txt`; `send_bot_message` and `on_bot_message` between the accounts in the process; `--watch`, which reloads a script when its files change; `--debugger`, which attaches pocketpy's VS Code debugger to one account.
    - Done when: each has tests, except the debugger (§12). Messages between accounts are tested through `AccountRunner` over real connections, since the server plays no part in them. Against the local engine, a `--watch` run writes a progress report and reloads an edited script without logging out, including after a syntax error, and a `--debugger` run stops at a breakpoint in `loop()` for a DAP client that attaches as VS Code's extension does, then logs out cleanly on Ctrl+C.

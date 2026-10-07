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
| Values | Query functions return copies wrapped in read-only Python objects (`Npc`, `Player`, `GroundItem`, `Loc`, `Item`). An object is a snapshot that stays valid after the entity is gone; actions look the entity up again by index |
| Actions | Return `True` when packets were queued, and `False` when the target is no longer tracked. Bad arguments (a wrong type, an option outside 1–5) raise `TypeError` or `ValueError` |
| Events | Decoders append typed events to a log in `GameState_s`, numbered like `messages`. After each pump, the script host dispatches the ones it hasn't seen yet |
| Runaway scripts | Each call into Python runs under pocketpy's watchdog (`scripting.callTimeoutMs`, 1000 ms by default). Overrunning raises `TimeoutError` in the script, which counts as a script error. `time.sleep` is replaced with a function that raises, because it would stall every account |
| Script errors | An uncaught exception in `loop()` or a hook, or a non-integer return from `loop()`, logs the traceback, stops that account's script and logs that account out. Other accounts carry on |
| Shutdown | The first Ctrl+C calls `on_kill_signal()` on each script that defines it, and logs the others out. A script with the hook keeps running until it calls `stop_account()` or `scripting.killGraceSeconds` runs out. A second Ctrl+C logs everyone out at once |
| Config | `client.jsonc` keeps the process-wide settings and gains a `scripting` section. Accounts move to `accounts/*.jsonc`, one file per account, holding the credentials, the script and its settings. This is a breaking change: the `account` section leaves `client.jsonc` |
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
├── scripts/
│   ├── __builtins__.pyi            API declarations for editors
│   ├── lib/                        shared helper modules
│   └── examples/                   idle.py, walker.py, chicken_killer.py, ...
├── docs/
│   ├── ScriptingDesign.md          this file
│   └── ScriptingApi.md             the script author's reference, like plutonium's API.md
├── src/
│   ├── Script/
│   │   ├── ScriptRuntime.hpp/.cpp  py_initialize/py_finalize, the 16 VM slots, the import and print callbacks
│   │   ├── ScriptVm.hpp/.cpp       owns one VM slot: run a module, call a function under the watchdog
│   │   ├── ScriptError.hpp         a script failed: compile error, exception, timeout, bad return
│   │   ├── PyConvert.hpp/.cpp      static: JSON to Python, C++ values to Python, argument parsing
│   │   ├── ScriptTypes.hpp/.cpp    registers Npc, Player, GroundItem, Loc and Item in a VM
│   │   ├── ScriptApi.hpp/.cpp      binding-neutral queries and actions over GameState_s and GameActions
│   │   ├── ScriptBindings.hpp/.cpp static: binds ScriptApi into a VM's builtins
│   │   └── ScriptHost.hpp/.cpp     one account's script: load, schedule loop(), dispatch events, handle errors
│   ├── Accounts/
│   │   ├── AccountFile.hpp/.cpp    static: loads and validates accounts/*.jsonc
│   │   ├── Account.hpp/.cpp        GameClient + GameActions + ScriptHost + named logger, and its lifecycle
│   │   └── AccountRunner.hpp/.cpp  the main loop over every account, and Ctrl+C
│   └── Game/State/
│       └── GameEvent_s.hpp         new: the event variant
└── tests/
    ├── Script/                     runtime, conversion, bindings and host tests
    └── Accounts/                   account file and runner tests
```

- `ScriptApi` holds all game logic the API needs, such as nearest-NPC filters and inventory counts, in plain C++. `ScriptBindings` only converts arguments and results. A later control server or another language binds the same `ScriptApi`.
- Each `py_CFunction` thunk catches every C++ exception and turns it into a Python exception. A C++ exception must never unwind through pocketpy's C frames.
- A thunk finds its account through `py_getvmctx()`, which `ScriptHost` sets to itself when it takes the slot.

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
5. Register the classes (`ScriptTypes`), then bind the API and constants into `builtins` (`ScriptBindings`).
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
| `on_progress_report()` | Every `script.progressReportMinutes`; returns a `dict` written as a table (Phase 5) |

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
| Control | `log(*args)`, `debug(*args)`, `stop_script()`, `stop_account()` |

The option numbers behind the conveniences (`attack_npc` is op 2, `take_ground_item` op 3, `drop_item` op 5) and the component constants (`INVENTORY`, `EQUIPMENT`) are the usual 2004 values. They get checked against the engine's configs in Phase 3, before they're documented.

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
    "killGraceSeconds": 30
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

- `AccountFile` loads it with the same nlohmann setup as `ConfigFile`, so it has the same comment support, error paths and no secrets in messages.
- A missing `script`, or an empty `file`, means the account just idles and logs a state summary every 10 s. That's today's smoke test.
- `settings` may be any JSON object. `PyConvert` turns objects into `dict`s with string keys, arrays into `list`s, and keeps the scalars as they are. The top-level object becomes the attribute-access `settings` global.
- `accounts/*.jsonc` is git-ignored; `accounts/example.jsonc.sample` is committed.

### Command line

`rs2004-headless [client.jsonc] [--account accounts/test.jsonc]`. Without `--account`, every enabled file in `accountsDirectory` runs.

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

Today `GameClient::Login`, `Reconnect` and `Logout(timeout)` block: the handshake can wait up to `loginTimeout`, and a reconnect can retry several times. With one loop, that would stall every other account's scripts and keepalives. Phase 4 changes `GameClient` so that:

- `BeginLogin()` starts the connection and returns. A new `ClientStatus_e::Connecting` covers the handshake, which `Pump` advances as bytes arrive. `LoginHandshake` becomes a step-wise state machine with the same messages and errors.
- Reconnect attempts are scheduled and advanced from `Pump` the same way, with no sleeping.
- `RequestLogout()` clicks the logout button and returns. `Pump` finishes the logout, and a deadline disconnects if the server never confirms.
- `GetLoginCount()` rises on each successful login, so the host can tell a reconnect happened.
- The blocking `Login()` and `Logout(timeout)` stay as wrappers that pump until done. The tests and single-account tools keep working unchanged.

The 10 ms poll is simple and costs almost nothing next to 600 ms ticks. A shared wake signal across all sockets can replace it later if it ever matters.

---

## 9. Changes to existing code

| Where | Change | Phase |
|---|---|---|
| `GameState_s`, decoders | The event log (§5); `Stat_s` moves to `Stat_s.hpp` | 2 |
| `Logger` | An optional name shown on each line, for per-account loggers that share one sink | 3 |
| `ConfigFile`, `ConfigDesign.md` | Remove `account`, add `scripting` | 3 |
| `Application` | Builds `ScriptRuntime` and `AccountRunner`; the smoke-test summary moves into `Account` | 3 |
| `GameClient`, `LoginHandshake` | Non-blocking login, reconnect and logout (§8) | 4 |
| `.gitignore` | `accounts/*.jsonc` | 3 |

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
- **Smoke**, against the local engine: run the example scripts, including one that walks, attacks and picks up loot. Then run two accounts at once.

---

## 12. Implementation order

1. **pocketpy and the runtime.**
    - Work: the overlay port, `vcpkg-configuration.json`, `ScriptRuntime`, `ScriptVm`, `ScriptError`, and the Phase 1 checks listed in §3.
    - Done when: the runtime tests pass on both presets, a test script's `log()` reaches the logger, and the watchdog stops an endless loop.
2. **Events.**
    - Work: `GameEvent_s`, the log in `GameState_s`, and emitting from the decoders.
    - Done when: the event tests pass and the existing 113 tests still pass.
3. **One scripted account.**
    - Work: `PyConvert`, `ScriptTypes`, `ScriptApi`, `ScriptBindings`, `ScriptHost`, `AccountFile`, `Account`, the config changes, the named logger, the example scripts, `__builtins__.pyi` and `ScriptingApi.md`. It also covers checking the option numbers and component IDs against the engine.
    - Done when: `--account accounts/test.jsonc` runs an example script against the local engine that walks, attacks an NPC and picks up its drop, and a script error logs a traceback and logs out cleanly.
4. **Many accounts.**
    - Work: `AccountRunner`, the non-blocking `GameClient` (§8), and Ctrl+C with `on_kill_signal`.
    - Done when: the runner tests pass, and two accounts run their scripts side by side on the local engine. Restarting the server makes both reconnect without blocking each other.
5. **Extras, each optional.**
    - progress reports to `logs/progress_reports/<account>.txt`;
    - `send_bot_message` / `on_bot_message` between accounts in the process;
    - reloading a script when its file changes;
    - attaching pocketpy's VS Code debugger to one account (`py_debugger_waitforattach`).

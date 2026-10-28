# Script structure, bots and control

How a script file is laid out, the bot classes it builds on, the hooks the client calls, and the functions that stop or restart it. Everything here is a builtin: no import needed.

- [Two shapes of script](#two-shapes-of-script)
- [define_bot](#define_bot)
- [AbstractBot](#abstractbot)
- [LoopingBot](#loopingbot)
- [TaskBot and Task](#taskbot-and-task)
- [TreeBot, BranchTask and LeafTask](#treebot-branchtask-and-leaftask)
- [What loop() returns](#what-loop-returns)
- [Lifecycle hooks](#lifecycle-hooks)
- [Upkeep hooks](#upkeep-hooks)
- [Running a bot inside another: ScriptActivity](#running-a-bot-inside-another-scriptactivity)
- [Logging](#logging)
- [Stopping and relogging](#stopping-and-relogging)
- [Timing rules](#timing-rules)

## Two shapes of script

A script is either a **module-level script** or a **bot**.

A module-level script defines `loop()` at the top level, plus any `on_*` hooks. The client wraps it in a `LoopingBot`. It reads its settings from the global `settings`, which holds the whole `script.settings` object of the account file, and may declare them with a module-level `SETTINGS_SCHEMA` dict.

```python
def on_start():
    log('Starting at', game.tile())

def loop():
    tree = locs.query().name('Tree').action('Chop down').within(10).nearest()
    if tree is not None and tree.interact('Chop down'):
        yield from execution.delay_until(lambda: not game.animating(), 8000)
    return 600
```

A bot assigns `BOT = define_bot(...)` at module level. The client calls `create()` to make the bot, and the bot's methods are its loop and hooks. It reads only `script.settings["<name>"]` from the account file, as `self.settings` (and the global `settings`).

```python
class Chopper(LoopingBot):
    def on_start(self):
        self.logs = 0

    def loop(self):
        ...

    def on_skill_xp(self, e):
        if e.name == 'woodcutting':
            self.logs += 1

BOT = define_bot(name='Chopper', create=Chopper)
```

A file with neither `BOT` nor a callable `loop` fails to load with `ValueError`.

The module body runs once, before login. Use it for imports, constants, classes and `BOT`. Game reads return empty values there, and actions fail, because there is no session yet.

## define_bot

```python
define_bot(name=None, create=None, description=None, version=None, category=None, tags=None, settings_schema=None)
```

Describes a bot. Assign the result to the module-level `BOT`.

| Parameter | Meaning |
|---|---|
| `name` | Required, a non-empty string. Names the bot's settings object in the account file, `script.settings["<name>"]`. A missing or empty name raises `ValueError` |
| `create` | Required. A class, or a function that returns a bot (an instance of `AbstractBot` or a subclass). A non-callable raises `TypeError`; a `create()` that returns anything other than a bot raises `TypeError` at load |
| `description`, `version`, `category` | Free text, for your own reference |
| `tags` | A list of strings; `[]` when `None` |
| `settings_schema` | A dict of setting name to [`SettingDef`](settings.md#settingdef). See [Settings](settings.md) |

Returns a `BotManifest` with the same attributes. Every parameter has a default only so it can be passed by keyword, which pocketpy allows only for parameters with defaults.

```python
BOT = define_bot(
    name='Power miner',
    create=PowerMiner,
    description='Mines rocks and drops the ore',
    category='Mining',
    settings_schema={'radius': SettingDef('number', 10, min=1, max=30)},
)
```

## `AbstractBot`

The base class of every bot. Subclass `LoopingBot`, `TaskBot` or `TreeBot` rather than this directly.

### Attributes

| Attribute | Default | Meaning |
|---|---|---|
| `settings` | set before `on_start` | The bot's [`SettingsBag`](settings.md#settingsbag) |
| `loop_delay` | `600` | Milliseconds to wait after a `loop()` that returns `None`. Must be a non-negative `int`, or the script stops with `TypeError`. 600 means "the next server tick", not 600 ms of wall-clock time |
| `loop_cadence` | `None` | When set, wins over `loop_delay` for a `loop()` that returns `None`. One of `{'kind': 'frame'}` (the next pass once a packet arrives, or after 20ms, rs2b0t's client cycle), `{'kind': 'server_tick', 'ticks': n}` or `{'kind': 'time', 'ms': n}`. Anything else stops the script with `ValueError` |
| `delegated` | `False` | Whether another bot runs this one, as a [`ScriptActivity`](#running-a-bot-inside-another-scriptactivity) |

### Methods

| Method | Does |
|---|---|
| `log(*args)` | The same as the builtin [`log`](#logging); for a bot another runs, its parent's log, prefixed with its name |
| `on(event, callback)` | Subscribes `callback` to an [event](events.md) until the bot stops. Returns `None` |
| `command(name, handler, help=None)` | Adds a [console command](console-and-messages.md#console-commands) until the bot stops. Returns `None` |
| `request_finish(reason)` | Stops the script, leaving the account logged in. `on_stop` and the `script_finish` event receive `reason`. A bot another runs ends only its activity |
| `bind_log(sink)`, `bind_finish(sink)` | Send its log lines, and its `request_finish(reason)`, to `sink(text)` instead. `ScriptActivity` uses them |

### Methods the client reads

Override these to change how the client's upkeep treats the bot. A module-level script defines them as top-level functions instead.

| Method | Default | Meaning |
|---|---|---|
| `grind_targets()` | `[]` | NPC names you fight on purpose; the random-event guardian never takes them for a hostile event |
| `ignored_randoms()` | `[]` | Random-event names to leave alone. See [Random events](upkeep.md#random-events) for the names |
| `lamp_skill()` | The [Global](settings.md#global-settings) `lamp_skill`, `'strength'` by default | The skill a genie's lamp is rubbed for |
| `recovery_anchor()` | `None` | Where the bot works, as a `Tile`, for the [stall guard](upkeep.md#the-stall-guard) to walk back to. `None` means restart the bot instead |

## `LoopingBot`

A bot that calls `loop()` over and over. Override `loop(self)`; the base raises `NotImplementedError`. See [What loop() returns](#what-loop-returns).

```python
class Miner(LoopingBot):
    def loop(self):
        if inventory.is_full():
            yield from self.drop_ore()
            return 0
        rock = locs.query().id(2090, 2091).within(8).nearest()
        if rock is None:
            return 1200
        rock.interact('Mine')
        yield from execution.delay_until(lambda: not rock.valid(), 8000)
```

## TaskBot and Task

### `TaskBot`

A `LoopingBot` whose `loop()` runs the first task whose `validate()` is true, then returns `None` (so the bot waits `loop_delay`). Add tasks in `on_start`, highest priority first.

| Member | Meaning |
|---|---|
| `add(*tasks)` | Appends tasks, in order. Each must have callable `validate` and `execute`, or `TypeError` |
| `active_task_name` | The running task's `label`, or `None` between tasks |

`validate()` and `execute()` may both be generators: a validate that waits is run with `yield from`, and its result decides.

### `Task(validate=None, execute=None, label=None)`

A guard and the action it guards. Either pass two callables, or subclass and override `validate(self)` and `execute(self)`. Calling a missing one raises `NotImplementedError`.

```python
from rs2004.catalogs import ContinueDialog

class Fighter(TaskBot):
    def on_start(self):
        self.add(
            ContinueDialog(),
            Task(lambda: game.in_combat(), lambda: None, label='fight'),
            Task(lambda: True, self.attack, label='attack'),
        )

    def attack(self):
        target = npcs.query().name('Cow').within(8).where(lambda n: not n.in_combat).nearest()
        if target is not None and target.interact('Attack'):
            yield from execution.delay_ticks(2)
```

A subclass that defines `__init__` must call `Task.__init__(self, ...)`. pocketpy looks methods up on the class before the instance, which is why the callables are stored apart from the methods.

## TreeBot, BranchTask and LeafTask

### `TreeBot`

A `LoopingBot` whose `loop()` walks a behaviour tree from `root()` down to a leaf and runs it. Override `root(self)`. A node that is neither a `BranchTask` nor a `LeafTask` raises `TypeError`.

### `BranchTask`

A decision. Override `validate()`, `success()` and `failure()`: when `validate()` is true the walk continues at `success()`, otherwise at `failure()`. Each returns the next node. A branch's `validate()` can't wait.

### `LeafTask`

An action. Override `execute()`, which may be a generator.

```python
class HaveFood(BranchTask):
    def validate(self):
        return inventory.contains('Lobster')
    def success(self):
        return FIGHT
    def failure(self):
        return BANK

class Fight(LeafTask):
    def execute(self):
        ...

class GetFood(LeafTask):
    def execute(self):
        opened = yield from banking.open()
        if opened:
            yield from bank.withdraw_x('Lobster', 10)

FIGHT = Fight()
BANK = GetFood()

class Fighter(TreeBot):
    def root(self):
        return HaveFood()
```

## What loop() returns

`loop()` returns how long to wait before it runs again, read the way rs2b0t reads it:

| Return | Waits |
|---|---|
| `None`, or no `return` | The bot's `loop_cadence`, else `loop_delay` (600: the next server tick) |
| `0` | The next pass of the client's main loop, a few milliseconds |
| `600` | The next server tick, exactly |
| Any other `int` ≥ 0 | That many milliseconds of wall-clock time |

A negative number raises `ValueError`; a non-`int` (including `bool` and `float`) raises `TypeError`. Either stops the script.

`loop()` may be a generator: it waits with `yield from` on the functions in [Waiting](waiting.md), and its `return` value is read as above once it finishes. A generator can also `yield` a number of milliseconds itself; a yielded `600` is 600 ms of wall-clock time, not a tick.

`resolve_loop_cadence(loop_delay_ms, override=None)` is the rule above as a function: it returns `override` when given, else `{'kind': 'frame'}` for 0 or less, `{'kind': 'server_tick', 'ticks': 1}` for 600, and `{'kind': 'time', 'ms': n}` otherwise.

## Lifecycle hooks

Define these as methods on a bot, or as module-level functions. Unlike [events](events.md), they have no subscribers.

| Hook | Called |
|---|---|
| `on_start()` | Once, one server tick after the player is first placed in the world, when stats and inventories have arrived. May be a generator; it runs before the first `loop()`. On Tutorial Island, after the [tutorial skip](upkeep.md#tutorial-island) |
| `on_stop(reason)` | Once, when the script stops: after `stop_script()`, `stop_account()`, `request_finish(reason)`, an error, a stall-guard restart, or a logout the client starts, such as Ctrl+C. `reason` is a string. Can't wait |
| `on_pause()`, `on_resume()` | When the console's [`pause` and `resume`](console-and-messages.md#built-in-commands) stop and start the bot. Can't wait |
| `on_progress_report()` | When a [progress report](console-and-messages.md#progress-reports) is due. Returns a `dict` |

A function or method named `on_<something>` that isn't a hook or an event draws a warning at load, which catches typos.

Hooks (other than `on_start`) can't wait: one that returns a generator stops the script with `TypeError`. Set a flag and do the work in `loop()`.

## Upkeep hooks

A module-level script can define these as top-level functions, with the same meaning as the [bot methods](#methods-the-client-reads):

```python
def grind_targets():
    return ['Cow', 'Cow calf']

def ignored_randoms():
    return ['drunken dwarf']

def lamp_skill():
    return 'woodcutting'

def recovery_anchor():
    return Tile(3255, 3288, 0)
```

## Running a bot inside another: `ScriptActivity`

rs2b0t's `ScriptActivity`, with which its account leveler runs each training method's bot. The parent imports the child's module for its `BOT`; a bot in `scripts/bots/` is importable as `bots.<name>`.

```python
from bots.cow_killer import BOT as COW_KILLER

class Leveler(LoopingBot):
    def on_start(self):
        self.activity = ScriptActivity(self.log)
        yield from self.activity.start(COW_KILLER, {'location': 'North-west of Lumbridge'})

    def grind_targets(self):
        child = self.activity.child
        return child.grind_targets() if child is not None else []

    def loop(self):
        if self.activity.outcome is not None:
            log('the cow killer ended:', self.activity.outcome.kind, self.activity.outcome.reason)
            return None
        yield from self.activity.loop()
```

| Member | Does |
|---|---|
| `ScriptActivity(log=None)` | One child at a time. `log(text)` gets the child's log lines, prefixed with its name; without it they go to the account's log |
| `start(manifest, overrides=None)` | **Wait.** Makes the bot `manifest` (a `define_bot` result) describes and runs its `on_start`. Its settings are the schema's defaults and `overrides`, checked as an account's are, so a wrong one raises `ValueError` naming `activity settings["<name>"]`. `RuntimeError` while a child runs; `TypeError` for anything but a `define_bot` result, or a bot that isn't a `LoopingBot` |
| `loop()` | **Wait.** One pass of the child's `loop()`, when its `loop_delay` or `loop_cadence` says it's due; nothing otherwise. Call it from the parent's `loop()` |
| `outcome` | `None` while the child runs. Then an `ActivityOutcome`: `kind` is `'finished'` (it called `request_finish`), `'failed'` (it raised; `reason` is the message) or `'interrupted'`, and `reason` says why |
| `child` | The child bot, or `None` once it has ended |
| `current_task` | The child `TaskBot`'s task in progress, or `None` |
| `interrupt(reason)` | Ends the child now, such as when the player dies: its step in progress stops at its next wait |
| `stop()` | Ends the child: its `on_stop(reason)` and subscriptions, and what it set for the whole account (`sustain`, `run_manager.override`, `event_signal`'s interrupt) |

The child's `on_<event>` hooks are called as subscriptions, which end with it. Its lifecycle hooks are the parent's to call: `on_pause` and `on_resume` aren't passed on unless the parent does it. The random event guardian reads the parent's `grind_targets()` and `ignored_randoms()`, so a parent that runs fighters passes the child's on, as above.

## Logging

| Function | Does |
|---|---|
| `log(*args)` | Writes the arguments, separated by spaces, to the log at Info level, tagged with the account's name |
| `debug(*args)` | The same at Verbose level, shown with `loglevel verbose` |
| `print(*args)` | Also goes to the log |

## Stopping and relogging

### `stop_script()`

Stops calling the script: no more `loop()`, hooks or events. `on_stop` runs. The account stays logged in and idles.

### `stop_account()`

Stops the script, then logs the account out. The logout is retried while the server refuses it, as it does for 10 seconds after combat.

### `relog(delay_seconds=0)`

Logs the account out, waits `delay_seconds` (0 to 86400), and logs it back in, with the script still loaded. Meanwhile `loop()` and hooks wait; `on_disconnect` runs at the logout and `on_reconnect` once the player is placed again, and a wait in progress carries on. Ctrl+C during the wait leaves the account logged out. A value outside the range raises `ValueError`.

### `bot.request_finish(reason)`

As `stop_script()`, but `on_stop` and the `script_finish` event receive `reason`.

### What stops a script

- Any uncaught exception, in `loop()`, a hook, an event subscriber or a console command handler.
- A `loop()` that returns or yields something it can't (see [What loop() returns](#what-loop-returns)).
- Exceeding the call timeout (see below).

The client then calls `on_stop`, logs the traceback, and logs the account out, unless it's running with `--watch`, which leaves it logged in until the next save.

## Timing rules

- Every account in a process runs on one thread. Each call into a script, and each stretch of a generator between two waits, may run for at most `scripting.callTimeoutMs` (1000 ms by default) before it's stopped with `TimeoutError`. A route search inside `traversal` gets five times that; the call gets its usual time afresh once the search returns.
- `time.sleep()` raises `RuntimeError`, since it would stall every account. Wait with [`execution`](waiting.md) instead.
- Each pass of the main loop, the client: (1) calls hooks and subscribers for everything that arrived, events first, then chat messages, then messages from other scripts and console commands; (2) calls `on_tick` if a server tick passed; (3) calls `on_progress_report` if one is due; (4) runs the client's [upkeep](upkeep.md) once a tick; (5) steps `loop()` if what it waits for has happened.
- When the random-event guardian or the stall guard takes over, the `loop()` generator that was waiting is dropped, and `loop()` starts afresh once they finish. A dropped connection or a `relog()` doesn't drop it: the wait carries on once the player is placed again. A long loop can ask [`event_signal.pending()`](waiting.md#event_signal) and stop at a safe point first.
- `pause` drops the step in progress too, and `resume` starts `loop()` afresh.

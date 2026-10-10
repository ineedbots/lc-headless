"""The host's side of a running bot: loading it, its steps, its events and its end. Scripts don't call these.

Each step returns how the host should wait before the next one:
    ('ms', n)       n milliseconds of wall-clock time
    ('update', n)   the next pump that decoded a packet, or n milliseconds, whichever is first; n is -1 for no limit
    ('ticks', n)    n more server ticks
"""

import _core
from rs2004 import events as _events
from rs2004 import upkeep as _upkeep
from rs2004.bot import AbstractBot, BotManifest, LoopingBot, is_generator, resolve_loop_cadence
from rs2004.execution import Ticks, Update
from rs2004.settings import SettingsBag, apply_schema
from rs2004.random_events import random_events

bot = None
_hooks_from = None
_generator = None
# Set while the step in progress is on_start, not loop().
_starting = False
_finish_reason = None
_finished = False
# The random event guardian's solver, or the stall guard's recovery, while it has taken over from the bot.
_guardian = None
# What load() was given, so the stall guard can make the bot afresh.
_main = None
_settings = None
# configure()'s choices.
_random_events_on = False
_stall_minutes = 0


class _ModuleBot(LoopingBot):
    """A script without BOT: its module-level loop() and on_* functions, as a LoopingBot. grind_targets(),
    ignored_randoms() and lamp_skill() at module level are used too."""

    def __init__(self, module):
        self._module = module

    def loop(self):
        return self._module.loop()

    def _module_or(self, name, fallback):
        found = getattr(self._module, name, None)
        return found() if callable(found) else fallback

    def grind_targets(self):
        return self._module_or('grind_targets', [])

    def ignored_randoms(self):
        return self._module_or('ignored_randoms', [])

    def lamp_skill(self):
        return self._module_or('lamp_skill', 'strength')

    def recovery_anchor(self):
        return self._module_or('recovery_anchor', None)


def make_settings(text):
    import json
    values = json.loads(text)
    if not isinstance(values, dict):
        raise TypeError('script.settings must be an object')
    return SettingsBag(values)


def load(main, settings):
    """Makes the bot from the script's module, checks its settings, and finds its hooks. Returns warnings."""
    global bot, _generator, _starting, _finish_reason, _finished, _guardian, _main, _settings
    bot = None
    _generator = None
    _guardian = None
    _starting = False
    _finish_reason = None
    _finished = False
    _main = main
    _settings = settings

    manifest = getattr(main, 'BOT', None)
    if manifest is not None:
        if not isinstance(manifest, BotManifest):
            raise TypeError('BOT must be made by define_bot(...)')
        warnings = apply_schema(settings, manifest.settings_schema)
    else:
        if not callable(getattr(main, 'loop', None)):
            raise ValueError('the script has neither BOT = define_bot(...) nor a loop() function')
        warnings = apply_schema(settings, getattr(main, 'SETTINGS_SCHEMA', None))
    return warnings + _make_bot()


def _make_bot():
    """Makes the bot from what load() was given, and finds its hooks. Returns warnings."""
    global bot, _hooks_from
    manifest = getattr(_main, 'BOT', None)
    if manifest is not None:
        created = manifest.create()
        if not isinstance(created, AbstractBot):
            raise TypeError(f"BOT's create must make a bot, such as a LoopingBot, not {type(created).__name__}")
        bot = created
        _hooks_from = created
    else:
        bot = _ModuleBot(_main)
        _hooks_from = _main

    bot.settings = _settings
    warnings = []
    hooks = []
    for name in dir(_hooks_from):
        if not name.startswith('on_') or not callable(getattr(_hooks_from, name, None)):
            continue
        event = name[3:]
        if event in _events.HOOK_NAMES:
            hooks.append(event)
        else:
            warnings.append(f"defines {name}(), which isn't a hook the client calls")

    _events.set_hooks(hooks)
    return warnings


def _hook(name):
    if _hooks_from is None:
        return None
    hook = getattr(_hooks_from, 'on_' + name, None)
    return hook if callable(hook) else None


def start():
    """Runs on_start once the player is first placed. One that's a generator runs as the first step, and
    loop() follows on the next pass once it finishes."""
    global _generator, _starting
    hook = _hook('start')
    if hook is None:
        return
    result = hook()
    if is_generator(result):
        _generator = result
        _starting = True


def dispatch(name, *args):
    """Calls the event's hook, then its subscribers, and returns what the hook returned."""
    call_args = _events.make_args(name, args)
    result = None
    hook = _hook(name)
    if hook is not None:
        result = hook(*call_args)
        if is_generator(result):
            raise TypeError(f"on_{name}() can't wait; set a flag and do the work in loop()")
    for callback in _events.events.subscribers(name):
        callback(*call_args)
    return result


def configure(random_events_on, stall_minutes, run_auto, run_energy_min):
    """The config's choices for upkeep: scripting.randomEvents, stallMinutes, runAuto and runEnergyMin."""
    global _random_events_on, _stall_minutes
    _random_events_on = random_events_on
    _stall_minutes = stall_minutes
    _upkeep.run_manager.configure(run_auto, run_energy_min)
    _upkeep.stall_guard.configure(stall_minutes)
    _upkeep.stall_guard.reset(_core.step_time())


def upkeep():
    """Once a server tick: turns run on when it should be, and when a random event needs answering or the
    bot has stalled, drops its step in progress for the guardian's solver or the stall guard's recovery,
    which the next step runs. True when one took over. on_start isn't interrupted."""
    global _generator, _guardian
    if bot is None or not _core.is_placed():
        return False
    now = _core.step_time()
    _upkeep.run_manager.tick(now)
    if _guardian is not None or _starting:
        _upkeep.stall_guard.busy(now)
        return False

    if _random_events_on:
        event = random_events.check(bot)
        if event is not None:
            _generator = None
            _guardian = random_events.handle(event)
            return True

    if _upkeep.stall_guard.observe(now, _upkeep.here(), _upkeep.total_xp(), _core.last_progress()):
        _generator = None
        _guardian = _recover()
        return True
    return False


def _recover():
    outcome = yield from _upkeep.recover(bot, _stall_minutes, lambda message: log(message))
    if outcome == 'restart':
        restart('the stall guard restarted the bot')
    else:
        _upkeep.stall_guard.reset(_core.step_time())


def restart(reason):
    """Ends the bot with on_stop(reason) and starts a new one, as rs2b0t's stall guard restarts a script:
    BOT's create() makes it afresh, and on_start runs again. A module's globals stay as they are."""
    global _generator, _starting
    hook = _hook('stop')
    if hook is not None:
        hook(reason)
    bot._dispose_subscriptions()
    _generator = None
    _starting = False
    for warning in _make_bot():
        log(warning)
    _upkeep.stall_guard.reset(_core.step_time())
    start()


def step():
    """Runs the bot's loop until it next waits, and returns how to wait."""
    global _generator, _starting, _guardian
    if _guardian is not None:
        try:
            value = next(_guardian)
        except StopIteration:
            _guardian = None
            return ('ms', 0)
        return _yielded(value)

    if _generator is None:
        result = bot.loop()
        if not is_generator(result):
            return _after_loop(result)
        _generator = result

    try:
        value = next(_generator)
    except StopIteration as e:
        _generator = None
        if _starting:
            _starting = False
            return ('ms', 0)
        return _after_loop(e.value)
    return _yielded(value)


def reset():
    """Drops the step in progress, so the next step calls loop() afresh."""
    global _generator, _starting, _guardian
    _generator = None
    _starting = False
    _guardian = None
    random_events.handling = False


def _after_loop(result):
    if result is None:
        delay = bot.loop_delay
        if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
            raise TypeError('loop_delay must be 0 or more milliseconds, as an int')
        return _cadence_wait(resolve_loop_cadence(delay, bot.loop_cadence))

    if not isinstance(result, int) or isinstance(result, bool):
        raise TypeError(f'loop() must return how many milliseconds to wait, as an int, or None, not {type(result).__name__}')
    if result < 0:
        raise ValueError(f'loop() returned {result}; return 0 or more milliseconds, or None')
    return _cadence_wait(resolve_loop_cadence(result))


def _cadence_wait(cadence):
    kind = cadence.get('kind') if isinstance(cadence, dict) else None
    if kind == 'frame':
        return ('ms', 0)
    if kind == 'server_tick':
        return ('ticks', max(1, cadence.get('ticks', 1)))
    if kind == 'time':
        return ('ms', max(0, cadence['ms']))
    raise ValueError("loop_cadence must be {'kind': 'frame'}, {'kind': 'server_tick', 'ticks': n} or {'kind': 'time', 'ms': n}")


def _yielded(value):
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0:
            raise ValueError(f'loop() yielded {value}; yield 0 or more milliseconds')
        return ('ms', value)
    if isinstance(value, Update):
        timeout = value.timeout_ms
        return ('update', -1 if timeout is None else max(0, int(timeout)))
    if isinstance(value, Ticks):
        return ('ticks', value.count)
    raise TypeError(f'loop() must yield milliseconds as an int, or a wait from execution, not {type(value).__name__}')


def request_finish(reason):
    global _finish_reason
    _finish_reason = reason
    stop_script()


def finish(reason):
    """Ends the bot once: on_stop(reason), then script_finish, then its subscriptions. A reason the bot gave
    request_finish wins."""
    global _finished, _generator
    if _finished or bot is None:
        return
    _finished = True
    _generator = None
    if _finish_reason is not None:
        reason = _finish_reason

    error = None
    hook = _hook('stop')
    if hook is not None:
        try:
            hook(reason)
        except Exception as e:
            error = e
    try:
        dispatch('script_finish', reason)
    except Exception as e:
        if error is None:
            error = e
    bot._dispose_subscriptions()
    if error is not None:
        raise error

"""Running a bot inside another. Mirrors rs2b0t's runtime/ScriptActivity.ts (MIT, see thirdparty/rs2b0t), with
which its account leveler runs each training method's bot.

    from bots.woodcutter import BOT as WOODCUTTER

    def on_start(self):
        self.activity = ScriptActivity(self.log)
        yield from self.activity.start(WOODCUTTER, {'tree': 'Oak'})

    def loop(self):
        if self.activity.outcome is not None:
            ...                                  # it finished, failed or was interrupted
        yield from self.activity.loop()          # one pass of the child's loop(), once it's due

The child's settings are its schema's defaults and the overrides, checked as an account's are. Its log lines
go to log, prefixed with its name, and its request_finish(reason) ends the activity rather than the script.
Its on_<event> hooks are called as subscriptions, which end with it.
"""

import _core
from rs2004.bot import BotManifest, LoopingBot, TaskBot, is_generator, resolve_loop_cadence
from rs2004.events import EVENT_NAMES
from rs2004.execution import event_signal
from rs2004.settings import SettingsBag, apply_schema

__all__ = ['ScriptActivity', 'ActivityOutcome']


class ActivityOutcome:
    """How an activity ended: kind is 'finished', 'failed' or 'interrupted', and reason says why."""

    def __init__(self, kind, reason):
        self.kind = kind
        self.reason = reason

    def __repr__(self):
        return f'ActivityOutcome({repr(self.kind)}, {repr(self.reason)})'


class ActivityFinished(Exception):
    """Raised through the child's step when it asks to finish, ending the step."""
    pass


class ScriptActivity:
    """One child bot at a time. outcome is None while it runs, and says how it ended once it has."""

    def __init__(self, log=None):
        self._log = log
        self.child = None
        self.outcome = None
        self._name = None
        self._next_at = 0
        self._next_tick = 0
        self._running = False
        self._interrupted = False

    @property
    def current_task(self):
        """The child TaskBot's task in progress, or None."""
        child = self.child
        return child.active_task_name if isinstance(child, TaskBot) else None

    def _say(self, message):
        if self._log is not None:
            self._log(message)
        else:
            log(message)

    def start(self, manifest, overrides=None):
        """Makes the bot the manifest describes, with its settings, and runs its on_start. Use with yield from."""
        if self.child is not None:
            raise RuntimeError('an activity is already running')
        if not isinstance(manifest, BotManifest):
            raise TypeError('an activity runs a bot made by define_bot(...)')
        child = manifest.create()
        if not isinstance(child, LoopingBot):
            raise TypeError(f'{manifest.name} cannot run as an activity')

        name = manifest.name
        bag = SettingsBag({key: value for key, value in (overrides or {}).items()})
        for warning in apply_schema(bag, manifest.settings_schema, f'activity settings["{name}"]'):
            self._say(warning)
        child.settings = bag
        child.bind_log(lambda message: self._say(f'[{name}] {message}'))
        child.bind_finish(self._finish)

        self.child = child
        self.outcome = None
        self._name = name
        self._next_at = 0
        self._next_tick = 0
        self._interrupted = False
        self._subscribe_hooks(child)

        hook = getattr(child, 'on_start', None)
        if callable(hook):
            yield from self._run(child, hook)

    def _subscribe_hooks(self, child):
        for attribute in dir(child):
            if attribute.startswith('on_') and attribute[3:] in EVENT_NAMES:
                hook = getattr(child, attribute, None)
                if callable(hook):
                    child.on(attribute[3:], hook)

    def loop(self):
        """One pass of the child's loop(), when its cadence says it's due; nothing otherwise. Use with yield from."""
        child = self.child
        if child is None or _core.step_time() < self._next_at or _core.tick() < self._next_tick:
            return
        delay = yield from self._run(child, child.loop)
        if self.child is not child:
            return
        if not isinstance(delay, int) or isinstance(delay, bool):
            delay = child.loop_delay
        cadence = resolve_loop_cadence(delay, child.loop_cadence)
        kind = cadence.get('kind')
        self._next_at = _core.step_time() + max(0, cadence['ms']) if kind == 'time' else 0
        self._next_tick = _core.tick() + max(1, cadence.get('ticks', 1)) if kind == 'server_tick' else 0

    def _run(self, child, call):
        """Runs call(), driving the generator it may give one step at a time, so an interrupt between steps
        ends it. A finish or failure becomes the outcome, and ends the activity."""
        self._running = True
        result = None
        try:
            result = call()
            if is_generator(result):
                result = yield from self._drive(child, result)
        except ActivityFinished:
            result = None
        except Exception as e:
            if self.outcome is None:
                self.outcome = ActivityOutcome('failed', str(e))
                self._say(f'{self._name} failed: {e}')
            result = None
        self._running = False
        if self.outcome is not None:
            self.stop()
        return result

    def _drive(self, child, generator):
        while not self._interrupted and self.child is child:
            try:
                value = next(generator)
            except StopIteration as e:
                return e.value
            yield value
        return None

    def _finish(self, reason):
        if self.outcome is None:
            self.outcome = ActivityOutcome('finished', reason)
            self._say(f'{self._name} finished: {reason}')
        if self._running:
            raise ActivityFinished(reason)
        self.stop()

    def interrupt(self, reason):
        """Ends the child now, such as when the player dies; outcome says 'interrupted'."""
        if self.child is None:
            return
        self._interrupted = True
        if self.outcome is None:
            self.outcome = ActivityOutcome('interrupted', reason)
        self.stop()

    def stop(self):
        """Ends the child: its on_stop, its subscriptions, and what it set for the whole account (sustain,
        the run manager's override and the interrupt)."""
        child = self.child
        self.child = None
        if child is None:
            return
        self._interrupted = True
        reason = self.outcome.reason if self.outcome is not None else 'activity stopped'
        error = None
        hook = getattr(child, 'on_stop', None)
        if callable(hook):
            try:
                hook(reason)
            except Exception as e:
                error = e
        child._dispose_subscriptions()
        from rs2004.catalogs.tasks import sustain
        from rs2004.upkeep import run_manager
        sustain.set(None)
        event_signal.set_interrupt(None)
        run_manager.override()
        if error is not None:
            raise error

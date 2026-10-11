"""Bots. Mirrors rs2b0t's api/bot/Bot.ts and runtime/defineBot.ts (MIT, see thirdparty/rs2b0t).

A script either sets BOT = define_bot(...) to one of these classes, or defines a module-level loop() and
on_* hooks, which then run as a LoopingBot. Where rs2b0t awaits, loop(), execute() and on_start() may be
generators, used with yield from.
"""

from rs2004.events import events

__all__ = [
    'AbstractBot', 'LoopingBot', 'Task', 'TaskBot', 'BranchTask', 'LeafTask', 'TreeBot',
    'BotManifest', 'define_bot', 'resolve_loop_cadence',
]

# rs2b0t: 600 means one server tick, because so many bots return it meaning exactly that.
ONE_TICK_MS = 600


def resolve_loop_cadence(loop_delay_ms, override=None):
    """How long to wait before the next loop(): 0 is the next pass, 600 the next server tick, and anything
    else that many milliseconds. An override, such as a bot's loop_cadence, wins."""
    if override is not None:
        return override
    if loop_delay_ms <= 0:
        return {'kind': 'frame'}
    if loop_delay_ms == ONE_TICK_MS:
        return {'kind': 'server_tick', 'ticks': 1}
    return {'kind': 'time', 'ms': loop_delay_ms}


def is_generator(value):
    return type(value).__name__ == 'generator'


class AbstractBot:
    """The base of every bot. Override the hooks you need: on_start(), on_stop(reason), on_<event>(...),
    recovery_anchor(), grind_targets(), ignored_randoms() and lamp_skill()."""

    # How long to wait between loops when loop() returns None: 600 is the next server tick.
    loop_delay = ONE_TICK_MS
    # {'kind': 'frame'}, {'kind': 'server_tick', 'ticks': n} or {'kind': 'time', 'ms': n}; wins over loop_delay.
    loop_cadence = None
    # The resolved settings, set before on_start.
    settings = None
    _subscriptions = None

    def log(self, *args):
        log(*args)

    def on(self, event, callback):
        """Subscribes to an event until the bot stops."""
        unsubscribe = events.on(event, callback)
        if self._subscriptions is None:
            self._subscriptions = []
        self._subscriptions.append(unsubscribe)

    def request_finish(self, reason):
        """Stops the script, giving on_stop and script_finish the reason. The account stays logged in."""
        from rs2004 import _runtime
        _runtime.request_finish(reason)

    def grind_targets(self):
        """NPCs this bot fights on purpose, which the random-event guard leaves alone."""
        return []

    def ignored_randoms(self):
        """Random events this bot doesn't stop for, by name: 'genie', 'swarm', 'maze' and so on."""
        return []

    def lamp_skill(self):
        """The skill a genie's lamp is spent on."""
        return 'strength'

    def recovery_anchor(self):
        """Where the bot works, as a Tile, for the stall guard to walk back to; None to restart it instead."""
        return None

    def _dispose_subscriptions(self):
        for unsubscribe in self._subscriptions or []:
            unsubscribe()
        self._subscriptions = []


class LoopingBot(AbstractBot):
    """Implement loop(). It returns how long to wait, as resolve_loop_cadence reads it, or None for the bot's
    loop_delay, or is a generator."""

    def loop(self):
        raise NotImplementedError(f'{type(self).__name__} must define loop()')


class Task:
    """A guard and the action it guards: Task(validate, execute, label=None) from two callables, or a
    subclass that overrides validate() and execute(). Either may be a generator."""

    # pocketpy looks methods up on the class before the instance, so the callables are kept apart.
    def __init__(self, validate=None, execute=None, label=None):
        self._validate = validate
        self._execute = execute
        self.label = label

    def validate(self):
        if self._validate is None:
            raise NotImplementedError(f'{type(self).__name__} must define validate()')
        return self._validate()

    def execute(self):
        if self._execute is None:
            raise NotImplementedError(f'{type(self).__name__} must define execute()')
        return self._execute()


class TaskBot(LoopingBot):
    """Runs the first task whose validate() holds, once per loop. Add tasks in on_start, highest priority
    first."""

    active_task_name = None
    _tasks = None

    def add(self, *tasks):
        if self._tasks is None:
            self._tasks = []
        for task in tasks:
            if not callable(getattr(task, 'validate', None)) or not callable(getattr(task, 'execute', None)):
                raise TypeError('a task needs validate() and execute()')
            self._tasks.append(task)

    def loop(self):
        for task in self._tasks or []:
            valid = task.validate()
            if is_generator(valid):
                valid = yield from valid
            if not valid:
                continue

            self.active_task_name = getattr(task, 'label', None)
            result = task.execute()
            if is_generator(result):
                yield from result
            self.active_task_name = None
            return None

        self.active_task_name = None
        return None


class BranchTask:
    """A decision in a behaviour tree: validate() chooses success() or failure()."""

    def validate(self):
        raise NotImplementedError(f'{type(self).__name__} must define validate()')

    def success(self):
        raise NotImplementedError(f'{type(self).__name__} must define success()')

    def failure(self):
        raise NotImplementedError(f'{type(self).__name__} must define failure()')


class LeafTask:
    """An action in a behaviour tree. execute() may be a generator."""

    def execute(self):
        raise NotImplementedError(f'{type(self).__name__} must define execute()')


class TreeBot(LoopingBot):
    """Each loop walks the tree from root() to a leaf, and runs it."""

    def root(self):
        raise NotImplementedError(f'{type(self).__name__} must define root()')

    def loop(self):
        node = self.root()
        while isinstance(node, BranchTask):
            node = node.success() if node.validate() else node.failure()
        if not isinstance(node, LeafTask):
            raise TypeError(f'a behaviour tree node must be a BranchTask or a LeafTask, not {type(node).__name__}')

        result = node.execute()
        if is_generator(result):
            yield from result
        return None


class BotManifest:
    def __init__(self, name, create, description, version, category, tags, settings_schema):
        self.name = name
        self.create = create
        self.description = description
        self.version = version
        self.category = category
        self.tags = tags or []
        self.settings_schema = settings_schema

    def __repr__(self):
        return f'BotManifest({repr(self.name)})'


# pocketpy only takes a parameter by keyword when it has a default, so every one here has one, and
# define_bot(name='Miner', create=Miner) works as rs2b0t's object literal does.
def define_bot(name=None, create=None, description=None, version=None, category=None, tags=None, settings_schema=None):
    """Describes a bot: create() makes it, and settings_schema maps each setting to a SettingDef. Assign the
    result to BOT."""
    if not isinstance(name, str) or not name:
        raise ValueError('define_bot needs a name')
    if not callable(create):
        raise TypeError('define_bot needs create, a class or function that makes the bot')
    return BotManifest(name, create, description, version, category, tags, settings_schema)

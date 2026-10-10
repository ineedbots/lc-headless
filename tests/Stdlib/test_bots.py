from helpers import FakeModule, raises
from rs2004 import _runtime
from rs2004.execution import Ticks, Update


def load(module, values=None):
    events.clear()
    return _runtime.load(module, SettingsBag(values or {}))


def returning(value):
    return FakeModule(loop=lambda: value)


def test_loop_returns_are_read_as_rs2b0t_reads_them():
    load(returning(None))
    assert _runtime.step() == ('ticks', 1)
    load(returning(600))
    assert _runtime.step() == ('ticks', 1)
    load(returning(0))
    assert _runtime.step() == ('ms', 0)
    load(returning(250))
    assert _runtime.step() == ('ms', 250)


def test_bad_loop_returns_are_errors():
    load(returning('soon'))
    assert 'as an int, or None, not str' in raises(TypeError, _runtime.step)
    load(returning(-1))
    assert 'returned -1' in raises(ValueError, _runtime.step)
    load(returning(True))
    assert 'not bool' in raises(TypeError, _runtime.step)


def test_a_generator_loop_waits_as_it_yields():
    def loop():
        yield 100
        yield Ticks(2)
        yield Update(50)
        yield Update()
        return 0

    load(FakeModule(loop=loop))
    assert _runtime.step() == ('ms', 100)
    assert _runtime.step() == ('ticks', 2)
    assert _runtime.step() == ('update', 50)
    assert _runtime.step() == ('update', -1)
    assert _runtime.step() == ('ms', 0)


def test_a_generator_loop_can_only_yield_waits():
    def loop():
        yield 'soon'

    load(FakeModule(loop=loop))
    assert 'or a wait from execution, not str' in raises(TypeError, _runtime.step)


def test_reset_drops_the_step_in_progress():
    calls = []

    def loop():
        calls.append('start')
        yield 100
        calls.append('rest')

    load(FakeModule(loop=loop))
    _runtime.step()
    _runtime.reset()
    _runtime.step()
    assert calls == ['start', 'start']


class Counter(LoopingBot):
    loop_cadence = {'kind': 'time', 'ms': 75}

    def loop(self):
        self.count = getattr(self, 'count', 0) + 1


def test_a_bot_from_BOT_uses_its_cadence():
    load(FakeModule(BOT=define_bot(name='Counter', create=Counter)))
    assert _runtime.step() == ('ms', 75)
    assert _runtime.bot.count == 1


def test_BOT_must_come_from_define_bot():
    assert 'define_bot' in raises(TypeError, lambda: load(FakeModule(BOT=Counter)))
    assert 'must make a bot' in raises(TypeError, lambda: load(FakeModule(BOT=define_bot(name='x', create=lambda: 5))))


class Priorities(TaskBot):
    loop_delay = 0

    def on_start(self):
        self.ran = []
        self.hungry = True
        self.add(
            Task(lambda: self.hungry, self.eat, label='eat'),
            Task(lambda: True, lambda: self.ran.append('fight'), label='fight'),
        )

    def eat(self):
        self.ran.append('eat ' + self.active_task_name)
        yield 100
        self.hungry = False


def test_a_task_bot_runs_the_first_task_that_validates():
    load(FakeModule(BOT=define_bot(name='Priorities', create=Priorities)))
    _runtime.start()
    bot = _runtime.bot
    assert _runtime.step() == ('ms', 100)
    assert _runtime.step() == ('ms', 0)
    assert _runtime.step() == ('ms', 0)
    assert bot.ran == ['eat eat', 'fight']
    assert bot.active_task_name is None


class Hungry(BranchTask):
    def __init__(self, bot):
        self.bot = bot

    def validate(self):
        return self.bot.hungry

    def success(self):
        return Do(self.bot, 'eat')

    def failure(self):
        return Do(self.bot, 'fight')


class Do(LeafTask):
    def __init__(self, bot, what):
        self.bot = bot
        self.what = what

    def execute(self):
        self.bot.ran.append(self.what)


class Tree(TreeBot):
    hungry = True

    def root(self):
        if not hasattr(self, 'ran'):
            self.ran = []
        return Hungry(self)


def test_a_tree_bot_walks_to_a_leaf():
    load(FakeModule(BOT=define_bot(name='Tree', create=Tree)))
    _runtime.step()
    _runtime.bot.hungry = False
    _runtime.step()
    assert _runtime.bot.ran == ['eat', 'fight']


def test_a_generator_on_start_runs_as_the_first_step():
    def on_start():
        yield 300

    load(FakeModule(loop=lambda: 0, on_start=on_start))
    _runtime.start()
    assert _runtime.step() == ('ms', 300)
    assert _runtime.step() == ('ms', 0)


def test_hooks_are_found_and_misspellings_warned_about():
    warnings = load(FakeModule(loop=lambda: 0, on_tick=lambda e: None, on_npc_spawn=lambda npc: None))
    assert 'tick' in _listening
    assert warnings == ["defines on_npc_spawn(), which isn't a hook the client calls"]


def test_hooks_get_payloads_and_cannot_wait():
    seen = []

    def on_skill_xp(e):
        seen.append(e.name)

    def on_tick(e):
        yield 1

    load(FakeModule(loop=lambda: 0, on_skill_xp=on_skill_xp, on_tick=on_tick))
    _runtime.dispatch('skill_xp', 8, 100, 25)
    assert seen == ['woodcutting']
    assert "can't wait" in raises(TypeError, lambda: _runtime.dispatch('tick', 1))


class Finisher(LoopingBot):
    def on_start(self):
        self.stopped = []
        self.on('tick', lambda e: None)

    def loop(self):
        self.request_finish('done')

    def on_stop(self, reason):
        self.stopped.append(reason)


def test_finishing_runs_on_stop_once_and_drops_subscriptions():
    load(FakeModule(BOT=define_bot(name='Finisher', create=Finisher)))
    _runtime.start()
    bot = _runtime.bot
    assert 'tick' in _listening

    _runtime.step()
    _runtime.finish('the script stopped')
    _runtime.finish('again')
    assert bot.stopped == ['done']
    assert 'tick' not in _listening

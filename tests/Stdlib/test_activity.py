"""ScriptActivity, with rs2b0t's test/runtime/ScriptActivity.test.ts ported."""

from helpers import raises
from rs2004 import _runtime


def drive(generator):
    """Runs a generator to its end, giving its return value."""
    while True:
        try:
            next(generator)
        except StopIteration as e:
            return e.value


def host():
    return ScriptActivity(lambda message: None)


def child(name, create, schema=None):
    return define_bot(name=name, create=create, settings_schema=schema)


class Finishing(LoopingBot):
    stops = 0
    after_finish = False

    def loop(self):
        self.request_finish('out of logs')
        Finishing.after_finish = True

    def on_stop(self, reason):
        Finishing.stops += 1


def test_a_childs_finish_unwinds_its_step_keeps_the_parent_running_and_cleans_up_once():
    finish_before = _runtime._finish_reason
    activity = host()
    drive(activity.start(child('child', Finishing), {}))
    drive(activity.loop())
    assert activity.outcome.kind == 'finished'
    assert activity.outcome.reason == 'out of logs'
    assert _runtime._finish_reason == finish_before
    assert not Finishing.after_finish
    activity.stop()
    assert Finishing.stops == 1


class DoneAtStart(LoopingBot):
    loops = 0

    def on_start(self):
        self.request_finish('already done')

    def loop(self):
        DoneAtStart.loops += 1


def test_finishing_during_on_start_never_runs_the_childs_loop():
    activity = host()
    drive(activity.start(child('child', DoneAtStart), {}))
    drive(activity.loop())
    assert DoneAtStart.loops == 0
    assert activity.outcome.reason == 'already done'
    assert activity.child is None


class Reading(LoopingBot):
    seen = None

    def on_start(self):
        Reading.seen = self.settings.raw()

    def loop(self):
        return None


def test_defaults_are_resolved_with_the_overrides_and_checked():
    schema = {'amount': SettingDef('number', 12, min=1), 'mode': SettingDef('string', 'bank')}
    activity = host()
    drive(activity.start(child('child', Reading, schema), {'amount': 5}))
    assert Reading.seen == {'amount': 5, 'mode': 'bank'}
    assert activity.child.delegated
    activity.stop()

    message = raises(ValueError, lambda: drive(host().start(child('child', Reading, schema), {'amount': 0})))
    assert message == 'activity settings["child"].amount must be at least 1'


class Broken(LoopingBot):
    stopped = None

    def loop(self):
        raise RuntimeError('broken operation')

    def on_stop(self, reason):
        Broken.stopped = reason


def test_unexpected_child_exceptions_are_failures_and_torn_down():
    activity = host()
    drive(activity.start(child('broken', Broken), {}))
    drive(activity.loop())
    assert activity.outcome.kind == 'failed'
    assert activity.outcome.reason == 'broken operation'
    assert Broken.stopped == 'broken operation'


class Waiting(LoopingBot):
    continued = False
    stops = 0

    def loop(self):
        yield from execution.delay_ticks(100)
        Waiting.continued = True

    def on_stop(self, reason):
        Waiting.stops += 1


def test_an_interrupt_unwinds_the_childs_step_in_progress():
    activity = host()
    drive(activity.start(child('waiting', Waiting), {}))
    running = activity.loop()
    next(running)
    activity.interrupt('death')
    assert drive(running) is None
    assert not Waiting.continued
    assert Waiting.stops == 1
    assert activity.outcome.kind == 'interrupted'
    assert activity.outcome.reason == 'death'


class Supplying(Task):
    def __init__(self):
        Task.__init__(self, label='Withdraw supplies')

    def validate(self):
        return True

    def execute(self):
        yield 100


class Supplier(TaskBot):
    def on_start(self):
        self.add(Supplying())


def test_the_childs_task_in_progress_is_visible():
    activity = host()
    drive(activity.start(child('child', Supplier), {}))
    running = activity.loop()
    next(running)
    assert activity.current_task == 'Withdraw supplies'
    drive(running)
    assert activity.current_task is None
    activity.stop()


class Paced(LoopingBot):
    loop_cadence = {'kind': 'time', 'ms': 75}
    loops = 0

    def loop(self):
        Paced.loops += 1


def test_the_childs_cadence_decides_when_its_next_loop_is_due():
    activity = host()
    drive(activity.start(child('paced', Paced), {}))
    drive(activity.loop())
    drive(activity.loop())
    assert Paced.loops == 1
    activity.stop()


class Talkative(LoopingBot):
    ticks = []

    def on_start(self):
        self.log('starting', 2)

    def on_tick(self, e):
        Talkative.ticks.append(e.tick)

    def loop(self):
        return None


def test_the_childs_log_is_prefixed_and_its_hooks_last_as_long_as_it_does():
    events.clear()
    lines = []
    activity = ScriptActivity(lines.append)
    drive(activity.start(child('Chopper', Talkative), {}))
    assert lines == ['[Chopper] starting 2']
    _runtime.dispatch('tick', 7)
    activity.stop()
    _runtime.dispatch('tick', 8)
    assert Talkative.ticks == [7]


def test_only_one_child_at_a_time_and_only_from_define_bot():
    activity = host()
    drive(activity.start(child('paced', Paced), {}))
    assert 'already running' in raises(RuntimeError, lambda: drive(activity.start(child('paced', Paced), {})))
    activity.stop()
    assert 'define_bot' in raises(TypeError, lambda: drive(activity.start(Paced, {})))
    assert 'cannot run as an activity' in raises(TypeError, lambda: drive(activity.start(child('x', lambda: AbstractBot()), {})))

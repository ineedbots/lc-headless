"""Preparation, interruption and bounded recovery from upstream 95175bcc."""

import rs2004.quests.engine.quest_engine as engine
from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, quest_step
from rs2004.quests.engine.retaliation import prepare_quest_retaliation
from rs2004.quests.types import QuestRecord


def result(value):
    yield from ()
    return value


class Reset:
    def __init__(self):
        self.pending = False
        self.supplies = []
        self.reason = 'blocked reset'
        self.restore_ok = True
        self.prepare_ok = True
        self.calls = []

    def prepare(self, module, snap, log):
        self.calls.append('bank')
        self.pending = True
        yield from ()
        return self.prepare_ok

    def restore(self, log):
        self.calls.append('restore')
        if self.restore_ok:
            self.pending = False
        yield from ()
        return self.restore_ok

    def tick(self, module, snap, log):
        prepared = yield from self.prepare(module, snap, log)
        if not prepared:
            return False
        restored = yield from self.restore(log)
        return restored


class Host:
    def __init__(self):
        self.skip = False
        self.restart = False
        self.death = False
        self.outcome = 'working'
        self.finished = []
        self.stopped = 0
        self.notes = []

    def log(self, text):
        pass

    def food_item(self):
        return None

    def picked_ids(self):
        return set(['cook'])

    def skip_pending(self):
        return self.skip

    def automatic_recovery(self):
        return True

    def consume_skip(self):
        skip = self.skip
        self.skip = False
        return skip

    def consume_restart(self):
        restart = self.restart
        self.restart = False
        return restart

    def consume_death(self):
        death = self.death
        self.death = False
        return death

    def finish(self, reason):
        self.finished.append(reason)

    def note_state(self, rows, id, message, count, parked):
        self.notes.append(message)

    def prepare(self, request):
        if self.outcome == 'error':
            raise RuntimeError('cannot source supplies')
        yield from ()
        return self.outcome

    def stop_preparation(self):
        self.stopped += 1

    def exit_preparation(self):
        yield from ()


def world():
    scene = Scene()
    host = Host()
    runner = engine.QuestEngine(host)
    runner.running_id = 'cook'
    module = QuestModule(record=QuestRecord(id='cook', name="Cook's Assistant"))
    spy_on(engine, 'def_by_id', returns=module)
    spy_on(runner, '_build_snapshot', returns=QuestSnapshot(journal='in_progress'))
    spy_on(runner, '_refresh_bank_counts')
    spy_on(runner, '_current_rows', returns=[])
    spy_on(event_signal, 'pending', returns=False)
    reset = Reset()
    spy_on(engine, 'QuestBankReset', impl=lambda food: reset)
    return scene, host, runner, module, reset


def preparation_cycle():
    scene, host, runner, module, reset = world()
    runner._preparation = Record({'id': 'cook', 'request': Record({}), 'reset': reset, 'phase': 'bank', 'tries': 0})
    run_wait(runner._run_preparation())
    expect(runner._preparation.phase).to_be('work')
    expect(reset.pending).to_be(True)
    host.outcome = 'ready'
    reset.restore_ok = False
    run_wait(runner._run_preparation())
    expect(runner._preparation.phase).to_be('restore')
    expect('cook' in runner._prepared).to_be(False)
    reset.restore_ok = True
    run_wait(runner._run_preparation())
    expect(runner._preparation).to_be(None)
    expect('cook' in runner._prepared).to_be(True)
    expect('cook' in runner._freshened).to_be(True)
    expect(runner._bank_known).to_be(False)


test('preparation waits for work and acknowledged loadout restoration before resuming', preparation_cycle)


def preparation_interruption(mode):
    def run():
        scene, host, runner, module, reset = world()
        reset.pending = True
        runner._preparation = Record({'id': 'cook', 'request': Record({}), 'reset': reset, 'phase': 'work', 'tries': 0})
        if mode == 'skip':
            host.skip = True
        elif mode == 'restart':
            host.restart = True
        else:
            host.outcome = 'error'
        run_wait(runner._run_preparation())
        if mode == 'error':
            expect(runner._preparation.phase).to_be('restore')
            run_wait(runner._run_preparation())
        expect(runner._preparation).to_be(None)
        expect(reset.calls).to_contain('restore')
        if mode == 'restart':
            expect('cook' in runner._prepared).to_be(False)
        else:
            expect(runner.running_id).to_be(None)
    return run


for mode in ['skip', 'restart', 'error']:
    test('preparation restores the saved loadout on ' + mode, preparation_interruption(mode))


def recovery_escalation():
    scene, host, runner, module, reset = world()
    spy_on(engine.quests, 'journal', impl=lambda name: result(True))
    expect(runner._begin_recovery('cook', 'stalled')).to_be(True)
    expect(runner._recovery.mode).to_be('refresh')
    run_wait(runner._run_recovery())
    expect(runner._recovery).to_be(None)
    runner._begin_recovery('cook', 'stalled again')
    expect(runner._recovery.mode).to_be('bank')
    run_wait(runner._run_recovery())
    expect(reset.calls).to_equal(['bank', 'restore'])
    runner._begin_recovery('cook', 'still stalled')
    expect(runner._recovery.abort).to_contain('exhausted')
    run_wait(runner._run_recovery())
    expect(runner.running_id).to_be(None)
    expect(runner._blocked['cook'][0]).to_contain('exhausted')


test('recovery refreshes once, resets through the bank once, then aborts the quest', recovery_escalation)


def stalled_recovery():
    scene, host, runner, module, reset = world()
    reset.prepare_ok = False
    runner._begin_recovery('cook', 'restart', True)
    for attempt in range(engine.FRESH_GIVE_UP):
        run_wait(runner._run_recovery())
    expect(host.finished[0]).to_contain('cannot safely restart')
    expect(runner._recovery is not None).to_be(True)


test('an unreachable recovery bank stops with the pending loadout retained', stalled_recovery)


def retaliation_and_progress():
    scene, host, runner, module, reset = world()
    state = [True]
    spy_on(game, 'auto_retaliate_on', impl=lambda: state[0])
    spy_on(game, 'set_auto_retaliate', impl=lambda wanted: state.__setitem__(0, wanted) is None)
    module.auto_retaliate = False
    expect(run_wait(prepare_quest_retaliation(module, QuestSnapshot()))).to_be(True)
    expect(state[0]).to_be(False)
    clock = [100]
    spy_on(engine, '_now_ms', impl=lambda: clock[0])
    snap = QuestSnapshot(journal='in_progress', stage=1)
    step = quest_step('wait', reason='blocked')
    expect(runner._monitor_progress('cook', step, snap, False)).to_be(False)
    clock[0] += 300001
    expect(runner._monitor_progress('cook', step, snap, False)).to_be(None)
    expect(runner._recovery.mode).to_be('refresh')


test('quest retaliation is confirmed and a five-minute stationary stall starts recovery', retaliation_and_progress)


def bounded_preparation():
    scene, host, runner, module, reset = world()
    module.on_start = lambda: host.notes.append('started')
    reset.prepare_ok = False
    runner._preparation = Record({'id': 'cook', 'request': Record({}), 'reset': reset, 'phase': 'bank', 'tries': 0})
    for attempt in range(engine.FRESH_GIVE_UP):
        run_wait(runner._run_preparation())
    expect(host.finished[0]).to_contain('cannot safely prepare')
    reset.prepare_ok = True
    host.outcome = 'ready'
    reset.restore_ok = False
    for attempt in range(engine.FRESH_GIVE_UP):
        run_wait(runner._run_preparation())
    expect(host.finished[-1]).to_contain('cannot restore')
    reset.restore_ok = True
    run_wait(runner._run_preparation())
    expect(host.notes).to_contain('started')
    expect(runner._preparation).to_be(None)
    run_wait(runner._run_preparation())
    run_wait(runner._run_recovery())
    request = Record({'skills': [Record({'skill': 'mining', 'level': 100})]})
    expect(runner._needs_preparation(request, {})).to_be(True)
    request = Record({'items': [Record({'item': 'Iron bar', 'count': 2})]})
    expect(runner._needs_preparation(request, {'iron bar': 1})).to_be(True)
    expect(runner._needs_preparation(request, {'iron bar': 2})).to_be(False)
    runner._last_bank_counts = {'cake': 1}
    runner._last_bank_id_counts = {1891: 1}
    spy_on(engine, 'quest_preparation_request', returns=Record({'food': Record({'item': 'Cake', 'count': 8})}))
    runner._prepared.clear()
    host.outcome = 'working'
    expect(run_wait(runner._prepare_candidate('cook', module, QuestSnapshot(journal='in_progress')))).to_be(True)
    expect(runner._preparation.phase).to_be('work')


test('preparation failure budgets stop safely and stock shortages start preparation', bounded_preparation)


def recovery_interruptions():
    scene, host, runner, module, reset = world()
    module.on_start = lambda: host.notes.append('started')
    runner._begin_recovery('cook', 'stalled')
    host.restart = True
    run_wait(runner._run_recovery())
    expect(reset.calls).to_equal(['bank', 'restore'])
    runner._begin_recovery('cook', 'stalled')
    host.skip = True
    run_wait(runner._run_recovery())
    expect(runner.running_id).to_be(None)
    expect(host.notes).to_contain('started')
    runner._begin_recovery('cook', 'stalled')
    def throws(module, snap, log):
        raise RuntimeError('bank unavailable')
        yield
    spy_on(reset, 'tick', impl=throws)
    for attempt in range(engine.FRESH_GIVE_UP):
        run_wait(runner._run_recovery())
    expect(host.finished[-1]).to_contain('bank unavailable')
    spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(prepare_quest_retaliation(module, QuestSnapshot()))).to_be(False)
    run_wait(runner._run_recovery())
    runner._preparation = Record({'id': 'cook', 'phase': 'bank', 'reset': reset})
    run_wait(runner._run_preparation())
    expect(runner._preparation.phase).to_be('bank')
    spy_on(event_signal, 'pending', returns=False)
    spy_on(game, 'auto_retaliate_on', returns=False)
    spy_on(game, 'set_auto_retaliate', returns=False)
    expect(run_wait(prepare_quest_retaliation(module, QuestSnapshot()))).to_be(False)


test('recovery honors restart, skip, event interruption and bounded bank errors', recovery_interruptions)


def preparation_deaths():
    scene, host, runner, module, reset = world()
    module.on_start = lambda: host.notes.append('started')
    runner._preparation = Record({'id': 'cook', 'phase': 'work', 'reset': reset})
    for attempt in range(3):
        host.death = True
        expect(run_wait(runner._recover_death_if_pending())).to_be(True)
        expect(runner._preparation.phase).to_be('restore')
        expect(runner._preparation.retry).to_be(True)
    expect(runner._preparation.error).to_contain('3 deaths')
    runner._preparation = None
    host.death = True
    run_wait(runner._recover_death_if_pending())
    expect(runner.running_id).to_be(None)
    runner.running_id = 'cook'
    reset.pending = True
    runner._recovery = Record({'reset': reset})
    host.death = True
    run_wait(runner._recover_death_if_pending())
    expect(host.finished[-1]).to_contain('died while restoring')


test('preparation deaths restore first and three deaths stop the quest', preparation_deaths)


def execute_preparation_and_recovery():
    scene, host, runner, module, reset = world()
    runner._preparation = Record({'id': 'cook', 'request': Record({}), 'reset': reset, 'phase': 'bank', 'tries': 0})
    run_wait(runner.execute())
    expect(runner._preparation.phase).to_be('work')
    runner._preparation = None
    runner._begin_recovery('cook', 'stalled', True)
    run_wait(runner.execute())
    expect(runner._recovery).to_be(None)
    host.restart = True
    run_wait(runner.execute())
    expect(runner._recovery).to_be(None)
    expect(reset.calls).to_contain('restore')


test('the task loop services preparation and recovery before normal quest steps', execute_preparation_and_recovery)


def selection_with_preparation():
    scene, host, runner, module, reset = world()
    scene.at = Tile(3093, 3243)
    runner._records = [module.record]
    runner._order = ['cook']
    runner.running_id = None
    patch(engine, 'QUEST_DEFS', [Fake(record=module.record, module=lambda: module)])
    spy_on(engine.quests, 'status', returns='in_progress')
    spy_on(engine, 'evaluate', returns=Record({'id': 'cook', 'name': 'Cook', 'status': 'BLOCKED', 'reasons': ['skill']}))
    spy_on(runner, '_read_player_state', returns=Record({'quest_points': 0, 'completed_quests': set()}))
    spy_on(runner, '_read_item_snapshot', returns=Record({}))
    spy_on(runner, '_recover_area', impl=lambda picked, elig: result(False))
    spy_on(runner, '_read_stage', impl=lambda module: result((None, None)))
    spy_on(runner, '_prepare_candidate', impl=lambda id, module, snap: result(True))
    run_wait(runner.execute())
    expect(runner.running_id).to_be('cook')
    runner.running_id = None
    module.resume_at = lambda tile: True
    expect(engine.QUEST_DEFS[0].module()).to_be(module)
    expect(engine.QUEST_DEFS[0].module().resume_at(scene.at)).to_be(True)
    expect(engine.quests.status(module.record.name)).to_be('in_progress')
    run_wait(runner.execute())
    if not host.finished:
        raise AssertionError('owner selected: ' + str(runner.running_id) + ' notes: ' + str(host.notes))
    expect(host.finished[-1]).to_contain('cannot switch quests')
    module.resume_at = None
    runner.running_id = 'cook'
    host.skip = True
    run_wait(runner.execute())
    expect(runner.running_id).to_be(None)


test('a quest blocked by trainable skills enters preparation and a sealed owner prevents switching', selection_with_preparation)


def partner_progress():
    scene, host, runner, module, reset = world()
    clock = [0]
    spy_on(engine, '_now_ms', impl=lambda: clock[0])
    patch(Host, 'waiting_for_partner', lambda self, id: True)
    patch(Host, 'partner_progress_key', lambda self, id: 'stage-1')
    snap = QuestSnapshot(journal='in_progress', stage=1)
    step = quest_step('wait', reason='partner', cooperative=True)
    expect(runner._monitor_progress('cook', step, snap, False)).to_be(True)
    clock[0] += 599999
    expect(runner._monitor_progress('cook', step, snap, False)).to_be(True)
    expect(runner._recovery).to_be(None)
    clock[0] += 2
    expect(runner._monitor_progress('cook', step, snap, False)).to_be(None)
    expect(runner._recovery.mode).to_be('refresh')
    expect(runner.coordination_progress()).to_equal({})


test('cooperative waits reset ordinary watchdogs but recover after ten minutes without partner progress', partner_progress)

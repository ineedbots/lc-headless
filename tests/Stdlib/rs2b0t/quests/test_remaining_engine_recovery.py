"""Bank acknowledgements, bounded recovery and preparation for restarted quests."""

import rs2004.quests.engine.quest_engine as engine
import rs2004.quests.engine.resume_preparation as preparation
from rs2004.quests.engine.types import QuestModule, QuestSnapshot, quest_step
from rs2004.catalogs.record import Record
from rs2004.bank import bank
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004 import execution


def result(value):
    return value
    yield


def world():
    scene = Scene(Tile(3093, 3243, 0))
    import rs2004.traversal as travel
    spy_on(travel, 'nearest_bank', returns={'tile': {'x': 3093, 'z': 3243, 'level': 0}})
    host = Fake(log=scene.log, verbose=lambda: False, food_item=lambda: 'Trout', note_state=lambda *args: None,
                finish=lambda reason: scene.lines.append('FINISH: ' + reason))
    runner = engine.QuestEngine(host)
    spy_on(runner, '_refresh_bank_counts')
    module = QuestModule(record=Record({'id': 'imp', 'name': 'Imp Catcher', 'items': []}), tools=[])
    snap = QuestSnapshot(journal='in_progress', inv_ids={}, bank_known=True, free_slots=0, tile=scene.at)
    return scene, runner, module, snap


def resumed_caps():
    scene, runner, module, snap = world()
    plan = Record({'keep_ids': [333], 'caps': [Record({'id': 333, 'qty': 1})]})
    spy_on(preparation, 'resume_preparation', returns=plan)
    item = scene.item(333, 'Trout', count=3, actions=['Deposit-1'])
    item._fields['interact'] = lambda op: setattr(item, 'count', item.count - 1) or True
    spy_on(bank, 'backpack_ready', impl=lambda **kwargs: result(True))
    deposits = spy_on(engine, 'execute_step', impl=lambda *args: result(True))
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(True)
    expect(item.count).to_be(1)
    expect('imp' in runner._freshened).to_be(True)
    expect(deposits.calls[0][0].keep_ids).to_equal([333])
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)


test('resumed inventory preparation confirms each excess item was deposited', resumed_caps)


def preparation_failures(mode):
    def run():
        scene, runner, module, snap = world()
        behavior = mode
        spy_on(preparation, 'resume_preparation', returns=Record({'keep_ids': [333], 'caps': [Record({'id': 333, 'qty': 1})]}))
        scene.item(333, 'Trout', count=3, actions=[] if mode == 'no-op' else ['Deposit-1'])
        spy_on(bank, 'backpack_ready', impl=lambda **kwargs: result(behavior != 'not-ready'))
        spy_on(engine, 'execute_step', impl=lambda *args: result(behavior != 'deposit'))
        runner.running_id = 'imp'
        for attempt in range(engine.FRESH_GIVE_UP):
            expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(True)
        expect('imp' in runner._blocked).to_be(True)
        expect(runner.running_id).to_be(None)
        expect('imp' in runner._freshened).to_be(False)
    return run


for mode in ['deposit', 'not-ready', 'no-op', 'no-change']:
    test('resumed preparation blocks after bounded failed ' + mode, preparation_failures(mode))


def preparation_guards():
    scene, runner, module, snap = world()
    spy_on(preparation, 'resume_preparation', returns=None)
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)
    runner._freshened.clear()
    spy_on(preparation, 'resume_preparation', returns=Record({'keep_ids': [], 'caps': []}))
    snap.tile = None
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)
    snap.tile = scene.at
    scene.fighting = True
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)
    scene.fighting = False
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, [], quest_step('deposit', keep=[])))).to_be(False)
    snap.journal = 'not_started'
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)


test('resumed preparation yields to combat, the current deposit and unread locations', preparation_guards)


def recovery_and_retreat():
    scene, runner, module, snap = world()
    module.recover = lambda tile: quest_step('custom', name='leave pocket', run=lambda log: result(True))
    definition = Fake(record=module.record, module=lambda: module)
    patch(engine, 'QUEST_DEFS', [definition])
    spy_on(engine, 'queue_rows', returns=[])
    outcome = spy_on(engine, 'execute_step', impl=lambda *args: result(False))
    for attempt in range(engine.RETREAT_GIVE_UP):
        expect(run_wait(runner._recover_area(set(), {}))).to_be(True)
    expect(scene.logged('FINISH: could not recover')).to_be(True)
    outcome.mock_implementation(lambda *args: result(True))
    expect(run_wait(runner._recover_area(set(), {}))).to_be(True)
    expect(runner._recovery_tries).to_equal({})
    module.recover = None
    expect(run_wait(runner._recover_area(set(), {}))).to_be(False)
    scene.at = None
    expect(run_wait(runner._recover_area(set(), {}))).to_be(False)
    runner._retreat_tries['imp'] = engine.RETREAT_GIVE_UP
    expect(run_wait(runner._retreat_to_bank(module, 'imp', []))).to_be(False)
    expect(scene.logged('FINISH: could not leave')).to_be(True)


test('finished-area recovery retries only to its limit and a failed retreat stops the queue', recovery_and_retreat)


def bank_detours():
    import rs2004.traversal as travel
    scene, runner, module, snap = world()
    walked = spy_on(travel.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
    spy_on(preparation, 'resume_preparation', returns=Record({'keep_ids': [], 'caps': []}))
    spy_on(engine, 'execute_step', impl=lambda *args: result(True))
    snap.tile = Tile(3200, 3400, 0)
    destination = {'tile': {'x': 3185, 'z': 3436, 'level': 0}}
    spy_on(travel, 'nearest_walkable_bank', returns=destination)
    spy_on(travel, 'bank_cost_for_navigator', returns=lambda *args: 0)
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(True)
    expect('imp' in runner._freshened).to_be(True)
    runner._freshened.clear()
    spy_on(travel, 'nearest_walkable_bank', returns=None)
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(True)
    expect('imp' in runner._freshened).to_be(False)
    snap.tile = Tile(2500, 3300, 0)
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, []))).to_be(False)
    expect(run_wait(runner._prepare_resume(module, 'imp', snap, [], quest_step('withdraw', items=[], bank=scene.at)))).to_be(True)


test('resumed inventory uses a reachable mainland bank and avoids remote detours', bank_detours)

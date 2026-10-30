"""Exercise Druidic Ritual and Monk's Friend through the runtime facades."""
import _core
import rs2004.quests.defs.druidicritual as ritual
import rs2004.quests.defs.monksfriend as monk
from rs2004 import execution
from rs2004.execution import Ticks
from rs2004.catalogs.tasks import sustain
from rs2004.game import reader
from rs2004.tabs import quests
from rs2004.quests.defs import def_by_id, QUEST_DEFS
from rs2004.quests.engine.types import QuestModule, QuestSnapshot
from rs2004.quests.exec.steps import execute_step
from rs2004.bank import bank
from rs2004.dialogue import modals
import rs2004.quests.exec.steps as steps


def instant_result(value):
    return value
    yield


def journal_case(id, line, stage):
    def run():
        text = line
        closed = []
        def journal(name):
            yield from execution.delay_ticks(1)
            return [text]
        spy_on(quests, 'status', returns='in_progress')
        spy_on(quests, 'journal', impl=journal)
        spy_on(reader, 'modals', returns=Fake(main=123))
        spy_on(_core, 'close_interfaces', impl=lambda: closed.append(True))
        module = def_by_id(id)
        expect(isinstance(module, QuestModule)).to_be(True)
        expect(run_wait(module.read_stage())).to_be(stage)
        expect(closed).to_equal([True])
    return run


test('Druidic Ritual reads the journal and closes its main modal', journal_case('druid',
     '@dre@Sanfew@dbl@ told me for the ritual they would need raw meats', 2))
test("Monk's Friend reads the journal and closes its main modal", journal_case('drunkmonk',
     '@dbl@He needs some @dre@wood@dbl@ for his cart', 50))


def list_statuses():
    for module, start, complete in [[ritual.druidicritual, 0, 4], [monk.monksfriend, 0, 80]]:
        for status, expected in [['unknown', None], ['not_started', start], ['complete', complete]]:
            spy_on(quests, 'status', returns=status)
            spy_on(quests, 'journal', impl=lambda name: fail('stage reader opened an unnecessary journal'))
            expect(run_wait(module.read_stage())).to_be(expected)


test('stage readers use list status before opening a journal', list_statuses)


def queue_wiring():
    for id in ['druid', 'drunkmonk']:
        matching = [d for d in QUEST_DEFS if d.record.id == id]
        expect(len(matching)).to_be(1)
        expect(matching[0].module()).to_be(def_by_id(id))


test('both members quests load through the AIOQuester registry', queue_wiring)


def withdrawal_case(module, snap, expected):
    def run():
        quest_module = module
        snapshot = snap
        calls = []
        def withdraw(name, qty):
            calls.append([name, qty])
            yield from execution.delay_ticks(1)
            return True
        spy_on(steps, 'open_bank_leg', impl=lambda message, tile, log: instant_result(True))
        spy_on(bank, 'withdraw_x', impl=withdraw)
        spy_on(modals, 'close', impl=instant_ticks)
        step = quest_module.decide(snapshot)
        expect(step.kind).to_be('withdraw')
        expect(run_wait(execute_step(step, [], lambda message: None))).to_be(True)
        expect(calls).to_equal(expected)
    return run


test('ritual bank recovery runs through the real withdrawal executor', withdrawal_case(ritual.druidicritual,
     QuestSnapshot(journal='in_progress', stage=2, bank_known=True, bank={'enchanted bear': 1}),
     [['Enchanted bear', 1]]))
test('monk water recovery runs through the real withdrawal executor', withdrawal_case(monk.monksfriend,
     QuestSnapshot(journal='in_progress', stage=40, bank_known=True, bank={'jug of water': 1}),
     [['Jug of water', 1]]))


def jug_wait():
    calls = []
    def use(item, loc, prefer, expect, log):
        calls.append([item, loc.id])
        yield from execution.delay_ticks(1)
        return True
    spy_on(monk, 'use_on_loc', impl=use)
    expect(run_wait(monk.fill_jug(lambda message: None))).to_be(True)
    expect(calls).to_equal([[1935, 873]])


test('filling the jug drives the use-on generator to its result', jug_wait)


def cauldron_entry():
    calls = []
    def walk(dest, radius, hops, log):
        calls.append(dest)
        yield from execution.delay_ticks(1)
        return True
    spy_on(ritual.game, 'tile', returns=Tile(3220, 3220))
    spy_on(ritual, 'walk_with_hops', impl=walk)
    expect(run_wait(ritual.enter_cauldron_room(lambda message: None))).to_be(False)
    expect(calls).to_equal([ritual.CAULDRON_DOOR_OUTSIDE])


test('the first cauldron pass drives the dungeon hop before opening the door', cauldron_entry)


def combat_upkeep():
    state = {'ticks': 0, 'upkeep': 0}
    def hook():
        state['upkeep'] += 1
        yield from execution.delay_ticks(1)
    def tick(count):
        state['ticks'] += count
        yield Ticks(count)
    stub(sustain, hook=hook)
    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(_core, 'step_time', impl=lambda: state['ticks'] * 600)
    expect(run_wait(ritual.wait_with_upkeep(lambda: state['ticks'] >= 4, 120000))).to_be(True)
    expect(state['upkeep']).to_be(2)
    state['ticks'] = 0
    expect(run_wait(ritual.wait_with_upkeep(lambda: False, 1000))).to_be(False)


test('long ritual waits pump upkeep and stop at their deadline', combat_upkeep)


def ritual_recovers_attack():
    state = {'ticks': 0, 'attacks': 0}
    def attack(op):
        assert op == 'Attack'
        state['attacks'] += 1
        return True
    target = Fake(index=7, valid=lambda: state['ticks'] < 2, interact=attack)
    spy_on(ritual.game, 'facing', returns=None)
    def tick(count):
        state['ticks'] += count
        yield
    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(sustain, 'run', impl=instant_ticks)
    expect(run_wait(ritual.wait_with_upkeep(lambda: not target.valid(), 120000, target))).to_be(True)
    expect(state['attacks']).to_be(2)


test('ritual combat reissues a cleared attack until the tracked NPC disappears', ritual_recovers_attack)

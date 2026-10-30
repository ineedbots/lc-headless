"""Exercise evidence transformations and repeatable poison interviews."""
import rs2004.quests.defs.murder.evidence as evidence
import rs2004.quests.defs.murder.poison as poison
from rs2004.quests.defs.murder.areas import MURDER_OBJ as OBJ, SUSPECTS
from rs2004.quests.engine.types import QuestProgress
from rs2004 import execution


def result(value):
    return value
    yield


def fingerprint_case(killer):
    def run():
        matching_print = killer
        state = {'pack': {OBJ.POT: 3}, 'pending': None, 'searches': []}
        pack = state['pack']
        spy_on(evidence, 'held_id', impl=lambda id: pack.get(id, 0))
        spy_on(evidence.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(execution, 'delay_ticks', impl=instant_ticks)
        def take(op):
            assert op == 'Take'
            state['pending'] = ('take', OBJ.DAGGER, 0)
            return True
        dagger = Fake(id=OBJ.DAGGER, distance=lambda: 1, interact=take)
        spy_on(evidence.ground_items, 'query', impl=querying(lambda: [dagger]))
        def use(source, target):
            assert pack.get(source, 0) > 0 and pack.get(target.id, 0) > 0
            state['pending'] = ('use', source, target.id)
            return True
        def item(id):
            apply = use
            return Fake(id=id, use_on=lambda target: apply(id, target))
        spy_on(evidence.inventory, 'items', impl=lambda: [item(id) for id in pack if pack[id] > 0])
        def drive(expectation, prefer, log, timeout):
            kind, source, target = state['pending']
            if kind == 'take':
                pack[source] = 1
            elif source == OBJ.POT_FLOUR:
                pack[source] -= 1
                pack[OBJ.POT] = pack.get(OBJ.POT, 0) + 1
                pack[target] -= 1
                pack[OBJ.DAGGER_DUST if target == OBJ.DAGGER else target + 1] = 1
            elif source == OBJ.FLYPAPER:
                pack[source] -= 1
                pack[target] -= 1
                prints = [s.print for s in SUSPECTS if s.dust == target]
                pack[OBJ.UNKNOWN_PRINT if target == OBJ.DAGGER_DUST else prints[0]] = 1
            else:
                assert source == OBJ.UNKNOWN_PRINT
                pack[target] -= 1
                if target == matching_print:
                    pack[OBJ.KILLERS_PRINT] = 1
            state['pending'] = None
            assert expectation(), 'the item change must satisfy the real completion predicate'
            return True
            yield
        spy_on(evidence, 'drive_until', impl=drive)
        def prompt(step, log):
            if step.id == evidence.MURDER_LOC.SACKS:
                pack[OBJ.FLYPAPER] = pack.get(OBJ.FLYPAPER, 0) + 1
            elif step.id == evidence.MURDER_LOC.FLOUR_BARREL:
                pack[OBJ.POT] -= 1
                pack[OBJ.POT_FLOUR] = pack.get(OBJ.POT_FLOUR, 0) + 1
            else:
                suspect = [s for s in SUSPECTS if s.barrel.id == step.id][0]
                state['searches'].append(suspect.print)
                pack[suspect.silver] = 1
            assert step.expect()
            return True
            yield
        spy_on(evidence, 'prompt_loc', impl=prompt)
        order = SUSPECTS[:3]
        expect(run_wait(evidence.take_prints(order, lambda message: None))).to_be(killer is not None)
        expected = [s.print for s in order]
        if killer is not None:
            expected = expected[:expected.index(killer) + 1]
        expect(state['searches']).to_equal(expected)
        expect(pack[OBJ.UNKNOWN_PRINT]).to_be(1)
        expect(pack.get(OBJ.KILLERS_PRINT, 0)).to_be(1 if killer is not None else 0)
        before = len(state['searches'])
        if killer is not None:
            expect(run_wait(evidence.take_prints(order, lambda message: None))).to_be(True)
            expect(len(state['searches'])).to_be(before)
    return run


test('Murder lifts dagger and suspect prints, dismisses mismatches and stops at the matching killer', fingerprint_case(SUSPECTS[1].print))
test('Murder reports an exhausted fingerprint search without inventing a match', fingerprint_case(None))


def reach_retry(success_at):
    def run():
        goal = success_at
        state = {'calls': 0}
        def prompt(step, log):
            state['calls'] += 1
            return state['calls'] == goal
            yield
        spy_on(evidence, 'prompt_loc', impl=prompt)
        spy_on(evidence, 'held_id', returns=0)
        expect(run_wait(evidence.take_thread(lambda message: None))).to_be(success_at <= 3)
        expect(state['calls']).to_be(min(success_at, 3))
    return run


test('Murder retries an approach before investigating the window', reach_retry(2))
test('Murder bounds retries when a window cannot be reached', reach_retry(4))


def missing_supplies():
    spy_on(evidence, 'held_id', returns=0)
    spy_on(evidence.inventory, 'items', returns=[])
    log = lambda message: None
    expect(run_wait(evidence.fill_pot(log))).to_be(False)
    expect(run_wait(evidence.use_held(OBJ.FLYPAPER, OBJ.DAGGER_DUST, lambda: True, log))).to_be(False)
    spy_on(evidence, 'prompt_loc', impl=lambda *args: result(False))
    expect(run_wait(evidence.take_flypaper(log))).to_be(False)
    expect(run_wait(evidence.lift_print(OBJ.DAGGER_DUST, OBJ.UNKNOWN_PRINT, log))).to_be(False)
    expect(run_wait(evidence.flour_onto(OBJ.DAGGER, OBJ.DAGGER_DUST, log))).to_be(False)


test('Murder refuses to dust or lift without the required supplies', missing_supplies)


def poison_sweep(proved_at):
    def run():
        goal = proved_at
        state = {'interview': None, 'investigations': 0}
        calls = []
        spy_on(poison, 'goto_npc', impl=lambda stop, hops, log: result(True))
        def talk(name, prefer, log):
            calls.append(name)
            state['interview'] = name
            return True
            yield
        spy_on(poison, 'talk_through', impl=talk)
        spy_on(poison.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(poison, 'settle_scene', impl=instant_ticks)
        spy_on(execution, 'delay_until', impl=instant_until)
        spy_on(poison.chat_dialog, 'is_open', returns=True)
        def investigate(op):
            assert op == 'Investigate'
            state['investigations'] += 1
            return True
        def objects():
            suspect = [s for s in SUSPECTS if s.stop.npc == state['interview']][0]
            return [Fake(id=suspect.poison.id, actions=lambda: ['Investigate'], distance=lambda: 1, interact=investigate)]
        spy_on(poison.locs, 'query', impl=querying(objects))
        spy_on(poison, 'drive_choice', impl=lambda *args: result(True))
        def progress():
            flags = [poison.POISON_PROVED] if state['investigations'] == goal else []
            return result(QuestProgress(stage=1, flags=flags))
        spy_on(poison, 'read_murder_progress', impl=progress)
        expect(run_wait(poison.prove_poison(SUSPECTS[:3], lambda message: None))).to_be(proved_at <= 3)
        expect(calls).to_equal(['Poison Salesman'] + [s.stop.npc for s in SUSPECTS[:min(proved_at, 3)]])
        expect(state['investigations']).to_be(min(proved_at, 3))
    return run


test('Murder interviews and investigates each suspect until the journal proves the poison lie', poison_sweep(2))
test('Murder leaves poison unproved when none of the suspects advance the journal', poison_sweep(4))

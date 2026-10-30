"""Test contest entry, exact pipe positioning, catches and recovery hand-ins."""
import rs2004.quests.defs.fishingcontest.contest as contest
from rs2004 import execution


def result(value):
    return value
    yield


def gate_crossing(entering):
    def run():
        state = {'tile': contest.FC_TILE.GATE_OUTSIDE if entering else contest.FC_TILE.PIPE_STAND}
        destination = contest.FC_TILE.PIPE_STAND if entering else contest.FC_TILE.GATE_OUTSIDE
        inbound = entering
        spy_on(contest.game, 'tile', impl=lambda: state['tile'])
        spy_on(contest.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(contest, 'settle_scene', impl=instant_ticks)
        clicks = []
        gate = Fake(id=contest.FC_LOC.GATE_LEFT, actions=lambda: ['Open'], distance=lambda: 1, interact=lambda op: clicks.append(op) or True)
        spy_on(contest.locs, 'query', impl=querying(lambda: [gate]))
        def drive(predicate, prefer, log, timeout):
            assert not predicate()
            expect(prefer).to_equal([] if inbound else [contest.QUIT_CONTEST])
            state['tile'] = destination
            return predicate()
            yield
        spy_on(contest, 'drive_until', impl=drive)
        run_leg = contest.enter_compound if entering else contest.leave_compound
        expect(run_wait(run_leg(lambda message: None))).to_be(True)
        expect(run_wait(run_leg(lambda message: None))).to_be(True)
        expect(clicks).to_equal(['Open'])
    return run


test('Fishing Contest enters by driving the gate dialogue and skips an already-completed crossing', gate_crossing(True))
test('Fishing Contest exit accepts the reset option and skips an already-completed crossing', gate_crossing(False))


def garlic_underfoot():
    state = {'garlic': 1}
    spy_on(contest, 'enter_compound', impl=lambda log: result(True))
    spy_on(contest.game, 'tile', returns=contest.FC_TILE.PIPE_STAND)
    walks = []
    def walk(tile, **options):
        walks.append(options['radius'])
        return True
        yield
    spy_on(contest.traversal, 'walk_resilient', impl=walk)
    spy_on(contest, 'settle_scene', impl=instant_ticks)
    wrong = Fake(id=contest.FC_LOC.WALL_PIPE, tile=lambda: contest.FC_TILE.PIPE_STAND.translate(1, 0))
    pipe = Fake(id=contest.FC_LOC.WALL_PIPE, tile=lambda: contest.FC_TILE.PIPE_STAND)
    spy_on(contest.locs, 'query', impl=querying(lambda: [wrong, pipe]))
    def use(target):
        assert target is pipe
        state['garlic'] = 0
        return True
    spy_on(contest.inventory, 'items', returns=[Fake(id=contest.FC_ID.GARLIC, use_on=use)])
    spy_on(contest, 'held_id', impl=lambda id: state['garlic'])
    spy_on(contest, 'drive_until', impl=lambda predicate, *args: result(predicate()))
    expect(run_wait(contest.stash_garlic(lambda message: None))).to_be(True)
    expect(walks).to_equal([0])


test('Fishing Contest stashes garlic in the pipe underfoot rather than the adjacent wall decoration', garlic_underfoot)


def fishing_catch(trophy, accepted):
    def run():
        state = {'fish': 2, 'trophy': 0}
        award = trophy
        click_ok = accepted
        spy_on(contest, 'enter_compound', impl=lambda log: result(True))
        spy_on(contest.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(contest, 'settle_scene', impl=instant_ticks)
        def fish(op):
            assert op == 'Fish'
            if click_ok:
                state['fish'] = 0 if award else 3
                state['trophy'] = 1 if award else 0
            return click_ok
        spot = Fake(id=contest.FC_NPC.PIPES_SPOT, actions=lambda: ['Fish'], distance=lambda: 1, interact=fish)
        spy_on(contest.npcs, 'query', impl=querying(lambda: [spot]))
        spy_on(contest, 'held_id', impl=lambda id: state['fish'] if id == contest.FC_ID.RAW_GIANT_CARP else state['trophy'])
        spy_on(contest, 'drive_until', impl=lambda predicate, *args: result(predicate()))
        expect(run_wait(contest.fish_at_pipes(lambda message: None))).to_be(accepted)
    return run


test('Fishing Contest confirms an increased giant carp count', fishing_catch(False, True))
test('Fishing Contest accepts a trophy when the third catch consumes the carp', fishing_catch(True, True))
test('Fishing Contest stops when the fishing click is refused', fishing_catch(False, False))


def recover_and_deliver():
    state = {'sardines': 2, 'trophy': 0}
    log = lambda message: None
    spy_on(contest, 'enter_compound', impl=lambda log: result(True))
    spy_on(contest, 'held_id', impl=lambda id: state['sardines'] if id == contest.FC_ID.RAW_SARDINE else state['trophy'])
    spy_on(contest, 'walk_and_talk', impl=lambda *args: result(True))
    expect(run_wait(contest.hand_over_catch(log))).to_be(False)
    def report(stop, log):
        assert stop.npc == 'Bonzo'
        state['sardines'] = 0
        state['trophy'] = 1
        return True
        yield
    spy_on(contest, 'walk_and_talk', impl=report)
    expect(run_wait(contest.hand_over_catch(log))).to_be(True)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(contest.claim_spare_trophy(log))).to_be(True)
    order = []
    def leave(log):
        order.append('leave')
        return True
        yield
    def deliver(stop, log):
        order.append('report')
        expect(stop.prefer).to_equal(list(contest.DWARF_REPORT.prefer))
        return True
        yield
    spy_on(contest, 'leave_compound', impl=leave)
    spy_on(contest.game, 'tile', returns=contest.FC_TILE.GATE_OUTSIDE)
    spy_on(contest, 'walk_and_talk', impl=deliver)
    expect(run_wait(contest.deliver_trophy(log))).to_be(True)
    expect(order).to_equal(['leave', 'report'])


test('Fishing Contest verifies losing fish are gone, recovers a trophy and exits before the dwarf hand-in', recover_and_deliver)

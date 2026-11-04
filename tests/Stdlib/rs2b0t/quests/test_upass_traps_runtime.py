"""Underground Pass trap crossings, journal timing and fixed railing routes."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.navigation import navigator, reachability
from rs2004.quests.defs.upass import grid, railings, stall
from rs2004.quests.defs.upass.areas import GRID_ZONE, UP_LOC, UP_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def move(scene, at):
    def effect(*args):
        scene.at = at
        return True
    return effect


def grid_pit():
    scene = Scene(UP_TILE.GRID_APPROACH)
    spy_on(grid, 'travel_to', impl=scene._walk)
    expect(run_wait(grid.to_approach(scene.log))).to_be(True)
    scene.at = Tile(GRID_ZONE.min_x, GRID_ZONE.min_z, 0)
    expect(grid.in_grid()).to_be(True)
    scene.walk_ok = False
    expect(run_wait(grid.to_approach(scene.log))).to_be(False)
    expect(run_wait(grid.cross_grid(scene.log))).to_be(False)
    scene.at = Tile(2400, grid.PIT.min_z, 0)
    expect(run_wait(grid.climb_out_of_pit(scene.log))).to_be(False)
    expect(run_wait(grid.to_approach(scene.log))).to_be(False)
    scene.loc('Rocks', ['Climb'], id=UP_LOC.GRID_HANDHOLDS,
              effect=move(scene, UP_TILE.GRID_APPROACH))
    expect(run_wait(grid.climb_out_of_pit(scene.log))).to_be(True)
    expect(grid.in_pit()).to_be(False)
    expect(run_wait(grid.climb_out_of_pit(scene.log))).to_be(True)
    scene.at = Tile(GRID_ZONE.min_x - 1, GRID_ZONE.min_z, 0)
    expect(grid.at_lever()).to_be(True)
    expect(run_wait(grid.to_approach(scene.log))).to_be(True)
    expect(run_wait(grid.pull_through(scene.log))).to_be(False)
    scene.loc('Lever', ['Pull'], id=UP_LOC.PORTCULLIS_LEVER,
              effect=move(scene, Tile(UP_TILE.GRID_APPROACH.x - 30, UP_TILE.GRID_APPROACH.z, 0)))
    expect(run_wait(grid.cross_grid(scene.log))).to_be(True)
    expect(grid.past_grid()).to_be(True)
    expect(run_wait(grid.to_approach(scene.log))).to_be(True)
    scene.at = UP_TILE.GRID_APPROACH
    scene.walk_ok = True
    crossing = spy_on(grid, 'stalled_crossing', impl=answer(False))
    expect(run_wait(grid.cross_grid(scene.log))).to_be(False)
    crossing.mock_implementation(answer(True))
    expect(run_wait(grid.cross_grid(scene.log))).to_be(True)


test('grid pits recover to the approach and the lever must move the player through the portcullis', grid_pit)


def railing_ops():
    scene = Scene(railings.TO_RAILINGS[0].stand)
    spy_on(navigator, 'find_path', returns=Fake(ok=True))
    reachable = spy_on(reachability, 'can_reach', returns=True)
    expect(railings.outstanding_crossing()).to_be_null()
    expect(run_wait(railings.take_next_crossing(scene.log))).to_be(False)
    for step in railings.TO_RAILINGS:
        scene.locs = []
        scene.walk_ok = False
        expect(run_wait(railings.take(step, scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(railings.take(step, scene.log))).to_be(False)
        scene.loc('Crossing', [step.op], id=step.loc, tile=step.at, effect=lambda op: False)
        expect(run_wait(railings.take(step, scene.log))).to_be(False)
        scene.locs = []
        scene.loc('Crossing', [step.op], id=step.loc, tile=step.at, effect=move(scene, step.lands))
        if step.item:
            scene.item(step.item.id, step.item.name, on_use=move(scene, step.lands))
        verdict = spy_on(railings, 'verdict_since', returns='refused')
        expect(run_wait(railings.take(step, scene.log))).to_be(False)
        verdict.mock_return_value('crossing')
        expect(run_wait(railings.take(step, scene.log))).to_be(True)
        expect(scene.at).to_equal(step.lands)
    expect(run_wait(railings.reach_loose_railings(scene.log))).to_be(True)
    path = spy_on(railings, 'can_walk_to', returns=False)
    expect(run_wait(railings.reach_loose_railings(scene.log))).to_be(False)
    first = railings.TO_RAILINGS[0]
    path.mock_implementation(lambda tile: tile == first.stand)
    take = spy_on(railings, 'take', impl=answer(False))
    expect(run_wait(railings.reach_loose_railings(scene.log))).to_be(False)
    reachable.mock_implementation(lambda tile: tile == first.stand)
    take.mock_implementation(answer(True))
    expect(run_wait(railings.take_next_crossing(scene.log))).to_be(True)
    done = []

    def crossing(step, log):
        done.append(step.lands)
        return True
        yield

    take.mock_implementation(crossing)
    path.mock_implementation(lambda tile: tile == first.stand or tile in done)
    expect(run_wait(railings.reach_loose_railings(scene.log))).to_be(True)
    expect(len(done)).to_be(len(railings.TO_RAILINGS))


test('railings use exact named locs, inventory tools and crossing verdicts before advancing', railing_ops)


def journal_walk():
    scene = Scene(Tile(2400, 9600, 0))
    opts = Record({'what': 'lever', 'send': answer(False), 'arrived': lambda: False, 'log': scene.log})
    expect(run_wait(stall.stalled_approach(opts))).to_be(False)
    opts.send = answer(True)
    expect(run_wait(stall.stalled_approach(opts))).to_be(False)

    def send():
        scene.later(move(scene, Tile(scene.at.x + 1, scene.at.z, 0)))
        return True
        yield

    opts.send = send
    press = spy_on(stall, 'press_journal', returns=False)
    expect(run_wait(stall.stalled_approach(opts))).to_be(False)
    press.mock_return_value(True)
    hold_impl = stall.hold_journal_walk
    hold = spy_on(stall, 'hold_journal_walk', impl=answer(True))
    expect(run_wait(stall.stalled_approach(opts))).to_be(True)

    def broken(*args):
        raise RuntimeError('interrupted modal')
        yield

    hold.mock_implementation(broken)
    scene.main_modal = 123
    try:
        run_wait(stall.stalled_approach(opts))
        expect(False).to_be(True)
    except RuntimeError:
        expect(scene.main_modal).to_be(-1)
    hold.mock_implementation(hold_impl)
    opts.abort = lambda: True
    expect(run_wait(stall.hold_journal_walk(opts, lambda: False, 10000, scene.log))).to_be(False)
    opts.abort = None
    scene.main_modal = 123
    expect(run_wait(stall.hold_journal_walk(opts, lambda: False, 10000, scene.log))).to_be(False)
    expect(scene.logged('walk stopped')).to_be(True)
    scene.main_modal = -1
    expect(run_wait(stall.hold_journal_walk(opts, lambda: False, 1000, scene.log))).to_be(False)
    scene.main_modal = 123
    scene.later(lambda: setattr(scene, 'main_modal', -1))
    expect(run_wait(stall.hold_journal_walk(opts, lambda: False, 3000, scene.log))).to_be(False)
    expect(run_wait(stall.hold_journal_walk(opts, lambda: True, 1000, scene.log))).to_be(True)


test('journal timing distinguishes stationary clicks, movement, idle modals, aborts and interruptions', journal_walk)


def journal_journey():
    scene = Scene(Tile(2400, 9600, 0))
    goal = Record({'what': 'goal', 'send': answer(False), 'arrived': lambda: False, 'in_range': lambda: True})
    opts = Record({'goal': goal, 'next_stone': lambda: None, 'log': scene.log, 'legs': 2})
    expect(run_wait(stall.finish_goal(goal, scene.log))).to_be(False)
    goal.send = answer(True)
    spy_on(stall, 'press_journal', returns=True)
    expect(run_wait(stall.finish_goal(goal, scene.log))).to_be(False)
    approach_impl = stall.stalled_approach
    approach = spy_on(stall, 'stalled_approach', impl=answer(False))
    finish = spy_on(stall, 'finish_goal', impl=answer(False))
    expect(run_wait(stall.stalled_journey(opts))).to_be(False)
    opts.next_stone = lambda: goal
    expect(run_wait(stall.stalled_journey(opts))).to_be(False)
    finish.mock_implementation(answer(True))
    expect(run_wait(stall.stalled_journey(opts))).to_be(True)
    approach.mock_implementation(answer(True))
    expect(run_wait(stall.stalled_journey(opts))).to_be(True)
    goal.arrived = lambda: True
    expect(run_wait(stall.stalled_journey(opts))).to_be(True)
    goal.arrived = lambda: False

    def broken(*args):
        raise RuntimeError('interrupted journey')
        yield

    approach.mock_implementation(broken)
    scene.main_modal = 123
    try:
        run_wait(stall.stalled_journey(opts))
        expect(False).to_be(True)
    except RuntimeError:
        expect(scene.main_modal).to_be(-1)
    approach.mock_implementation(approach_impl)
    expect(run_wait(stall.stalled_walk_to_loc(999, 'Pull', lambda: False, scene.log))).to_be(False)
    scene.loc('Lever', ['Pull'], id=999)
    expect(run_wait(stall.stalled_walk_to_loc(999, 'Pull', lambda: True, scene.log))).to_be(True)
    crossing = Record({'arrived': lambda: False, 'find': lambda: None, 'op': 'Pull',
                       'log': scene.log, 'recover': answer(False)})
    walk = spy_on(stall, 'stalled_walk', impl=answer(False))
    expect(run_wait(stall.stalled_crossing(crossing))).to_be(False)
    crossing.recover = answer(True)
    expect(run_wait(stall.stalled_crossing(crossing))).to_be(False)
    walk.mock_implementation(answer(True))
    expect(run_wait(stall.stalled_crossing(crossing))).to_be(True)


test('journal journeys retry final ops, release on exceptions and bound crossing recovery', journal_journey)

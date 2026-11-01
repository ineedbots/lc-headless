"""Ported from rs2b0t's test/api/ai/quests/upassGrid.test.ts (MIT, see thirdparty/rs2b0t), with the client faked through
spec.py's spies: a tile that walks one step a tick, and a modal that stops the lever's op."""

import _core
import math
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.quests.defs.upass.areas import past_grid_tile
from rs2004.quests.defs.upass.grid import cross_grid
from rs2004.quests.defs.upass.stall import stalled_approach, stalled_journey
from rs2004.tabs import quests

# Why: the journal blocks the lever op that moves the player through the portcullis.
GRID_APPROACH = Tile(2479, 9679, 0)
LEVER_STAND = Tile(2466, 9673, 0)
TICK_CAP = 500

sim = Record({})


def reset(at):
    sim.tile = at
    sim.modal = False
    sim.walking_to = None
    sim.pending_op = False
    sim.ticks = 0
    sim.pulls = 0
    sim.on_idle_tick = None


def sign(n):
    return 1 if n > 0 else (-1 if n < 0 else 0)


def step():
    sim.ticks += 1
    if sim.walking_to is not None:
        sim.tile = Tile(sim.tile.x + sign(sim.walking_to.x - sim.tile.x), sim.tile.z + sign(sim.walking_to.z - sim.tile.z), 0)
        if sim.tile.x == sim.walking_to.x and sim.tile.z == sim.walking_to.z:
            sim.walking_to = None
        return
    if sim.on_idle_tick is not None:
        sim.on_idle_tick()
        return
    if sim.pending_op and not sim.modal and sim.tile.x == LEVER_STAND.x and sim.tile.z == LEVER_STAND.z:
        sim.pending_op = False
        sim.pulls += 1
        sim.tile = Tile(sim.tile.x - 2, sim.tile.z + 4, 0)


def ticks(n=1):
    for i in range(n):
        if not (sim.ticks < TICK_CAP):
            break
        step()
    if False:
        yield


def until(cond, max_ticks):
    for i in range(max_ticks):
        if not (sim.ticks < TICK_CAP):
            break
        if cond():
            return True
        yield from ticks(1)
    return cond()


def until_ms(cond, timeout_ms=6000):
    return until(cond, math.ceil(timeout_ms / 600))


def press_journal(name):
    sim.modal = True
    return True


def close_modal():
    sim.modal = False
    return True


def walk_to_lever():
    sim.walking_to = LEVER_STAND
    sim.pending_op = True
    return True
    if False:
        yield


class Lever:
    id = 3337

    def interact(self, op):
        return run_wait(walk_to_lever())


class LeverQuery:
    def where(self, fn):
        return self

    def action(self, op):
        return self

    def within(self, radius):
        return self

    def nearest(self):
        return Lever()


def install():
    reset(GRID_APPROACH)
    spy_on(execution, 'delay_ticks', impl=ticks)
    spy_on(execution, 'delay_until', impl=until_ms)
    spy_on(execution, 'delay_until_ticks', impl=until)
    spy_on(game, 'tile', impl=lambda: sim.tile)
    spy_on(reader, 'modals', impl=lambda: Record({'main': (1 if sim.modal else -1), 'side': -1, 'chat': -1}))
    spy_on(quests, 'press_journal', impl=press_journal)
    spy_on(locs, 'query', impl=lambda: LeverQuery())
    patch(_core, 'close_interfaces', close_modal)
    patch(_core, 'step_time', lambda: sim.ticks * 600)


before_each(install)


def _fn1():
    def _fn2():
        reset(GRID_APPROACH)
        lines = []
        carried = yield from stalled_approach(Record({
            'send': walk_to_lever,
            'what': 'a script the modal will not let run',
            'arrived': lambda: sim.pulls > 0,
            'hold': True,
            'log': lambda m: lines.append(m),
        }))
        expect(carried).to_be(False)
        expect(sim.tile).to_equal(LEVER_STAND)
        expect([l for l in lines if ('never reached the far side' in l)]).to_equal([])
        expect(sim.ticks).to_be_less_than(30)
    test('stops when the walk does, rather than sitting out the timeout under a modal nothing can run', _fn2)


describe('a stalled walk whose oracle waits on a script', _fn1)


def _fn3():
    def _fn4():
        reset(Tile(LEVER_STAND.x + 4, LEVER_STAND.z, 0))
        lines = []

        # Why: the journal must close after walking before the goal op can run.
        def _fn5():
            if sim.pending_op and not sim.modal and sim.tile.x == LEVER_STAND.x and sim.tile.z == LEVER_STAND.z:
                sim.pending_op = False
                sim.pulls += 1
        sim.on_idle_tick = _fn5
        reached = yield from stalled_journey(Record({
            'goal': Record({'in_range': lambda: True, 'arrived': lambda: sim.pulls > 0, 'what': 'the Orb of light', 'send': walk_to_lever}),
            'next_stone': lambda: None,
            'log': lambda m: lines.append(m),
        }))
        expect(reached).to_be(True)
        expect(sim.pulls).to_be(1)
        expect(sim.modal).to_be(False)
        expect([l for l in lines if ('steps toward' in l)]).to_equal([])
        expect(sim.ticks).to_be_less_than(30)
    test('drops the journal at the goal and finishes it, rather than reporting nothing steps there', _fn4)


describe('a journey whose goal is an op script', _fn3)


def _fn6():
    def _fn7():
        reset(GRID_APPROACH)
        lines = []
        crossed = yield from cross_grid(lambda m: lines.append(m))
        expect(crossed).to_be(True)
        expect(past_grid_tile(sim.tile)).to_be(True)
        expect(sim.pulls).to_be(1)
        expect(sim.modal).to_be(False)
        expect([l for l in lines if ('never reached the far side' in l)]).to_equal([])
        expect([l for l in lines if ('recovering' in l)]).to_equal([])
        expect(sim.ticks).to_be_less_than(40)
    test('lets the lever fire and carries the player through, without waiting out the stall timeout', _fn7)


describe('the spiked grid crossing', _fn6)

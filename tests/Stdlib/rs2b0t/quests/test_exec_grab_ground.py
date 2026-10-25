"""rs2b0t's test/api/ai/quests/exec/grabGround.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004 import execution
from rs2004.entities import ground_items
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.engine.types import quest_step
from rs2004.quests.exec.steps import execute_step
from rs2004.traversal import traversal

ANCHOR = Tile(3227, 3300, 0)
FAR = Tile(3255, 3288, 0)

S = {}


class Egg:
    name = 'Egg'

    def distance(self):
        return 1

    def interact(self, action):
        expect(action).to_be('Take')
        S['takes'] += 1
        S['held'] += 1
        return True


class GroundQuery:
    def __init__(self, rows):
        self.rows = rows

    def name(self, *names):
        return GroundQuery([r for r in self.rows if r.name in names])

    def within(self, distance):
        return GroundQuery([r for r in self.rows if r.distance() <= distance])

    def nearest(self):
        rows = sorted(self.rows, key=lambda r: r.distance())
        return rows[0] if len(rows) > 0 else None


def answered(condition, ms=0):
    return condition()
    yield


def waited(n=1):
    S['waits'] += 1
    if False:
        yield


def walked(*args, **kwargs):
    S['walks'] += 1
    S['here'] = ANCHOR
    return True
    yield


def _setup():
    S['held'] = 0
    S['here'] = FAR
    S['ground'] = []
    S['walks'] = 0
    S['waits'] = 0
    S['takes'] = 0
    spy_on(execution, 'delay_until', impl=answered)
    spy_on(execution, 'delay_ticks', impl=waited)
    spy_on(game, 'tile', impl=lambda: S['here'])
    spy_on(inventory, 'count', impl=lambda name: S['held'] if name.lower() == 'egg' else 0)
    spy_on(traversal, 'walk_resilient', impl=walked)
    spy_on(ground_items, 'query', impl=lambda: GroundQuery(list(S['ground'])))


before_each(_setup)


def quiet(m):
    pass


def grab(wait_if_missing=False):
    result = yield from execute_step(quest_step('grab_ground', item='Egg', anchor=ANCHOR, wait_if_missing=wait_if_missing), [], quiet)
    return result


def later_egg():
    S['queries'] += 1
    return GroundQuery([S['item']] if S['queries'] >= 2 else [])


def _fn1():
    def _fn2():
        S['here'] = ANCHOR
        S['ground'] = [Egg()]
        grabbed = yield from grab()
        expect(grabbed).to_be(True)
        expect(S['takes']).to_be(1)
        expect(S['walks']).to_be(0)
        expect(S['held']).to_be(1)
    test('Takes a visible egg without walking', _fn2)

    def _fn3():
        grabbed = yield from grab()
        expect(grabbed).to_be(False)
        expect(S['walks']).to_be(1)
        expect(S['takes']).to_be(0)
        expect(S['held']).to_be(0)
    test('arrival with an empty pen is not success', _fn3)

    def _fn4():
        S['item'] = Egg()
        S['queries'] = 0
        spy_on(ground_items, 'query', impl=later_egg)
        grabbed = yield from grab()
        expect(grabbed).to_be(True)
        expect(S['walks']).to_be(1)
        expect(S['takes']).to_be(1)
        expect(S['held']).to_be(1)
    test('Takes after the walk if the egg is there on re-query', _fn4)

    def _fn5():
        grabbed = yield from grab(True)
        expect(grabbed).to_be(False)
        expect(S['walks']).to_be(1)
        expect(S['waits']).to_be(1)
    test('waitIfMissing delays when the pen is still empty', _fn5)


describe('grabGround', _fn1)

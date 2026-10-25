"""rs2b0t's test/api/ai/quests/exec/useOnLoc.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.exec.prompts import use_on_loc
from rs2004.traversal import traversal

SPINDLE = 'Clock spindle'
STAND = Tile(2569, 3243, 0)

S = {}


class FakeLoc:
    def __init__(self, id, name):
        self.id = id
        self.name = name


# Why: all four Clock Tower spindles render "Clock spindle" and stand within three tiles, so the decoy is always the
# nearer match.
SCENE = [FakeLoc(28, SPINDLE), FakeLoc(29, SPINDLE), FakeLoc(26, SPINDLE)]


class LocChain:
    def __init__(self, rows):
        self.rows = rows

    def name(self, *names):
        return LocChain([l for l in self.rows if l.name in names])

    def within(self, *args):
        return self

    def where(self, pred):
        return LocChain([l for l in self.rows if pred(l)])

    def nearest(self):
        return self.rows[0] if len(self.rows) > 0 else None


class Item:
    id = 23
    count = 1

    def use_on(self, target):
        S['used'] = target
        return True


def ticks(n=1):
    if False:
        yield


def answered(fn, ms=0):
    return fn()
    yield


def walked(*args, **kwargs):
    return True
    yield


def quiet(m):
    pass


def _setup():
    S['used'] = None
    spy_on(execution, 'delay_ticks', impl=ticks)
    spy_on(execution, 'delay_until', impl=answered)
    spy_on(traversal, 'walk_resilient', impl=walked)
    spy_on(locs, 'query', impl=lambda: LocChain(SCENE))
    spy_on(inventory, 'items', impl=lambda: [Item()])


before_each(_setup)


def _fn1():
    ok = yield from use_on_loc(23, Record({'name': SPINDLE, 'near': STAND, 'id': 29}), [], lambda: S['used'] is not None, quiet)
    expect(ok).to_be(True)
    expect(S['used'].id).to_be(29)


test('uses the item on the spindle with the named loc id, not the nearest same-named decoy', _fn1)


def _fn2():
    ok = yield from use_on_loc(23, Record({'name': SPINDLE, 'near': STAND}), [], lambda: S['used'] is not None, quiet)
    expect(ok).to_be(True)
    expect(S['used'].id).to_be(28)


test('falls back to the nearest match when no loc id is given', _fn2)

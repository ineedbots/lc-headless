"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/dragonslayerMazeRun.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.dragonslayer.areas import DS_ID
from rs2004.quests.defs.dragonslayer.maze import MazeRun
from rs2004.game import reader
from rs2004.traversal import traversal
here = None
keys = None
walks = None
restore = None
from rs2004.game import game
from rs2004.items import inventory
from rs2004.geometry import Tile

def _fn1():
    global here, keys, walks
    here = Tile(3069, 3518, 0)
    keys = set([DS_ID.MAZE_KEY])
    walks = []

    def walk(tile, **kwargs):
        walks.append(Fake(**{'x': tile.x, 'z': tile.z, 'level': tile.level}))
        return False
        yield
    spy_on(game, 'tile', impl=lambda: here)
    spy_on(inventory, 'items', impl=lambda: [Fake(id=id, count=1) for id in keys])
    spy_on(traversal, 'walk_resilient', impl=walk)
before_each(_fn1)

def log(*args):
    pass

def _fn3():

    def _fn4():
        _w5 = yield from MazeRun().step(log)
        expect(_w5).to_be(False)
        expect(walks).to_equal([Fake(**{'x': 2941, 'z': 3248, 'level': 0})])
    test('a fresh run from Oziach walks to the front door', _fn4)

    def _fn6():
        global here, walks
        run = MazeRun()
        here = Tile(2931, 9643, 0)
        keys.add(DS_ID.BLUE_KEY)
        yield from run.step(log)
        keys.discard(DS_ID.BLUE_KEY)
        here = Tile(2929, 9649, 0)
        yield from run.step(log)
        expect(walks[-1] if len(walks) > 0 else None).to_equal(Fake(**{'x': 2929, 'z': 9649, 'level': 0}))
        here = Tile(3069, 3518, 0)
        walks = []
        _w7 = yield from run.step(log)
        expect(_w7).to_be(False)
        _w8 = yield from run.step(log)
        expect(_w8).to_be(False)
        expect(walks).to_equal([Fake(**{'x': 2941, 'z': 3248, 'level': 0}), Fake(**{'x': 2941, 'z': 3248, 'level': 0})])
    test('returning to Oziach after reaching Melzar restarts at the front door', _fn6)

    def _fn9():
        keys.add(DS_ID.BLUE_KEY)
        _w10 = yield from MazeRun().step(log)
        expect(_w10).to_be(False)
        expect(walks).to_equal([Fake(**{'x': 2941, 'z': 3248, 'level': 0})])
    test('a coloured key outside the maze cannot skip the front door', _fn9)

    def _fn11():
        global here
        run = MazeRun()
        here = Tile(2931, 9643, 0)
        keys.add(DS_ID.BLUE_KEY)
        yield from run.step(log)
        keys.discard(DS_ID.BLUE_KEY)
        here = Tile(2930, 9643, 0)
        yield from run.step(log)
        expect(walks).to_equal([Fake(**{'x': 2931, 'z': 9643, 'level': 0}), Fake(**{'x': 2929, 'z': 9649, 'level': 0})])
    test('spending the blue key inside keeps the route moving to Melzar', _fn11)
describe('MazeRun recovery', _fn3)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

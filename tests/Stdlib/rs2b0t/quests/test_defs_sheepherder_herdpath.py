"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/sheepherder-herdpath.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.sheepherder.herd_path import herd_cost, herd_directions, herd_distance, herd_distances, herd_plan, pinned, pushable, risky

SIZE = 9


def field(*walls):
    """An open SIZE×SIZE field with the named tiles blocked; everything off the field is blocked too."""
    blocked = set([f'{x},{z}' for x, z in walls])

    def walkable(x, z):
        return x >= 0 and x < SIZE and z >= 0 and z < SIZE and not (f'{x},{z}' in blocked)

    return Record({'walkable': walkable, 'can_step': lambda x, z, dx, dz: walkable(x, z) and walkable(x + dx, z + dz)})


def column(x, z0, z1):
    tiles = []
    for z in range(z0, z1 + 1):
        tiles.append([x, z])
    return tiles


PEN = Record({'x0': 1, 'x1': 1, 'z0': 0, 'z1': 0})


def _fn2():
    def _fn3():
        grid = field([4, 6])
        expect(pushable(grid, 4, 5, Record({'dx': 0, 'dz': -1}))).to_be(False)
        expect(pushable(grid, 4, 4, Record({'dx': 0, 'dz': -1}))).to_be(True)
    test('a push needs a standable tile behind the sheep', _fn3)

    def _fn4():
        grid = field([4, 3])
        expect(pushable(grid, 4, 4, Record({'dx': 0, 'dz': -1}))).to_be(False)
    test('a push needs somewhere for the sheep to land', _fn4)

    def _fn5():
        open = field()
        # A fence between x = 4 and x = 5: both tiles walkable, neither side steppable.
        fenced = Record({
        'walkable': open.walkable,
        'can_step': lambda x, z, dx, dz: open.can_step(x, z, dx, dz) and not (z == 6 and ((x == 4 and dx == 1) or (x == 5 and dx == -1))),
    })
        expect(fenced.walkable(5, 6)).to_be(True)
        expect(pushable(fenced, 4, 6, Record({'dx': -1, 'dz': 0}))).to_be(False)
        expect(pushable(fenced, 4, 6, Record({'dx': 0, 'dz': 1}))).to_be(True)
    test('a push needs the stand to be able to reach the sheep', _fn5)

    def _fn6():
        dist = herd_distances(field(), Record({'x': 4, 'z': 5}), PEN)
        expect(herd_distance(dist, 4, 5)).to_be(3 + 5)
    test('counts pushes, not tiles', _fn6)

    def _fn7():
        dist = herd_distances(field(*column(2, 0, 6)), Record({'x': 4, 'z': 1}), PEN)
        expect(herd_distance(dist, 4, 1)).to_be(6 + 3 + 7)
    test('routes around a wall rather than through it', _fn7)

    def _fn8():
        dist = herd_distances(field(*column(2, 0, 6)), Record({'x': 4, 'z': 0}), PEN)
        expect(herd_distance(dist, 4, 0)).to_be_undefined()
    test('gives up on a sheep pinned where the push it needs has no stand', _fn8)

    def _fn9():
        dirs = herd_directions(field(), Record({'x': 4, 'z': 4}), PEN)
        expect(dirs).to_have_length(4)
        expect(sorted([f'{d.dx},{d.dz}' for d in dirs[0:2]])).to_equal(['-1,0', '0,-1'])
    test('offers every legal push, closest to the pen first', _fn9)

    def _fn10():
        grid = field(*column(3, 0, 8), *column(0, 0, 8))
        expect(herd_directions(grid, Record({'x': 5, 'z': 4}), PEN)).to_equal([])
    test('reports nothing when the pen is walled off', _fn10)

    def _fn11():
        expect(herd_distance(herd_distances(field(), Record({'x': 1, 'z': 0}), PEN), 1, 0)).to_be(0)
    test('a sheep already in the pen is zero pushes from it', _fn11)
    NOTCH = field([4, 3], [5, 4], [3, 4])

    def _fn12():
        expect(pinned(NOTCH, 4, 4)).to_be(True)
        expect(pinned(NOTCH, 4, 5)).to_be(False)
        expect(pinned(NOTCH, 4, 3)).to_be(False)
    test('names a walkable tile with no standable side a trap', _fn12)

    def _fn13():
        expect(risky(NOTCH, 4, 5)).to_be(True)
        expect(risky(NOTCH, 5, 5)).to_be(True)
        expect(risky(NOTCH, 4, 6)).to_be(False)
    test('calls a tile touching a trap risky, out to the diagonals', _fn13)
    CORRIDOR = field([4, 3], [3, 4], [5, 4])
    WEST_PEN = Record({'x0': 1, 'x1': 1, 'z0': 5, 'z1': 5})

    def _fn14():
        plan = herd_plan(CORRIDOR, Record({'x': 6, 'z': 5}), WEST_PEN)
        expect(pinned(CORRIDOR, 4, 4)).to_be(True)
        expect(herd_distance(plan.any, 6, 5)).to_be(5)
        expect(herd_distance(plan.clear, 6, 5)).to_be(7)
    test('routes around a trap even when that costs pushes', _fn14)

    def _fn15():
        plan = herd_plan(CORRIDOR, Record({'x': 4, 'z': 5}), WEST_PEN)
        expect(herd_distance(plan.clear, 4, 5)).to_be_undefined()
        expect(herd_directions(CORRIDOR, Record({'x': 4, 'z': 5}), WEST_PEN)).not_.to_equal([])
    test('falls back to the trap-blind route for a sheep already off the clear network', _fn15)

    def _fn16():
        plan = herd_plan(CORRIDOR, Record({'x': 6, 'z': 5}), WEST_PEN)
        expect(herd_cost(plan, 6, 6)).to_be(6)
        expect(herd_cost(plan, 4, 5)).to_be_greater_than(100)
        expect(herd_cost(plan, 8, 0)).to_be_undefined()
    test('costs every off-network tile above every clear one, so the two never swap potentials', _fn16)

    def _fn17():
        grid = field([1, 1], [0, 0], [2, 0])
        expect(herd_distance(herd_distances(grid, Record({'x': 1, 'z': 0}), PEN), 1, 0)).to_be_undefined()
    test('drops a pen tile no push could ever be issued at', _fn17)


describe('herd path', _fn2)

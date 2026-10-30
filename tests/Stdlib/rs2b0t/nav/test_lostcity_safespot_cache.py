"""The walking half of rs2b0t's test/api/ai/quests/defs/lostcity-safespot.test.ts (MIT, see thirdparty/rs2b0t), over
this cache's world map. rs2b0t's file also ran its engine's naive pathfinder over the engine's map files and checked
the Strike ray's line of sight; the native line of sight reads the loaded scene, which a real-cache test hasn't, so
those cases stay with rs2b0t."""

import _core
from rs2004.quests.defs.lostcity_combat import LURE, TREE_SPIRIT_SAFESPOT, TREE_SPIRIT_TRAP, TREE_STAND

# WalkMap's exit bits: north, east, south, west, then the diagonals clockwise from north-east.
STEPS = [[0, 1], [1, 0], [0, -1], [-1, 0], [1, 1], [1, -1], [-1, -1], [-1, 1]]


def distance(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def can_step(tile, dx, dz):
    exits = _core.walk_tile(tile.x, tile.z, tile.level)[1]
    return (exits & (1 << STEPS.index([dx, dz]))) != 0


def fungus_blocks():
    for tile in [TREE_SPIRIT_SAFESPOT, TREE_SPIRIT_TRAP]:
        expect(tile.level).to_be(0)
        expect(_core.walk_tile(tile.x, tile.z, tile.level)[0], str(tile)).to_be(1)
    expect(distance(TREE_SPIRIT_SAFESPOT, TREE_SPIRIT_TRAP)).to_be(2)
    expect(_core.walk_tile(2859, 9732, 0)[0]).to_be(0)
    expect(can_step(TREE_SPIRIT_TRAP, 0, -1)).to_be(False)


def lure_connects():
    route = [TREE_STAND] + list(LURE)
    for i in range(1, len(route)):
        a = route[i - 1]
        b = route[i]
        expect(distance(a, b), str(b)).to_be(1)
        expect(can_step(a, b.x - a.x, b.z - a.z), str(b)).to_be(True)


describe('Lost City packed safespot geometry', lambda: [
    test('the fungus blocks walking from the trapped tile to the safespot', fungus_blocks),
    test('the south lure is one open step at a time', lure_connects),
])

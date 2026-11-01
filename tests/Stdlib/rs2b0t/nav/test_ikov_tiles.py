"""rs2b0t's test/event/webwalk/ikovTiles.test.ts (MIT, see thirdparty/rs2b0t), against this client's real cache and
walker graph."""

import _core
from rs2004.quests.defs.ikov.areas import GUARDIAN_STOP, ICE_CHESTS, IKOV_TILE, LAVA_BRIDGE_ZONE, LUCIEN_START, WINELDA_STOP
from rs2004.routeplan import crossings

ROUTED = [
    ['dungeon entrance', IKOV_TILE.ENTRANCE],
    ['Door of Fear, south side', IKOV_TILE.FEAR_GATE_SOUTH],
    ['south gate, north side', IKOV_TILE.SOUTH_GATE_NORTH],
    ['lever bracket', IKOV_TILE.LEVER_BRACKET],
    ['dark stairs down', IKOV_TILE.DARK_STAIRS_DOWN],
    ['trap lever', IKOV_TILE.TRAP_LEVER],
    ['east bank of the lava bridge', IKOV_TILE.BRIDGE_EAST],
    ['fire warrior door', IKOV_TILE.FIRE_DOOR_SOUTH],
    ['Winelda', IKOV_TILE.WINELDA],
]
# Why: each is entered by a script the graph cannot express, so a route appearing here is the bug, not the absence of one.
# Why: here the bridge's own tiles are walkable, so the two past it are sealed by the zone every walk of the module avoids.
SEALED = [
    ['boots room', IKOV_TILE.DARK_LANDING],
    ['west of the lava bridge', IKOV_TILE.BRIDGE_WEST],
    ['Lever spawn', IKOV_TILE.IKOV_LEVER_SPAWN],
    ["guardians' temple", IKOV_TILE.GUARDIANS],
    ['secret wall, inner side', IKOV_TILE.SECRET_WALL_INSIDE],
]


def walkable(tile):
    return _core.walk_tile(tile.x, tile.z, tile.level)[0] == 1


def route(a, b, zones=None):
    return navigator.find_path(a, b, max_expansions=4000000, policy={'use_teleports': False}, avoid_zones=zones).ok


# Why: a stand tile beside an unwalkable loc is the classic silent failure. The op is dropped with no refusal and no movement.
def stands():
    tiles = [[key, IKOV_TILE.get(key)] for key in IKOV_TILE.keys()]
    tiles += [['Lucien anchor', LUCIEN_START.anchor], ['Winelda anchor', WINELDA_STOP.anchor], ['Guardian anchor', GUARDIAN_STOP.anchor]]
    expect([name for name, tile in tiles if not walkable(tile)]).to_equal([])


test('every named tile and anchor is walkable', stands)


def routed():
    expect([name for name, to in ROUTED if not route(IKOV_TILE.TEMPLE_LADDER, to)]).to_equal([])


test('every leg the baked graph owns routes from the temple ladder', routed)


def chests():
    for chest in ICE_CHESTS:
        expect(walkable(chest.stand)).to_be(True)
        expect(route(IKOV_TILE.TEMPLE_LADDER, chest.stand)).to_be(True)


test('every chest stand is walkable and routes from the temple ladder', chests)


def sealed():
    expect([name for name, to in SEALED if route(IKOV_TILE.TEMPLE_LADDER, to, [LAVA_BRIDGE_ZONE])]).to_equal([])


test('the scripted pockets stay sealed', sealed)


# Why: Winelda's teleport is the way in and the shiny key door is the way out, so both sides are the module's problem, not the walker's.
def landing():
    for to in [IKOV_TILE.SHINY_KEY_SPAWN, IKOV_TILE.SECRET_WALL, IKOV_TILE.MCGRUBOR_LADDER]:
        expect(route(IKOV_TILE.WINELDA_LANDING, to)).to_be(True)


test("Winelda's landing reaches the shiny key and the secret wall", landing)


def keyed():
    door = [c for c in crossings() if c['x'] == 2657 and c['z'] == 3496 and c['level'] == 0]
    expect(len(door)).to_be(1)
    expect(door[0]['requires']).to_equal({'item': 'Shiny key', 'count': 1})


test('the McGrubor door is a keyed special crossing', keyed)

"""Issue #56: 289's reception ladder asks a warning, then enters the cavern without a quest gate."""

from rs2004.geometry import Tile
from rs2004.navigation import navigator
from rs2004.quests.defs.observatory.areas import OBS_LOC, OBS_TILE
from rs2004.routeplan import special_crossing_for_transport


def reception_route(dest):
    found = navigator.find_path(OBS_TILE.RECEPTION_LADDER, dest, max_expansions=400000,
                                policy={'use_teleports': False})
    expect(found.ok, found.reason).to_be(True)
    points = found.raw.get('waypoints', [])
    expect([points[-1]['x'], points[-1]['z'], points[-1]['level']]).to_equal([dest.x, dest.z, dest.level])
    hops = [p['transport'] for p in points if p.get('transport')]
    expect(hops[0].get('loc_id')).to_be(OBS_LOC.RECEPTION_LADDER)
    expect(hops[0].get('to_tile')).to_equal([2420, 9459])
    crossing = special_crossing_for_transport(hops[0], OBS_TILE.RECEPTION_LADDER, OBS_TILE.DUNGEON_LANDING)
    expect(crossing is not None).to_be(True)
    expect(crossing.get('dialogue')).to_equal({'choose': []})
    expect(crossing.get('toTile')).to_equal({'x': 2420, 'z': 9459, 'level': 0})
    expect(special_crossing_for_transport(hops[0], OBS_TILE.RECEPTION_LADDER, OBS_TILE.DOME_ARRIVE)).to_be(None)


def enters_cavern():
    reception_route(OBS_TILE.DUNGEON_LANDING)


test('the reception ladder enters the cavern through its warning dialogue', enters_cavern)


def reaches_telescope():
    reception_route(Tile(2440, 3160, 0))


test('a world walk from reception reaches the telescope through the cavern', reaches_telescope)

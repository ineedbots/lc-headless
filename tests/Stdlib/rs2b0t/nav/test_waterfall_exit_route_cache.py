"""The routing half of rs2b0t's test/event/webwalk/waterfallTransports.test.ts (MIT, see thirdparty/rs2b0t). rs2b0t
routed over a hand-built pack of four islands; here the planner routes over this cache, and the finished quest's way
out must take the three curated exits in order. The real dungeon's own doors come between them.
QuestNavigationDataTests.cpp checks the edges themselves."""

from rs2004.geometry import Tile
from rs2004.navigation import navigator

RAISED_ROOM = Tile(2603, 9913, 0)
RIVERBANK = Tile(2530, 3413, 0)


def exits():
    route = navigator.find_path(RAISED_ROOM, RIVERBANK, max_expansions=4000000, policy={'use_teleports': False})
    expect(route.ok, route.reason).to_be(True)
    taken = [w['transport'] for w in route.raw.get('waypoints', []) if isinstance(w, dict) and w.get('transport')]
    curated = [t for t in taken if t.get('kind') == 'dungeon']
    expect([[t.get('loc_x'), t.get('loc_z'), t.get('action'), t.get('to_tile')] for t in curated]).to_equal([
        [2604, 9900, 'Open', [2566, 9901]],
        [2575, 9861, 'Open', [2511, 3463]],
        [2512, 3463, 'Get in', [2527, 3413]],
    ])


test('routes the completed-quest exit through both doors and the barrel', exits)

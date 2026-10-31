"""The routing half of rs2b0t's test/api/ai/quests/defs/deathplateauScout.test.ts (MIT, see thirdparty/rs2b0t). rs2b0t
routed over its own collision pack; here the planner routes over this cache, kept off the thrower trolls' approach
the quest's secret-path walks avoid, and crosses the stile behind Tenzing (loc 3730)."""

from rs2004.navigation import navigator
from rs2004.quests.defs.deathplateau.areas import TILE
from rs2004.quests.defs.deathplateau.nav import THROWER_APPROACH
from rs2004.walkgeom import tile_in_danger_zones

STILE = 3730


def route(start, dest):
    found = navigator.find_path(start, dest, avoid_zones=THROWER_APPROACH, max_expansions=400000, policy={'use_teleports': False})
    expect(found.ok, found.reason).to_be(True)
    return found


def off_the_approach(found):
    return all([not tile_in_danger_zones(t.x, t.z, t.level, THROWER_APPROACH) for t in found.waypoints])


def crosses_stile(found):
    for w in found.raw.get('waypoints', []):
        hop = w.get('transport') if isinstance(w, dict) else None
        if hop and hop.get('kind') == 'shortcut' and hop.get('loc_x') == 2817 and hop.get('loc_z') == 3562:
            return True
    return False


def _fn1():
    found = route(TILE.TENZING_BACK, TILE.SCOUT)
    last = found.waypoints[-1]
    expect([last.x, last.z, last.level]).to_equal([TILE.SCOUT.x, TILE.SCOUT.z, TILE.SCOUT.level])
    expect(off_the_approach(found)).to_be(True)
    expect(crosses_stile(found)).to_be(True)


test('scout anchor is reachable inside the trigger through the stile', _fn1)


def _fn2():
    found = route(TILE.SCOUT, TILE.STILE_SOUTH)
    expect(crosses_stile(found)).to_be(True)
    expect(off_the_approach(found)).to_be(True)


test('the return to Tenzing crosses the stile without entering the troll approach', _fn2)


def _fn3():
    expect(off_the_approach(route(TILE.STILE_SOUTH, TILE.DENULTH))).to_be(True)


test('the hand-in stays off the approach after leaving the stile', _fn3)

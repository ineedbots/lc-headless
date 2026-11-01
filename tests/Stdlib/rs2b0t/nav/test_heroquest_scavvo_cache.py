"""Scavvo's shop, over the Champions' Guild stairs: phase 17g's live run walked to rs2b0t's stair edge outside the west
wall, where the staircase answers "I can't reach that!"."""

from rs2004.geometry import Tile
from rs2004.quests.defs.heroquest.areas import HERO_TILE

SOUTH_OF_THE_GUILD = Tile(3189, 3351, 0)


def climbs_from_inside():
    route = navigator.find_path(SOUTH_OF_THE_GUILD, HERO_TILE.SCAVVO, max_expansions=4000000, policy={'use_teleports': False})
    expect(route.ok).to_be(True)
    tiles = [[t.x, t.z] for t in route.waypoints if t.level == 0]
    expect(tiles).to_contain([3188, 3358])
    expect([3187, 3355] in tiles).to_be(False)


test('the guild staircase is climbed from inside the guild', climbs_from_inside)

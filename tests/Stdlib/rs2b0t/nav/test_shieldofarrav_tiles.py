"""rs2b0t's shieldOfArravTiles tests, against this client's real cache and walker graph."""
import _core
from rs2004.quests.defs.shieldofarrav.areas import SOA_TILE, RELDO, BARAEK, TRAMP, STRAVEN_JOIN, KATRINE_JOIN, CURATOR, ROALD


def stands():
    tiles = list(SOA_TILE._fields.values()) + [stop.anchor for stop in [RELDO, BARAEK, TRAMP, STRAVEN_JOIN, KATRINE_JOIN, CURATOR, ROALD]]
    for tile in tiles:
        expect(_core.walk_tile(tile.x, tile.z, tile.level)[0], str(tile)).to_be(1)


test('all named stand tiles and NPC anchors are walkable', stands)


def route(a, b):
    return navigator.find_path(a, b, max_expansions=4000000, policy={'use_teleports':False}).ok


def upper_floors():
    for spawn in [SOA_TILE.CROSSBOW_WEST, SOA_TILE.CROSSBOW_EAST]:
        expect(route(SOA_TILE.STORE_LADDER_TOP, spawn)).to_be(True)
    expect(route(SOA_TILE.BLACKARM_STAIRS_TOP, SOA_TILE.CUPBOARD_STAND)).to_be(True)
    expect(route(SOA_TILE.PHOENIX_DOOR_INNER, SOA_TILE.CHEST_STAND)).to_be(True)


test('each hideout interior reaches its quest item', upper_floors)


def sealed_chest():
    for start in [SOA_TILE.HQ_LADDER, SOA_TILE.PHOENIX_DOOR]:
        expect(route(start, SOA_TILE.CHEST_STAND)).to_be(False)


test('the chest needs its scripted door crossing', sealed_chest)

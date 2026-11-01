"""Ported from rs2b0t's src/bot/api/ai/quests/defs/elementalworkshop/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['EW_ITEM', 'PICKAXES', 'SEERS_BANK', 'BOOKCASE', 'KNIFE_SPAWN', 'SMITHY', 'STAIRS_TOP', 'WORKSHOP_ARRIVAL', 'ROCK_STAND', 'WATER_STAND', 'BELLOWS_STAND', 'FURNACE_STAND', 'TROUGH_STAND', 'WORKBENCH_STAND', 'CRATE_HUB', 'ew_area']

# Classic 2004 object ids (rs2b2t pack). Empty and full stone bowls both
# render as "A stone bowl", so every bowl check goes through id.
EW_ITEM = Record({
    'BATTERED_BOOK': Record({'id': 2886, 'name': 'Battered book'}),
    'BATTERED_KEY': Record({'id': 2887, 'name': 'Battered key'}),
    'STONE_BOWL': Record({'id': 2888, 'name': 'A stone bowl'}),
    'STONE_BOWL_FULL': Record({'id': 2889, 'name': 'A stone bowl'}),
    'ELEMENTAL_SHIELD': Record({'id': 2890, 'name': 'Elemental shield'}),
    'ELEMENTAL_ORE': Record({'id': 2892, 'name': 'Elemental ore'}),
    'ELEMENTAL_METAL': Record({'id': 2893, 'name': 'Elemental metal'}),
    'KNIFE': Record({'id': 946, 'name': 'Knife'}),
    'NEEDLE': Record({'id': 1733, 'name': 'Needle'}),
    'THREAD': Record({'id': 1734, 'name': 'Thread'}),
    'LEATHER': Record({'id': 1741, 'name': 'Leather'}),
    'COAL': Record({'id': 453, 'name': 'Coal'}),
    'HAMMER': Record({'id': 2347, 'name': 'Hammer'}),
    'COINS': Record({'id': 995, 'name': 'Coins'}),
})
PICKAXES = [
    Record({'id': 1275, 'name': 'Rune pickaxe'}),
    Record({'id': 1271, 'name': 'Adamant pickaxe'}),
    Record({'id': 1273, 'name': 'Mithril pickaxe'}),
    Record({'id': 1269, 'name': 'Steel pickaxe'}),
    Record({'id': 1267, 'name': 'Iron pickaxe'}),
    Record({'id': 1265, 'name': 'Bronze pickaxe'}),
]
SEERS_BANK = Tile(2725, 3491, 0)
# House south-west of Seers bank: bookcase on the east wall.
BOOKCASE = Tile(2716, 3481, 0)
# House south of the smithy often has a ground Knife near the range.
KNIFE_SPAWN = Tile(2714, 3477, 0)
# Outside the Seers smithy, walkable stand; the odd-looking wall tile itself is blocked.
SMITHY = Tile(2709, 3499, 0)
# Spiral stairs land at 0_42_54_21_41, i.e. (2709, 3497). Approach from the west.
STAIRS_TOP = Tile(2708, 3497, 0)
# Spiral stairs land at 0_42_154_28_32, i.e. (2716, 9888).
WORKSHOP_ARRIVAL = Tile(2716, 9888, 0)
# West chamber approach; the rock loc tile itself is unwalkable.
ROCK_STAND = Tile(2705, 9888, 0)
WATER_STAND = Tile(2719, 9904, 0)
BELLOWS_STAND = Tile(2734, 9884, 0)
FURNACE_STAND = Tile(2724, 9874, 0)
TROUGH_STAND = Tile(2720, 9876, 0)
WORKBENCH_STAND = Tile(2716, 9888, 0)
CRATE_HUB = Tile(2718, 9892, 0)
WORKSHOP_Z_MIN = 9850
WORKSHOP_Z_MAX = 9950
WORKSHOP_X_MIN = 2690
WORKSHOP_X_MAX = 2760


def ew_area(tile):
    if not tile:
        return 'unknown'
    if tile.level == 0 and tile.x >= WORKSHOP_X_MIN and tile.x <= WORKSHOP_X_MAX and tile.z >= WORKSHOP_Z_MIN and tile.z <= WORKSHOP_Z_MAX:
        return 'workshop'
    if tile.x >= 2680 and tile.x <= 2760 and tile.z >= 3460 and tile.z <= 3520:
        return 'seers'
    return 'elsewhere'

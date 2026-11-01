"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['UP_ITEM', 'UP_ORBS', 'UP_BADGES', 'UP_AMULETS', 'UP_NPC', 'UP_LOC', 'UP_TILE', 'CAVERN_LINKS', 'PLATFORM_LINKS', 'upass_area', 'held', 'banked', 'owned', 'worn', 'carried', 'count_held', 'GRID_ZONE', 'inside_witch_house', 'inside_iban_temple', 'past_grid_tile']

# Why: all 4 orbs display as "Orb of light" and 2 of the 3 badges as "Paladin's badge", so every lookup goes through the id.
UP_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'LOBSTER': Record({'id': 379, 'name': 'Lobster'}),
    'TINDERBOX': Record({'id': 590, 'name': 'Tinderbox'}),
    'BUCKET': Record({'id': 1925, 'name': 'Bucket'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'SPADE': Record({'id': 952, 'name': 'Spade'}),
    'GAS_MASK': Record({'id': 1506, 'name': 'Gas mask'}),
    'SHORTBOW': Record({'id': 841, 'name': 'Shortbow'}),
    'BRONZE_ARROW': Record({'id': 882, 'name': 'Bronze arrow'}),
    'DAMP_CLOTH': Record({'id': 1485, 'name': 'Damp cloth'}),
    'UNLIT_ARROW': Record({'id': 598, 'name': 'Bronze fire arrows'}),
    'LIT_ARROW': Record({'id': 942, 'name': 'Bronze fire arrows'}),
    'ORB1': Record({'id': 1481, 'name': 'Orb of light'}),
    'ORB2': Record({'id': 1482, 'name': 'Orb of light'}),
    'ORB3': Record({'id': 1483, 'name': 'Orb of light'}),
    'ORB4': Record({'id': 1484, 'name': 'Orb of light'}),
    'RAILING': Record({'id': 1486, 'name': 'Piece of railing'}),
    'UNICORN_HORN': Record({'id': 1487, 'name': 'Unicorn horn'}),
    'BADGE_JERRO': Record({'id': 1488, 'name': "Paladin's badge"}),
    'BADGE_CARL': Record({'id': 1489, 'name': "Paladin's badge"}),
    'BADGE_HARRY': Record({'id': 1490, 'name': "Paladin's badge"}),
    'WITCH_CAT': Record({'id': 1491, 'name': 'Witches cat'}),
    'DOLL': Record({'id': 1492, 'name': 'Doll of iban'}),
    'HISTORY': Record({'id': 1494, 'name': 'History of iban'}),
    'GAUNTLETS': Record({'id': 1495, 'name': "Klank's gauntlets"}),
    'DOVE': Record({'id': 1496, 'name': "Iban's dove"}),
    'AMULET_OTHAINIAN': Record({'id': 1497, 'name': 'Amulet of othanian'}),
    'AMULET_DOOMION': Record({'id': 1498, 'name': 'Amulet of doomion'}),
    'AMULET_HOLTHION': Record({'id': 1499, 'name': 'Amulet of holthion'}),
    'SHADOW': Record({'id': 1500, 'name': "Iban's shadow"}),
    'DWARF_BREW': Record({'id': 1501, 'name': 'Dwarf brew'}),
    'ASHES': Record({'id': 1502, 'name': "Iban's ashes"}),
    'IBAN_STAFF': Record({'id': 1409, 'name': 'Staff of iban'}),
    'ZAM_TOP': Record({'id': 1035, 'name': 'Robe of zamorak'}),
    'ZAM_BOTTOM': Record({'id': 1033, 'name': 'Robe of zamorak'}),
})
UP_ORBS = [UP_ITEM.ORB1, UP_ITEM.ORB2, UP_ITEM.ORB3, UP_ITEM.ORB4]
UP_BADGES = [UP_ITEM.BADGE_JERRO, UP_ITEM.BADGE_CARL, UP_ITEM.BADGE_HARRY]
UP_AMULETS = [UP_ITEM.AMULET_DOOMION, UP_ITEM.AMULET_OTHAINIAN, UP_ITEM.AMULET_HOLTHION]
# Why: 5 NPCs all render as "Koftik", so the guide is matched by id.
UP_NPC = Record({
    'KOFTIK_SURFACE': 972,
    'KOFTIK_BRIDGE': 973,
    'KOFTIK_GRID': 974,
    'KOFTIK_INSANE': 975,
    'KOFTIK_LAST': 976,
    'BOULDER': 986,
    'PALADIN_JERRO': 988,
    'PALADIN_CARL': 989,
    'PALADIN_HARRY': 990,
    'WITCH': 992,
    'WITCH_CAT': 993,
    'NILHOOF': 994,
    'KLANK': 995,
    'KAMEN': 996,
    'KALRAG': 997,
    'OTHAINIAN': 998,
    'DOOMION': 999,
    'HOLTHION': 1000,
    'DISCIPLE': 1002,
    'IBAN': 1003,
})
UP_LOC = Record({
    'CAVE_ENTRANCE': 3213,
    'CAVE_EXIT': 3214,
    'GUIDEROPE': 3340,
    'BRIDGE_LEVER': 3241,
    'LOGTRAP_TRIGGER': 3339,
    'ORB_VIS': 3361,
    'SPEARTRAP': 3234,
    'SPRINGTRAP': 3230,
    'FURNACE': 3294,
    'WELL': 3264,
    'TABLET_WEST': 3298,
    'TABLET_EAST': 3297,
    'PORTCULLIS_LEVER': 3337,
    'PORTCULLIS': 3303,
    'GRID_HANDHOLDS': 3365,
    'RAILINGS_LOCKED': 3266,
    'RAILINGS_LOOSE': 3267,
    'RAILINGS_HARD': 3268,
    'MUDPILE': 3307,
    'UNICORN_CAGE': 3308,
    'UNICORN_DOOR_R': 3218,
    'UNICORN_DOOR_L': 3219,
    'BLOODWELL': 3305,
    'TEMPLE_DOOR_L': 3220,
    'TEMPLE_DOOR_R': 3221,
    'TUNNEL_DOWN': 3222,
    'TUNNEL_UP': 3223,
    'LEDGE': 3238,
    'ROCK_BRIDGE': 3276,
    'ROCKSWING': 2275,
    'ROCKSWING_ANCHOR': 2276,
    'ROCKSWING_BACK': 2274,
    'ROCKSLIDE': 3309,
    'COLLAPSED_A': 3254,
    'COLLAPSED_B': 3255,
    'WITCH_DOOR': 3270,
    'WITCH_CHEST': 3272,
    'WITCH_CHEST_OPEN': 3273,
    'SEALED_CHEST': 3274,
    'CAGE_DOVE': 3351,
    'CAGE_EMPTY': 3352,
    'BREW_BARREL': 3344,
    'IBAN_TOMB_L': 3353,
    'IBAN_TOMB_R': 3354,
    'IBAN_DOOR_R': 3333,
    'IBAN_DOOR_L': 3334,
    'IBAN_ALTAR': 3359,
    'LAST_OUT': 3224,
    'FOOD_CRATE': 3360,
    'PIPE_AREA1': 3235,
    'PIPE_AREA2': 3237,
    'MUD_DIG': 3216,
    'WALL_DOOR_L': 2048,
    'WALL_DOOR_R': 2049,
})
# Why: every tile here that fronts a loc is a stand, since a multi-tile loc covers its origin and walking to it fails outright.
UP_TILE = Record({
    'ARDOUGNE_BANK': Tile(2655, 3283, 0),
    'AEMAD': Tile(2613, 3294, 0),
    'LOWE': Tile(3231, 3421, 0),
    'LATHAS': Tile(2578, 3293, 1),
    'CASTLE_STAIRS': Tile(2572, 3296, 0),
    'WALL_GATE_EAST': Tile(2559, 3300, 0),
    'WALL_GATE_WEST': Tile(2555, 3300, 0),
    'CAVE_MOUTH': Tile(2436, 3315, 0),
    'CAVE_ENTRANCE': Tile(2433, 3313, 0),
    'AREA1_LANDING': Tile(2494, 9716, 0),
    'KOFTIK_BRIDGE': Tile(2449, 9716, 0),
    'GUIDEROPE_SHOT': Tile(2448, 9721, 0),
    'BRIDGE_WEST': Tile(2442, 9716, 0),
    'BRIDGE_LEVER': Tile(2436, 9716, 0),
    'ROCKSWING_WEST': Tile(2462, 9699, 0),
    'ROCKSWING_EAST': Tile(2466, 9699, 0),
    'GRID_EAST': Tile(2477, 9677, 0),
    'GRID_APPROACH': Tile(2479, 9679, 0),
    'GRID_WEST': Tile(2467, 9677, 0),
    'PORTCULLIS_LEVER': Tile(2466, 9672, 0),
    'FURNACE': Tile(2454, 9682, 0),
    'ORB2': Tile(2386, 9677, 0),
    'ORB3': Tile(2385, 9685, 0),
    'ORB4': Tile(2416, 9698, 0),
    'LOGTRAP': Tile(2382, 9668, 0),
    'WELL': Tile(2416, 9674, 0),
    'CORRIDOR_HUB': Tile(2422, 9671, 0),
    'AREA2_LANDING': Tile(2423, 9660, 0),
    'RAILINGS_LOOSE': Tile(2397, 9606, 0),
    'BOULDER': Tile(2398, 9596, 0),
    'UNICORN_CAGE': Tile(2375, 9604, 0),
    'MUDPILE': Tile(2423, 9661, 0),
    'MUD_DIG': Tile(2393, 9650, 0),
    'PALADINS': Tile(2424, 9719, 0),
    'BLOODWELL': Tile(2373, 9718, 0),
    'TEMPLE_DOOR': Tile(2370, 9718, 0),
    'MAIN_LANDING': Tile(2173, 4725, 1),
    'CAGE_DOVE': Tile(2134, 4702, 1),
    'TUNNEL_TO_DWARVES': Tile(2150, 4545, 1),
    'TUNNEL_FROM_DWARVES': Tile(2336, 9793, 0),
    'TUNNEL_TO_KALRAG': Tile(2112, 4729, 1),
    'TUNNEL_FROM_KALRAG': Tile(2304, 9915, 0),
    'NILHOOF': Tile(2315, 9806, 0),
    'KLANK': Tile(2323, 9804, 0),
    'KAMEN': Tile(2325, 9799, 0),
    'BREW_BARREL': Tile(2327, 9799, 0),
    'IBAN_TOMB': Tile(2357, 9800, 0),
    'KALRAG': Tile(2356, 9911, 0),
    'WITCH_DOOR': Tile(2158, 4566, 1),
    'WITCH_DOOR_OUT': Tile(2158, 4567, 1),
    'WITCH_CHEST': Tile(2157, 4564, 1),
    'WITCH_CAT': Tile(2131, 4602, 1),
    'SEALED_CHEST': Tile(2136, 4578, 1),
    'DOOMION': Tile(2134, 4565, 1),
    'HOLTHION': Tile(2132, 4554, 1),
    'OTHAINIAN': Tile(2122, 4562, 1),
    'DISCIPLE': Tile(2159, 4646, 1),
    'IBAN_DOOR': Tile(2144, 4647, 1),
    'IBAN_ALTAR': Tile(2136, 4647, 1),
    'IBAN_THROWN_OUT': Tile(2482, 9607, 0),
    'LAST_OUT': Tile(2438, 9607, 0),
    'CAVE_EXIT': Tile(2496, 9714, 0),
    'WELL_OF_VOYAGE': Tile(2008, 4711, 1),
})
# Why: The static level-1 pocket graph is generated from collision data to avoid runtime searches among identical bridges.
# Why: the first cavern is a pocket graph too and the runtime search fails it the same way: from 9a025db the rockslide that leaves it is 21 tiles east and the client's build area lags you, so a scene query can't hold it. These 2 are the links the bridge-to-grid route needs.
CAVERN_LINKS = [
    Record({
    'bridge': Tile(2491, 9691, 0),
    'a': Record({'tile': Tile(2491, 9692, 0), 'pocket': '9a025db'}),
    'b': Record({'tile': Tile(2491, 9690, 0), 'pocket': '9b225ca'}),
}),
    Record({
    'bridge': Tile(2482, 9679, 0),
    'a': Record({'tile': Tile(2483, 9679, 0), 'pocket': '9b225ca'}),
    'b': Record({'tile': Tile(2481, 9679, 0), 'pocket': '9a225c9'}),
}),
]
PLATFORM_LINKS = [
    Record({
    'bridge': Tile(2123, 4582, 1),
    'a': Record({'tile': Tile(2123, 4581, 1), 'pocket': '84811d6'}),
    'b': Record({'tile': Tile(2123, 4585, 1), 'pocket': '84b11e9'}),
}),
    Record({
    'bridge': Tile(2126, 4566, 1),
    'a': Record({'tile': Tile(2125, 4566, 1), 'pocket': '84811d6'}),
    'b': Record({'tile': Tile(2129, 4566, 1), 'pocket': '85111c9'}),
}),
    Record({
    'bridge': Tile(2127, 4592, 1),
    'a': Record({'tile': Tile(2127, 4591, 1), 'pocket': '84b11e9'}),
    'b': Record({'tile': Tile(2130, 4592, 1), 'pocket': '84711f5'}),
}),
    Record({
    'bridge': Tile(2136, 4584, 1),
    'a': Record({'tile': Tile(2135, 4584, 1), 'pocket': '85211e7'}),
    'b': Record({'tile': Tile(2139, 4584, 1), 'pocket': '84711f5'}),
}),
    Record({
    'bridge': Tile(2142, 4562, 1),
    'a': Record({'tile': Tile(2142, 4561, 1), 'pocket': '85111c9'}),
    'b': Record({'tile': Tile(2142, 4565, 1), 'pocket': '84711f5'}),
}),
    Record({
    'bridge': Tile(2143, 4604, 1),
    'a': Record({'tile': Tile(2142, 4604, 1), 'pocket': '84711f5'}),
    'b': Record({'tile': Tile(2146, 4604, 1), 'pocket': '86211fc'}),
}),
    Record({
    'bridge': Tile(2147, 4583, 1),
    'a': Record({'tile': Tile(2146, 4583, 1), 'pocket': '84711f5'}),
    'b': Record({'tile': Tile(2150, 4583, 1), 'pocket': '86311db'}),
}),
    Record({
    'bridge': Tile(2156, 4582, 1),
    'a': Record({'tile': Tile(2155, 4582, 1), 'pocket': '86311db'}),
    'b': Record({'tile': Tile(2159, 4582, 1), 'pocket': '84111c4'}),
}),
    Record({
    'bridge': Tile(2161, 4599, 1),
    'a': Record({'tile': Tile(2161, 4598, 1), 'pocket': '86811f4'}),
    'b': Record({'tile': Tile(2161, 4602, 1), 'pocket': '86211fc'}),
}),
    Record({
    'bridge': Tile(2121, 4686, 1),
    'a': Record({'tile': Tile(2120, 4686, 1), 'pocket': '84111c4'}),
    'b': Record({'tile': Tile(2124, 4686, 1), 'pocket': '84c124e'}),
}),
    Record({
    'bridge': Tile(2145, 4717, 1),
    'a': Record({'tile': Tile(2145, 4716, 1), 'pocket': '84c124e'}),
    'b': Record({'tile': Tile(2145, 4720, 1), 'pocket': '8601270'}),
}),
    Record({
    'bridge': Tile(2154, 4690, 1),
    'a': Record({'tile': Tile(2154, 4689, 1), 'pocket': '84c124e'}),
    'b': Record({'tile': Tile(2154, 4693, 1), 'pocket': '869125a'}),
}),
    Record({
    'bridge': Tile(2155, 4704, 1),
    'a': Record({'tile': Tile(2155, 4703, 1), 'pocket': '869125a'}),
    'b': Record({'tile': Tile(2155, 4707, 1), 'pocket': '86b1263'}),
}),
    Record({
    'bridge': Tile(2155, 4718, 1),
    'a': Record({'tile': Tile(2155, 4717, 1), 'pocket': '86b1263'}),
    'b': Record({'tile': Tile(2155, 4721, 1), 'pocket': '8601270'}),
}),
    Record({
    'bridge': Tile(2158, 4724, 1),
    'a': Record({'tile': Tile(2157, 4724, 1), 'pocket': '8601270'}),
    'b': Record({'tile': Tile(2161, 4724, 1), 'pocket': '84111c4'}),
}),
    Record({
    'bridge': Tile(2164, 4686, 1),
    'a': Record({'tile': Tile(2163, 4686, 1), 'pocket': '869125a'}),
    'b': Record({'tile': Tile(2167, 4686, 1), 'pocket': '84111c4'}),
}),
    Record({
    'bridge': Tile(2123, 4616, 1),
    'a': Record({'tile': Tile(2123, 4615, 1), 'pocket': '8491201'}),
    'b': Record({'tile': Tile(2123, 4619, 1), 'pocket': '84a120f'}),
}),
    Record({
    'bridge': Tile(2127, 4610, 1),
    'a': Record({'tile': Tile(2126, 4610, 1), 'pocket': '8491201'}),
    'b': Record({'tile': Tile(2130, 4610, 1), 'pocket': '84a120f'}),
}),
    Record({
    'bridge': Tile(2148, 4614, 1),
    'a': Record({'tile': Tile(2147, 4614, 1), 'pocket': '84a120f'}),
    'b': Record({'tile': Tile(2151, 4614, 1), 'pocket': '86211fc'}),
}),
    Record({
    'bridge': Tile(2160, 4625, 1),
    'a': Record({'tile': Tile(2160, 4624, 1), 'pocket': '86211fc'}),
    'b': Record({'tile': Tile(2160, 4628, 1), 'pocket': '86f1218'}),
}),
    Record({
    'bridge': Tile(2161, 4637, 1),
    'a': Record({'tile': Tile(2161, 4636, 1), 'pocket': '86f1218'}),
    'b': Record({'tile': Tile(2161, 4640, 1), 'pocket': '8611226'}),
}),
    Record({
    'bridge': Tile(2161, 4654, 1),
    'a': Record({'tile': Tile(2161, 4653, 1), 'pocket': '8611226'}),
    'b': Record({'tile': Tile(2161, 4657, 1), 'pocket': '8701233'}),
}),
    Record({
    'bridge': Tile(2162, 4663, 1),
    'a': Record({'tile': Tile(2162, 4662, 1), 'pocket': '8701233'}),
    'b': Record({'tile': Tile(2162, 4666, 1), 'pocket': '84c124e'}),
}),
]


def upass_area(tile):
    """Which sealed pocket of the pass you're standing in. Why: the pass is a chain of one-way `p_teleport` hops between map squares the navigator can't route across, so every leg first asks where it is."""
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    # Why: the cavern platforms sit at level 1 under z 5000, the same band as the surface, so the x window separates them.
    if level == 1 and x >= 2112 and x <= 2175:
        if z >= 4672 and z <= 4735:
            return 'main'
        if z >= 4608 and z <= 4671:
            return 'temple'
        if z >= 4544 and z <= 4607:
            return 'witch'
    if level == 1 and x >= 1984 and x <= 2047 and z >= 4672 and z <= 4735:
        return 'voyage'
    if x >= 2304 and x <= 2367:
        if z >= 9856 and z <= 9919:
            return 'kalrag'
        if z >= 9792 and z <= 9855:
            return 'dwarves'
    if z >= 9536 and z <= 9599:
        return 'gridpit'
    if z >= 9600 and z <= 9663:
        return 'area2'
    if z >= 9664 and z <= 9727:
        return 'area1'
    if z >= 5000:
        return 'unknown'
    # Why: West Ardougne is sealed behind the wall with the Plague City sewer pipe the only way in, so it's its own region.
    return ('westardougne' if level == 0 and x >= 2433 and x <= 2556 and z >= 3266 and z <= 3334 else 'mainland')


def held(snap, item):
    _v1 = (snap.inv_ids.get(item.id) if snap.inv_ids is not None else None)
    return (_v1 if _v1 is not None else 0)


def banked(snap, item):
    _v2 = (snap.bank_ids.get(item.id) if snap.bank_ids is not None else None)
    return (_v2 if _v2 is not None else 0)


def owned(snap, item):
    return held(snap, item) + banked(snap, item)


def worn(snap, item):
    _v3 = ((item.id in snap.worn_ids) if snap.worn_ids is not None else None)
    return (_v3 if _v3 is not None else False)


def carried(snap, item):
    return held(snap, item) + ((1 if worn(snap, item) else 0))


def count_held(snap, items):
    """How many of a set the pack holds; the orbs, badges and amulets each share a display name."""
    return len([item for item in items if held(snap, item) > 0])


GRID_ZONE = Record({'min_x': 2467, 'max_x': 2476, 'min_z': 9673, 'max_z': 9682})
# Why: The orb corridor and bridge shelf have overlapping bounds, so classify the shelf first and treat the remaining area as corridor.
CORRIDOR = Record({'max_x': 2464, 'west_of_shelf': 2430, 'below_shelf': 9685, 'min_z': 9664})
# Why: Kardia's house is a sealed 15-tile pocket, x 2151-2157 by z 4565-4567, and the pack calls her door blocked because it's a door, so every leg that lifts the doll ends shut in with every walk out "unreachable".
WITCH_HOUSE = Record({'min_x': 2151, 'max_x': 2157, 'min_z': 4565, 'max_z': 4567})


def inside_witch_house(tile):
    return tile is not None and tile.level == 1 and tile.x >= WITCH_HOUSE.min_x and tile.x <= WITCH_HOUSE.max_x and tile.z >= WITCH_HOUSE.min_z and tile.z <= WITCH_HOUSE.max_z


# Why: stages 7 and 8 print the same journal text, so "am I past the doors" is answered by standing west of them on the temple floor.
def inside_iban_temple(tile):
    return tile is not None and tile.level == 1 and tile.x < UP_TILE.IBAN_DOOR.x and tile.x >= 2128 and tile.z >= 4640 and tile.z <= 4656


def past_grid_tile(tile):
    return tile is not None and tile.x <= CORRIDOR.max_x and tile.z >= CORRIDOR.min_z and (tile.z <= CORRIDOR.below_shelf or tile.x <= CORRIDOR.west_of_shelf)


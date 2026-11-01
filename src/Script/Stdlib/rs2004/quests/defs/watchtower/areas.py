"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['WT_ITEM', 'CRYSTALS', 'RELIC_PARTS', 'WT_LOC', 'WT_NPC', 'WT_TILE', 'WT_CAVES', 'WT_NIGHTSHADE', 'watchtower_area']

# Why: these are the engine's names and several collide: all 4 crystals are "Crystal", both mid-brew vials are "Vial", and the ogre potion is "Potion".
# Why: every lookup in this quest therefore goes through the id.
WT_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
    'LIT_CANDLE': Record({'id': 33, 'name': 'Lit candle'}),
    'VIAL_WATER': Record({'id': 227, 'name': 'Vial of water'}),
    'JANGERBERRIES': Record({'id': 247, 'name': 'Jangerberries'}),
    'GUAM_LEAF': Record({'id': 249, 'name': 'Guam leaf'}),
    'GUAM_VIAL': Record({'id': 91, 'name': 'Unfinished potion'}),
    'PESTLE': Record({'id': 233, 'name': 'Pestle and mortar'}),
    'PICKAXE': Record({'id': 1265, 'name': 'Bronze pickaxe'}),
    'BAT_BONES': Record({'id': 530, 'name': 'Bat bones'}),
    'DRAGON_BONES': Record({'id': 536, 'name': 'Dragon bones'}),
    'DEATH_RUNE': Record({'id': 560, 'name': 'Death rune'}),
    'GOLD_BAR': Record({'id': 2357, 'name': 'Gold bar'}),
    'OGRE_RELIC': Record({'id': 2372, 'name': 'Ogre relic'}),
    'RELIC_PART1': Record({'id': 2373, 'name': 'Relic part 1'}),
    'RELIC_PART2': Record({'id': 2374, 'name': 'Relic part 2'}),
    'RELIC_PART3': Record({'id': 2375, 'name': 'Relic part 3'}),
    'SKAVID_MAP': Record({'id': 2376, 'name': 'Skavid map'}),
    'OGRE_TOOTH': Record({'id': 2377, 'name': 'Ogre tooth'}),
    'TOBAN_KEY': Record({'id': 2378, 'name': 'Toban key'}),
    'ROCK_CAKE': Record({'id': 2379, 'name': 'Rock cake'}),
    'CRYSTAL1': Record({'id': 2380, 'name': 'Crystal'}),
    'CRYSTAL2': Record({'id': 2381, 'name': 'Crystal'}),
    'CRYSTAL3': Record({'id': 2382, 'name': 'Crystal'}),
    'CRYSTAL4': Record({'id': 2383, 'name': 'Crystal'}),
    'FINGERNAILS': Record({'id': 2384, 'name': 'Finger nails'}),
    'JANGER_VIAL': Record({'id': 2389, 'name': 'Vial'}),
    'GUAM_JANGER_VIAL': Record({'id': 2390, 'name': 'Vial'}),
    'GROUND_BAT_BONES': Record({'id': 2391, 'name': 'Ground bat bones'}),
    'STOLEN_GOLD': Record({'id': 2393, 'name': 'Gold'}),
    'OGRE_POTION': Record({'id': 2394, 'name': 'Potion'}),
    'MAGIC_OGRE_POTION': Record({'id': 2395, 'name': 'Magic ogre potion'}),
    'WATCHTOWER_SPELL': Record({'id': 2396, 'name': 'Spell scroll'}),
    'SHAMAN_ROBE': Record({'id': 2397, 'name': 'Shaman robe'}),
    'NIGHTSHADE': Record({'id': 2398, 'name': 'Nightshade'}),
})
CRYSTALS = [WT_ITEM.CRYSTAL1, WT_ITEM.CRYSTAL2, WT_ITEM.CRYSTAL3, WT_ITEM.CRYSTAL4]
RELIC_PARTS = [WT_ITEM.RELIC_PART1, WT_ITEM.RELIC_PART2, WT_ITEM.RELIC_PART3]
WT_LOC = Record({
    'WALL_CLIMB': 2299,
    'LADDER_TOP': 1746,
    'WATCH_LADDER_UP': 2796,
    'WATCH_LADDER_DOWN': 2797,
    'TOWER_LADDER': 2833,
    'LEVER': 2794,
    'BUSH_NAIL': 2799,
    'ROPESWING': 2324,
    'ROPESWING_NOROPE': 2326,
    'TOBAN_CHEST': 2790,
    'TOBAN_CAVE': 2811,
    'TOBAN_LADDER_DOWN': 2812,
    'GATE_RELIC': 2788,
    'GATE_EAST': 2786,
    'ROCK_CAKE_STALL': 2793,
    'BATTLEMENT': 2832,
    'JUMP_IN': 2830,
    'JUMP_OUT': 2831,
    'ENCLAVE_CAVE': 2813,
    'DARK_CAVE_ESCAPE': 2825,
    'ROCK_OF_DALGROTH': 2816,
    'CAVE_IN': [2805, 2806, 2807, 2808, 2809, 2810],
    'CAVE_OUT': [2817, 2818, 2819, 2820, 2821, 2822],
})
WT_NPC = Record({
    'WIZARD': 'Watchtower wizard',
    'OG': 'Og',
    'GREW': 'Grew',
    'TOBAN': 'Toban',
    'GORAD': 'Gorad',
    'CITY_GUARD': 'City guard',
    'OGRE_GUARD': 'Ogre guard',
    'ENCLAVE_GUARD': 'Enclave guard',
    'SHAMAN': 'Ogre shaman',
    'SKAVID': 'Skavid',
    'SCARED_SKAVID': 'Scared skavid',
    'MAD_SKAVID': 'Mad skavid',
})
WT_TILE = Record({
    'YANILLE_BANK': Tile(2612, 3092, 0),
    'WALL_CLIMB_STAND': Tile(2548, 3120, 0),
    'TOWER_LADDER_STAND': Tile(2544, 3112, 0),
    'LADDER_UP_STAND': Tile(2549, 3112, 1),
    'WIZARD_FLOOR': Tile(2549, 3112, 2),
    'LEVER_STAND': Tile(2543, 3116, 2),
    'BUSH_NAIL': Tile(2544, 3134, 0),
    'CANDLE': Tile(2547, 3115, 0),
    'OG': Tile(2506, 3116, 0),
    'ROPESWING_STAND': Tile(2501, 3087, 0),
    'GREW': Tile(2513, 3084, 0),
    'GREW_EXIT_STAND': Tile(2511, 3091, 0),
    'JANGERBERRIES': [Tile(2510, 3090, 0), Tile(2512, 3080, 0), Tile(2516, 3086, 0), Tile(2517, 3082, 0)],
    'TOBAN_CAVE': Tile(2499, 2988, 0),
    'TOBAN_LADDER': Tile(2575, 3028, 0),
    'TOBAN_CHEST': Tile(2575, 3032, 0),
    'TOBAN': Tile(2576, 3027, 0),
    'GORAD': Tile(2577, 3021, 0),
    'GATE_RELIC_STAND': Tile(2506, 3062, 0),
    'HILL': Tile(2546, 3065, 0),
    'ROCK_CAKE_STALL': Tile(2506, 3024, 0),
    'EAST_GATE_STAND': Tile(2550, 3030, 0),
    'EAST_GATE_INSIDE': Tile(2549, 3027, 0),
    'BATTLEMENT_GUARD': Tile(2503, 3011, 0),
    'BATTLEMENT_INSIDE': Tile(2508, 3011, 0),
    'JUMP_STAND': Tile(2531, 3026, 0),
    'JUMP_BACK_STAND': Tile(2530, 3029, 0),
    'CITY_GUARD': Tile(2541, 3029, 0),
    'ENCLAVE_GUARD': Tile(2507, 3037, 0),
    'ENCLAVE_EXIT': Tile(2598, 9467, 0),
    'ROCK_OF_DALGROTH': Tile(2590, 9450, 0),
    'SHAMAN_ROBE': Tile(2617, 9437, 0),
    'SHAMANS': [
    Tile(2577, 9451, 0),
    Tile(2582, 9437, 0),
    Tile(2592, 9436, 0),
    Tile(2599, 9461, 0),
    Tile(2606, 9438, 0),
    Tile(2607, 9451, 0),
],
})
WT_CAVES = [
    Record({'index': 1, 'stand': Tile(2561, 3021, 0), 'landing': Tile(2498, 9418, 0)}),
    Record({'index': 2, 'stand': Tile(2522, 3070, 0), 'landing': Tile(2532, 9469, 0)}),
    Record({'index': 3, 'stand': Tile(2539, 3054, 0), 'landing': Tile(2518, 9455, 0)}),
    Record({'index': 4, 'stand': Tile(2552, 3054, 0), 'landing': Tile(2498, 9451, 0)}),
    Record({'index': 5, 'stand': Tile(2552, 3034, 0), 'landing': Tile(2504, 9441, 0)}),
    Record({'index': 6, 'stand': Tile(2529, 3013, 0), 'landing': Tile(2522, 9411, 0)}),
]
WT_NIGHTSHADE = Record({'cave2': Tile(2530, 9462, 0), 'cave6': Tile(2528, 9415, 0)})


def watchtower_area(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    if x >= 2900 and x <= 2960 and z >= 4670 and z <= 4740:
        return 'mirrorTower'
    if z >= 9400 and z <= 9480 and x >= 2490 and x <= 2540:
        return 'skavidCaves'
    if z >= 9400 and z <= 9480 and x >= 2560 and x <= 2623:
        return 'enclave'
    if level == 2 and x >= 2540 and x <= 2552 and z >= 3108 and z <= 3120:
        return 'towerFloor'
    if x >= 2505 and x <= 2519 and z >= 3079 and z <= 3092:
        return 'grewIsland'
    if x >= 2565 and x <= 2585 and z >= 3015 and z <= 3040:
        return 'tobanCamp'
    if x >= 2527 and x <= 2545 and z >= 3027 and z <= 3036:
        return 'cityGuard'
    if x >= 2508 and x <= 2532 and z >= 3005 and z <= 3026:
        return 'lowerCity'
    return 'yanille'

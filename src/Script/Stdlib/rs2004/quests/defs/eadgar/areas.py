"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.defs.trollstronghold.areas import troll_zone

__all__ = ['ER_ITEM', 'LIQUORS', 'ER_LOC', 'ER_NPC', 'CHICKEN_NPC_ID', 'ER_TILE', 'THISTLE_SPOTS', 'SANFEW_START', 'SANFEW_FINISH', 'EADGAR_TALK', 'BURNTMEAT_TALK', 'TEGID_ROBE', 'PETE_WHEN', 'PETE_FEED', 'eadgar_zone', 'committed', 'quest_bank', 'held', 'banked', 'owned', 'worn']

# Why: every unfinished potion displays as "Unfinished potion", so the ranarr vial is addressed by id; a name-keyed withdraw pulls the first unf the bank lists.
ER_ITEM = Record({
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'CLIMBING_BOOTS': Record({'id': 3105, 'name': 'Climbing boots'}),
    'KNIFE': Record({'id': 946, 'name': 'Knife'}),
    'AXE': Record({'id': 1349, 'name': 'Iron axe'}),
    'TINDERBOX': Record({'id': 590, 'name': 'Tinderbox'}),
    'PESTLE': Record({'id': 233, 'name': 'Pestle and mortar'}),
    'LOGS': Record({'id': 1511, 'name': 'Logs'}),
    'RAW_CHICKEN': Record({'id': 2138, 'name': 'Raw chicken'}),
    'GRAIN': Record({'id': 1947, 'name': 'Grain'}),
    'PINEAPPLE': Record({'id': 2114, 'name': 'Pineapple'}),
    'PINEAPPLE_CHUNKS': Record({'id': 2116, 'name': 'Pineapple chunks'}),
    'VODKA': Record({'id': 2015, 'name': 'Vodka'}),
    'ALCO_CHUNKS': Record({'id': 3270, 'name': 'Alco-chunks'}),
    'DRUNK_PARROT': Record({'id': 3266, 'name': 'Drunk parrot'}),
    'DIRTY_ROBE': Record({'id': 3267, 'name': 'Dirty robe'}),
    'FAKE_MAN': Record({'id': 3268, 'name': 'Fake man'}),
    'BURNT_MEAT': Record({'id': 2146, 'name': 'Burnt meat'}),
    'STOREROOM_KEY': Record({'id': 3269, 'name': 'Storeroom key'}),
    'GOUTWEED': Record({'id': 3261, 'name': 'Goutweed'}),
    'THISTLE': Record({'id': 3262, 'name': 'Troll thistle'}),
    'DRIED_THISTLE': Record({'id': 3263, 'name': 'Dried thistle'}),
    'GROUND_THISTLE': Record({'id': 3264, 'name': 'Ground thistle'}),
    'TROLL_POTION': Record({'id': 3265, 'name': 'Troll potion'}),
    'RANARR': Record({'id': 257, 'name': 'Ranarr weed'}),
    'VIAL_WATER': Record({'id': 227, 'name': 'Vial of water'}),
    'RANARR_VIAL': Record({'id': 99, 'name': 'Unfinished potion'}),
})
LIQUORS = [
    ER_ITEM.VODKA,
    Record({'id': 2019, 'name': 'Gin'}),
    Record({'id': 2021, 'name': 'Brandy'}),
    Record({'id': 2017, 'name': 'Whisky'}),
]
ER_LOC = Record({
    'AVIARY_HATCH': 4043,
    'RACK': 3821,
    'KITCHEN_DRAWERS': 3816,
    'KITCHEN_DRAWERS_OPEN': 3817,
    'STOREROOM_DOOR': 3810,
    'GOUTWEED_CRATE': 3822,
    'CAVE_ENTRANCE': 3759,
    'CAVE_EXIT': 3760,
})
ER_NPC = Record({
    'SANFEW': 'Sanfew',
    'EADGAR': 'Eadgar',
    'BURNTMEAT': 'Burntmeat',
    'TEGID': 'Tegid',
    'PETE': 'Parroty Pete',
    'THISTLE': 'Thistle',
    'CHICKEN': 'Chicken',
})
CHICKEN_NPC_ID = 41
ER_TILE = Record({
    'FALADOR_BANK': Tile(2946, 3369, 0),
    'ARDOUGNE_BANK': Tile(2616, 3332, 0),
    'SANFEW': Tile(2897, 3426, 1),
    'JATIX': Tile(2899, 3427, 0),
    'TEGID': Tile(2913, 3417, 0),
    'TENZING': Tile(2820, 3556, 0),
    'CAVE_MOUTH': Tile(2893, 3671, 0),
    'CAVE_INSIDE': Tile(2893, 10074, 2),
    'EADGAR': Tile(2890, 10086, 2),
    'BURNTMEAT': Tile(2844, 10057, 1),
    'KITCHEN_DRAWERS': Tile(2853, 10051, 1),
    'RACK': Tile(2828, 10095, 0),
    'STOREROOM_DOOR_OUT': Tile(2869, 10084, 0),
    'STOREROOM_DOOR_IN': Tile(2869, 10085, 0),
    'GOUTWEED_CRATE': Tile(2856, 10075, 0),
    'PETE': Tile(2611, 3285, 0),
    'AVIARY_HATCH': Tile(2610, 3287, 0),
    'AEMAD': Tile(2613, 3294, 0),
    'HECKEL': Tile(2493, 3488, 1),
    'GULLUCK': Tile(2468, 3487, 2),
    'WISTAN': Tile(2928, 3546, 0),
    'CHICKENS': Tile(2691, 3273, 0),
    'WHEAT': Tile(2647, 3348, 0),
    'TREES': Tile(2605, 3320, 0),
    'TREES_FALADOR': Tile(2920, 3368, 0),
})
THISTLE_SPOTS = [Tile(2883, 3670, 0), Tile(2887, 3675, 0), Tile(2891, 3676, 0), Tile(2892, 3686, 0), Tile(2902, 3674, 0)]
SANFEW_START = Record({
    'npc': ER_NPC.SANFEW,
    'anchor': ER_TILE.SANFEW,
    'leash': 8,
    'prefer': ['Have you any more work for me', "I'll do it."],
})
SANFEW_FINISH = Record({
    'npc': ER_NPC.SANFEW,
    'anchor': ER_TILE.SANFEW,
    'leash': 8,
    'prefer': ['I have some more goutweed for you.', "Actually I don't need to speak to you."],
})
# Why: one stop covers every Eadgar visit; the option offered depends on the stage and no stage offers two of these at once, so one ordered list never picks the wrong branch.
EADGAR_TALK = Record({
    'npc': ER_NPC.EADGAR,
    'anchor': ER_TILE.EADGAR,
    'leash': 10,
    'prefer': ['I need to find some goutweed.', "Okay, I'll be right back.", 'No thanks, Eadgar.', 'More'],
})
BURNTMEAT_TALK = Record({
    'npc': ER_NPC.BURNTMEAT,
    'anchor': ER_TILE.BURNTMEAT,
    'leash': 8,
    'prefer': ['So, where can I get some goutweed?', "I'll be going now."],
})
# Why: "Fine." ends the dialogue with no robe; both of the other two hand one over.
TEGID_ROBE = Record({
    'npc': ER_NPC.TEGID,
    'anchor': ER_TILE.TEGID,
    'leash': 6,
    'prefer': ["Sanfew won't be happy", "You'll give me those robes right now"],
})
# Why: `make_alco_chunks` needs both of Pete's varbits set and each `opnpc1` offers only one of the 3 lines, so the two that matter are 2 visits.
PETE_WHEN = Record({'npc': ER_NPC.PETE, 'anchor': ER_TILE.PETE, 'leash': 8, 'prefer': ['When did you add it?']})
PETE_FEED = Record({'npc': ER_NPC.PETE, 'anchor': ER_TILE.PETE, 'leash': 8, 'prefer': ['What do you feed them?']})


def eadgar_zone(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    level = tile.level
    # Mad Eadgar's cave: mapsquare 45,157 on the level the freed-Eadgar teleport lands on.
    if level == 2 and x >= 2880 and x <= 2943 and z >= 10048 and z <= 10111:
        return 'cave'
    troll = troll_zone(tile)
    if troll == 'stronghold':
        return 'stronghold'
    if troll == 'mainland' or troll == 'unknown':
        return 'mainland'
    return 'trollside'


def committed(zone):
    """True once you're past the stile: no more cheap bank trips."""
    return zone != 'mainland' and zone != 'unknown'


# Why: `nearest` ranks banks by straight line, and from the cave and stronghold at z ~10000 every surface bank is about 6000 tiles away, so the ordering is noise.
# Pin the only practical bank on this side of the map.
def quest_bank(snap):
    """The bank a leg should open: pinned above the stile, nearest anywhere else."""
    return (ER_TILE.FALADOR_BANK if committed(eadgar_zone(snap.tile)) else None)


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

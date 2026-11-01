"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['CB_QUEST', 'CB_STAGE', 'CB_ID', 'CB_NAME', 'BELLOWS_IDS', 'ANY_BELLOWS', 'CB_LOC', 'CB_LOC_ID', 'CB_NPC', 'CB_TILE', 'BOB_AXES', 'GERRANT', 'RANTZ', 'BUGS', 'FYCIE', 'in_bait_zone', 'in_cave']

CB_QUEST = 'Big Chompy Bird Hunting'
CB_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 5,
    'GIVEN_ARROWS': 10,
    'KIDS_PLAY_WITH_TOAD': 15,
    'REMOVED_ROCK': 20,
    'SHOWN_TOAD': 25,
    'DROPPED_TOAD': 30,
    'CHOMPY_SPAWNED': 35,
    'RANTZ_MISSED': 40,
    'GOT_BOW': 45,
    'KILLED_CHOMPY': 50,
    'TOLD_TO_COOK': 55,
    'CHOMPY_COOKED': 60,
    'COMPLETE': 65,
})
CB_ID = Record({
    'ACHEY_LOGS': 2862,
    'SHAFT': 2864,
    'FLIGHTED': 2865,
    'WOLF_BONES': 2859,
    'ARROWTIPS': 2861,
    'ARROW': 2866,
    'BOW': 2883,
    'BELLOWS_EMPTY': 2871,
    'BELLOWS3': 2872,
    'BELLOWS2': 2873,
    'BELLOWS1': 2874,
    'TOAD': 2875,
    'RAW_CHOMPY': 2876,
    'SEASONED_CHOMPY': 2882,
    'RUINED_CHOMPY': 2880,
    'FEATHER': 314,
    'KNIFE': 946,
    'CHISEL': 1755,
    'POTATO': 1942,
    'ONION': 1957,
    'CABBAGE': 1965,
    'TOMATO': 1982,
    'DOOGLE': 1573,
    'EQUA': 2128,
    'COINS': 995,
    'BONES': 526,
})
CB_NAME = Record({
    'ACHEY_LOGS': 'Achey tree logs',
    'SHAFT': 'Ogre arrow shaft',
    'FLIGHTED': 'Flighted ogre arrow',
    'WOLF_BONES': 'Wolf bones',
    'ARROWTIPS': 'Wolfbone arrowtips',
    'ARROW': 'Ogre arrow',
    'BOW': 'Ogre bow',
    'TOAD': 'Bloated toad',
    'RAW_CHOMPY': 'Raw chompy',
    'SEASONED_CHOMPY': 'Seasoned chompy',
    'RUINED_CHOMPY': 'Ruined chompy',
    'FEATHER': 'Feather',
    'KNIFE': 'Knife',
    'CHISEL': 'Chisel',
    'POTATO': 'Potato',
    'ONION': 'Onion',
    'CABBAGE': 'Cabbage',
    'TOMATO': 'Tomato',
    'DOOGLE': 'Doogle leaves',
    'EQUA': 'Equa leaves',
    'COINS': 'Coins',
})
BELLOWS_IDS = [CB_ID.BELLOWS3, CB_ID.BELLOWS2, CB_ID.BELLOWS1]
ANY_BELLOWS = [CB_ID.BELLOWS_EMPTY] + list(BELLOWS_IDS)
CB_LOC = Record({
    'ACHEY': 'Achey Tree',
    'BUBBLES': 'Swamp bubbles',
    'CHEST_LOCKED': 'Locked Ogre chest',
    'CHEST_OPEN': 'Unlocked Ogre chest',
    'SPIT': 'Ogre spit-roast',
    'POTATO': 'Potato',
    'ONION': 'Onion',
    'CABBAGE': 'Cabbage',
})
CB_LOC_ID = Record({'CHEST': 3377, 'CHEST_OPEN': 3378, 'SPIT_EMPTY': 3375})
CB_NPC = Record({
    'RANTZ': 'Rantz',
    'FYCIE': 'Fycie',
    'BUGS': 'Bugs',
    'TOAD': 'Swamp toad',
    'CHOMPY': 'Chompy bird',
    'WOLF': 'Wolf',
})
CB_TILE = Record({
    'RANTZ': Tile(2630, 2981, 0),
    'SPIT': Tile(2630, 2990, 0),
    'CAVE_MOUTH': Tile(2630, 2997, 0),
    'CAVE_ARRIVAL': Tile(2647, 9379, 0),
    'BUGS': Tile(2640, 9391, 0),
    'FYCIE': Tile(2650, 9393, 0),
    'CHEST': Tile(2638, 9397, 0),
    'ACHEY': Tile(2626, 2974, 0),
    'WOLVES': Tile(2607, 2962, 0),
    'BUBBLE': Tile(2598, 2963, 0),
    'SWAMP': Tile(2598, 2962, 0),
    'BAIT': Tile(2636, 2966, 0),
    'POTATO': Tile(2641, 2958, 0),
    'CABBAGE': Tile(2645, 2958, 0),
    'ONION': Tile(2583, 2966, 0),
    'TOMATO': Tile(2584, 2965, 0),
    'EQUA': Tile(2639, 2952, 0),
    'DOOGLE': Tile(2562, 2972, 0),
    'YANILLE_BANK': Tile(2612, 3092, 0),
})
BOB_AXES = Record({'npc': 'Bob', 'anchor': Tile(3232, 3203, 0)})
GERRANT = Record({'npc': 'Gerrant', 'anchor': Tile(3013, 3225, 0)})
RANTZ = Record({
    'npc': CB_NPC.RANTZ,
    'anchor': CB_TILE.RANTZ,
    'leash': 6,
    'prefer': ["Ok, I'll make you some 'stabbers'.", "Ok, I'll make the 'stabbers' for you.", 'Ok, thanks.'],
})
BUGS = Record({
    'npc': CB_NPC.BUGS,
    'anchor': CB_TILE.BUGS,
    'leash': 6,
    'prefer': ["Ok, I'll give you 10 bright pretties.", 'Ok, thanks.'],
})
FYCIE = Record({
    'npc': CB_NPC.FYCIE,
    'anchor': CB_TILE.FYCIE,
    'leash': 6,
    'prefer': ["Ok, I'll give you 50 bright pretties.", 'Ok, thanks.'],
})


# Why: `opheld1,bloated_toad` refuses outside this box with "This is too far away for Rantz to shoot the chompy bird."
def in_bait_zone(t):
    """The clearing the quest will accept bait in, `inzone(0_41_46_7_18, 0_41_46_15_27)`."""
    return t is not None and t.level == 0 and t.x >= 2631 and t.x <= 2639 and t.z >= 2962 and t.z <= 2971


def in_cave(t):
    """Rantz's cave, reached and left by scripted teleports alone."""
    return t is not None and t.z >= 9340 and t.z <= 9410 and t.x >= 2620 and t.x <= 2690

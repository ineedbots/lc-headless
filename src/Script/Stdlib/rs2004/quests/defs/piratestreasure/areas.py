"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile


__all__ = ['PT_QUEST', 'PT_STAGE', 'PT_ID', 'PT_NAME', 'PT_LOC', 'BANANA_TREE_IDS', 'PT_TILE', 'FRANK', 'LUTHAS', 'WYDIN', 'THESSALIA_SHOP', 'ZAMBO_SHOP']

PT_QUEST = "Pirate's Treasure"
PT_STAGE = Record({'NOT_STARTED': 0, 'FETCH_RUM': 1, 'RECEIVED_KEY': 2, 'READ_NOTE': 3, 'COMPLETE': 4})
PT_ID = Record({
    'RUM': 431,
    'CHEST_KEY': 432,
    'PIRATE_MESSAGE': 433,
    'SPADE': 952,
    'COINS': 995,
    'WHITE_APRON': 1005,
    'GARDENER': 1217,
    'BANANA': 1963,
})
PT_NAME = Record({
    'RUM': 'Karamjan rum',
    'CHEST_KEY': 'Chest key',
    'PIRATE_MESSAGE': 'Pirate message',
    'SPADE': 'Spade',
    'COINS': 'Coins',
    'WHITE_APRON': 'White apron',
    'GARDENER': 'Gardener',
    'BANANA': 'Banana',
})
# Why: ordinary `crate` and `crate3` also render "Crate" with op1=Search, and 4 of them stand within 6 tiles of Wydin's grocery crate, so the nearest is rarely the right one.
PT_LOC = Record({'GROCERY_CRATE': 2071, 'BANANA_CRATE': 2072, 'PIRATE_CHEST': 2079})
# Why: a tree keeps the name "Banana Tree" and its Search op down to empty, so matching by name re-picks a bare tree forever; 2078 is the empty one and the 5 with fruit are the only targets.
BANANA_TREE_IDS = [2073, 2074, 2075, 2076, 2077]
PT_TILE = Record({
    'DRAYNOR_BANK': Tile(3093, 3243, 0),
    'FRANK': Tile(3053, 3250, 0),
    'BANANA_CRATE': Tile(2943, 3151, 0),
    'BANANA_GROVE': Tile(2926, 3160, 0),
    'WYDIN': Tile(3014, 3204, 0),
    'GROCERY_CRATE': Tile(3009, 3207, 0),
    'THESSALIA': Tile(3204, 3417, 0),
    'PIRATE_CHEST': Tile(3218, 3396, 1),
    'SPADE_SPAWN': Tile(2981, 3369, 0),
    'DIG_SITE': Tile(2999, 3383, 0),
})
# Why: `redbeard_arr` jumps back to its own option list, so "Arr!" never ends the conversation and the trade line is the only safe way to close it.
FRANK = Record({
    'npc': 'Redbeard Frank',
    'anchor': PT_TILE.FRANK,
    'leash': 6,
    'prefer': ["I'm in search of treasure.", "Ok thanks, I'll go and get it.", 'Do you have anything for trade?'],
})
# Why: "Will you pay me for another crate full?" re-employs at the plantation, which the quest never needs twice, so the thanks line is preferred ahead of it.
LUTHAS = Record({
    'npc': 'Luthas',
    'anchor': Tile(2939, 3154, 0),
    'leash': 6,
    'prefer': [
    'Could you offer me employment on your plantation?',
    "Thank you, I'll be on my way",
    "No, the crate isn't full yet.",
],
})
WYDIN = Record({
    'npc': 'Wydin',
    'anchor': PT_TILE.WYDIN,
    'leash': 6,
    'prefer': ['Can I get a job here?', "No, it's a complete mess"],
})
THESSALIA_SHOP = Record({'npc': 'Thessalia', 'anchor': PT_TILE.THESSALIA})
ZAMBO_SHOP = Record({'npc': 'Zambo', 'anchor': Tile(2925, 3143, 0)})

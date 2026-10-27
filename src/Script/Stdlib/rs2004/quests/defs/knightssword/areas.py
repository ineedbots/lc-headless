"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile


__all__ = ['KS_QUEST', 'KS_STAGE', 'KS_ID', 'KS_NAME', 'KS_TILE', 'VYVIN_APPROACHES', 'BLURITE_ROCKS', 'SQUIRE', 'RELDO', 'THURGO', 'WYDIN', 'GENERAL_STORE']

KS_QUEST = "The Knight's Sword"
KS_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_RELDO': 2,
    'GIVEN_PIE': 3,
    'SPOKEN_THURGO': 4,
    'LOOKING_PORTRAIT': 5,
    'LOOKING_BLURITE': 6,
    'COMPLETE': 7,
})
KS_ID = Record({
    'PORTRAIT': 666,
    'BLURITE_SWORD': 667,
    'BLURITE_ORE': 668,
    'IRON_BAR': 2351,
    'IRON_ORE': 440,
    'PIE_DISH': 2313,
    'PIE_SHELL': 2315,
    'UNCOOKED_PIE': 2321,
    'REDBERRY_PIE': 2325,
    'BURNT_PIE': 2329,
    'PASTRY_DOUGH': 1953,
    'REDBERRIES': 1951,
    'POT_OF_FLOUR': 1933,
    'BUCKET': 1925,
    'BUCKET_OF_WATER': 1929,
})
KS_NAME = Record({
    'PORTRAIT': 'Portrait',
    'BLURITE_SWORD': 'Blurite sword',
    'BLURITE_ORE': 'Blurite ore',
    'IRON_BAR': 'Iron bar',
    'IRON_ORE': 'Iron ore',
    'PIE_DISH': 'Pie dish',
    'PIE_SHELL': 'Pie shell',
    'UNCOOKED_PIE': 'Uncooked berry pie',
    'REDBERRY_PIE': 'Redberry pie',
    'BURNT_PIE': 'Burnt pie',
    'PASTRY_DOUGH': 'Pastry dough',
    'REDBERRIES': 'Redberries',
    'POT_OF_FLOUR': 'Pot of flour',
    'BUCKET': 'Bucket',
    'BUCKET_OF_WATER': 'Bucket of water',
})
KS_TILE = Record({
    'FALADOR_BANK': Tile(2946, 3369, 0),
    'FURNACE': Tile(2975, 3368, 0),
    'VYVIN_ROOM': Tile(2985, 3335, 2),
    'VYVIN_RETREAT': Tile(2980, 3340, 2),
    'GENERAL_STORE': Tile(3218, 3415, 0),
    'PIE_DISH_SPAWN': Tile(3222, 3494, 0),
    'KITCHEN_SINK': Tile(3224, 3494, 0),
    'WYDIN': Tile(3014, 3204, 0),
    'RANGE': Tile(3019, 3237, 0),
    'IRON_ROCKS': Tile(2972, 3239, 0),
    'PICKAXE_SPAWN': Tile(2963, 3216, 0),
    'LADDER_BOTTOM': Tile(3008, 9551, 0),
})
# Why: the cupboard spans (2984,3336)-(2985,3336) and only its south side is legal, so these 2 tiles are the approach.
# Why: the one further from Sir Vyvin is the one whose search lands.
VYVIN_APPROACHES = [Tile(2985, 3335, 2), Tile(2984, 3335, 2)]
BLURITE_ROCKS = [Tile(3049, 9566, 0), Tile(3059, 9564, 0), Tile(3067, 9581, 0), Tile(3067, 9582, 0)]
SQUIRE = Record({
    'npc': 'Squire',
    'anchor': Tile(2977, 3342, 0),
    'leash': 6,
    'prefer': [
    'And how is life as a squire?',
    'I can make a new sword if you like',
    'So would these dwarves make another one?',
    "Ok, I'll give it a go.",
],
})
RELDO = Record({
    'npc': 'Reldo',
    'anchor': Tile(3209, 3495, 0),
    'leash': 6,
    'prefer': ['What do you know about the Imcando dwarves?'],
})
THURGO = Record({
    'npc': 'Thurgo',
    'anchor': Tile(3001, 3144, 0),
    'leash': 6,
    'prefer': [
    'Would you like a redberry pie?',
    'Would you like some redberry pie?',
    'About that sword...',
    'Can you make me a special sword?',
    'Hello. Are you an Imcando dwarf?',
],
})
WYDIN = Record({'npc': 'Wydin', 'anchor': KS_TILE.WYDIN})
GENERAL_STORE = Record({'npc': 'Shop keeper', 'anchor': KS_TILE.GENERAL_STORE})

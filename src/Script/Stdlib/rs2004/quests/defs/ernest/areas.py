"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile


__all__ = ['EC_QUEST', 'EC_STAGE', 'EC_ID', 'EC_NAME', 'EC_TILE', 'VERONICA', 'ODDENSTEIN']

EC_QUEST = 'Ernest the Chicken'
EC_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'SPOKEN_ODDENSTEIN': 2, 'COMPLETE': 3})
EC_ID = Record({
    'PRESSURE_GAUGE': 271,
    'FISH_FOOD': 272,
    'POISON': 273,
    'POISONED_FISH_FOOD': 274,
    'CLOSET_KEY': 275,
    'RUBBER_TUBE': 276,
    'OIL_CAN': 277,
    'SPADE': 952,
})
EC_NAME = Record({
    'PRESSURE_GAUGE': 'Pressure gauge',
    'FISH_FOOD': 'Fish food',
    'POISON': 'Poison',
    'POISONED_FISH_FOOD': 'Poisoned fish food',
    'CLOSET_KEY': 'Key',
    'RUBBER_TUBE': 'Rubber tube',
    'OIL_CAN': 'Oil can',
    'SPADE': 'Spade',
})
EC_TILE = Record({
    'DRAYNOR_BANK': Tile(3093, 3243, 0),
    'SPADE_SPAWN': Tile(3120, 3359, 0),
    'POISON_SPAWN': Tile(3097, 3366, 0),
    'FISH_FOOD_SPAWN': Tile(3108, 3356, 1),
    'COMPOST_STAND': Tile(3085, 3360, 0),
    'FOUNTAIN_STAND': Tile(3087, 3336, 0),
    'CLOSET_STAND': Tile(3107, 3367, 0),
    'CLOSET_INSIDE': Tile(3108, 3367, 0),
    'RUBBER_TUBE_SPAWN': Tile(3111, 3367, 0),
    'BOOKCASE_STAND': Tile(3098, 3358, 0),
    'ALCOVE': Tile(3096, 3358, 0),
    'ALCOVE_LEVER': Tile(3096, 3357, 0),
    'LADDER_DOWN_STAND': Tile(3092, 3363, 0),
    'BASEMENT_LANDING': Tile(3116, 9754, 0),
    'LADDER_UP_STAND': Tile(3117, 9755, 0),
    'OIL_CAN_SPAWN': Tile(3092, 9755, 0),
})
VERONICA = Record({
    'npc': 'Veronica',
    'anchor': Tile(3110, 3330, 0),
    'leash': 6,
    'prefer': ["Aha, sounds like a quest. I'll help."],
})
ODDENSTEIN = Record({
    'npc': 'Professor Oddenstein',
    'anchor': Tile(3110, 3367, 2),
    'leash': 6,
    'prefer': [
    "I'm looking for a guy called Ernest.",
    'Change him back this instant!',
    "I'm glad Veronica didn't actually get engaged to a chicken.",
],
})

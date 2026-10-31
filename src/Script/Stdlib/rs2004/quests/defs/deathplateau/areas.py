"""Ported from rs2b0t's src/bot/api/ai/quests/defs/deathplateau/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['FALADOR_WEST_BANK', 'DEATH_ITEM', 'PEDESTALS', 'BALL_PICKUP', 'ALL_BALL_IDS', 'TILE', 'BLURBERRY_SHOP', 'TOSTIG_SHOP', 'DENULTH_START', 'DENULTH_FINISH', 'EOHRIC_GUARD', 'EOHRIC_HAROLD_REFUSED', 'HAROLD_DUTY', 'SABA_PATH', 'TENZING_HELP', 'TENZING_SUPPLIES', 'DUNSTAN_SPIKES', 'DEATH_DICE_MAIN', 'HAROLD_DOOR', 'HAROLD_PURSE_START', 'MAX_BET', 'COIN_FLOAT', 'GAMBLE_STAKE_FLOAT', 'ALE_PRICE']

FALADOR_WEST_BANK = Tile(2946, 3369, 0)
DEATH_ITEM = Record({
    'ASGARNIAN_ALE': Record({'id': 1905, 'name': 'Asgarnian ale'}),
    'BLURBERRY_SPECIAL': Record({'id': 2064, 'name': 'Blurberry special'}),
    'PREMADE_BLURBERRY_SPECIAL': Record({'id': 2028, 'name': 'Blurberry special'}),
    'IOU': Record({'id': 3103, 'name': 'Iou'}),
    'COMBINATION': Record({'id': 3102, 'name': 'Combination'}),
    'SECRET_MAP': Record({'id': 3104, 'name': 'Secret way map'}),
    'CLIMBING_BOOTS': Record({'id': 3105, 'name': 'Climbing boots'}),
    'SPIKED_BOOTS': Record({'id': 3107, 'name': 'Spiked boots'}),
    'ENTRANCE_CERT': Record({'id': 3114, 'name': 'Certificate'}),
    'BREAD': Record({'id': 2309, 'name': 'Bread'}),
    'TROUT': Record({'id': 333, 'name': 'Trout'}),
    'IRON_BAR': Record({'id': 2351, 'name': 'Iron bar'}),
    'BALL_YELLOW': Record({'id': 3111, 'name': 'Stone ball', 'ground': Tile(2893, 3561, 0)}),
    'BALL_GREEN': Record({'id': 3113, 'name': 'Stone ball', 'ground': Tile(2893, 3562, 0)}),
    'BALL_PURPLE': Record({'id': 3112, 'name': 'Stone ball', 'ground': Tile(2893, 3563, 0)}),
    'BALL_BLUE': Record({'id': 3110, 'name': 'Stone ball', 'ground': Tile(2893, 3564, 0)}),
    'BALL_RED': Record({'id': 3109, 'name': 'Stone ball', 'ground': Tile(2893, 3565, 0)}),
})
PEDESTALS = [
    Record({'ball_id': DEATH_ITEM.BALL_BLUE.id, 'color': 'blue', 'at': Tile(2894, 3562, 0)}),
    Record({'ball_id': DEATH_ITEM.BALL_YELLOW.id, 'color': 'yellow', 'at': Tile(2895, 3562, 0)}),
    Record({'ball_id': DEATH_ITEM.BALL_RED.id, 'color': 'red', 'at': Tile(2894, 3563, 0)}),
    Record({'ball_id': DEATH_ITEM.BALL_PURPLE.id, 'color': 'purple', 'at': Tile(2895, 3563, 0)}),
    Record({'ball_id': DEATH_ITEM.BALL_GREEN.id, 'color': 'green', 'at': Tile(2895, 3564, 0)}),
]
BALL_PICKUP = [
    Record({'id': DEATH_ITEM.BALL_YELLOW.id, 'at': DEATH_ITEM.BALL_YELLOW.ground}),
    Record({'id': DEATH_ITEM.BALL_GREEN.id, 'at': DEATH_ITEM.BALL_GREEN.ground}),
    Record({'id': DEATH_ITEM.BALL_PURPLE.id, 'at': DEATH_ITEM.BALL_PURPLE.ground}),
    Record({'id': DEATH_ITEM.BALL_BLUE.id, 'at': DEATH_ITEM.BALL_BLUE.ground}),
    Record({'id': DEATH_ITEM.BALL_RED.id, 'at': DEATH_ITEM.BALL_RED.ground}),
]
ALL_BALL_IDS = [b.id for b in BALL_PICKUP]
TILE = Record({
    'DENULTH': Tile(2896, 3528, 0),
    'EOHRIC': Tile(2902, 3565, 1),
    'HAROLD': Tile(2905, 3539, 1),
    'HAROLD_DOOR': Tile(2907, 3544, 1),
    'HAROLD_DOOR_LOC': Tile(2906, 3543, 1),
    'TOSTIG': Tile(2910, 3537, 0),
    'DUNSTAN': Tile(2919, 3574, 0),
    'TENZING': Tile(2820, 3556, 0),
    'TENZING_DOOR': Tile(2823, 3555, 0),
    'TENZING_BACK': Tile(2820, 3558, 0),
    'STILE_NORTH': Tile(2817, 3564, 0),
    'STILE_SOUTH': Tile(2817, 3561, 0),
    'SABA_ENTRANCE': Tile(2858, 3577, 0),
    'SABA_INSIDE': Tile(2270, 4759, 0),
    'SABA_EXIT': Tile(2269, 4752, 0),
    'STONE_STAND': Tile(2894, 3563, 0),
    'SCOUT': Tile(2864, 3609, 0),
    'CASTLE_DOOR': Tile(2899, 3558, 0),
    'CASTLE_STAIRS_BOTTOM': Tile(2896, 3566, 0),
    'CASTLE_STAIRS_TOP': Tile(2897, 3569, 1),
    'INN_STAIRS_BOTTOM': Tile(2914, 3538, 0),
    'INN_STAIRS_TOP': Tile(2914, 3542, 1),
})
BLURBERRY_SHOP = Record({'npc': 'Barman', 'anchor': Tile(2482, 3488, 1)})
TOSTIG_SHOP = Record({'npc': 'Tostig', 'anchor': TILE.TOSTIG})
DENULTH_START = Record({
    'npc': 'Denulth',
    'anchor': TILE.DENULTH,
    'leash': 8,
    'prefer': [
    'Do you have any quests for me?',
    'No but perhaps I could try and find one?',
    'Can you remind me of the quest I am on?',
],
})
DENULTH_FINISH = Record({'npc': 'Denulth', 'anchor': TILE.DENULTH, 'leash': 8, 'prefer': []})
EOHRIC_GUARD = Record({
    'npc': 'Eohric',
    'anchor': TILE.EOHRIC,
    'leash': 8,
    'prefer': ["I'm looking for the guard that was on last night."],
})
EOHRIC_HAROLD_REFUSED = Record({'npc': 'Eohric', 'anchor': TILE.EOHRIC, 'leash': 8, 'prefer': []})
HAROLD_DUTY = Record({
    'npc': 'Harold',
    'anchor': TILE.HAROLD,
    'leash': 5,
    'prefer': ["You're the guard that was on duty last night?"],
})
SABA_PATH = Record({
    'npc': 'Saba',
    'anchor': TILE.SABA_INSIDE,
    'leash': 8,
    'prefer': ['Do you know of another way up Death Plateau?'],
})
TENZING_HELP = Record({'npc': 'Tenzing', 'anchor': TILE.TENZING, 'leash': 8, 'prefer': ["OK, I'll get those for you."]})
TENZING_SUPPLIES = Record({'npc': 'Tenzing', 'anchor': TILE.TENZING, 'leash': 8, 'prefer': []})
DUNSTAN_SPIKES = Record({
    'npc': 'Dunstan',
    'anchor': TILE.DUNSTAN,
    'leash': 8,
    'prefer': ['Tenzing has asked me to bring you his climbing boots', 'Yes, but I still want them.'],
})
DEATH_DICE_MAIN = 6675
HAROLD_DOOR = Record({'id': 3747, 'x': 2906, 'z': 3543, 'level': 1})
HAROLD_PURSE_START = 100
MAX_BET = 1000
COIN_FLOAT = 2000
GAMBLE_STAKE_FLOAT = HAROLD_PURSE_START + 1
ALE_PRICE = 5

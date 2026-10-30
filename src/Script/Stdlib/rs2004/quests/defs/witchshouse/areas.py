"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['WITCHS_HOUSE_QUEST', 'WH_OBJ', 'WH_NAME', 'WH_LOC', 'WH_NPC', 'EXPERIMENT_IDS', 'EXPERIMENT_NAMES', 'WH_TILE', 'BOY', 'WYDIN', 'THESSALIA', 'SHOP_GP', 'FALADOR_WEST_BANK', 'in_garden', 'in_shed', 'in_porch']

WITCHS_HOUSE_QUEST = "Witch's House"
WH_OBJ = Record({
    'GLOVES': 1059,
    'CHEESE': 1985,
    'BALL': 2407,
    'DIARY': 2408,
    'DOOR_KEY': 2409,
    'MAGNET': 2410,
    'SHED_KEY': 2411,
})
WH_NAME = Record({'GLOVES': 'Leather gloves', 'CHEESE': 'Cheese'})
WH_LOC = Record({
    'FRONT_DOOR': 2861,
    'BACK_DOOR': 2862,
    'SHED_DOOR': 2863,
    'FOUNTAIN': 2864,
    'POT': 2867,
    'CUPBOARD_SHUT': 2868,
    'CUPBOARD_OPEN': 2869,
    'MOUSE_HOLE': 2870,
})
WH_NPC = Record({'BOY': 895, 'MOUSE': 901})
EXPERIMENT_IDS = [897, 898, 899, 900]
EXPERIMENT_NAMES = [
    'Witches experiment',
    'Witches experiment second form',
    'Witches experiment third form',
    'Witches experiment fourth form',
]
WH_TILE = Record({
    'BOY': Tile(2928, 3456, 0),
    'POT': Tile(2899, 3474, 0),
    'CUPBOARD': Tile(2899, 9873, 0),
    'PORCH': Tile(2902, 3466, 0),
    'DIARY': Tile(2901, 3473, 1),
    'FOUNTAIN': Tile(2911, 3470, 0),
    'SHED_DOOR': Tile(2933, 3463, 0),
    'BALL': Tile(2935, 3461, 0),
    'THROWN_OUT': Tile(2929, 3456, 0),
})
BOY = Record({
    'npc': 'Boy',
    'anchor': WH_TILE.BOY,
    'leash': 6,
    'prefer': ["What's the matter?", "Ok, I'll see what I can do."],
})
# Why: both keepers carry `op3=Trade`, so the buy step's `Shop.open` reaches the counter without driving the dialogue.
WYDIN = Record({'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)})
THESSALIA = Record({'npc': 'Thessalia', 'anchor': Tile(3204, 3417, 0)})
SHOP_GP = 200
FALADOR_WEST_BANK = Tile(2946, 3369, 0)


def within(t, x0, x1, z0, z1, level):
    return not not t and t.level == level and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


# Why: a flood over the collision pack puts the walkable garden in 3 strips; the hedges seal everything between them, and the witch's patrol lane is a 4th strip nothing can reach.
def in_garden(t):
    """Past the back door: the ring corridor and the fountain yard it leads to."""
    return within(t, 2901, 2933, 3460, 3465, 0) or within(t, 2912, 2933, 3466, 3466, 0) or within(t, 2908, 2912, 3467, 3475, 0)


def in_shed(t):
    """Past the shed door, where the ball and the shapeshifter are."""
    return within(t, 2934, 2937, 3459, 3467, 0)


def in_porch(t):
    """The 4 porch tiles the mouse hole is reachable from."""
    return within(t, 2901, 2902, 3466, 3467, 0)

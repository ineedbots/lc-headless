"""Ported from rs2b0t's src/bot/api/ai/quests/defs/seaslug/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['SS_OBJ', 'SS_ITEM', 'SS_LOC', 'SS_TILE', 'KHAZARD_SHOP', 'CAROLINE', 'HOLGART_LAND', 'HOLGART_PLATFORM', 'HOLGART_ISLAND', 'BAILEY', 'KENT', 'on_platform', 'on_island']

SS_OBJ = Record({
    'TORCH_LIT': 594,
    'TORCH_UNLIT': 596,
    'DAMP_STICKS': 1467,
    'DRY_STICKS': 1468,
    'BROKEN_GLASS': 1469,
    'SWAMP_PASTE': 1941,
})
SS_ITEM = Record({
    'DAMP_STICKS': 'Damp sticks',
    'DRY_STICKS': 'Dry sticks',
    'BROKEN_GLASS': 'Broken glass',
    'SWAMP_PASTE': 'Swamp paste',
})
SS_LOC = Record({'LADDER_UP': 2517, 'LOOSE_PANEL': 2518, 'CRATES': 2519, 'CRANE': 2520, 'LADDER_DOWN': 1746})
SS_TILE = Record({
    'BANK': Tile(2655, 3283, 0),
    'CAROLINE': Tile(2716, 3302, 0),
    'HOLGART_LAND': Tile(2720, 3306, 0),
    'SHORE': Tile(2722, 3305, 0),
    'KHAZARD_SHOP': Tile(2641, 3171, 0),
    'PLATFORM_ARRIVE': Tile(2782, 3273, 0),
    'HOLGART_PLATFORM': Tile(2782, 3276, 0),
    'BAILEY': Tile(2763, 3277, 0),
    'LADDER_FOOT': Tile(2784, 3286, 0),
    'DAMP_STICKS_SPAWN': Tile(2784, 3289, 0),
    'BROKEN_GLASS_SPAWN': Tile(2765, 3289, 0),
    'LADDER_TOP': Tile(2784, 3286, 1),
    'CRATES_STAND': Tile(2764, 3286, 1),
    'PANEL_STAND': Tile(2766, 3288, 1),
    'CRANE_STAND': Tile(2769, 3290, 1),
    'ISLAND_ARRIVE': Tile(2800, 3320, 0),
    'KENT': Tile(2794, 3321, 0),
    'HOLGART_ISLAND': Tile(2798, 3321, 0),
})
KHAZARD_SHOP = Record({'npc': 'Shop keeper', 'anchor': SS_TILE.KHAZARD_SHOP})
CAROLINE = Record({'npc': 'Caroline', 'anchor': SS_TILE.CAROLINE, 'leash': 6, 'prefer': ['I suppose so, how do I get there?']})
HOLGART_LAND = Record({
    'npc': 'Holgart',
    'anchor': SS_TILE.HOLGART_LAND,
    'leash': 6,
    'prefer': ['Okay, lets do it.', "Okay, let's do it.", 'Will you take me there?'],
})
HOLGART_PLATFORM = Record({'npc': 'Holgart', 'anchor': SS_TILE.HOLGART_PLATFORM, 'leash': 6, 'prefer': ["Okay, let's go back."]})
HOLGART_ISLAND = Record({'npc': 'Holgart', 'anchor': SS_TILE.HOLGART_ISLAND, 'leash': 8, 'prefer': []})
BAILEY = Record({'npc': 'Bailey', 'anchor': SS_TILE.BAILEY, 'leash': 8, 'prefer': []})
KENT = Record({'npc': 'Kent', 'anchor': SS_TILE.KENT, 'leash': 8, 'prefer': []})


def on_platform(tile):
    return tile is not None and tile is not None and tile.x >= 2758 and tile.x <= 2798 and tile.z >= 3268 and tile.z <= 3294


def on_island(tile):
    return tile is not None and tile is not None and tile.x >= 2786 and tile.x <= 2804 and tile.z >= 3310 and tile.z <= 3328

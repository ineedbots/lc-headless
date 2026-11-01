"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile

__all__ = ['SM_QUEST', 'SM_STAGE', 'SM_VARP', 'SM_ID', 'SM_NAME', 'SM_LOC', 'SM_LOC_ID', 'is_temple_wall', 'SM_TILE', 'VARROCK_GENERAL', 'SM_NPC', 'SM_NPC_ID', 'RAZMIRE_STOP', 'ULSQUIRE_STOP', 'in_mortton', 'in_temple_zone']

SM_QUEST = 'Shades of Mortton'
SM_STAGE = Record({
    'NOT_STARTED': 0,
    'READ_DIARY': 5,
    'MADE_SERUM': 10,
    'KILL_SHADES': 15,
    'KILLED_1': 20,
    'KILLED_2': 25,
    'KILLED_3': 30,
    'KILLED_4': 35,
    'KILLED_5': 40,
    'SHADES_TO_RAZMIRE': 45,
    'SHADES_TO_ULSQUIRE': 47,
    'ULSQUIRE_TEMPLE': 50,
    'REBUILD_TEMPLE': 55,
    'CAN_LIGHT_ALTAR': 60,
    'CREATED_SACRED_OIL': 65,
    'CREATED_PYRE_LOGS': 70,
    'LOGS_ON_PYRE': 75,
    'LIT_PYRE': 80,
    'COMPLETE': 85,
})
# Why: `%morttonquest` isn't transmitted but the 3 flamtaer meters are, so the temple leg reads its progress off varps without flashing the journal every tick.
SM_VARP = Record({'TEMPLE_REPAIRED': 343, 'TEMPLE_RESOURCES': 344, 'TEMPLE_SANCTITY': 345})
SM_ID = Record({
    'COINS': 995,
    'DIARY': 3395,
    'UNID_TARROMIN': 203,
    'TARROMIN': 253,
    'TARROMIN_UNF': 95,
    'VIAL_WATER': 227,
    'VIAL_EMPTY': 229,
    'ASHES': 592,
    'ASHES_VIAL': 3406,
    'SERUM4': 3408,
    'SERUM3': 3410,
    'SERUM2': 3412,
    'SERUM1': 3414,
    'SERUM_PERM4': 3416,
    'SERUM_PERM3': 3417,
    'SERUM_PERM2': 3418,
    'SERUM_PERM1': 3419,
    'REMAINS': 3396,
    'LIMESTONE_BRICK': 3420,
    'PLANK': 960,
    'SWAMP_PASTE': 1941,
    'OLIVE_OIL4': 3422,
    'OLIVE_OIL3': 3424,
    'OLIVE_OIL2': 3426,
    'OLIVE_OIL1': 3428,
    'SACRED_OIL4': 3430,
    'SACRED_OIL3': 3432,
    'SACRED_OIL2': 3434,
    'SACRED_OIL1': 3436,
    'LOGS': 1511,
    'PYRE_LOGS': 3438,
    'HAMMER': 2347,
    'TINDERBOX': 590,
    'ROTTEN_FOOD': 2959,
    'UNID_ROGUES_PURSE': 1533,
})
SM_NAME = Record({
    'COINS': 'Coins',
    'DIARY': 'Diary',
    'TARROMIN': 'Tarromin',
    'VIAL_WATER': 'Vial of water',
    'VIAL_EMPTY': 'Vial',
    'ASHES': 'Ashes',
    'REMAINS': 'Loar remains',
    'LIMESTONE_BRICK': 'Limestone brick',
    'PLANK': 'Plank',
    'SWAMP_PASTE': 'Swamp paste',
    'OLIVE_OIL3': 'Olive oil(3)',
    'LOGS': 'Logs',
    'PYRE_LOGS': 'Pyre logs',
    'HAMMER': 'Hammer',
    'TINDERBOX': 'Tinderbox',
})
SM_LOC = Record({
    'SHELF': 'Shelf',
    'TABLE': 'Smashed table',
    'SINK': 'Sink',
    'DEAD_TREE': 'Dead tree',
    'BROKEN_WALL': 'Broken Wall',
    'TEMPLE_WALL': 'Temple wall',
    'ALTAR_UNLIT': 'Fire altar',
    'ALTAR_LIT': 'Flaming Fire altar',
    'ALTAR_BROKEN': 'Broken fire altar',
    'PYRE': 'Funeral Pyre',
})
SM_LOC_ID = Record({
    'SHELF': 4062,
    'TABLE': 4064,
    'SINK': 4063,
    'WALL_BASE': 4068,
    'WALL_DONE': 4078,
    'CORNER_BASE': 4079,
    'CORNER_DONE': 4089,
    'ALTAR_LIT': 4090,
    'ALTAR_UNLIT': 4091,
    'ALTAR_BROKEN': 4092,
    'PYRE_EMPTY': 4093,
    'PYRE_LOGS': 4094,
    'PYRE_BONES': 4100,
})


def is_temple_wall(id):
    """Every piece of the temple shell, at any repair level."""
    return (id >= SM_LOC_ID.WALL_BASE and id <= SM_LOC_ID.WALL_DONE) or (id >= SM_LOC_ID.CORNER_BASE and id <= SM_LOC_ID.CORNER_DONE)


SM_TILE = Record({
    'SHELF': Tile(3481, 3279, 0),
    'TABLE': Tile(3482, 3278, 0),
    'VIALS': Tile(3481, 3278, 0),
    'SINK': Tile(3495, 3289, 0),
    'DEAD_TREE': Tile(3491, 3289, 0),
    'RAZMIRE': Tile(3489, 3296, 0),
    'ULSQUIRE': Tile(3496, 3289, 0),
    'TOWN': Tile(3490, 3290, 0),
    'TEMPLE_DOOR': Tile(3506, 3314, 0),
    'TEMPLE_INSIDE': Tile(3506, 3315, 0),
    'ALTAR': Tile(3506, 3316, 0),
    'PYRE': Tile(3506, 3274, 0),
    'VARROCK_LOGS': Tile(3243, 3396, 0),
    'VARROCK_BANK': Tile(3253, 3420, 0),
})
VARROCK_GENERAL = Record({'npc': 'Shop keeper', 'anchor': Tile(3218, 3414, 0)})
# Why: Serum changes each villager's name for 200 ticks, so queries accept both forms.
SM_NPC = Record({
    'RAZMIRE': 'Razmire Keelgan',
    'RAZMIRE_AFFLICTED': 'Afflicted(Razmire)',
    'ULSQUIRE': 'Ulsquire Shauncy',
    'ULSQUIRE_AFFLICTED': 'Afflicted(Ulsquire)',
    'SHADOW': 'Loar Shadow',
    'SHADE': 'Loar Shade',
})
SM_NPC_ID = Record({'SHADOW': 1240, 'SHADE': 1241})
RAZMIRE_STOP = Record({
    'npc': SM_NPC.RAZMIRE,
    'anchor': SM_TILE.RAZMIRE,
    'leash': 6,
    'prefer': [
    'Yes, I have actually!',
    "Yes, I'll dispatch those dark and evil creatures.",
    'What are all these shadow creatures?',
    'Ok, thanks.',
],
})
ULSQUIRE_STOP = Record({
    'npc': SM_NPC.ULSQUIRE,
    'anchor': SM_TILE.ULSQUIRE,
    'leash': 6,
    'prefer': ['What can you tell me about that temple?', 'Ok thanks', 'Ok, thanks.'],
})


def in_mortton(t):
    """The Mort'ton map square, everything this quest does happens inside it."""
    return not not t and t.level == 0 and t.x >= 3456 and t.x <= 3519 and t.z >= 3264 and t.z <= 3327


# Why: Razmire's ai_timer only recomputes the 3 flamtaer meters for players in this zone, so a reading outside it is stale.
def in_temple_zone(t):
    """The `mortton_temple_zones` coord pair the overlay update tests."""
    return not not t and t.level == 0 and t.x >= 3492 and t.x <= 3518 and t.z >= 3308 and t.z <= 3323

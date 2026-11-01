"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop, LadderHop

__all__ = ['HERO_NAME', 'HERO_ID', 'HERO_NAMED', 'HERO_NPC', 'HERO_LOC', 'HERO_TILE', 'ACHIETTIES', 'KATRINE_TASK', 'KATRINE_ARMBAND', 'STRAVEN_TASK', 'STRAVEN_ARMBAND', 'TROBERT', 'ALFONSE', 'CHARLIE', 'VELRAK', 'GERRANT', 'HERO_SAY', 'GRIP', 'HERO_SHOP', 'TAVERLEY_HOP_DOWN', 'TAVERLEY_HOP_UP', 'WWM_HOP_DOWN', 'WWM_HOP_UP', 'HERO_HOPS', 'in_kitchen', 'in_garden', 'in_yard', 'in_side_room', 'in_treasure_room', 'in_store_corridor', 'in_west_wing', 'in_mansion', 'in_brimhaven_hq', 'in_taverley_dungeon', 'in_velrak_cell', 'in_deep_dungeon', 'in_wwm_dungeon', 'on_entrana']

HERO_NAME = "Hero's Quest"
HERO_ID = Record({
    'COINS': 995,
    'MISC_KEY': 1586,
    'GRIP_KEYS': 1588,
    'ID_PAPERS': 1584,
    'CANDLESTICK': 1577,
    'ARMBAND': 1579,
    'BLACK_PLATEBODY': 1125,
    'BLACK_PLATELEGS': 1077,
    'BLACK_FULL_HELM': 1165,
    'OAK_LONGBOW': 845,
    'STEEL_ARROW': 886,
    'ICE_GLOVES': 1580,
    'FEATHER': 1583,
    'SLIME': 1581,
    'BLAMISH_OIL': 1582,
    'UNID_HARRALANDER': 205,
    'HARRALANDER': 255,
    'VIAL_WATER': 227,
    'VIAL_EMPTY': 229,
    'HARRALANDER_VIAL': 97,
    'FISHING_ROD': 307,
    'OILY_ROD': 1585,
    'FISHING_BAIT': 313,
    'RAW_LAVA_EEL': 2148,
    'LAVA_EEL': 2149,
    'JAIL_KEY': 1591,
    'DUSTY_KEY': 1590,
    'TINDERBOX': 590,
    'LOGS': 1511,
})
HERO_NAMED = Record({
    'MISC_KEY': 'Miscellaneous key',
    'GRIP_KEYS': "Grips' keyring",
    'ID_PAPERS': 'Id papers',
    'CANDLESTICK': "Pete's candlestick",
    'ARMBAND': "Thieves' armband",
    'BLACK_PLATEBODY': 'Black platebody',
    'BLACK_PLATELEGS': 'Black platelegs',
    'BLACK_FULL_HELM': 'Black full helm',
    'OAK_LONGBOW': 'Oak longbow',
    'STEEL_ARROW': 'Steel arrow',
    'ICE_GLOVES': 'Ice gloves',
    'FEATHER': 'Fire feather',
    'SLIME': 'Blamish snail slime',
    'BLAMISH_OIL': 'Blamish oil',
    'UNID_HERB': 'Herb',
    'HARRALANDER': 'Harralander',
    'VIAL_WATER': 'Vial of water',
    'VIAL_EMPTY': 'Vial',
    'HARRALANDER_VIAL': 'Unfinished potion',
    'FISHING_ROD': 'Fishing rod',
    'OILY_ROD': 'Oily fishing rod',
    'FISHING_BAIT': 'Fishing bait',
    'RAW_LAVA_EEL': 'Raw lava eel',
    'LAVA_EEL': 'Lava eel',
    'JAIL_KEY': 'Jail key',
    'DUSTY_KEY': 'Dusty key',
    'TINDERBOX': 'Tinderbox',
    'LOGS': 'Logs',
    'COINS': 'Coins',
})
HERO_NPC = Record({
    'ACHIETTIES': 796,
    'KATRINE': 642,
    'STRAVEN': 644,
    'GRUBOR': 789,
    'TROBERT': 790,
    'ALFONSE': 793,
    'CHARLIE': 794,
    'GARV': 788,
    'GRIP': 792,
    'PIRATE_GUARD': 799,
    'ICE_QUEEN': 795,
    'FIREBIRD': 139,
    'CHAOS_DRUID': 181,
    'LAVA_FISH': 800,
    'JAILER': 201,
    'VELRAK': 798,
    'GERRANT': 558,
    'JATIX': 587,
    'LOWE': 550,
    'VALAINE': 536,
    'HORVIK': 549,
})
HERO_LOC = Record({
    'TREASURE_DOOR': 2621,
    'SIDE_DOOR': 2622,
    'GRUBOR_DOOR': 2626,
    'GARV_DOOR': 2627,
    'KITCHEN_DOOR': 2628,
    'KITCHEN_PANEL': 2629,
    'CHEST_SHUT': 2632,
    'CHEST_OPEN': 2633,
    'JAIL_DOOR': 2631,
    'DEEP_GATE': 2623,
    'CABINET_SHUT': 2635,
    'CABINET_OPEN': 2636,
})
HERO_TILE = Record({
    'ACHIETTIES': Tile(2903, 3511, 0),
    'GRUBOR_DOOR': Tile(2810, 3170, 0),
    'GRUBOR_DOOR_INNER': Tile(2811, 3170, 0),
    'TROBERT': Tile(2806, 3175, 0),
    'ALFONSE': Tile(2793, 3189, 0),
    'KITCHEN_DOOR': Tile(2788, 3189, 0),
    'KITCHEN_DOOR_INNER': Tile(2788, 3190, 0),
    'CHARLIE': Tile(2789, 3191, 0),
    'KITCHEN_PANEL': Tile(2787, 3190, 0),
    'KITCHEN_PANEL_INNER': Tile(2786, 3190, 0),
    'GARDEN': Tile(2784, 3194, 0),
    'YARD': Tile(2781, 3196, 0),
    'SIDE_ROOM': Tile(2781, 3197, 0),
    'ARROW_SLIT': Tile(2780, 3198, 0),
    'GRIP_LURE': Tile(2777, 3198, 0),
    'GARV_DOOR': Tile(2774, 3187, 0),
    'GARV_DOOR_INNER': Tile(2774, 3188, 0),
    'GRIP': Tile(2774, 3191, 0),
    'CABINET_STAND': Tile(2775, 3197, 0),
    'WEST_WING': Tile(2765, 3194, 0),
    'TREASURE_DOOR': Tile(2763, 3197, 0),
    'TREASURE_DOOR_INNER': Tile(2764, 3197, 0),
    'CHEST_STAND': Tile(2766, 3198, 0),
    'RENDEZVOUS': Tile(2793, 3180, 0),
    'GERRANT': Tile(3013, 3226, 0),
    'JATIX': Tile(2899, 3428, 0),
    'LOWE': Tile(3232, 3424, 0),
    'LOUIE': Tile(3316, 3176, 0),
    'HORVIK': Tile(3229, 3439, 0),
    'VALAINE': Tile(3193, 3362, 1),
    'SCAVVO': Tile(3191, 3352, 1),
    'CHAMPIONS_STAIRS': Tile(3188, 3358, 0),
    'CHAMPIONS_STAIRS_TOP': Tile(3188, 3354, 1),
    'TAVERLEY_LADDER': Tile(2884, 3398, 0),
    'TAVERLEY_DUNGEON': Tile(2884, 9798, 0),
    'CHAOS_DRUIDS': Tile(2932, 9849, 0),
    'JAILER': Tile(2932, 9693, 0),
    'JAIL_DOOR': Tile(2931, 9690, 0),
    'JAIL_DOOR_INNER': Tile(2931, 9689, 0),
    'VELRAK': Tile(2931, 9686, 0),
    'DEEP_GATE': Tile(2924, 9803, 0),
    'DEEP_GATE_INNER': Tile(2923, 9803, 0),
    'LAVA_FISH': Tile(2892, 9767, 0),
    'CATHERBY_RANGE': Tile(2817, 3443, 0),
    'WWM_LADDER': Tile(2845, 3526, 0),
    'WWM_DUNGEON': Tile(2845, 9926, 0),
    'ICE_QUEEN': Tile(2866, 9955, 0),
    'PORT_SARIM_MONK': Tile(3048, 3236, 0),
    'ENTRANA_DOCK': Tile(2834, 3335, 0),
    'FIREBIRD': Tile(2847, 3387, 0),
    'VARROCK_BANK': Tile(3185, 3436, 0),
    'DRAYNOR_BANK': Tile(3092, 3245, 0),
})
# Why: `pickPreferred` matches a lower-cased substring and the content mixes straight and curly quotes, so every fragment here is apostrophe-free; one wrong glyph picks no option at all.
ACHIETTIES = NpcStop('Achietties', HERO_TILE.ACHIETTIES, 8, ['may I apply to join', 'start looking for all those things'])
KATRINE_TASK = NpcStop('Katrine', Tile(3186, 3385, 0), 6, ['rank of master thief'])
KATRINE_ARMBAND = NpcStop('Katrine', Tile(3186, 3385, 0), 6, ['have a candlestick now'])
STRAVEN_TASK = NpcStop('Straven', Tile(3246, 9780, 0), 6, [])
STRAVEN_ARMBAND = NpcStop('Straven', Tile(3246, 9780, 0), 6, [])
TROBERT = NpcStop('Trobert', HERO_TILE.TROBERT, 6, ['help me get scarface pete', 'volunteer to undertake'])
ALFONSE = NpcStop('Alfonse the waiter', HERO_TILE.ALFONSE, 8, ['do you sell gherkins'])
CHARLIE = NpcStop('Charlie the cook', HERO_TILE.CHARLIE, 6, ['looking for a gherkin', 'want to steal scarface pete'])
VELRAK = NpcStop('Velrak the explorer', HERO_TILE.VELRAK, 4, ['know anywhere good to explore', 'yes please'])
GERRANT = NpcStop('Gerrant', HERO_TILE.GERRANT, 8, ['how to catch a lava eel'])
HERO_SAY = Record({
    'BLACK_ARM_PASSWORD': 'four leaved clover',
    'GRIP_DUTIES': 'what do my duties involve',
    'GRIP_TASK': 'anything i can do now',
    'GRIP_LEAVE': 'better sort my new room out',
    'CABINET_PEEK': 'notice me having a quick look',
})
GRIP = NpcStop('Grip', HERO_TILE.GRIP, 6, [HERO_SAY.GRIP_DUTIES, HERO_SAY.GRIP_TASK, HERO_SAY.GRIP_LEAVE])
HERO_SHOP = Record({
    'LOWE': Record({'npc': 'Lowe', 'anchor': HERO_TILE.LOWE}),
    'HORVIK': Record({'npc': 'Horvik', 'anchor': HERO_TILE.HORVIK}),
    'VALAINE': Record({'npc': 'Valaine', 'anchor': HERO_TILE.VALAINE}),
    'SCAVVO': Record({'npc': 'Scavvo', 'anchor': HERO_TILE.SCAVVO}),
    'AEMAD': Record({'npc': 'Aemad', 'anchor': Tile(2613, 3294, 0)}),
    'LOUIE': Record({'npc': 'Louie legs', 'anchor': HERO_TILE.LOUIE}),
    'GERRANT': Record({'npc': 'Gerrant', 'anchor': HERO_TILE.GERRANT}),
    'JATIX': Record({'npc': 'Jatix', 'anchor': HERO_TILE.JATIX}),
})
TAVERLEY_HOP_DOWN = LadderHop(HERO_TILE.TAVERLEY_LADDER, 'Ladder', 'Climb-down', HERO_TILE.TAVERLEY_DUNGEON)
TAVERLEY_HOP_UP = LadderHop(HERO_TILE.TAVERLEY_DUNGEON, 'Ladder', 'Climb-up', HERO_TILE.TAVERLEY_LADDER)
WWM_HOP_DOWN = LadderHop(HERO_TILE.WWM_LADDER, 'Ladder', 'Climb-down', HERO_TILE.WWM_DUNGEON)
WWM_HOP_UP = LadderHop(HERO_TILE.WWM_DUNGEON, 'Ladder', 'Climb-up', HERO_TILE.WWM_LADDER)
HERO_HOPS = [TAVERLEY_HOP_DOWN, TAVERLEY_HOP_UP, WWM_HOP_DOWN, WWM_HOP_UP]


def within(t, x0, x1, z0, z1, level):
    return not not t and t.level == level and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


# Why: every box below is a flood of the collision pack. The mansion is 6 sealed pockets and a distance test calls 2 tiles either side of one wall the same place.
def in_kitchen(t):
    """The Shrimp and Parrot's kitchen, which only `herokitchendoor` opens."""
    return within(t, 2787, 2799, 3190, 3192, 0)


def in_garden(t):
    """Mr Olbors' garden, reached only by pushing the kitchen wall panel."""
    return within(t, 2783, 2788, 3188, 3199, 0) and not in_kitchen(t)


def in_yard(t):
    """The 9-tile yard between the garden door and the side door."""
    return within(t, 2780, 2782, 3193, 3196, 0)


def in_side_room(t):
    """The 5-tile side room, sealed from the mansion by the snipable wall."""
    return within(t, 2780, 2782, 3197, 3198, 0)


def in_treasure_room(t):
    """Past `pete_treasuredoor`, where the candlestick chest is. 17 tiles."""
    return within(t, 2764, 2769, 3196, 3199, 0)


def in_store_corridor(t):
    """The 8-tile store the treasure room's ordinary door opens onto; nothing in the quest needs it."""
    return within(t, 2770, 2772, 3196, 3198, 0)


def in_west_wing(t):
    """The mansion's west wing, past the ordinary door at (2767,3194) and outside `pete_treasuredoor`."""
    return within(t, 2759, 2766, 3188, 3199, 0) and not in_treasure_room(t)


def in_mansion(t):
    """Everything `garvdoor` seals: the hall Grip patrols and the west wing behind it."""
    if in_treasure_room(t) or in_store_corridor(t):
        return False
    return within(t, 2767, 2779, 3188, 3199, 0) or in_west_wing(t)


# Why: Hideout and alley bounds overlap, so use separate narrow regions around their interleaved tiles.
def in_brimhaven_hq(t):
    """The Brimhaven Black Arm hideout, past Grubor's door. 69 tiles."""
    return within(t, 2811, 2815, 3167, 3178, 0) or within(t, 2805, 2810, 3171, 3178, 0)


def in_taverley_dungeon(t):
    return within(t, 2820, 2950, 9600, 9900, 0)


def in_velrak_cell(t):
    """Velrak's cell, past `dungeonjail`. 33 tiles."""
    return within(t, 2928, 2934, 9683, 9689, 0)


# Why: the deep dungeon and the rest of Taverley's interleave across x 2881-2923, so these 4 boxes cover the flood: all 2473 pocket tiles inside one, no tile of the main component.
def in_deep_dungeon(t):
    """Past the dusty-key gate, where the lava eels are fished."""
    return within(t, 2817, 2880, 9761, 9854, 0) or within(t, 2817, 2914, 9761, 9793, 0) or within(t, 2888, 2923, 9769, 9816, 0) or within(t, 2881, 2882, 9802, 9808, 0)


def in_wwm_dungeon(t):
    return within(t, 2810, 2890, 9900, 9990, 0)


def on_entrana(t):
    return within(t, 2800, 2870, 3330, 3400, 0)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['DIG_NAME', 'DIG_ID', 'DIG_ITEM', 'DIG_NPC', 'DIG_LOC', 'DIG_SOIL_IDS', 'DIG_ZONE', 'DIG_TILE', 'EXAMINER', 'EXPERT', 'CURATOR', 'PANNING_GUIDE', 'in_shaft_east', 'in_shaft_west', 'in_altar_cave', 'in_dig_cave']

DIG_NAME = 'Digsite Quest'
# Why: Student, Digsite workman, Panning tray, Mixed chemicals and Rock sample each name more than one thing, so this module never matches by display name alone.
DIG_ID = Record({
    'COINS': 995,
    'SPECIMEN_JAR': 669,
    'SPECIMEN_BRUSH': 670,
    'ROCK_SAMPLE_GREEN': 671,
    'ROCK_SAMPLE_ORANGE': 672,
    'ROCK_SAMPLE_PURPLE': 673,
    'CRACKED_SAMPLE': 674,
    'ROCK_PICK': 675,
    'TROWEL': 676,
    'TRAY_EMPTY': 677,
    'TRAY_MUD': 679,
    'NUGGETS': 680,
    'TALISMAN': 681,
    'PLAIN_LETTER': 682,
    'STAMPED_LETTER': 683,
    'CERT_1': 691,
    'CERT_2': 692,
    'CERT_3': 693,
    'EXPERT_SCROLL': 696,
    'STONE_TABLET': 699,
    'POWDER': 700,
    'AMMONIUM_NITRATE': 701,
    'LIQUID': 702,
    'NITROGLYCERIN': 703,
    'GROUND_CHARCOAL': 704,
    'PRE_CHARCOAL': 705,
    'POST_CHARCOAL': 706,
    'COMPOUND': 707,
    'ARCENIA_ROOT': 708,
    'CHEST_KEY': 709,
    'VIAL': 229,
    'PESTLE': 233,
    'TINDERBOX': 590,
    'CHARCOAL': 973,
    'ROPE': 954,
    'CHISEL': 1755,
    'OPAL': 1609,
    'UNCUT_OPAL': 1625,
    'CUP_OF_TEA': 1978,
})
DIG_ITEM = Record({
    'COINS': 'Coins',
    'TROWEL': 'Trowel',
    'SPECIMEN_JAR': 'Specimen jar',
    'SPECIMEN_BRUSH': 'Specimen brush',
    'TRAY': 'Panning tray',
    'ROPE': 'Rope',
    'VIAL': 'Vial',
    'PESTLE': 'Pestle and mortar',
    'TINDERBOX': 'Tinderbox',
    'CHISEL': 'Chisel',
    'CHARCOAL': 'Charcoal',
    'CUP_OF_TEA': 'Cup of tea',
    'OPAL': 'Opal',
    'UNCUT_OPAL': 'Uncut opal',
    'ARCENIA_ROOT': 'Arcenia root',
    'STONE_TABLET': 'Stone tablet',
    'TALISMAN': 'Talisman of zaros',
    'EXPERT_SCROLL': 'Invitation letter',
    'CHEST_KEY': 'Chest key',
    'PLAIN_LETTER': 'Unstamped letter',
    'STAMPED_LETTER': 'Stamped letter',
})
DIG_NPC = Record({
    'WORKMAN': 613,
    'CAVE_WORKMAN': 614,
    'STUDENT_GREEN': 615,
    'STUDENT_ORANGE': 616,
    'STUDENT_PURPLE': 617,
    'EXAMINER': 618,
    'EXPERT': 619,
    'PANNING_GUIDE': 620,
    'CURATOR': 646,
})
DIG_LOC = Record({
    'WINCH_MAIN': 2350,
    'WINCH_PRIVATE': 2351,
    'LADDER_WEST': 2352,
    'LADDER_EAST': 2353,
    'SAMPLE_SACKS': 2356,
    'BUSH_SAMPLE': 2358,
    'BARREL': 2359,
    'CHEST_OPEN': 2360,
    'CHEST_SHUT': 2361,
    'BRICK': 2362,
    'PANNING_POINT': 2363,
})
DIG_SOIL_IDS = [2376, 2377, 2378]
# Why: `area_digsite.rs2` picks the exam level from `inzone(...)` on the soil's own coordinate, so these boxes are copied from it.
DIG_ZONE = Record({
    'LEVEL3': Record({'stand': Tile(3353, 3408, 0), 'min_x': 3350, 'max_x': 3357, 'min_z': 3404, 'max_z': 3412}),
    'TRAINING': Record({'stand': Tile(3354, 3397, 0), 'min_x': 3352, 'max_x': 3357, 'min_z': 3396, 'max_z': 3400}),
})
DIG_TILE = Record({
    'VARROCK_BANK': Tile(3253, 3420, 0),
    'CURATOR': Tile(3255, 3446, 0),
    'TEA_SELLER': Tile(3271, 3412, 0),
    'GENERAL_STORE': Tile(3218, 3414, 0),
    'JATIX': Tile(2899, 3427, 0),
    'EXAMINER': Tile(3360, 3343, 0),
    'EXPERT': Tile(3355, 3334, 0),
    'PANNING_GUIDE': Tile(3376, 3378, 0),
    'PANNING_STAND': Tile(3379, 3378, 0),
    'TRAY_SPAWN_STAND': Tile(3370, 3378, 0),
    'TRAY_SPAWN': Tile(3369, 3378, 0),
    'BUSH_STAND': Tile(3358, 3372, 0),
    'BARREL_STAND': Tile(3364, 3377, 0),
    'CHEST_STAND': Tile(3373, 3378, 0),
    'SACKS_STAND': Tile(3359, 3399, 0),
    'STUDENTS': Tile(3358, 3410, 0),
    'WORKMEN': Tile(3357, 3407, 0),
    'WINCH_MAIN_STAND': Tile(3352, 3418, 0),
    'WINCH_PRIVATE_STAND': Tile(3370, 3427, 0),
    'SHAFT_EAST_LANDING': Tile(3370, 9828, 0),
    'SHAFT_WEST_LANDING': Tile(3353, 9818, 0),
    'CAVE_WORKMAN': Tile(3352, 9822, 0),
    'ARCENIA_WEST': Tile(3351, 9824, 0),
    'ARCENIA_WEST_ALT': Tile(3348, 9819, 0),
    'BRICK_STAND': Tile(3379, 9826, 0),
    'ALTAR_LANDING': Tile(3368, 9767, 0),
    'TABLET': Tile(3374, 9747, 0),
    'ALTAR_LADDER': Tile(3370, 9764, 0),
})
EXAMINER = NpcStop('Examiner', DIG_TILE.EXAMINER, 8, [])
EXPERT = NpcStop('Archaeological expert', DIG_TILE.EXPERT, 6, [])
CURATOR = NpcStop('Curator', DIG_TILE.CURATOR, 6, [])
PANNING_GUIDE = NpcStop('Panning guide', DIG_TILE.PANNING_GUIDE, 6, [])


def within(t, x0, x1, z0, z1):
    return not not t and t.level == 0 and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


# Why: a flood over the collision pack puts the 4 shaft pockets at 189, 52, 426 and 52 tiles with nothing walking between them, so these boxes are tight.
def in_shaft_east(t):
    """The eastern shaft before the blast: only the blast bricks are here."""
    return within(t, 3360, 3392, 9820, 9856)


def in_shaft_west(t):
    """The western shaft: the cave workman with the chest key, and 2 arcenia roots."""
    return within(t, 3344, 3360, 9810, 9828)


def in_altar_cave(t):
    """The eastern shaft after the blast, which is a different mapsquare and holds the altar."""
    return within(t, 3360, 3392, 9736, 9792)


def in_dig_cave(t):
    """Any of the dig shafts, above or below the blast."""
    return within(t, 3344, 3392, 9736, 9856)

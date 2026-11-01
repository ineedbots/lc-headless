"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['FT_NAME', 'FT_ID', 'FT_LOC', 'FT_TILE', 'MAZE_ROUTE', 'BRUNDT', 'MANNI', 'THORA', 'OLAF', 'PEER', 'SIGLI', 'SIGMUND', 'SWENSEN', 'THORVALD', 'YRSA', 'SKULGRIMEN', 'FISHERMAN', 'SAILOR', 'ASKELADDEN', 'LALLI', 'COUNCIL_WORKMAN', 'POISON_SALESMAN', 'MERCHANT_FIRST', 'in_maze', 'in_battleground', 'in_puzzle_room', 'in_seer_west', 'in_seer_east', 'in_longhall', 'on_stage', 'past_backstage']

FT_NAME = 'The Fremennik Trials'
FT_ID = Record({
    'UNSTRUNG_LYRE': 3688,
    'LYRE': 3689,
    'ENCHANTED_LYRE': 3690,
    'BRANCH': 3692,
    'GOLDEN_FLEECE': 3693,
    'GOLDEN_WOOL': 3694,
    'PET_ROCK': 3695,
    'TALISMAN_CHARGED': 3696,
    'TALISMAN': 3697,
    'FLOWER': 3698,
    'BALLAD': 3699,
    'STURDY_BOOTS': 3700,
    'HUNTERS_MAP': 3701,
    'BOWSTRING': 3702,
    'UNUSUAL_FISH': 3703,
    'SEA_MAP': 3704,
    'FORECAST': 3705,
    'CHAMPIONS_TOKEN': 3706,
    'COCKTAIL': 3707,
    'FISCAL_STATEMENT': 3708,
    'PROMISSORY_NOTE': 3709,
    'WARRIORS_CONTRACT': 3710,
    'BEER_KEG': 3711,
    'LOW_ALCOHOL_KEG': 3712,
    'FIRECRACKER': 3713,
    'FIRECRACKER_LIT': 3714,
    'BUCKET_5': 3722,
    'BUCKET_4': 3723,
    'BUCKET_3': 3724,
    'BUCKET_2': 3725,
    'BUCKET_1': 3726,
    'BUCKET_EMPTY': 3727,
    'JUG_3': 3729,
    'JUG_2': 3730,
    'JUG_1': 3731,
    'JUG_EMPTY': 3732,
    'VASE': 3734,
    'VASE_WATER': 3735,
    'VASE_LID': 3737,
    'SEALED_VASE_WATER': 3740,
    'FROZEN_KEY': 3741,
    'RED_HERRING': 3742,
    'RED_DISK': 3743,
    'WOODEN_DISK': 3744,
    'SEERS_KEY': 3745,
    'RED_GOOP': 3746,
    'RAW_SHARK': 383,
    'KNIFE': 946,
    'COINS': 995,
    'POTATO': 1942,
    'ONION': 1957,
    'CABBAGE': 1965,
})
FT_LOC = Record({
    'LAKE_ALTAR': 4141,
    'MUSICAL_TREE': 4142,
    'TROLL_CAULDRON': 4149,
    'MAZE_PORTAL_1': 4150,
    'MAZE_PORTAL_2': 4151,
    'MAZE_PORTAL_3': 4152,
    'MAZE_PORTAL_4': 4153,
    'MAZE_PORTAL_5': 4154,
    'MAZE_PORTAL_6': 4155,
    'MAZE_PORTAL_7': 4156,
    'MAZE_LADDER_TOP': 4158,
    'MAZE_EXIT': 4160,
    'BACKSTAGE_DOOR': 4148,
    'PIPE': 4162,
    'SEER_UP_LADDER': 4163,
    'SEER_DOWN_LADDER': 4164,
    'SEER_DOOR1': 4165,
    'SEER_DOOR2': 4166,
    'SEER_CHEST_SHUT': 4167,
    'SEER_CHEST_OPEN': 4168,
    'FROZEN_TABLE': 4169,
    'SCALES_CHEST': 4170,
    'BOOKCASE': 4171,
    'RANGE': 4172,
    'TRAPDOOR_OPEN': 4173,
    'TRAPDOOR_SHUT': 4174,
    'DRAIN': 4175,
    'TAP': 4176,
    'CUPBOARD_SHUT': 4177,
    'CUPBOARD_OPEN': 4178,
    'MURAL': 4179,
    'UNICORN_HEAD': 4181,
    'BULL_HEAD': 4182,
    'WARRIOR_LADDER': 4187,
    'WARRIOR_LADDER_DOWN': 4189,
})
FT_TILE = Record({
    'SEERS_BANK': Tile(2725, 3491, 0),
    'LONGHALL': Tile(2660, 3676, 0),
    'KEG_TABLE': Tile(2660, 3676, 0),
    'PIPE_STAND': Tile(2664, 3674, 0),
    'STAGE': Tile(2658, 3683, 0),
    'BACKSTAGE_DOOR': Tile(2667, 3683, 0),
    'BACKSTAGE_INNER': Tile(2666, 3683, 0),
    'ONION_PATCH': Tile(2677, 3656, 0),
    'POTATO_PATCH': Tile(2677, 3654, 0),
    'CABBAGE_PATCH': Tile(2677, 3652, 0),
    'KNIFE_SPAWN': Tile(2681, 3717, 0),
    'AXE_SPAWN': Tile(2678, 3731, 0),
    'MUSICAL_TREE': Tile(2739, 3638, 0),
    'TROLL_CAULDRON': Tile(2772, 3624, 0),
    'LAKE_ALTAR': Tile(2626, 3599, 0),
    'SPINNING_WHEEL': Tile(2712, 3471, 1),
    'COUNCIL_WORKMAN': Tile(2655, 3593, 0),
    'FORESTERS_ARMS': Tile(2690, 3494, 0),
    'POISON_SALESMAN': Tile(2695, 3495, 0),
    'ARHEIN': Tile(2803, 3431, 0),
    'RUFUS': Tile(3507, 3497, 0),
    'MAZE_LADDER': Tile(2644, 3658, 0),
    'MAZE_ENTRY': Tile(2631, 10004, 0),
    'MAZE_EXIT_STAND': Tile(2665, 10038, 0),
    'SEER_DOOR1': Tile(2631, 3667, 0),
    'SEER_DOOR1_INNER': Tile(2631, 3666, 0),
    'SEER_UP_LADDER': Tile(2631, 3664, 0),
    'SEER_DOWN_LADDER': Tile(2635, 3663, 0),
    'SEER_DOOR2_INNER': Tile(2636, 3666, 0),
    'MURAL_STAND': Tile(2635, 3663, 0),
    'PUZZLE_WEST_TRAPDOOR': Tile(2631, 3664, 2),
    'PUZZLE_EAST_TRAPDOOR': Tile(2636, 3664, 2),
    'PUZZLE_TAP': Tile(2630, 3661, 2),
    'PUZZLE_DRAIN': Tile(2630, 3662, 2),
    'PUZZLE_RANGE': Tile(2630, 3663, 2),
    'PUZZLE_CUPBOARD': Tile(2629, 3661, 2),
    'PUZZLE_UNICORN': Tile(2632, 3661, 2),
    'PUZZLE_BULL': Tile(2634, 3661, 2),
    'PUZZLE_CHEST': Tile(2635, 3661, 2),
    'PUZZLE_SCALES': Tile(2632, 3664, 2),
    'PUZZLE_BOOKCASE': Tile(2634, 3664, 2),
    'PUZZLE_FROZEN_TABLE': Tile(2638, 3664, 2),
    'WARRIOR_LADDER': Tile(2666, 3694, 0),
    'WARRIOR_LOFT': Tile(2667, 3692, 1),
    'WARRIOR_LOFT_LADDER': Tile(2666, 3694, 1),
})
MAZE_ROUTE = [
    Record({'id': FT_LOC.MAZE_PORTAL_1, 'stand': Tile(2631, 10003, 0), 'land': Tile(2642, 10017, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_2, 'stand': Tile(2640, 10015, 0), 'land': Tile(2651, 10004, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_3, 'stand': Tile(2655, 10004, 0), 'land': Tile(2667, 10015, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_4, 'stand': Tile(2665, 10017, 0), 'land': Tile(2630, 10028, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_5, 'stand': Tile(2630, 10024, 0), 'land': Tile(2653, 10035, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_6, 'stand': Tile(2656, 10036, 0), 'land': Tile(2668, 10026, 0)}),
    Record({'id': FT_LOC.MAZE_PORTAL_7, 'stand': Tile(2666, 10028, 0), 'land': Tile(2665, 10038, 0)}),
]


def stop(npc, x, z, prefer=None, leash=8):
    if prefer is None:
        prefer = []
    return NpcStop(npc, Tile(x, z, 0), leash, prefer)


def BRUNDT(prefer):
    return stop('Brundt the Chieftain', 2659, 3669, prefer, 10)


def MANNI(prefer):
    return stop('Manni the Reveller', 2660, 3673, prefer)


def THORA(prefer):
    return stop('Thora the Barkeep', 2662, 3673, prefer)


def OLAF(prefer):
    return stop('Olaf the Bard', 2673, 3683, prefer)


def PEER(prefer):
    return stop('Peer the Seer', 2634, 3668, prefer)


def SIGLI(prefer):
    return stop('Sigli the Huntsman', 2660, 3653, prefer)


def SIGMUND(prefer):
    return stop('Sigmund The Merchant', 2641, 3680, prefer)


def SWENSEN(prefer):
    return stop('Swensen the Navigator', 2646, 3660, prefer)


def THORVALD(prefer):
    return stop('Thorvald the Warrior', 2666, 3693, prefer)


def YRSA(prefer):
    return stop('Yrsa', 2625, 3675, prefer)


def SKULGRIMEN(prefer):
    return stop('Skulgrimen', 2663, 3694, prefer)


def FISHERMAN(prefer):
    return stop('Fisherman', 2641, 3699, prefer)


def SAILOR(prefer):
    return stop('Sailor', 2629, 3693, prefer)


def ASKELADDEN(prefer):
    return stop('Askeladden', 2658, 3660, prefer)


def LALLI(prefer):
    return stop('Lalli', 2770, 3623, prefer)


def COUNCIL_WORKMAN(prefer):
    return stop('Council workman', 2655, 3593, prefer)


def POISON_SALESMAN(prefer):
    return stop('Poison salesman', 2695, 3495, prefer)


MERCHANT_FIRST = ["Ask about the Merchant's trial"]


def within(t, x0, x1, z0, z1, level):
    return not not t and t.level == level and t.x >= x0 and t.x <= x1 and t.z >= z0 and t.z <= z1


def in_maze(t):
    return within(t, 2624, 2687, 9984, 10047, 0)


def in_battleground(t):
    return within(t, 2624, 2687, 10048, 10111, 2)


def in_puzzle_room(t):
    """The level-2 puzzle rooms, which only the 2 ladders reach."""
    return within(t, 2628, 2639, 3659, 3666, 2)


# Why: both halves are sealed pockets in the collision pack, split by the wall at x 2634 the mural hangs on; these boxes were measured by a flood from each door.
def in_seer_west(t):
    """The half of the puzzle house behind door 1: the way in and the way to fail out."""
    return within(t, 2629, 2633, 3659, 3666, 0)


def in_seer_east(t):
    """The half behind door 2, holding the mural and the locked exit."""
    return within(t, 2634, 2638, 3659, 3666, 0)


def in_longhall(t):
    return within(t, 2655, 2662, 3665, 3681, 0)


def on_stage(t):
    return within(t, 2655, 2662, 3682, 3685, 0)


def past_backstage(t):
    """The doorway and the corridor behind it, where the crossing is already spent."""
    return within(t, 2663, 2667, 3682, 3685, 0)

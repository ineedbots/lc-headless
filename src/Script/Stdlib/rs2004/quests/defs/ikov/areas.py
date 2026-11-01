"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ikov/areas.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from rs2004.quests.exec.primitives import NpcStop

__all__ = ['IKOV_QUEST', 'IKOV_OBJ', 'IKOV_LOC', 'LAVA_BRIDGE_ZONE', 'IKOV_NPC', 'IKOV_NAME', 'IKOV_FOODS', 'ROOTS_WANTED', 'ARROWS_WANTED', 'IKOV_TILE', 'ICE_CHESTS', 'LUCIEN_START', 'WINELDA_STOP', 'GUARDIAN_STOP', 'in_dark_room', 'in_chamber_of_fear', 'west_of_bridge', 'in_ice_cavern', 'past_south_gate', 'in_trap_pit', 'on_winelda_ledge', 'in_guardian_temple', 'in_temple']

IKOV_QUEST = 'Temple of Ikov'
IKOV_OBJ = Record({
    'LIT_CANDLE': 33,
    'UNLIT_CANDLE': 36,
    'UNSTRUNG_YEW_SHORTBOW': 68,
    'ICE_ARROW': 78,
    'LEVER': 83,
    'STAFF': 84,
    'SHINY_KEY': 85,
    'PENDANT_LUCIEN': 86,
    'PENDANT_ARMADYL': 87,
    'BOOTS': 88,
    'BOOTS_WORN': 89,
    'LIMPWURT_ROOT': 225,
    'TINDERBOX': 590,
    'YEW_SHORTBOW': 857,
    'KNIFE': 946,
    'IRON_AXE': 1349,
    'YEW_LOGS': 1515,
    'BOW_STRING': 1777,
    'FLAX': 1779,
})
IKOV_LOC = Record({
    'LEVER_BRACKET': 86,
    'MENDED_LEVER': 87,
    'LEVER_DOWN': 88,
    'SOUTH_GATE_LEFT': 89,
    'SOUTH_GATE_RIGHT': 90,
    'TRAP_LEVER': 91,
    'FEAR_GATE_LEFT': 94,
    'FEAR_GATE_RIGHT': 95,
    'TRAPLEVER_DOOR': 92,
    'FIREWARRIOR_DOOR': 93,
    'DARK_STAIRS_UP': 96,
    'DARK_STAIRS_DOWN': 98,
    'TRAP_LADDER': 101,
    'CHEST_SHUT': 103,
    'CHEST_OPEN': 104,
    'YEW_TREE': 1309,
    'SECRET_WALL': 1586,
    'SECRET_WALL_OPEN': 1587,
    'SPINNING_WHEEL': 2644,
    'FLAX': 2646,
    'WEB': 733,
    'WEB_SLASHED': 734,
})
LAVA_BRIDGE_ZONE = {'min_x': 2648, 'max_x': 2650, 'min_z': 9828, 'max_z': 9829, 'level': 0}
IKOV_NPC = Record({
    'HOBGOBLIN_UNARMED': 122,
    'HOBGOBLIN_ARMED': 123,
    'LUCIEN_HOSTILE': 272,
    'LUCIEN_QUESTGIVER': 273,
    'GUARDIAN_MALE': 274,
    'GUARDIAN_FEMALE': 275,
    'WINELDA': 276,
    'FIRE_WARRIOR': 277,
})
IKOV_NAME = Record({
    'LIT_CANDLE': 'Lit candle',
    'CANDLE': 'Candle',
    'TINDERBOX': 'Tinderbox',
    'KNIFE': 'Knife',
    'IRON_AXE': 'Iron axe',
    'YEW_LOGS': 'Yew logs',
    'FLAX': 'Flax',
    'BOW_STRING': 'Bow string',
    'YEW_SHORTBOW': 'Yew shortbow',
    'UNSTRUNG_YEW_SHORTBOW': 'Yew shortbow',
    'ICE_ARROWS': 'Ice arrows',
    'BOOTS': 'Boots of lightness',
    'PENDANT_LUCIEN': 'Pendant of lucien',
    'PENDANT_ARMADYL': 'Armadyl pendant',
    'SHINY_KEY': 'Shiny key',
    'LEVER': 'Lever',
    'LIMPWURT_ROOT': 'Limpwurt root',
    'LOBSTER': 'Lobster',
})
IKOV_FOODS = ['lobster', 'swordfish', 'tuna']
ROOTS_WANTED = 20
# Why: he has 59 hp, 4 shots in 5 land recoverable and the leg sweeps them mid-fight, so this is a floor one chest circuit clears.
ARROWS_WANTED = 20
IKOV_TILE = Record({
    'LUCIEN_INN': Tile(2573, 3321, 0),
    'LUCIEN_HUT': Tile(3176, 3476, 0),
    'ARDOUGNE_BANK': Tile(2616, 3332, 0),
    'SEERS_BANK': Tile(2725, 3491, 0),
    'CATHERBY_BANK': Tile(2809, 3441, 0),
    'AEMAD': Tile(2613, 3294, 0),
    'CANDLE_MAKER': Tile(2800, 3439, 0),
    'ARHEIN': Tile(2803, 3430, 0),
    'KNIFE_SPAWN': Tile(2704, 3475, 0),
    'YEW_TREES': Tile(2759, 3431, 0),
    'FLAX_FIELD': Tile(2740, 3444, 0),
    'SPINNING_WHEEL': Tile(2712, 3471, 1),
    'SPINNING_WHEEL_STAIRS': Tile(2714, 3472, 0),
    'HOBGOBLINS': Tile(2911, 3284, 0),
    'HOBGOBLIN_RETREAT': Tile(2933, 3323, 0),
    'TEMPLE_LADDER': Tile(2677, 3406, 0),
    'ENTRANCE': Tile(2677, 9806, 0),
    'FEAR_GATE_SOUTH': Tile(2661, 9814, 0),
    'FEAR_GATE_NORTH': Tile(2661, 9815, 0),
    'SOUTH_GATE_NORTH': Tile(2661, 9803, 0),
    'SOUTH_GATE_SOUTH': Tile(2661, 9802, 0),
    'LEVER_BRACKET': Tile(2672, 9804, 0),
    'DARK_STAIRS_DOWN': Tile(2654, 9808, 0),
    'DARK_LANDING': Tile(2641, 9764, 0),
    'BOOTS_WEB': Tile(2654, 9765, 0),
    'BOOTS_SPAWN': Tile(2654, 9767, 0),
    'DARK_STAIRS_UP': Tile(2641, 9763, 0),
    'DARK_STAIRS_ARRIVE': Tile(2654, 9809, 0),
    'BRIDGE_EAST': Tile(2651, 9828, 0),
    'BRIDGE_ZONE_EAST': Tile(2650, 9828, 0),
    'BRIDGE_ZONE_WEST': Tile(2648, 9828, 0),
    'BRIDGE_WEST': Tile(2647, 9828, 0),
    'IKOV_LEVER_SPAWN': Tile(2637, 9819, 0),
    'TRAP_LEVER': Tile(2665, 9854, 0),
    'TRAP_PIT_LADDER': Tile(2682, 9850, 0),
    'TRAPLEVER_DOOR_SOUTH': Tile(2648, 9856, 0),
    'FIRE_DOOR_SOUTH': Tile(2646, 9869, 0),
    'FIRE_WARRIOR_SPAWN': Tile(2646, 9866, 0),
    'WINELDA': Tile(2656, 9875, 0),
    'WINELDA_LANDING': Tile(2664, 9876, 0),
    'SHINY_KEY_SPAWN': Tile(2628, 9859, 0),
    'SECRET_WALL': Tile(2643, 9892, 0),
    'SECRET_WALL_INSIDE': Tile(2643, 9893, 0),
    'GUARDIANS': Tile(2643, 9897, 0),
    'MCGRUBOR_LADDER': Tile(2659, 9893, 0),
    'MCGRUBOR_SURFACE': Tile(2659, 3493, 0),
})
# Why: `ikov_chestclosed` is `forceapproach=north`, rotated by each placement, so the stand is the only side an Open lands from.
ICE_CHESTS = [
    Record({'loc': Tile(2710, 9850, 0), 'stand': Tile(2710, 9849, 0)}),
    Record({'loc': Tile(2719, 9838, 0), 'stand': Tile(2719, 9839, 0)}),
    Record({'loc': Tile(2729, 9850, 0), 'stand': Tile(2729, 9849, 0)}),
    Record({'loc': Tile(2738, 9835, 0), 'stand': Tile(2739, 9835, 0)}),
    Record({'loc': Tile(2745, 9821, 0), 'stand': Tile(2745, 9822, 0)}),
    Record({'loc': Tile(2747, 9848, 0), 'stand': Tile(2746, 9848, 0)}),
]
# Why: the first two options start the quest; "That sounds like a laugh!" is the only branch that hands the pendant over.
LUCIEN_START = NpcStop('Lucien', IKOV_TILE.LUCIEN_INN, 8, ["I'm a mighty hero!", 'That sounds like a laugh!', "Why can't you get it yourself?", "What's the reward?"])
WINELDA_STOP = NpcStop('Winelda', IKOV_TILE.WINELDA, 8, ['Yes I do!', 'Yes we do!'])
# Why: the "yearly bath" branch is the only one that ends in the Armadyl pendant; every other answer sets the guardian on you.
GUARDIAN_STOP = NpcStop('Guardian of Armadyl', IKOV_TILE.GUARDIANS, 12, [
    'I seek the Staff of Armadyl.',
    'Lucien will give me a grand reward for it!',
    "You're right, it's time for my yearly bath.",
    "Ok! I'll help!",
])


def in_dark_room(t):
    return t.x >= 2639 and t.x <= 2655 and t.z >= 9759 and t.z <= 9768


def in_chamber_of_fear(t):
    return t.x >= 2646 and t.x <= 2686 and t.z >= 9815 and t.z <= 9855


def west_of_bridge(t):
    """West of the lava bridge, where the Lever lies; the bridge is the only way in or out."""
    return t.x >= 2630 and t.x <= 2647 and t.z >= 9815 and t.z <= 9835


def in_ice_cavern(t):
    """South of the mended-lever gate: the cavern that loops east to the six ice-arrow chests."""
    return t.z <= 9802 or t.x >= 2688


# Why: `inIceCavern` is a half-plane and the boots room sits inside it, so only this may stand in for "through the south gate".
def past_south_gate(t):
    """Through the south gate; the boots room doesn't count however far south it lies."""
    # Why: the half-plane holds the whole surface too, so a restart up there read the gate as passed and walked at it in armour.
    return in_temple(t) and in_ice_cavern(t) and not in_dark_room(t)


def in_trap_pit(t):
    return t.x >= 2672 and t.x <= 2686 and t.z >= 9845 and t.z <= 9856


# Why: the far side wraps past the ledge on both sides, and this box is the strip that holds only the ledge itself.
def on_winelda_ledge(t):
    """The ledge Winelda stands on, between the Fire Warrior's room and the lava."""
    return t.x >= 2643 and t.x <= 2658 and t.z >= 9871 and t.z <= 9879


# Why: the far side wraps around the Fire Warrior's room and Winelda's ledge, so only the temple behind the wall is boxable, and z 9893 is the one row where both sides have tiles.
def in_guardian_temple(t):
    """The guardians' temple, behind the secret wall."""
    if t.x < 2633 or t.x > 2651:
        return False
    if t.z >= 9894:
        return True
    return t.z == 9893 and t.x >= 2642 and t.x <= 2645


def in_temple(t):
    return t.level == 0 and t.x >= 2624 and t.x <= 2751 and t.z >= 9728 and t.z <= 9919

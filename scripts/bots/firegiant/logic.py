"""FireGiant's tiles and pure decisions: rs2b0t's scripts/FireGiant/FireGiantLogic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import Record

RAFT_STAND = Tile(2510, 3493, 0)
ROCK_TILE = Tile(2512, 3468, 0)
POST_ROCK = Tile(2513, 3468, 0)
TREE_STAND = Tile(2512, 3466, 0)
LEDGE = Tile(2511, 3463, 0)
LEDGE_DOOR = Tile(2511, 3464, 0)
WASHED_OUT = Tile(2527, 3413, 0)

# Why: 9892 sees two giants but can take a hit; 9893 is the one-target melee-proof fallback.
DEFAULT_SAFESPOT = Tile(2568, 9892, 0)
DEFAULT_SAFESPOT_FALLBACK = Tile(2568, 9893, 0)
DEFAULT_MELEE_TILE = Tile(2575, 9893, 0)

# Why: only attack targets already in weapon range, so the server doesn't walk off the safespot.
_ATTACK_RANGE = {'melee': 1, 'range': 7, 'mage': 10}


def attack_range_for(style, weapon=''):
    if style == 'range':
        lower = weapon.lower()
        if 'dart' in lower or 'knife' in lower:
            return 3
        if 'javelin' in lower:
            return 5
        if 'thrownaxe' in lower:
            return 4
        if 'crossbow' in lower:
            return 10
    return _ATTACK_RANGE.get(style, 1)


# Why: prefer east to west before distance, because a wall blocks the nearest west giant.
def east_first_key(x, distance):
    """A sort key: the easternmost first, then the nearest. rs2b0t's eastFirst comparator."""
    return (-x, distance)


# Why: gate targets by chamber, and keep npcs fighting someone else reserved through face target gaps.
def taken_by_another(is_ours, in_combat, targets_me, targets_another):
    """Whether a giant already belongs to someone else's fight."""
    if is_ours:
        return False
    return targets_another or (in_combat and not targets_me)


# Why: scale the pickup wait by distance, so the walk back to the safespot doesn't cancel a Take in flight.
def loot_wait_ms(distance):
    """How long to wait for a Take to land, given how far the drop is."""
    return 1200 + max(0, distance) * 700


_WEST_ROOM = (2556, 2571, 9880, 9902)
_EAST_ROOM = (2572, 2586, 9880, 9902)


def _in_box(t, b):
    return t.x >= b[0] and t.x <= b[1] and t.z >= b[2] and t.z <= b[3]


def room_of(t):
    """'west', 'east' or None."""
    if t is None:
        return None
    if _in_box(t, _WEST_ROOM):
        return 'west'
    return 'east' if _in_box(t, _EAST_ROOM) else None


# Why: the chambers overlap inside the field radius, so a drop in the next room reads as nearer than half of our own
# room's spawns.
def same_room(reference, other):
    """Whether two points share a chamber, permissive when the reference isn't in one."""
    room = room_of(reference)
    return room is None or room_of(other) == room


# Why: the exit door sits on the dungeon entry tile and drops you on the ledge, where the barrel ("A wooden barrel,
# maybe a way off this rock.") washes you to 2527,3413, 118 tiles from Ardougne West.
# Why: that walk out needs no runes, no magic level and no quest, so a teleport only saves the walk back to the door.
EXIT_DOOR = Tile(2575, 9861, 0)
EXIT_DOOR_LOC = 'Door'
BARREL_LOC = 'Barrel'
BARREL_OP = 'Get in'
RAFT_LOC = 'Log raft'
RAFT_OP = 'Board'
ROCK_LOC = 'Rock'
TREE_LOC = 'Dead tree'
LEDGE_LOC = 'Ledge'
LEDGE_OP = 'Open'
AMULET = "Glarial's amulet"
ROPE = 'Rope'

# The engine's inzone(0_39_54_14_20, 0_39_54_18_25): the rope throw is refused outside it.
THROW_ZONE = Record({'min_x': 2510, 'max_x': 2514, 'min_z': 3476, 'max_z': 3481})

# The rock is across water, so the op only lands from inside aplocu range; from the raft landing, 13 tiles off, the
# server answers "I can't reach that!" and nothing happens.
AP_RANGE = 10
ROPE_THROW_STAND = Tile(2512, 3477, 0)

DUNGEON_MIN_Z = 9000


def _cheb(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


def leg_for(t):
    """Where on the way in the bot stands: 'InDungeon', 'AtLedge', 'PastRock', 'AtLanding', 'WashedOut', 'AtRaft'
    or 'Surface'."""
    if t is None:
        return 'Surface'
    if t.z > DUNGEON_MIN_Z:
        return 'InDungeon'
    if t.x == LEDGE.x and t.z == LEDGE.z:
        return 'AtLedge'
    if _cheb(t, POST_ROCK) <= 3:
        return 'PastRock'
    if t.x >= THROW_ZONE.min_x and t.x <= THROW_ZONE.max_x and t.z >= THROW_ZONE.min_z and t.z <= THROW_ZONE.max_z:
        return 'AtLanding'
    if _cheb(t, WASHED_OUT) <= 6:
        return 'WashedOut'
    if _cheb(t, RAFT_STAND) <= 5:
        return 'AtRaft'
    return 'Surface'


class EscapeTele:
    """A teleport out: its spell name, magic level, runes as (rune, count), where it lands and the bank there."""

    def __init__(self, name, level, runes, lands, bank):
        self.name = name
        self.level = level
        self.runes = runes
        self.lands = lands
        self.bank = bank

    def __repr__(self):
        return f'EscapeTele({repr(self.name)})'


ESCAPE_TELES = {
    'Camelot': EscapeTele('Camelot', 45, [('Air rune', 5), ('Law rune', 1)], Tile(2757, 3478, 0), Tile(2725, 3491, 0)),
    'Ardougne': EscapeTele('Ardougne', 51, [('Water rune', 2), ('Law rune', 2)], Tile(2661, 3301, 0), Tile(2616, 3332, 0)),
    'Falador': EscapeTele('Falador', 37, [('Water rune', 1), ('Air rune', 3), ('Law rune', 1)], Tile(2965, 3378, 0), Tile(2946, 3369, 0)),
    'Varrock': EscapeTele('Varrock', 25, [('Fire rune', 1), ('Air rune', 3), ('Law rune', 1)], Tile(3213, 3424, 0), Tile(3185, 3440, 0)),
}

BARREL_EXIT = 'Barrel (free)'
EXIT_OPTIONS = [BARREL_EXIT] + list(ESCAPE_TELES.keys())
# Ardougne West, 118 tiles from the wash-up.
BARREL_BANK = Tile(2616, 3332, 0)

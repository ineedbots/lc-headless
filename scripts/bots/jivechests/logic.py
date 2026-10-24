"""JiveChests' tiles and pure decisions: rs2b0t's scripts/JiveChests/logic.ts (MIT, see thirdparty/rs2b0t)."""

KEY = 'Crystal key'
PACK = 28

# Why: the client's own names, since a drop and a count both match on those; "Swordfish" is the cooked one and "Body
# runes" is nothing the pack ever holds.
# The rewards that may be dropped to make room for ground loot.
JUNK = ['Raw swordfish', 'Body rune', 'Spinach roll', 'Adamant sq shield']

# The chest sits at (2914, 3452); this is the tile it's opened from.
CHEST_STAND = Tile(2914, 3451, 0)
CHEST = 'Closed chest'

# The keys a trip carries.
KEYS_PER_TRIP = 7

_REWARDS = [
    ['Uncut dragonstone'],
    ['Half of a key'],
    ['Runite bar'],
    ['Diamond'],
    ['Ruby'],
    ['Rune platelegs', 'Rune plateskirt'],
    ['Coins', 'Iron ore', 'Coal', 'Air rune', 'Water rune', 'Earth rune', 'Fire rune', 'Mind rune', 'Chaos rune', 'Death rune', 'Cosmic rune',
     'Nature rune', 'Law rune'],
]
_PRIORITIES = {}
for _rank in range(len(_REWARDS)):
    for _name in _REWARDS[_rank]:
        _PRIORITIES[_name.lower()] = _rank

# Not a reward worth taking: rs2b0t's Infinity.
NOT_LOOT = 1000000


def loot_priority(name):
    """The reward's rank, 0 the most valuable; NOT_LOOT for one not worth taking."""
    return _PRIORITIES.get((name or '').lower(), NOT_LOOT)


def junk_held(count):
    return sum([count(name) for name in JUNK])


def keys_to_withdraw(held, banked):
    """The keys to draw so the pack carries a full trip, bounded by what the bank holds."""
    return max(0, min(KEYS_PER_TRIP - held, banked))


class PackState:
    """What decide reads: keys and junk held, free slots, whether the bot stands at the chest, whether loot lies
    there and some of it can be taken, whether loot is left from before, and whether a bank trip is under way."""

    def __init__(self, keys=0, junk=0, free=0, at_chest=False, ground_loot=False, can_loot=False, pending_loot=False, banking=False):
        self.keys = keys
        self.junk = junk
        self.free = free
        self.at_chest = at_chest
        self.ground_loot = ground_loot
        self.can_loot = can_loot
        self.pending_loot = pending_loot
        self.banking = banking


def decide(pack):
    """The next step: 'drop', 'loot', 'open', 'travel' or 'bank'."""
    if pack.banking:
        return 'bank'
    if pack.pending_loot and not pack.at_chest:
        return 'travel'
    if pack.at_chest and pack.ground_loot:
        if pack.can_loot:
            return 'loot'
        return 'drop' if pack.free == 0 and pack.junk > 0 else 'bank'
    if pack.keys > 0 and pack.free > 0:
        return 'open' if pack.at_chest else 'travel'
    return 'bank'

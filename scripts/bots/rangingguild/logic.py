"""RangingGuild's tiles, ids and pure decisions: rs2b0t's scripts/RangingGuild/RangingGuildLogic.ts (MIT, see
thirdparty/rs2b0t)."""

from rs2004.catalogs import ToolTier, best_from_tiers

RANGED_REQUIRED = 40
ENTRY_FEE = 200
ARROW_RESTOCK_FEE = 100
SHOTS_PER_ROUND = 10
TICKETS_PER_RUNE_ARROWS = 2000
RUNE_ARROWS_PER_TRADE = 50

COINS = 995
BRONZE_ARROW = 882
RUNE_ARROW = 892
ARCHERY_TICKET = 1464
BRONZE_ARROW_NAME = 'Bronze arrow'
RUNE_ARROW_NAME = 'Rune arrow'
TICKET_NAME = 'Archery ticket'
COINS_NAME = 'Coins'

# The round's shots fired, its score, and where the last shot hit.
VARP_TARGET_COUNT = 156
VARP_TARGET_SCORE = 157
VARP_TARGET_HIT = 158

JUDGE = 'Competition Judge'
MERCHANT = 'Ticket Merchant'
TARGET = 'Target'
FIRE_OP = 'Fire-at'

STAND = Tile(2672, 3419, 0)
JUDGE_SPAWN = Tile(2669, 3418, 0)
JUDGE_STAND = Tile(2670, 3418, 0)
MERCHANT_STAND = Tile(2659, 3430, 0)
SEERS_BANK = Tile(2725, 3491, 0)
TARGETS = [Tile(2679, 3426, 0), Tile(2679, 3428, 0), Tile(2681, 3425, 0), Tile(2681, 3427, 0), Tile(2682, 3425, 0)]

BOWS = [
    ToolTier('Magic shortbow', 50), ToolTier('Magic longbow', 50),
    ToolTier('Yew shortbow', 40), ToolTier('Yew longbow', 40),
    ToolTier('Maple shortbow', 30), ToolTier('Maple longbow', 30),
    ToolTier('Willow shortbow', 20), ToolTier('Willow longbow', 20),
    ToolTier('Oak shortbow', 5), ToolTier('Oak longbow', 5),
    ToolTier('Shortbow', 1), ToolTier('Longbow', 1),
]

_BOW_NAMES = set([b.name.lower() for b in BOWS])


def is_bow(name):
    return name is not None and name.lower() in _BOW_NAMES


def best_bow(ranged_level, available):
    return best_from_tiers(ranged_level, BOWS, available)


JUDGE_PREFS = ['give it a go', 'take some', "i've got it"]


def pick_option(options, prefs):
    """The index of the first option holding the first preference that any holds, or -1."""
    lower = [o.lower() for o in options]
    for pref in prefs:
        wanted = pref.lower()
        for i in range(len(lower)):
            if wanted in lower[i]:
                return i
    return -1


def round_phase(target_count):
    """'idle', 'shooting' or 'finished'."""
    if target_count >= 1 and target_count <= SHOTS_PER_ROUND:
        return 'shooting'
    return 'finished' if target_count == SHOTS_PER_ROUND + 1 else 'idle'


class WorldView:
    """What decide reads: the round's shot count, the tickets and coins held, whether a bow is worn or held, and
    the bronze arrows worn and held."""

    def __init__(self, target_count=0, tickets=0, coins=0, bow_worn=False, bow_held=False, bronze_worn=0, bronze_held=0):
        self.target_count = target_count
        self.tickets = tickets
        self.coins = coins
        self.bow_worn = bow_worn
        self.bow_held = bow_held
        self.bronze_worn = bronze_worn
        self.bronze_held = bronze_held


def decide(v):
    """The next action: 'redeem', 'collect', 'wield-bow', 'wield-arrows', 'shoot', 'restock-arrows', 'enter' or
    'bank'."""
    if v.tickets >= TICKETS_PER_RUNE_ARROWS:
        return 'redeem'
    phase = round_phase(v.target_count)
    if phase == 'finished':
        return 'collect'
    if not v.bow_worn:
        return 'wield-bow' if v.bow_held else 'bank'
    if phase == 'shooting':
        if v.bronze_worn > 0:
            return 'shoot'
        if v.bronze_held > 0:
            return 'wield-arrows'
        return 'restock-arrows' if v.coins >= ARROW_RESTOCK_FEE else 'bank'
    return 'enter' if v.coins >= ENTRY_FEE else 'bank'


# Each refusal's lines, matched without regard to case.
_REFUSALS = [
    (['behind the'], 'too-close'),
    (['bow might help', 'need a bow'], 'no-bow'),
    (['needing those bronze arrows', 'use the 10 bronze arrows'], 'no-arrows'),
    (['fired all your arrows'], 'round-over'),
    (['ask before using', 'only use the targets'], 'not-entered'),
    (["i can't reach that"], 'unreachable'),
]


def classify_shot(messages):
    """Why a shot was refused, from the game messages since it: 'too-close', 'no-bow', 'no-arrows', 'round-over',
    'not-entered' or 'unreachable'; None for none."""
    for text in messages:
        lower = text.lower()
        for patterns, refusal in _REFUSALS:
            for pattern in patterns:
                if pattern in lower:
                    return refusal
    return None


def hit_label(hit):
    if hit == 0:
        return 'Bulls-Eye!'
    if hit == 1:
        return 'Hit Yellow!'
    if hit <= 4:
        return 'Hit Red!'
    if hit <= 8:
        return 'Hit Blue!'
    if hit <= 10:
        return 'Hit Black!'
    return 'Missed!'


def hit_points(hit):
    if hit == 0:
        return 100
    if hit == 1:
        return 50
    if hit <= 4:
        return 30
    if hit <= 8:
        return 20
    if hit <= 10:
        return 10
    return 0


def tickets_for_score(score):
    return score // 10

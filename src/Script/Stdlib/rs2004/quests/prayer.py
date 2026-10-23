"""Holding a quest's protection prayer: rs2b0t's api/ai/quests/prayer.ts (MIT, see thirdparty/rs2b0t). A quest
declares its prayer as {protect: 'melee', 'magic' or 'missiles', potions: doses to carry}; set_quest_prayer points
the upkeep at it, and prayer_upkeep, which the prompts call between boxes, spends a tick on it when one's needed."""

from rs2004.game import game
from rs2004.items import inventory
from rs2004.tabs import PROTECT_FROM_MAGIC, PROTECT_FROM_MELEE, PROTECT_FROM_MISSILES, prayer

__all__ = [
    'PRAYER_FLOOR', 'PROTECT_LEVEL', 'PROTECTION_NAME', 'PRAYER_POTION', 'PRAYER_POTION_IDS', 'prayer_upkeep_action',
    'protection_name', 'protection_level', 'quest_prayer_state', 'set_quest_prayer', 'prayer_upkeep',
]

# Points at which a dose is worth more than the swing it costs.
PRAYER_FLOOR = 25

# Level 43 gates Protect from Melee, the highest of the three.
PROTECT_LEVEL = {'magic': 37, 'missiles': 40, 'melee': 43}

PROTECTION_NAME = {'melee': PROTECT_FROM_MELEE, 'magic': PROTECT_FROM_MAGIC, 'missiles': PROTECT_FROM_MISSILES}

# The dose the engine draws into the float; the smaller flasks are drunk if the bank only has those.
PRAYER_POTION = 'Prayer potion(4)'

# Every dose form, so a half-used flask still counts as a dose in the pack.
PRAYER_POTION_IDS = [2434, 139, 141, 143]


def prayer_upkeep_action(in_combat, protect_active, protect_available, points, doses):
    """The one thing to do this tick: 'none', 'protect', 'drink' or 'drop'.

    Why: the server runs one op per tick and drops the rest, so upkeep names a single action and the caller spends
    the tick on it. Why: protection is dropped as soon as a fight ends; held through the walk out it empties the
    flask the next fight needed."""
    if not in_combat:
        return 'drop' if protect_active else 'none'
    if points <= PRAYER_FLOOR and doses > 0:
        return 'drink'
    if not protect_active and protect_available:
        return 'protect'
    return 'none'


def _protect(pray):
    return pray['protect'] if isinstance(pray, dict) else pray.protect


def protection_name(pray):
    return PROTECTION_NAME[_protect(pray)]


def protection_level(pray):
    return PROTECT_LEVEL[_protect(pray)]


class _QuestPrayerState:
    """The running quest's prayer, shared by one-shot steps, sustain loops and long fights."""

    def __init__(self):
        self.current = None
        self.warned = False
        self.log = None


quest_prayer_state = _QuestPrayerState()


def set_quest_prayer(pray, log):
    """Points the upkeep at a quest's prayer; None for a quest that declares none."""
    quest_prayer_state.current = pray
    quest_prayer_state.warned = False
    quest_prayer_state.log = log


def _say(text):
    if quest_prayer_state.log is not None:
        quest_prayer_state.log(text)


def prayer_upkeep():
    """Spends at most one tick holding the running quest's protection prayer. True when it acted. Use with yield
    from."""
    pray = quest_prayer_state.current
    if not pray:
        return False
    name = protection_name(pray)
    if prayer.max() < protection_level(pray):
        if not quest_prayer_state.warned:
            quest_prayer_state.warned = True
            _say(f'Prayer {prayer.max()}, no {name}, fighting on food alone')
        return False
    doses = [item for item in inventory.items() if item.id in PRAYER_POTION_IDS]
    action = prayer_upkeep_action(game.in_combat(), prayer.active(name), prayer.available(name), prayer.points(), len(doses))
    if action == 'drink':
        _say(f'drinking a prayer dose ({prayer.points()}/{prayer.max()})')
        return doses[0].interact('Drink')
    if action == 'protect':
        _say(f'raising {name} ({prayer.points()}/{prayer.max()})')
        result = yield from prayer.set(name, True)
        return result
    if action == 'drop':
        result = yield from prayer.set(name, False)
        return result
    return False

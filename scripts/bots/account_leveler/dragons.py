from rs2004.geometry import Tile
"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/dragons.ts (MIT, see thirdparty/rs2b0t)."""

import math
from bots.account_leveler.record import Record

__all__ = ['DRAGON_CAMPS', 'dragon_ready', 'dragon_food_levels', 'dragon_planks', 'next_dragon_quest', 'dragon_supply_levels', 'dragon_prayer']

from rs2004.quests.defs.dragonslayer.journal import DRAGON_STAGE
from rs2004.quests.data import QUESTS
from bots.account_leveler.equipment import melee_equipment
from bots.account_leveler.types import stock_of
QUEST_ORDER = [
    'runemysteries',
    'cook',
    'doric',
    'sheep',
    'priest',
    'haunted',
    'hetty',
    'romeojuliet',
    'prince',
    'hunt',
    'gobdip',
    'blackknight',
    'vampire',
    'squire',
    'arthur',
]
DRAGON_CAMPS = ['prayer-green-dragons', 'prayer-blue-dragons']


def dragon_ready(s):
    return all([s.levels.get(skill) >= 40 for skill in ['attack', 'strength', 'defence', 'hitpoints']])


def dragon_food_levels(s):
    return (Record({}) if stock_of(s, 'Lobster') >= 40 else Record({'fishing': 40, 'cooking': 40}))


def dragon_planks(s):
    if ((s.dragon_stage if s.dragon_stage is not None else 0)) >= DRAGON_STAGE.REPAIRED_SHIP:
        return 0
    return (min(3, stock_of(s, 'Plank')) if s.dragon_stage == DRAGON_STAGE.BOUGHT_SHIP and stock_of(s, 'Plank') > 0 else 3)


def next_dragon_quest(s, memory):
    if s.quests.get('Dragon Slayer') or not dragon_ready(s) or not s.wilderness and stock_of(s, 'Plank') < dragon_planks(s):
        return None
    points = (s.quest_points if s.quest_points is not None else sum([((q.quest_points if s.quests.get(q.name) else 0)) for q in QUESTS]))
    _v3 = ([q for q in [([q for q in QUESTS if q.id == id] or [None])[0] for id in ((['dragon'] if points >= 32 else QUEST_ORDER))] if not s.quests.get(q.name) and ((q.requirements.min_quest_points if q.requirements.min_quest_points is not None else 0)) <= points and all([s.quests.get(name) for name in ((q.requirements.quests if q.requirements.quests is not None else []))]) and not any([id.startswith(f'quest-{q.id}-') and until > s.now for id, until in list(memory.cooldowns.items())]) and ((memory.cooldowns.get(f'quest-{q.id}') if memory.cooldowns.get(f'quest-{q.id}') is not None else 0)) <= s.now] or [None])[0]
    return (_v3 if _v3 is not None else None)


def dragon_supply_levels(s):
    if ((s.dragon_stage if s.dragon_stage is not None else 0)) >= DRAGON_STAGE.REPAIRED_SHIP:
        return Record({})
    _merged4 = {}
    for _k, _v in (((Record({'smithing': 34, 'mining': 30}) if stock_of(s, 'Nails') < dragon_planks(s) * 4 else Record({})))._fields if isinstance(((Record({'smithing': 34, 'mining': 30}) if stock_of(s, 'Nails') < dragon_planks(s) * 4 else Record({}))), Record) else ((Record({'smithing': 34, 'mining': 30}) if stock_of(s, 'Nails') < dragon_planks(s) * 4 else Record({})))).items():
        _merged4[_k] = _v
    for _k, _v in (((Record({'crafting': 8}) if stock_of(s, 'Unfired bowl') < 1 else Record({})))._fields if isinstance(((Record({'crafting': 8}) if stock_of(s, 'Unfired bowl') < 1 else Record({}))), Record) else ((Record({'crafting': 8}) if stock_of(s, 'Unfired bowl') < 1 else Record({})))).items():
        _merged4[_k] = _v
    return Record(_merged4)


def dragon_prayer(s, memory, random):
    if not dragon_ready(s) or stock_of(s, 'Dragonfire shield') < 1:
        return None
    candidates = [id for id in DRAGON_CAMPS if (id != DRAGON_CAMPS[0] or s.wilderness) and ((memory.cooldowns.get(id) if memory.cooldowns.get(id) is not None else 0)) <= s.now]
    fresh = [id for id in candidates if not (id in memory.recent[-3:])]
    choices = (fresh if len(fresh) else candidates)
    if not len(choices):
        return None
    id = choices[min(len(choices) - 1, math.floor(max(0, random()) * len(choices)))]
    green = id == DRAGON_CAMPS[0]
    gear = melee_equipment(s)
    weapon = gear[0].item
    _merged5 = {}
    for _k, _v in {
        'combat_style': 'melee',
        'melee_style': 'strength',
        'weapon': weapon,
        'loadout': '',
        'food': 'Lobster',
        'food_withdraw': 20,
        'use_potions': False,
        'use_special': False,
        'bury_bones': True,
        'solve_clues': False,
        'bank_common_junk': False,
        'loot': ['Dragon bones', 'Dragonhide'],
    }.items():
        _merged5[_k] = _v
    for _k, _v in (((Record({'escape': 'Flee to bank'}) if green else Record({'site': 'taverley-blue', 'leave_via': 'walk'})))._fields if isinstance(((Record({'escape': 'Flee to bank'}) if green else Record({'site': 'taverley-blue', 'leave_via': 'walk'}))), Record) else ((Record({'escape': 'Flee to bank'}) if green else Record({'site': 'taverley-blue', 'leave_via': 'walk'})))).items():
        _merged5[_k] = _v
    return Record({
        'id': id,
        'objective': 'prayer',
        'label': f"{('Green' if green else 'Blue')} dragons for Prayer",
        'script': ('GreenDragon' if green else 'JiveDragons'),
        'combat': True,
        'wilderness': green,
        'food': 'Lobster',
        'travel': (Tile(3094, 3493, 0) if green else Tile(2946, 3368, 0)),
        'needs': list(gear) + [Record({'item': 'Dragonfire shield', 'count': 1, 'carry': 1, 'equip': True}), Record({'item': 'Lobster', 'count': 40, 'carry': 20}), Record({'item': 'Coins', 'count': 200, 'carry': 200})],
        'settings': Record(_merged5),
    })

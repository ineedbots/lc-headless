"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/equipment.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import AXES, PICKAXES
from bots.account_leveler.record import Record

__all__ = ['gathering_tool', 'melee_equipment', 'ranged_bow']

from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.types import requirement_key
DRAGON_WEAPONS = ['Dragon longsword', 'Dragon dagger']

metals = [
    Record({'item': 'Rune', 'level': 40}),
    Record({'item': 'Adamant', 'level': 30}),
    Record({'item': 'Mithril', 'level': 20}),
    Record({'item': 'Black', 'level': 10}),
    Record({'item': 'Steel', 'level': 5}),
    Record({'item': 'Iron', 'level': 1}),
    Record({'item': 'Bronze', 'level': 1}),
]
bows = [
    Record({'item': 'Magic shortbow', 'id': 861, 'level': 50}),
    Record({'item': 'Magic longbow', 'id': 859, 'level': 50}),
    Record({'item': 'Yew shortbow', 'id': 857, 'level': 40}),
    Record({'item': 'Yew longbow', 'id': 855, 'level': 40}),
    Record({'item': 'Maple shortbow', 'id': 853, 'level': 30}),
    Record({'item': 'Maple longbow', 'id': 851, 'level': 30}),
    Record({'item': 'Willow shortbow', 'id': 849, 'level': 20}),
    Record({'item': 'Willow longbow', 'id': 847, 'level': 20}),
    Record({'item': 'Oak shortbow', 'id': 843, 'level': 5}),
    Record({'item': 'Oak longbow', 'id': 845, 'level': 5}),
    Record({'item': 'Shortbow', 'id': 841, 'level': 1}),
    Record({'item': 'Longbow', 'id': 839, 'level': 1}),
]


def cost(s, level, choice):
    if level < choice.level or (choice.quest and not s.quests.get(choice.quest)):
        return float('inf')
    _merged1 = {}
    for _k, _v in (choice._fields if isinstance(choice, Record) else choice).items():
        _merged1[_k] = _v
    for _k, _v in {'count': 1}.items():
        _merged1[_k] = _v
    key = requirement_key(Record(_merged1)).lower()
    _v2 = s.stock.get(key)
    if ((_v2 if _v2 is not None else 0)) > 0:
        return 0
    if (any([item.lower() == key or item.lower() == choice.item.lower() for item in s.unavailable_items]) if s.unavailable_items is not None else None):
        return float('inf')
    offer = supply_offer(choice.item)
    return (purchase_budget(offer, 1) if offer else float('inf'))


def choose(s, level, choices, fallback, coins):
    def _fn4(choice):
        price = cost(s, level, choice)
        return price == 0 or price <= coins - 200
    _v5 = ([_x for _x in choices if _fn4(_x)] or [None])[0]
    selected = (_v5 if _v5 is not None else fallback)
    _merged6 = {}
    for _k, _v in {'item': selected.item}.items():
        _merged6[_k] = _v
    for _k, _v in (((Record({}) if selected.id is None else Record({'id': selected.id})))._fields if isinstance(((Record({}) if selected.id is None else Record({'id': selected.id}))), Record) else ((Record({}) if selected.id is None else Record({'id': selected.id})))).items():
        _merged6[_k] = _v
    for _k, _v in {'count': 1, 'carry': 1}.items():
        _merged6[_k] = _v
    return Record(_merged6)


def gathering_tool(s, kind):
    tiers = [(Record({'item': tier.name, 'level': tier.level})) for tier in ((AXES if kind == 'axe' else PICKAXES))]
    _v7 = s.stock.get('coins')
    return choose(s, s.levels.get(('woodcutting' if kind == 'axe' else 'mining')), tiers, tiers[len(tiers) - 1], (_v7 if _v7 is not None else 0))


def choices_for(suffixes):
    choices = []
    for metal in metals:
        for suffix in suffixes:
            choice = Record({'item': f'{metal.item} {suffix}', 'level': metal.level})
            if metal.item == 'Rune' and suffix == 'platebody':
                choice.quest = 'Dragon Slayer'
            choices.append(choice)
    return choices


def melee_equipment(s):
    coins = s.stock.get('coins', 0)
    dragons = [Record({'item': item, 'level': 60, 'quest': 'Lost City'}) for item in DRAGON_WEAPONS if s.stock.get(item.lower(), 0) > 0]
    slots = [
        Record({'level': s.levels.get('attack'), 'choices': dragons + choices_for(['scimitar']), 'fallback': Record({'item': 'Iron scimitar', 'level': 1})}),
        Record({'level': s.levels.get('defence'), 'choices': choices_for(['platebody', 'chainbody']), 'fallback': Record({'item': 'Iron chainbody', 'level': 1})}),
        Record({'level': s.levels.get('defence'), 'choices': choices_for(['platelegs', 'plateskirt']), 'fallback': Record({'item': 'Iron platelegs', 'level': 1})}),
    ]
    kit = []
    for index, slot in enumerate(slots):
        remaining = 0
        for next_slot in slots[index + 1:]:
            minimum = min([cost(s, next_slot.level, choice) for choice in next_slot.choices])
            if minimum != float('inf'):
                remaining += minimum
        need = choose(s, slot.level, slot.choices, slot.fallback, coins - remaining)
        if s.stock.get(requirement_key(need).lower(), 0) <= 0:
            offer = supply_offer(need.item)
            if offer:
                coins -= purchase_budget(offer, 1)
        need['equip'] = True
        kit.append(need)
    for choice in choices_for(['full helm', 'med helm']):
        price = cost(s, s.levels.get('defence'), choice)
        if price == 0 or price <= coins - 200:
            kit.append(Record({'item': choice.item, 'count': 1, 'carry': 1, 'equip': True}))
            break
    return kit


def ranged_bow(s):
    need = choose(s, s.levels.get('ranged'), bows, Record({'item': 'Shortbow', 'id': 841, 'level': 1}), s.stock.get('coins', 0))
    need['equip'] = True
    return need

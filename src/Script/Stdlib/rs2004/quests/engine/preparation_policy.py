"""Ported from rs2b0t's src/bot/api/ai/quests/engine/preparationPolicy.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.record import Record
from rs2004.quests.defs.tbwt.areas import FOOD_TARGET as TB_FOOD_TARGET, TB_MAIN
from rs2004.quests.defs.touristtrap_supplies import TOURIST_TRAP_FOOD_TARGET
from rs2004.quests.food import FOOD_FLOAT

__all__ = ['quest_food_request', 'quest_preparation_request']

from rs2004.catalogs.tables import item_db
ITEM_DB = item_db()
from rs2004.market._data import UNTRADEABLE_IDS
def supplies(*items):
    return [(Record({'item': item, 'count': 1}) if isinstance(item, str) else Record({'item': item[0], 'count': item[1]})) for item in items]


SUPPLIES = Record({
    'elemental_workshop': supplies('Hammer', 'Thread'),
    'priestperil': supplies('Bronze pickaxe'),
    'death': supplies(['Bread', 10], ['Trout', 10], 'Iron bar'),
    'itwatchtower': supplies('Guam leaf', 'Bat bones', 'Gold bar'),
    'tbwt': supplies('Small fishing net', 'Seaweed'),
    'upass': supplies(['Bronze arrow', 50], 'Tinderbox', 'Spade', 'Bucket'),
    'regicide': supplies('Spade'),
    'legends': supplies('Rune axe', 'Lockpick', 'Unpowered orb', ['Cosmic rune', 3], ['Prayer potion(4)', 3]),
})
FOOD_COUNTS = Record({
    'squire': 8,
    'haunted': 8,
    'hunt': 8,
    'blackarmgang': 8,
    'gobdip': 8,
    'demon': 8,
    'blackknight': 8,
    'druid': 8,
    'zanaris': 8,
    'itwatchtower': 8,
    'junglepotion': 8,
    'tbwt': TB_FOOD_TARGET,
    'zombiequeen': 8,
    'elemental_workshop': 8,
    'troll': 8,
    'eadgar': 8,
    'biohazard': 8,
    'crest': 10,
    'horror': 8,
    'chompybird': 6,
    'upass': 8,
    'regicide': 8,
    'viking': 8,
    'hero': 8,
    'legends': 9,
})
FIXED_FOOD = Record({'upass': 'Lobster', 'regicide': 'Shark'})
FOOD_CHOICES = Record({
    'crest': ['Lobster', 'Shark', 'Trout', 'Herring'],
    'legends': ['Lobster', 'Shark', 'Swordfish', 'Tuna'],
    'ikov': ['Lobster', 'Swordfish', 'Tuna'],
    'elemental_workshop': ['Lobster', 'Swordfish', 'Salmon', 'Trout'],
})
MATERIAL_FOOD = Record({
    'death': ['bread', 'trout'],
    'crest': ['tuna', 'bass', 'salmon', 'shrimps', 'swordfish'],
    'tbwt': ['banana', 'sliced banana', 'raw karambwan', 'karambwan', 'poorly cooked karambwan'],
    'regicide': ['cooked rabbit'],
})
FISH = [['Swordfish', 50, 45], ['Bass', 46, 43], ['Tuna', 35, 30], ['Salmon', 30, 25], ['Shrimps', 1, 1]]
PROTECT = Record({'melee': 43, 'missiles': 40, 'magic': 37})
ORDINARY_SUPPLIES = set(['coins'])
for _key in SUPPLIES.keys():
    for _item in SUPPLIES.get(_key):
        ORDINARY_SUPPLIES.add(_item.item.lower())


def ordinary_item(name):
    if (name.lower() in ORDINARY_SUPPLIES):
        return True
    matches = [item for item in ITEM_DB if item.name.lower() == name.lower()]
    return len(matches) == 1 and not (matches[0].id in UNTRADEABLE_IDS)


def quest_food_request(module, configured):
    id = module.record.id
    if id == 'waterfall':
        return None
    if id == 'desertrescue':
        return (Record({'item': configured.strip(), 'count': TOURIST_TRAP_FOOD_TARGET}) if (configured.strip() if configured is not None else None) else None)
    _v1 = FOOD_COUNTS.get(id)
    _v2 = (_v1 if _v1 is not None else module.food)
    count = (_v2 if _v2 is not None else ((FOOD_FLOAT if module.sustain else 0)))
    if count <= 0:
        return None
    choices = FOOD_CHOICES.get(id)
    _v3 = MATERIAL_FOOD.get(id)
    forbidden = (_v3 if _v3 is not None else [])
    preferred = (configured.strip() if configured is not None else None)
    accepted = preferred and not (preferred.lower() in forbidden) and (not choices or any([item.lower() == preferred.lower() for item in choices]))
    fallback = [name for name in (module.sustain.foods if module.sustain is not None else []) if name.lower() not in forbidden]
    item = FIXED_FOOD.get(id) or (preferred if accepted else (choices[0] if choices else (fallback[0] if fallback else 'Trout')))
    return Record({'item': item, 'count': count})


def quest_preparation_request(module, food_name, status, stock=None, stock_ids=None, progress=None):
    if stock is None:
        stock = {}
    if status == 'unknown' or status == 'complete':
        return None
    id = module.record.id
    if id == 'desertrescue' and status == 'in_progress':
        return None
    levels = {}

    def skill(name, level):
        _v6 = levels.get(name)
        levels[name] = max((_v6 if _v6 is not None else 0), level)

    def count(name):
        return (stock.get(name.lower()) if stock.get(name.lower()) is not None else 0)

    def has(*names):
        return any([count(name) > 0 for name in names])

    for requirement in (module.record.requirements.skills if module.record.requirements.skills is not None else []):
        skill(requirement.skill, requirement.level)
    if module.pray and id != 'troll':
        skill('prayer', PROTECT.get(module.pray.protect))
    if id == 'upass':
        skill('ranged', 25)
    items = []
    if status == 'not_started':
        required = [(Record({'item': item.name, 'count': item.qty})) for item in [item for item in module.record.items if item.kind == 'mustHave' and ordinary_item(item.name)]]
        for supply in list((SUPPLIES.get(id) if SUPPLIES.get(id) is not None else [])) + list(required):
            if id == 'tbwt' and supply.item.startswith('Agility potion'):
                continue
            if supply.item == 'Bronze pickaxe' and any([qty > 0 and name.endswith('pickaxe') for name, qty in list(stock.items())]):
                continue
            if supply.item.endswith('potion(4)'):
                base = supply.item[0:-3]
                doses = sum([count(f'{base}({dose})') * dose for dose in [1, 2, 3, 4]])
                if doses >= supply.count * 4:
                    continue
            existing = ([item for item in items if item.item.lower() == supply.item.lower()] or [None])[0]
            if existing:
                existing.count = max(existing.count, supply.count)
            else:
                items.append(Record({'item': supply.item, 'count': supply.count}))
        if id == 'squire' and count('Iron bar') < 2:
            skill('smithing', 15)
            if count('Iron ore') < 2 - count('Iron bar'):
                skill('mining', 15)
        if id == 'elemental_workshop' and count('Coal') < 4:
            skill('mining', 30)
        if id == 'druidspirit' and not has('Silver sickle', 'Silver sickle(b)', 'Silver bar'):
            skill('smithing', 20)
            if not has('Silver ore'):
                skill('mining', 20)
        if id == 'chompybird':
            skill('crafting', 5)
        if id == 'tbwt':
            skill('firemaking', 30)
        if id == 'regicide' and count('Coal') < 12:
            skill('mining', 30)
        if id == 'dragon':
            if not has('Unfired bowl'):
                skill('crafting', 8)
            if count('Nails') < 12:
                skill('smithing', 34)
                bars = max(0, math.ceil((12 - count('Nails')) / 2) - count('Steel bar'))
                if count('Iron ore') < bars:
                    skill('mining', 15)
                if count('Coal') < bars * 2:
                    skill('mining', 30)
        if id == 'crest':
            for fish, fishing, cooking in FISH:
                if has(fish):
                    continue
                skill('cooking', cooking)
                if not has(f'Raw {fish}'):
                    skill('fishing', fishing)
        bow_ready = (((stock_ids.get(857) if stock_ids.get(857) is not None else 0)) > 0 if stock_ids is not None else has('Yew shortbow'))
        if id == 'ikov' and not bow_ready:
            skill('fletching', 65)
            stave = (((stock_ids.get(68) if stock_ids.get(68) is not None else 0)) > 0 if stock_ids is not None else has('Yew shortbow (u)'))
            if not stave and not has('Yew logs'):
                skill('woodcutting', 60)
            if not has('Bow string'):
                skill('crafting', 10)
        if id == 'hero':
            if not has('Ice gloves', 'Fire feather'):
                skill('mining', 50)
            if not has('Lava eel'):
                skill('cooking', 53)
            if not has('Lava eel', 'Raw lava eel'):
                skill('fishing', 53)
                if not has('Oily fishing rod', 'Blamish oil'):
                    skill('herblore', 25)
    if id == 'tbwt' and not (progress is not None and 'agility' in progress.flags) and (((progress.stage if progress is not None else None) if (progress.stage if progress is not None else None) is not None else 0)) < TB_MAIN.ALL_BROTHERS:
        doses = sum([count(f'Agility potion({dose})') * dose for dose in [1, 2, 3, 4]])
        if doses < 4:
            items.append(Record({'item': 'Agility potion(3)', 'count': count('Agility potion(3)') + math.ceil((4 - doses) / 3)}))
    food = quest_food_request(module, food_name)
    skills = [(Record({'skill': name, 'level': level})) for name, level in list(levels.items())]
    request = Record({})
    if skills:
        request.skills = skills
    if items:
        request.items = items
    if food:
        request.food = food
    return request

"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/catalog.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['refresh_consumables', 'consumable_batch', 'WOODS', 'FLETCHING', 'FISH', 'MILESTONES', 'can_source_wood', 'next_milestone', 'POTIONS', 'smith_product', 'can_catch']

from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.types import stock_of
def refresh_consumables(s, plan):
    style = ('craft' if plan.script == 'LeatherCrafter' else ('fish' if plan.script == 'Fisher' else (plan.settings.get('combat_style') if plan.script == 'AutoFighter' else None)))
    if style == 'mage':
        from bots.account_leveler.magic import magic_equipment
        magic = magic_equipment(s)
        result = Record(plan._fields)
        result.needs = [need for need in plan.needs if not need.item.lower().endswith(' rune') and need.item != 'Staff of air'] + magic.needs
        result.settings = Record(plan.settings._fields)
        result.settings['spell'] = magic.spell
        result.settings['runes_withdraw'] = magic.casts
        return result
    if style != 'craft' and style != 'fish' and style != 'range' and style != 'mage':
        return plan


    consumables = [need for need in plan.needs if ((need.minimum if need.minimum is not None else 0)) > 0 and (((need.item.lower().endswith(' rune')) if style == 'mage' else need.item == (('Thread' if style == 'craft' else ('Feather' if style == 'fish' else 'Bronze arrow')))))]
    if not len(consumables):
        return plan
    target = (100 if style == 'craft' else (300 if style == 'range' else 200))
    batch = consumable_batch(s, [(Record({'item': need.item, 'count': need.minimum})) for need in consumables], target, (150 if style == 'mage' else target))

    needs = []
    for need in plan.needs:
        if need in consumables:
            index = consumables.index(need)
            replacement = Record(need._fields)
            for key, value in batch[index].items():
                replacement[key] = value
            needs.append(replacement)
        else:
            needs.append(need)
    setting = 'thread_per_trip' if style == 'craft' else ('runes_withdraw' if style == 'mage' else ('bait_qty' if style == 'fish' else 'ammo_withdraw'))
    settings = Record(plan.settings._fields)
    settings[setting] = batch[0].carry // batch[0].minimum
    result = Record(plan._fields)
    result.settings = settings
    result.needs = needs
    return result


def consumable_batch(s, costs, target, carry=None):
    if carry is None:
        carry = target
    banked = min(target, *[(stock_of(s, cost.item) // cost.count) for cost in costs])
    uses = (banked if banked > 0 else target)
    return [(Record({
        'item': cost.item,
        'count': uses * cost.count,
        'carry': min(carry, uses) * cost.count,
        'minimum': cost.count,
    })) for cost in costs]


WOODS = [
    Record({'level': 1, 'item': 'Logs', 'tree': 'Tree', 'location': 'Draynor (trees)'}),
    Record({'level': 15, 'item': 'Oak logs', 'tree': 'Oak', 'location': 'Draynor Oaks'}),
    Record({'level': 30, 'item': 'Willow logs', 'tree': 'Willow', 'location': 'Draynor Willows'}),
]
FLETCHING = [
    Record({'level': 1, 'item': 'Logs', 'product': 'Arrow shafts'}),
    Record({'level': 5, 'item': 'Logs', 'product': 'Short bow'}),
    Record({'level': 10, 'item': 'Logs', 'product': 'Long bow'}),
    Record({'level': 20, 'item': 'Oak logs', 'product': 'Short bow'}),
    Record({'level': 25, 'item': 'Oak logs', 'product': 'Long bow'}),
    Record({'level': 35, 'item': 'Willow logs', 'product': 'Short bow'}),
    Record({'level': 40, 'item': 'Willow logs', 'product': 'Long bow'}),
]
FISH = [
    Record({
    'level': 1,
    'cooking': 1,
    'food': 'Shrimps',
    'method': 'Small net — shrimp/anchovy',
    'location': 'Draynor Village',
    'tool': 'Small fishing net',
}),
    Record({
    'level': 20,
    'cooking': 15,
    'food': 'Trout',
    'method': 'Fly fishing — trout/salmon',
    'location': 'Barbarian Village',
    'tool': 'Fly fishing rod',
}),
    Record({
    'level': 30,
    'cooking': 25,
    'food': 'Salmon',
    'method': 'Fly fishing — trout/salmon',
    'location': 'Barbarian Village',
    'tool': 'Fly fishing rod',
}),
    Record({
    'level': 40,
    'cooking': 40,
    'food': 'Lobster',
    'method': 'Lobster cage — lobster',
    'location': 'Catherby',
    'tool': 'Lobster pot',
}),
    Record({
    'level': 76,
    'cooking': 80,
    'food': 'Shark',
    'method': 'Harpoon — sharks',
    'location': 'Catherby',
    'tool': 'Harpoon',
}),
]
MILESTONES = Record({
    'agility': [15],
    'thieving': [10, 25],
    'herblore': [5, 12, 22, 30, 38],
    'mining': [6, 21, 30, 31, 41],
    'woodcutting': [15, 30],
    'fishing': [20, 30, 40],
    'cooking': [15, 25, 40],
    'firemaking': [15, 30],
    'fletching': [5, 10, 20, 25, 35, 40],
    'smithing': [15, 30],
    'attack': [5, 20, 30, 40],
    'defence': [5, 20, 30, 40],
    'ranged': [5, 20, 30, 40],
    'magic': [5, 9, 13, 17, 23, 29, 35],
})


def can_source_wood(s, item):
    wood = ([w for w in WOODS if w.item == item] or [None])[0]
    return stock_of(s, item) >= 28 or not not wood and s.levels.get('woodcutting') >= wood.level


def next_milestone(s, skill):
    return (([level for level in MILESTONES.get(skill) if level > s.levels.get(skill) and level < s.target] or [None])[0] if MILESTONES.get(skill) is not None else None)


POTIONS = [
    Record({'level': 3, 'herb': 'Guam leaf', 'secondary': 'Eye of newt'}),
    Record({'level': 5, 'herb': 'Marrentill', 'secondary': 'Unicorn horn dust'}),
    Record({'level': 12, 'herb': 'Tarromin', 'secondary': 'Limpwurt root'}),
    Record({'level': 22, 'herb': 'Harralander', 'secondary': "Red spiders' eggs"}),
    Record({'level': 30, 'herb': 'Ranarr weed', 'secondary': 'White berries'}),
    Record({'level': 38, 'herb': 'Ranarr weed', 'secondary': 'Snape grass'}),
]


def smith_product(level, metal):
    offset = (15 if metal == 'Iron' else 0)
    return ('Platebody' if level >= 18 + offset else ('2h sword' if level >= 14 + offset else ('Scimitar' if level >= 5 + offset else 'Dagger')))


def can_catch(s, fish):
    if s.levels.get('fishing') < fish.level:
        return False
    needs = [Record({'item': fish.tool, 'count': 1})] + list(((consumable_batch(s, [Record({'item': 'Feather', 'count': 1})], 200) if fish.tool == 'Fly fishing rod' else [])))
    budget = 0
    for need in needs:
        missing = max(0, need.count - stock_of(s, need.item))
        if not missing:
            continue
        if ((need.item.lower() in s.unavailable_items) if s.unavailable_items is not None else None):
            return False
        offer = supply_offer(need.item)
        if not offer:
            return False
        budget += purchase_budget(offer, missing)
    return budget == 0 or budget + 200 <= stock_of(s, 'Coins')

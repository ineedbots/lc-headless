"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/shopping.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['SHOPPING_RESERVE', 'audit_supplies', 'shopping_stops']

from rs2004.events import SKILL_NAMES
from bots.account_leveler.magic import magic_equipment
from bots.account_leveler.equipment import gathering_tool, melee_equipment, ranged_bow
from bots.account_leveler.offers import purchase_budget, supply_offer, supply_offers
from bots.account_leveler.types import requirement_key
SHOPPING_RESERVE = 200


def audit_supplies(s):
    _v1 = s.stock.get('coins')
    gold = max(0, (_v1 if _v1 is not None else 0))
    result = Record({'needs': [], 'budget': 0, 'reserve': min(gold, max(SHOPPING_RESERVE, (gold // 10))), 'skipped': []})
    if not s.bank_ready:
        _merged2 = {}
        for _k, _v in (result._fields if isinstance(result, Record) else result).items():
            _merged2[_k] = _v
        for _k, _v in {'skipped': ['Bank contents have not loaded']}.items():
            _merged2[_k] = _v
        return Record(_merged2)
    unfinished = set([skill for skill in SKILL_NAMES.values() if s.levels.get(skill, 0) > 0 and s.levels.get(skill) < s.target])

    def any_(*skills):
        return any([(skill in unfinished) for skill in skills])

    fly_fishing = s.levels.get('fishing', 0) >= 20 and (any_('fishing') or (any_('cooking') and s.levels.get('cooking', 0) >= 15))
    net_fishing = (any_('fishing') and s.levels.get('fishing', 0) < 20) or (any_('cooking') and (s.levels.get('fishing', 0) < 20 or s.levels.get('cooking', 0) < 15))

    def available():
        _merged3 = {}
        for _k, _v in (s.stock._fields if isinstance(s.stock, Record) else s.stock).items():
            _merged3[_k] = _v
        for _k, _v in {'coins': gold - result.reserve - result.budget + SHOPPING_RESERVE}.items():
            _merged3[_k] = _v
        _merged4 = {}
        for _k, _v in (s._fields if isinstance(s, Record) else s).items():
            _merged4[_k] = _v
        for _k, _v in {'stock': Record(_merged3)}.items():
            _merged4[_k] = _v
        return (Record(_merged4))

    def add(item, count=1, id=None):
        _merged5 = {}
        for _k, _v in {'item': item, 'count': count}.items():
            _merged5[_k] = _v
        for _k, _v in (((Record({}) if id is None else Record({'id': id})))._fields if isinstance(((Record({}) if id is None else Record({'id': id}))), Record) else ((Record({}) if id is None else Record({'id': id})))).items():
            _merged5[_k] = _v
        need = Record(_merged5)
        _v6 = s.stock.get(requirement_key(need).lower())
        owned = (_v6 if _v6 is not None else 0)
        if owned >= need.count:
            return
        if (any([item.lower() == need.item.lower() or item.lower() == requirement_key(need).lower() for item in s.unavailable_items]) if s.unavailable_items is not None else None):
            result.skipped.append(f'Unavailable: {need.item}')
            return
        offer = supply_offer(need.item)
        if not offer:
            result.skipped.append(f'No shop for {need.item}')
            return
        budget = purchase_budget(offer, need.count - owned)
        if result.budget + budget > gold - result.reserve:
            result.skipped.append(f'Cannot budget {need.count - owned} {need.item} ({budget} coins)')
            return
        result.needs.append(need)
        result.budget += budget

    def gear(need):
        return add(need.item, need.count, need.id)

    if any_('attack', 'strength', 'defence', 'hitpoints', 'prayer') or (any_('herblore') and not s.quests.get('Druidic Ritual')) or (any_('crafting') and s.levels.get('crafting') < 10):
        for need in melee_equipment(available()):
            gear(need)
    if any_('ranged'):
        gear(ranged_bow(available()))
    if any_('magic'):
        for need in magic_equipment(available()).needs:
            gear(need)
    if any_('woodcutting', 'firemaking', 'fletching'):
        gear(gathering_tool(available(), 'axe'))
    if any_('mining', 'smithing', 'runecraft'):
        pickaxe = gathering_tool(available(), 'pickaxe')
        if (s.levels.get('hitpoints', 99) < 25 or s.levels.get('defence', 99) < 20) and not s.stock.get(pickaxe.item.lower()) and (supply_offer(pickaxe.item).keeper if supply_offer(pickaxe.item) is not None else None) == 'Nurmof':
            result.skipped.append('Defer Nurmof until Hitpoints 25 and Defence 20; buy the pickaxe when mining starts')
        else:
            gear(pickaxe)
    if any_('firemaking'):
        add('Tinderbox')
    if any_('fletching'):
        add('Knife')
    if any_('smithing'):
        add('Hammer')
    if net_fishing:
        add('Small fishing net')
    if fly_fishing:
        add('Fly fishing rod')
    if any_('crafting') and s.levels.get('crafting') < 10:
        add('Needle')
    if any_('ranged') and s.levels.get('ranged') < 40:
        add('Bronze arrow', 1000)
    if fly_fishing:
        add('Feather', 1000)
    if any_('crafting') and s.levels.get('crafting') < 10:
        add('Thread', 100)
    if any_('herblore') and s.quests.get('Druidic Ritual'):
        add('Vial of water', 27)
        add('Eye of newt', 27)
    return result


def shopping_stops(needs, stock):
    stops = {}
    for need in needs:
        _v7 = stock.get(requirement_key(need).lower())
        if ((_v7 if _v7 is not None else 0)) >= need.count:
            continue
        for offer in supply_offers(need.item):
            _v8 = stops.get(offer.keeper)
            stop = (_v8 if _v8 is not None else Record({'keeper': offer.keeper, 'tile': offer.tile, 'needs': []}))
            stop.needs.append(need)
            stops[offer.keeper] = stop
    return list(list(stops.values()))

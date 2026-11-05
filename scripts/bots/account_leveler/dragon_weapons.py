"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/dragonWeapons.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['DRAGON_SHOP_COOLDOWN', 'zanaris_exit_needs', 'audit_dragon_weapons']

from bots.account_leveler.equipment import DRAGON_WEAPONS
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.shopping import SHOPPING_RESERVE
from bots.account_leveler.types import stock_of
DRAGON_SHOP_COOLDOWN = 'quest-zanaris-weapons'


def zanaris_exit_needs(s):
    if s.levels.get('magic') >= 25 and stock_of(s, 'Law rune') > 0:
        return [
            Record({'item': 'Law rune', 'count': 1}),
            Record({'item': 'Air rune', 'count': 3}),
            Record({'item': 'Fire rune', 'count': 1}),
        ]
    if stock_of(s, 'Diamond') > 0:
        return [Record({'item': 'Diamond', 'count': 1})]
    if s.levels.get('crafting') >= 43 and stock_of(s, 'Uncut diamond') > 0:
        return [Record({'item': 'Chisel', 'count': 1}), Record({'item': 'Uncut diamond', 'count': 1})]
    return None


def audit_dragon_weapons(s):
    gold = stock_of(s, 'Coins')
    result = Record({'needs': [], 'budget': 0, 'reserve': min(gold, max(SHOPPING_RESERVE, (gold // 10))), 'skipped': []})
    if not s.bank_ready or s.levels.get('attack') < 60 or not s.quests.get('Lost City'):
        return result
    missing = [item for item in DRAGON_WEAPONS if stock_of(s, item) == 0]
    if not len(missing):
        return result
    if not stock_of(s, 'Dramen staff'):
        _merged1 = {}
        for _k, _v in (result._fields if isinstance(result, Record) else result).items():
            _merged1[_k] = _v
        for _k, _v in {'skipped': ['Dragon weapons: need a Dramen staff for Zanaris']}.items():
            _merged1[_k] = _v
        return Record(_merged1)
    cut = not stock_of(s, 'Diamond') and s.levels.get('crafting') >= 43 and stock_of(s, 'Uncut diamond') > 0
    if not stock_of(s, 'Diamond') and not cut:
        _merged2 = {}
        for _k, _v in (result._fields if isinstance(result, Record) else result).items():
            _merged2[_k] = _v
        for _k, _v in {'skipped': ['Dragon weapons: need a Diamond, or Crafting 43 and an Uncut diamond, for the marketplace tax']}.items():
            _merged2[_k] = _v
        return Record(_merged2)
    for item in list(((['Chisel'] if cut and not stock_of(s, 'Chisel') else []))) + list(missing):
        if (any([unavailable.lower() == item.lower() for unavailable in s.unavailable_items]) if s.unavailable_items is not None else None):
            result.skipped.append(f'Dragon weapons: {item} supplier is cooling down')
            continue
        budget = purchase_budget(supply_offer(item), 1)
        if result.budget + budget > gold - result.reserve:
            result.skipped.append(f'Dragon weapons: cannot budget {item} ({budget} coins)')
            continue
        result.needs.append(Record({'item': item, 'count': 1}))
        result.budget += budget
    if not any([(need.item in DRAGON_WEAPONS) for need in result.needs]) or cut and not stock_of(s, 'Chisel') and not any([need.item == 'Chisel' for need in result.needs]):
        result.needs = []
        result.budget = 0
    return result

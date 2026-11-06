"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/magic.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import SPELL_DB
from bots.account_leveler.record import Record

__all__ = ['magic_equipment']

from bots.account_leveler.catalog import consumable_batch
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.types import stock_of
from bots.account_leveler.runes import can_steal_chaos

def magic_equipment(s):
    supply = s
    if can_steal_chaos(s):
        supply = Record(s._fields)
        supply.stock = Record(s.stock._fields if isinstance(s.stock, Record) else s.stock)
        supply.stock['chaos rune'] = max(200, stock_of(s, 'Chaos rune'))
    options = []
    for spell, fields in reversed(list(SPELL_DB.items())):
        row = Record(fields)
        if row.level > s.levels.get('magic') or ('Strike' not in spell and 'Bolt' not in spell):
            continue
        runes = consumable_batch(supply, [Record({'item': rune.rune, 'count': rune.count}) for rune in row.runes if rune.rune != 'Air rune'], 200, 150)
        needs = [Record({'item': 'Staff of air', 'count': 1, 'carry': 1, 'equip': True})] + runes
        budget = 0
        for need in needs:
            missing = max(0, need.count - stock_of(s, need.item))
            if missing <= 0 or need.item == 'Chaos rune' and can_steal_chaos(s):
                continue
            offer = supply_offer(need.item)
            if not offer or need.item.lower() in (s.unavailable_items or []):
                budget = float('inf')
                break
            budget += purchase_budget(offer, missing)
        options.append(Record({'spell': spell, 'needs': needs, 'casts': runes[0].carry // runes[0].minimum, 'budget': budget}))
    if can_steal_chaos(s):
        for option in options:
            if 'Bolt' in option.spell and option.budget + 200 <= stock_of(s, 'Coins'):
                return option
    for option in options:
        if option.budget == 0:
            return option
    for option in options:
        if option.budget + 200 <= stock_of(s, 'Coins'):
            return option
    for option in options:
        if option.spell == 'Wind Strike':
            return option
    raise RuntimeError('Magic level has not loaded')

"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/rangingGuild.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

__all__ = ['ranging_guild_plan']

from bots.rangingguild.logic import ARROW_RESTOCK_FEE, ENTRY_FEE, JUDGE_STAND, RANGED_REQUIRED
from bots.account_leveler.equipment import ranged_bow
from bots.account_leveler.offers import purchase_budget, supply_offer
from bots.account_leveler.shopping import SHOPPING_RESERVE
from bots.account_leveler.types import requirement_key, stock_of

def ranging_guild_plan(s, memory):
    if s.levels.get('ranged') < RANGED_REQUIRED or ((memory.cooldowns.get('ranging-guild') if memory.cooldowns.get('ranging-guild') is not None else 0)) > s.now:
        return None
    minimum = ENTRY_FEE + ARROW_RESTOCK_FEE + 2 * SHOPPING_RESERVE
    gold = stock_of(s, 'Coins')
    _merged1 = {}
    for _k, _v in (s.stock._fields if isinstance(s.stock, Record) else s.stock).items():
        _merged1[_k] = _v
    for _k, _v in {'coins': max(0, gold - minimum + SHOPPING_RESERVE)}.items():
        _merged1[_k] = _v
    _merged2 = {}
    for _k, _v in (s._fields if isinstance(s, Record) else s).items():
        _merged2[_k] = _v
    for _k, _v in {'stock': Record(_merged1)}.items():
        _merged2[_k] = _v
    bow = ranged_bow(Record(_merged2))
    owned = stock_of(s, requirement_key(bow)) > 0
    if not owned and (any([(item.lower() in [bow.item.lower(), requirement_key(bow)]) for item in s.unavailable_items]) if s.unavailable_items is not None else None):
        return None
    offer = supply_offer(bow.item)
    cost = (0 if owned else (purchase_budget(offer, 1) if offer else float('inf')))
    coins = min(10000, gold - cost)
    if coins < minimum:
        return None
    return Record({
        'id': 'ranging-guild',
        'label': 'Ranging Guild archery competition',
        'objective': 'ranged',
        'script': 'RangingGuild',
        'settings': Record({'coins_per_trip': coins, 'coins_reserve': SHOPPING_RESERVE}),
        'needs': [Record({'item': 'Coins', 'count': coins, 'carry': coins}), bow],
        'travel': JUDGE_STAND,
    })

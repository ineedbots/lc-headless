"""Shop prices and stock: the engine's price curve, stock coming back over ticks, and a buyout's plan. Ported
from rs2b0t's api/shop/BuyoutLogic.ts, StockModel.ts and shopPrice.ts (MIT, see thirdparty/rs2b0t). A shop
record is a `shop_db()` entry as a Record (`Record(shop_db()['magearena_runeshop'])`), or any object with its
fields."""

import math

from rs2004.catalogs.record import Record

TICK_MS = 600

# The shop_sell_multiplier and shop_delta a shopkeeper carries when its npc names neither.
SHOP_SELL_MULTIPLIER = 100
SHOP_DELTA = 10


def _field(value, key):
    return value[key] if isinstance(value, dict) else getattr(value, key)


def expected_stock(item, seen, now_ms):
    """How many of the item the shop has now, from what was `seen` (a count and `at_ms`) or None. Stock moves
    one towards the baseline every `restock_ticks`."""
    if not seen:
        return item.baseline
    steps = int(math.floor((now_ms - seen.at_ms) / TICK_MS / item.restock_ticks))
    if seen.count < item.baseline:
        return min(item.baseline, seen.count + steps)
    return max(item.baseline, seen.count - steps)


def unit_price(item, shop, stock):
    """What one costs with `stock` on the shelf, by the engine's formula; `shop` has `sell` and `delta`."""
    d = stock - item.baseline
    haggle = min(1000, max(-5000, d * _field(shop, 'delta')))
    pct = max(100, _field(shop, 'sell') - haggle)
    return max(1, (pct * item.cost) // 1000)


def units_under_policy(policy, stock, baseline):
    """How many to buy: all of it for a `'buyout'` policy, or down to `pct` percent of the baseline for a
    `'floor'` one."""
    if _field(policy, 'kind') == 'buyout':
        return max(0, stock)
    floor_count = math.ceil((_field(policy, 'pct') / 100) * baseline)
    return max(0, stock - floor_count)


def shop_buy_price(base_cost, bought, sell_multiplier=100, delta=10):
    """What the next one costs once `bought` have left the shelf.

    Why: the engine's calc_shop_value raises the price with every one bought, so a full shelf costs far more
    than stock times cost, and a trip funded on that arithmetic comes home with change and no goods."""
    swing = min(1000, max(-5000, -bought * delta))
    return max(1, (max(100, sell_multiplier - swing) * base_cost) // 1000)


def buyout_cost(base_cost, stock, sell_multiplier=100, delta=10):
    """Coins a full shelf costs, summed one at a time."""
    total = 0
    for bought in range(stock):
        total += shop_buy_price(base_cost, bought, sell_multiplier, delta)
    return total


def buyout_plan(rec, stock, coins, chosen):
    """What to buy of the shop's `chosen` items (lower-case names) with `coins`: the costliest first, each as many
    as its `stock` (by obj name) and the budget allow. Records with obj, name, units and est_cost."""
    wants = [i for i in rec.items if i.name.lower() in chosen and stock.get(i.obj, 0) > 0]
    wants.sort(key=lambda i: i.cost, reverse=True)
    left = coins
    plan = []
    for item in wants:
        have = stock.get(item.obj, 0)
        units = 0
        est_cost = 0
        while units < have:
            next_ = unit_price(item, rec, have - units)
            if est_cost + next_ > left:
                break
            est_cost += next_
            units += 1
        left -= est_cost
        if units > 0:
            plan.append(Record({'obj': item.obj, 'name': item.name, 'units': units, 'est_cost': est_cost}))
    return plan

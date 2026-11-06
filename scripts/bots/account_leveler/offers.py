"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/offers.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs import shop_db
from bots.account_leveler.record import Record

SHOP_DB = {key: Record(value) for key, value in shop_db().items()}

__all__ = ['supply_offers', 'supply_offer', 'purchase_budget']

vendors = [
    ['dragonswordshop', 'Jakut', 3252, 9572],
    ['scimitarshop', 'Zeke', 3288, 3190],
    ['axeshop', 'Bob', 3231, 3203],
    ['pickaxeshop', 'Nurmof', 2997, 9844],
    ['fishingshop', 'Gerrant', 3013, 3224],
    ['archeryshop', 'Lowe', 3231, 3421],
    ['runeshop', 'Aubury', 3253, 3401],
    ['generalshop1', 'Shop keeper', 3212, 3247],
    ['shantayshop', 'Shantay', 3304, 3123],
    ['magicshop', 'Betty', 3012, 3258],
    ['adventurershop', 'Aemad', 2613, 3294],
    ['legsshop', 'Louie legs', 3316, 3175],
    ['helmetshop', 'Peksa', 3076, 3429],
    ['armourshop', 'Horvik', 3229, 3438],
    ['craftingshop2', 'Dommik', 3316, 3192],
]
vial_vendors = [
    ['herbloreshop', 'Jatix', 2899, 3427],
    ['viking_general_store', 'Sigmund The Merchant', 2641, 3680],
    ['junglestore', 'Jiminua', 2767, 3122],
]


def supply_offers(name):


    if name.lower().endswith(' rune') or name.lower().endswith(' arrow'):
        sources = [(key, _2, _3, _4) for key, _2, _3, _4 in vendors if (key in ['runeshop', 'magicshop', 'archeryshop'])]
        return shop_offers(name, list(sources) + [['archeryshop2', 'Hickton', 2821, 3442]])
    water = name.lower() == 'vial of water'
    if not water and name.lower() != 'vial':
        offer = primary_offer(name)
        return ([offer] if offer else [])
    offers = []
    if water:
        offers.append(primary_offer('Vial of water'))
    for key, keeper, x, z in vial_vendors:
        shop = SHOP_DB.get(key)
        fill_vials = water and keeper == 'Jatix'
        item = ([item for item in shop.items if item.name == (('Vial of water' if water and not fill_vials else 'Vial'))] or [None])[0]
        offers.append(Record({
            'keeper': keeper,
            'tile': Record({'x': x, 'z': z, 'level': 0}),
            'item': item,
            'shop': shop,
            'fill_vials': fill_vials,
        }))
    return offers


def supply_offer(name):
    _v2 = (supply_offers(name) or [None])[0]
    return (_v2 if _v2 is not None else None)


def primary_offer(name):
    if name == 'Staff of air':
        return Record({
            'keeper': 'Zaff',
            'tile': Record({'x': 3203, 'z': 3433, 'level': 0}),
            'shop': Record({'sell': 1000, 'delta': 20}),
            'item': Record({
            'obj': 'staff_of_air',
            'name': name,
            'baseline': 2,
            'restock_ticks': 1000,
            'cost': 1500,
            'stackable': False,
            'members': False,
        }),
        })
    _v3 = (shop_offers(name) or [None])[0]
    return (_v3 if _v3 is not None else None)


def shop_offers(name, sources=None):
    if sources is None:
        sources = vendors

    def _fn8(_arg9):
        key, keeper, x, z = _arg9
        shop = SHOP_DB.get(key)
        item = ([i for i in (shop.items if shop is not None else None) if i.name.lower() == name.lower() and i.baseline > 0] or [None])[0]
        return ([Record({'keeper': keeper, 'tile': Record({'x': x, 'z': z, 'level': 0}), 'item': item, 'shop': shop})] if item else [])
    _flat10 = []
    for _x in sources:
        _flat10.extend(_fn8(_x))
    return _flat10


def purchase_budget(offer, count):
    if offer.keeper == 'Jakut':
        from rs2004.catalogs.shops import unit_price
        return math.ceil(max(1, count) * unit_price(offer.item, offer.shop, 1))
    return math.ceil(max(1, count) * offer.item.cost * (offer.shop.sell + 5000) / 1000)

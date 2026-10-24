"""rs2b0t's test/api/shop/stockmodel.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, TICK_MS, expected_stock, unit_price, units_under_policy


death = Record({
    'obj': 'deathrune',
    'name': 'Death rune',
    'baseline': 1000,
    'restock_ticks': 150,
    'cost': 30,
    'stackable': True,
    'members': False,
})
fire = Record({
    'obj': 'firerune',
    'name': 'Fire rune',
    'baseline': 2000,
    'restock_ticks': 10,
    'cost': 4,
    'stackable': True,
    'members': False,
})
SHOP = Record({'sell': 1000, 'delta': 10})


def _fn1():
    def _fn2():
        expect(expected_stock(death, None, 0)).to_be(1000)
    test('never seen → assume baseline (first lap visits everything)', _fn2)

    def _fn3():
        seen = Record({'count': 0, 'at_ms': 0})
        expect(expected_stock(death, seen, 150 * TICK_MS)).to_be(1)
        expect(expected_stock(death, seen, 149 * TICK_MS)).to_be(0)
        expect(expected_stock(death, seen, 10 * 150 * TICK_MS)).to_be(10)
        expect(expected_stock(death, seen, 100000 * 150 * TICK_MS)).to_be(1000)
    test('restocks +1 per restockTicks ticks, capped at baseline', _fn3)

    def _fn4():
        seen = Record({'count': 1010, 'at_ms': 0})
        expect(expected_stock(death, seen, 150 * TICK_MS * 3)).to_be(1007)
        expect(expected_stock(death, seen, 150 * TICK_MS * 100)).to_be(1000)
    test('overstock decays toward baseline at the same rate', _fn4)


describe('expectedStock', _fn1)


def _fn5():
    def _fn6():
        expect(unit_price(fire, SHOP, 2000)).to_be(4)
        expect(unit_price(death, SHOP, 1000)).to_be(30)
    test('at baseline pays 100%: fire rune = 4gp, death rune = 30gp', _fn6)

    def _fn7():
        expect(unit_price(death, SHOP, 900)).to_be(60)
    test('price rises ~1%/unit below baseline: death at −100 → 2× = 60gp', _fn7)

    def _fn8():
        expect(unit_price(death, SHOP, 500)).to_be(180)
        expect(unit_price(death, SHOP, 1)).to_be(180)
    test('caps at 6× from −500 down (clamp −5000)', _fn8)

    def _fn9():
        expect(unit_price(death, SHOP, 100000)).to_be(3)
        expect(unit_price(fire, SHOP, 100000)).to_be(1)
    test('overstock floors at 10% (pct min 100), price min 1gp', _fn9)


describe('unitPrice (engine formula)', _fn5)


def _fn10():
    def _fn11():
        expect(units_under_policy(Record({'kind': 'buyout'}), 700, 1000)).to_be(700)
    test('buyout takes everything', _fn11)

    def _fn12():
        expect(units_under_policy(Record({'kind': 'floor', 'pct': 50}), 1000, 1000)).to_be(500)
        expect(units_under_policy(Record({'kind': 'floor', 'pct': 50}), 400, 1000)).to_be(0)
        expect(units_under_policy(Record({'kind': 'floor', 'pct': 33}), 1000, 1000)).to_be(670)
    test('floor 50% buys down to ceil(50% of baseline)', _fn12)


describe('unitsUnderPolicy', _fn10)


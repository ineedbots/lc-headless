"""rs2b0t's test/api/shop/shopPrice.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record, buyout_cost, shop_buy_price


# Why: `calc_shop_value` raises the price with every one bought, so a shelf costs far more than stock times cost and a trip funded on that arithmetic comes home with change and no goods.
ROACHEY = Record({'sell': 1000, 'delta': 10, 'stock': 1500})
FERNAHEI = Record({'sell': 1000, 'delta': 20, 'stock': 800})
FEATHER = 2


def _fn1():
    def _fn2():
        expect(shop_buy_price(FEATHER, 0, ROACHEY.sell, ROACHEY.delta)).to_be(2)
        expect(shop_buy_price(FEATHER, 0, FERNAHEI.sell, FERNAHEI.delta)).to_be(2)
    test('the first one off a full shelf is the price the shop lists', _fn2)

    def _fn3():
        expect(shop_buy_price(FEATHER, 50, ROACHEY.sell, ROACHEY.delta)).to_be(3)
        expect(shop_buy_price(FEATHER, 250, ROACHEY.sell, ROACHEY.delta)).to_be(7)
        expect(shop_buy_price(FEATHER, 25, FERNAHEI.sell, FERNAHEI.delta)).to_be(3)
        expect(shop_buy_price(FEATHER, 125, FERNAHEI.sell, FERNAHEI.delta)).to_be(7)
    test('it climbs with the delta, a gp per fifty at ten and per twenty-five at twenty', _fn3)

    def _fn4():
        expect(shop_buy_price(FEATHER, 500, ROACHEY.sell, ROACHEY.delta)).to_be(12)
        expect(shop_buy_price(FEATHER, 1499, ROACHEY.sell, ROACHEY.delta)).to_be(12)
        expect(shop_buy_price(FEATHER, 250, FERNAHEI.sell, FERNAHEI.delta)).to_be(12)
    test('and stops at twelve, where the engine clamps the swing at -5000', _fn4)

    def _fn5():
        expect(shop_buy_price(0, 0)).to_be(1)
    test('never asks less than a gp, whatever the base cost', _fn5)

    def _fn6():
        expect(buyout_cost(FEATHER, ROACHEY.stock, ROACHEY.sell, ROACHEY.delta)).to_be(15250)
    test("Roachey's 1500 feathers run to 15,250gp", _fn6)

    def _fn7():
        expect(buyout_cost(FEATHER, FERNAHEI.stock, FERNAHEI.sell, FERNAHEI.delta)).to_be(8225)
    test("Fernahei's 800 run to 8,225gp, since his delta is twice Roachey's", _fn7)

    # Why: this is the run that bought 571 on 4,000gp seeded, which is what pins the curve to the live engine rather than to a reading of the script.
    def _fn8():
        expect(buyout_cost(FEATHER, 571, ROACHEY.sell, ROACHEY.delta)).to_be(4102)
    test('571 of Roachey cost 4,102gp', _fn8)

    def _fn9():
        expect(buyout_cost(FEATHER, 0, ROACHEY.sell, ROACHEY.delta)).to_be(0)
    test('an empty shelf costs nothing', _fn9)


describe('the engine price curve', _fn1)


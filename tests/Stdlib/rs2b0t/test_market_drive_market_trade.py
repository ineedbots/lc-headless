"""rs2b0t's test/api/market/driveMarketTrade.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.market import offer_covers, offers_match


def side(entries):
    return {_k: _v for _k, _v in entries}


COINS = 995
IRON = 440
JUNK = 1127


def _fn1():
    def _fn2():
        expect(offers_match(side([[IRON, 100]]), side([[IRON, 100]]))).to_be(True)
        expect(offers_match(side([[IRON, 99]]), side([[IRON, 100]]))).to_be(False)
        expect(offers_match(side([[IRON, 100], [JUNK, 1]]), side([[IRON, 100]]))).to_be(False)
    test('exact by id and count, with nothing extra', _fn2)


describe('offersMatch', _fn1)


def _fn3():
    # Why: require the shop's exact offer while allowing customer extras and rounded payment.
    def _fn4():
        expect(offer_covers(side([[COINS, 2200]]), side([[COINS, 2200]]))).to_be(True)
    test('the exact deal is covered', _fn4)

    def _fn5():
        expect(offer_covers(side([[COINS, 5000]]), side([[COINS, 2200]]))).to_be(True)
    test('more than the deal is still the deal', _fn5)

    def _fn6():
        expect(offer_covers(side([[COINS, 2199]]), side([[COINS, 2200]]))).to_be(False)
    test('short of the deal is not the deal', _fn6)

    def _fn7():
        expect(offer_covers(side([[COINS, 2200], [JUNK, 1]]), side([[COINS, 2200]]))).to_be(True)
    test('something else in the window does not stop it settling', _fn7)

    def _fn8():
        expect(offer_covers(side([[JUNK, 99]]), side([[COINS, 2200]]))).to_be(False)
        expect(offer_covers(side([]), side([[COINS, 1]]))).to_be(False)
    test('a missing id is never covered, however much else is up', _fn8)

    # Why: nothing wanted is not a deal to accept, it is a window with nothing agreed in it.
    def _fn9():
        expect(offer_covers(side([[COINS, 5000]]), side([]))).to_be(False)
    test('wanting nothing is not covered by anything', _fn9)


describe('offerCovers', _fn3)


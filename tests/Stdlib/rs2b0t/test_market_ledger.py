"""rs2b0t's test/api/market/ledger.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import Ledger


IRON = 440
YEW = 1515
ledger = None


def _fn1():
    global ledger
    ledger = Ledger()
    ledger.set_stock([Record({'id': IRON, 'count': 1000}), Record({'id': YEW, 'count': 12})])


before_each(_fn1)


def _fn2():
    def _fn3():
        expect(ledger.held(IRON)).to_be(1000)
        expect(ledger.held(9999)).to_be(0)
    test('held comes from the last read', _fn3)

    def _fn4():
        ledger.set_stock([Record({'id': IRON, 'count': 5}), Record({'id': IRON, 'count': 7})])
        expect(ledger.held(IRON)).to_be(12)
    test('setStock sums duplicate ids', _fn4)

    def _fn5():
        ledger.set_stock([Record({'id': IRON, 'count': 5})])
        expect(ledger.held(YEW)).to_be(0)
    test('setStock replaces rather than merges', _fn5)


describe('what the bank held at the last look', _fn2)


def _fn6():
    # Why: the per-item cap has to mean something before the next time the bank is opened.
    def _fn7():
        ledger.add(IRON, 50)
        expect(ledger.held(IRON)).to_be(1050)
        ledger.add(IRON, -100)
        expect(ledger.held(IRON)).to_be(950)
    test('buying raises the count and selling lowers it', _fn7)

    def _fn8():
        ledger.add(YEW, -999)
        expect(ledger.held(YEW)).to_be(0)
    test('it never goes below zero', _fn8)

    def _fn9():
        ledger.add(9999, 5)
        expect(ledger.held(9999)).to_be(5)
    test('an unknown id starts from nothing', _fn9)


describe('trades move it between bank trips', _fn6)


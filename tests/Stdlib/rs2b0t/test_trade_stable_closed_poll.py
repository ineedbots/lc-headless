"""rs2b0t's test/api/trade/StableClosedPoll.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import stable_closed_poll
from rs2004.trade import trade


def open_trade_never_closes():
    spy_on(trade, 'active', returns=True)
    clock = [1000]
    poll = stable_closed_poll(600, lambda: clock[0])
    expect(poll()).to_be(False)
    clock[0] = 3000
    expect(poll()).to_be(False)


test('returns false while the trade screen remains active', open_trade_never_closes)


def reopening_resets_timer():
    active = [False]
    clock = [1000]
    spy_on(trade, 'active', impl=lambda: active[0])
    poll = stable_closed_poll(600, lambda: clock[0])
    expect(poll()).to_be(False)
    clock[0] = 1300
    expect(poll()).to_be(False)
    active[0] = True
    expect(poll()).to_be(False)
    active[0] = False
    clock[0] = 1600
    expect(poll()).to_be(False)
    clock[0] = 2200
    expect(poll()).to_be(True)


test('reopening a trade resets the sustained closure timer', reopening_resets_timer)


def _fn1():
    def _fn4():
        clock = [1000]
        poll = stable_closed_poll(600, lambda: clock[0])
        expect(poll()).to_be(False)
        clock[0] = 1500
        expect(poll()).to_be(False)
    test('returns false when inactive time is less than minMs', _fn4)

    def _fn5():
        clock = [1000]
        poll = stable_closed_poll(600, lambda: clock[0])
        expect(poll()).to_be(False)
        clock[0] = 1600
        expect(poll()).to_be(True)
    test('returns true when inactive time reaches minMs', _fn5)

    def _fn7():
        clock = [1000]
        poll = stable_closed_poll(600, lambda: clock[0])
        expect(poll()).to_be(False)
        clock[0] = 1599
        expect(poll()).to_be(False)
        clock[0] = 1600
        expect(poll()).to_be(True)
    test('edge case: exactly at minMs boundary', _fn7)


describe('stableClosedPoll', _fn1)

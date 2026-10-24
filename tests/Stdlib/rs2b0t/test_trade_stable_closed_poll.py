"""rs2b0t's test/api/trade/StableClosedPoll.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. Its cases with a trade open stub Trade.active, which pocketpy can't (a method set on an instance does
nothing), so only those with none open are here; with no game, trade.active() is False."""

from rs2004.catalogs import stable_closed_poll


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

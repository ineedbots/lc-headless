"""Ported from rs2b0t's test/api/ai/quests/upassSeamRank.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.upass.rank import order_seams, seam_bucket

# Why: reachable seams must beat closer-looking seams across sealed pocket walls.
def seam(gains, open, dist):
    return (Record({'gains': gains, 'open': open, 'dist': dist}))


def order(*seams):
    return [s.dist for s in order_seams(seams, lambda s: s, lambda s: s.dist)]


def _fn1():
    def _fn2():
        expect(seam_bucket(Record({'gains': True, 'open': True}))).to_be(0)
    test('takes one that gains and this pocket can reach', _fn2)

    def _fn3():
        expect(seam_bucket(Record({'gains': False, 'open': True}))).to_be(1)
    test('then one this pocket can reach that gains nothing', _fn3)

    def _fn4():
        expect(seam_bucket(Record({'gains': True, 'open': False}))).to_be(2)
        expect(seam_bucket(Record({'gains': False, 'open': False}))).to_be(3)
    test('then one that gains behind a wall, and last one that does neither', _fn4)

    def _fn5():
        # The reachable ledge has less apparent gain than seven walled bridges.
        expect(order(seam(True, False, 21), seam(False, True, 36), seam(True, False, 25))).to_equal([36, 21, 25])
    test('puts the ledge under the character ahead of every walled bridge', _fn5)

    def _fn6():
        expect(order(seam(False, True, 36), seam(True, True, 21))).to_equal([21, 36])
    test('and behind one that both gains and is reachable', _fn6)

    def _fn7():
        expect(order(seam(True, True, 30), seam(True, True, 12), seam(True, True, 21))).to_equal([12, 21, 30])
    test('breaks a tie inside a bucket on distance to the target', _fn7)


describe('which seam the search tries first', _fn1)


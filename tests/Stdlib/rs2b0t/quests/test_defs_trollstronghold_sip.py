"""Ported from rs2b0t's test/api/ai/quests/defs/trollstrongholdSip.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.trollstronghold.combat import needs_sip

def _fn1():
    def _fn2():
        expect(needs_sip(34, 70)).to_be(True)
    test('sips below half the bar', _fn2)

    def _fn3():
        expect(needs_sip(35, 70)).to_be(False)
    test('leaves a bar at half alone', _fn3)

    def _fn4():
        expect(needs_sip(70, 70)).to_be(False)
    test('leaves a full bar alone', _fn4)

    def _fn5():
        expect(needs_sip(0, 70)).to_be(True)
    test('sips at empty', _fn5)

    def _fn6():
        expect(needs_sip(0, 0)).to_be(False)
    test('a character with no prayer levels never sips', _fn6)


describe('needsSip', _fn1)

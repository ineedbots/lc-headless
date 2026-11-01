"""Ported from rs2b0t's test/api/ai/quests/defs/holygrail-titan.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.holygrail.legs import PROTECT_LEVEL, should_protect

def _fn1():
    def _fn2():
        expect(should_protect(PROTECT_LEVEL, 43, False)).to_be(True)
    test('arms melee protection at the prayer level that unlocks it', _fn2)

    def _fn3():
        expect(should_protect(PROTECT_LEVEL - 1, 42, False)).to_be(False)
    test('a character below the level never arms it', _fn3)

    def _fn4():
        expect(should_protect(70, 0, False)).to_be(False)
    test('an empty prayer bar spends no tick on the button', _fn4)

    def _fn5():
        expect(should_protect(70, 70, True)).to_be(False)
    test('a prayer already up is left alone', _fn5)

    def _fn6():
        expect(should_protect(0, 0, False)).to_be(False)
    test('a character with no prayer levels never arms it', _fn6)


describe('shouldProtect', _fn1)

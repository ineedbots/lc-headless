"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fightarena-legs.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.fightarena.areas import FA_OBJ
from rs2004.quests.defs.fightarena.legs import combat_swap

RUNE_FULL_HELM = 1163
RUNE_CHAINBODY = 1113
LOBSTER = 379


def _fn1():
    def _fn2():
        expect(combat_swap([LOBSTER, RUNE_CHAINBODY, RUNE_FULL_HELM])).to_equal([RUNE_FULL_HELM, RUNE_CHAINBODY])
    test('picks the pack hat and torso, hat first', _fn2)

    def _fn3():
        expect(combat_swap([FA_OBJ.HELMET, FA_OBJ.ARMOUR])).to_equal([])
    test('never picks the Khazard pieces back up', _fn3)

    def _fn4():
        expect(combat_swap([])).to_equal([])
    test('an empty pack swaps nothing', _fn4)

    def _fn5():
        expect(combat_swap([FA_OBJ.HELMET, RUNE_CHAINBODY])).to_equal([RUNE_CHAINBODY])
    test('a pack with only a body still swaps the body', _fn5)


describe('combatSwap', _fn1)

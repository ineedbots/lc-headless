"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fightarena-fights.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.fightarena.areas import FA_NPC
from rs2004.quests.defs.fightarena.fights import FA_FIGHT, fight_won

def _fn1():
    def _fn2():
        expect(FA_FIGHT.ogre.npc_id).to_be(FA_NPC.OGRE)
        expect(FA_FIGHT.scorpion.npc_id).to_be(FA_NPC.SCORPION)
        expect(FA_FIGHT.bouncer.npc_id).to_be(FA_NPC.BOUNCER)
    test('each fight names the npc id the server spawns', _fn2)

    def _fn3():
        expect(FA_FIGHT.bouncer.guard).to_be_greater_than(FA_FIGHT.scorpion.guard)
        expect(FA_FIGHT.bouncer.guard).to_be_greater_than(FA_FIGHT.ogre.guard)
    test('Bouncer gets the longest guard — 116 hitpoints behind 120 defence', _fn3)


describe('the arena fights', _fn1)


def _fn4():
    def _fn5():
        expect(fight_won(0, 99)).to_be(False)
    test('an empty scene before the first swing is not a win', _fn5)

    def _fn6():
        expect(fight_won(4, 1)).to_be(False)
    test('one missing tick after a swing is not a win', _fn6)

    def _fn7():
        expect(fight_won(4, 3)).to_be(True)
    test('three missing ticks after a swing is a win', _fn7)


describe('fightWon', _fn4)

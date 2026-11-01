"""Ported from rs2b0t's test/api/ai/quests/defs/horrorMelee.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.horror.fight import FORM_ELEMENT, IMMUNE_FORMS, MELEE_FORM, MOTHER_IDS, RANGED_FORM

# `npc.dat` runs the block contiguously from horror_dagannoth_jr4 (1347): aira/airb/airc/air, water, fire, earth, ranged, melee.
# Why: swapping the last two swings a scimitar at the ranged-only form, with no message and no damage.
def _fn1():
    def _fn2():
        expect(MELEE_FORM).to_be(1356)
        expect(RANGED_FORM).to_be(1355)
    test('the melee-weak form is 1356, the ranged-weak form 1355', _fn2)

    def _fn3():
        expect((MELEE_FORM in IMMUNE_FORMS)).to_be(True)
        expect((RANGED_FORM in IMMUNE_FORMS)).to_be(True)
        expect(FORM_ELEMENT.get(MELEE_FORM)).to_be_undefined()
        expect(FORM_ELEMENT.get(RANGED_FORM)).to_be_undefined()
    test('neither of the two takes damage from any spell', _fn3)

    def _fn4():
        expect(MOTHER_IDS).to_contain(MELEE_FORM)
        expect(MOTHER_IDS).to_contain(RANGED_FORM)
    test('both are still forms the fight expects to meet', _fn4)

    def _fn5():
        # These four are what cross-validate the 104 offset against npc.dat:
        # water/fire/earth land where the pack orders them.
        expect(FORM_ELEMENT.get(1352)).to_be('Water')
        expect(FORM_ELEMENT.get(1353)).to_be('Fire')
        expect(FORM_ELEMENT.get(1354)).to_be('Earth')
        expect(FORM_ELEMENT.get(1351)).to_be('Wind')
    test('the elemental forms keep their spells — the block alignment depends on it', _fn5)

    def _fn6():
        for id in MOTHER_IDS:
            has_spell = FORM_ELEMENT.get(id) is not None
            expect(has_spell).to_be(not (id in IMMUNE_FORMS))
    test('every non-immune form has a spell, and no form has both', _fn6)


describe('Dagannoth mother forms', _fn1)

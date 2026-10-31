"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/dwarfcannon-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.dwarfcannon.journal import MC_FLAG, MC_STAGE, parse_dwarf_cannon_journal

INTRO = '@str@I have spoken to the Commander, he recruited me|@str@into the Black Guard and asked me to help the dwarves.||'


def _fn1():
    def _fn2():
        text = '@dbl@I can start this quest by speaking to the @dre@Commander of the Black Watch@dbl@. He is defending an area @dre@north-west of the Fishing Guild@dbl@ against @dre@goblin@dbl@ attack.|'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.NOT_STARTED)
    test('not started', _fn2)

    def _fn3():
        text = INTRO + '@dbl@My first task is to @dre@fix the broken railings@dbl@ in the dwarves defensive perimeter.'
        progress = parse_dwarf_cannon_journal(text)
        expect(progress.stage).to_be(MC_STAGE.RAILINGS)
        expect((MC_FLAG.RAILINGS_DONE in progress.flags)).to_be(False)
    test('railings outstanding', _fn3)

    def _fn4():
        text = INTRO + '@str@I have repaired all the broken railings,|@dbl@I should report back to the Commander.'
        progress = parse_dwarf_cannon_journal(text)
        expect(progress.stage).to_be(MC_STAGE.RAILINGS)
        expect((MC_FLAG.RAILINGS_DONE in progress.flags)).to_be(True)
    test('railings all fixed still reads stage 1, with the flag', _fn4)

    def _fn5():
        text = INTRO + '@str@I have repaired all the broken railings,|@dbl@The Commander has asked me to check up on his guards at @dre@the watchtower@dbl@ to the South of his camp.'
        progress = parse_dwarf_cannon_journal(text)
        expect(progress.stage).to_be(MC_STAGE.GUARD_TOWER)
        expect((MC_FLAG.HAS_REMAINS in progress.flags)).to_be(False)
    test('guard tower outranks the railings line it also carries', _fn5)

    def _fn6():
        text = INTRO + '@str@I went to the watchtower where I found some dwarf|@str@remains.|@dbl@I should take them back to @dre@the Commander@dbl@.'
        progress = parse_dwarf_cannon_journal(text)
        expect(progress.stage).to_be(MC_STAGE.GUARD_TOWER)
        expect((MC_FLAG.HAS_REMAINS in progress.flags)).to_be(True)
    test('remains in the pack', _fn6)

    def _fn7():
        text = INTRO + '@str@I gave the remains to the Commander.|@dbl@He sent me to find the @dre@Goblin base@dbl@.'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.GOBLIN_CAVE)
    test('goblin cave', _fn7)

    def _fn8():
        text = INTRO + "@str@I found the Goblin's base.|@dbl@Next I need to find the @dre@Dwarf child@dbl@."
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.FIND_CHILD)
    test('find the child', _fn8)

    def _fn9():
        text = INTRO + '@str@I have rescued the dwarf child and sent him back to the|@str@Commander.|@dbl@I need to @dre@speak to the Commander@dbl@ again.'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.CHILD_RESCUED)
    test('child rescued', _fn9)

    def _fn10():
        text = INTRO + '@dbl@The Commander has asked me to @dre@fix the multicannon@dbl@.'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.FIX_CANNON)
    test('stages 6 and 7 are one branch', _fn10)

    def _fn11():
        text = INTRO + "@str@I've fixed the broken multicannon,|@dbl@I need to @dre@speak to the Commander@dbl@ again."
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.CANNON_FIXED)
    test('cannon repaired', _fn11)

    def _fn12():
        text = INTRO + '@dbl@The Commander asked me to find @dre@Nulodion the Cannon Engineer@dbl@, he needs to know what @dre@ammunition the multicannon@dbl@ fires.'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.SEE_NULODION)
    test('sent to Nulodion', _fn12)

    def _fn13():
        text = INTRO + "@str@I've spoken to Nulodion,|@str@He gave me an ammo mould and notes,|@dbl@I need to @dre@speak to the Commander@dbl@ again."
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.RETURN_NOTES)
    test('carrying the mould and notes back', _fn13)

    def _fn14():
        text = INTRO + '@str@I fixed the cannon and got a mould for the Commander.|@dbl@I can now @dre@buy a multicannon@dbl@ from @dre@Nulodion@dbl@ as a reward.||@red@QUEST COMPLETE!'
        expect((parse_dwarf_cannon_journal(text).stage if parse_dwarf_cannon_journal(text) is not None else None)).to_be(MC_STAGE.COMPLETE)
    test('complete', _fn14)

    def _fn15():
        expect(parse_dwarf_cannon_journal('nothing here')).to_be_undefined()
    test('unrecognised text is undefined', _fn15)


describe('parseDwarfCannonJournal', _fn1)

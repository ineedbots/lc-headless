"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-journal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE, parse_prince_journal
INTRO = '@str@Prince Ali has been kidnapped but luckily the spy Leela|@str@has found he is being held near draynor village. I will|' + '@str@need to disguise the Prince and tie up his captor to free|@str@him from their clutches.|'
DRUNK = '@str@I also had to prevent the Guard from seeing what I was up|@str@to, by getting him drunk.|'
TIED = '@str@With the guard disposed of, I used my rope to tie up Lady|@str@Keli in a cupboard, so I could disguise the Prince.|'
SAVED = '@str@I then used a wig, a skirt and some skin paste to make the|@str@prince look like Lady Keli so he could escape to his|' + '@str@freedom with Leela after unlocking his cell door.|'
JOURNAL = {PRINCE_STAGE.NOT_STARTED: '@dbl@I can start this quest by speaking to @dre@Hassan@dbl@ in @dre@Al-Kharid Palace@dbl@.', PRINCE_STAGE.STARTED: '@str@I started this quest by speaking to Hassan in Al-Kharid|@str@Palace. He told me I should speak to Osman the spy master.|' + '@dbl@I should go and speak to @dre@Osman@dbl@ for details on the quest.', PRINCE_STAGE.SPOKEN_OSMAN: '@str@Prince Ali has been kidnapped but luckily the spy Leela|@str@has found he is being held near draynor village. I will|' + '@str@need to disguise the Prince and tie up his captor to free|@str@him from their clutches. To do this I should:||' + '@dbl@Talk to @dre@Leela@dbl@ near @dre@Draynor Village@dbl@ for advice|' + '@dbl@Get a duplicate of the key that is imprisoning the prince|' + "@dbl@Get some rope to tie up the Princes' kidnapper|", PRINCE_STAGE.PREP_FINISHED: INTRO + '@dbl@Before I can free @dre@Prince Ali@dbl@, I need to deal with the @dre@Guard@dbl@.|' + '@dre@Leela@dbl@ suggested I speak with the @dre@Guard@dbl@ to try and determine any weaknesses he might have.|', PRINCE_STAGE.GUARD_DRUNK: INTRO + DRUNK + '@dbl@The last thing I need to do is deal with @dre@Lady Keli@dbl@.|@dre@Leela@dbl@ suggested I use some @dre@Rope@dbl@ to tie her up.', PRINCE_STAGE.TIED_KELI: INTRO + DRUNK + TIED + "@dbl@I can now free @dre@Prince Ali@dbl@. I'll need to make sure I give him his disguise when I do.", PRINCE_STAGE.SAVED: INTRO + DRUNK + TIED + SAVED + '@dbl@I should return to @dre@Hassan@dbl@ to claim my reward.', PRINCE_STAGE.COMPLETE: '@str@I started this quest by speaking to Hassan in Al-Kharid|@str@Palace. He told me I should speak to Osman the spy master.|' + '@str@I should go and speak to Osman for details on the quest.|' + INTRO + DRUNK + TIED + SAVED + '@str@I returned to Al-Kharid where Hassan rewarded me for|@str@my work.||@red@QUEST COMPLETE!'}

def _fn1():
    for stage, text in JOURNAL.items():

        def _make__fn2(stage, text):
            def _fn2():
                expect(parse_prince_journal(text).stage if parse_prince_journal(text) is not None else None).to_be(float(stage))
            return _fn2
        test(f'stage {stage} reads back as itself', _make__fn2(stage, text))

    def _fn3():
        expect(parse_prince_journal(JOURNAL[PRINCE_STAGE.TIED_KELI]).stage if parse_prince_journal(JOURNAL[PRINCE_STAGE.TIED_KELI]) is not None else None).to_be(PRINCE_STAGE.TIED_KELI)
        expect(parse_prince_journal(JOURNAL[PRINCE_STAGE.SAVED]).stage if parse_prince_journal(JOURNAL[PRINCE_STAGE.SAVED]) is not None else None).to_be(PRINCE_STAGE.SAVED)
        expect(parse_prince_journal(JOURNAL[PRINCE_STAGE.COMPLETE]).stage if parse_prince_journal(JOURNAL[PRINCE_STAGE.COMPLETE]) is not None else None).to_be(PRINCE_STAGE.COMPLETE)
    test('later entries keep the earlier history, so needles must be newest-first', _fn3)

    def _fn4():
        expect(JOURNAL[PRINCE_STAGE.PREP_FINISHED]).not_.to_contain('for advice')
    test('"for advice" is unique to stage 20 and does not leak into 30', _fn4)

    def _fn5():
        expect(parse_prince_journal(JOURNAL[PRINCE_STAGE.GUARD_DRUNK]).stage if parse_prince_journal(JOURNAL[PRINCE_STAGE.GUARD_DRUNK]) is not None else None).to_be(PRINCE_STAGE.GUARD_DRUNK)
    test('stage 40\'s "need to do is deal with" is not stage 30\'s "need to deal with the"', _fn5)

    def _fn6():
        expect(parse_prince_journal(['@red@QUEST', 'COMPLETE!']).stage if parse_prince_journal(['@red@QUEST', 'COMPLETE!']) is not None else None).to_be(PRINCE_STAGE.COMPLETE)
    test('an array of lines parses the same as the joined string', _fn6)

    def _fn7():
        expect(parse_prince_journal([])).to_be_undefined()
        expect(parse_prince_journal('')).to_be_undefined()
    test('an empty journal is undefined, not stage 0', _fn7)

    def _fn8():
        expect(parse_prince_journal('@str@Some other quest entirely.')).to_be_undefined()
    test('unrecognised text is undefined', _fn8)

    def _fn9():
        expect(len(parse_prince_journal(JOURNAL[PRINCE_STAGE.SPOKEN_OSMAN]).flags if parse_prince_journal(JOURNAL[PRINCE_STAGE.SPOKEN_OSMAN]) is not None else None)).to_be(0)
    test('flags are always empty — the stage carries everything', _fn9)
describe('prince journal', _fn1)

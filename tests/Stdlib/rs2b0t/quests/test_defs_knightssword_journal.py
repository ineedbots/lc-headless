"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/knightssword-journal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.knightssword.areas import KS_STAGE
from rs2004.quests.defs.knightssword.journal import parse_knights_sword_journal
HELPED = '@str@I told the Squire I would help him to replace the sword he had|' + '@str@lost. It could only be made by an Imcando dwarf.|'
FOUND_THURGO = '@str@I found an Imcando dwarf named Thurgo thanks to|' + "@str@information provided by Reldo. He wasn't very talkative|" + '@str@until I gave him a Redberry pie, which he gobbled up.|'
TOOK_PORTRAIT = '@str@Turgo needed a picture of the sword before he could start|' + '@str@work on a replacement. I took him a portrait of it.|'
NOT_STARTED = '@dbl@I can start this quest by talking to the @dre@Squire @dbl@in the|' + "@dbl@courtyard of the @dre@White Knights' Castle@dbl@.|" + '@str@I have a mining level of 10|' + '@dbl@I would have an advantage if I had a combat level of @dre@20.'
STARTED = HELPED + '@dbl@The Squire suggests I speak to @dre@Reldo @dbl@in the @dre@Varrock Palace|' + '@dre@Library @dbl@for information about the @dre@Imcando Dwarves.'
SPOKEN_RELDO = HELPED + "@dbl@Reldo couldn't give me much information about the @dre@Imcando|" + '@dbl@except a few live on the @dre@southern peninsula of Asgarnia,|' + '@dbl@they dislike strangers, and LOVE @dre@redberry pies.'
GIVEN_PIE = HELPED + FOUND_THURGO + '@dbl@He will help me now I have gained his trust through @dre@pie.'
SPOKEN_THURGO = HELPED + FOUND_THURGO + '@dre@Thurgo @dbl@needs a @dre@picture of the sword @dbl@before he can help.|' + '@dbl@I should probably ask the @dre@Squire @dbl@about obtaining one.'
LOOKING_PORTRAIT = HELPED + FOUND_THURGO + '@str@Turgo needed a picture of the sword to replace.|' + "@dbl@The Squire told me about a @dre@portrait @dbl@of Sir Vyvin's father|" + "@dbl@which has a @dre@picture of the sword @dbl@in @dre@Sir Vyvin's room.|"
NEEDS_MATERIALS = HELPED + FOUND_THURGO + TOOK_PORTRAIT + '@dbl@According to @dre@Thurgo @dbl@to make a @dre@replica sword @dbl@he will need @dre@two|' + '@dre@Iron Bars @dbl@and some @dre@Blurite Ore@dbl@. @dre@Blurite Ore @dbl@can only be|' + "@dbl@found @dre@deep in the caves below Thurgo's house@dbl@. I should|" + '@dbl@prepare myself to fend off Ice giants.'
SWORD_MADE = HELPED + FOUND_THURGO + TOOK_PORTRAIT + "@str@Thurgo has now smithed me a replica of Sir Vyvin's sword.|" + '@dbl@I should return it to the @dre@Squire @dbl@for my @dre@reward.'
COMPLETE = HELPED + FOUND_THURGO + TOOK_PORTRAIT + '@str@After bringing Thurgo two iron bars and some blurite ore|' + "@str@he made me a fine replica of Sir Vyvin's sword, which I|" + '@str@returned to the Squire for a reward.||' + '@red@QUEST COMPLETE!'

def _fn1():
    cases = [['not started', NOT_STARTED, KS_STAGE.NOT_STARTED], ['started', STARTED, KS_STAGE.STARTED], ['spoken to Reldo', SPOKEN_RELDO, KS_STAGE.SPOKEN_RELDO], ['given the pie', GIVEN_PIE, KS_STAGE.GIVEN_PIE], ['spoken to Thurgo', SPOKEN_THURGO, KS_STAGE.SPOKEN_THURGO], ['looking for the portrait', LOOKING_PORTRAIT, KS_STAGE.LOOKING_PORTRAIT], ['needing materials', NEEDS_MATERIALS, KS_STAGE.LOOKING_BLURITE], ['holding the finished sword', SWORD_MADE, KS_STAGE.LOOKING_BLURITE], ['complete', COMPLETE, KS_STAGE.COMPLETE]]
    for label, text, stage in cases:

        def _make__fn2(label, text, stage):
            def _fn2():
                expect(parse_knights_sword_journal(text).stage if parse_knights_sword_journal(text) is not None else None).to_be(stage)
            return _fn2
        test(f'reads {label}', _make__fn2(label, text, stage))

    def _fn3():
        expect(parse_knights_sword_journal('@dbl@Some other quest entirely.')).to_be_undefined()
    test('an unrecognised scroll reads as undefined', _fn3)

    def _fn4():
        expect(parse_knights_sword_journal(SWORD_MADE.split('|')).stage if parse_knights_sword_journal(SWORD_MADE.split('|')) is not None else None).to_be(KS_STAGE.LOOKING_BLURITE)
    test('accepts an array of lines', _fn4)

    def _fn5():
        for label, text, stage in [row for row in cases if row[2] >= KS_STAGE.GIVEN_PIE]:
            expect(parse_knights_sword_journal(text).stage if parse_knights_sword_journal(text) is not None else None).to_be_greater_than_or_equal(KS_STAGE.GIVEN_PIE)
            expect(parse_knights_sword_journal(text).stage if parse_knights_sword_journal(text) is not None else None).to_be(stage)
    test('the appended prefix never outranks the newest marker', _fn5)
describe("The Knight's Sword journal", _fn1)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/witchshouse-journal.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.witchshouse.journal import WH_STAGE, parse_witchs_house_journal
# Pages copied from content `ball_journal.rs2`, struck-through history and all.
INTRO = '@str@A small boy has kicked his ball over the fence into the|@str@nearby garden, and I have agreed to retrieve it for him.|'
MAGNET_DONE = '@str@I have found a magnet in a cupboard in the basement.|'


def _fn1():
    def _fn2():
        expect(parse_witchs_house_journal('')).to_be_undefined()
    test('an empty page is unreadable rather than not started', _fn2)

    def _fn3():
        expect(parse_witchs_house_journal('@dbl@I should speak to Duke Horacio.')).to_be_undefined()
    test('a page from another quest is unreadable', _fn3)

    def _fn4():
        text = '@dbl@I can start this quest by speaking to the @dre@little boy|@dbl@standing by the long garden just @dre@north of taverley|' + '@dbl@I must be able to defeat a @dre@level 53 enemy'
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.NOT_STARTED)
    test('not started', _fn4)

    def _fn5():
        text = INTRO + '@dbl@I should find a way into the @dre@garden@dbl@ where the @dre@ball@dbl@ is'
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.STARTED)
    test('started', _fn5)

    def _fn6():
        text = INTRO + '@dbl@I have found a @dre@magnet@dbl@ in a cupboard in the basement'
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.FOUND_MAGNET)
    test('magnet found', _fn6)

    def _fn7():
        text = INTRO + MAGNET_DONE + '@dbl@I have worked out how to unlock the back door to the|@dre@garden'
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.UNLOCKED_DOOR)
    test('the back door outranks the magnet line it still carries', _fn7)

    def _fn8():
        text = INTRO + "@dbl@Now the @dre@shapeshifter@dbl@ is dead I should return the boy's @dre@ball"
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.DEFEATED)
    test('the experiment is dead', _fn8)

    def _fn9():
        text = INTRO + '@str@After puzzling through the strangely elaborate security|@str@system, and defeating a very strange monster, I returned|' + "@str@the child's ball to him, and he thanked me for my help.||@red@QUEST COMPLETE!"
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.COMPLETE)
    test('complete', _fn9)

    def _fn10():
        lines = [
        '@str@A small boy has kicked his ball over the fence into the',
        'nearby garden, and I have agreed to retrieve it for him.',
        '@dbl@I have found a @dre@magnet@dbl@ in a cupboard in the basement',
    ]
        expect((parse_witchs_house_journal(lines).stage if parse_witchs_house_journal(lines) is not None else None)).to_be(WH_STAGE.FOUND_MAGNET)
    test('the journal arrives as separate lines as well as one string', _fn10)

    # Why: `witches_diary.rs2` moves the varp 3 → 5 and `ball_journal.rs2` renders both cases from the
    # same branch, so the read is invisible to the client and the module tracks it itself.
    def _fn11():
        text = INTRO + MAGNET_DONE + '@dbl@I have worked out how to unlock the back door to the|@dre@garden'
        expect((parse_witchs_house_journal(text).stage if parse_witchs_house_journal(text) is not None else None)).to_be(WH_STAGE.UNLOCKED_DOOR)
        expect(WH_STAGE.READ_DIARY).to_be_greater_than(WH_STAGE.UNLOCKED_DOOR)
    test('reading the diary leaves the page identical to stage 3', _fn11)

    def _fn12():
        spliced = INTRO + '@dbl@I have worked out how to@dre@ unlock the back door to the|@dre@garden'
        expect((parse_witchs_house_journal(spliced).stage if parse_witchs_house_journal(spliced) is not None else None)).to_be(WH_STAGE.UNLOCKED_DOOR)
    test('a colour tag inside a needle still matches once normalized', _fn12)


describe('parseWitchsHouseJournal', _fn1)

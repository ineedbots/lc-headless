"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fishingcontest-journal.test.ts (MIT, see thirdparty/rs2b0t)."""


from rs2004.quests.defs.fishingcontest.journal import FC_STAGE, parse_fishing_contest_journal
PREAMBLE = '@str@The Dwarves will let me use the tunnel through White Wolf|@str@Mountain if I can win the Hemenster Fishing Competition.|'
PAGE = Obj({
    FC_STAGE.NOT_STARTED: '@dbl@I can start this quest by speaking to the @dre@Dwarves@dbl@ at the tunnel entrances on either side of @dre@White Wolf Mountain@dbl@.|' + '@str@I must have level 10 fishing.',
    FC_STAGE.STARTED: PREAMBLE + '@dbl@They gave me a @dre@Fishing Contest Pass@dbl@ to enter the contest. I need to bring them back the @dre@Hemenster Fishing Trophy',
    FC_STAGE.IN_COMP: PREAMBLE + '@dbl@My @dre@fishing spot@dbl@ in the contest is @dre@next to the willow tree @dbl@I need to catch the @dre@biggest fish@dbl@ to win!',
    FC_STAGE.GARLIC_COMP: PREAMBLE + '@dbl@My @dre@fishing spot@dbl@ in the contest is @dre@next to the pipes @dbl@I need to catch the @dre@biggest fish@dbl@ to win!',
    FC_STAGE.WON_COMP: PREAMBLE + '@str@I easily won the contest by catching some Giant Carp.|' + '@dbl@I should take the @dre@Trophy@dbl@ back to the @dre@Dwarf@dbl@ at the side of @dre@White Wolf Mountain@dbl@ and claim my @dre@reward',
    FC_STAGE.COMPLETE: '@dbl@The Dwarves wanted me to earn their friendship by|@dbl@winning the Hemenster Fishing Competition.|' + '@dbl@I scared away a vampire with some garlic and easily won the contest by catching some Giant Carp.|' + '@dbl@As a reward for getting the Fishing Competition Trophy the Dwarves will let me use their tunnel to travel quickly and|' + '@dbl@safely under White Wolf Mountain anytime I wish.||@red@QUEST COMPLETE!',
})


def journal_case(stage, page):
    def run():
        expect(parse_fishing_contest_journal(page)).to_be(stage)
    return run


def _fn1():
    for stage, page in PAGE.items():
        test(f'reads its own page as stage {stage}', journal_case(stage, page))

    def _fn3():
        expect(parse_fishing_contest_journal(PAGE[FC_STAGE.IN_COMP])).to_be(FC_STAGE.IN_COMP)
        expect(parse_fishing_contest_journal(PAGE[FC_STAGE.GARLIC_COMP])).to_be(FC_STAGE.GARLIC_COMP)
    test('separates the willow-tree spot from the pipes', _fn3)

    def _fn4():
        expect(parse_fishing_contest_journal(PAGE[FC_STAGE.COMPLETE])).to_be(FC_STAGE.COMPLETE)
    test('reads the complete page even though it still mentions the garlic and the carp', _fn4)

    def _fn5():
        expect(parse_fishing_contest_journal(PAGE[FC_STAGE.WON_COMP].split('|'))).to_be(FC_STAGE.WON_COMP)
    test('accepts the page as an array of lines', _fn5)

    def _fn6():
        expect(parse_fishing_contest_journal('some other quest entirely')).to_be_undefined()
        expect(parse_fishing_contest_journal('')).to_be_undefined()
    test('returns undefined for a page it cannot place', _fn6)


describe('Fishing Contest journal parsing', _fn1)

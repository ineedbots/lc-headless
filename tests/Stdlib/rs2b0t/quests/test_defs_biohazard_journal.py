"""Ported from rs2b0t's test/api/ai/quests/defs/biohazard-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.biohazard.journal import BIO_STAGE, parse_biohazard_journal

SPOKEN_ELENA = "@str@I've spoken to Elena, the Mourners stole her distillator|"
SPOKEN_JERICO = "|@str@I've spoken to Jerico about getting into West Ardougne|"
CROSSED = "|@str@I've crossed the wall into West Ardougne" + '|@str@Omart and Kilron will stay to help me out again|'
HUNTING = "|@dbl@Somewhere in this city is @dre@Elena's distillator @dbl@- I must find|it and return it to her|"
RETURNED = "|@str@I've found Elena's Distillator and returned it to her|"
CHEMICALS = '|@str@Elena gave me some chemicals to take to Guidor|'
DELIVERED = "|@str@I've given all the items to Guidor|"


def page(*lines):
    return ''.join(lines)


def _fn1():
    def _fn2():
        text = '@dbl@I can start this quest by speaking to @dre@Elena @dbl@who is in @dre@East|Ardougne'
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.NOT_STARTED)
    test('the opening page is not started', _fn2)

    def _fn3():
        text = page(SPOKEN_ELENA, '|@dbl@I need to talk to @dre@Jerico @dbl@about getting over the wall and|into @dre@West Ardougne')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.STARTED)
    test('a quest that has only met Elena needs Jerico', _fn3)

    def _fn4():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, '|@dre@Omart @dbl@will be able to get me over the wall', "|@dbl@He's waiting at the @dre@South @dbl@end of the wall")
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.SPOKEN_JERICO)
    test('Jerico names Omart', _fn4)

    def _fn5():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, "|@dbl@I've chucked some birdfeed onto the Watch Tower")
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.USED_BIRDFEED)
    test('the thrown seed reads past the Jerico line', _fn5)

    def _fn6():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, '|@dbl@The Watch Tower is now surrounded by flapping pigeons!', '|@dbl@Maybe I can sneak over the wall while the mourners are|distracted')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.RELEASED_PIGEONS)
    test('the flapping pigeons read past the seed', _fn6)

    def _fn7():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, HUNTING)
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.CLIMBED_LADDER)
    test('crossing the wall reads past everything before it', _fn7)

    def _fn8():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, HUNTING, "|@dbl@I have rather unkindly poisoned the mourners' stew by|putting rotten apples into it!")
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.POISONED_STEW)
    test('the poisoned stew outranks the crossing line it sits under', _fn8)

    def _fn9():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, "|@str@I managed to find Elena's distillator", '|@dbl@Now I can return the @dre@distillator @dbl@to @dre@Elena')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.FOUND_DISTILLATOR)
    test('finding the distillator outranks the poisoned stew', _fn9)

    def _fn10():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, "|@str@I managed to find Elena's distillator", '|@dbl@I seem to have mislaid the @dre@distillator')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.FOUND_DISTILLATOR)
    test('a mislaid distillator still reads as found, not as lost progress', _fn10)

    def _fn11():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, RETURNED, "|@dbl@Elena's asked me to take the following items to @dre@Guidor @dbl@who|lives in @dre@Varrock", '|@dre@Plague Sample @dbl@from @dre@Elena')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.GIVEN_DISTILLATOR)
    test("Elena's shopping list is the handed-over stage", _fn11)

    def _fn12():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, RETURNED, CHEMICALS, '|@dbl@The Varrock guards are out looking for someone carrying|suspicious materials.')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.SPOKEN_CHEMIST)
    test('the Varrock guards line is the chemist stage', _fn12)

    def _fn13():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, RETURNED, CHEMICALS, DELIVERED, "|@dre@Guidor's @dbl@findings were very interesting", '|@dbl@Apparently there is no @dre@Plague@dbl@!')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.FOUND_SECRET)
    test("Guidor's findings outrank the delivery line under them", _fn13)

    def _fn14():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, RETURNED, CHEMICALS, DELIVERED, "|@str@I've told Elena Guidor's findings, she was horrified!|", '|@dbl@I need to confront the @dre@King of East Ardougne')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.REPORTED_ELENA)
    test('the king line outranks the findings under it', _fn14)

    def _fn15():
        text = page(SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, RETURNED, CHEMICALS, DELIVERED, "|@str@I've spoken to King Lathas, he admits the Plague was fake!|", '@red@QUEST COMPLETE!')
        expect((parse_biohazard_journal(text).stage if parse_biohazard_journal(text) is not None else None)).to_be(BIO_STAGE.COMPLETE)
    test('a finished quest reads complete', _fn15)

    def _fn16():
        expect(parse_biohazard_journal('@dbl@Something else entirely')).to_be_undefined()
    test('an unrecognised page is undefined rather than stage zero', _fn16)

    def _fn17():
        lines = [SPOKEN_ELENA, SPOKEN_JERICO, CROSSED, HUNTING]
        expect((parse_biohazard_journal(lines).stage if parse_biohazard_journal(lines) is not None else None)).to_be(BIO_STAGE.CLIMBED_LADDER)
    test('an array of lines parses the same as the joined page', _fn17)


describe('biohazard journal parser', _fn1)

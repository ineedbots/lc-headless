"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/scorpcatcher-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.scorpcatcher.areas import SC_STAGE
from rs2004.quests.defs.scorpcatcher.journal import parse_scorpion_journal

NOT_STARTED = "@dbl@I can start this quest by speaking to @dre@Thormac@dbl@ who is in the @dre@Sorcerer's Tower@dbl@" + ' south-west of @dre@Catherby@dbl@.||@dbl@Requirements:|@str@Level 31 Prayer|'
PREAMBLE = "@str@I've spoken to Thormac in the Sorcerer's Tower south-west|" + "@str@of Catherby. He's lost his pet Kharid Scorpions and needs|" + '@str@my help to find them.'
SEER_NEXT = "||@dbl@I need to go to the @dre@Seers' Village@dbl@ and talk to the @dre@Seers@dbl@" + ' about the lost @dre@Kharid Scorpions@dbl@.'
SEEN_A_SEER = "||@str@I've spoken to a Seer and been given the location of one|@str@of the Kharid Scorpions."
FIRST_HINT = '||@dbl@The first @dre@Kharid Scorpion@dbl@ is in a secret room near some @dre@nasty spiders@dbl@' + ' with two @dre@coffins@dbl@ nearby.'
CATCH_THE_FIRST = "||@dbl@I'll need to talk to a @dre@Seer@dbl@ again once I've caught the first @dre@Kharid Scorpion@dbl@."
SECOND_HINT = '||@dbl@The second @dre@Kharid Scorpion@dbl@ has been in a @dre@village of uncivilised-looking warriors' + " in the east@dbl@. It's been picked up by some sort of @dre@merchant@dbl@."
THIRD_HINT = '||@dbl@The third @dre@Kharid Scorpion@dbl@ is in some sort of @dre@upstairs room@dbl@' + ' with @dre@brown clothing@dbl@ on a table.'
COMPLETE = "||@str@I've spoken to Thormac and he thanked me for finding his|@str@pet Kharid Scorpions." + '||@red@QUEST COMPLETE!'


def _fn1():
    def _fn2():
        expect((parse_scorpion_journal(NOT_STARTED).stage if parse_scorpion_journal(NOT_STARTED) is not None else None)).to_be(SC_STAGE.NOT_STARTED)
    test('the unstarted page reads stage 0', _fn2)

    def _fn3():
        expect((parse_scorpion_journal(PREAMBLE + SEER_NEXT).stage if parse_scorpion_journal(PREAMBLE + SEER_NEXT) is not None else None)).to_be(SC_STAGE.STARTED)
    test('Thormac spoken to but no Seer yet reads stage 1', _fn3)

    def _fn4():
        page = PREAMBLE + SEEN_A_SEER + FIRST_HINT + CATCH_THE_FIRST
        expect((parse_scorpion_journal(page).stage if parse_scorpion_journal(page) is not None else None)).to_be(SC_STAGE.FIRST_HINT)
    test('the first hint alone reads stage 2', _fn4)

    # Why: the second and third hints arrive together, and the page keeps the first, so a rule that stops at the first hint would read every later stage as 2.
    def _fn5():
        page = PREAMBLE + SEEN_A_SEER + FIRST_HINT + SECOND_HINT + THIRD_HINT
        expect((parse_scorpion_journal(page).stage if parse_scorpion_journal(page) is not None else None)).to_be(SC_STAGE.SECOND_HINT)
    test('the second hint reads stage 3 even with the first hint still on the page', _fn5)

    def _fn6():
        page = PREAMBLE + SEEN_A_SEER + FIRST_HINT + SECOND_HINT + THIRD_HINT + COMPLETE
        expect((parse_scorpion_journal(page).stage if parse_scorpion_journal(page) is not None else None)).to_be(SC_STAGE.COMPLETE)
    test('the reward line reads complete', _fn6)

    def _fn7():
        expect((parse_scorpion_journal([PREAMBLE, SEER_NEXT]).stage if parse_scorpion_journal([PREAMBLE, SEER_NEXT]) is not None else None)).to_be(SC_STAGE.STARTED)
    test('lines arrive as an array as well as a string', _fn7)

    def _fn8():
        expect(parse_scorpion_journal('@dbl@I can start this quest by talking to @dre@Brother Kojo')).to_be_undefined()
    test('a page from another quest parses to nothing', _fn8)


describe('parseScorpionJournal', _fn1)

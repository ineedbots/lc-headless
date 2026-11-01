"""rs2b0t's test/api/ai/quests/defs/chompybird-journal.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.quests.defs.chompybird.areas import CB_STAGE
from rs2004.quests.defs.chompybird.journal import parse_chompy_journal

NOT_STARTED = '@dbl@I can start this quest by speaking to the ogre @dre@Rantz @dbl@who|lives @dre@East ' + '@dbl@of the @dre@Ogre City@dbl@, @dre@North @dbl@of the @dre@Swamp Pool.|@dbl@To complete this quest I need:|' + '@str@Level 5 Fletching|@str@Level 30 Cooking|@str@Level 30 Ranging|'
OPENING = "@str@I found an ogre named Rantz near a cave just East of|@str@the Ogre City. When I spoke to him he seemed obsessed|@str@with using things called 'stabbers' to hunt 'Chompy Birds'.|"
STARTED = "|@dbl@I agreed to get @dre@Rants @dbl@some @dre@'stabbers'"
ARROWS = "|@str@It turned out that 'stabbers' are a kind of specially made|@str@ogre arrow that are quite sturdily constructed. I brought|@str@Rantz some so that he could catch 'chompy'.|"
TOADIES = "|@str@Rantz told me 'fatsy toadies' grow fat on swamp gas...|"
TRAPPED = "|@str@I managed to trap some 'fatsy toadies' by using some gas|@str@filled ogre bellows. I took the 'fatsy toady' to Rantz.|"
DROPPED = '|@str@I dropped a fatsy toady on the spot Rantz showed me.|'
MISSED = "|@str@Rantz doesn't seem to be a very good shot... maybe I|@str@should try to shoot a chompy for him?|"
LENT = '|@dre@Rantz @dbl@has lent me an @dre@Ogre bow @dbl@so I can kill a @dre@chompy|bird.'
KILLED = '|@str@Rantz taught me how to use bloated swamp toads to lure|@str@Chompy Birds and hunt them. ' + "I've killed a chompy bird!|"
SHOWN = '|@str@I showed Rantz the chompy. He seemed quite impressed.|'
COOKED = "|@dbl@I've @dre@cooked @dbl@the @dre@chompy @dbl@for that cheeky @dre@ogre @dbl@and his @dre@kids@dbl@,|" + "I'd better take it to them before they @dre@starve@dbl@!"
COMPLETE = "@str@Once I had Rantz's bow, it was easy to hunt chompy birds|@str@using the nearby swamp toads." + '|@red@QUEST COMPLETE!'


def stage_of(page):
    return (parse_chompy_journal(page).stage if parse_chompy_journal(page) is not None else None)


def _fn1():
    def _fn2():
        expect(parse_chompy_journal('nothing to do with ogres')).to_be_undefined()
    test('an unrecognised page parses to nothing', _fn2)

    def _fn3():
        expect(stage_of(NOT_STARTED)).to_be(CB_STAGE.NOT_STARTED)
    test('the not-started page', _fn3)

    def _fn4():
        expect(stage_of(OPENING + ARROWS + KILLED + COMPLETE)).to_be(CB_STAGE.COMPLETE)
    test('the completion page wins over every line above it', _fn4)

    def _fn5():
        expect(stage_of(OPENING + STARTED)).to_be(CB_STAGE.STARTED)
    test('agreeing to make the stabbers', _fn5)

    def _fn6():
        expect(stage_of(OPENING + ARROWS)).to_be(CB_STAGE.GIVEN_ARROWS)
    test('the arrows handed over', _fn6)

    def _fn7():
        expect(stage_of(OPENING + ARROWS + TOADIES)).to_be(CB_STAGE.KIDS_PLAY_WITH_TOAD)
    test('the toadies explained', _fn7)

    def _fn8():
        expect(stage_of(OPENING + ARROWS + TOADIES + TRAPPED)).to_be(CB_STAGE.SHOWN_TOAD)
    test('a toad shown to Rantz', _fn8)

    def _fn9():
        expect(stage_of(OPENING + ARROWS + TOADIES + TRAPPED + DROPPED)).to_be(CB_STAGE.DROPPED_TOAD)
    test('the bait placed', _fn9)

    # Why: 40 and 45 render the same paragraph, and only the lent-bow line separates them.
    def _fn10():
        expect(stage_of(OPENING + ARROWS + TOADIES + TRAPPED + DROPPED + MISSED)).to_be(CB_STAGE.RANTZ_MISSED)
    test('Rantz missing his shot', _fn10)

    def _fn11():
        expect(stage_of(OPENING + ARROWS + TOADIES + TRAPPED + DROPPED + MISSED + LENT)).to_be(CB_STAGE.GOT_BOW)
    test('the bow lent out', _fn11)

    def _fn12():
        expect(stage_of(OPENING + ARROWS + TOADIES + TRAPPED + DROPPED + MISSED + KILLED)).to_be(CB_STAGE.KILLED_CHOMPY)
    test('the chompy killed', _fn12)

    def _fn13():
        expect(stage_of(OPENING + ARROWS + DROPPED + MISSED + KILLED + SHOWN)).to_be(CB_STAGE.TOLD_TO_COOK)
    test('the carcass shown to Rantz', _fn13)

    def _fn14():
        expect(stage_of(OPENING + ARROWS + DROPPED + MISSED + KILLED + SHOWN + COOKED)).to_be(CB_STAGE.CHOMPY_COOKED)
    test('the chompy cooked', _fn14)

    def _fn15():
        expect((parse_chompy_journal([OPENING, ARROWS, TOADIES]).stage if parse_chompy_journal([OPENING, ARROWS, TOADIES]) is not None else None)).to_be(CB_STAGE.KIDS_PLAY_WITH_TOAD)
    test('a page split into components reads the same as one string', _fn15)


describe('big chompy bird hunting journal', _fn1)

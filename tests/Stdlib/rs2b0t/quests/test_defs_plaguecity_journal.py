"""Ported from rs2b0t's test/api/ai/quests/defs/plaguecity-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, plague_area
from rs2004.quests.defs.plaguecity.journal import PC_STAGE, parse_plague_journal

def at(x, z, level=0):
    return (Record({'x': x, 'z': z, 'level': level}))


OPENING = "@str@I've spoken to Edmond, he's asked me to help find his|@str@daughter Elena.|"
GASMASK = '@str@Alrena has given me a Gasmask to protect me from the|@str@plague while in West Ardougne.'
DIGGING = "@str@I've spoken to Edmond about getting into West Ardougne.|"
SOFT = "@str@I've softened the ground in Edmond's garden enough to dig.|"
TUNNEL = "@str@I've dug a tunnel into the sewers.|"
PIPE = "@str@I've managed to clear the way into West Ardougne.|"
JETHICK = "@str@I've spoken to Jethick, he thinks Elena was staying with|@str@the Rehnison Family, in a timber house to the north of the|@str@city.|"
MILLI = "@str@I've spoken to Milli about Elena, she says Elena was taken|@str@into one of the Plague Houses.|"
CURE = '@str@Bravek might give me clearance if I make his Hangover|@str@Cure.|'
WARRANT = "@str@I've given Bravek the Hangover Cure and he has given me|@str@a warrant to enter the plague House.|"


def _fn1():
    def _fn2():
        expect(plague_area(at(2616, 3332))).to_be('east')
        expect(plague_area(at(2540, 3305))).to_be('west')
        expect(plague_area(at(2529, 3331, 1))).to_be('upstairs')
        expect(plague_area(at(2541, 9672))).to_be('cellar')
        expect(plague_area(at(2530, 9703))).to_be('sewer')
        expect(plague_area(at(2561, 9737))).to_be('sewer')
    test('classifies every pocket the quest can strand the bot in', _fn2)

    def _fn3():
        expect(plague_area(at(2537, 9670))).to_be('cellar')
        expect(plague_area(at(2535, 9719))).to_be('sewer')
    test('the plague house cellar is not swallowed by the sewer', _fn3)

    def _fn4():
        expect(plague_area(at(2566, 3331))).to_be('east')
        expect(plague_area(at(2556, 3300))).to_be('west')
        expect(plague_area(at(2557, 3300))).to_be('east')
    test("Edmond's garden is east, one tile outside the West Ardougne wall", _fn4)

    def _fn5():
        expect(plague_area(None)).to_be('unknown')
        expect(plague_area(None)).to_be('unknown')
    test('a null tile is unknown, never a default area', _fn5)


describe('plagueArea', _fn1)


def _fn6():
    def _fn7():
        expect(PC_ITEM.TURNIP_BOOK.name).to_be('Book')
        expect(PC_ITEM.SCRUFFY_NOTE.name).to_be('A scruffy note')
        expect(PC_ITEM.ELENA_KEY.name).to_be('A small key')
        expect(PC_ITEM.ARDOUGNE_SCROLL.name).to_be('A magic scroll')
        expect(PC_ITEM.PICTURE.name).to_be('Picture')
    test('the engine names that differ from the wiki are recorded exactly', _fn7)


describe('plague city item names', _fn6)


def _fn8():
    def _fn9():
        expect((parse_plague_journal('@dbl@I can start this quest by speaking to @dre@Edmond').stage if parse_plague_journal('@dbl@I can start this quest by speaking to @dre@Edmond') is not None else None)).to_be(PC_STAGE.NOT_STARTED)
    test('not started', _fn9)

    def _fn10():
        expect((parse_plague_journal([OPENING, '@dbl@I need to get some Dwellberries for @dre@Alrena']).stage if parse_plague_journal([OPENING, '@dbl@I need to get some Dwellberries for @dre@Alrena']) is not None else None)).to_be(PC_STAGE.STARTED)
    test('started, before the berries reach Alrena', _fn10)

    def _fn11():
        p = parse_plague_journal([OPENING, GASMASK, '@dbl@I need to talk to @dre@Edmond @dbl@about getting into @dre@West Ardougne'])
        expect((p.stage if p is not None else None)).to_be(PC_STAGE.GASMASK)
    test('the mask alone is stage 2 — the digging line has not appeared', _fn11)

    def _fn12():
        p = parse_plague_journal([OPENING, GASMASK, DIGGING, '@dbl@I need to use @dre@Water @dbl@to soften the ground'])
        expect((p.stage if p is not None else None)).to_be(PC_STAGE.MUD_START)
    test('stages 3 to 6 all read as the low end of the water block', _fn12)

    def _fn13():
        expect((parse_plague_journal([OPENING, GASMASK, DIGGING, SOFT, '@dbl@Now I need to dig a tunnel']).stage if parse_plague_journal([OPENING, GASMASK, DIGGING, SOFT, '@dbl@Now I need to dig a tunnel']) is not None else None)).to_be(PC_STAGE.MUD_SOFT)
    test('softened soil outranks the digging line', _fn13)

    def _fn14():
        expect((parse_plague_journal([SOFT, TUNNEL]).stage if parse_plague_journal([SOFT, TUNNEL]) is not None else None)).to_be(PC_STAGE.TUNNEL)
        expect((parse_plague_journal([SOFT, TUNNEL, "@dbl@I've tied a rope to the sewer grill but I need help"]).stage if parse_plague_journal([SOFT, TUNNEL, "@dbl@I've tied a rope to the sewer grill but I need help"]) is not None else None)).to_be(PC_STAGE.ROPE_TIED)
        expect((parse_plague_journal([SOFT, TUNNEL, PIPE]).stage if parse_plague_journal([SOFT, TUNNEL, PIPE]) is not None else None)).to_be(PC_STAGE.PIPE_OPEN)
    test('the tunnel, the tied rope and the open pipe each outrank the block below', _fn14)

    def _fn15():
        expect((parse_plague_journal([PIPE, JETHICK]).stage if parse_plague_journal([PIPE, JETHICK]) is not None else None)).to_be(PC_STAGE.SHOWN_PICTURE)
    test('stages 20 and 21 both read as SHOWN_PICTURE — the book in the pack tells them apart', _fn15)

    def _fn16():
        expect((parse_plague_journal([JETHICK, "@dbl@The @dre@Rehnisons' daughter Milli @dbl@may have seen @dre@Elena."]).stage if parse_plague_journal([JETHICK, "@dbl@The @dre@Rehnisons' daughter Milli @dbl@may have seen @dre@Elena."]) is not None else None)).to_be(PC_STAGE.SPOKEN_PARENTS)
        expect((parse_plague_journal([JETHICK, MILLI, '@dbl@I need to get access to the @dre@Plague House']).stage if parse_plague_journal([JETHICK, MILLI, '@dbl@I need to get access to the @dre@Plague House']) is not None else None)).to_be(PC_STAGE.SPOKEN_MILLI)
    test('the parents line is stage 22 and Milli is stage 23', _fn16)

    def _fn17():
        expect((parse_plague_journal([MILLI, '@dbl@I need clearance from either the @dre@Head Mourner @dbl@or @dre@Bravek']).stage if parse_plague_journal([MILLI, '@dbl@I need clearance from either the @dre@Head Mourner @dbl@or @dre@Bravek']) is not None else None)).to_be(PC_STAGE.NEED_CLEARANCE)
    test('stages 24 and 25 both read as NEED_CLEARANCE', _fn17)

    def _fn18():
        expect((parse_plague_journal([MILLI, CURE, '@dbl@I need to bring @dre@Bravek @dbl@the @dre@Hangover Cure']).stage if parse_plague_journal([MILLI, CURE, '@dbl@I need to bring @dre@Bravek @dbl@the @dre@Hangover Cure']) is not None else None)).to_be(PC_STAGE.SPOKEN_BRAVEK)
        expect((parse_plague_journal([CURE, WARRANT]).stage if parse_plague_journal([CURE, WARRANT]) is not None else None)).to_be(PC_STAGE.CURED_BRAVEK)
        expect((parse_plague_journal([WARRANT, "@str@I've freed Elena from the Plague House.|"]).stage if parse_plague_journal([WARRANT, "@str@I've freed Elena from the Plague House.|"]) is not None else None)).to_be(PC_STAGE.FREED_ELENA)
    test('the recipe, the warrant and the rescue each move the stage on', _fn18)

    def _fn19():
        expect((parse_plague_journal([WARRANT, "@str@I've freed Elena from the Plague House.|", '@red@QUEST COMPLETE!']).stage if parse_plague_journal([WARRANT, "@str@I've freed Elena from the Plague House.|", '@red@QUEST COMPLETE!']) is not None else None)).to_be(PC_STAGE.COMPLETE)
    test('complete', _fn19)

    def _fn20():
        expect(parse_plague_journal(['something else entirely'])).to_be_undefined()
    test('unrecognised journal text yields undefined, never a default stage', _fn20)


describe('parsePlagueJournal', _fn8)

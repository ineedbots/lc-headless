"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/observatory-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.observatory.areas import OBS_STAGE
from rs2004.quests.defs.observatory.journal import parse_observatory_journal

HEAD_DBL = '@dbl@I can start this quest by talking to the @dre@professor@dbl@, in the ' + '@dre@Observatory reception, south-west of Ardougne.'
HEAD = '@str@I can start this quest by talking to the professor, in the|' + '@str@Observatory reception, south-west of Ardougne.|'
LIST_DBL = '@dbl@Seems the observatory telescope needs repairing, due to the nearby goblins. ' + 'The @dre@professor@dbl@ wants me to help by getting the following, with the help of his @dre@assistant:||'
LIST_STR = '@str@Seems the observatory telescope needs repairing, due to|' + '@str@the nearby goblins. The professor wants me to help by|' + '@str@getting the following, with the help of his assistant:||' + '@str@3 wooden planks|@str@1 bronze bar|@str@1 molten glass|@str@1 lens mould|'
LENS_DBL = '@dbl@The @dre@professor@dbl@ was pleased to have all the pieces needed to fix the telescope. Apparently, ' + "the professor's last attempt at Crafting ended in disaster. So, he wants me to create the @dre@lens@dbl@ " + 'by using the @dre@molten glass@dbl@ with the @dre@mould.|Fine by me!|'
LENS_STR = '@str@The professor was pleased to have all the pieces needed|' + "@str@to fix the telescope. Apparently, the professor's last|" + '@str@attempt at Crafting ended in disaster. So, he wants me to|' + '@str@create the lens by using the molten glass with the mould.|' + '@str@Fine by me!|'
TELE_DBL = '@dbl@The @dre@professor@dbl@ has gone ahead to the @dre@Observatory.@dbl@ He wants me to meet him there ' + 'by travelling through the @dre@dungeon@dbl@ below it.|'
TELE_STR = '@str@The professor has eagerly gone ahead to the Observatory.|' + '@str@He wants me to meet him there by travelling through the|' + '@str@dungeon below it. I hope I get to look through the|' + '@str@telescope!|'
WANTED = ['3 wooden planks', '1 bronze bar', '1 molten glass', '1 lens mould']


def shopping(index):
    """Stages 1-4 list every item won so far in `@str@` and the one still wanted in `@dre@`."""
    return HEAD + LIST_DBL + ''.join([f'@str@{w}|' for w in WANTED[0:index]]) + f'@dre@{WANTED[index]}|'


PAGES = {
    OBS_STAGE.NOT_STARTED: HEAD_DBL,
    OBS_STAGE.STARTED: shopping(0),
    OBS_STAGE.GIVEN_PLANKS: shopping(1),
    OBS_STAGE.GIVEN_BRONZE: shopping(2),
    OBS_STAGE.GIVEN_GLASS: shopping(3),
    OBS_STAGE.GIVEN_MOULD: HEAD + LIST_STR + LENS_DBL,
    OBS_STAGE.SENT_TELESCOPE: HEAD + LIST_STR + LENS_STR + TELE_DBL,
    OBS_STAGE.COMPLETE: HEAD + LIST_STR + LENS_STR + TELE_STR + '@dre@QUEST COMPLETE!' + '|@dbl@I should probably see what the @dre@assistant@dbl@ thinks of all this.|He should be pleased.',
}


def reads(stage, page):
    def run():
        expect(parse_observatory_journal(page)).to_be(stage)
    return run


def _fn1():
    for stage, page in PAGES.items():
        test(f'reads stage {stage}', reads(stage, page))

    def _fn3():
        expect(parse_observatory_journal([HEAD, LIST_DBL, '@dre@3 wooden planks|'])).to_be(OBS_STAGE.STARTED)
    test('reads a page handed over as separate lines', _fn3)

    def _fn4():
        wine = PAGES[OBS_STAGE.COMPLETE].replace('@dbl@I should probably', '@str@I had a word with') + '@str@some wine! What a pleasant chap.'
        expect(parse_observatory_journal(wine)).to_be(OBS_STAGE.COMPLETE)
    test('the claimed-wine page still reads complete', _fn4)

    def _fn5():
        expect(parse_observatory_journal('@dbl@I can start this by talking to Duke Horacio.')).to_be_undefined()
    test('an unrelated page reads as unknown', _fn5)

    def _fn6():
        expect(parse_observatory_journal([])).to_be_undefined()
    test('an empty page reads as unknown', _fn6)


describe('parseObservatoryJournal', _fn1)

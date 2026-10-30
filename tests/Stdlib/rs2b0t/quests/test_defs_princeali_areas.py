"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/princeali-areas.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.quests.defs.princeali.areas import KELI_PRINT, NED_ROPE, NED_WIG, OSMAN_BRIEF, PA_ITEM

def _fn1():
    INSTRUCTIONS = ['What is the first thing I must do?', 'What is the second thing you need?']
    FIRST_THING = ['Explain the first thing again.', 'What is the second thing you need?', 'Okay, I better go find some things.']
    SECOND_THING = ['What is the first thing I must do?', 'What exactly is the second thing you need?', 'Okay, I better go find some things.']

    def _fn2():
        expect(pick_preferred(INSTRUCTIONS, OSMAN_BRIEF.prefer)).to_be('What is the second thing you need?')
    test('the first page moves on to a branch', _fn2)

    def _fn3():
        expect(pick_preferred(SECOND_THING, OSMAN_BRIEF.prefer)).to_be('Okay, I better go find some things.')
    test('the second-thing page takes the exit, not the way back', _fn3)

    def _fn4():
        expect(pick_preferred(FIRST_THING, OSMAN_BRIEF.prefer)).to_be('Okay, I better go find some things.')
    test('the first-thing page also takes the exit', _fn4)
describe('Osman briefing cannot loop', _fn1)

def _fn5():
    STANDARD = ['Ned, could you make other things from wool?', 'Yes, I would like some rope.', "No thanks, Ned. I don't need any."]
    WITHOUT_WOOL = ['Okay, please sell me some rope.', "That's a little more than I want to pay.", 'I will go and get some wool.']
    WITH_WOOL = ['Okay, please sell me some rope.', "That's a little more than I want to pay.", 'I have some balls of wool. Could you make me some rope?']

    def _fn6():
        expect(pick_preferred(STANDARD, NED_ROPE.prefer)).to_be('Yes, I would like some rope.')
    test('opens by asking for rope, not for wool work', _fn6)

    def _fn7():
        expect(pick_preferred(WITHOUT_WOOL, NED_ROPE.prefer)).to_be('Okay, please sell me some rope.')
    test('pays 15 coins with no wool in the pack', _fn7)

    def _fn8():
        expect(pick_preferred(WITH_WOOL, NED_ROPE.prefer)).to_be('Okay, please sell me some rope.')
    test('still pays 15 coins when four balls of wool are in the pack', _fn8)
describe('Ned never spends four balls of wool on rope', _fn5)

def _fn9():
    STANDARD = ['Ned, could you make other things from wool?', 'Yes, I would like some rope.', "No thanks, Ned. I don't need any."]
    OTHER_THINGS = ['Could you knit me a sweater?', 'How about some sort of wig?', 'Could you repair the arrow holes in the back of my shirt?']
    WIG = ['I have that now. Please, make me a wig.', 'I will come back when I need you to make me one.']

    def _fn10():
        expect(pick_preferred(STANDARD, NED_WIG.prefer)).to_be('Ned, could you make other things from wool?')
    test('page 1 asks about wool work', _fn10)

    def _fn11():
        expect(pick_preferred(OTHER_THINGS, NED_WIG.prefer)).to_be('How about some sort of wig?')
    test('page 2 asks for a wig', _fn11)

    def _fn12():
        expect(pick_preferred(WIG, NED_WIG.prefer)).to_be('I have that now. Please, make me a wig.')
    test('page 3 hands over the wool', _fn12)
describe('Ned makes the wig in three picks', _fn9)

def keli_picks(page, want):
    def run():
        expect(pick_preferred(page, KELI_PRINT.prefer)).to_be(want)
    return run


def _fn13():
    PAGES = [['Heard of you? You are famous in RuneScape!', 'I have heard a little, but I think Katrine is tougher.', 'I have heard rumours that you kill people.', 'No I have never really heard of you.'], ['I think Katrine is still tougher.', 'What is your latest plan then?', 'You must have trained a lot for this work.', 'I should not disturb someone as tough as you.'], ['Ah I see. You must have been very skillful.', 'Thats great, are you sure they will pay?', 'Can you be sure they will not try to get him out?', 'I should not disturb someone as tough as you.'], ['Could I see the key please?', 'That is a good way to keep secrets.', 'I should not disturb someone as tough as you.'], ['Could I touch the key for a moment?', 'I should not disturb someone as tough as you.']]
    WANT = ['Heard of you? You are famous in RuneScape!', 'What is your latest plan then?', 'Can you be sure they will not try to get him out?', 'Could I see the key please?', 'Could I touch the key for a moment?']
    for i in range(len(PAGES)):
        test(f'page {i + 1} picks "{WANT[i]}"', keli_picks(PAGES[i], WANT[i]))

    def _fn15():
        for page in PAGES:
            pick = pick_preferred(page, KELI_PRINT.prefer)
            expect(pick).not_.to_contain('I should not disturb')
            expect(pick).not_.to_contain('Katrine')
    test('never takes the polite exit, and never insults her into a dead end', _fn15)
describe('Lady Keli walks all five pages to the imprint', _fn13)

def _fn16():

    def _fn17():
        expect(PA_ITEM.PLAIN_WIG.name).to_be(PA_ITEM.BLOND_WIG.name)
        expect(PA_ITEM.PLAIN_WIG.id).not_.to_be(PA_ITEM.BLOND_WIG.id)
    test('the two wigs share a name and differ only by id', _fn17)

    def _fn18():
        expect(PA_ITEM.BLOND_WIG.id).to_be(2419)
        expect(PA_ITEM.PLAIN_WIG.id).to_be(2421)
        expect(PA_ITEM.PRINCE_KEY.id).to_be(2418)
        expect(PA_ITEM.KEY_PRINT.id).to_be(2423)
        expect(PA_ITEM.PASTE.id).to_be(2424)
        expect(PA_ITEM.BEER.id).to_be(1917)
        expect(PA_ITEM.POT_OF_FLOUR.id).to_be(1933)
        expect(PA_ITEM.LOGS.id).to_be(1511)
        expect(PA_ITEM.COINS.id).to_be(995)
        expect(PA_ITEM.SOFT_CLAY.id).to_be(1761)
        expect(PA_ITEM.CLAY.id).to_be(434)
    test('ids match the engine obj.pack', _fn18)
describe('item identity', _fn16)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/piratestreasure-journal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.piratestreasure.journal import parse_pirates_treasure_journal
from rs2004.quests.defs.piratestreasure.areas import PT_STAGE
NOT_STARTED = "@dbl@I can start this quest by speaking to @dre@Redbeard Frank@dbl@ who is at @dre@Port Sarim@dbl@.||@dbl@There aren't any requirements for this quest."
STARTED = '@dbl@I have spoken to @dre@Redbeard Frank@dbl@. He has agreed to tell me the location of some @dre@treasure@dbl@ for some @dre@Karamja Rum@dbl@.||'
PLANTATION = '@dbl@I have taken employment on the @dre@banana plantation@dbl@, as the @dre@Customs Officers@dbl@ might not notice the @dre@rum@dbl@ if it is covered in @dre@bananas@dbl@.||'
SHIPPED_HISTORY = '@str@I have taken employment on the banana plantation, as the|@str@Customs Officers might not notice the rum if it is covered in|@str@bananas.||@str@I have hidden my rum in the crate. I should fill it with|@str@bananas and speak to Luthas to have it shipped over.||'
STORE_HISTORY = SHIPPED_HISTORY + "@str@I have spoken to Luthas, and the crate has been shipped to|@str@to Wydin's store in Port Sarim. Now all I have to do is|@str@get to it.||"
KEY_HISTORY = "@str@I have spoken to Redbeard Frank. He has agreed to tell me|@str@the location of some treasure for some Karamja Rum.||@str@I have smuggled some rum off Karamja, and retrieved it|@str@from the back room of Wydin's shop.||@dbl@I have given the rum to @dre@Redbeard Frank@dbl@. He has told me that the @dre@treasure@dbl@ is hidden in the chest in the upstairs room of the @dre@Blue Moon Inn@dbl@ in @dre@Varrock@dbl@.||"
NOTE_HISTORY = "@str@I have spoken to Redbeard Frank. He has agreed to tell me|@str@the location of some treasure for some Karamja Rum.||@str@I have smuggled some rum off Karamja, and retrieved it|@str@from the back room of Wydin's shop.||@str@I have given the rum to Redbeard Frank. He has told me|@str@that the treasure is hidden in the chest in the upstairs|@str@room of the Blue Moon Inn in Varrock.||@str@I have opened the chest in the Blue Moon, and found a|@str@note inside. I think it will tell me where to dig.||"

def flag(text):
    progress = parse_pirates_treasure_journal(text)
    return list(progress.flags)[0] if progress else None

def _fn1():

    def _fn2():
        expect(parse_pirates_treasure_journal(NOT_STARTED).stage if parse_pirates_treasure_journal(NOT_STARTED) is not None else None).to_be(PT_STAGE.NOT_STARTED)
    test('not started', _fn2)

    def _fn3():
        expect(parse_pirates_treasure_journal(STARTED + '@dbl@I need to go to @dre@Karamja@dbl@ and buy some @dre@rum@dbl@. I hope it is not too expensive.').stage if parse_pirates_treasure_journal(STARTED + '@dbl@I need to go to @dre@Karamja@dbl@ and buy some @dre@rum@dbl@. I hope it is not too expensive.') is not None else None).to_be(PT_STAGE.FETCH_RUM)
    test('fetch rum', _fn3)

    def _fn4():
        expect(parse_pirates_treasure_journal(KEY_HISTORY + '@dbl@I have a @dre@key@dbl@ that can be used to unlock the chest that hold the treasure.').stage if parse_pirates_treasure_journal(KEY_HISTORY + '@dbl@I have a @dre@key@dbl@ that can be used to unlock the chest that hold the treasure.') is not None else None).to_be(PT_STAGE.RECEIVED_KEY)
    test('received key', _fn4)

    def _fn5():
        expect(parse_pirates_treasure_journal(NOTE_HISTORY + "@dbl@The note reads @dre@'Visit the city of the White Knights. In the park, Saradomin points to the X which marks the spot.'").stage if parse_pirates_treasure_journal(NOTE_HISTORY + "@dbl@The note reads @dre@'Visit the city of the White Knights. In the park, Saradomin points to the X which marks the spot.'") is not None else None).to_be(PT_STAGE.READ_NOTE)
    test('read note outranks the key history it keeps', _fn5)

    def _fn6():
        expect(parse_pirates_treasure_journal(NOTE_HISTORY + "@str@The note reads 'Visit the city of the White Knights. In the|@str@park, Saradomin points to the X which marks the spot.'||@red@QUEST COMPLETE!").stage if parse_pirates_treasure_journal(NOTE_HISTORY + "@str@The note reads 'Visit the city of the White Knights. In the|@str@park, Saradomin points to the X which marks the spot.'||@red@QUEST COMPLETE!") is not None else None).to_be(PT_STAGE.COMPLETE)
    test('complete outranks the note history it keeps', _fn6)

    def _fn7():
        expect(parse_pirates_treasure_journal('')).to_be_undefined()
    test('an unparseable page is undefined, not stage 0', _fn7)
describe('pirate journal — stages', _fn1)

def _fn8():

    def _fn9():
        expect(flag(STARTED + '@dbl@I need to go to @dre@Karamja@dbl@ and buy some @dre@rum@dbl@. I hope it is not too expensive.')).to_be('need-rum')
    test('need rum', _fn9)

    def _fn10():
        expect(flag(STARTED + '@dbl@I have the @dre@rum@dbl@, and now I need to find a way to get the rum off @dre@Karamja@dbl@. This might be tricky, as the @dre@Customs Officers|@dbl@are searching people for it.')).to_be('rum-held-unemployed')
    test('rum held, not employed', _fn10)

    def _fn11():
        expect(flag(STARTED + PLANTATION + "@dbl@Now all I need is some @dre@rum@dbl@ to hide in the next crate destined for @dre@Wydin's store@dbl@.")).to_be('employed-need-rum')
    test('employed, no rum', _fn11)

    def _fn12():
        expect(flag(STARTED + PLANTATION + "@dbl@I'm sure I will be able to hide my @dre@rum@dbl@ in the next crate destined for @dre@Wydin's store@dbl@.")).to_be('rum-held-employed')
    test('employed, rum held', _fn12)

    def _fn13():
        expect(flag(STARTED + PLANTATION + '@dbl@I have hidden my @dre@rum@dbl@ in the crate. I should fill it with @dre@bananas@dbl@ and speak to @dre@Luthas@dbl@ and have it shipped over.')).to_be('rum-in-crate')
    test('rum in the crate, bananas outstanding', _fn13)

    def _fn14():
        expect(flag(STARTED + PLANTATION + '@dbl@I have hidden my @dre@rum@dbl@ in the crate and filled it with @dre@bananas@dbl@. I should speak to @dre@Luthas@dbl@ and have it shipped|@dbl@over.')).to_be('crate-full')
    test('crate full', _fn14)

    def _fn15():
        expect(flag(STARTED + SHIPPED_HISTORY + "@dbl@I have spoken to @dre@Luthas@dbl@, and the crate has been shipped to @dre@Wydin's store@dbl@ in @dre@Port Sarim@dbl@. Now all I have to do is get to it.")).to_be('rum-shipped')
    test('shipped outranks the fill-it history it keeps', _fn15)

    def _fn16():
        expect(flag(STARTED + STORE_HISTORY + "@dbl@I have taken a job at @dre@Wydin's store@dbl@. I now have access to the back room of his shop where the @dre@rum@dbl@ is hidden.")).to_be('store-job')
    test('store job outranks the shipped history it keeps', _fn16)

    def _fn17():
        expect(flag(STARTED + '@dbl@I have the @dre@Karamja Rum@dbl@. I should take it to @dre@Redbeard Frank@dbl@.')).to_be('rum-in-hand')
    test('rum in hand', _fn17)

    def _fn18():
        expect(flag(STARTED + '@dbl@I had some @dre@rum@dbl@, but I seem to have lost it. I will need to smuggle some more off @dre@Karamja@dbl@.')).to_be('rum-lost')
    test('rum lost', _fn18)

    def _fn19():
        expect(len(parse_pirates_treasure_journal(KEY_HISTORY + '@dbl@I have a @dre@key@dbl@ that can be used to unlock the chest that hold the treasure.').flags if parse_pirates_treasure_journal(KEY_HISTORY + '@dbl@I have a @dre@key@dbl@ that can be used to unlock the chest that hold the treasure.') is not None else None)).to_be(0)
    test('only stage 1 carries a smuggle flag', _fn19)
describe('pirate journal — smuggle sub-state', _fn8)

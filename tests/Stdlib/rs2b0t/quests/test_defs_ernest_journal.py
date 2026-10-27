"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/ernest-journal.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.ernest.areas import EC_STAGE
from rs2004.quests.defs.ernest.journal import parse_ernest_journal
NOT_STARTED = "@dbl@I can start this quest by speaking to @dre@Veronica@dbl@ who is outside @dre@Draynor Manor||@dbl@There aren't any requirements for this quest"
STARTED = "@str@I have spoken to Veronica||@dbl@I need to find @dre@Ernest|@dbl@He went into @dre@Draynor Manor@dbl@ and hasn't returned"
SPOKEN = "@str@I have spoken to Veronica||@str@I've spoken to Dr Oddenstein, and discovered Ernest is a|@str@chicken||@dbl@I need to bring @dre@Dr Oddenstein@dbl@ parts for his machine|@dre@1 Oil Can|@dre@1 Pressure Gauge|@dre@1 Rubber Tube"
COMPLETE = '@str@I have spoken to Veronica||@str@I have collected all the parts for the machine||@str@Dr Oddenstein thanked me for helping fix his machine|@str@We turned Ernest back to normal and he rewarded me|@red@QUEST COMPLETE!'

def _fn1():

    def _fn2():
        expect(parse_ernest_journal(NOT_STARTED).stage if parse_ernest_journal(NOT_STARTED) is not None else None).to_be(EC_STAGE.NOT_STARTED)
        expect(parse_ernest_journal(STARTED).stage if parse_ernest_journal(STARTED) is not None else None).to_be(EC_STAGE.STARTED)
        expect(parse_ernest_journal(SPOKEN).stage if parse_ernest_journal(SPOKEN) is not None else None).to_be(EC_STAGE.SPOKEN_ODDENSTEIN)
        expect(parse_ernest_journal(COMPLETE).stage if parse_ernest_journal(COMPLETE) is not None else None).to_be(EC_STAGE.COMPLETE)
    test('reads every stage the engine can render', _fn2)

    def _fn3():
        expect(parse_ernest_journal(SPOKEN.split('|')).stage if parse_ernest_journal(SPOKEN.split('|')) is not None else None).to_be(EC_STAGE.SPOKEN_ODDENSTEIN)
    test('accepts the line array the client actually hands over', _fn3)

    def _fn4():
        all_held = SPOKEN.replace('@dre@', '@str@')
        expect(parse_ernest_journal(all_held).stage if parse_ernest_journal(all_held) is not None else None).to_be(EC_STAGE.SPOKEN_ODDENSTEIN)
    test('the stage-2 needle survives the parts checklist flipping to green', _fn4)

    def _fn5():
        expect(parse_ernest_journal('@dbl@I can start this quest by talking to the @dre@Squire')).to_be_undefined()
    test('returns undefined for text from another quest', _fn5)
describe('Ernest the Chicken journal', _fn1)

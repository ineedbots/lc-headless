"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/piratestreasure-crate.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.piratestreasure.crate import read_crate_messages

def _fn1():

    def _fn2():
        expect(read_crate_messages(['The crate is completely empty.'])).to_equal(Fake(**{'rum': False, 'bananas': 0}))
    test('completely empty', _fn2)

    def _fn3():
        expect(read_crate_messages(['There is some rum in here, although with no bananas to cover it.', 'It is a little obvious.'])).to_equal(Fake(**{'rum': True, 'bananas': 0}))
    test('rum alone', _fn3)

    def _fn4():
        expect(read_crate_messages(['The crate has 1 banana inside.'])).to_equal(Fake(**{'rum': False, 'bananas': 1}))
    test('one banana is singular', _fn4)

    def _fn5():
        expect(read_crate_messages(['The crate has 7 bananas inside.', 'There is also some rum stashed in here too.'])).to_equal(Fake(**{'rum': True, 'bananas': 7}))
    test('several bananas and the rum', _fn5)

    def _fn6():
        expect(read_crate_messages(['The crate is full of bananas.', 'There is also some rum stashed in here too.'])).to_equal(Fake(**{'rum': True, 'bananas': 10}))
    test('full reads as ten without a number in the line', _fn6)

    def _fn7():
        expect(read_crate_messages(['You pick a banana.'])).to_be_null()
    test('unrelated chatter is not a crate reading', _fn7)
describe('banana crate messages', _fn1)

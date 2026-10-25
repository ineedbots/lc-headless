"""rs2b0t's test/api/ai/quests/engine/progress.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import flag_value, has_flag

def _fn1():
    def _fn2():
        progress = Record({'stage': 2, 'flags': set(['helped-og'])})
        expect(has_flag(progress, 'helped-og')).to_be(True)
        expect(has_flag(progress, 'helped-grew')).to_be(False)
    test('hasFlag finds a set flag and misses an unset one', _fn2)

    def _fn3():
        expect(has_flag(None, 'helped-og')).to_be(False)
    test('hasFlag on an absent progress is false, never a throw', _fn3)

    def _fn4():
        progress = Record({'stage': 10, 'flags': set(['shamans-left:4'])})
        expect(flag_value(progress, 'shamans-left')).to_be(4)
    test('flagValue reads the numeric tail of a "name:N" flag', _fn4)

    def _fn5():
        progress = Record({'stage': 10, 'flags': set()})
        expect(flag_value(progress, 'shamans-left')).to_be_undefined()
    test('flagValue is undefined when the flag is absent', _fn5)

    def _fn6():
        progress = Record({'stage': 10, 'flags': set(['shamans-left:0'])})
        expect(flag_value(progress, 'shamans-left')).to_be(0)
    test('flagValue reads zero, which must not be confused with absent', _fn6)


describe('quest progress flags', _fn1)

"""Ported from rs2b0t's test/api/ai/quests/upassVerdict.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.messages import game_messages
from rs2004.quests.defs.upass.verdict import verdict_since

# Why: obstacle messages settle the attempt immediately instead of paying the full timeout.
heard = []


def say(*lines):
    mark = len(heard)
    heard.extend(lines)
    return mark


def _listen():
    heard.clear()
    spy_on(game_messages, 'mark', impl=lambda: len(heard))
    spy_on(game_messages, 'since', impl=lambda mark: [Fake(text=text) for text in heard[mark:]])


before_each(_listen)


def _fn1():
    def _fn2():
        expect(verdict_since(game_messages.mark())).to_be_null()
    test('is nothing before the script has spoken', _fn2)

    def _fn3():
        expect(verdict_since(say('You climb onto the rock...', '...and step down the other side.'))).to_be('crossing')
    test('reads a rockslide that carried the character as a crossing', _fn3)

    def _fn4():
        expect(verdict_since(say('You climb onto the rock...', '...but you slip back down.'))).to_be('failed')
    test('reads a rockslide that slipped as a failed roll, which is worth another try', _fn4)

    def _fn5():
        expect(verdict_since(say('You attempt to pick the lock...', 'You manage to pick the lock.', 'You walk through.', 'The cage slams shut behind you.'))).to_be('crossing')
    test('reads a cage that opened as a crossing', _fn5)

    def _fn6():
        expect(verdict_since(say('You attempt to pick the lock...', 'You fail to pick the lock.'))).to_be('failed')
    test('reads a cage that did not as a failed roll', _fn6)

    def _fn7():
        expect(verdict_since(say("You can't do that from here."))).to_be('refused')
        expect(verdict_since(say('You cannot do that from here.'))).to_be('refused')
    test('reads the server refusing the side as refused, in both spellings the pass uses', _fn7)

    def _fn8():
        expect(verdict_since(say("I can't reach that!"))).to_be('refused')
    test('reads a path that dead-ended as refused', _fn8)

    def _fn9():
        expect(verdict_since(say('The pipe is being used'))).to_be('refused')
        expect(verdict_since(say('The rock is being used.'))).to_be('refused')
        expect(verdict_since(say('The rope swing is being used'))).to_be('refused')
    test('reads every cooldown the pass has as refused, so no retry waits one out', _fn9)

    def _fn10():
        expect(verdict_since(say('The other end of the pipe is blocked by a grill.', 'You cannot open the grill from this side.'))).to_be('refused')
    test('reads the grilled end of the first pipe as refused', _fn10)

    def _fn11():
        expect(verdict_since(say('You need a Thieving level of 50 to pick this lock.'))).to_be('refused')
    test('reads a thieving gate as refused rather than as a roll to repeat', _fn11)

    def _fn12():
        expect(verdict_since(say('You climb onto the rock...', '...but you slip back down.', 'You climb onto the rock...', '...and step down the other side.'))).to_be('crossing')
    test('takes the LAST verdict, so a roll that failed and then landed reads as a crossing', _fn12)

    def _fn13():
        say('...and step down the other side.')
        expect(verdict_since(game_messages.mark())).to_be_null()
    test('ignores anything said before the mark', _fn13)

    def _fn14():
        expect(verdict_since(say('You fall in to the rat pit.'))).to_be('failed')
        expect(verdict_since(say('...and fall off it.'))).to_be('failed')
        expect(verdict_since(say('...and make it.'))).to_be('crossing')
        expect(verdict_since(say('... but you slip and tumble into the darkness.'))).to_be('failed')
        expect(verdict_since(say('... you manage to cross safely.'))).to_be('crossing')
        expect(verdict_since(say('You try to swing but fall in to the darkness.'))).to_be('failed')
        expect(verdict_since(say('You skillfully swing across.'))).to_be('crossing')
        expect(verdict_since(say('You crawl through the pipe.'))).to_be('crossing')
    test('reads the ledge, the bridges, the swing and the pipes', _fn14)


describe('what the chatbox says an obstacle did', _fn1)


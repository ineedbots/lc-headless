"""rs2b0t's test/event/webwalk/questLock.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.routeplan import is_quest_lock_dialogue, is_quest_lock_text



def _fn1():
    def _fn2():
        expect(is_quest_lock_text('The door is locked.')).to_be(True)
        expect(is_quest_lock_text('You need a key to open this door.')).to_be(True)
        expect(is_quest_lock_text("You can't open this door.")).to_be(True)
        expect(is_quest_lock_text('Members only area.')).to_be(True)
        expect(is_quest_lock_text('You must complete the quest first.')).to_be(True)
        expect(is_quest_lock_text('Hello, traveller.')).to_be(False)
        expect(is_quest_lock_text('Yes, ok.')).to_be(False)
    test('matches common lock phrases', _fn2)

    def _fn3():
        expect(is_quest_lock_dialogue(['Ulizius looks at you.', 'The gate is locked.'])).to_be(True)
        expect(is_quest_lock_dialogue(['How can I help you?'])).to_be(False)
    test('any line in chat modal', _fn3)


describe('quest lock dialogue', _fn1)

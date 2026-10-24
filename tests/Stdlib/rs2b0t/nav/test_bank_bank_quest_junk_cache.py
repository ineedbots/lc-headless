"""rs2b0t's test/api/bank/bankQuestJunk.test.ts (MIT, see thirdparty/rs2b0t), its content-pack half: there it
reads the content's obj.pack and .obj names, here the real cache's. On spec.py's describe, test and expect."""

from rs2004.banksort import QUEST_JUNK


def _fn1():
    def _fn2():
        for item in QUEST_JUNK:
            kind = reader.item_type(item.id)
            expect(kind is not None, f'#{item.id}').to_be(True)
            # Noted forms and the ice arrows' dummy stacks are left off the list.
            expect(kind.note_of is None, f'#{item.id} is noted').to_be(True)
            expect(kind.name, f'#{item.id}').to_be(item.name)
    test('every id and display name matches the cache', _fn2)


describe('QUEST_JUNK against the cache', _fn1)

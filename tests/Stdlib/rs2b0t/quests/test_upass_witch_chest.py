"""Ported from rs2b0t's test/api/ai/quests/upassWitchChest.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.upass.areas import UP_LOC
from rs2004.quests.defs.upass.chest import CHEST_FORMS, chest_form

# Why: the chest changes from loc 3272 `Open` to loc 3273 `Search` for 20 ticks; both run the same script.
def in_scene(*ids):
    return lambda id, op: (id in ids) and ((op == 'Open' if id == UP_LOC.WITCH_CHEST else op == 'Search'))


def _fn1():
    def _fn2():
        expect(chest_form(in_scene(UP_LOC.WITCH_CHEST))).to_equal(Record({'id': UP_LOC.WITCH_CHEST, 'op': 'Open'}))
    test('takes the closed chest with Open when it is the one standing there', _fn2)

    def _fn3():
        expect(chest_form(in_scene(UP_LOC.WITCH_CHEST_OPEN))).to_equal(Record({'id': UP_LOC.WITCH_CHEST_OPEN, 'op': 'Search'}))
    test('takes the open chest with Search while the loc_change is still up', _fn3)

    def _fn4():
        expect(chest_form(in_scene())).to_equal(Record({'id': UP_LOC.WITCH_CHEST, 'op': 'Open'}))
    test('falls back to the closed form when neither is in the scene, so the reach still walks', _fn4)

    def _fn5():
        expect(CHEST_FORMS).to_equal([
        Record({'id': UP_LOC.WITCH_CHEST, 'op': 'Open'}),
        Record({'id': UP_LOC.WITCH_CHEST_OPEN, 'op': 'Search'}),
    ])
    test('knows both forms and nothing else', _fn5)


describe('which chest to act on', _fn1)


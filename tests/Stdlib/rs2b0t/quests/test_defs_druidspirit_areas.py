"""rs2b0t's test/api/ai/quests/defs/druidspirit-areas.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.druidspirit.areas import NS_ID, NS_STAGE, NS_TILE, in_camp, in_grotto, in_swamp

def _fn1():
    def _fn2():
        expect(in_swamp(Record({'x': 3440, 'z': 3336, 'level': 0}))).to_be(True)
        expect(in_swamp(Record({'x': 3392, 'z': 3328, 'level': 0}))).to_be(True)
        expect(in_swamp(Record({'x': 3519, 'z': 3455, 'level': 0}))).to_be(True)
        expect(in_swamp(Record({'x': 3391, 'z': 3336, 'level': 0}))).to_be(False)
        expect(in_swamp(Record({'x': 3440, 'z': 3456, 'level': 0}))).to_be(False)
        expect(in_swamp(Record({'x': 3440, 'z': 3336, 'level': 1}))).to_be(False)
    test('the swamp zone matches the inzone bounds the scripts use', _fn2)

    def _fn3():
        expect(in_camp(Record({'x': 3440, 'z': 3336, 'level': 0}))).to_be(True)
        expect(in_camp(Record({'x': 3434, 'z': 3330, 'level': 0}))).to_be(True)
        expect(in_camp(Record({'x': 3448, 'z': 3344, 'level': 0}))).to_be(True)
        expect(in_camp(Record({'x': 3433, 'z': 3336, 'level': 0}))).to_be(False)
        expect(in_camp(Record({'x': 3440, 'z': 3345, 'level': 0}))).to_be(False)
    test("Filliman's camp is the decay-free pocket inside the swamp", _fn3)

    def _fn4():
        expect(in_grotto(Record({'x': 3442, 'z': 9734, 'level': 0}))).to_be(True)
        expect(in_grotto(Record({'x': 3442, 'z': 9734, 'level': 1}))).to_be(True)
        expect(in_grotto(Record({'x': 3440, 'z': 3336, 'level': 0}))).to_be(False)
    test('the grotto is the sealed pocket under the camp, on either level', _fn4)

    def _fn5():
        expect(NS_ID.POUCH_EMPTY).to_be(2957)
        expect(NS_ID.POUCH).to_be(2958)
    test('the two druid pouches are separate ids under one display name', _fn5)

    def _fn6():
        expect(NS_TILE.FAITH_STONE.x).to_be(3440)
        expect(NS_TILE.FAITH_STONE.z).to_be(3335)
    test('the faith stone is the tile the ritual is judged from', _fn6)

    def _fn7():
        expect(NS_STAGE.STARTED).to_be(5)
        expect(NS_STAGE.BLESSED).to_be(40)
        expect(NS_STAGE.PERFORMED_RITUAL).to_be(60)
        expect(NS_STAGE.BLESSED_SICKLE).to_be(75)
        expect(NS_STAGE.ADDED_POUCH).to_be(90)
        expect(NS_STAGE.KILLED_GHAST3).to_be(105)
    test('stages match quest_druidspirit.constant', _fn7)


describe('nature spirit areas', _fn1)

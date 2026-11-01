"""rs2b0t's test/api/ai/quests/defs/mortton-supplies.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.mortton.areas import SM_ID, SM_STAGE
from rs2004.quests.defs.mortton.supplies import ashes_short, doses_needed, logs_short, serum_doses, serums_short

def pack(inv_ids=None):
    if inv_ids is None:
        inv_ids = []
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': {_k: _v for _k, _v in inv_ids},
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 0,
        'bank': {},
        'bank_ids': {},
        'bank_known': True,
        'tile': Record({'x': 3490, 'z': 3290, 'level': 0}),
        'free_slots': 20,
    })


def _fn1():
    def _fn2():
        expect(doses_needed(SM_STAGE.NOT_STARTED)).to_be(4)
        expect(doses_needed(SM_STAGE.READ_DIARY)).to_be(4)
    test('a fresh quest owes four conversations', _fn2)

    def _fn3():
        expect(doses_needed(SM_STAGE.KILL_SHADES)).to_be(3)
        expect(doses_needed(SM_STAGE.KILLED_5)).to_be(3)
        expect(doses_needed(SM_STAGE.SHADES_TO_RAZMIRE)).to_be(2)
        expect(doses_needed(SM_STAGE.ULSQUIRE_TEMPLE)).to_be(1)
        expect(doses_needed(SM_STAGE.LIT_PYRE)).to_be(1)
    test('each villager paid off drops one dose from the bill', _fn3)

    def _fn4():
        expect(serum_doses(pack([[SM_ID.SERUM4, 1], [SM_ID.SERUM1, 2]]))).to_be(6)
    test('doses are counted across every vial size', _fn4)

    def _fn5():
        expect(serums_short(pack(), SM_STAGE.READ_DIARY)).to_be(2)
    test('an empty pack at the start brews two vials, which is what the table funds', _fn5)

    def _fn6():
        expect(serums_short(pack([[SM_ID.SERUM3, 1]]), SM_STAGE.READ_DIARY)).to_be(1)
    test('one brewed vial still leaves one to brew', _fn6)

    def _fn7():
        expect(serums_short(pack([[SM_ID.SERUM3, 2]]), SM_STAGE.READ_DIARY)).to_be(0)
    test('two brewed vials cover the whole quest', _fn7)

    # Why: counting the unfinished potion as a vial stopped the chain on it and left the last conversation unpayable.
    def _fn8():
        expect(serums_short(pack([[SM_ID.SERUM3, 1], [SM_ID.TARROMIN_UNF, 1]]), SM_STAGE.READ_DIARY)).to_be(1)
    test('an unfinished potion is not a vial yet', _fn8)

    def _fn9():
        expect(serums_short(pack([[SM_ID.SERUM_PERM3, 1]]), SM_STAGE.LIT_PYRE)).to_be(0)
    test('a sanctified vial pays the last conversation', _fn9)

    def _fn10():
        expect(serums_short(pack(), SM_STAGE.LIT_PYRE)).to_be(1)
    test('a dry pack late in the quest brews one more', _fn10)


describe('serum dose accounting', _fn1)


def _fn11():
    def _fn12():
        expect(ashes_short(pack(), SM_STAGE.READ_DIARY)).to_be(2)
    test('two serums to brew means two burns', _fn12)

    def _fn13():
        expect(ashes_short(pack([[SM_ID.ASHES, 2]]), SM_STAGE.READ_DIARY)).to_be(0)
    test('ashes already held retire the burns', _fn13)

    def _fn14():
        expect(logs_short(pack(), SM_STAGE.READ_DIARY)).to_be(3)
        expect(logs_short(pack([[SM_ID.ASHES, 2]]), SM_STAGE.READ_DIARY)).to_be(1)
        expect(logs_short(pack([[SM_ID.ASHES, 2], [SM_ID.LOGS, 1]]), SM_STAGE.READ_DIARY)).to_be(0)
    test('the logs order is one per burn plus the pyre', _fn14)

    def _fn15():
        expect(logs_short(pack([[SM_ID.SERUM3, 2], [SM_ID.PYRE_LOGS, 1]]), SM_STAGE.CREATED_PYRE_LOGS)).to_be(0)
    test('a made pyre log retires the spare', _fn15)

    # Why: the log is on the pyre by then, and asking for another sent the bot back across the swamp for it.
    def _fn16():
        expect(logs_short(pack([[SM_ID.SERUM3, 2]]), SM_STAGE.LOGS_ON_PYRE)).to_be(0)
        expect(logs_short(pack([[SM_ID.SERUM3, 2]]), SM_STAGE.LIT_PYRE)).to_be(0)
    test('a stacked pyre retires the spare too', _fn16)


describe('ashes and logs', _fn11)

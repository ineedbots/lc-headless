"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-blackarm.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.shieldofarrav.blackarm import blackarm_step
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
ALLEY = Fake(**{'x': 3208, 'z': 3391, 'level': 0})
STORE_GROUND = Fake(**{'x': 3251, 'z': 3384, 'level': 0})
STORE_UPPER = Fake(**{'x': 3251, 'z': 3384, 'level': 1})

def at(stage, flags=None, ids=None, bank_ids=None, bank_known=True):
    if flags is None:
        flags = []
    if ids is None:
        ids = []
    if bank_ids is None:
        bank_ids = []
    return Fake(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': bank_known, 'tile': ALLEY, 'free_slots': 20, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set(flags)})})

def _fn1():

    def _fn2():
        expect(blackarm_step(at(SOA_STAGE.NOT_STARTED))).to_match_object(Fake(**{'kind': 'custom', 'name': 'ask the Tramp about the alley'}))
    test('an unstarted quest talks to the Tramp', _fn2)

    def _fn3():
        expect(blackarm_step(at(SOA_STAGE.TRAMP_TOLD))).to_match_object(Fake(**{'kind': 'custom', 'name': 'ask Katrine to join the Black Arm Gang'}))
    test('after the Tramp, Katrine is approached', _fn3)

    def _fn4():
        snap = at(SOA_STAGE.KATRINE_TASK, [], [[SOA_ID.CROSSBOW, 2]])
        snap.tile = STORE_GROUND
        expect(blackarm_step(snap)).to_match_object(Fake(**{'kind': 'custom', 'name': 'leave the weapon store'}))
    test('crossbows held inside the store pocket leave before the hand-in', _fn4)

    def _fn5():
        snap = at(SOA_STAGE.KATRINE_TASK, [], [[SOA_ID.CROSSBOW, 2]])
        snap.tile = STORE_UPPER
        expect(blackarm_step(snap)).to_match_object(Fake(**{'kind': 'custom', 'name': 'leave the weapon store'}))
    test('crossbows held upstairs in the store leave before the hand-in', _fn5)

    def _fn6():
        expect(blackarm_step(at(SOA_STAGE.KATRINE_TASK, [], [[SOA_ID.CROSSBOW, 2]]))).to_match_object(Fake(**{'name': 'hand the crossbows to Katrine'}))
    test('crossbows held outside the store hand in rather than leaving again', _fn6)

    def _fn7():
        step = blackarm_step(at(SOA_STAGE.KATRINE_TASK))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('key')
    test('without the store key the leg waits rather than walking at a locked door', _fn7)

    def _fn8():
        step = blackarm_step(at(SOA_STAGE.KATRINE_TASK, [], [], [[SOA_ID.STORE_KEY, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.STORE_KEY)
    test('a banked key is withdrawn rather than waited on', _fn8)

    def _fn9():
        step = blackarm_step(at(SOA_STAGE.KATRINE_TASK, [], [], [[SOA_ID.STORE_KEY, 1]], False))
        expect(step.kind).to_be('wait')
    test('an unread bank does not count as a banked key', _fn9)

    def _fn10():
        step = blackarm_step(at(SOA_STAGE.KATRINE_TASK, [], [[SOA_ID.STORE_KEY, 1]], [[SOA_ID.STORE_KEY, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom'}))
    test('a held key outranks a banked one', _fn10)

    def _fn11():
        expect(blackarm_step(at(SOA_STAGE.KATRINE_TASK, ['key-held'], [[SOA_ID.STORE_KEY, 1]]))).to_match_object(Fake(**{'kind': 'custom'}))
    test('with the store key the weapon store is raided', _fn11)

    def _fn12():
        expect(blackarm_step(at(SOA_STAGE.KATRINE_TASK, ['crossbows-held'], [[SOA_ID.CROSSBOW, 2]]))).to_match_object(Fake(**{'kind': 'custom', 'name': 'hand the crossbows to Katrine'}))
    test('two crossbows go back to Katrine', _fn12)

    def _fn13():
        half = at(SOA_STAGE.KATRINE_TASK, ['key-held'], [[SOA_ID.STORE_KEY, 1], [SOA_ID.CROSSBOW, 1]])
        expect(blackarm_step(half)).to_match_object(Fake(**{'kind': 'custom'}))
    test('one crossbow is not two — the raid continues', _fn13)

    def _fn14():
        both = at(SOA_STAGE.KATRINE_TASK, [], [[SOA_ID.STORE_KEY, 1], [SOA_ID.CROSSBOW, 2]])
        expect(blackarm_step(both)).to_match_object(Fake(**{'kind': 'custom', 'name': 'hand the crossbows to Katrine'}))
    test('crossbows outrank the key: a hand-in never re-enters the store', _fn14)

    def _fn15():
        expect(blackarm_step(at(SOA_STAGE.BLACKARM_JOINED))).to_match_object(Fake(**{'kind': 'custom'}))
    test('a joined member without the half searches the cupboard', _fn15)

    def _fn16():
        step = blackarm_step(at(SOA_STAGE.BLACKARM_JOINED, ['own-half-only'], [[SOA_ID.SHIELD_BLACKARM, 1]]))
        expect(step.kind).to_be('wait')
    test('a joined member holding the half asks for nothing more from this leg', _fn16)

    def _fn17():
        step = blackarm_step(at(SOA_STAGE.BLACKARM_JOINED, [], [], [[SOA_ID.SHIELD_BLACKARM, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.SHIELD_BLACKARM)
    test('a banked half is withdrawn, not searched for a second time', _fn17)

    def _fn18():
        step = blackarm_step(at(SOA_STAGE.BLACKARM_JOINED, [], [[SOA_ID.SHIELD_BLACKARM, 1]], [[SOA_ID.SHIELD_BLACKARM, 1]]))
        expect(step.kind).to_be('wait')
    test('a held half stops the withdraw even while the bank read still shows one', _fn18)

    def _fn19():
        step = blackarm_step(at(SOA_STAGE.KILL_JONNY))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('black arm leg')
    test('a phoenix stage is not this leg and says so', _fn19)
describe('black arm leg', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

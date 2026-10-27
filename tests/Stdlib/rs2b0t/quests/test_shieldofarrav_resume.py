"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-resume.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav import decide, reset_gang_cache
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
VARROCK = Fake(**{'x': 3210, 'z': 3490, 'level': 0})
PHOENIX_STATES = [['not started', SOA_STAGE.NOT_STARTED, [], []], ['told of the book', SOA_STAGE.TOLD_OF_BOOK, [], []], ['book in the pack', SOA_STAGE.TOLD_OF_BOOK, [], [[SOA_ID.BOOK, 1]]], ['book read', SOA_STAGE.READ_BOOK, [], [[SOA_ID.BOOK, 1]]], ['sent to Baraek, broke', SOA_STAGE.SENT_TO_BARAEK, [], []], ['sent to Baraek, funded', SOA_STAGE.SENT_TO_BARAEK, [], [[SOA_ID.COINS, 500]]], ['hideout located', SOA_STAGE.FIND_STRAVEN, [], [[SOA_ID.COINS, 480]]], ['mission set, no report', SOA_STAGE.KILL_JONNY, [], []], ['report held', SOA_STAGE.KILL_JONNY, ['report-held'], [[SOA_ID.REPORT, 1]]], ['joined, empty handed', SOA_STAGE.PHOENIX_JOINED, [], [[SOA_ID.STORE_KEY, 1]]], ['joined, own half', SOA_STAGE.PHOENIX_JOINED, ['own-half-only'], [[SOA_ID.SHIELD_PHOENIX, 1]]], ['joined, both halves', SOA_STAGE.PHOENIX_JOINED, ['both-halves'], [[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.SHIELD_BLACKARM, 1]]], ['joined, two certificates', SOA_STAGE.PHOENIX_JOINED, ['two-certificates'], [[SOA_ID.CERTIFICATE, 2]]], ['joined, one certificate', SOA_STAGE.PHOENIX_JOINED, ['certificate'], [[SOA_ID.CERTIFICATE, 1]]]]
BLACKARM_STATES = [['not started', SOA_STAGE.NOT_STARTED, [], []], ['tramp told', SOA_STAGE.TRAMP_TOLD, [], []], ['task set, key held', SOA_STAGE.KATRINE_TASK, ['key-held'], [[SOA_ID.STORE_KEY, 1]]], ['task set, one crossbow', SOA_STAGE.KATRINE_TASK, ['key-held'], [[SOA_ID.STORE_KEY, 1], [SOA_ID.CROSSBOW, 1]]], ['task set, both crossbows', SOA_STAGE.KATRINE_TASK, ['crossbows-held'], [[SOA_ID.CROSSBOW, 2]]], ['joined, empty handed', SOA_STAGE.BLACKARM_JOINED, [], []], ['joined, own half', SOA_STAGE.BLACKARM_JOINED, ['own-half-only'], [[SOA_ID.SHIELD_BLACKARM, 1]]], ['joined, one certificate', SOA_STAGE.BLACKARM_JOINED, ['certificate'], [[SOA_ID.CERTIFICATE, 1]]]]

def snap(stage, flags, ids):
    return snapshot_fields(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {}, 'bank_ids': {}, 'bank_known': True, 'tile': VARROCK, 'free_slots': 20, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set(flags)})})

def stalled(states):
    return [label for label, stage, flags, ids in states if decide(snap(stage, flags, ids)).kind == 'wait']

def _fn3():
    arrav_config.gang = 'random'
    arrav_config.partner = ''
    arrav_config.cert_target = 2
    reset_gang_cache()
after_each(_fn3)

def _fn4():

    def _fn5():
        arrav_config.gang = 'phoenix'
        arrav_config.partner = 'Partner'
        reset_gang_cache()
        expect(stalled(PHOENIX_STATES)).to_equal([])
    test('the phoenix path never stalls when a partner is configured', _fn5)

    def _fn6():
        arrav_config.gang = 'blackarm'
        arrav_config.partner = 'Partner'
        reset_gang_cache()
        expect(stalled(BLACKARM_STATES)).to_equal([])
    test('the black arm path never stalls when a partner is configured', _fn6)

    def _fn7():
        arrav_config.gang = 'phoenix'
        arrav_config.partner = ''
        reset_gang_cache()
        up_to_own_half = [row for row in PHOENIX_STATES if row[0] != 'joined, own half']
        expect(stalled(up_to_own_half)).to_equal([])
    test('a partnerless phoenix bot runs its whole path unaided, up to holding its own half', _fn7)

    def _fn9():
        arrav_config.gang = 'phoenix'
        arrav_config.partner = ''
        reset_gang_cache()
        step = decide(snap(SOA_STAGE.PHOENIX_JOINED, ['own-half-only'], [[SOA_ID.SHIELD_PHOENIX, 1]]))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('half')
    test('a partnerless phoenix bot holding its own half says what it is missing', _fn9)

    def _fn10():
        arrav_config.gang = 'blackarm'
        arrav_config.partner = ''
        reset_gang_cache()
        step = decide(snap(SOA_STAGE.KATRINE_TASK, [], []))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('key')
    test('a partnerless black arm bot on the crossbow task says why it is stuck', _fn10)

    def _fn11():
        arrav_config.gang = 'phoenix'
        arrav_config.partner = ''
        reset_gang_cache()
        s = snap(SOA_STAGE.PHOENIX_JOINED, [], [])
        s.bank_ids = {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.STORE_KEY, 1]]}
        step = decide(s)
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.SHIELD_PHOENIX)
    test('a phoenix bot whose half was swept into the bank withdraws it rather than re-searching', _fn11)

    def _fn12():
        arrav_config.gang = 'blackarm'
        arrav_config.partner = ''
        reset_gang_cache()
        s = snap(SOA_STAGE.BLACKARM_JOINED, [], [])
        s.bank_ids = {_k: _v for _k, _v in [[SOA_ID.SHIELD_BLACKARM, 1]]}
        expect(decide(s)).to_match_object(Fake(**{'kind': 'withdraw'}))
    test('a black arm bot whose half was swept into the bank withdraws it too', _fn12)

    def _fn13():
        arrav_config.gang = 'phoenix'
        arrav_config.partner = ''
        reset_gang_cache()
        s = snap(SOA_STAGE.PHOENIX_JOINED, [], [])
        s.bank_ids = {_k: _v for _k, _v in [[SOA_ID.CERTIFICATE, 2]]}
        expect(decide(s)).to_match_object(Fake(**{'kind': 'withdraw'}))
    test('a banked certificate lets a partnerless bot finish', _fn13)

    def _fn14():
        arrav_config.gang = 'phoenix'
        reset_gang_cache()
        for _, stage, flags, ids in PHOENIX_STATES:
            s = snap(stage, flags, ids)
            s.journal = 'complete'
            expect(decide(s)).to_match_object(Fake(**{'kind': 'done'}))
    test('a complete journal is done from any inventory', _fn14)

    def _fn15():
        arrav_config.gang = 'random'
        arrav_config.partner = 'Partner'
        reset_gang_cache()
        first = decide(snap(SOA_STAGE.NOT_STARTED, [], []))
        for i in range(10):
            expect(decide(snap(SOA_STAGE.NOT_STARTED, [], []))).to_match_object(Fake(**{'kind': first.kind}))
    test('a random gang is stable across every state in one run', _fn15)
describe('shield of arrav resumes from every reachable state', _fn4)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.data import QUESTS
from rs2004.quests.defs import QUEST_DEFS, def_by_id
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav import decide, reset_gang_cache, shieldofarrav
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.data import QUESTS
from rs2004.quests.defs import QUEST_DEFS, def_by_id
VARROCK = Fake(**{'x': 3210, 'z': 3490, 'level': 0})

def snap(over=None):
    if over is None:
        over = Fake(**{})
    stage = over.stage if over.stage is not None else SOA_STAGE.NOT_STARTED
    _merged1 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': {}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {}, 'bank_ids': {}, 'bank_known': True, 'tile': VARROCK, 'free_slots': 20, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set()})}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged1[_k] = _v
    return snapshot_fields(**_merged1)

def with_gang(gang):
    arrav_config.gang = gang
    reset_gang_cache()

def _fn2():
    arrav_config.gang = 'random'
    arrav_config.partner = ''
    arrav_config.cert_target = 2
    reset_gang_cache()
after_each(_fn2)

def _fn3():

    def _fn4():
        expect(decide(snap(Fake(**{'journal': 'unknown'})))).to_match_object(Fake(**{'kind': 'wait'}))
    test('an unloaded journal waits rather than restarting a finished quest', _fn4)

    def _fn5():
        expect(decide(snap(Fake(**{'journal': 'complete'})))).to_match_object(Fake(**{'kind': 'done'}))
    test('a green journal is done', _fn5)

    def _fn6():
        expect(decide(snap(Fake(**{'stage': None, 'progress': None})))).to_match_object(Fake(**{'kind': 'wait'}))
    test('an unreadable stage waits', _fn6)

    def _fn7():
        with_gang('phoenix')
        expect(decide(snap(Fake(**{'bank_known': False})))).to_match_object(Fake(**{'kind': 'scan_bank'}))
    test('an unread bank is scanned before anything else is decided', _fn7)

    def _fn8():
        with_gang('phoenix')
        expect(decide(snap(Fake(**{'bank_known': True}))).kind).not_.to_be('scan_bank')
    test('the scan happens once — a read bank falls straight through to the quest', _fn8)

    def _fn9():
        with_gang('phoenix')
        s = snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.CERTIFICATE, 1]]}}))
        expect(decide(s)).to_match_object(Fake(**{'kind': 'custom'}))
    test('a held certificate outranks every gang leg', _fn9)

    def _fn10():
        with_gang('phoenix')
        arrav_config.partner = 'Someone'
        s = snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.SHIELD_BLACKARM, 1]]}}))
        expect(decide(s)).to_match_object(Fake(**{'kind': 'custom'}))
    test('both halves outrank a partner handoff', _fn10)

    def _fn11():
        with_gang('phoenix')
        arrav_config.partner = 'Someone'
        s = snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.STORE_KEY, 1]]}}))
        expect(decide(s)).to_match_object(Fake(**{'kind': 'custom'}))
    test('a handoff outranks the gang leg', _fn11)

    def _fn12():
        with_gang('phoenix')
        expect(decide(snap())).to_match_object(Fake(**{'kind': 'custom'}))
    test('the phoenix setting runs the phoenix leg', _fn12)

    def _fn13():
        with_gang('blackarm')
        expect(decide(snap())).to_match_object(Fake(**{'kind': 'custom'}))
    test('the black arm setting runs the black arm leg', _fn13)

    def _fn14():
        with_gang('phoenix')
        step = decide(snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1]]}})))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('partner')
    test('a partnerless phoenix member holding its half parks with the reason', _fn14)

    def _fn15():
        with_gang('blackarm')
        step = decide(snap(Fake(**{'stage': SOA_STAGE.BLACKARM_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.BLACKARM_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_BLACKARM, 1]]}})))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('partner')
    test('a partnerless black arm member parks the same way', _fn15)

    def _fn16():
        with_gang('phoenix')
        step = decide(snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'bank_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1]]}})))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.SHIELD_PHOENIX)
    test('a partnerless member recovers a banked half before it parks on it', _fn16)

    def _fn17():
        with_gang('phoenix')
        step = decide(snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1]]}, 'bank_ids': {_k: _v for _k, _v in [[SOA_ID.CERTIFICATE, 1]]}})))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
    test('a banked certificate is worth a solo run, so it redeems instead of parking', _fn17)

    def _fn18():
        with_gang('phoenix')
        arrav_config.partner = 'Someone'
        step = decide(snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()}), 'inv_ids': {_k: _v for _k, _v in [[SOA_ID.SHIELD_PHOENIX, 1]]}})))
        expect(step).to_match_object(Fake(**{'kind': 'custom'}))
    test('a configured partner keeps the gang leg running', _fn18)

    def _fn19():
        with_gang('phoenix')
        step = decide(snap(Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'progress': Fake(**{'stage': SOA_STAGE.PHOENIX_JOINED, 'flags': set()})})))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'search the Phoenix hideout chest'}))
    test('a partnerless member empty handed still fetches its own half', _fn19)

    def _fn20():
        expect([d.module() for d in QUEST_DEFS]).to_contain(shieldofarrav)
        expect(def_by_id('blackarmgang')).to_be(shieldofarrav)
    test('the module is registered and reachable by id', _fn20)

    def _fn21():
        expect(shieldofarrav.record).to_be(([r for r in QUESTS if r.id == 'blackarmgang'] or [None])[0])
        expect(shieldofarrav.record.name).to_be('Shield of Arrav')
        expect(shieldofarrav.record.quest_points).to_be(1)
    test('the record it claims is the one in the data table', _fn21)

    def _fn22():
        expect(shieldofarrav.owns_inventory).to_be(True)
        expect(shieldofarrav.tools).to_contain('coins')
    test('the module owns its inventory and keeps coins for the bribe', _fn22)

    def _fn23():
        for item in shieldofarrav.record.items:
            if item.kind == 'acquirable':
                expect(shieldofarrav.gather.get(item.name.lower())).to_be_defined()
    test('every acquirable record item has a gather entry', _fn23)

    def _fn24():
        arrav_config.partner = ''
        _fn25 = getattr(shieldofarrav, 'warn_readiness', None)
        expect(_fn25() if _fn25 is not None else None).to_contain('partner')
        arrav_config.partner = 'Someone'
        _fn26 = getattr(shieldofarrav, 'warn_readiness', None)
        expect(_fn26() if _fn26 is not None else None).to_be_null()
    test('a partnerless account is warned before it starts, not after it parks', _fn24)

    def _fn27():
        expect(len(shieldofarrav.hops) if shieldofarrav.hops is not None else None).to_be_greater_than(0)
        expect(any([h.arrive.z > 6400 for h in shieldofarrav.hops])).to_be(True)
        expect(any([h.stand.z > 6400 for h in shieldofarrav.hops])).to_be(True)
    test('the hops cover the hideout, which nothing walks into', _fn27)
describe('shield of arrav decide', _fn3)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

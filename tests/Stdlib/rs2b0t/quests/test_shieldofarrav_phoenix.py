"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-phoenix.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.defs.shieldofarrav.phoenix import phoenix_step
VARROCK = Fake(**{'x': 3210, 'z': 3490, 'level': 0})

def at(stage, flags=None, ids=None, bank_ids=None, bank_known=True):
    if flags is None:
        flags = []
    if ids is None:
        ids = []
    if bank_ids is None:
        bank_ids = []
    return Fake(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': bank_known, 'tile': VARROCK, 'free_slots': 20, 'stage': stage, 'progress': Fake(**{'stage': stage, 'flags': set(flags)})})

def _fn1():
    arrav_config.partner = ''
after_each(_fn1)

def _fn2():

    def _fn3():
        expect(phoenix_step(at(SOA_STAGE.NOT_STARTED))).to_match_object(Fake(**{'kind': 'custom', 'name': 'ask Reldo for a quest'}))
    test('an unstarted quest talks to Reldo', _fn3)

    def _fn4():
        expect(phoenix_step(at(SOA_STAGE.TOLD_OF_BOOK))).to_match_object(Fake(**{'kind': 'custom'}))
    test('the book is checked out of the quest bookcase', _fn4)

    def _fn5():
        expect(phoenix_step(at(SOA_STAGE.TOLD_OF_BOOK, [], [[SOA_ID.BOOK, 1]]))).to_match_object(Fake(**{'kind': 'custom'}))
    test('a held book is read rather than re-taken', _fn5)

    def _fn6():
        expect(phoenix_step(at(SOA_STAGE.READ_BOOK))).to_match_object(Fake(**{'kind': 'custom', 'name': 'ask Reldo for a quest'}))
    test('after reading, Reldo names Baraek', _fn6)

    def _fn7():
        expect(phoenix_step(at(SOA_STAGE.SENT_TO_BARAEK))).to_match_object(Fake(**{'kind': 'withdraw'}))
    test('the bribe is funded before Baraek is approached', _fn7)

    def _fn8():
        expect(phoenix_step(at(SOA_STAGE.SENT_TO_BARAEK, [], [[SOA_ID.COINS, 19]]))).to_match_object(Fake(**{'kind': 'withdraw'}))
    test('nineteen coins is not twenty', _fn8)

    def _fn9():
        expect(phoenix_step(at(SOA_STAGE.SENT_TO_BARAEK, [], [[SOA_ID.COINS, 500]]))).to_match_object(Fake(**{'kind': 'custom', 'name': 'bribe Baraek for the hideout'}))
    test('with the bribe in the pack Baraek is approached', _fn9)

    def _fn10():
        expect(phoenix_step(at(SOA_STAGE.FIND_STRAVEN, [], [[SOA_ID.COINS, 480]]))).to_match_object(Fake(**{'kind': 'custom', 'name': 'offer Straven your services'}))
    test('the located hideout sends the bot to Straven', _fn10)

    def _fn11():
        expect(phoenix_step(at(SOA_STAGE.KILL_JONNY))).to_match_object(Fake(**{'kind': 'custom'}))
    test('the mission stage kills Jonny while no report is held', _fn11)

    def _fn12():
        expect(phoenix_step(at(SOA_STAGE.KILL_JONNY, [], [[SOA_ID.REPORT, 1]]))).to_match_object(Fake(**{'kind': 'custom', 'name': 'hand the report to Straven'}))
    test('a held report is handed to Straven', _fn12)

    def _fn13():
        expect(phoenix_step(at(SOA_STAGE.KILL_JONNY, ['report-held']))).to_match_object(Fake(**{'kind': 'custom', 'name': 'hand the report to Straven'}))
    test('the journal flag alone is enough to hand in, before the pack has synced', _fn13)

    def _fn14():
        expect(phoenix_step(at(SOA_STAGE.PHOENIX_JOINED))).to_match_object(Fake(**{'kind': 'custom'}))
    test('a joined member without the half searches the chest', _fn14)

    def _fn15():
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, ['own-half-only'], [[SOA_ID.SHIELD_PHOENIX, 1]]))
        expect(step.kind).to_be('wait')
    test('a joined member holding the half asks for nothing more from this leg', _fn15)

    def _fn16():
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [], [[SOA_ID.SHIELD_PHOENIX, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.SHIELD_PHOENIX)
    test('a banked half is withdrawn, not searched for a second time', _fn16)

    def _fn17():
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [[SOA_ID.SHIELD_PHOENIX, 1]], [[SOA_ID.SHIELD_PHOENIX, 1]]))
        expect(step.kind).to_be('wait')
    test('a held half stops the withdraw even while the bank read still shows one', _fn17)

    def _fn18():
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [], [[SOA_ID.SHIELD_PHOENIX, 1]], False))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'search the Phoenix hideout chest'}))
    test('an unread bank searches the chest rather than a booth it never opened', _fn18)

    def _fn19():
        arrav_config.partner = 'Someone'
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [], [[SOA_ID.STORE_KEY, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.STORE_KEY)
    test('a banked store key is withdrawn for the partner who is owed it', _fn19)

    def _fn20():
        arrav_config.partner = 'Someone'
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [], [[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.STORE_KEY, 1]]))
        expect([i['id'] for i in step.items]).to_equal([SOA_ID.SHIELD_PHOENIX, SOA_ID.STORE_KEY])
    test('a banked half and a banked key come out on one trip', _fn20)

    def _fn21():
        step = phoenix_step(at(SOA_STAGE.PHOENIX_JOINED, [], [], [[SOA_ID.STORE_KEY, 1]]))
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'search the Phoenix hideout chest'}))
    test('a partnerless bot leaves the key where it is, since nothing it does needs one', _fn21)

    def _fn22():
        step = phoenix_step(at(SOA_STAGE.KATRINE_TASK))
        expect(step.kind).to_be('wait')
        expect(step.reason).to_contain('phoenix leg')
    test('a black arm stage is not this leg and says so', _fn22)
describe('phoenix leg', _fn2)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

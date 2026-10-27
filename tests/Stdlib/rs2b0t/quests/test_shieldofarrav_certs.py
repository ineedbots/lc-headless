"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-certs.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.areas import SOA_ID
from rs2004.quests.defs.shieldofarrav.certs import cert_step, certs_banked, certs_held, curator_step
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav.partner import arrav_handoff_state
VARROCK = Fake(**{'x': 3253, 'z': 3420, 'level': 0})

def snap(inv_ids=None, bank_ids=None, bank_known=True):
    if inv_ids is None:
        inv_ids = []
    if bank_ids is None:
        bank_ids = []
    return snapshot_fields(**{'journal': 'in_progress', 'inv': {}, 'inv_ids': {_k: _v for _k, _v in inv_ids}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {_k: _v for _k, _v in bank_ids}, 'bank_known': bank_known, 'tile': VARROCK, 'free_slots': 20})

def _fn1():
    arrav_config.cert_target = 2
    arrav_config.partner = ''
    arrav_handoff_state.gave_cert = False
after_each(_fn1)

def _fn2():

    def _fn3():
        s = snap([[SOA_ID.CERTIFICATE, 2]], [[SOA_ID.CERTIFICATE, 3]])
        expect(certs_held(s)).to_be(2)
        expect(certs_banked(s)).to_be(3)
    test('counts read inventory and bank by id', _fn3)

    def _fn4():
        s = snap([], [[SOA_ID.CERTIFICATE, 3]], False)
        expect(certs_banked(s)).to_be(0)
    test('an unread bank counts as zero, not as empty', _fn4)

    def _fn5():
        s = snap([[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.SHIELD_BLACKARM, 1]])
        expect(curator_step(s, 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
        expect(curator_step(s, 'blackarm')).to_match_object(Fake(**{'kind': 'custom'}))
    test('both halves go to the curator, whichever gang holds them', _fn5)

    def _fn6():
        s = snap([[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.SHIELD_BLACKARM, 1], [SOA_ID.CERTIFICATE, 1]])
        expect(curator_step(s, 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
    test('the curator is due even with a certificate already held', _fn6)

    def _fn7():
        s = snap([[SOA_ID.SHIELD_PHOENIX, 1]], [[SOA_ID.SHIELD_BLACKARM, 1]])
        step = curator_step(s, 'phoenix')
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect([i['id'] for i in step.items]).to_equal([SOA_ID.SHIELD_BLACKARM])
    test('a pair split between the pack and the bank is reunited before the curator', _fn7)

    def _fn8():
        s = snap([], [[SOA_ID.SHIELD_PHOENIX, 1], [SOA_ID.SHIELD_BLACKARM, 1]])
        step = curator_step(s, 'blackarm')
        expect(sorted([i['id'] for i in step.items])).to_equal(sorted([SOA_ID.SHIELD_PHOENIX, SOA_ID.SHIELD_BLACKARM]))
    test('a pair sitting entirely in the bank comes out on one trip', _fn8)

    def _fn9():
        s = snap([[SOA_ID.SHIELD_PHOENIX, 1]], [[SOA_ID.SHIELD_BLACKARM, 1]], False)
        expect(curator_step(s, 'phoenix')).to_be_null()
    test('an unread bank is not a banked half', _fn9)

    def _fn10():
        expect(curator_step(snap([[SOA_ID.SHIELD_PHOENIX, 1]]), 'phoenix')).to_be_null()
        expect(curator_step(snap([[SOA_ID.SHIELD_BLACKARM, 1]]), 'blackarm')).to_be_null()
    test('one half alone is never a curator trip', _fn10)

    def _fn11():
        arrav_config.cert_target = 10
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]]), 'blackarm')).to_match_object(Fake(**{'kind': 'custom'}))
    test('a black arm bot redeems a received certificate whatever the mint target', _fn11)

    def _fn12():
        arrav_config.cert_target = 10
        arrav_config.partner = 'Someone'
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]]), 'phoenix')).to_be_null()
    test('a phoenix bot mid-stockpile keeps farming rather than redeeming its last one', _fn12)

    def _fn13():
        arrav_config.cert_target = 10
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]]), 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
    test('a partnerless phoenix bot redeems what it has rather than stockpiling', _fn13)

    def _fn14():
        arrav_config.cert_target = 10
        step = cert_step(snap([], [[SOA_ID.CERTIFICATE, 1]]), 'phoenix')
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['qty']).to_be(1)
    test('a partnerless phoenix bot withdraws a banked certificate below target', _fn14)

    def _fn15():
        arrav_config.cert_target = 10
        arrav_handoff_state.gave_cert = True
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]], [[SOA_ID.CERTIFICATE, 4]]), 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
    test('a phoenix bot that has paid its partner stops minting whatever the total reads', _fn15)

    def _fn16():
        arrav_config.cert_target = 6
        arrav_config.partner = 'Someone'
        after_deposit = cert_step(snap([], [[SOA_ID.CERTIFICATE, 4]]), 'phoenix')
        expect(after_deposit).to_be_null()
    test('banking the surplus does not make the bot withdraw it straight back', _fn16)

    def _fn17():
        step = cert_step(snap([], [[SOA_ID.CERTIFICATE, 2]]), 'phoenix')
        expect(step).to_match_object(Fake(**{'kind': 'withdraw'}))
        expect(step.items[0]['id']).to_be(SOA_ID.CERTIFICATE)
    test('a banked certificate at target is withdrawn', _fn17)

    def _fn18():
        arrav_config.partner = 'Someone'
        arrav_config.cert_target = 6
        step = cert_step(snap([], [[SOA_ID.CERTIFICATE, 6]]), 'phoenix')
        expect(step.items[0]['qty']).to_be(2)
    test('a phoenix bot that still owes its partner withdraws two', _fn18)

    def _fn19():
        arrav_config.partner = 'Someone'
        arrav_config.cert_target = 6
        arrav_handoff_state.gave_cert = True
        step = cert_step(snap([], [[SOA_ID.CERTIFICATE, 6]]), 'phoenix')
        expect(step.items[0]['qty']).to_be(1)
    test('once the partner has been paid, one is enough', _fn19)

    def _fn20():
        step = cert_step(snap([], [[SOA_ID.CERTIFICATE, 6]]), 'phoenix')
        expect(step.items[0]['qty']).to_be(1)
    test('a partnerless bot withdraws one', _fn20)

    def _fn21():
        s = snap([[SOA_ID.CERTIFICATE, 1]], [[SOA_ID.CERTIFICATE, 1]])
        expect(cert_step(s, 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
    test('a held certificate at target is taken to the king', _fn21)

    def _fn22():
        arrav_config.cert_target = 10
        arrav_config.partner = 'Someone'
        step = cert_step(snap([[SOA_ID.CERTIFICATE, 2]]), 'phoenix')
        expect(step).to_match_object(Fake(**{'kind': 'deposit'}))
        expect(step.keep_ids).not_.to_contain(SOA_ID.CERTIFICATE)
    test('below target the surplus banks instead of being redeemed', _fn22)

    def _fn23():
        arrav_config.cert_target = 10
        arrav_config.partner = 'Someone'
        step = cert_step(snap([[SOA_ID.CERTIFICATE, 2]]), 'phoenix')
        expect(step.keep_ids).to_contain(SOA_ID.SHIELD_PHOENIX)
        expect(step.keep_ids).to_contain(SOA_ID.SHIELD_BLACKARM)
        expect(step.keep_ids).to_contain(SOA_ID.STORE_KEY)
        expect(step.keep_ids).to_contain(SOA_ID.COINS)
        expect(step.keep).to_contain('lobster')
    test('a banking deposit spares the halves, the key, coins and food', _fn23)

    def _fn24():
        arrav_config.cert_target = 10
        arrav_config.partner = 'Someone'
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]]), 'phoenix')).to_be_null()
    test('one certificate below target is left alone so the gang legs farm another half', _fn24)

    def _fn25():
        expect(cert_step(snap(), 'phoenix')).to_be_null()
    test('nothing certificate-shaped yields null so the gang legs run', _fn25)

    def _fn26():
        expect(cert_step(snap([[SOA_ID.SHIELD_PHOENIX, 1]]), 'phoenix')).to_be_null()
        expect(cert_step(snap([[SOA_ID.SHIELD_BLACKARM, 1]]), 'blackarm')).to_be_null()
    test('one half alone leaves the certificate step idle', _fn26)

    def _fn27():
        expect(cert_step(snap([], [[SOA_ID.CERTIFICATE, 5]], False), 'phoenix')).to_be_null()
    test('an unread bank does not send the bot to a booth for a certificate it never saw', _fn27)

    def _fn28():
        arrav_config.cert_target = 0
        expect(cert_step(snap([[SOA_ID.CERTIFICATE, 1]]), 'phoenix')).to_match_object(Fake(**{'kind': 'custom'}))
    test('a target below one is clamped, so a zero setting still redeems', _fn28)
describe('arrav certificates', _fn2)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/shieldofarrav-partner.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.defs.shieldofarrav.partner import decide_handoff

def input(over):
    _merged1 = {}
    for _k, _v in {'gang': 'phoenix', 'stage': SOA_STAGE.PHOENIX_JOINED, 'has_key': False, 'has_own_half': False, 'has_other_half': False, 'certs': 0, 'certs_held': 0, 'cert_target': 2, 'partner_configured': True, 'halves_given': 0, 'gave_cert': False}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged1[_k] = _v
    return Fake(**_merged1)

def _fn2():

    def _fn3():
        expect(decide_handoff(input(Fake(**{'partner_configured': False, 'has_key': True})))).to_be_null()
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.KATRINE_TASK, 'partner_configured': False})))).to_be_null()
    test('no partner means no handoff at all', _fn3)

    def _fn4():
        expect(decide_handoff(input(Fake(**{'has_key': True})))).to_be('give-key')
    test('a joined phoenix bot hands its spare key over', _fn4)

    def _fn5():
        expect(decide_handoff(input(Fake(**{'stage': SOA_STAGE.KILL_JONNY, 'has_key': True})))).to_be_null()
    test('a phoenix bot below the join has no key to give', _fn5)

    def _fn6():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.KATRINE_TASK})))).to_be('take-key')
    test('a keyless black arm bot on the crossbow task asks for one', _fn6)

    def _fn7():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.KATRINE_TASK, 'has_key': True})))).to_be_null()
    test('a black arm bot that already holds the key asks for nothing', _fn7)

    def _fn8():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.BLACKARM_JOINED, 'has_own_half': True})))).to_be('give-half')
    test('a black arm bot holding its half gives it to the minter', _fn8)

    def _fn9():
        expect(decide_handoff(input(Fake(**{'has_own_half': True})))).to_be('take-half')
    test('a phoenix bot holding only its own half waits to receive the other', _fn9)

    def _fn10():
        expect(decide_handoff(input(Fake(**{'has_own_half': True, 'has_other_half': True})))).to_be_null()
    test('a phoenix bot with both halves does not trade — it mints', _fn10)

    def _fn11():
        expect(decide_handoff(input(Fake(**{'certs': 2, 'certs_held': 2, 'cert_target': 2})))).to_be('give-cert')
    test('two certificates at target are split with the partner', _fn11)

    def _fn12():
        expect(decide_handoff(input(Fake(**{'certs': 6, 'certs_held': 0, 'cert_target': 6})))).to_be_null()
    test('a banked stockpile is not offerable, so no handoff is asked for', _fn12)

    def _fn13():
        expect(decide_handoff(input(Fake(**{'certs': 6, 'certs_held': 2, 'cert_target': 6, 'gave_cert': True})))).to_be_null()
    test('the split happens once', _fn13)

    def _fn14():
        expect(decide_handoff(input(Fake(**{'certs': 2, 'certs_held': 2, 'cert_target': 10})))).to_be_null()
    test('two certificates below target are not split yet', _fn14)

    def _fn15():
        expect(decide_handoff(input(Fake(**{'certs': 10, 'certs_held': 2, 'cert_target': 10})))).to_be('give-cert')
    test('ten certificates at a target of ten are split', _fn15)

    def _fn16():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.BLACKARM_JOINED, 'has_own_half': False, 'certs': 0, 'halves_given': 1})))).to_be('take-cert')
    test('a black arm bot that gave its half away collects a certificate', _fn16)

    def _fn17():
        stocking = Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.BLACKARM_JOINED, 'has_own_half': False, 'certs': 0, 'cert_target': 6})
        _merged18 = {}
        for _k, _v in (stocking._fields if isinstance(stocking, (Record, Fake)) else stocking).items():
            _merged18[_k] = _v
        for _k, _v in {'halves_given': 1}.items():
            _merged18[_k] = _v
        expect(decide_handoff(input(Fake(**_merged18)))).to_be_null()
        _merged19 = {}
        for _k, _v in (stocking._fields if isinstance(stocking, (Record, Fake)) else stocking).items():
            _merged19[_k] = _v
        for _k, _v in {'halves_given': 2}.items():
            _merged19[_k] = _v
        expect(decide_handoff(input(Fake(**_merged19)))).to_be_null()
        _merged20 = {}
        for _k, _v in (stocking._fields if isinstance(stocking, (Record, Fake)) else stocking).items():
            _merged20[_k] = _v
        for _k, _v in {'halves_given': 3}.items():
            _merged20[_k] = _v
        expect(decide_handoff(input(Fake(**_merged20)))).to_be('take-cert')
    test('a black arm bot keeps supplying halves until the target is covered', _fn17)

    def _fn21():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.BLACKARM_JOINED, 'has_own_half': False, 'certs': 0, 'halves_given': 0})))).to_be_null()
    test('a black arm bot that has never farmed a half is left to the cupboard leg', _fn21)

    def _fn22():
        expect(decide_handoff(input(Fake(**{'gang': 'blackarm', 'stage': SOA_STAGE.BLACKARM_JOINED, 'certs': 1})))).to_be_null()
    test('a black arm bot that already holds a certificate is done trading', _fn22)

    def _fn23():
        expect(decide_handoff(input(Fake(**{'stage': SOA_STAGE.COMPLETE, 'has_key': True})))).to_be_null()
    test('the key hand-over stops once the quest is complete', _fn23)
describe('arrav handoffs', _fn2)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

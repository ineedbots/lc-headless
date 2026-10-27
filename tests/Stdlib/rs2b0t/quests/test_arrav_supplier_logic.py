"""Ported from rs2b0t's src/bot/../../test/scripts/ArravSupplier/ArravSupplierLogic.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from bots.arravsupplier.logic import supplier_phase

def state(over=None):
    if over is None:
        over = Fake(**{})
    _merged1 = {}
    for _k, _v in {'in_black_arm': False, 'in_phoenix': False, 'has_key': False, 'has_report': False, 'crossbows': 0, 'phoenix_half': 0, 'blackarm_half': 0, 'certs_banked': 0, 'cert_target': 10}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged1[_k] = _v
    return Fake(**_merged1)

def dual(over=None):
    if over is None:
        over = Fake(**{})
    _merged2 = {}
    for _k, _v in {'in_black_arm': True, 'in_phoenix': True}.items():
        _merged2[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged2[_k] = _v
    return state(Fake(**_merged2))

def _fn3():

    def _fn4():
        expect(supplier_phase(state())).to_be('await-key')
    test('without a key it waits for one rather than walking at a locked door', _fn4)

    def _fn5():
        expect(supplier_phase(state(Fake(**{'has_key': True})))).to_be('raid-store')
    test('with a key and no crossbows it raids the store', _fn5)

    def _fn6():
        expect(supplier_phase(state(Fake(**{'has_key': True, 'crossbows': 1})))).to_be('raid-store')
    test('one crossbow is not two', _fn6)

    def _fn7():
        expect(supplier_phase(state(Fake(**{'has_key': True, 'crossbows': 2})))).to_be('join-blackarm')
    test('two crossbows go to Katrine', _fn7)

    def _fn8():
        expect(supplier_phase(state(Fake(**{'in_black_arm': True})))).to_be('kill-jonny')
    test('a black arm member with no report kills Jonny', _fn8)

    def _fn9():
        expect(supplier_phase(state(Fake(**{'in_black_arm': True, 'has_report': True})))).to_be('join-phoenix')
    test('a black arm member holding the report uses it on Straven', _fn9)

    def _fn10():
        expect(supplier_phase(dual())).to_be('take-phoenix-half')
    test('a dual-gang supplier below target farms the phoenix half first', _fn10)

    def _fn11():
        expect(supplier_phase(dual(Fake(**{'phoenix_half': 1})))).to_be('take-blackarm-half')
    test('holding the phoenix half it farms the black arm half', _fn11)

    def _fn12():
        expect(supplier_phase(dual(Fake(**{'phoenix_half': 1, 'blackarm_half': 1})))).to_be('mint')
    test('holding both halves it mints', _fn12)

    def _fn13():
        expect(supplier_phase(dual(Fake(**{'certs_banked': 10, 'cert_target': 10, 'phoenix_half': 1, 'blackarm_half': 1})))).to_be('done')
    test('at target it stops, even holding both halves', _fn13)

    def _fn14():
        expect(supplier_phase(dual(Fake(**{'certs_banked': 24, 'cert_target': 10})))).to_be('done')
    test('past target it stays done', _fn14)

    def _fn15():
        phases = set()
        for certs_banked in [0, 1, 5, 9, 10, 20]:
            for phoenix_half in [0, 1]:
                for blackarm_half in [0, 1]:
                    phases.add(supplier_phase(dual(Fake(**{'certs_banked': certs_banked, 'phoenix_half': phoenix_half, 'blackarm_half': blackarm_half}))))
        expect(sorted(list(phases))).to_equal(['done', 'mint', 'take-blackarm-half', 'take-phoenix-half'])
    test('it never reaches a redeem phase, at any stock level', _fn15)

    def _fn16():
        seen = []
        s = state(Fake(**{'cert_target': 2}))
        seen.append(supplier_phase(s))
        _merged17 = {}
        for _k, _v in (s._fields if isinstance(s, (Record, Fake)) else s).items():
            _merged17[_k] = _v
        for _k, _v in {'has_key': True}.items():
            _merged17[_k] = _v
        s = Fake(**_merged17)
        seen.append(supplier_phase(s))
        _merged18 = {}
        for _k, _v in (s._fields if isinstance(s, (Record, Fake)) else s).items():
            _merged18[_k] = _v
        for _k, _v in {'crossbows': 2}.items():
            _merged18[_k] = _v
        s = Fake(**_merged18)
        seen.append(supplier_phase(s))
        _merged19 = {}
        for _k, _v in (s._fields if isinstance(s, (Record, Fake)) else s).items():
            _merged19[_k] = _v
        for _k, _v in {'in_black_arm': True, 'crossbows': 0}.items():
            _merged19[_k] = _v
        s = Fake(**_merged19)
        seen.append(supplier_phase(s))
        _merged20 = {}
        for _k, _v in (s._fields if isinstance(s, (Record, Fake)) else s).items():
            _merged20[_k] = _v
        for _k, _v in {'has_report': True}.items():
            _merged20[_k] = _v
        s = Fake(**_merged20)
        seen.append(supplier_phase(s))
        _merged21 = {}
        for _k, _v in (s._fields if isinstance(s, (Record, Fake)) else s).items():
            _merged21[_k] = _v
        for _k, _v in {'in_phoenix': True, 'has_report': False}.items():
            _merged21[_k] = _v
        s = Fake(**_merged21)
        seen.append(supplier_phase(s))
        expect(seen).to_equal(['await-key', 'raid-store', 'join-blackarm', 'kill-jonny', 'join-phoenix', 'take-phoenix-half'])
    test('the bootstrap runs in one order and never skips a gang', _fn16)
describe('arrav supplier phases', _fn3)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

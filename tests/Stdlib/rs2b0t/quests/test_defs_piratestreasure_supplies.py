"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/piratestreasure-supplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.piratestreasure.supplies import kit, COIN_TARGET, COIN_LOW
from rs2004.quests.defs.piratestreasure.areas import PT_ID

def snap(over=None):
    if over is None:
        over = Fake(**{})
    _merged1 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': {}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank': {}, 'bank_ids': {}, 'bank_known': True}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged1[_k] = _v
    return _snapshot(**_merged1)

def _fn2():

    def _fn3():
        step = kit(snap(Fake(**{'bank_known': False})), False, False)
        expect(step.kind if step is not None else None).to_be('scan_bank')
    test('an unread bank is scanned before anything is decided', _fn3)

    def _fn4():
        step = kit(snap(Fake(**{'bank': {_k: _v for _k, _v in [['coins', 100000]]}})), False, False)
        expect(step.kind if step is not None else None).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0]).to_equal(Fake(**{'name': 'Coins', 'qty': COIN_TARGET}))
    test('an empty pack withdraws the coin float', _fn4)

    def _fn5():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', COIN_LOW + 1]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, COIN_LOW + 1]]}, 'bank': {_k: _v for _k, _v in [['coins', 100000]]}}))
        expect(kit(s, False, False)).to_be_null()
    test('coins above the low-water mark are left alone', _fn5)

    def _fn6():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', 5000]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, 5000]]}, 'bank': {_k: _v for _k, _v in [['coins', 5000], ['white apron', 1]]}, 'bank_ids': {_k: _v for _k, _v in [[PT_ID.WHITE_APRON, 1]]}}))
        step = kit(s, True, False)
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0]).to_equal(Fake(**{'name': 'White apron', 'qty': 1, 'id': PT_ID.WHITE_APRON}))
    test('a banked apron is withdrawn by id rather than bought', _fn6)

    def _fn7():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', 5000]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, 5000]]}, 'bank': {_k: _v for _k, _v in [['coins', 5000]]}}))
        step = kit(s, True, False)
        expect((step.kind if step is not None else None) == 'buy' and step.shop.npc).to_be('Thessalia')
    test('no banked apron buys one at Thessalia', _fn7)

    def _fn8():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', 5000]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, 5000]]}, 'worn_ids': set([PT_ID.WHITE_APRON]), 'bank': {_k: _v for _k, _v in [['coins', 5000]]}}))
        expect(kit(s, True, False)).to_be_null()
    test('a worn apron counts as held', _fn8)

    def _fn9():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', 5000]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, 5000]]}, 'bank': {_k: _v for _k, _v in [['coins', 5000]]}}))
        step = kit(s, False, True)
        expect(step.kind if step is not None else None).to_be('grab_ground')
        expect((step.kind if step is not None else None) == 'grab_ground' and step.item).to_be('Spade')
    test('no banked spade falls back to the Falador park ground spawn', _fn9)

    def _fn10():
        s = snap(Fake(**{'inv': {_k: _v for _k, _v in [['coins', 5000]]}, 'inv_ids': {_k: _v for _k, _v in [[PT_ID.COINS, 5000]]}, 'bank': {_k: _v for _k, _v in [['coins', 5000]]}}))
        expect(kit(s, False, False)).to_be_null()
    test('the spade is not fetched until the leg that digs asks for it', _fn10)
describe('pirate kit', _fn2)

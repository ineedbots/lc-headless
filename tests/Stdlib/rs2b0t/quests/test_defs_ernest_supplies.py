"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/ernest-supplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot

def _snapshot(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
from rs2004.quests.defs.ernest.areas import EC_ID
from rs2004.quests.defs.ernest.supplies import kit
from rs2004.quests.food import quest_food
original_food = quest_food.name

def _fn1():
    quest_food.name = 'Lobster'
before_each(_fn1)

def _fn2():
    quest_food.name = original_food
after_each(_fn2)

def snap(options=None):
    if options is None:
        options = Fake(**{})
    return _snapshot(**{'journal': 'in_progress', 'inv': {_k: _v for _k, _v in [['lobster', options.food if options.food is not None else 10]]}, 'inv_ids': {_k: _v for _k, _v in (options.inv_ids if options.inv_ids is not None else [[EC_ID.SPADE, 1]])}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 2000000, 'bank': {_k: _v for _k, _v in (options.bank if options.bank is not None else [])}, 'bank_ids': {_k: _v for _k, _v in (options.bank_ids if options.bank_ids is not None else [])}, 'bank_known': options.bank_known if options.bank_known is not None else True, 'tile': Fake(**{'x': 3093, 'z': 3243, 'level': 0}), 'free_slots': 20})

def _fn3():

    def _fn4():
        expect(kit(snap())).to_be_null()
    test('asks for nothing when the spade and food are already packed', _fn4)

    def _fn5():
        expect(kit(snap(Fake(**{'inv_ids': [], 'bank_known': False}))).kind if kit(snap(Fake(**{'inv_ids': [], 'bank_known': False}))) is not None else None).to_be('scan_bank')
    test('scans the bank before deciding anything when the bank is unknown', _fn5)

    def _fn6():
        step = kit(snap(Fake(**{'inv_ids': [], 'bank_ids': [[EC_ID.SPADE, 1]]})))
        expect(step.kind if step is not None else None).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items[0]).to_equal(Fake(**{'name': 'Spade', 'qty': 1, 'id': EC_ID.SPADE}))
    test('withdraws a banked spade by id, not by name', _fn6)

    def _fn7():
        step = kit(snap(Fake(**{'inv_ids': []})))
        expect(step.kind if step is not None else None).to_be('grab_ground')
        expect((step.kind if step is not None else None) == 'grab_ground' and step.item).to_be('Spade')
    test('falls back to the manor ground spawn when no spade is banked', _fn7)

    def _fn8():
        expect(kit(snap(Fake(**{'food': 6, 'bank': [['lobster', 40]]})))).to_be_null()
    test('leaves a comfortable pack alone even with food banked', _fn8)

    def _fn9():
        step = kit(snap(Fake(**{'food': 1, 'inv_ids': [], 'bank_ids': [[EC_ID.SPADE, 1]], 'bank': [['lobster', 40]]})))
        expect(step.kind if step is not None else None).to_be('withdraw')
        expect((step.kind if step is not None else None) == 'withdraw' and step.items).to_equal([Fake(**{'name': 'Spade', 'qty': 1, 'id': EC_ID.SPADE})])
    test('draws the spade and never the food, however much of it the bank holds', _fn9)

    def _fn10():
        expect(kit(snap(Fake(**{'food': 0, 'bank': [['lobster', 40]]})))).to_be_null()
    test('asks for nothing once the spade is held, however empty the pack is of food', _fn10)
describe('Ernest kit()', _fn3)

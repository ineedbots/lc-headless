"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/dragonslayerSupplies.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.dragonslayer import dragonslayer
from rs2004.quests.defs.dragonslayer.supplies import SUPPLY_GATHERS
from rs2004.quests.engine.provisioning import plan_provisioning
from rs2004.game import skills
from rs2004.quests.engine.provisioning import plan_provisioning
levels = spy_on(skills, 'effective')

def _fn1():
    global levels
    levels = spy_on(skills, 'effective').mock_return_value(99)
before_each(_fn1)

def snapshot(over=None):
    if over is None:
        over = Fake(**{})
    _merged2 = {}
    for _k, _v in {'journal': 'in_progress', 'inv': {}, 'inv_ids': {}, 'worn': set(), 'worn_ids': set(), 'no_progress': 0, 'bank_coins': 0, 'bank_known': True, 'free_slots': 10}.items():
        _merged2[_k] = _v
    for _k, _v in (over._fields if isinstance(over, (Record, Fake)) else over).items():
        _merged2[_k] = _v
    return snapshot_fields(**_merged2)
ORE_LOAD = {_k: _v for _k, _v in [['coins', 200], ['bronze pickaxe', 1], ['hammer', 1], ['maze key', 1], ['lobster', 6], ['iron ore', 6], ['coal', 12]]}

def _fn3():

    def _fn4():
        levels.mock_return_value(7)
        given = snapshot(Fake(**{'inv': ORE_LOAD, 'free_slots': 0}))
        step = SUPPLY_GATHERS.get('unfired bowl')(given, 1)
        expect(step.kind).to_be('wait')
        if step.kind != 'wait':
            raise RuntimeError('expected a blocked production step')
        expect(step.reason).to_contain('Crafting 8')
        expect(step.reason).to_contain('bank')
    test('waits before acquiring bowl materials when Crafting is 7', _fn4)

    def _fn5():
        levels.mock_return_value(8)
        given = snapshot()
        step = SUPPLY_GATHERS.get('unfired bowl')(given, 1)
        expect(step).to_match_object(Fake(**{'kind': 'custom', 'name': 'make an unfired bowl'}))
    test('produces a bowl when Crafting is exactly 8', _fn5)

    def _fn6():
        for name in SUPPLY_GATHERS.keys():
            step = SUPPLY_GATHERS.get(name)(snapshot(Fake(**{'inv': ORE_LOAD, 'free_slots': 0})), 1)
            expect(Fake(**{'name': name, 'kind': step.kind})).to_equal(Fake(**{'name': name, 'kind': 'deposit'}))
    test('a full pack banks before it shops', _fn6)

    def _fn7():
        step = SUPPLY_GATHERS.get("wizard's mind bomb")(snapshot(Fake(**{'inv': ORE_LOAD, 'free_slots': 0})), 1)
        keep = step.keep
        expect(keep).to_contain('coins')
        expect(keep).to_contain("wizard's mind bomb")
        expect(keep).not_.to_contain('iron ore')
        expect(keep).not_.to_contain('coal')
    test('the mining load is what gets banked, not the shopping', _fn7)

    def _fn8():
        expect(SUPPLY_GATHERS.get("wizard's mind bomb")(snapshot(Fake(**{'free_slots': 5})), 1).kind).to_be('custom')
        expect(SUPPLY_GATHERS.get('hammer')(snapshot(Fake(**{'free_slots': 5})), 1).kind).to_be('buy')
    test('room to spare still shops', _fn8)

    def _fn9():
        expect(SUPPLY_GATHERS.get('plank')(snapshot(Fake(**{'inv': ORE_LOAD, 'free_slots': 2})), 3).kind).to_be('deposit')
        expect(SUPPLY_GATHERS.get('plank')(snapshot(Fake(**{'free_slots': 3})), 3).kind).to_be('custom')
    test('planks need a slot each', _fn9)

    def _fn10():
        only_keepers = {_k: _v for _k, _v in [['coins', 1], ['silk', 1], ['plank', 3]]}
        step = SUPPLY_GATHERS.get('hammer')(snapshot(Fake(**{'inv': only_keepers, 'free_slots': 0})), 1)
        expect(step.kind).to_be('wait')
    test('a full pack with nothing spare says so instead of shopping', _fn10)
describe('Dragon Slayer supply gathers', _fn3)

def _fn11():

    def _fn12():
        plan = plan_provisioning(dragonslayer.record.items, {_k: _v for _k, _v in [['coins', 1]]}, {})
        expect(plan.gather).to_equal([])
        expect(plan.satisfied).to_be(True)
    test('lists nothing the quest consumes, so a resumed session re-provisions nothing', _fn12)
describe('Dragon Slayer record', _fn11)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)

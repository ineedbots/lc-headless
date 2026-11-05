"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerLowLevelCamps.test.ts (MIT, see thirdparty/rs2b0t)."""

from bots.account_leveler.record import Record

from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.planner import empty_memory, enabled_skills




additions = [
    Record({'id': 'lumbridge-swamp-giant-rats', 'npc_ids': [86, 87]}),
    Record({'id': 'lumbridge-south-giant-rats', 'npc_ids': [86, 87]}),
    Record({'id': 'port-sarim-giant-rats', 'npc_ids': [86, 87]}),
    Record({'id': 'varrock-east-giant-rats', 'npc_ids': [86, 87]}),
    Record({'id': 'varrock-spiders', 'npc_ids': [61]}),
    Record({'id': 'lumbridge-giant-spiders', 'npc_ids': [59, 60]}),
    Record({'id': 'edgeville-giant-spiders', 'npc_ids': [59, 60]}),
    Record({'id': 'al-kharid-spiders', 'npc_ids': [61]}),
    Record({'id': 'falador-dwarves', 'npc_ids': [118, 120, 206]}),
    Record({'id': 'ice-mountain-dwarves', 'npc_ids': [118, 120, 206]}),
    Record({'id': 'ice-mountain-west-dwarves', 'npc_ids': [118, 120, 206]}),
    Record({'id': 'lumbridge-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'lumbridge-east-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'port-sarim-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'falador-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'varrock-square-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'varrock-northeast-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'catherby-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'yanille-women', 'npc_ids': [4, 5, 6]}),
    Record({'id': 'barbarian-women', 'npc_ids': [17]}),
    Record({'id': 'varrock-barbarian-woman', 'npc_ids': [17]}),
    Record({'id': 'al-kharid-warriors', 'npc_ids': [18]}),
    Record({'id': 'falador-highwaymen', 'npc_ids': [180]}),
    Record({'id': 'draynor-highwayman', 'npc_ids': [180]}),
    Record({'id': 'varrock-unicorns', 'npc_ids': [89]}),
    Record({'id': 'edgeville-unicorns', 'npc_ids': [89]}),
    Record({'id': 'al-kharid-scorpions', 'npc_ids': [107]}),
    Record({'id': 'khazard-gnomes', 'npc_ids': [66, 67, 68]}),
]


def snapshot(level=40):
    return (Record({
        'levels': {_k: _v for _k, _v in [[skill, (max(10, level) if skill == 'hitpoints' else level)] for skill in enabled_skills]},
        'stock': Record({'coins': 100000, 'trout': 100, 'bronze arrow': 87}),
        'bank_ready': True,
        'quests': Record({}),
        'target': 40,
        'wilderness': True,
        'now': 1000,
    }))


def isolate(id):
    _merged1 = {}
    for _k, _v in (empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory()).items():
        _merged1[_k] = _v
    for _k, _v in {'cooldowns': {_k: _v for _k, _v in [[camp.id, 2000] for camp in [camp for camp in COMBAT_CAMPS if camp.id != id]]}}.items():
        _merged1[_k] = _v
    return (Record(_merged1))


def _fn9(_arg10, *_args):
    id = _arg10.id
    camp = ([camp for camp in COMBAT_CAMPS if camp.id == id] or [None])[0]
    expect(camp, id).to_be_defined()
    if not camp:
        return
    for objective in ['attack', 'ranged', 'magic']:
        plan = combat_plan(snapshot(), objective, isolate(id), lambda: 0)
        expect((plan.id if plan is not None else None)).to_be(id)
        expect((plan.settings if plan is not None else None).get('target')).to_be(camp.target)
    s = snapshot()
    for _k, _v in (Record({'hitpoints': camp.hp, 'attack': camp.offence, 'strength': camp.offence, 'defence': camp.defence})).items():
        s.levels[_k] = _v
    s.levels
    expect((combat_plan(s, 'attack', isolate(id), lambda: 0).id if combat_plan(s, 'attack', isolate(id), lambda: 0) is not None else None)).to_be(id)
    for skill in ['hitpoints', 'attack', 'strength', 'defence']:
        _merged11 = {}
        for _k, _v in (s.levels._fields if isinstance(s.levels, Record) else s.levels).items():
            _merged11[_k] = _v
        for _k, _v in {skill: s.levels.get(skill) - 1}.items():
            _merged11[_k] = _v
        _merged12 = {}
        for _k, _v in (s._fields if isinstance(s, Record) else s).items():
            _merged12[_k] = _v
        for _k, _v in {'levels': _merged11}.items():
            _merged12[_k] = _v
        low = Record(_merged12)
        expect(combat_plan(low, 'attack', isolate(id), lambda: 0)).to_be_null()


test_each(additions)('new camp $id is selectable at its stat gates for every combat style', _fn9)


def _fn13(*_args):
    s = snapshot(1)
    s.stock = Record({'coins': 100000})
    memory = empty_memory()
    seed = [812]

    def random():

        seed[0] = (seed[0] * 1664525 + 1013904223) & 0xffffffff
        return seed[0] / 4294967296
    camps = set()
    mobs = set()
    for i in range(200):
        plan = combat_plan(s, 'attack', memory, random)
        expect(plan.death_walk).to_be(True)
        expect(plan.food).to_be_undefined()
        camps.add(plan.id)
        mobs.add(str(plan.settings.get('target')))
        memory.recent = (list(memory.recent) + [plan.id])[-6:]
    expect(len(camps)).to_be_greater_than_or_equal(20)
    expect(len(mobs)).to_be_greater_than_or_equal(8)


test('fresh accounts rotate through at least twenty camps and eight ordinary target types without food', _fn13)


def _fn14(*_args):
    expect(any([camp.target == 'Imp' for camp in COMBAT_CAMPS])).to_be(False)
    for id in ['port-sarim-rats', 'varrock-chickens', 'varrock-rats']:
        expect(any([camp.id == id for camp in COMBAT_CAMPS])).to_be(False)


test('teleporting imps and the three inaccessible starter sites remain excluded', _fn14)

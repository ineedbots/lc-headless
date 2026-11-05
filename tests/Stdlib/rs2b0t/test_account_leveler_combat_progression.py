"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerCombatProgression.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next

def snapshot(hitpoints):
    _merged1 = {}
    for _k, _v in (({_k: _v for _k, _v in [[skill, 1] for skill in enabled_skills]}._fields if isinstance({_k: _v for _k, _v in [[skill, 1] for skill in enabled_skills]}, Record) else {_k: _v for _k, _v in [[skill, 1] for skill in enabled_skills]})).items():
        _merged1[_k] = _v
    for _k, _v in {'attack': 12, 'strength': 12, 'defence': 12, 'hitpoints': hitpoints}.items():
        _merged1[_k] = _v
    return Record({'levels': Record(_merged1), 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': True, 'now': 1000})

def _fn2(*_args):
    early = plan_next(snapshot(16), empty_memory(), lambda: 0)
    expect(early.kind == 'activity' and early.plan.death_walk).to_be(True)
    supplied = plan_next(snapshot(17), empty_memory(), lambda: 0)
    expect(supplied.kind).to_be('activity')
    if supplied.kind != 'activity':
        return
    expect([plan.script for plan in supplied.queue]).to_equal(['Fisher', 'CookBot', 'AutoFighter'])
    expect((((supplied.queue[-1] if len(supplied.queue) > 0 else None)).death_walk if ((supplied.queue[-1] if len(supplied.queue) > 0 else None)) is not None else None)).to_be(False)
    expect(((((supplied.queue[-1] if len(supplied.queue) > 0 else None)).settings if ((supplied.queue[-1] if len(supplied.queue) > 0 else None)) is not None else None)).get('food_withdraw')).to_be(12)
test('combat 14 trains without food and combat 15 queues fishing and cooking before fighting', _fn2)

def _fn3(*_args):
    s = snapshot(17)
    s.stock['raw shrimps'] = 100
    raw = plan_next(s, empty_memory(), lambda: 0)
    expect(raw.kind == 'activity' and raw.plan.script).to_be('CookBot')
    s.stock['shrimps'] = 24
    ready = plan_next(s, empty_memory(), lambda: 0)
    expect(ready.kind == 'activity' and ready.plan.script).to_be('AutoFighter')
    expect(ready.kind == 'activity' and ready.plan.food).to_be('Shrimps')
test('combat 15 cooks owned raw shrimp and uses cooked food without fishing again', _fn3)

def _fn4(*_args):
    s = snapshot(18)
    s.stock['shrimps'] = 100
    memory = empty_memory()
    targets = set()
    for i in range(100):
        plan = combat_plan(s, 'attack', memory, lambda: i / 100)
        expect(['Chicken', 'Rat', 'Man', 'Woman', 'Goblin', 'Spider', 'Giant spider']).not_.to_contain(plan.settings.get('target'))
        expect(plan.death_walk).to_be(False)
        targets.add(str(plan.settings.get('target')))
        memory.recent = list(memory.recent) + [plan.id][-6:]
    expect(len(targets)).to_be_greater_than_or_equal(3)
test('food-backed combat 15 prefers stronger targets across randomized choices', _fn4)

def _fn5(*_args):
    for skill in ['ranged', 'magic']:
        s = snapshot(10)
        for _k, _v in {'attack': 1, 'strength': 1, 'defence': 1, skill: 30}.items():
            s.levels[_k] = _v
        s.levels
        plan = combat_plan(s, 'attack', empty_memory(), lambda: 0)
        expect(plan.death_walk).to_be(False)
        expect(plan.food).to_be('Shrimps')
        expect(plan.settings.get('target')).not_.to_be('Guard')
test('higher ranged or magic combat levels also end melee death walking', _fn5)

def _fn6(*_args):
    s = snapshot(40)
    for _k, _v in Record({'attack': 40, 'strength': 40, 'defence': 40}).items():
        s.levels[_k] = _v
    s.levels
    plan = combat_plan(s, 'crafting', empty_memory(), lambda: 0, 'Cow hide')
    expect(((plan.settings if plan is not None else None)).get('target')).to_be('Cow')
test('resource gathering can still choose low-tier cows despite combat progression', _fn6)

def _fn7(*_args):
    s = snapshot(18)
    memory = empty_memory()
    memory.cooldowns = {_k: _v for _k, _v in [[c.id, 2000] for c in [c for c in COMBAT_CAMPS if c.target != 'Cow']]}
    expect(((combat_plan(s, 'attack', memory, lambda: 0).settings if combat_plan(s, 'attack', memory, lambda: 0) is not None else None)).get('target')).to_be('Cow')
test('cooling down stronger camps still leaves a usable fallback instead of blocking training', _fn7)

def _fn8(*_args):
    s = snapshot(25)
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 15}).items():
        s.levels[_k] = _v
    s.levels
    memory = empty_memory()
    memory.cooldowns = {_k: _v for _k, _v in [[c.id, 2000] for c in [c for c in COMBAT_CAMPS if c.id != 'taverley-druids']]}
    expect(combat_plan(s, 'attack', memory, lambda: 0)).to_be_null()
test('unavailable lower camps cannot force normal training into a later combat group', _fn8)

def _fn9(*_args):
    s = snapshot(40)
    for _k, _v in Record({'attack': 40, 'strength': 40, 'defence': 40}).items():
        s.levels[_k] = _v
    s.levels
    memory = empty_memory()
    memory.cooldowns = {_k: _v for _k, _v in [[c.id, 2000] for c in [c for c in COMBAT_CAMPS if c.id != 'edgeville-dungeon-giants']]}
    plan = combat_plan(s, 'prayer', memory, lambda: 0)
    expect(((plan.settings if plan is not None else None)).get('target')).to_be('Giant')
    expect(((plan.settings if plan is not None else None)).get('bury_bones')).to_be(True)
    expect(((plan.settings if plan is not None else None)).get('bury_big_bones')).to_be(True)
test('giant training enables Big bones burial so prayer sessions gain XP', _fn9)

def resolved_wait(value):
    if False:
        yield
    return value

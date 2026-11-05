"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerMembersCombat.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next
members = [['seers-men', [1, 2, 3]], ['seers-women', [4, 5, 6]], ['catherby-men', [1, 2, 3]], ['ardougne-men', [24]], ['ardougne-cows', [81]], ['ardougne-monks', [281]], ['ardougne-guards', [32]], ['ardougne-goblins', [100, 101]], ['khazard-troopers', [475, 476]], ['yanille-men', [1, 3]], ['yanille-cows', [81]], ['yanille-soldiers', [35]], ['taverley-surface-druids', [14]]]
starters = [['rimmington-rats', [47]], ['port-sarim-goblins', [100]], ['draynor-goblins', [100]], ['lumbridge-west-chickens', [41]]]

def snapshot(level=40):
    return Record({'levels': {_k: _v for _k, _v in [[skill, (max(10, level) if skill == 'hitpoints' else level)] for skill in enabled_skills]}, 'stock': Record({'coins': 100000, 'trout': 100, 'bronze arrow': 87}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': True, 'now': 1000})

def isolate(id):
    _merged1 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged1[_k] = _v
    for _k, _v in {'cooldowns': {_k: _v for _k, _v in [[camp.id, 2000] for camp in [camp for camp in COMBAT_CAMPS if camp.id != id]]}}.items():
        _merged1[_k] = _v
    return Record(_merged1)

def _fn2(level, *_args):
    s = snapshot(level)
    s.stock = Record({'coins': 100000})
    seed = [level]

    def random():
        seed[0] = seed[0] * 1664525 + 1013904223 & 4294967295
        return seed[0] / 4294967296
    selected = set()
    for i in range(200):
        _merged3 = {}
        for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
            _merged3[_k] = _v
        for _k, _v in {'objective': 'attack'}.items():
            _merged3[_k] = _v
        decision = plan_next(s, Record(_merged3), random)
        expect(decision.kind).to_be('activity')
        if decision.kind != 'activity':
            continue
        expect([plan.script for plan in decision.queue]).to_equal(['AutoFighter'])
        expect(decision.plan.death_walk).to_be(True)
        expect(decision.plan.label).to_contain('(death walk)')
        expect(decision.plan.food).to_be_undefined()
        expect(decision.plan.settings.get('food_withdraw')).to_be(0)
        expect(decision.plan.settings.get('panic_hp')).to_be(0)
        selected.add(decision.plan.id)
    expect(len(selected)).to_be_greater_than_or_equal(9)
    for id, ids in starters:
        expect(id in selected, id).to_be(True)
    expect(len(set([([camp for camp in COMBAT_CAMPS if camp.id == id] or [None])[0].region for id in list(selected)]))).to_be_greater_than_or_equal(6)
test_each([1, 10])('melee level %i starts varied death walks without fishing or cooking', _fn2)

def _fn4(*_args):
    s = snapshot(1)
    plan = combat_plan(s, 'attack', isolate('lumbridge-chickens'), lambda: 0)
    expect(plan.death_walk).to_be(True)
    expect(any([need.item in ['Trout', 'Shrimps'] for need in plan.needs])).to_be(False)
    expect(plan.settings.get('food_withdraw')).to_be(0)
test('banked food does not become a mandatory restock requirement for death walking', _fn4)

def _fn5(*_args):
    s = snapshot(1)
    s.stock = Record({'iron scimitar': 1, 'iron chainbody': 1, 'iron platelegs': 1})
    _merged6 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged6[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged6[_k] = _v
    next_ = plan_next(s, Record(_merged6), lambda: 0)
    expect(next_.kind).to_be('activity')
    if next_.kind == 'activity':
        expect(next_.plan.script).to_be('AutoFighter')
        expect(any([need.item == 'Coins' for need in next_.plan.needs])).to_be(False)
    s.levels = snapshot().levels
    expect(combat_plan(s, 'attack', isolate('seers-men'), lambda: 0)).to_be_null()
test('owned melee equipment can train locally without coins and cannot select an unfunded western trip', _fn5)

def _fn7(*_args):
    s = snapshot(20)
    expect((combat_plan(s, 'attack', isolate('lumbridge-chickens'), lambda: 0).death_walk if combat_plan(s, 'attack', isolate('lumbridge-chickens'), lambda: 0) is not None else None)).not_.to_be(True)
    s.levels = snapshot(1).levels
    early = combat_plan(s, 'attack', isolate('lumbridge-chickens'), lambda: 0)
    expect(early.death_walk).to_be(True)
    expect(combat_plan(s, 'attack', isolate('ardougne-farmer'), lambda: 0)).to_be_null()
    for id, objective in [['lumbridge-chickens', 'ranged'], ['lumbridge-chickens', 'magic']]:
        plan = combat_plan(s, objective, isolate(id), lambda: 0)
        expect(plan.death_walk).not_.to_be(True)
        expect(plan.food).to_be_defined()
        expect(plan.settings.get('food_withdraw')).to_be(12)
    s.levels['hitpoints'] = 30
    expect(combat_plan(s, 'attack', isolate('taverley-druids'), lambda: 0)).to_be_null()
test('death walking applies only below combat 15 and never to western, dangerous or ranged camps', _fn7)

def _fn8(*_args):
    for id, ids in members:
        plan = combat_plan(snapshot(), 'attack', isolate(id), lambda: 0)
        expect((plan.id if plan is not None else None), id).to_be(id)
        expect(((plan.settings if plan is not None else None)).get('target')).not_.to_be('Rock crab')
        if plan:
            expect(plan.needs).to_contain_equal(Record({'item': 'Coins', 'count': 200, 'carry': 200}))
test('each members camp is selectable without quests and travel carries fares', _fn8)

def _fn9(*_args):
    plan = combat_plan(snapshot(), 'attack', isolate('lumbridge-chickens'), lambda: 0)
    expect(plan.needs).to_contain_equal(Record({'item': 'Coins', 'count': 200, 'carry': 200}))
test('east-side combat carries return fares after training in members regions', _fn9)

def _fn10(*_args):
    for id, ids in members:
        camp = ([camp for camp in COMBAT_CAMPS if camp.id == id] or [None])[0]
        expect(camp, id).to_be_defined()
        if not camp:
            continue
        for skill, level in [['hitpoints', camp.hp], ['attack', camp.offence], ['strength', camp.offence], ['defence', camp.defence]]:
            s = snapshot()
            s.levels[skill] = level - 1
            expect(combat_plan(s, 'attack', isolate(id), lambda: 0), f'{id}:{skill}').to_be_null()
        fragile = snapshot(1)
        fragile.levels['attack'] = 40
        expect(combat_plan(fragile, 'attack', isolate(id), lambda: 0), id).to_be_null()
test('members camps independently require hitpoints, offence and defence', _fn10)

def _fn11(*_args):
    s = snapshot(20)
    s.levels['hitpoints'] = 30
    s.levels['prayer'] = 1
    memory = empty_memory()
    for i in range(20):
        plan = combat_plan(s, 'attack', memory, lambda: 0)
        region = ([camp for camp in COMBAT_CAMPS if camp.id == plan.id] or [None])[0].region
        expect([([camp for camp in COMBAT_CAMPS if camp.id == id] or [None])[0].region for id in memory.recent]).not_.to_contain(region)
        memory.recent = (list(memory.recent) + [plan.id])[-6:]
test('region selection prefers regions outside the production six-session history', _fn11)

def _fn12(*_args):
    seed = [731]

    def random():
        seed[0] = seed[0] * 1664525 + 1013904223 & 4294967295
        return seed[0] / 4294967296
    memory = empty_memory()
    visited = set()
    for i in range(100):
        plan = combat_plan(snapshot(), 'attack', memory, random)
        visited.add(plan.id)
        memory.recent = (list(memory.recent) + [plan.id])[-6:]
    for id in ['yanille-giants', 'rimmington-hobgoblins', 'burthorpe-guards', 'edgeville-dungeon-giants']:
        expect(id in visited, id).to_be(True)
    expect('seers-men' in visited).to_be(False)
test('seeded sessions rotate stronger members and free-world camps with the production history limit', _fn12)

def _fn13(*_args):
    selected = set()
    for region in range(0, 100, 10):
        for camp in range(len(COMBAT_CAMPS)):
            calls = [0]
            def select():
                calls[0] += 1
                return region / 100 if calls[0] == 1 else camp / len(COMBAT_CAMPS)
            selected.add(combat_plan(snapshot(), 'attack', empty_memory(), select).id)
    expect(len(selected)).to_be_greater_than_or_equal(5)
    for id in ['lumbridge-chickens', 'seers-men', 'rimmington-rats']:
        expect(id in selected).to_be(False)
    memory = empty_memory()
    memory.recent = ['yanille-giants', 'rimmington-hobgoblins', 'burthorpe-guards']
    memory.cooldowns['edgeville-dungeon-giants'] = 2000
    for i in range(100):
        plan = combat_plan(snapshot(), 'attack', memory, lambda: i / 100)
        expect(list(memory.recent) + ['edgeville-dungeon-giants']).not_.to_contain(plan.id)
test('random selection retires starter camps while skipping recent or cooling stronger camps', _fn13)

def _fn14(resource, *_args):
    for i in range(100):
        plan = combat_plan(snapshot(), 'crafting', empty_memory(), lambda: i / 100, resource)
        camp = ([camp for camp in COMBAT_CAMPS if camp.id == plan.id] or [None])[0]
        expect((camp.herbs if resource == '#199' else (camp.talisman if resource == 'Air talisman' else camp.target == 'Cow'))).to_be(True)
        expect((plan.output.item if plan.output is not None else None)).to_be(resource)
test_each(['#199', 'Air talisman', 'Cow hide'])('region rotation keeps %s production on matching camps', _fn14)

def _fn15(objective, *_args):
    baseline = combat_plan(snapshot(), objective, isolate('lumbridge-chickens'), lambda: 0)
    for id, ids in members:
        plan = combat_plan(snapshot(), objective, isolate(id), lambda: 0)
        expect([need for need in ((plan.needs if plan is not None else None)) if need.item != 'Coins'], id).to_equal([need for need in baseline.needs if need.item != 'Coins'])
        expect(((plan.settings if plan is not None else None)).get('combat_style')).to_be(baseline.settings.get('combat_style'))
        expect(((plan.settings if plan is not None else None)).get('ammo_withdraw')).to_be(baseline.settings.get('ammo_withdraw'))
        expect(((plan.settings if plan is not None else None)).get('runes_withdraw')).to_be(baseline.settings.get('runes_withdraw'))
test_each(['attack', 'ranged', 'magic'])('members %s camps keep the same exact equipment and ammunition manifest', _fn15)

def resolved_wait(value):
    if False:
        yield
    return value

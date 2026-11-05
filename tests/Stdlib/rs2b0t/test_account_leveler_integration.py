"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerIntegration.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.offers import supply_offer
from bots.account_leveler.combat import COMBAT_CAMPS, combat_plan
from bots.account_leveler.session import LevelerSession

def snapshot(level=1):
    return Record({'levels': {_k: _v for _k, _v in [[s, (max(10, level) if s == 'hitpoints' else level)] for s in enabled_skills]}, 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': True, 'now': 1000})

def validate(plan, s):
    meta = manifest_for(plan.script)
    expect(meta, plan.script).to_be_defined()
    for key, value in plan.settings.items():
        _v1 = (meta.settings_schema if meta is not None else None)
        def_ = (_v1[key] if _v1 is not None else None)
        expect(def_, f'{plan.script}.{key}').to_be_defined()
        if ((len((def_.options if def_ is not None else None)) if ((def_.options if def_ is not None else None)) is not None else None)) and (not def_.options_from):
            for chosen in (value if isinstance(value, list) else [value]):
                expect(def_.options, f'{plan.script}.{key}={chosen}').to_contain(chosen)
    for need in plan.needs:
        if need.item == 'Coins':
            continue
        expect(supply_offer(need.item) or producer(s, plan.objective, need, empty_memory(), lambda: 0), need.item).to_be_truthy()

def _fn2(*_args):
    for level in [1, 5, 10, 14, 15, 20, 25, 30, 39, 40, 41, 50, 59]:
        s = snapshot(level)
        s.target = 60
        for stocked in [False, True]:
            s.stock['shrimps'] = (24 if stocked else 0)
            for quests in [False, True]:
                s.quests = Record({'Druidic Ritual': quests, 'Rune Mysteries Quest': quests})
                for skill in enabled_skills:
                    for roll in [0, 0.25, 0.5, 0.75, 0.999]:
                        plan = method_for(s, skill, empty_memory(), lambda: roll)
                        expect(plan, skill).not_.to_be_null()
                        if plan:
                            validate(plan, s)
test('every training adapter uses an installed script and supported settings', _fn2)

def _fn3(*_args):
    s = snapshot(39)
    for camp in COMBAT_CAMPS:
        memory = empty_memory()
        memory.cooldowns = {_k: _v for _k, _v in [[c.id, s.now + 60000] for c in [c for c in COMBAT_CAMPS if c.id != camp.id]]}
        for objective in ['attack', 'ranged', 'magic']:
            plan = combat_plan(s, objective, memory, lambda: 0)
            expect((plan.id if plan is not None else None), camp.id).to_be(camp.id)
            if plan:
                validate(plan, s)
test('every eligible combat camp has a valid adapter for all three combat styles', _fn3)

def _fn4(*_args):
    s = snapshot()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    _merged5 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged5[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged5[_k] = _v
    _merged6 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged6[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged6[_k] = _v
    session = LevelerSession(Record(_merged6))
    scripts = []
    for step in range(3):
        next_ = plan_next(s, session.memory, lambda: 0)
        expect(next_.kind).to_be('activity')
        if next_.kind != 'activity':
            return
        scripts.append(next_.plan.script)
        validate(next_.plan, s)
        session.start(next_.plan, s.now, lambda: 0)
        for need in next_.plan.needs:
            if supply_offer(need.item):
                s.stock[need.item.lower()] = need.count
        if next_.plan.output:
            s.stock[next_.plan.output.item.lower()] = next_.plan.output.count
        session.complete(s.now + 100, True)
        s.now += 1000
    expect(scripts).to_equal(['Fisher', 'CookBot', 'AutoFighter'])
test('established combat supplies progress from catching to cooking to equipped combat', _fn4)

def _fn7(*_args):
    s = snapshot(39)
    s.wilderness = False
    memory = empty_memory()
    for i in range(30):
        plan = combat_plan(s, 'attack', memory, lambda: i / 30)
        expect((plan.wilderness if plan is not None else None)).not_.to_be(True)
    s.wilderness = True
    wild = ([plan for plan in [combat_plan(s, 'attack', memory, lambda: i / 200) for i in range(200)] if ((plan.wilderness if plan is not None else None))] or [None])[0]
    expect((wild.wilderness if wild is not None else None)).to_be(True)
    if not wild:
        return
    memory.cooldowns[wild.id] = s.now + 60000
    expect((combat_plan(s, 'attack', memory, lambda: 0.999).id if combat_plan(s, 'attack', memory, lambda: 0.999) is not None else None)).not_.to_be(wild.id)
test('cooldown and Wilderness preference exclude camps from actual combat selection', _fn7)

def _fn8(*_args):
    s = snapshot()
    s.levels['attack'] = 40
    for i in range(20):
        plan = combat_plan(s, 'attack', empty_memory(), lambda: i / 20)
        camp = ([c for c in COMBAT_CAMPS if c.id == ((plan.id if plan is not None else None))] or [None])[0]
        expect(camp).to_be_defined()
        expect(camp.hp).to_be_less_than_or_equal(10)
        expect(camp.offence).to_be(1)
        expect(camp.defence).to_be(1)
test('high attack alone does not qualify a fragile account for stronger camps', _fn8)

def _fn9(*_args):
    from rs2004.settings import settings_store as SettingsStore
    Game = game
    Execution = execution

    def _fn15(cond, *_args):
        return cond()
        if False:
            yield
    patches = [spy_on(Execution, 'delay_until').mock_implementation(_fn15), spy_on(Game, 'ingame').mock_return_value(True), spy_on(Game, 'tile').mock_return_value(Record({'x': 3220, 'z': 3218, 'level': 0})), spy_on(SettingsStore, 'display_string').mock_return_value('melee'), spy_on(SettingsStore, 'saved').mock_return_value('strength')]
    logs = []
    activity = ScriptActivity(lambda message: logs.append(message))
    try:
        yield from activity.start(manifest_for('AutoFighter'), {'combat_style': 'mage', 'spell': 'Wind Strike', 'solve_clues': False})
        expect(any(['style mage (Wind Strike' in line for line in logs])).to_be(True)
    except Exception as e:
        activity.stop()
        for patch in patches:
            restore_all()
        raise e
    activity.stop()
    for patch in patches:
        restore_all()
test('delegated AutoFighter uses the requested combat style instead of saved standalone settings', _fn9)

def _fn16(*_args):
    s = snapshot(39)
    s.levels['crafting'] = 1
    first = method_for(s, 'crafting', empty_memory(), lambda: 0)
    expect((first.script if first is not None else None)).to_be('LeatherCrafter')
    s.levels['crafting'] = 10
    expect((method_for(s, 'crafting', empty_memory(), lambda: 0).script if method_for(s, 'crafting', empty_memory(), lambda: 0) is not None else None)).to_be('FlaxAIO')
test('Crafting 1 uses leather before switching to flax at 10', _fn16)

def _fn17(*_args):
    s = snapshot()
    s.stock['shrimps'] = 100
    first = method_for(s, 'herblore', empty_memory(), lambda: 0)
    expect((first.script if first is not None else None)).to_be('AutoFighter')
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    quest = method_for(s, 'herblore', empty_memory(), lambda: 0)
    expect((quest.script if quest is not None else None)).to_be('AIOQuester')
    expect(any([n.item == 'Mithril scimitar' and n.equip for n in ((quest.needs if quest is not None else None))])).to_be(True)
    expect(any([n.item == 'Shrimps' and n.carry == 12 for n in ((quest.needs if quest is not None else None))])).to_be(True)
test('Druidic Ritual first trains combat prerequisites then carries equipment and food', _fn17)

def _fn18(*_args):
    s = snapshot(40)
    s.levels['cooking'] = 1
    s.stock['trout'] = 24
    plan = method_for(s, 'cooking', empty_memory(), lambda: 0)
    expect(((plan.settings if plan is not None else None)).get('fish')).to_be('Raw shrimps')
test('Cooking 1 ignores banked trout when choosing a recipe it can cook', _fn18)

def resolved_wait(value):
    if False:
        yield
    return value

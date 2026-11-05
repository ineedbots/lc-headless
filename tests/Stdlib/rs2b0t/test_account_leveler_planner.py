"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerPlanner.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.planner import plan_next, scimitar_for, enabled_skills, empty_memory
from bots.account_leveler.combat import combat_plan

def fresh():
    return Record({'levels': {_k: _v for _k, _v in [[s, (10 if s == 'hitpoints' else 1)] for s in enabled_skills]}, 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({}), 'target': 40, 'wilderness': True, 'now': 1000})

def trained():
    _merged1 = {}
    for _k, _v in ((fresh()._fields if isinstance(fresh(), Record) else fresh())).items():
        _merged1[_k] = _v
    for _k, _v in {'levels': {_k: _v for _k, _v in [[s, 40] for s in enabled_skills]}}.items():
        _merged1[_k] = _v
    return Record(_merged1)

def _fn2(*_args):
    expect(plan_next(trained(), empty_memory(), lambda: 0).kind).to_be('complete')
    for skill in enabled_skills:
        snapshot = trained()
        snapshot.levels[skill] = 1
        try:
            result = plan_next(snapshot, empty_memory(), lambda: 0)
        except Exception as error:
            raise AssertionError(skill + ': ' + str(error))
        expect(result.kind).not_.to_be('complete')
test('completion covers every enabled skill and ignores disabled Slayer', _fn2)

def _fn3(*_args):
    _merged4 = {}
    for _k, _v in ((fresh()._fields if isinstance(fresh(), Record) else fresh())).items():
        _merged4[_k] = _v
    for _k, _v in {'bank_ready': False}.items():
        _merged4[_k] = _v
    expect(plan_next(Record(_merged4), empty_memory(), lambda: 0).kind).to_be('refresh')
test('an unread bank cannot turn into a missing-supplies decision', _fn3)

def _fn5(*_args):
    _merged6 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged6[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged6[_k] = _v
    memory = Record(_merged6)
    result = plan_next(fresh(), memory, lambda: 0)
    expect(result.kind).to_be('activity')
    if result.kind != 'activity':
        return
    expect(result.plan.script).to_be('AutoFighter')
    expect(result.plan.death_walk).to_be(True)
    expect([plan.script for plan in result.queue]).to_equal(['AutoFighter'])
test('early combat starts without making food first', _fn5)

def _fn7(*_args):
    snapshot = fresh()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        snapshot.levels[_k] = _v
    snapshot.levels
    snapshot.stock['raw shrimps'] = 100
    _merged8 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged8[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged8[_k] = _v
    result = plan_next(snapshot, Record(_merged8), lambda: 0)
    expect(result.kind == 'activity' and result.plan.script).to_be('CookBot')
test('cooking uses banked raw fish before gathering more', _fn7)

def _fn9(*_args):
    snapshot = trained()
    snapshot.levels['fletching'] = 1
    _merged10 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged10[_k] = _v
    for _k, _v in {'objective': 'fletching'}.items():
        _merged10[_k] = _v
    result = plan_next(snapshot, Record(_merged10), lambda: 0)
    expect(result.kind == 'activity' and result.plan.script).to_be('Woodcutter')
test('fletching still gathers logs when woodcutting already reached 40', _fn9)

def _fn11(*_args):
    snapshot = trained()
    snapshot.levels['herblore'] = 1
    snapshot.stock['shrimps'] = 100
    _merged12 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged12[_k] = _v
    for _k, _v in {'objective': 'herblore'}.items():
        _merged12[_k] = _v
    result = plan_next(snapshot, Record(_merged12), lambda: 0)
    expect(result.kind == 'activity' and result.plan.settings.get('quests')).to_equal(['druid'])
test('herblore schedules only its required quest', _fn11)

def _fn13(*_args):
    expect([scimitar_for(_x) for _x in [1, 5, 10, 20, 30, 40]]).to_equal(['Iron scimitar', 'Steel scimitar', 'Steel scimitar', 'Mithril scimitar', 'Mithril scimitar', 'Mithril scimitar'])
test('scimitar upgrades never request stock Zeke does not sell', _fn13)

def _fn14(*_args):
    snapshot = trained()
    snapshot.levels['herblore'] = 3
    snapshot.quests['Druidic Ritual'] = True
    snapshot.stock['#201'] = 100
    snapshot.stock['shrimps'] = 100
    _merged15 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged15[_k] = _v
    for _k, _v in {'objective': 'herblore'}.items():
        _merged15[_k] = _v
    result = plan_next(snapshot, Record(_merged15), lambda: 0)
    expect(result.kind == 'activity' and result.plan.script).to_be('AutoFighter')
    snapshot.stock['#199'] = 30
    _merged16 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged16[_k] = _v
    for _k, _v in {'objective': 'herblore'}.items():
        _merged16[_k] = _v
    clean = plan_next(snapshot, Record(_merged16), lambda: 0)
    expect(clean.kind == 'activity' and clean.plan.script).to_be('HerbCleaner')
test('herbs use the unidentified guam id rather than every item named Herb', _fn14)

def _fn17(*_args):
    snapshot = trained()
    snapshot.levels['fishing'] = 1
    snapshot.stock['coins'] = 0
    _merged18 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged18[_k] = _v
    for _k, _v in {'objective': 'fishing'}.items():
        _merged18[_k] = _v
    result = plan_next(snapshot, Record(_merged18), lambda: 0)
    expect(result.kind).to_be('blocked')
    expect(result.kind == 'blocked' and result.reason).to_contain('Small fishing net')
test('zero banked coins blocks a needed purchase with the missing item named', _fn17)

def _fn20(_arg21, *_args):
    level, unstrung, strung, name = (_arg21.level, _arg21.unstrung, _arg21.strung, _arg21.name)
    snapshot = trained()
    snapshot.levels['ranged'] = level
    snapshot.stock = {'coins': 0, 'shrimps': 30, 'bronze arrow': 300, name.lower(): 20, f'#{unstrung}': 20}
    blocked = plan_next(snapshot, empty_memory(), lambda: 0)
    expect(blocked.kind).to_be('blocked')
    expect(blocked.kind == 'blocked' and blocked.reason).to_contain('Shortbow')
    snapshot.stock[f'#{strung}'] = 1
    ready = plan_next(snapshot, empty_memory(), lambda: 0)
    expect(ready.kind == 'activity' and ready.plan.script).to_be('AutoFighter')
test_each([Record({'level': 1, 'unstrung': 50, 'strung': 841, 'name': 'Shortbow'}), Record({'level': 5, 'unstrung': 54, 'strung': 843, 'name': 'Oak shortbow'})])('unstrung bows do not fund a ranged kit: %j', _fn20)

def _fn22(*_args):
    plan = combat_plan(trained(), 'crafting', empty_memory(), lambda: 0, 'Cow hide')
    expect(((plan.settings if plan is not None else None)).get('target')).to_be('Cow')
    expect(((plan.settings if plan is not None else None)).get('loot')).to_contain('Cow hide')
test('cowhide gathering selects cows and loots their hides', _fn22)

def _fn23(*_args):
    s = trained()
    s.levels['fishing'] = 1
    s.stock = Record({'coins': 100})
    result = plan_next(s, empty_memory(), lambda: 0)
    expect(result.kind).to_be('blocked')
    expect(result.kind == 'blocked' and result.reason).to_contain('budget 230')
test('a shopping dependency accounts for travel money before selecting an unaffordable activity', _fn23)

def _fn24(*_args):
    s = fresh()
    s.stock['shrimps'] = 100
    _merged25 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged25[_k] = _v
    for _k, _v in {'objective': 'agility', 'attempted': Record({'attack': 999, 'strength': 999, 'defence': 999})}.items():
        _merged25[_k] = _v
    memory = Record(_merged25)
    for random in [0, 0.3, 0.8, 0.99]:
        next_ = plan_next(s, memory, lambda: random)
        expect(next_.kind).to_be('activity')
        if next_.kind == 'activity':
            expect(['attack', 'strength', 'defence']).to_contain(next_.plan.objective)
            expect(next_.plan.script).to_be('AutoFighter')
test('unfinished melee takes priority over an older saved skilling objective', _fn24)

def _fn26(*_args):
    s = fresh()
    s.stock['shrimps'] = 100
    for _k, _v in Record({'attack': 30, 'strength': 25, 'defence': 5}).items():
        s.levels[_k] = _v
    s.levels
    _merged27 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged27[_k] = _v
    for _k, _v in {'objective': 'attack'}.items():
        _merged27[_k] = _v
    next_ = plan_next(s, Record(_merged27), lambda: 0)
    expect(next_.kind == 'activity' and next_.plan.objective).to_be('defence')
    expect(next_.kind == 'activity' and next_.plan.settings.get('melee_style')).to_be('defence')
test('low Defence supersedes a saved higher-level Attack objective', _fn26)

def _fn28(*_args):
    s = fresh()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    _merged29 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged29[_k] = _v
    for _k, _v in {'objective': 'woodcutting'}.items():
        _merged29[_k] = _v
    next_ = plan_next(s, Record(_merged29), lambda: 0)
    expect(next_.kind == 'activity' and next_.plan.script).to_be('Fisher')
    expect(next_.kind == 'activity' and next_.plan.objective).to_be('attack')
test('food production serves the combat objective even when the saved goal was skilling', _fn28)

def _fn30(*_args):
    s = fresh()
    s.stock['shrimps'] = 100
    for _k, _v in Record({'attack': 40, 'strength': 40, 'defence': 40}).items():
        s.levels[_k] = _v
    s.levels
    _merged31 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged31[_k] = _v
    for _k, _v in {'objective': 'runecraft'}.items():
        _merged31[_k] = _v
    next_ = plan_next(s, Record(_merged31), lambda: 0)
    expect(next_.kind == 'activity' and next_.plan.objective in ['hitpoints', 'ranged', 'magic', 'prayer']).to_be(True)
test('other combat stats precede skilling after melee reaches the target', _fn30)

def _fn32(*_args):
    s = fresh()
    s.target = 10
    for skill in ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']:
        s.levels[skill] = 10
    _merged33 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged33[_k] = _v
    for _k, _v in {'objective': 'woodcutting'}.items():
        _merged33[_k] = _v
    next_ = plan_next(s, Record(_merged33), lambda: 0)
    expect(next_.kind == 'activity' and next_.plan.objective).to_be('woodcutting')
test('skilling unlocks once combat reaches the configured target', _fn32)

def _fn34(*_args):
    s = fresh()
    s.stock = Record({'coins': 0, 'bronze axe': 1})
    _merged35 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged35[_k] = _v
    for _k, _v in {'objective': 'woodcutting'}.items():
        _merged35[_k] = _v
    next_ = plan_next(s, Record(_merged35), lambda: 0)
    expect(next_.kind).to_be('blocked')
test('blocked combat does not send a fragile account on an unrelated training trip', _fn34)

def _fn36(*_args):
    s = fresh()
    for _k, _v in Record({'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25}).items():
        s.levels[_k] = _v
    s.levels
    _merged37 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged37[_k] = _v
    for _k, _v in {'cooldowns': Record({'fish-shrimps': s.now + 900000})}.items():
        _merged37[_k] = _v
    memory = Record(_merged37)
    decision = plan_next(s, memory, lambda: 0)
    expect(decision.kind).to_be('activity')
    expect(decision.kind == 'activity' and decision.plan.script).to_be('Fisher')
test('legacy shrimp cooldowns cannot block the food dependency for every melee objective', _fn36)

def resolved_wait(value):
    if False:
        yield
    return value

"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerProgression.test.ts (MIT, see thirdparty/rs2b0t)."""
import _core
from bots.account_leveler.record import Record
from bots.account_leveler.bot import AccountLeveler, SETTINGS
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.planner import empty_memory, enabled_skills, plan_next, resolve_activity
after_each(lambda *_args: restore_all())

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, 60] for skill in enabled_skills]}, 'stock': Record({'coins': 1000000, 'lobster': 100, 'air talisman': 1, 'rune pickaxe': 1}), 'quests': Record({'Druidic Ritual': True, 'Rune Mysteries Quest': True}), 'bank_ready': True, 'target': 60, 'wilderness': True, 'now': 1000})

def _fn1(target, *_args, **_kwargs):
    expect(SETTINGS.get('target_level')).to_match_object(Record({'default': 60, 'max': 60}))
    bot = AccountLeveler()
    bot.settings = SettingsBag(({} if target is None else {'target_level': target}))
    bot.bind_log(lambda *_args: None)
    spy_on(execution, 'delay_until').mock_implementation(lambda *args, **kwargs: resolved_wait(True))
    spy_on(game, 'my_name').mock_return_value(None)
    try:
        yield from bot.on_start()
        expect(bot._target).to_be((40 if target == 40 else 60))
    except Exception as e:
        bot.on_stop()
        bot._dispose_subscriptions()
        raise e
    bot.on_stop()
    bot._dispose_subscriptions()
test_each([None, 40, 60, 99])('target %s defaults to 60, supports 60 and preserves lower choices', _fn1)

def _fn2(skill, *_args, **_kwargs):
    s = snapshot()
    s.levels[skill] = 59
    next_ = plan_next(s, empty_memory(), lambda: 0)
    expect(next_.kind).to_be('activity')
    if next_.kind == 'activity':
        expect(next_.plan.objective).to_be(skill)
    s.levels[skill] = 60
    expect(plan_next(s, empty_memory()).kind).to_be('complete')
test_each(enabled_skills)('%s still has a resolvable training method at 59', _fn2)

def _fn3(level, *_args, **_kwargs):
    s = snapshot()
    s.levels['agility'] = level
    plan = method_for(s, 'agility', empty_memory(), lambda: 0)
    if level < 15:
        expect(plan.script).to_be('GnomeCourse')
        expect(plan.prerequisite_levels).to_equal(Record({'agility': 15}))
    else:
        expect(plan.script).to_be('EdgevilleMonkeyBars')
        expect(plan.wilderness).to_be(True)
        expect(plan.travel).to_match_object(Record({'x': 3094, 'z': 3493, 'level': 0}))
        expect(plan.settings).to_match_object(Record({'food': 'Lobster', 'food_amount': 12, 'restock_mode': 'Dungeon ladder (out of food)', 'loadout': ''}))
        expect(plan.needs).to_contain_equal(Record({'item': 'Lobster', 'count': 24, 'carry': 12}))
test_each([1, 14, 15, 40, 59])('agility %s selects the appropriate course and supplies', _fn3)

def _fn4(*_args, **_kwargs):
    s = snapshot()
    s.wilderness = False
    s.levels['agility'] = 59
    expect((method_for(s, 'agility', empty_memory(), lambda: 0).script if method_for(s, 'agility', empty_memory(), lambda: 0) is not None else None)).to_be('GnomeCourse')
test('disabling Wilderness keeps agility on the Gnome course', _fn4)

def _fn5(count, *_args, **_kwargs):
    s = snapshot()
    s.levels['runecraft'] = 20
    s.stock['rune essence'] = count
    _merged6 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged6[_k] = _v
    for _k, _v in {'objective': 'runecraft'}.items():
        _merged6[_k] = _v
    next_ = plan_next(s, Record(_merged6), lambda: 0)
    expect(next_.kind).to_be('activity')
    if next_.kind != 'activity':
        return
    expect(next_.plan.script).to_be(('EssMiner' if count < 27 else 'RuneCrafter'))
    if count < 27:
        expect(next_.plan.output).to_equal(Record({'item': 'Rune essence', 'count': 1000}))
        expect([plan.script for plan in next_.queue]).to_equal(['EssMiner', 'RuneCrafter'])
        s.stock['rune essence'] = 1008
        expect(resolve_activity(s, next_.queue[1], empty_memory(), lambda: 0)).to_match_object(Record({'kind': 'activity', 'plan': Record({'script': 'RuneCrafter'})}))
test_each([0, 26, 27, 500, 999])('runecrafting with %s essence only stocks up below a load', _fn5)

def _fn7(*_args, **_kwargs):
    expect((((producer(snapshot(), 'runecraft', Record({'item': 'Rune essence', 'count': 1500}), empty_memory(), lambda: 0).output if producer(snapshot(), 'runecraft', Record({'item': 'Rune essence', 'count': 1500}), empty_memory(), lambda: 0) is not None else None)).count if ((producer(snapshot(), 'runecraft', Record({'item': 'Rune essence', 'count': 1500}), empty_memory(), lambda: 0).output if producer(snapshot(), 'runecraft', Record({'item': 'Rune essence', 'count': 1500}), empty_memory(), lambda: 0) is not None else None)) is not None else None)).to_be(1500)
test('large explicit essence requests are not reduced to the standard batch', _fn7)

def _fn8(*_args, **_kwargs):
    bot = AccountLeveler()
    s = snapshot()
    s.levels['runecraft'] = 20
    plan = producer(s, 'runecraft', Record({'item': 'Rune essence', 'count': 27}), empty_memory(), lambda: 0)
    craft = method_for(s, 'runecraft', empty_memory(), lambda: 0)
    bank_open = [False]
    carried = [27]
    spy_on(game, 'scene_ready').mock_return_value(True)
    spy_on(game, 'tile').mock_return_value(None)
    spy_on(game, 'in_combat').mock_return_value(False)
    spy_on(game, 'my_name').mock_return_value(None)
    spy_on(bank, 'is_open').mock_implementation(lambda: bank_open[0])
    spy_on(bank, 'ready').mock_implementation(lambda: bank_open[0])
    spy_on(inventory, 'count').mock_implementation(lambda name: (carried[0] if name == 'Rune essence' else 0))
    spy_on(AccountLeveler, '_snapshot').mock_return_value(s)
    spy_on(AccountLeveler, '_eat').mock_implementation(lambda *args, **kwargs: resolved_wait(None))
    spy_on(AccountLeveler, '_observe').mock_return_value(None)
    work = spy_on(bot._activity, 'loop').mock_implementation(lambda *args, **kwargs: resolved_wait(None))
    try:
        bot._phase = 'train'
        bot._session.start(plan, _core.step_time(), lambda: 0)
        bot._session.remaining_ms = 0
        bot._pending_plans = [craft]
        s.stock['rune essence'] = 54
        yield from bot.loop()
        expect(len(work.calls)).to_be(1)
        expect(bot._session.plan).to_be(plan)
        s.stock['rune essence'] = 1008
        yield from bot.loop()
        expect(len(work.calls)).to_be(2)
        expect(bot._session.plan).to_be(plan)
        bank_open[0] = True
        carried[0] = 0
        yield from bot.loop()
        expect(bot._session.plan).to_be_null()
        expect(bot._session.memory.objective).to_be('runecraft')
        expect(bot._pending_plans).to_equal([craft])
        expect(str(bot._phase)).to_be('bank')
    except Exception as e:
        bot.on_stop()
        raise e
    bot.on_stop()
test('essence stocking finishes the batch and banks it before resuming runecrafting, even after session expiry', _fn8)

def resolved_wait(value):
    if False:
        yield
    return value

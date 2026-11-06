"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerDragonAdapters.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs import loadouts
from bots.aio_quester import AIOQuester
from rs2004.quests.food import quest_food
from rs2004.quests.gear import quest_loadout
from rs2004.quests.defs.dragonslayer.supplies import SUPPLY_GATHERS
from bots.account_leveler.record import Record
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.bot import AccountLeveler
from bots.account_leveler.methods import method_for
from bots.account_leveler.planner import empty_memory, enabled_skills

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, 50] for skill in enabled_skills]}, 'stock': Record({'coins': 100000, 'lobster': 100, 'dragonfire shield': 1}), 'quests': Record({'Dragon Slayer': True}), 'target': 60, 'wilderness': True, 'bank_ready': True, 'now': 1000})
after_each(restore_all)
def adapter(roll):
    s = snapshot()
    plan = method_for(s, 'prayer', empty_memory(), lambda: roll)
    meta = manifest_for(plan.script)
    for key, value in plan.settings.items():
        definition = meta.settings_schema.get(key)
        assert definition is not None, plan.script + '.' + key
        if definition.options and not definition.options_from:
            for chosen in value if isinstance(value, list) else [value]:
                assert chosen in definition.options, str(chosen)
    spy_on(game, 'ingame', returns=True)
    spy_on(game, 'tile', returns=Tile(2946, 3368))
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(skills, 'level', returns=50)
    spy_on(inventory, 'items', returns=[])
    spy_on(equipment, 'items', returns=[])
    logs = []
    runner = ScriptActivity(logs.append)
    yield from runner.start(meta, plan.settings._fields)
    assert runner.outcome is None, str(runner.outcome)
    food = runner.child.food if hasattr(runner.child, 'food') else runner.child.food_name
    assert food == 'Lobster'
    runner.stop()

test_each([0, 0.999])('dragon adapter %s uses supported settings and keeps prepared food', adapter)

def _fn3(*_args):
    s = snapshot()
    bot = AccountLeveler()
    prayer = method_for(s, 'prayer', empty_memory(), lambda: 0)
    expect(bot._reached(prayer, s)).to_be(False)
    s.levels['prayer'] = 60
    expect(bot._reached(prayer, s)).to_be(True)
    _merged4 = {}
    for _k, _v in ((prayer._fields if isinstance(prayer, Record) else prayer)).items():
        _merged4[_k] = _v
    for _k, _v in {'quest': 'Dragon Slayer'}.items():
        _merged4[_k] = _v
    quest = Record(_merged4)
    s.quests['Dragon Slayer'] = False
    expect(bot._reached(quest, s)).to_be(False)
    s.quests['Dragon Slayer'] = True
    expect(bot._reached(quest, s)).to_be(True)
    _merged5 = {}
    for _k, _v in ((prayer._fields if isinstance(prayer, Record) else prayer)).items():
        _merged5[_k] = _v
    for _k, _v in {'objective': 'magic', 'output': Record({'item': 'Chaos rune', 'count': 200})}.items():
        _merged5[_k] = _v
    runes = Record(_merged5)
    s.stock['chaos rune'] = 199
    expect(bot._reached(runes, s)).to_be(False)
    s.stock['chaos rune'] = 200
    expect(bot._reached(runes, s)).to_be(True)
test('controller completes dragon Prayer, quest and rune collection at their own goals', _fn3)

def _fn6(*_args):
    previous_food = quest_food.name
    previous_loadout = quest_loadout.current
    snap = Record({'journal': 'in_progress', 'inv': {}, 'worn': set(), 'bank_coins': 500, 'no_progress': 0, 'free_slots': 10})
    spy_on(execution, 'delay_until').mock_implementation(lambda *args, **kwargs: resolved_wait(True))
    bot = AIOQuester()
    bot.bind_log(lambda *_args: None)
    bot.settings = SettingsBag({'quests': ['dragon'], 'gather_wilderness_planks': False})
    try:
        yield from bot.on_start()
        expect(SUPPLY_GATHERS.get('plank')(snap, 1).kind).to_be('wait')
        expect(SUPPLY_GATHERS.get('plank')(snap, 3).kind).to_be('wait')
    except Exception as e:
        bot.on_stop('test')
        bot._dispose_subscriptions()
        quest_food.name = previous_food
        quest_loadout.current = previous_loadout
        raise e
    bot.on_stop('test')
    bot._dispose_subscriptions()
    quest_food.name = previous_food
    quest_loadout.current = previous_loadout
    expect(SUPPLY_GATHERS.get('plank')(snap, 3).kind).to_be('custom')
test('delegated quest cannot gather Wilderness planks after a partial repair or lost supplies', _fn6)

def resolved_wait(value):
    if False:
        yield
    return value

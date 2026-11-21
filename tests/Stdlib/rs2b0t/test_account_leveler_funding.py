from bots.account_leveler.record import Record
from bots.account_leveler.planner import plan_next, empty_memory, enabled_skills, resolve_activity
from bots.account_leveler.funding import coin_plan


def starter():
    return Record({'levels': {skill: 10 if skill == 'hitpoints' else 1 for skill in enabled_skills},
                   'stock': {'coins': 25}, 'bank_ready': True, 'quests': {},
                   'target': 60, 'wilderness': False, 'now': 1000, 'tile': Tile(3092, 3242)})


def low_funds():
    s = starter()
    result = plan_next(s, empty_memory(), lambda: 0)
    assert result.kind == 'activity'
    plan = result.plan
    assert plan.funding and plan.script == 'Thiever'
    assert plan.settings['target'] == 'Man / Woman'
    assert plan.settings['banking'] == 'None'
    assert plan.settings['suicide'] == False
    assert plan.needs == []
    assert plan.travel.x > 2840
    assert plan.output.item == 'Coins'
    assert plan.output.count > 25
    assert plan.output.count == 1072
    s.levels['thieving'] = 10
    result = plan_next(s, empty_memory(), lambda: 0)
    assert result.plan.settings['target'] == 'Farmer'
    assert result.plan.travel == Tile(3227, 3290)
    s.stock['coins'] = 100000
    assert plan_next(s, empty_memory(), lambda: 0).plan.script == 'AutoFighter'


test('unfunded starter earns coins without buying supplies, switches targets at 10, then resumes melee', low_funds)


def cash_need():
    s = starter()
    cash = Record({'id': 'fare', 'label': 'travel', 'objective': 'attack', 'needs': [{'item': 'Coins', 'count': 1000}]})
    blocked = resolve_activity(s, cash, empty_memory(), lambda: 0)
    assert blocked.kind == 'blocked' and blocked.coins_needed == 1000
    s.tile = Tile(2725, 3493)
    s.stock['shrimps'] = 1
    plan = coin_plan(s, 'attack', 1000)
    assert plan.travel.x < 2840
    assert len(plan.needs) == 1 and plan.needs[0].count == 1
    assert all([need.item != 'Coins' for need in plan.needs])
    s.levels['thieving'] = 60
    plan = coin_plan(s, 'attack', 1000)
    assert plan.settings['target'] == 'Farmer'
    assert plan.travel.x < 2840
    s.stock = Record({'coins': 25, 'bread': 1})
    plan = coin_plan(s, 'attack', 1000)
    assert plan.food == 'Bread' and plan.needs[0].count == 1


test('cash requirements report a budget and funding uses existing food on the current side of the coast', cash_need)

"""Travel-food preparation regressions from rs2b0t 27e57fa3 (MIT)."""

from bots.account_leveler.record import Record
from bots.account_leveler.methods import producer
from bots.account_leveler.planner import empty_memory, enabled_skills, resolve_activity
from bots.account_leveler.types import requirement_key


def snapshot():
    levels = {skill: 50 for skill in enabled_skills}
    levels['fishing'] = 40
    levels['cooking'] = 40
    return Record({'levels': levels, 'stock': {'coins': 100000, 'lobster pot': 1, 'small fishing net': 1},
                   'bank_ready': True, 'quests': {}, 'target': 50, 'wilderness': False, 'now': 1000})


def empty_food_bank():
    s = snapshot()
    memory = empty_memory()
    cook = producer(s, 'prayer', Record({'item': 'Lobster', 'count': 24}), memory, lambda: 0)
    result = resolve_activity(s, cook, memory, lambda: 0)
    expect(result.kind).to_be('activity')
    expect([[plan.script, plan.settings.location] for plan in result.queue]).to_equal([
        ['Fisher', 'Draynor Village'], ['CookBot', 'Draynor'], ['Fisher', 'Catherby'], ['CookBot', 'Draynor']])
    expect([plan.output.item for plan in result.queue]).to_equal(['Raw shrimps', 'Shrimps', 'Raw lobster', 'Lobster'])
    expect(result.queue[2].needs).to_contain_equal(Record({'item': 'Shrimps', 'count': 12, 'carry': 12}))
    for plan in result.queue:
        expect(resolve_activity(s, plan, memory, lambda: 0).kind).to_be('activity')
        if plan.output:
            s.stock[requirement_key(plan.output).lower()] = plan.output.count
    expect(s.stock.lobster).to_be(24)


test('an empty food bank prepares local food before a lobster trip', empty_food_bank)


def existing_food():
    s = snapshot()
    s.stock['raw shrimps'] = 28
    plan = producer(s, 'prayer', Record({'item': 'Raw lobster', 'count': 28}), empty_memory(), lambda: 0)
    result = resolve_activity(s, plan, empty_memory(), lambda: 0)
    expect(result.kind).to_be('activity')
    expect([p.script for p in result.queue]).to_equal(['CookBot', 'Fisher'])
    s.stock['trout'] = 12
    plan = producer(s, 'prayer', Record({'item': 'Raw lobster', 'count': 28}), empty_memory(), lambda: 0)
    expect(plan.food).to_be('Trout')
    s.levels['fishing'] = 39
    expect(producer(s, 'prayer', Record({'item': 'Raw lobster', 'count': 28}), empty_memory(), lambda: 0)).to_be_null()
    for mode in ['coins', 'combat']:
        s = snapshot()
        if mode == 'coins':
            s.stock['coins'] = 199
        else:
            s.levels['hitpoints'] = 10
        expect(producer(s, 'prayer', Record({'item': 'Raw lobster', 'count': 28}), empty_memory(), lambda: 0)).to_be_null()


test('travel food reuses stock while retaining fishing, fare and combat requirements', existing_food)

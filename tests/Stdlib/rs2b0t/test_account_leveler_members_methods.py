"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerMembersMethods.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.manifests import manifest_for
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.planner import empty_memory, enabled_skills

def snapshot(levels=None):
    if levels is None:
        levels = Record({})
    _merged1 = {}
    for _k, _v in (({_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]}._fields if isinstance({_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]}, Record) else {_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]})).items():
        _merged1[_k] = _v
    for _k, _v in ((levels._fields if isinstance(levels, Record) else levels)).items():
        _merged1[_k] = _v
    return Record({'levels': _merged1, 'stock': Record({'coins': 500000, 'shrimps': 30}), 'bank_ready': True, 'quests': Record({}), 'target': 50, 'wilderness': False, 'now': 1000})

def method(s, skill, recent=None, random=0):
    if recent is None:
        recent = []
    _merged2 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged2[_k] = _v
    for _k, _v in {'recent': recent}.items():
        _merged2[_k] = _v
    return method_for(s, skill, Record(_merged2), lambda: random)

def transit(plan):
    expect(plan.food).to_be('Shrimps')
    expect((([need for need in plan.needs if need.item == 'Shrimps'] or [None])[0].carry if ([need for need in plan.needs if need.item == 'Shrimps'] or [None])[0] is not None else None)).to_be(12)
    expect(([need for need in plan.needs if need.item == 'Coins'] or [None])[0]).to_match_object(Record({'count': 200, 'carry': 200}))
    expect((plan.travel.x if plan.travel is not None else None)).to_be_less_than(2900)

def _fn4(_arg5, *_args):
    woodcutting, location = (_arg5.woodcutting, _arg5.location)
    plan = method(snapshot(Record({'woodcutting': woodcutting})), 'woodcutting')
    expect(plan.settings.get('location')).to_be(location)
    expect(any([need.item == 'Steel axe' for need in plan.needs])).to_be(True)
    transit(plan)
test_each([Record({'woodcutting': 1, 'location': 'Seers (trees)'}), Record({'woodcutting': 15, 'location': 'Seers Oaks'}), Record({'woodcutting': 30, 'location': 'Seers Willows'})])('woodcutting $woodcutting uses its matching Seers camp with travel supplies', _fn4)

def _fn6(*_args):
    expect(method(snapshot(Record({'fishing': 1})), 'fishing').settings.get('location')).to_be('Draynor Village')
    fly = method(snapshot(Record({'fishing': 20})), 'fishing')
    expect(fly.settings).to_match_object(Record({'location': 'Seers (fly fishing)', 'fish_method': 'Fly fishing — trout/salmon'}))
    transit(fly)
    lobster = method(snapshot(Record({'fishing': 40})), 'fishing')
    expect(lobster.settings).to_match_object(Record({'location': 'Catherby', 'fish_method': 'Lobster cage — lobster'}))
    expect(lobster.needs).to_contain_equal(Record({'item': 'Lobster pot', 'count': 1, 'carry': 1}))
    transit(lobster)
test('fishing selects member methods at their real levels without using unsupported Catherby shrimp spots', _fn6)

def _fn7(*_args):
    s = snapshot(Record({'mining': 29}))
    expect(method(s, 'mining').settings).to_match_object(Record({'rocks': ['Copper'], 'location': 'Southeast Varrock Mine'}))
    s.stock['copper ore'] = 14
    expect(method(s, 'mining').settings.get('rocks')).to_equal(['Tin'])
    s.levels['mining'] = 30
    iron = method(s, 'mining')
    expect(iron.settings).to_match_object(Record({'rocks': ['Iron'], 'location': 'Fight Arena Mine'}))
    expect(iron.travel).to_match_object(Record({'x': 2612, 'z': 3092, 'level': 0}))
    transit(iron)
test('mining keeps copper and tin below 30, then uses the verified Fight Arena iron mine and Yanille bank', _fn7)

def _fn8(*_args):
    s = snapshot()
    first = method(s, 'cooking')
    expect(first.settings.get('location')).to_be('Catherby')
    second = method(s, 'cooking', [first.id])
    expect(second.settings.get('location')).to_be('Seers')
    expect(second.id).not_.to_be(first.id)
    expect(method(s, 'cooking', [], 0.99).settings.get('location')).to_be('Draynor')
    transit(first)
    transit(second)
test('cooking rotates between supported member ranges and avoids its recent camp', _fn8)

def _fn9(*_args):
    burn = method(snapshot(), 'firemaking')
    expect(burn.settings.get('location')).to_be('Seers')
    transit(burn)
    smelt = method(snapshot(), 'smithing')
    expect(smelt.script).to_be('SmelterBot')
    expect(smelt.settings).to_match_object(Record({'bar': 'Iron', 'bank_stand': Record({'x': 2655, 'z': 3283, 'level': 0}), 'furnace_stand': Record({'x': 2600, 'z': 3310, 'level': 0})}))
    transit(smelt)
test('firemaking and smelting use supported Seers and Ardougne facilities', _fn9)

def _fn10(*_args):
    expect(method(snapshot(Record({'thieving': 24})), 'thieving').settings.get('target')).to_be('Farmer')
    plan = method(snapshot(Record({'thieving': 25})), 'thieving')
    expect(plan.settings).to_match_object(Record({'target': 'Warrior woman', 'action': 'Pickpocket', 'banking': 'Auto'}))
    expect(plan.travel).to_match_object(Record({'x': 2629, 'z': 3295, 'level': 0}))
    transit(plan)
test('member thieving advances to verified Ardougne warrior women at 25', _fn10)

def _fn11(*_args):
    for change in ['food', 'coins', 'combat']:
        s = snapshot(Record({'fishing': 20}))
        if change == 'food':
            s.stock['shrimps'] = 0
        if change == 'coins':
            s.stock['coins'] = 199
        if change == 'combat':
            s.levels['hitpoints'] = 10
        for skill in ['woodcutting', 'mining', 'fishing', 'cooking', 'firemaking', 'smithing', 'thieving']:
            plan = method(s, skill)
            _v12 = (plan.travel.x if plan.travel is not None else None)
            expect((_v12 if _v12 is not None else 3200)).to_be_greater_than(2900)
            expect(['Seers', 'Seers Willows', 'Seers (fly fishing)', 'Catherby', 'Fight Arena Mine']).not_.to_contain(plan.settings.get('location'))
test('western sessions require owned food, fare coins, and combat readiness', _fn11)

def _fn13(*_args):
    s = snapshot(Record({'attack': 1, 'strength': 1, 'defence': 1, 'hitpoints': 10, 'fishing': 1, 'cooking': 1}))
    s.stock['shrimps'] = 0
    plan = producer(s, 'attack', Record({'item': 'Shrimps', 'count': 24}), empty_memory(), lambda: 0)
    expect(plan.settings.get('location')).to_be('Draynor')
    expect(any([need.item == 'Shrimps' for need in plan.needs])).to_be(False)
    expect(plan.output).to_equal(Record({'item': 'Shrimps', 'count': 24}))
test('initial food production stays local without requiring its own food output', _fn13)

def _fn14(*_args):
    s = snapshot()
    first = method(s, 'cooking')
    _merged15 = {}
    for _k, _v in ((empty_memory()._fields if isinstance(empty_memory(), Record) else empty_memory())).items():
        _merged15[_k] = _v
    for _k, _v in {'cooldowns': {first.id: s.now + 10000}}.items():
        _merged15[_k] = _v
    next_ = method_for(s, 'cooking', Record(_merged15), lambda: 0)
    expect(next_.settings.get('location')).to_be('Seers')
test('a cooled down member site rotates before resolution rather than blocking another valid site', _fn14)

def _fn16(*_args):
    s = snapshot()
    plans = [method(s, skill) for skill in ['woodcutting', 'mining', 'fishing', 'cooking', 'firemaking', 'smithing', 'thieving']]
    for plan in plans:
        schema = (manifest_for(plan.script).settings_schema if manifest_for(plan.script) is not None else None)
        expect(schema).to_be_defined()
        for key, value in plan.settings.items():
            _v17 = schema
            expect((_v17[key] if _v17 is not None else None), f'{plan.script}.{key}').to_be_defined()
            _v18 = schema
            if ((len(((_v18[key] if _v18 is not None else None)).options) if ((_v18[key] if _v18 is not None else None)).options is not None else None)) and (not schema.get(key).options_from):
                for chosen in (value if isinstance(value, list) else [value]):
                    expect(schema.get(key).options).to_contain(chosen)
    logs = producer(s, 'firemaking', Record({'item': 'Logs', 'count': 28}), empty_memory(), lambda: 0)
    expect(logs.settings).to_match_object(Record({'tree_name': 'Tree', 'location': 'Seers (trees)'}))
    expect(logs.output).to_equal(Record({'item': 'Logs', 'count': 28}))
test('every selected members plan uses installed script settings and preserves requested dependency materials', _fn16)

def _fn19(*_args):
    for skill in ['agility', 'crafting']:
        s = snapshot()
        s.stock['shrimps'] = 0
        plan = method(s, skill)
        expect((plan.travel.x if plan.travel is not None else None)).to_be_less_than(2800)
        expect(([need for need in plan.needs if need.item == 'Coins'] or [None])[0]).to_match_object(Record({'count': 200, 'carry': 200}))
        expect((([need for need in plan.needs if need.item == plan.food] or [None])[0].carry if ([need for need in plan.needs if need.item == plan.food] or [None])[0] is not None else None)).to_be(12)
test('existing members-only agility and flax plans prepare food and boat fares before explicit travel', _fn19)

def _fn20(*_args):
    plan = method(snapshot(), 'cooking', [], 0.99)
    expect(plan.settings.get('location')).to_be('Draynor')
    expect(plan.travel).to_match_object(Record({'x': 3093, 'z': 3243, 'level': 0}))
    expect(([need for need in plan.needs if need.item == 'Coins'] or [None])[0]).to_match_object(Record({'count': 200, 'carry': 200}))
    expect(([need for need in plan.needs if need.item == 'Shrimps'] or [None])[0]).to_match_object(Record({'count': 12, 'carry': 12}))
test('an eastbound fallback also carries available food and fares for the return around White Wolf Mountain', _fn20)

def _fn21(*_args):
    s = snapshot()
    s.stock['iron bar'] = 28
    s.quests['Rune Mysteries Quest'] = True
    smith = method(s, 'smithing')
    runes = method(s, 'runecraft')
    leather = producer(s, 'crafting', Record({'item': 'Leather', 'count': 26}), empty_memory(), lambda: 0)
    essence = producer(s, 'runecraft', Record({'item': 'Rune essence', 'count': 27}), empty_memory(), lambda: 0)
    s.quests['Rune Mysteries Quest'] = False
    quest = method(s, 'runecraft')
    for plan, x, z in [[smith, 3185, 3440], [runes, 3013, 3355], [leather, 3269, 3167], [essence, 3251, 3420], [quest, 3253, 3420]]:
        expect(plan.travel).to_match_object(Record({'x': x, 'z': z, 'level': 0}))
        expect((([need for need in plan.needs if need.item == 'Coins'] or [None])[0].carry if ([need for need in plan.needs if need.item == 'Coins'] or [None])[0] is not None else None)).to_be_greater_than_or_equal(200)
    expect((([need for need in quest.needs if need.item == 'Coins'] or [None])[0].count if ([need for need in quest.needs if need.item == 'Coins'] or [None])[0] is not None else None)).to_be(2000)
    expect((([need for need in quest.needs if need.item == quest.food] or [None])[0].count if ([need for need in quest.needs if need.item == quest.food] or [None])[0] is not None else None)).to_be(24)
test('fixed-site crafting, quest, and ore adapters enter through their actual east-side bank with fares', _fn21)

def resolved_wait(value):
    if False:
        yield
    return value

"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerMethods.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.planner import empty_memory, enabled_skills

def snapshot(level=40):
    return Record({'levels': {_k: _v for _k, _v in [[s, level] for s in enabled_skills]}, 'stock': Record({'coins': 100000}), 'bank_ready': True, 'quests': Record({'Druidic Ritual': True, 'Rune Mysteries Quest': True}), 'target': 40, 'wilderness': True, 'now': 1})

def method(s, skill):
    return method_for(s, skill, empty_memory(), lambda: 0)

def supply(s, item):
    return producer(s, 'smithing', Record({'item': item, 'count': 28}), empty_memory(), lambda: 0)

def _fn1(*_args):
    s = snapshot()
    for level in [1, 15, 29, 30, 40]:
        s.levels['mining'] = level
        expect(method(s, 'mining').settings.get('rocks')).to_equal([('Copper' if level < 30 else 'Iron')])
    s.levels['mining'] = 29
    s.stock['copper ore'] = 28
    expect(method(s, 'mining').settings.get('rocks')).to_equal(['Tin'])
test('mining stays on copper/tin through 29 then uses iron at 30', _fn1)

def _fn2(*_args):
    s = snapshot()
    for level, tree in [[1, 'Tree'], [14, 'Tree'], [15, 'Oak'], [29, 'Oak'], [30, 'Willow'], [40, 'Willow']]:
        s.levels['woodcutting'] = level
        expect(method(s, 'woodcutting').settings.get('tree_name')).to_be(tree)
    expect(supply(s, 'Logs').settings.get('tree_name')).to_be('Tree')
    expect(supply(s, 'Oak logs').settings.get('tree_name')).to_be('Oak')
    expect(supply(s, 'Tin ore').settings.get('rocks')).to_equal(['Tin'])
test('woodcutting progresses at 15 and 30 but log dependencies retain their tree type', _fn2)

def _fn3(*_args):
    s = snapshot()
    expect(method(s, 'firemaking').settings.get('log_type')).to_be('Willow logs')
    expect(method(s, 'fletching').settings.get('material')).to_be('Willow logs')
    s.levels['woodcutting'] = 1
    expect(method(s, 'firemaking').settings.get('log_type')).to_be('Logs')
    expect(method(s, 'fletching').settings.get('material')).to_be('Logs')
    s.stock['oak logs'] = 28
    expect(method(s, 'fletching').settings.get('material')).to_be('Oak logs')
test('firemaking and fletching recipes advance only when their material can be sourced', _fn3)

def _fn4(*_args):
    s = snapshot()
    for level, wood, product in [[1, 'Logs', 'Arrow shafts'], [5, 'Logs', 'Short bow'], [10, 'Logs', 'Long bow'], [20, 'Oak logs', 'Short bow'], [25, 'Oak logs', 'Long bow'], [35, 'Willow logs', 'Short bow'], [40, 'Willow logs', 'Long bow']]:
        s.levels['fletching'] = level
        expect(method(s, 'fletching').settings).to_match_object(Record({'material': wood, 'product': product}))
test('fletching chooses shafts, shortbows, then longbows at their actual recipe levels', _fn4)

def _fn5(*_args):
    s = snapshot()
    s.levels['fishing'] = 25
    s.stock = Record({'small fishing net': 1, 'coins': 200})
    expect(method(s, 'fishing').settings.get('fish_method')).to_be('Small net — shrimp/anchovy')
    s.levels['fishing'] = 40
    expect(method(s, 'fishing').settings.get('fish_method')).to_be('Fly fishing — trout/salmon')
test('fishing can fall back to a net below 40 but never stays on nets after 40 for training', _fn5)

def _fn6(*_args):
    s = snapshot()
    s.stock['raw salmon'] = 28
    s.stock['shrimps'] = 24
    expect(method(s, 'cooking').settings.get('fish')).to_be('Raw salmon')
    expect(supply(s, 'Raw lobster').settings).to_match_object(Record({'fish_method': 'Lobster cage — lobster', 'location': 'Catherby'}))
    s.levels['cooking'] = 1
    expect(method(s, 'cooking').settings.get('fish')).to_be('Raw shrimps')
test('higher cooking uses banked salmon and can supply lobster without Karamja ferries', _fn6)

def _fn7(*_args):
    s = snapshot(1)
    expect(method(s, 'woodcutting').prerequisite_levels).to_equal(Record({'woodcutting': 15}))
    expect(method(s, 'mining').prerequisite_levels).to_equal(Record({'mining': 6}))
    expect(method(s, 'fletching').prerequisite_levels).to_equal(Record({'fletching': 5}))
test('method milestones let the controller replan when the next useful method unlocks', _fn7)

def _fn8(*_args):
    s = snapshot()
    s.levels['thieving'] = 24
    expect(method(s, 'thieving').prerequisite_levels).to_equal(Record({'thieving': 25}))
test('thieving replans when warrior women unlock at 25', _fn8)

def _fn9(*_args):
    s = snapshot()
    s.stock['coins'] = 1000000
    for level, spell in [[1, 'Wind Strike'], [5, 'Water Strike'], [13, 'Fire Strike'], [17, 'Wind Bolt'], [35, 'Fire Bolt']]:
        s.levels['magic'] = level
        plan = method(s, 'magic')
        expect(plan.settings.get('spell')).to_be(spell)
        expect(any([n.item == (('Chaos rune' if level >= 17 else 'Mind rune')) for n in plan.needs])).to_be(True)
    s.stock = Record({'coins': 0, 'staff of air': 1, 'mind rune': 200, 'shrimps': 24})
    expect(method(s, 'magic').settings.get('spell')).to_be('Wind Strike')
test('magic upgrades spells and provisions every rune while respecting the shopping budget', _fn9)

def _fn10(*_args):
    s = snapshot()
    s.stock['iron bar'] = 28
    s.stock['leather'] = 26
    s.stock['ranarr weed'] = 14
    s.stock['snape grass'] = 14
    expect(method(s, 'smithing').settings).to_match_object(Record({'bar': 'Iron', 'product': 'Platebody'}))
    expect(method(s, 'crafting').script).to_be('LeatherCrafter')
    expect(method(s, 'herblore').settings).to_match_object(Record({'herb': 'Ranarr weed', 'secondary': 'Snape grass'}))
    s.stock['snape grass'] = 0
    expect(method(s, 'herblore').settings.get('herb')).to_be('Guam leaf')
test('banked supplies unlock better smithing, crafting and herblore recipes', _fn10)

def _fn11(*_args):
    s = snapshot()
    s.levels['thieving'] = 9
    expect(method(s, 'thieving').settings.get('target')).to_be('Man')
    s.levels['thieving'] = 10
    expect(method(s, 'thieving').settings).to_match_object(Record({'target': 'Farmer', 'banking': 'Auto', 'suicide': False}))
test('thieving advances to farmers with food and banking after level 10', _fn11)

def _fn12(*_args):
    s = snapshot()
    s.levels['fishing'] = 30
    s.levels['cooking'] = 25
    s.unavailable_items = ['feather']
    s.stock['small fishing net'] = 1
    expect(method(s, 'cooking').settings.get('fish')).to_be('Raw shrimps')
    expect(method(s, 'attack').food).to_be('Shrimps')
    s.stock['raw salmon'] = 28
    expect(method(s, 'cooking').settings.get('fish')).to_be('Raw salmon')
test('unavailable fly supplies fall back to shrimp for cooking and combat food', _fn12)

def _fn13(*_args):
    s = snapshot()
    s.levels['ranged'] = 30
    s.stock = Record({'coins': 2300, 'shrimps': 24})
    plan = method(s, 'ranged')
    expect((([n for n in plan.needs if n.item.endswith('bow')] or [None])[0].item if ([n for n in plan.needs if n.item.endswith('bow')] or [None])[0] is not None else None)).to_be('Shortbow')
test('ranged bow upgrades leave enough money for a full ammo loadout', _fn13)

def _fn14(*_args):
    s = snapshot()
    s.levels['cooking'] = 1
    s.stock['lobster'] = 24
    expect(method(s, 'attack').food).to_be('Lobster')
    expect(supply(s, 'Lobster')).to_be_null()
    s.levels['cooking'] = 40
    expect(supply(s, 'Lobster').script).to_be('CookBot')
test('owning high-level food does not permit cooking replacements below the recipe level', _fn14)

def resolved_wait(value):
    if False:
        yield
    return value

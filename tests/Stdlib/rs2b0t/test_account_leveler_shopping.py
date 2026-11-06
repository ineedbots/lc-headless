"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerShopping.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.shopping import audit_supplies, shopping_stops

def snapshot(levels=None, stock=None):
    if levels is None:
        levels = Record({})
    if stock is None:
        stock = Record({'coins': 500000})
    _merged1 = {}
    for _k, _v in {'attack': 20, 'strength': 20, 'defence': 20, 'hitpoints': 25, 'ranged': 5, 'magic': 1, 'prayer': 1, 'fishing': 20, 'cooking': 15, 'woodcutting': 1, 'firemaking': 1, 'fletching': 1, 'mining': 1, 'smithing': 1, 'crafting': 1, 'agility': 1, 'thieving': 1, 'herblore': 3, 'runecraft': 1}.items():
        _merged1[_k] = _v
    for _k, _v in ((levels._fields if isinstance(levels, Record) else levels)).items():
        _merged1[_k] = _v
    return Record({'levels': Record(_merged1), 'stock': stock, 'bank_ready': True, 'quests': Record({'Druidic Ritual': True}), 'target': 30, 'wilderness': False, 'now': 0})

def _fn2(*_args):
    audit = audit_supplies(snapshot())
    needs = {_k: _v for _k, _v in [[need.item, need.count] for need in audit.needs]}
    expect(needs).to_match_object(Record({'Mithril scimitar': 1, 'Mithril platebody': 1, 'Mithril platelegs': 1, 'Mithril full helm': 1, 'Oak shortbow': 1, 'Staff of air': 1, 'Mind rune': 200, 'Bronze arrow': 1000, 'Feather': 1000, 'Fly fishing rod': 1, 'Steel axe': 1, 'Iron pickaxe': 1, 'Tinderbox': 1, 'Knife': 1, 'Hammer': 1, 'Needle': 1, 'Thread': 100, 'Vial of water': 27, 'Eye of newt': 27}))
    expect(all([not need.carry and (not need.equip) for need in audit.needs])).to_be(True)
    expect((([need for need in audit.needs if need.item == 'Oak shortbow'] or [None])[0].id if ([need for need in audit.needs if need.item == 'Oak shortbow'] or [None])[0] is not None else None)).to_be(843)
    expect(audit.budget).to_be_greater_than(0)
    expect(audit.budget + audit.reserve).to_be_less_than_or_equal(500000)
test('a wealthy bare bank gets a current usable kit and useful consumable batches before training', _fn2)

def _fn3(*_args):
    first = audit_supplies(snapshot())
    stock = Record({'coins': 500000})
    for need in first.needs:
        stock[(need.item.lower() if need.id is None else f'#{need.id}')] = need.count
    expect(audit_supplies(snapshot(Record({}), stock)).needs).to_equal([])
    expect(audit_supplies(snapshot(Record({}), stock)).budget).to_be(0)
test('owned bank and equipment supply totals prevent another startup purchase', _fn3)

def _fn4(*_args):
    audit = audit_supplies(snapshot(Record({}), Record({'coins': 210})))
    expect(audit.budget + audit.reserve).to_be_less_than_or_equal(210)
    expect(audit.reserve).to_be_greater_than_or_equal(200)
    expect(any([need.item == 'Mithril scimitar' for need in audit.needs])).to_be(False)
    expect(len(audit.skipped)).to_be_greater_than(0)
    expect(audit_supplies(snapshot(Record({}), Record({'coins': 30}))).needs).to_equal([])
test('low gold preserves travel money and skips unaffordable supplies', _fn4)

def _fn5(*_args):
    s = snapshot()
    for skill in s.levels.keys():
        s.levels[skill] = 30
    s.levels['ranged'] = 1
    audit = audit_supplies(s)
    expect(audit.needs).to_equal([Record({'item': 'Shortbow', 'id': 841, 'count': 1}), Record({'item': 'Bronze arrow', 'count': 1000})])
    s.stock['shortbow'] = 20
    s.stock['#50'] = 20
    expect(any([need.id == 841 for need in audit_supplies(s).needs])).to_be(True)
    s.stock['#841'] = 1
    expect(any([need.id == 841 for need in audit_supplies(s).needs])).to_be(False)
test('completed skills and future gear do not inflate the startup shopping list', _fn5)

def _fn6(*_args):
    stops = shopping_stops([Record({'item': 'Iron chainbody', 'count': 1}), Record({'item': 'Shortbow', 'id': 841, 'count': 1}), Record({'item': 'Bronze arrow', 'count': 1000}), Record({'item': 'Iron platelegs', 'count': 1})], Record({'shortbow': 20, '#50': 20, 'iron platelegs': 1}))
    expect([Record({'keeper': stop.keeper, 'needs': [need.item for need in stop.needs]}) for stop in stops]).to_equal([Record({'keeper': 'Horvik', 'needs': ['Iron chainbody']}), Record({'keeper': 'Lowe', 'needs': ['Shortbow', 'Bronze arrow']}), Record({'keeper': 'Hickton', 'needs': ['Bronze arrow']})])
test('shopping stops group missing purchases by vendor and use exact bow ids', _fn6)

def _fn7(*_args):
    s = snapshot(Record({'herblore': 1, 'attack': 1, 'strength': 1, 'defence': 1, 'hitpoints': 10}))
    s.quests['Druidic Ritual'] = False
    audit = audit_supplies(s)
    expect(any([need.item == 'Vial of water' or need.item == 'Eye of newt' for need in audit.needs])).to_be(False)
    expect(any([stop.keeper == 'Aemad' for stop in shopping_stops(audit.needs, s.stock)])).to_be(False)
    expect(audit.needs).to_contain_equal(Record({'item': 'Iron scimitar', 'count': 1}))
test('locked herblore defers distant potion supplies until Druidic Ritual is complete', _fn7)

def _fn8(*_args):
    s = snapshot()
    for skill in s.levels.keys():
        s.levels[skill] = 30
    s.levels['cooking'] = 1
    expect(audit_supplies(s).needs).to_equal([Record({'item': 'Small fishing net', 'count': 1})])
test('cooking below trout level stocks a shrimp net even when fishing is already complete', _fn8)

def _fn9(*_args):
    s = snapshot(Record({'magic': 35}), Record({'coins': 1000000}))
    s.target = 40
    audit = audit_supplies(s)
    expect(audit.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 200}))
    expect(audit.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 800}))
    expect(any([need.item == 'Mind rune' for need in audit.needs])).to_be(False)
test('startup rune shopping matches the strongest affordable current spell', _fn9)

def _fn10(*_args):
    stops = shopping_stops([Record({'item': 'Mind rune', 'count': 200}), Record({'item': 'Bronze arrow', 'count': 1000})], Record({}))
    expect([Record({'keeper': _o.keeper, 'tile': _o.tile, 'items': [need.item for need in _o.needs]}) for _o in stops]).to_equal([Record({'keeper': 'Aubury', 'tile': Record({'x': 3253, 'z': 3401, 'level': 0}), 'items': ['Mind rune']}), Record({'keeper': 'Betty', 'tile': Record({'x': 3012, 'z': 3258, 'level': 0}), 'items': ['Mind rune']}), Record({'keeper': 'Lowe', 'tile': Record({'x': 3231, 'z': 3421, 'level': 0}), 'items': ['Bronze arrow']}), Record({'keeper': 'Hickton', 'tile': Record({'x': 2821, 'z': 3442, 'level': 0}), 'items': ['Bronze arrow']})])
test('rune and arrow shopping includes both suppliers at their shop locations', _fn10)

def _fn12(*_args):
    s = snapshot(Record({'attack': 1, 'strength': 1, 'defence': 1, 'hitpoints': 10}))
    audit = audit_supplies(s)
    expect(any([need.item.lower().endswith('pickaxe') for need in audit.needs])).to_be(False)
    expect(any(['Nurmof' in message for message in audit.skipped])).to_be(True)
test('a fresh account defers the underground pickaxe shop until combat is established', _fn12)

def resolved_wait(value):
    if False:
        yield
    return value

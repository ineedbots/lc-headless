"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerConsumables.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.catalog import can_catch, FISH, refresh_consumables
from bots.account_leveler.magic import magic_equipment
from bots.account_leveler.methods import method_for
from bots.account_leveler.planner import empty_memory, enabled_skills, resolve_activity

def snapshot(stock, levels=None):
    if levels is None:
        levels = Record({})
    _merged1 = {}
    for _k, _v in (({_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]}._fields if isinstance({_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]}, Record) else {_k: _v for _k, _v in [[skill, 40] for skill in enabled_skills]})).items():
        _merged1[_k] = _v
    for _k, _v in ((levels._fields if isinstance(levels, Record) else levels)).items():
        _merged1[_k] = _v
    _merged2 = {}
    for _k, _v in {'shrimps': 24}.items():
        _merged2[_k] = _v
    for _k, _v in ((stock._fields if isinstance(stock, Record) else stock)).items():
        _merged2[_k] = _v
    return Record({'levels': _merged1, 'stock': Record(_merged2), 'bank_ready': True, 'quests': Record({}), 'target': 50, 'wilderness': False, 'now': 1})

def method(s, skill):
    return method_for(s, skill, empty_memory(), lambda: 0)

def _fn3(arrows, *_args):
    s = snapshot(Record({'#843': 1, 'bronze arrow': arrows, 'coins': 0}))
    s.unavailable_items = ['bronze arrow']
    plan = method(s, 'ranged')
    expect(([need for need in plan.needs if need.item == 'Bronze arrow'] or [None])[0]).to_equal(Record({'item': 'Bronze arrow', 'count': min(300, arrows), 'carry': min(300, arrows), 'equip': True, 'minimum': 1}))
    expect(plan.settings.get('ammo_withdraw')).to_be(min(300, arrows))
    expect(resolve_activity(s, plan, empty_memory(), lambda: 0).kind).to_be('activity')
test_each([1, 8, 299, 300, 1000])('ranged starts with %i banked arrows instead of requiring a refill', _fn3)

def _fn4(*_args):
    plan = method(snapshot(Record({'coins': 100000, '#843': 1})), 'ranged')
    expect(([need for need in plan.needs if need.item == 'Bronze arrow'] or [None])[0]).to_match_object(Record({'count': 300, 'carry': 300, 'minimum': 1}))
test('empty ranged supplies request a useful refill with a one-arrow minimum', _fn4)

def _fn5(*_args):
    s = snapshot(Record({'coins': 500000, 'staff of air': 1, 'mind rune': 40}), Record({'magic': 35}))
    kit = magic_equipment(s)
    expect(kit.spell).to_be('Wind Strike')
    expect(kit.casts).to_be(40)
    expect(kit.needs).to_equal([Record({'item': 'Staff of air', 'count': 1, 'carry': 1, 'equip': True}), Record({'item': 'Mind rune', 'count': 40, 'carry': 40, 'minimum': 1})])
    expect(method(s, 'magic').settings.get('runes_withdraw')).to_be(40)
test('ready mind runes are used before buying an ideal expensive chaos batch', _fn5)

def _fn6(*_args):
    s = snapshot(Record({'coins': 0, 'staff of air': 1, 'chaos rune': 8, 'fire rune': 31}), Record({'magic': 35}))
    kit = magic_equipment(s)
    expect(kit.spell).to_be('Fire Bolt')
    expect(kit.casts).to_be(7)
    expect(kit.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 7, 'carry': 7, 'minimum': 1}))
    expect(kit.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 28, 'carry': 28, 'minimum': 4}))
    expect(any([need.item == 'Air rune' for need in kit.needs])).to_be(False)
    expect(resolve_activity(s, method(s, 'magic'), empty_memory(), lambda: 0).kind).to_be('activity')
test('multi-rune spells round every supply down to the same complete cast batch', _fn6)

def _fn7(*_args):
    kit = magic_equipment(snapshot(Record({'coins': 0, 'staff of air': 1, 'chaos rune': 8, 'fire rune': 3, 'earth rune': 2}), Record({'magic': 35})))
    expect(kit.spell).to_be('Wind Bolt')
    expect(kit.casts).to_be(8)
    expect(kit.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 8, 'carry': 8, 'minimum': 1}))
test('a stronger spell with less than one complete cast falls back to usable wind runes', _fn7)

def _fn8(*_args):
    kit = magic_equipment(snapshot(Record({'coins': 0, 'staff of air': 1, 'chaos rune': 500, 'fire rune': 2000}), Record({'magic': 35})))
    expect(kit.spell).to_be('Fire Bolt')
    expect(kit.casts).to_be(150)
    expect(kit.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 200, 'carry': 150, 'minimum': 1}))
    expect(kit.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 800, 'carry': 600, 'minimum': 4}))
test('full banked rune supplies retain reserve casts and the smaller carried batch', _fn8)

def _fn9(*_args):
    s = snapshot(Record({'coins': 0, 'staff of air': 1, 'fire rune': 3}), Record({'magic': 35}))
    plan = method(s, 'magic')
    expect(all([need.count > 0 for need in plan.needs])).to_be(True)
    expect(float(plan.settings.get('runes_withdraw'))).to_be_greater_than(0)
    expect(resolve_activity(s, plan, empty_memory(), lambda: 0).kind).to_be('blocked')
test('no complete rune batch cannot resolve to a zero-cast training activity', _fn9)

def _fn10(*_args):
    s = snapshot(Record({'coins': 0, 'mind rune': 40}), Record({'magic': 35}))
    expect(method(s, 'magic').needs).to_contain_equal(Record({'item': 'Staff of air', 'count': 1, 'carry': 1, 'equip': True}))
    expect(resolve_activity(s, method(s, 'magic'), empty_memory(), lambda: 0).kind).to_be('blocked')
test('a rune batch does not waive the air staff requirement', _fn10)

def _fn11(*_args):
    s = snapshot(Record({'coins': 0, 'fly fishing rod': 1, 'feather': 7}), Record({'fishing': 20}))
    s.unavailable_items = ['feather']
    expect(can_catch(s, FISH[1])).to_be(True)
    plan = method(s, 'fishing')
    expect(plan.needs).to_contain_equal(Record({'item': 'Feather', 'count': 7, 'carry': 7, 'minimum': 1}))
    expect(plan.settings.get('bait_qty')).to_be(7)
    expect(resolve_activity(s, plan, empty_memory(), lambda: 0).kind).to_be('activity')
test('fly fishing uses seven owned feathers even when shop feathers are unavailable', _fn11)

def _fn12(*_args):
    s = snapshot(Record({'coins': 100000, 'fly fishing rod': 1}), Record({'fishing': 20}))
    expect(method(s, 'fishing').needs).to_contain_equal(Record({'item': 'Feather', 'count': 200, 'carry': 200, 'minimum': 1}))
    s.unavailable_items = ['feather', 'small fishing net']
    expect(can_catch(s, FISH[1])).to_be(False)
    expect(can_catch(s, FISH[0])).to_be(False)
    s.stock['small fishing net'] = 1
    expect(can_catch(s, FISH[0])).to_be(True)
test('empty feathers require a refill and a missing unavailable net is not a valid fallback', _fn12)

def _fn13(*_args):
    plan = method(snapshot(Record({'#843': 1, 'bronze arrow': 8, 'coins': 0})), 'ranged')
    plan.output = Record({'item': 'Cow hide', 'count': 26})
    refreshed = refresh_consumables(snapshot(Record({'#843': 1, 'coins': 500000})), plan)
    expect(([need for need in refreshed.needs if need.item == 'Bronze arrow'] or [None])[0]).to_equal(Record({'item': 'Bronze arrow', 'count': 300, 'carry': 300, 'minimum': 1, 'equip': True}))
    expect(refreshed.settings.get('ammo_withdraw')).to_be(300)
    expect(refreshed.id).to_be(plan.id)
    expect(refreshed.travel).to_equal(plan.travel)
    expect(refreshed.output).to_equal(Record({'item': 'Cow hide', 'count': 26}))
    expect([need for need in refreshed.needs if not need.minimum]).to_equal([need for need in plan.needs if not need.minimum])
    expect(plan.settings.get('ammo_withdraw')).to_be(8)
test('an exhausted eight-arrow retry restores the policy refill while preserving its camp and output', _fn13)

def _fn14(*_args):
    plan = method(snapshot(Record({'#843': 1, 'bronze arrow': 8, 'coins': 0})), 'ranged')
    refreshed = refresh_consumables(snapshot(Record({'#843': 1, 'bronze arrow': 87, 'coins': 500000})), plan)
    expect(([need for need in refreshed.needs if need.item == 'Bronze arrow'] or [None])[0]).to_match_object(Record({'count': 87, 'carry': 87, 'minimum': 1}))
    expect(refreshed.settings.get('ammo_withdraw')).to_be(87)
test('retrying a former eight-arrow batch uses the newly banked 87 arrows', _fn14)

def _fn15(*_args):
    plan = method(snapshot(Record({'staff of air': 1, 'chaos rune': 8, 'fire rune': 32, 'coins': 0}), Record({'magic': 35})), 'magic')
    refreshed = refresh_consumables(snapshot(Record({'staff of air': 1, 'coins': 500000}), Record({'magic': 35})), plan)
    expect(refreshed.settings.get('spell')).to_be('Fire Bolt')
    expect(refreshed.settings.get('runes_withdraw')).to_be(150)
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 200, 'carry': 150, 'minimum': 1}))
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 800, 'carry': 600, 'minimum': 4}))
    expect(refreshed.id).to_be(plan.id)
test('an exhausted eight-cast retry restores the same spell to 200 reserve and 150 carried casts', _fn15)

def _fn16(*_args):
    plan = method(snapshot(Record({'staff of air': 1, 'chaos rune': 8, 'fire rune': 32, 'coins': 0}), Record({'magic': 35})), 'magic')
    refreshed = refresh_consumables(snapshot(Record({'staff of air': 1, 'chaos rune': 87, 'fire rune': 131, 'coins': 500000}), Record({'magic': 35})), plan)
    expect(refreshed.settings.get('runes_withdraw')).to_be(32)
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 32, 'carry': 32, 'minimum': 1}))
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Fire rune', 'count': 128, 'carry': 128, 'minimum': 4}))
test('a mage retry rounds newly available runes to the same positive complete cast batch', _fn16)

def _fn17(*_args):
    plan = method(snapshot(Record({'fly fishing rod': 1, 'feather': 7, 'coins': 0}), Record({'fishing': 20})), 'fishing')
    s = snapshot(Record({'fly fishing rod': 1, 'coins': 500000}), Record({'fishing': 20}))
    s.unavailable_items = ['feather']
    refreshed = refresh_consumables(s, plan)
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Feather', 'count': 200, 'carry': 200, 'minimum': 1}))
    expect(refreshed.settings.get('bait_qty')).to_be(200)
    expect(resolve_activity(s, refreshed, empty_memory(), lambda: 0).kind).to_be('blocked')
test('an exhausted seven-feather retry restores its 200-feather target and remains blocked when unavailable', _fn17)

def _fn18(*_args):
    s = snapshot(Record({'coins': 100000, 'thread': 8, 'leather': 26, 'needle': 1}), Record({'crafting': 5}))
    plan = method(s, 'crafting')
    expect(plan.settings.get('thread_per_trip')).to_be(8)
    expect(([need for need in plan.needs if need.item == 'Thread'] or [None])[0]).to_match_object(Record({'count': 8, 'carry': 8, 'minimum': 1}))
    s.stock['thread'] = 0
    refreshed = refresh_consumables(s, plan)
    expect(refreshed.settings.get('thread_per_trip')).to_be(100)
test('leather crafting uses available thread and restores its target after consuming it', _fn18)

def resolved_wait(value):
    if False:
        yield
    return value


def queued_strike_upgrade(magic, spell):
    s = snapshot(Record({'coins': 200, 'staff of air': 1, 'mind rune': 200, 'fire rune': 800}), Record({'magic': 13, 'thieving': 70}))
    plan = method(s, 'magic')
    expect(plan.settings.get('spell')).to_be('Fire Strike')
    plan.output = Record({'item': 'Cow hide', 'count': 26})
    s.levels['magic'] = magic
    for name, count in [('chaos rune', 200), ('water rune', 600), ('earth rune', 600)]:
        s.stock[name] = count
    refreshed = refresh_consumables(s, plan)
    expect(refreshed.settings.get('spell')).to_be(spell)
    expect(refreshed.settings.get('runes_withdraw')).to_be(150)
    expect(refreshed.needs).to_contain_equal(Record({'item': 'Chaos rune', 'count': 200, 'carry': 150, 'minimum': 1}))
    expect(any([need.item == 'Mind rune' for need in refreshed.needs])).to_be(False)
    expect([need for need in refreshed.needs if not need.minimum]).to_equal([need for need in plan.needs if not need.minimum])
    expect(refreshed.id).to_be(plan.id)
    expect(refreshed.travel).to_equal(plan.travel)
    expect(refreshed.output).to_equal(plan.output)
    expect(plan.settings.get('spell')).to_be('Fire Strike')

test_each([[17, 'Wind Bolt'], [23, 'Water Bolt'], [29, 'Earth Bolt'], [35, 'Fire Bolt']])('queued Strike upgrades after Paladin runes at %i', queued_strike_upgrade)


def strike_retry_owned_chaos():
    s = snapshot(Record({'coins': 0, 'staff of air': 1, 'mind rune': 40}), Record({'magic': 35, 'thieving': 70}))
    plan = method(s, 'magic')
    s.stock['chaos rune'] = 8
    s.unavailable_items = ['chaos rune']
    refreshed = refresh_consumables(s, plan)
    expect(refreshed.settings.get('spell')).to_be('Wind Bolt')
    expect(refreshed.settings.get('runes_withdraw')).to_be(8)
    expect(resolve_activity(s, refreshed, empty_memory(), lambda: 0)).to_match_object(Record({'kind': 'activity', 'plan': {'script': 'AutoFighter'}}))

test('Strike retry uses owned chaos even when Paladins are unaffordable', strike_retry_owned_chaos)


def strike_below_bolt_level():
    s = snapshot(Record({'coins': 0, 'staff of air': 1, 'mind rune': 40}), Record({'magic': 16}))
    plan = method(s, 'magic')
    s.stock['chaos rune'] = 200
    expect(refresh_consumables(s, plan).settings.get('spell')).to_be('Wind Strike')

test('banked chaos respects Bolt level requirement', strike_below_bolt_level)

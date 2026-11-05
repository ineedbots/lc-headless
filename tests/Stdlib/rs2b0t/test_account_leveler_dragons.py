"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerDragons.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.methods import method_for, producer
from bots.account_leveler.planner import empty_memory, enabled_skills, resolve_activity
from rs2004.quests.data import QUESTS

def snapshot():
    return Record({'levels': {_k: _v for _k, _v in [[skill, 50] for skill in enabled_skills]}, 'target': 60, 'now': 1000, 'bank_ready': True, 'wilderness': True, 'quests': Record({'Dragon Slayer': True}), 'stock': Record({'coins': 100000, 'lobster': 100, 'dragonfire shield': 1, 'mithril scimitar': 1})})

def method(s, skill='prayer', roll=0, memory=None):
    if memory is None:
        memory = empty_memory()
    return method_for(s, skill, memory, lambda: roll)

def _fn1(*_args):
    s = snapshot()
    plans = [method(s), method(s, 'prayer', 0.999)]
    expect(sorted([p.script for p in plans])).to_equal(['GreenDragon', 'JiveDragons'])
    for plan in plans:
        expect(plan.settings).to_match_object(Record({'bury_bones': True, 'solve_clues': False, 'use_potions': False, 'combat_style': 'melee', 'weapon': 'Mithril scimitar'}))
        expect(plan.needs).to_contain_equal(Record({'item': 'Dragonfire shield', 'count': 1, 'carry': 1, 'equip': True}))
        expect(plan.food).to_be('Lobster')
        expect(plan.combat).to_be(True)
test('prayer chooses green and blue dragons with burial, supplied gear and no clue detours', _fn1)

def _fn2(*_args):
    s = snapshot()
    s.wilderness = False
    expect(method(s).script).to_be('JiveDragons')
    s.wilderness = True
    memory = empty_memory()
    for roll in [0, 0.999]:
        memory.cooldowns[method(s, 'prayer', roll).id] = s.now + 60000
    expect(method(s, 'prayer', 0, memory).script).to_be('AutoFighter')
    s.stock.pop('dragonfire shield', None)
    expect(method(s).script).to_be('AutoFighter')
    s.stock['dragonfire shield'] = 1
    s.levels['hitpoints'] = 20
    expect(method(s).script).to_be('AutoFighter')
test('Wilderness preference, cooldowns and missing protection keep unsuitable dragon plans out', _fn2)

def _fn3(*_args):
    s = snapshot()
    s.quests = Record({})
    points = 0
    for i in range(20):
        plan = method(s)
        expect(plan.script).to_be('AIOQuester')
        quest = ([q for q in QUESTS if q.name == plan.quest] or [None])[0]
        expect(quest).to_be_defined()
        expect(s.quests.get(quest.name)).not_.to_be(True)
        if quest.id == 'dragon':
            expect(points).to_be_greater_than_or_equal(32)
            return
        s.quests[quest.name] = True
        points += quest.quest_points
    raise RuntimeError('Dragon Slayer was never selected')
test('Dragon Slayer progression earns 32 quest points without repeating quests', _fn3)

def _fn4(*_args):
    s = snapshot()
    s.quests = Record({})
    s.quest_points = 32
    expect(method(s).settings.get('quests')).to_equal(['dragon'])
    expect(any([n.equip and n.item.endswith('scimitar') for n in method(s).needs])).to_be(True)
    s.levels['smithing'] = 20
    expect(method(s).prerequisite_levels).to_equal(Record({'smithing': 34}))
    expect(method(s).objective).to_be('prayer')
    s.levels['smithing'] = 50
    s.levels['mining'] = 20
    expect(method(s).prerequisite_levels).to_equal(Record({'mining': 30}))
    s.levels['mining'] = 50
    s.wilderness = False
    expect(method(s).script).not_.to_be('AIOQuester')
    s.stock['plank'] = 3
    expect(method(s).settings.get('quests')).to_equal(['dragon'])
    s.quests['Dragon Slayer'] = True
    expect(method(s).script).to_be('JiveDragons')
test('Dragon Slayer uses actual quest points, equips melee gear and prepares supply skills', _fn4)

def _fn5(*_args):
    s = snapshot()
    s.levels['thieving'] = 70
    s.unavailable_items = ['chaos rune']
    s.stock['staff of air'] = 1
    s.stock['fire rune'] = 1000
    s.stock['chaos rune'] = 2
    plan = method(s, 'magic')
    expect(plan.settings.get('spell')).to_be('Fire Bolt')
    decision = resolve_activity(s, plan, empty_memory(), lambda: 0)
    expect(decision.kind).to_be('activity')
    if decision.kind != 'activity':
        return
    expect(decision.plan.script).to_be('Thiever')
    expect(decision.plan.settings).to_match_object(Record({'target': 'Paladin', 'banking': 'Auto', 'suicide': False}))
    expect(decision.plan.travel).to_match_object(Record({'x': 2655, 'z': 3311}))
    expect(decision.plan.output).to_equal(Record({'item': 'Chaos rune', 'count': 200}))
    expect(decision.plan.objective).to_be('magic')
    expect(decision.plan.prerequisite_levels).to_be_undefined()
    expect((((decision.queue[-1] if len(decision.queue) > 0 else None)).script if ((decision.queue[-1] if len(decision.queue) > 0 else None)) is not None else None)).to_be('AutoFighter')
    s.stock['chaos rune'] = 200
    stocked = resolve_activity(s, method(s, 'magic'), empty_memory(), lambda: 0)
    expect(stocked.kind == 'activity' and stocked.plan.script).to_be('AutoFighter')
test('eligible magic accounts gather chaos runes in Ardougne before returning to casting', _fn5)

def _fn6(*_args):
    s = snapshot()
    s.levels['thieving'] = 69
    s.unavailable_items = ['chaos rune']
    plan = method(s, 'magic')
    expect(plan.settings.get('spell')).to_contain('Strike')
    decision = resolve_activity(s, plan, empty_memory(), lambda: 0)
    expect(decision.kind == 'activity' and decision.plan.script).to_be('AutoFighter')
test('accounts below 70 Thieving keep casting without training Thieving for runes', _fn6)

def _fn7(*_args):
    s = snapshot()
    s.quests = Record({})
    s.quest_points = 32
    s.dragon_stage = 7
    s.wilderness = False
    s.stock['coins'] = 500
    s.levels['smithing'] = 1
    s.levels['mining'] = 1
    plan = method(s)
    expect(plan.settings.get('quests')).to_equal(['dragon'])
    expect((([n for n in plan.needs if n.item == 'Coins'] or [None])[0].count if ([n for n in plan.needs if n.item == 'Coins'] or [None])[0] is not None else None)).to_be(200)
    expect(any([n.item == 'Plank' for n in plan.needs])).to_be(False)
    expect(plan.prerequisite_levels).to_be_undefined()
test('resuming Dragon Slayer after ship repair does not require consumed planks, nails or the original cash', _fn7)

def _fn8(*_args):
    s = snapshot()
    s.levels['thieving'] = 70
    s.stock.pop('lobster', None)
    s.unavailable_items = ['chaos rune']
    s.stock['staff of air'] = 1
    s.stock['fire rune'] = 1000
    paladin = producer(s, 'magic', Record({'item': 'Chaos rune', 'count': 200}), empty_memory(), lambda: 0)
    expect(paladin).not_.to_be_null()
    decision = resolve_activity(s, paladin, empty_memory(), lambda: 0)
    expect(decision.kind).to_be('activity')
    if decision.kind != 'activity':
        return
    expect(['Fisher', 'CookBot']).to_contain(decision.plan.script)
    expect(any([p.settings['target'] == 'Paladin' for p in decision.queue])).to_be(True)
test('paladin supply trips can prepare food before travelling instead of treating low food as ineligible', _fn8)

def _fn9(*_args):
    s = snapshot()
    s.quests = Record({})
    s.stock['shrimps'] = 50
    plan = method(s)
    expect(plan.food).to_be('Lobster')
    expect(any([n.equip and n.item.endswith('scimitar') for n in plan.needs])).to_be(True)
test('Dragon Slayer point quests carry combat gear and proper food for their fights', _fn9)

def _fn10(*_args):
    s = snapshot()
    s.quest_points = 32
    s.quests = Record({})
    s.stock.pop('lobster', None)
    s.stock['trout'] = 1000
    s.levels['fishing'] = 1
    s.levels['cooking'] = 1
    expect(method(s).prerequisite_levels).to_equal(Record({'fishing': 40}))
    s.levels['fishing'] = 40
    expect(method(s).prerequisite_levels).to_equal(Record({'cooking': 40}))
    s.quests['Dragon Slayer'] = True
    expect(method(s).prerequisite_levels).to_equal(Record({'cooking': 40}))
test('quest and Prayer preparation train food skills before combat priority can starve them out', _fn10)

def _fn11(*_args):
    s = snapshot()
    s.quest_points = 32
    s.quests = Record({})
    s.dragon_stage = 3
    s.wilderness = False
    s.stock['plank'] = 2
    s.stock['nails'] = 8
    s.levels['smithing'] = 1
    s.levels['mining'] = 1
    plan = method(s)
    expect(plan.settings.get('quests')).to_equal(['dragon'])
    expect(([n for n in plan.needs if n.item == 'Plank'] or [None])[0]).to_match_object(Record({'count': 2, 'carry': 2}))
    expect(plan.prerequisite_levels).to_be_undefined()
test('partial hull repairs resume with remaining planks and nails', _fn11)

def _fn12(*_args):
    s = snapshot()
    s.quests = Record({})
    s.quest_points = 32
    s.stock = Record({'coins': 15000, 'lobster': 100})
    decision = resolve_activity(s, method(s), empty_memory(), lambda: 0)
    expect(decision.kind).to_be('blocked')
    _merged13 = {}
    for _k, _v in ((s.stock._fields if isinstance(s.stock, Record) else s.stock)).items():
        _merged13[_k] = _v
    for _k, _v in {'mithril scimitar': 1, 'mithril chainbody': 1, 'mithril platelegs': 1, 'mithril med helm': 1}.items():
        _merged13[_k] = _v
    s.stock = Record(_merged13)
    expect(resolve_activity(s, method(s), empty_memory(), lambda: 0).kind).to_be('activity')
test('quest provisioning reserves payments before purchasing equipment', _fn12)

def _fn14(*_args):
    s = snapshot()
    s.quests = {_k: _v for _k, _v in [[q.name, True] for q in QUESTS]}
    s.quests['Dragon Slayer'] = False
    s.quests["The Knight's Sword"] = False
    s.quest_points = 31
    s.levels['cooking'] = 20
    s.stock.pop('lobster', None)
    expect(method(s).prerequisite_levels).to_equal(Record({'cooking': 40}))
test('quest requirements cannot lower the food preparation threshold', _fn14)

def resolved_wait(value):
    if False:
        yield
    return value

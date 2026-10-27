"""rs2b0t's defs/demonslayer.test.ts: the five exact-target Bones gathering cases."""
from rs2004 import execution
from rs2004.entities import npcs, ground_items
from rs2004.game import game
from rs2004.items import inventory
from rs2004.traversal import traversal
from rs2004.quests.defs.demonslayer import demonslayer
from rs2004.quests.engine.types import QuestSnapshot

S = {}

def prepare():
    S.update({'bones': 0, 'combat': False, 'npcs': [], 'drops': [], 'attacked': [], 'taken': [], 'walks': []})
    spy_on(execution, 'delay_until').mock_implementation(instant_until)
    spy_on(execution, 'delay_ticks').mock_implementation(instant_ticks)
    spy_on(game, 'in_combat').mock_implementation(lambda: S['combat'])
    spy_on(inventory, 'count').mock_implementation(lambda name: S['bones'] if name == 'Bones' else 0)
    spy_on(npcs, 'query').mock_implementation(querying(lambda: S['npcs']))
    spy_on(ground_items, 'query').mock_implementation(querying(lambda: S['drops']))
    def walk(tile, **kwargs):
        S['walks'].append([tile.x, tile.z, kwargs.get('radius')])
        return True
        yield
    spy_on(traversal, 'walk_resilient').mock_implementation(walk)
before_each(prepare)

def npc(id, distance, busy=False, contested=False):
    def attack(op):
        S['attacked'].append(id)
        S['npcs'] = []
        return True
    return Fake(id=id, name='Wizard' if id == 13 else 'Goblin', distance=lambda: distance, in_combat=busy,
                targets_another_player=lambda: contested, valid=lambda: False, actions=lambda: ['Attack'], interact=attack)

def drop(id, distance):
    def take(op):
        S['taken'].append(id)
        S['bones'] += 1
        return True
    return Fake(id=id, name='Bones', distance=lambda: distance, actions=lambda: ['Take'], interact=take)

def gather():
    step = demonslayer.gather.get('bones')(QuestSnapshot(), 25)
    expect(step.kind).to_be('custom')
    return run_wait(step.run(lambda m: None))

def empty_field():
    gather()
    expect(S['walks']).to_equal([[3144, 3231, 3]])
    expect(demonslayer.grind).to_contain('goblin')
    expect(demonslayer.grind).not_.to_contain('wizard')
test('walks to the six level-2 Goblins west of Lumbridge', empty_field)

def exact_target():
    S['npcs'] = [npc(13, 2), npc(101, 3), npc(100, 4, True), npc(100, 5, False, True), npc(100, 6)]
    gather()
    expect(S['attacked']).to_equal([100])
    expect(S['walks']).to_equal([])
test('attacks only the exact idle level-2 Goblin', exact_target)

def exact_bones():
    S['drops'] = [drop(9526, 1), drop(526, 2)]
    S['npcs'] = [npc(100, 3)]
    gather()
    expect(S['taken']).to_equal([526])
    expect(S['attacked']).to_equal([])
test('takes exact plain Bones before fighting', exact_bones)

def fighting():
    S['combat'] = True
    S['npcs'] = [npc(100, 3)]
    gather()
    expect(S['walks']).to_equal([])
    expect(S['attacked']).to_equal([])
test('does not move or retarget during combat', fighting)

def enough():
    S['bones'] = 25
    expect(gather()).to_be(True)
    expect(S['attacked']).to_equal([])
test('finishes at 25 Bones', enough)

"""Watchtower crossings, gathering and potion recipes against a changing scene."""

from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.watchtower import caves, enclave, gutanoth, potion, tower, tribes
from rs2004.quests.defs.watchtower.areas import WT_CAVES, WT_ITEM, WT_LOC, WT_NPC, WT_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def world(module, area='surface', level=0):
    scene = Scene(Tile(2500, 3100, level))
    scene.area = area
    patch(module, 'watchtower_area', lambda tile: scene.area)
    spy_on(game, 'facing', returns=None)
    return scene


def move(scene, area, level=0):
    def effect(*args):
        scene.area = area
        scene.at = Tile(scene.at.x, scene.at.z, level)
    return effect


def give(scene, item):
    def effect(*args):
        scene.item(item.id, item.name)
    return effect


def climbing():
    for fn, id in [[tower.climb_wall, WT_LOC.WALL_CLIMB], [tower.climb_tower_ladder, WT_LOC.TOWER_LADDER]]:
        scene = world(tower)
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(scene.log))).to_be(False)
        ladder = scene.loc('Ladder', ['Climb-up'], id=id, effect=lambda op: False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.locs = []
        scene.loc('Ladder', ['Climb-up'], id=id)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.locs = []
        scene.loc('Ladder', ['Climb-up'], id=id, effect=move(scene, 'first', 1))
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(scene.at.level).to_be(1)

    scene = world(tower, 'towerFloor', 2)
    expect(run_wait(tower.climb_to_wizard(0, scene.log))).to_be(True)
    expect(scene.walks).to_equal([])
    scene.area = 'outside'
    expect(run_wait(tower.climb_to_wizard(0, scene.log))).to_be(False)
    for stage, id in [[0, WT_LOC.WALL_CLIMB], [1, WT_LOC.TOWER_LADDER]]:
        scene = world(tower)
        expect(run_wait(tower.climb_to_wizard(stage, scene.log))).to_be(False)
        scene.loc('Ladder', ['Climb-up'], id=id, effect=move(scene, 'first', 1))
        expect(run_wait(tower.climb_to_wizard(stage, scene.log))).to_be(False)
        scene.at = Tile(2500, 3100, 1)
        scene.walk_ok = False
        expect(run_wait(tower.climb_to_wizard(stage, scene.log))).to_be(False)
        scene.walk_ok = True
        scene.loc('Ladder', ['Climb-up'], id=WT_LOC.WATCH_LADDER_UP, effect=move(scene, 'towerFloor', 2))
        expect(run_wait(tower.climb_to_wizard(stage, scene.log))).to_be(True)


test('the tower uses the wall before starting and both ladders afterwards', climbing)


def descending():
    scene = world(tower)
    expect(run_wait(tower.leave_wizard_floor(scene.log))).to_be(True)
    scene.area = 'towerFloor'
    expect(run_wait(tower.leave_wizard_floor(scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-down'], id=WT_LOC.WATCH_LADDER_DOWN)
    expect(run_wait(tower.leave_wizard_floor(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Ladder', ['Climb-down'], id=WT_LOC.WATCH_LADDER_DOWN, effect=move(scene, 'towerFloor', 1))
    expect(run_wait(tower.leave_wizard_floor(scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-down'], id=WT_LOC.LADDER_TOP, effect=move(scene, 'surface', 0))
    expect(run_wait(tower.leave_wizard_floor(scene.log))).to_be(True)
    expect(scene.at.level).to_be(0)


test('leaving the wizard floor requires both descents to land', descending)


def evidence():
    scene = world(tower)
    scene.walk_ok = False
    expect(run_wait(tower.search_evidence_bush(scene.log))).to_be(False)
    scene.walk_ok = True
    for i in range(28):
        scene.item(i, 'Filler')
    expect(run_wait(tower.search_evidence_bush(scene.log))).to_be(False)
    expect(scene.logged('pack is full')).to_be(True)
    scene.pack = []
    expect(run_wait(tower.search_evidence_bush(scene.log))).to_be(False)
    scene.loc('Bush', ['Search'], id=WT_LOC.BUSH_NAIL, effect=give(scene, WT_ITEM.FINGERNAILS))
    expect(run_wait(tower.search_evidence_bush(scene.log))).to_be(True)
    expect(run_wait(tower.search_evidence_bush(scene.log))).to_be(True)
    expect(scene.has(WT_ITEM.FINGERNAILS.id)).to_be(True)


test('only the evidence bush yields fingernails and a full pack refuses them', evidence)


def wizard_tasks():
    scene = world(tower)
    climb = spy_on(tower, 'climb_to_wizard', impl=answer(False))
    talk = spy_on(tower, 'talk_to_wizard', impl=answer(True))
    tasks = [tower.start_quest, tower.ask_wizard_for_relic, tower.ask_wizard_about_shamans,
             tower.show_crystals_to_wizard, tower.pull_lever]
    for task in tasks:
        expect(run_wait(task(scene.log))).to_be(False)
    expect(run_wait(tower.hand_in_fingernails(scene.log))).to_be(False)
    scene.item(WT_ITEM.FINGERNAILS.id, WT_ITEM.FINGERNAILS.name)
    expect(run_wait(tower.hand_in_fingernails(scene.log))).to_be(False)
    climb.mock_implementation(answer(True))
    for task in [tower.start_quest, tower.hand_in_fingernails, tower.ask_wizard_for_relic, tower.ask_wizard_about_shamans]:
        expect(run_wait(task(scene.log))).to_be(True)
    expect(len(talk.calls)).to_be(4)
    expect(run_wait(tower.show_crystals_to_wizard(scene.log))).to_be(False)
    scene.npc(WT_NPC.WIZARD)
    scene.item(WT_ITEM.CRYSTAL1.id, WT_ITEM.CRYSTAL1.name)
    expect(run_wait(tower.show_crystals_to_wizard(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(tower.pull_lever(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(tower.pull_lever(scene.log))).to_be(False)

    def complete(op):
        scene.status = 'complete'

    scene.loc('Lever', ['Pull'], id=WT_LOC.LEVER, effect=complete)
    expect(run_wait(tower.pull_lever(scene.log))).to_be(True)
    restore_all()
    scene = world(tower)
    scene.talk_status = 'unreachable'
    expect(run_wait(tower.talk_to_wizard([], scene.log))).to_be(False)
    scene.talk_status = 'done'
    spy_on(tower, 'talk_through', impl=answer(True))
    expect(run_wait(tower.talk_to_wizard([], scene.log))).to_be(True)


test('wizard tasks stop on a failed climb and hand in only present items', wizard_tasks)


def relic_parts():
    scene = world(tower)
    climb = spy_on(tower, 'climb_to_wizard', impl=answer(False))
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(False)
    climb.mock_implementation(answer(True))
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(False)
    scene.item(123, 'Part')
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(False)
    wizard = scene.npc(WT_NPC.WIZARD)
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(False)
    scene.chat.pages = ['continue']
    scene.chat.shown = ['I already have that part']
    stub(tower.relic_state, refused=set())
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(True)
    expect(123 in tower.relic_state.refused).to_be(True)
    scene.chat.shown = []
    scene.chat.pages = ['continue']
    scene.later(lambda: scene.take(123))
    expect(run_wait(tower.give_relic_part(123, scene.log))).to_be(True)
    expect(scene.has(123)).to_be(False)


test('a relic part is accepted, explicitly refused or timed out without guessing', relic_parts)


def spell_scroll():
    scene = Scene()
    expect(run_wait(tower.read_spell_scroll(scene.log))).to_be(True)
    scene.item(WT_ITEM.WATCHTOWER_SPELL.id, 'Scroll', effect=lambda op: False)
    expect(run_wait(tower.read_spell_scroll(scene.log))).to_be(False)
    scene.pack = []
    scene.item(WT_ITEM.WATCHTOWER_SPELL.id, 'Scroll')
    scene.main_modal = 12
    expect(run_wait(tower.read_spell_scroll(scene.log))).to_be(True)
    expect(scene.main_modal).to_be(-1)
    expect(scene.logged('memorised')).to_be(True)


test('reading the teleport scroll closes its modal', spell_scroll)


def recipe():
    scene = Scene()
    expect(run_wait(potion.combine(1, 2, 3, scene.log))).to_be(False)
    scene.item(1, 'Source', on_use=lambda target: False)
    scene.item(2, 'Target')
    expect(run_wait(potion.combine(1, 2, 3, scene.log))).to_be(False)
    scene.pack = []
    scene.item(1, 'Source', on_use=give(scene, Fake(id=3, name='Product')))
    scene.item(2, 'Target')
    expect(run_wait(potion.combine(1, 2, 3, scene.log))).to_be(True)
    scene.pack = []
    expect(run_wait(potion.grind_bat_bones(scene.log))).to_be(False)
    scene.item(WT_ITEM.PESTLE.id, 'Pestle', on_use=give(scene, WT_ITEM.GROUND_BAT_BONES))
    scene.item(WT_ITEM.BAT_BONES.id, 'Bat bones')
    expect(run_wait(potion.grind_bat_bones(scene.log))).to_be(True)
    expect(run_wait(potion.grind_bat_bones(scene.log))).to_be(True)
    scene.pack = []
    expect(run_wait(potion.brew_ogre_potion(scene.log))).to_be(False)
    scene.item(WT_ITEM.GUAM_LEAF.id, 'Guam', on_use=give(scene, WT_ITEM.GUAM_VIAL))
    scene.item(WT_ITEM.VIAL_WATER.id, 'Water')
    expect(run_wait(potion.brew_ogre_potion(scene.log))).to_be(False)
    scene.item(WT_ITEM.JANGERBERRIES.id, 'Berries', on_use=give(scene, WT_ITEM.GUAM_JANGER_VIAL))
    scene.item(WT_ITEM.GROUND_BAT_BONES.id, 'Ground bones', on_use=give(scene, WT_ITEM.OGRE_POTION))
    expect(run_wait(potion.brew_ogre_potion(scene.log))).to_be(True)
    expect(run_wait(potion.brew_ogre_potion(scene.log))).to_be(True)
    climb = spy_on(potion, 'climb_to_wizard', impl=answer(False))
    expect(run_wait(potion.infuse_potion(scene.log))).to_be(False)
    climb.mock_implementation(answer(True))
    expect(run_wait(potion.infuse_potion(scene.log))).to_be(False)
    scene.npc(WT_NPC.WIZARD)
    scene.take(WT_ITEM.OGRE_POTION.id)
    scene.item(WT_ITEM.OGRE_POTION.id, 'Potion', on_use=give(scene, WT_ITEM.MAGIC_OGRE_POTION))
    expect(run_wait(potion.infuse_potion(scene.log))).to_be(True)
    expect(scene.has(WT_ITEM.MAGIC_OGRE_POTION.id)).to_be(True)


test('ogre potion is mixed in order and infused by the wizard', recipe)


CROSSINGS = [
    [tribes, tribes.enter_toban_camp, 'surface', 'tobanCamp', WT_LOC.TOBAN_CAVE, 'Enter'],
    [tribes, tribes.leave_toban_camp, 'tobanCamp', 'surface', WT_LOC.TOBAN_LADDER_DOWN, 'Climb-down'],
    [tribes, tribes.leave_grew_island, 'grewIsland', 'surface', WT_LOC.ROPESWING, 'Swing-on'],
    [gutanoth, gutanoth.leave_lower_city, 'lowerCity', 'surface', WT_LOC.BATTLEMENT, 'Climb-over'],
    [gutanoth, gutanoth.jump_back, 'cityGuard', 'surface', WT_LOC.JUMP_OUT, 'Jump-From'],
    [enclave, enclave.leave_enclave, 'enclave', 'surface', WT_LOC.ENCLAVE_CAVE, 'Enter'],
]


def crossing(module, fn, start, end, id, op):
    scene = world(module, end)
    expect(run_wait(fn(scene.log))).to_be(True)
    scene.area = start
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Crossing', [op], id=id)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Crossing', [op], id=id, effect=move(scene, end))
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(scene.area).to_be(end)


test_each(CROSSINGS)('a Watchtower crossing requires its arrival: %s %s', crossing)


def grew_and_gold():
    scene = world(tribes)
    scene.walk_ok = False
    expect(run_wait(tribes.swing_to_grew_island(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(tribes.swing_to_grew_island(scene.log))).to_be(False)
    scene.loc('Tree', id=WT_LOC.ROPESWING_NOROPE)
    scene.item(WT_ITEM.ROPE.id, 'Rope')
    expect(run_wait(tribes.swing_to_grew_island(scene.log))).to_be(False)
    scene.take(WT_ITEM.ROPE.id)
    scene.item(WT_ITEM.ROPE.id, 'Rope', on_use=move(scene, 'grewIsland'))
    expect(run_wait(tribes.swing_to_grew_island(scene.log))).to_be(True)
    expect(run_wait(tribes.swing_to_grew_island(scene.log))).to_be(True)
    scene.area = 'tobanCamp'
    scene.walk_ok = False
    expect(run_wait(tribes.open_toban_chest(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(tribes.open_toban_chest(scene.log))).to_be(False)
    scene.loc('Chest', id=WT_LOC.TOBAN_CHEST)
    scene.item(WT_ITEM.TOBAN_KEY.id, 'Key', on_use=give(scene, WT_ITEM.STOLEN_GOLD))
    expect(run_wait(tribes.open_toban_chest(scene.log))).to_be(True)
    expect(run_wait(tribes.open_toban_chest(scene.log))).to_be(True)
    expect(scene.has(WT_ITEM.TOBAN_KEY.id)).to_be(True)


test('Grew requires a rope and Toban gold is taken without consuming the key', grew_and_gold)


def tribal_talks():
    scene = world(tribes)
    enter = spy_on(tribes, 'enter_toban_camp', impl=answer(False))
    swing = spy_on(tribes, 'swing_to_grew_island', impl=answer(False))
    for fn in [tribes.talk_to_toban, tribes.talk_to_grew, tribes.kill_gorad]:
        expect(run_wait(fn(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    swing.mock_implementation(answer(True))
    scene.talk_status = 'unreachable'
    for fn in [tribes.talk_to_toban, tribes.talk_to_grew, tribes.talk_to_og, tribes.kill_gorad]:
        expect(run_wait(fn(scene.log))).to_be(False)
    scene.talk_status = 'done'
    talks = spy_on(tribes, 'talk_strict', impl=answer(True))
    for fn in [tribes.talk_to_toban, tribes.talk_to_grew, tribes.talk_to_og]:
        expect(run_wait(fn(scene.log))).to_be(True)
    expect(len(talks.calls)).to_be(3)
    through = spy_on(tribes, 'talk_through', impl=answer(False))
    expect(run_wait(tribes.kill_gorad(scene.log))).to_be(False)
    through.mock_implementation(answer(True))
    fight = spy_on(tribes, 'fight_gorad', impl=answer(True))
    expect(run_wait(tribes.kill_gorad(scene.log))).to_be(True)
    expect(len(fight.calls)).to_be(1)
    for i in range(28):
        scene.item(i, 'Filler')
    expect(run_wait(tribes.kill_gorad(scene.log))).to_be(False)
    scene.item(WT_ITEM.OGRE_TOOTH.id, 'Tooth')
    expect(run_wait(tribes.kill_gorad(scene.log))).to_be(True)


test('tribal dialogue stops at failed approaches and Gorad needs a pack slot', tribal_talks)


def berries_and_gorad():
    scene = world(tribes)
    swing = spy_on(tribes, 'swing_to_grew_island', impl=answer(False))
    expect(run_wait(tribes.pick_jangerberries(scene.log))).to_be(False)
    swing.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(tribes.pick_jangerberries(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(tribes.pick_jangerberries(scene.log))).to_be(False)
    scene.on_ground(WT_ITEM.JANGERBERRIES.id, WT_ITEM.JANGERBERRIES.name)
    expect(run_wait(tribes.pick_jangerberries(scene.log))).to_be(True)
    scene.item(WT_ITEM.JANGERBERRIES.id, WT_ITEM.JANGERBERRIES.name)
    expect(run_wait(tribes.pick_jangerberries(scene.log))).to_be(True)
    expect(run_wait(tribes.fight_gorad(scene.log))).to_be(False)
    expect(scene.logged('outlasted')).to_be(True)
    scene.npc(WT_NPC.GORAD, ['Attack'], effect=give(scene, WT_ITEM.OGRE_TOOTH))
    expect(run_wait(tribes.fight_gorad(scene.log))).to_be(True)
    expect(scene.has(WT_ITEM.OGRE_TOOTH.id)).to_be(True)


test('berries may be partially gathered and Gorad is fought until the tooth lands', berries_and_gorad)


def cave_entries():
    cave = WT_CAVES[0]
    scene = world(caves, 'skavidCaves')
    scene.at = cave.landing
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(True)
    scene.at = WT_CAVES[1].landing
    leave = spy_on(caves, 'leave_cave', impl=answer(False))
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(False)
    scene.walk_ok = True
    scene.area = 'surface'
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(False)
    scene.loc('Cave', ['Enter'], id=WT_LOC.CAVE_IN[0])
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(False)

    def wrong_cave(op):
        scene.area = 'skavidCaves'
        scene.at = WT_CAVES[1].landing

    scene.locs = []
    scene.loc('Cave', ['Enter'], id=WT_LOC.CAVE_IN[0], effect=wrong_cave)
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(False)
    expect(scene.logged('landed away')).to_be(True)
    scene.area = 'surface'

    def correct_cave(op):
        scene.area = 'skavidCaves'
        scene.at = cave.landing

    scene.locs = []
    scene.loc('Cave', ['Enter'], id=WT_LOC.CAVE_IN[0], effect=correct_cave)
    expect(run_wait(caves.enter_cave(cave.index, scene.log))).to_be(True)
    expect(scene.at).to_equal(cave.landing)
    enter = spy_on(caves, 'enter_cave', impl=answer(False))
    expect(run_wait(caves.reach_skavid(1, scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(caves.reach_skavid(1, scene.log))).to_be(True)


test('a skavid cave entry must reach the requested room rather than the dark cave', cave_entries)


def cave_exits():
    scene = world(caves)
    expect(run_wait(caves.leave_cave(scene.log))).to_be(True)
    scene.area = 'skavidCaves'
    expect(run_wait(caves.leave_cave(scene.log))).to_be(False)
    scene.loc('Rope', ['Climb'], id=WT_LOC.DARK_CAVE_ESCAPE, effect=lambda op: False)
    expect(run_wait(caves.leave_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Climb'], id=WT_LOC.DARK_CAVE_ESCAPE, effect=move(scene, 'surface'))
    expect(run_wait(caves.leave_cave(scene.log))).to_be(True)
    scene.area = 'skavidCaves'
    scene.locs = []
    scene.loc('Exit', ['Leave'], id=WT_LOC.CAVE_OUT[0], effect=lambda op: False)
    expect(run_wait(caves.leave_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Exit', ['Leave'], id=WT_LOC.CAVE_OUT[0])
    expect(run_wait(caves.leave_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Exit', ['Leave'], id=WT_LOC.CAVE_OUT[0], effect=move(scene, 'surface'))
    expect(run_wait(caves.leave_cave(scene.log))).to_be(True)


test('ordinary cave exits and the dark-cave rope both require a landed escape', cave_exits)


def skavid_words():
    scene = world(caves)
    reached = spy_on(caves, 'reach_skavid', impl=answer(False))
    talk = spy_on(caves, 'talk_strict', impl=answer(False))
    left = spy_on(caves, 'leave_cave', impl=answer(True))
    for fn, args in [[caves.learn_from_scared_skavid, []], [caves.learn_word, [1]]]:
        reached.mock_implementation(answer(False))
        expect(run_wait(fn(*args, scene.log))).to_be(False)
        reached.mock_implementation(answer(True))
        expect(run_wait(fn(*args, scene.log))).to_be(False)
        talk.mock_implementation(answer(True))
        expect(run_wait(fn(*args, scene.log))).to_be(True)
        talk.mock_implementation(answer(False))
    expect(len(left.calls)).to_be(2)
    cross = spy_on(caves, 'cross_east_gate', impl=answer(False))
    expect(run_wait(caves.answer_mad_skavid(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    reached.mock_implementation(answer(False))
    expect(run_wait(caves.answer_mad_skavid(scene.log))).to_be(False)
    reached.mock_implementation(answer(True))
    talks = spy_on(caves, 'talk_choosing_by', impl=answer(True))
    east = spy_on(caves, 'leave_east_gate', impl=answer(True))
    expect(run_wait(caves.answer_mad_skavid(scene.log))).to_be(False)
    expect(len(talks.calls)).to_be(5)
    expect(len(east.calls)).to_be(1)
    scene.item(WT_ITEM.CRYSTAL2.id, WT_ITEM.CRYSTAL2.name)
    left.mock_implementation(answer(False))
    expect(run_wait(caves.answer_mad_skavid(scene.log))).to_be(False)
    left.mock_implementation(answer(True))
    expect(run_wait(caves.answer_mad_skavid(scene.log))).to_be(True)


test('skavid lessons leave their caves and the mad skavid gets five attempts then an escape', skavid_words)


def nightshade():
    scene = world(caves)
    enter = spy_on(caves, 'enter_cave', impl=answer(False))
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(False)
    scene.on_ground(WT_ITEM.NIGHTSHADE.id, WT_ITEM.NIGHTSHADE.name, effect=lambda op: True)
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(WT_ITEM.NIGHTSHADE.id, WT_ITEM.NIGHTSHADE.name)
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(True)
    expect(run_wait(caves.take_nightshade(scene.log))).to_be(True)


test('nightshade is gathered from cave two and must actually reach the pack', nightshade)


def enclave_entry():
    scene = world(enclave, 'enclave')
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(True)
    scene.area = 'surface'
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(False)
    scene.item(WT_ITEM.NIGHTSHADE.id, WT_ITEM.NIGHTSHADE.name)
    scene.walk_ok = False
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(False)
    scene.npc(WT_NPC.ENCLAVE_GUARD)
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(False)
    scene.pack = []
    scene.item(WT_ITEM.NIGHTSHADE.id, WT_ITEM.NIGHTSHADE.name, on_use=move(scene, 'enclave'))
    scene.chat.pages = ['continue']
    expect(run_wait(enclave.enter_enclave(scene.log))).to_be(True)
    expect(scene.area).to_be('enclave')


test('the enclave guard must be distracted with nightshade before crossing', enclave_entry)


def enclave_gathering():
    scene = world(enclave, 'enclave')
    enter = spy_on(enclave, 'enter_enclave', impl=answer(False))
    for fn in [enclave.mine_dalgroth, enclave.search_shaman_robe, enclave.dissolve_shamans]:
        expect(run_wait(fn(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    for fn in [enclave.mine_dalgroth, enclave.search_shaman_robe]:
        expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(enclave.mine_dalgroth(scene.log))).to_be(False)
    scene.loc('Rock', ['Mine'], id=WT_LOC.ROCK_OF_DALGROTH, effect=give(scene, WT_ITEM.CRYSTAL4))
    expect(run_wait(enclave.mine_dalgroth(scene.log))).to_be(True)
    expect(run_wait(enclave.mine_dalgroth(scene.log))).to_be(True)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(False)
    scene.on_ground(WT_ITEM.SHAMAN_ROBE.id, WT_ITEM.SHAMAN_ROBE.name, effect=lambda op: True)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(False)
    scene.ground = []
    scene.item(WT_ITEM.SHAMAN_ROBE.id, WT_ITEM.SHAMAN_ROBE.name, effect=lambda op: False)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(False)
    scene.take(WT_ITEM.SHAMAN_ROBE.id)

    def robe_taken(op):
        scene.item(WT_ITEM.SHAMAN_ROBE.id, WT_ITEM.SHAMAN_ROBE.name, effect=give(scene, WT_ITEM.CRYSTAL3))

    scene.on_ground(WT_ITEM.SHAMAN_ROBE.id, WT_ITEM.SHAMAN_ROBE.name, effect=robe_taken)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(True)
    expect(run_wait(enclave.search_shaman_robe(scene.log))).to_be(True)
    expect(run_wait(enclave.dissolve_shamans(scene.log))).to_be(True)
    expect(scene.logged('potion is spent')).to_be(True)
    scene.item(WT_ITEM.MAGIC_OGRE_POTION.id, WT_ITEM.MAGIC_OGRE_POTION.name)
    scene.walk_ok = False
    expect(run_wait(enclave.dissolve_shamans(scene.log))).to_be(True)
    scene.walk_ok = True
    expect(run_wait(enclave.dissolve_shamans(scene.log))).to_be(True)
    scene.npc(WT_NPC.SHAMAN, dist=2)
    expect(run_wait(enclave.dissolve_shamans(scene.log))).to_be(True)
    expect(scene.ticks > 0).to_be(True)


test('enclave crystals are mined, searched from the robe and dissolved with potion', enclave_gathering)


def city_offers():
    for fn, item, npc, end in [
        [gutanoth.offer_relic, WT_ITEM.OGRE_RELIC, WT_NPC.OGRE_GUARD, Tile(2500, 3060, 0)],
        [gutanoth.offer_gold_bar, WT_ITEM.GOLD_BAR, WT_NPC.OGRE_GUARD, Tile(2541, 3026, 0)],
    ]:
        scene = world(gutanoth)
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.item(item.id, item.name, on_use=lambda target: False)
        scene.npc(npc)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.pack = []
        scene.item(item.id, item.name)
        expect(run_wait(fn(scene.log))).to_be(False)

        def crosses(target):
            scene.at = end
            scene.chat.pages = ['continue']

        scene.pack = []
        scene.item(item.id, item.name, on_use=crosses)
        spy_on(gutanoth, 'talk_through', impl=answer(True))
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(scene.at).to_equal(end)
        restore_all()


test('both city gates accept the right gift and require the crossing to land', city_offers)


def gate_retries():
    for fn, offer_name, item in [
        [gutanoth.show_relic_to_guard, 'offer_relic', WT_ITEM.OGRE_RELIC],
        [gutanoth.cross_east_gate, 'offer_gold_bar', WT_ITEM.GOLD_BAR],
    ]:
        scene = world(gutanoth)
        spy_on(gutanoth, 'past_east_gate', returns=False)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.item(item.id, item.name)
        offer = spy_on(gutanoth, offer_name, impl=answer(False))
        expect(run_wait(fn(scene.log))).to_be(False)
        expect(len(offer.calls)).to_be(2)
        offer.mock_implementation(answer(True))
        expect(run_wait(fn(scene.log))).to_be(True)
        attempts = []

        def second(log):
            attempts.append(True)
            return len(attempts) == 2
            yield

        offer.mock_implementation(second)
        expect(run_wait(fn(scene.log))).to_be(True)
        expect(len(attempts)).to_be(2)
        restore_all()


test('city gate guards can throw the player down the hill once before accepting', gate_retries)


def rock_cake():
    scene = world(gutanoth)
    scene.walk_ok = False
    expect(run_wait(gutanoth.steal_rock_cake(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gutanoth.steal_rock_cake(scene.log))).to_be(False)
    expect(scene.logged('ogre trader')).to_be(True)
    scene.loc('Stall', ['Steal-From'], id=WT_LOC.ROCK_CAKE_STALL, effect=give(scene, WT_ITEM.ROCK_CAKE))
    expect(run_wait(gutanoth.steal_rock_cake(scene.log))).to_be(True)
    expect(run_wait(gutanoth.steal_rock_cake(scene.log))).to_be(True)


test('rock cake stealing retries an empty or guarded stall', rock_cake)


def battlement():
    scene = world(gutanoth, 'lowerCity')
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(True)
    scene.area = 'surface'
    scene.walk_ok = False
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(False)
    scene.npc(WT_NPC.OGRE_GUARD, ['Talk-to'])
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(False)
    scene.item(WT_ITEM.ROCK_CAKE.id, WT_ITEM.ROCK_CAKE.name, on_use=move(scene, 'lowerCity'))
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(True)
    scene.area = 'surface'
    scene.pack = []
    scene.loc('Battlement', ['Climb-over'], id=WT_LOC.BATTLEMENT)
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Battlement', ['Climb-over'], id=WT_LOC.BATTLEMENT, effect=move(scene, 'lowerCity'))
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(True)
    scene.area = 'surface'
    scene.chat.pages = ['continue']
    spy_on(gutanoth, 'talk_strict', impl=answer(True))
    scene.npcs = []
    scene.npc(WT_NPC.OGRE_GUARD, ['Talk-to'], effect=move(scene, 'lowerCity'))
    expect(run_wait(gutanoth.cross_battlement(scene.log))).to_be(True)


test('the battlement accepts a gift in dialogue or is climbed after payment', battlement)


def chasm_and_riddle():
    scene = world(gutanoth, 'cityGuard')
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(True)
    scene.area = 'surface'
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    scene.item(WT_ITEM.COINS.id, 'Coins', count=20)
    cross = spy_on(gutanoth, 'cross_battlement', impl=answer(False))
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    cross.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    scene.loc('Rock', ['Jump-From'], id=WT_LOC.JUMP_IN)
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    scene.chat.pages = ['continue']
    talk = spy_on(gutanoth, 'talk_strict', impl=answer(False))
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rock', ['Jump-From'], id=WT_LOC.JUMP_IN, effect=move(scene, 'cityGuard'))
    expect(run_wait(gutanoth.jump_chasm(scene.log))).to_be(True)
    jump = spy_on(gutanoth, 'jump_chasm', impl=answer(False))
    expect(run_wait(gutanoth.ask_riddle(scene.log))).to_be(False)
    expect(run_wait(gutanoth.answer_riddle(scene.log))).to_be(False)
    scene.item(WT_ITEM.DEATH_RUNE.id, 'Death rune')
    expect(run_wait(gutanoth.answer_riddle(scene.log))).to_be(False)
    jump.mock_implementation(answer(True))
    scene.talk_status = 'unreachable'
    expect(run_wait(gutanoth.ask_riddle(scene.log))).to_be(False)
    scene.talk_status = 'done'
    expect(run_wait(gutanoth.ask_riddle(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(gutanoth.answer_riddle(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gutanoth.answer_riddle(scene.log))).to_be(False)
    scene.npc(WT_NPC.CITY_GUARD)
    scene.take(WT_ITEM.DEATH_RUNE.id)
    scene.item(WT_ITEM.DEATH_RUNE.id, 'Death rune', on_use=give(scene, WT_ITEM.SKAVID_MAP))
    spy_on(gutanoth, 'talk_through', impl=answer(True))
    expect(run_wait(gutanoth.answer_riddle(scene.log))).to_be(True)
    expect(scene.has(WT_ITEM.SKAVID_MAP.id)).to_be(True)


test('the chasm needs its toll and the riddle is answered with a Death rune', chasm_and_riddle)


def east_exit():
    scene = world(gutanoth)
    past = spy_on(gutanoth, 'past_east_gate', returns=False)
    expect(run_wait(gutanoth.leave_east_gate(scene.log))).to_be(True)
    past.mock_return_value(True)
    expect(run_wait(gutanoth.cross_east_gate(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(gutanoth.leave_east_gate(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(gutanoth.leave_east_gate(scene.log))).to_be(False)
    scene.loc('Gate', ['Open'], id=WT_LOC.GATE_EAST)
    expect(run_wait(gutanoth.leave_east_gate(scene.log))).to_be(False)
    scene.locs = []

    def out(op):
        scene.at = Tile(2540, 3030, 0)

    scene.loc('Gate', ['Open'], id=WT_LOC.GATE_EAST, effect=out)
    expect(run_wait(gutanoth.leave_east_gate(scene.log))).to_be(True)


test('the paid east gate opens for the return trip', east_exit)

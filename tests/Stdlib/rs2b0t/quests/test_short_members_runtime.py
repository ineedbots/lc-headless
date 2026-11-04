"""Druidic Ritual, Monk's Friend, Jungle Potion and the Carnillean side of Hazeel Cult."""

import rs2004.quests.defs.druidicritual as ritual
import rs2004.quests.defs.hazeelcult as cult
import rs2004.quests.defs.junglepotion as jungle
import rs2004.quests.defs.monksfriend as monk
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.entities import npcs
from rs2004.tabs import quests


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def restart_boundaries():
    scene = Scene(ritual.CAULDRON_DOOR_OUTSIDE)
    spy_on(ritual, 'walk_with_hops', impl=answer(True))
    expect(run_wait(ritual.leave_dungeon(scene.log))).to_be(True)
    scene.at = Tile(1, 1, 0)
    expect(run_wait(ritual.leave_dungeon(scene.log))).to_be(True)
    meat = ritual.RITUAL_MEATS[0]
    spy_on(game, 'in_combat', returns=True)
    spy_on(ritual, 'wait_with_upkeep', impl=answer(True))
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(False)
    leave = spy_on(cult, 'leave_hideout', impl=answer(False))
    stop = Fake(npc='Ceril', prefer=[])
    errand = cult.chat(stop)
    expect(run_wait(errand(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    goto = spy_on(cult, 'goto_npc', impl=answer(False))
    expect(run_wait(errand(scene.log))).to_be(False)
    goto.mock_implementation(answer(True))
    spy_on(cult, 'talk_strict', impl=answer(True))
    expect(run_wait(errand(scene.log))).to_be(True)
    status = spy_on(quests, 'status', returns='complete')
    expect(run_wait(cult.read_hazeel_progress()).stage).to_be(cult.HC_STAGE.COMPLETE)
    status.mock_return_value('not_started')
    expect(run_wait(cult.read_hazeel_progress()).stage).to_be(cult.HC_STAGE.NOT_STARTED)
    status.mock_return_value('unknown')
    expect(run_wait(cult.read_hazeel_progress())).to_be_null()
    scene.item(cult.ARMOUR_OBJ, 'Carnillean armour')
    expect(run_wait(cult.take_armour(scene.log))).to_be(True)


test('ritual and cult restarts leave sealed pockets and stop before unreachable conversations', restart_boundaries)


def give(scene, id, name):
    def effect(*args):
        scene.item(id, name)
    return effect


def ritual_hunting():
    scene = Scene(ritual.RITUAL_MEATS[0].anchor)
    spy_on(game, 'set_combat_style', returns=None)
    spy_on(game, 'facing', returns=None)
    meat = ritual.RITUAL_MEATS[0]
    scene.walk_ok = False
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(False)
    scene.npc(meat.npc, ['Attack'], id=meat.npc_id, effect=lambda op: False)
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(False)
    scene.npcs = []

    def killed(op):
        scene.npcs = []
        scene.on_ground(123, meat.raw)

    scene.npc(meat.npc, ['Attack'], id=meat.npc_id, effect=killed)
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(True)
    expect(run_wait(ritual.hunt_meat(meat, scene.log))).to_be(True)
    scene.pack = []
    scene.on_ground(123, meat.raw, effect=lambda op: False)
    expect(run_wait(ritual.take_meat_drop(meat))).to_be(False)
    scene.ground = []
    expect(run_wait(ritual.wait_with_upkeep(lambda: False, 1200))).to_be(False)


test('ritual meat hunting attacks an available animal and waits for its guaranteed drop', ritual_hunting)


def cauldron():
    scene = Scene(ritual.DUNGEON_LADDER)
    spy_on(game, 'facing', returns=None)
    expect(run_wait(ritual.fight_living_suit(scene.log))).to_be(False)
    scene.npc('Suit of armour', ['Attack'], id=ritual.SUIT_OF_ARMOUR_ID, effect=lambda op: False)
    expect(run_wait(ritual.fight_living_suit(scene.log))).to_be(True)
    scene.npcs = []
    scene.npc('Suit of armour', ['Attack'], id=ritual.SUIT_OF_ARMOUR_ID)
    expect(run_wait(ritual.fight_living_suit(scene.log))).to_be(True)
    scene.npcs = []
    scene.walk_ok = False
    expect(run_wait(ritual.enter_cauldron_room(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.at = ritual.CAULDRON_DOOR_OUTSIDE
    scene.loc('Prison door', ['Open'], effect=lambda op: False)
    expect(run_wait(ritual.enter_cauldron_room(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Prison door', ['Open'])
    expect(run_wait(ritual.enter_cauldron_room(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Prison door', ['Open'], effect=lambda op: scene.locs.clear())
    spy_on(direct_navigator, 'walk_to', impl=scene._walk)
    expect(run_wait(ritual.enter_cauldron_room(scene.log))).to_be(True)
    for meat in ritual.RITUAL_MEATS:
        scene.pack = []
        expect(run_wait(ritual.dip_meat(meat, scene.log))).to_be(False)
        scene.item(1, meat.raw)
        expect(run_wait(ritual.dip_meat(meat, scene.log))).to_be(False)
        scene.loc('Cauldron', id=ritual.CAULDRON_ID)
        scene.pack = []
        scene.item(1, meat.raw, on_use=lambda target: False)
        expect(run_wait(ritual.dip_meat(meat, scene.log))).to_be(False)

        def enchanted(target):
            scene.pack = []
            scene.item(2, meat.enchanted)

        scene.pack = []
        scene.item(1, meat.raw, on_use=enchanted)
        expect(run_wait(ritual.dip_meat(meat, scene.log))).to_be(True)
        expect(run_wait(ritual.dip_meat(meat, scene.log))).to_be(True)
        scene.locs = []


test('the cauldron room clears its animated guard and transforms each raw meat', cauldron)


def monk_cave():
    scene = Scene(monk.RING_STAND)
    scene.walk_ok = False
    expect(run_wait(monk.enter_cave(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(monk.enter_cave(scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-down'], tile=monk.RING_STAND, effect=lambda op: False)
    expect(run_wait(monk.enter_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Ladder', ['Climb-down'], tile=monk.RING_STAND)
    expect(run_wait(monk.enter_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Ladder', ['Climb-down'], tile=monk.RING_STAND,
              effect=lambda op: setattr(scene, 'at', monk.CAVE_FOOT))
    expect(run_wait(monk.enter_cave(scene.log))).to_be(True)
    expect(run_wait(monk.enter_cave(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(monk.fetch_blanket(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(monk.fetch_blanket(scene.log))).to_be(False)
    scene.on_ground(monk.BLANKET_OBJ, monk.BLANKET, effect=lambda op: False)
    expect(run_wait(monk.fetch_blanket(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(monk.BLANKET_OBJ, monk.BLANKET)
    expect(run_wait(monk.fetch_blanket(scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-up'], tile=monk.CAVE_LADDER,
              effect=lambda op: setattr(scene, 'at', monk.RING_STAND))
    expect(run_wait(monk.fetch_blanket(scene.log))).to_be(True)
    expect(scene.has(monk.BLANKET_OBJ)).to_be(True)


test('the hidden monk ladder must appear and the blanket is carried back to the surface', monk_cave)


def monk_logs_and_party():
    scene = Scene(monk.TREE)
    hops = spy_on(monk, 'walk_with_hops', impl=answer(False))
    expect(run_wait(monk.chop_logs(scene.log))).to_be(False)
    hops.mock_implementation(answer(True))
    expect(run_wait(monk.chop_logs(scene.log))).to_be(False)
    scene.loc('Tree', ['Chop down'], effect=lambda op: False)
    expect(run_wait(monk.chop_logs(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Tree', ['Chop down'])
    expect(run_wait(monk.chop_logs(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Tree', ['Chop down'], effect=give(scene, 1, 'Logs'))
    expect(run_wait(monk.chop_logs(scene.log))).to_be(True)
    expect(run_wait(monk.chop_logs(scene.log))).to_be(True)
    leave = spy_on(monk, 'leave_cave', impl=answer(False))
    expect(run_wait(monk.throw_party(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    hops.mock_implementation(answer(False))
    expect(run_wait(monk.throw_party(scene.log))).to_be(False)
    hops.mock_implementation(answer(True))
    talk = spy_on(monk, 'talk_strict', impl=answer(False))
    expect(run_wait(monk.throw_party(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(monk.throw_party(scene.log))).to_be(False)
    scene.status = 'complete'
    expect(run_wait(monk.throw_party(scene.log))).to_be(True)


test('monk logs retry slow chops and the party waits until the quest turns green', monk_logs_and_party)


def jungle_herbs():
    scene = Scene(jungle.TRUFITUS)
    prompt = spy_on(jungle, 'prompt_loc', impl=answer(False))
    expect(run_wait(jungle.enter_pothole(scene.log))).to_be(False)
    prompt.mock_implementation(answer(True))
    expect(run_wait(jungle.enter_pothole(scene.log))).to_be(True)
    scene.at = jungle.POTHOLE_EXIT.stand
    expect(run_wait(jungle.enter_pothole(scene.log))).to_be(True)
    expect(run_wait(jungle.leave_pothole(scene.log))).to_be(True)
    scene.at = jungle.TRUFITUS
    expect(run_wait(jungle.leave_pothole(scene.log))).to_be(True)
    for herb in jungle.JUNGLE_HERBS:
        expect(run_wait(jungle.pick_herb(herb)(scene.log))).to_be(True)
        expect(run_wait(jungle.identify_herb(herb)(scene.log))).to_be(False)
        scene.item(herb.unid_id, 'Herb', effect=lambda op: False)
        expect(run_wait(jungle.pick_herb(herb)(scene.log))).to_be(True)
        expect(run_wait(jungle.identify_herb(herb)(scene.log))).to_be(False)
        scene.take(herb.unid_id)
        scene.item(herb.unid_id, 'Herb', effect=give(scene, herb.id, herb.name))
        expect(run_wait(jungle.identify_herb(herb)(scene.log))).to_be(True)
        expect(run_wait(jungle.identify_herb(herb)(scene.log))).to_be(True)
        scene.pack = []
    scene.walk_ok = False
    expect(run_wait(jungle.start_quest(scene.log))).to_be(False)
    scene.walk_ok = True
    spy_on(jungle, 'talk_strict', impl=answer(True))
    expect(run_wait(jungle.start_quest(scene.log))).to_be(True)
    expect(run_wait(jungle.hand_in_herb(scene.log))).to_be(True)


test('Jungle Potion gathers fresh unidentified herbs and identifies all five before hand-in', jungle_herbs)


def cult_raft():
    scene = Scene(cult.FOREST_TOP)
    expect(run_wait(cult.board_raft(4, scene.log))).to_be(False)
    scene.loc('Raft', id=cult.RAFT_LOC, effect=lambda op: False)
    expect(run_wait(cult.board_raft(4, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Raft', id=cult.RAFT_LOC)
    expect(run_wait(cult.board_raft(4, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Raft', id=cult.RAFT_LOC, effect=lambda op: setattr(scene, 'at', cult.ALOMONE_TILE))
    expect(run_wait(cult.board_raft(4, scene.log))).to_be(True)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(cult.turn_valves(scene.log))).to_be(False)
    scene.loc_op_status = 'timeout'
    expect(run_wait(cult.turn_valves(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(cult.turn_valves(scene.log))).to_be(True)
    expect(len(scene.loc_ops) >= 5).to_be(True)
    expect(run_wait(cult.to_hideout(scene.log))).to_be(True)
    scene.at = None
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    scene.at = Tile(2580, 9680, 0)
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    scene.at = cult.SEWER_LANDING
    stub(cult, valves_turned=False)
    spy_on(cult, 'walk_with_hops', impl=answer(True))
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    scene.at = cult.FOREST_TOP
    turn = spy_on(cult, 'turn_valves', impl=answer(False))
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    turn.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    scene.walk_ok = True
    ride = spy_on(cult, 'board_raft', impl=answer(False))
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    ride.mock_implementation(answer(True))
    expect(run_wait(cult.to_hideout(scene.log))).to_be(False)
    expect(cult.valves_turned).to_be(False)


test('Hazeel raft travel resets the five valves when a ride refuses or stops on an island', cult_raft)


def cult_armour():
    scene = Scene(cult.ALOMONE_TILE)
    spy_on(game, 'set_combat_style', returns=None)
    spy_on(game, 'facing', returns=None)
    spy_on(npcs, 'all', impl=lambda: scene.npcs)
    scene.walk_ok = False
    expect(run_wait(cult.slay_alomone(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(cult.slay_alomone(scene.log))).to_be(False)
    scene.npc('Alomone', ['Attack'], effect=lambda op: False)
    expect(run_wait(cult.slay_alomone(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Alomone', ['Attack'])
    expect(run_wait(cult.slay_alomone(scene.log))).to_be(False)
    scene.npcs = []
    scene.npc('Alomone', ['Attack'], effect=lambda op: scene.npcs.clear())
    expect(run_wait(cult.slay_alomone(scene.log))).to_be(True)
    enter = spy_on(cult, 'to_hideout', impl=answer(False))
    expect(run_wait(cult.fetch_armour(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    fight = spy_on(cult, 'slay_alomone', impl=answer(False))
    expect(run_wait(cult.fetch_armour(scene.log))).to_be(False)
    fight.mock_implementation(answer(True))
    scene.later(lambda: scene.on_ground(cult.ARMOUR_OBJ, cult.ARMOUR_NAME))
    expect(run_wait(cult.fetch_armour(scene.log))).to_be(True)
    expect(run_wait(cult.fetch_armour(scene.log))).to_be(True)


test('Alomone is killed again if his armour despawned and the delayed drop is picked up', cult_armour)


def cult_cupboard():
    scene = Scene(cult.FOREST_TOP)
    expect(run_wait(cult.leave_hideout(scene.log))).to_be(True)
    expect(run_wait(cult.to_surface(scene.log))).to_be(True)
    scene.at = cult.ALOMONE_TILE
    scene.walk_ok = False
    expect(run_wait(cult.leave_hideout(scene.log))).to_be(False)
    leave = spy_on(cult, 'leave_hideout', impl=answer(False))
    expect(run_wait(cult.to_surface(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    spy_on(cult, 'walk_with_hops', impl=answer(True))
    expect(run_wait(cult.to_surface(scene.log))).to_be(True)
    scene.loc_op_status = 'unreachable'
    expect(run_wait(cult.open_cupboard(scene.log))).to_be(False)
    scene.loc_op_status = 'timeout'
    expect(run_wait(cult.open_cupboard(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(cult.open_cupboard(scene.log))).to_be(True)
    scene.loc('Cupboard', id=cult.CUPBOARD_OPEN)
    expect(run_wait(cult.open_cupboard(scene.log))).to_be(True)
    expect(run_wait(cult.drive_to_complete(scene.log))).to_be(False)
    surface = spy_on(cult, 'to_surface', impl=answer(False))
    expect(run_wait(cult.search_cupboard(scene.log))).to_be(False)
    surface.mock_implementation(answer(True))
    open = spy_on(cult, 'open_cupboard', impl=answer(False))
    expect(run_wait(cult.search_cupboard(scene.log))).to_be(False)
    open.mock_implementation(answer(True))
    scene.loc_op_status = 'unreachable'
    expect(run_wait(cult.search_cupboard(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    scene.status = 'complete'
    expect(run_wait(cult.search_cupboard(scene.log))).to_be(True)
    expect(run_wait(cult.drive_to_complete(scene.log))).to_be(True)


test('Jones cupboard is searched after escaping the hideout and quiet accusations are retried', cult_cupboard)

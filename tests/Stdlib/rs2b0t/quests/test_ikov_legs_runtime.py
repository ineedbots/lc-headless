"""Ikov dungeon and guardian legs, including failed crossings and interrupted fights."""

import _core
from rs2004.game import direct_navigator, game
from rs2004.items import equipment
from rs2004.quests.defs.ikov import dungeon, fight, temple
from rs2004.quests.defs.ikov.areas import ARROWS_WANTED, ICE_CHESTS, IKOV_LOC, IKOV_NAME, IKOV_NPC, IKOV_OBJ, IKOV_TILE
from rs2004.execution import event_signal


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id, name='Quest item'):
    def effect(*args):
        scene.item(id, name)
    return effect


def land(scene, at):
    def effect(*args):
        scene.at = at
    return effect


def world():
    scene = Scene(IKOV_TILE.SOUTH_GATE_NORTH)
    spy_on(game, 'weight', returns=-2)
    spy_on(game, 'set_combat_mode', returns=None)
    spy_on(game, 'set_auto_retaliate', returns=None)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(direct_navigator, 'walk_to', impl=answer(True))
    return scene


def fear_pendant():
    scene = world()
    expect(run_wait(dungeon.wear_fear_pendant(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.PENDANT_LUCIEN, IKOV_NAME.PENDANT_LUCIEN)
    expect(run_wait(dungeon.wear_fear_pendant(scene.log))).to_be(True)
    expect(run_wait(dungeon.wear_fear_pendant(scene.log))).to_be(True)
    expect(equipment.contains(IKOV_NAME.PENDANT_LUCIEN)).to_be(True)


test('the Door of Fear needs the pendant worn rather than merely carried', fear_pendant)


def bridge_safety():
    scene = world()
    scene.at = IKOV_TILE.BRIDGE_EAST
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(False)
    scene.wear(IKOV_NAME.BOOTS)
    weight = spy_on(game, 'weight', returns=0)
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(False)
    weight.mock_return_value(-1)
    scene.walk_ok = False
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(False)
    scene.walk_ok = True
    click = spy_on(_core, 'walk_to', returns=True)
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(False)
    click.mock_implementation(land(scene, IKOV_TILE.BRIDGE_WEST))
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(True)
    before = len(click.calls)
    expect(run_wait(dungeon.cross_bridge(True, scene.log))).to_be(True)
    expect(len(click.calls)).to_be(before)


test('the lava bridge refuses missing boots and nonnegative weight and confirms the far bank', bridge_safety)


def stairs():
    for fn, id, start in [
        [dungeon.climb_dark_stairs_up, IKOV_LOC.DARK_STAIRS_UP, IKOV_TILE.BOOTS_SPAWN],
        [dungeon.climb_trap_ladder, IKOV_LOC.TRAP_LADDER, IKOV_TILE.TRAP_PIT_LADDER],
    ]:
        scene = world()
        scene.at = start
        scene.walk_ok = False
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.loc('Exit', ['Climb-up'], id=id)
        expect(run_wait(fn(scene.log))).to_be(False)
        scene.locs = []
        scene.loc('Exit', ['Climb-up'], id=id, effect=land(scene, IKOV_TILE.SOUTH_GATE_NORTH))
        expect(run_wait(fn(scene.log))).to_be(True)
        restore_all()
    scene = world()
    scene.at = None
    expect(run_wait(dungeon.escape_pocket(scene.log))).to_be(False)
    for at, name in [[IKOV_TILE.BOOTS_SPAWN, 'climb_dark_stairs_up'],
                     [IKOV_TILE.TRAP_PIT_LADDER, 'climb_trap_ladder'],
                     [IKOV_TILE.BRIDGE_WEST, 'cross_bridge']]:
        scene.at = at
        called = spy_on(dungeon, name, impl=answer(True))
        expect(run_wait(dungeon.escape_pocket(scene.log))).to_be(True)
        expect(len(called.calls)).to_be(1)
    scene.at = IKOV_TILE.SOUTH_GATE_NORTH
    expect(run_wait(dungeon.escape_pocket(scene.log))).to_be(True)


test('sealed dungeon pockets leave by their own stairs, ladder or bridge', stairs)


def web_and_boots():
    scene = world()
    expect(run_wait(dungeon.slash_web(scene.log))).to_be(True)
    scene.loc('Web', id=IKOV_LOC.WEB)
    expect(run_wait(dungeon.slash_web(scene.log))).to_be(False)
    scene.item(IKOV_OBJ.KNIFE, 'Knife', on_use=lambda target: False)
    expect(run_wait(dungeon.slash_web(scene.log))).to_be(False)
    scene.pack = []
    scene.item(IKOV_OBJ.KNIFE, 'Knife')
    expect(run_wait(dungeon.slash_web(scene.log))).to_be(False)
    expect(scene.logged('eight cuts')).to_be(True)
    scene.pack = []

    def slash(target):
        scene.locs = []

    scene.item(IKOV_OBJ.KNIFE, 'Knife', on_use=slash)
    expect(run_wait(dungeon.slash_web(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(dungeon.take_boots(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.take_boots(scene.log))).to_be(False)
    scene.on_ground(IKOV_OBJ.BOOTS, IKOV_NAME.BOOTS, effect=lambda op: False)
    expect(run_wait(dungeon.take_boots(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(IKOV_OBJ.BOOTS, IKOV_NAME.BOOTS)
    expect(run_wait(dungeon.take_boots(scene.log))).to_be(True)
    expect(run_wait(dungeon.take_boots(scene.log))).to_be(True)
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(True)
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(True)


test('the web needs a knife and the boots must be taken then equipped', web_and_boots)


def boots_descent():
    scene = world()
    escape = spy_on(dungeon, 'escape_pocket', impl=answer(False))
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    escape.mock_implementation(answer(True))
    light = spy_on(dungeon, 'light_candle', impl=answer(False))
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    light.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    scene.loc('Stairs', ['Climb-down'], id=IKOV_LOC.DARK_STAIRS_DOWN)
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Stairs', ['Climb-down'], id=IKOV_LOC.DARK_STAIRS_DOWN, effect=land(scene, IKOV_TILE.BOOTS_SPAWN))
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(True)
    take = spy_on(dungeon, 'take_boots', impl=answer(False))
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(False)
    take.mock_implementation(answer(True))
    spy_on(equipment, 'equip', impl=answer(False))
    spy_on(dungeon, 'climb_dark_stairs_up', impl=answer(True))
    expect(run_wait(dungeon.fetch_boots(scene.log))).to_be(True)
    expect(scene.logged('could not wear')).to_be(True)


test('the boots errand descends only with a lit candle and recovers from a dark-room restart', boots_descent)


def trap_lever():
    scene = world()
    escape = spy_on(dungeon, 'escape_pocket', impl=answer(False))
    pendant = spy_on(dungeon, 'wear_fear_pendant', impl=answer(False))
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    escape.mock_implementation(answer(True))
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    pendant.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    scene.loc('Lever', id=IKOV_LOC.TRAP_LEVER, effect=lambda op: False)
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', id=IKOV_LOC.TRAP_LEVER, effect=lambda op: op != 'Pull')
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', id=IKOV_LOC.TRAP_LEVER)
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(True)
    scene.locs = []
    scene.loc('Lever', id=IKOV_LOC.TRAP_LEVER, effect=land(scene, IKOV_TILE.TRAP_PIT_LADDER))
    climb = spy_on(dungeon, 'climb_trap_ladder', impl=answer(True))
    expect(run_wait(dungeon.pull_trap_lever(scene.log))).to_be(True)
    expect(len(climb.calls)).to_be(1)


test('the trap lever is searched then pulled and a fired trap triggers the escape ladder', trap_lever)


def lever_repair():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(dungeon.take_ikov_lever(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.take_ikov_lever(scene.log))).to_be(False)
    scene.on_ground(IKOV_OBJ.LEVER, 'Lever', effect=lambda op: False)
    expect(run_wait(dungeon.take_ikov_lever(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(IKOV_OBJ.LEVER, 'Lever')
    expect(run_wait(dungeon.take_ikov_lever(scene.log))).to_be(True)
    escape = spy_on(dungeon, 'escape_pocket', impl=answer(False))
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    escape.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.loc('Bracket', id=IKOV_LOC.LEVER_BRACKET)
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.LEVER)
    scene.item(IKOV_OBJ.LEVER, 'Lever', on_use=lambda target: False)
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.LEVER)
    scene.item(IKOV_OBJ.LEVER, 'Lever', on_use=lambda target: scene.take(IKOV_OBJ.LEVER))
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.loc('Lever', id=IKOV_LOC.MENDED_LEVER, effect=lambda op: False)
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Lever', id=IKOV_LOC.MENDED_LEVER)
    expect(run_wait(dungeon.mend_and_pull_lever(scene.log))).to_be(True)


test('the spare lever must be fitted and consumed before the mended lever is pulled', lever_repair)


def lever_errand():
    scene = world()
    scene.at = None
    expect(run_wait(dungeon.fetch_ikov_lever(scene.log))).to_be(False)
    scene.at = IKOV_TILE.BRIDGE_EAST
    steps = []
    for name in ['escape_pocket', 'wear_fear_pendant', 'cross_bridge', 'take_ikov_lever']:
        step = spy_on(dungeon, name, impl=answer(False))
        steps.append(step)
        expect(run_wait(dungeon.fetch_ikov_lever(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(dungeon.fetch_ikov_lever(scene.log))).to_be(True)
    scene.item(IKOV_OBJ.LEVER, 'Lever')
    expect(run_wait(dungeon.fetch_ikov_lever(scene.log))).to_be(True)
    scene.at = IKOV_TILE.BRIDGE_WEST
    expect(run_wait(dungeon.fetch_ikov_lever(scene.log))).to_be(True)
    expect(steps[2].calls[-1][0]).to_be(False)


test('the spare lever trip crosses the bridge back even when restarting with it in hand', lever_errand)


def chests():
    scene = world()
    chest = ICE_CHESTS[0]
    scene.walk_ok = False
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(False)
    scene.loc('Chest', id=IKOV_LOC.CHEST_SHUT, effect=lambda op: False)
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Chest', id=IKOV_LOC.CHEST_SHUT)
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Chest', id=IKOV_LOC.CHEST_OPEN, effect=lambda op: False)
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Chest', id=IKOV_LOC.CHEST_OPEN, effect=give(scene, 25, IKOV_NAME.ICE_ARROWS))
    expect(run_wait(dungeon.search_chest(chest, scene.log))).to_be(True)
    scene.locs = []
    expect(run_wait(dungeon.search_ice_chests(scene.log))).to_be(False)
    scene.loc('Chest', id=IKOV_LOC.CHEST_OPEN, effect=give(scene, 25, IKOV_NAME.ICE_ARROWS))
    expect(run_wait(dungeon.search_ice_chests(scene.log))).to_be(True)
    expect(len([i for i in scene.pack if i.name == IKOV_NAME.ICE_ARROWS]) >= ARROWS_WANTED).to_be(True)


test('ice chests must open and arrow circuits re-search a chest after a successful find', chests)


def south_gate():
    scene = world()
    stub(dungeon, south_gate_seen_open=False)
    scene.walk_ok = False
    expect(run_wait(dungeon.enter_ice_cavern(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(dungeon.enter_ice_cavern(scene.log))).to_be(False)
    scene.loc('Gate', id=IKOV_LOC.SOUTH_GATE_LEFT, effect=land(scene, IKOV_TILE.SOUTH_GATE_SOUTH))
    expect(run_wait(dungeon.enter_ice_cavern(scene.log))).to_be(True)
    expect(dungeon.south_gate_open()).to_be(True)
    expect(run_wait(dungeon.enter_ice_cavern(scene.log))).to_be(True)
    scene.at = IKOV_TILE.SOUTH_GATE_NORTH
    scene.locs = []
    spy_on(direct_navigator, 'walk_to', impl=scene._walk)
    expect(run_wait(dungeon.enter_ice_cavern(scene.log))).to_be(True)


test('the south gate is remembered open only after standing inside the ice cavern', south_gate)


def gate_workflows():
    scene = world()
    spy_on(dungeon, 'wearing_boots', returns=True)
    for name in ['escape_pocket', 'enter_ice_cavern', 'fetch_ikov_lever', 'mend_and_pull_lever']:
        step = spy_on(dungeon, name, impl=answer(False))
        expect(run_wait(dungeon.unlock_south_gate(scene.log))).to_be(False)
        if name != 'enter_ice_cavern':
            step.mock_implementation(answer(True))
    enter = spy_on(dungeon, 'enter_ice_cavern', impl=answer(True))
    expect(run_wait(dungeon.unlock_south_gate(scene.log))).to_be(True)
    escape = spy_on(dungeon, 'escape_pocket', impl=answer(False))
    expect(run_wait(dungeon.stock_ice_arrows(scene.log))).to_be(False)
    escape.mock_implementation(answer(True))
    enter.mock_implementation(answer(False))
    expect(run_wait(dungeon.stock_ice_arrows(scene.log))).to_be(False)
    expect(dungeon.south_gate_open()).to_be(False)
    enter.mock_implementation(answer(True))
    search = spy_on(dungeon, 'search_ice_chests', impl=answer(True))
    expect(run_wait(dungeon.stock_ice_arrows(scene.log))).to_be(True)
    expect(len(search.calls)).to_be(1)


test('gate unlocking and arrow stocking stop on each failed prerequisite', gate_workflows)


def guardian_key_and_colours():
    scene = world()
    scene.walk_ok = False
    expect(run_wait(temple.take_shiny_key(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(temple.take_shiny_key(scene.log))).to_be(False)
    scene.on_ground(IKOV_OBJ.SHINY_KEY, 'Key', effect=lambda op: False)
    expect(run_wait(temple.take_shiny_key(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(IKOV_OBJ.SHINY_KEY, 'Key')
    expect(run_wait(temple.take_shiny_key(scene.log))).to_be(True)
    expect(run_wait(temple.take_shiny_key(scene.log))).to_be(True)
    scene.wear(IKOV_NAME.PENDANT_LUCIEN)
    unequip = spy_on(equipment, 'unequip', impl=answer(False))
    expect(run_wait(temple.shed_lucien_colours(scene.log))).to_be(False)
    unequip.mock_implementation(scene._unequip)
    scene.item(IKOV_OBJ.STAFF, 'Staff')
    expect(run_wait(temple.shed_lucien_colours(scene.log))).to_be(False)
    scene.take(IKOV_OBJ.STAFF)
    expect(run_wait(temple.shed_lucien_colours(scene.log))).to_be(True)


test('the guardian route takes the shiny key and removes hostile equipment', guardian_key_and_colours)


def winelda():
    scene = world()
    ledge = spy_on(temple, 'on_winelda_ledge', returns=False)
    expect(run_wait(temple.ensure_across_the_lava(scene.log))).to_be(True)
    ledge.mock_return_value(True)
    scene.walk_ok = False
    expect(run_wait(temple.ensure_across_the_lava(scene.log))).to_be(False)
    scene.walk_ok = True
    talk = spy_on(temple, 'talk_strict', impl=answer(False))
    expect(run_wait(temple.ensure_across_the_lava(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    expect(run_wait(temple.ensure_across_the_lava(scene.log))).to_be(False)
    scene.later(lambda: ledge.mock_return_value(False))
    expect(run_wait(temple.ensure_across_the_lava(scene.log))).to_be(True)


test('Winelda is asked to ferry again if her delayed teleport never arrives', winelda)


def secret_wall():
    scene = world()
    inside = spy_on(temple, 'in_guardian_temple', returns=False)
    expect(run_wait(temple.push_secret_wall(False, scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(temple.push_secret_wall(True, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(temple.push_secret_wall(True, scene.log))).to_be(False)
    scene.loc('Wall', id=IKOV_LOC.SECRET_WALL, effect=lambda op: False)
    expect(run_wait(temple.push_secret_wall(True, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Wall', id=IKOV_LOC.SECRET_WALL, effect=lambda op: inside.mock_return_value(True))
    expect(run_wait(temple.push_secret_wall(True, scene.log))).to_be(True)
    inside.mock_return_value(False)
    scene.locs = []

    def through(*args):
        inside.mock_return_value(True)
        return True
        yield

    spy_on(direct_navigator, 'walk_to', impl=through)
    expect(run_wait(temple.push_secret_wall(True, scene.log))).to_be(True)


test('the secret wall teleports through or permits the final step after opening', secret_wall)


def guardian_workflow():
    scene = world()
    for name in ['escape_pocket', 'ensure_across_the_lava', 'take_shiny_key', 'shed_lucien_colours', 'push_secret_wall', 'temple_walk', 'talk_strict']:
        step = spy_on(temple, name, impl=answer(False))
        expect(run_wait(temple.join_the_guardians(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    expect(run_wait(temple.join_the_guardians(scene.log))).to_be(False)
    scene.later(give(scene, IKOV_OBJ.PENDANT_ARMADYL))
    expect(run_wait(temple.join_the_guardians(scene.log))).to_be(True)
    expect(run_wait(temple.join_the_guardians(scene.log))).to_be(True)


test('joining the guardians requires every prerequisite and their pendant as confirmation', guardian_workflow)


def far_side_exit():
    scene = world()
    scene.at = None
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(False)
    scene.at = IKOV_TILE.LUCIEN_HUT
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(True)
    scene.at = IKOV_TILE.GUARDIANS
    inside = spy_on(temple, 'in_guardian_temple', returns=True)
    push = spy_on(temple, 'push_secret_wall', impl=answer(False))
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(False)
    push.mock_implementation(answer(True))
    key = spy_on(temple, 'take_shiny_key', impl=answer(False))
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(False)
    key.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-up'], effect=land(scene, IKOV_TILE.LUCIEN_HUT))
    expect(run_wait(temple.leave_the_far_side(scene.log))).to_be(True)


test('the far side leaves through the secret wall and the ladder to the surface', far_side_exit)


def arming_and_sweeping():
    scene = world()
    expect(run_wait(fight.nock_arrows())).to_be(False)
    expect(run_wait(fight.arm_for_the_warrior(scene.log))).to_be(False)
    scene.item(1, IKOV_NAME.YEW_SHORTBOW)
    expect(run_wait(fight.arm_for_the_warrior(scene.log))).to_be(False)
    scene.item(2, IKOV_NAME.ICE_ARROWS, count=5)
    expect(run_wait(fight.arm_for_the_warrior(scene.log))).to_be(True)
    expect(run_wait(fight.nock_arrows())).to_be(True)
    expect(fight.ice_arrows_held()).to_be(5)
    expect(run_wait(fight.stow_spent_bow(scene.log))).to_be_null()
    scene.worn = [i for i in scene.worn if i.name != IKOV_NAME.ICE_ARROWS]
    run_wait(fight.stow_spent_bow(scene.log))
    expect(equipment.contains(IKOV_NAME.YEW_SHORTBOW)).to_be(False)
    scene.on_ground(3, IKOV_NAME.ICE_ARROWS, dist=3)
    run_wait(fight.pick_up_arrows(scene.log))
    expect(fight.ice_arrows_held()).to_be(1)
    scene.on_ground(4, IKOV_NAME.ICE_ARROWS, effect=lambda op: False)
    run_wait(fight.pick_up_arrows(scene.log))
    expect(len(scene.ground)).to_be(1)
    scene.ground = []
    scene.on_ground(4, IKOV_NAME.ICE_ARROWS, effect=lambda op: True)
    run_wait(fight.pick_up_arrows(scene.log))
    expect(scene.logged('recovered arrows')).to_be(True)


test('the warrior kit nocks pack arrows and stows the bow when all ammunition is spent', arming_and_sweeping)


def summoning_and_dialogue():
    scene = world()
    expect(run_wait(fight.summon_warrior(scene.log))).to_be(False)
    scene.loc('Door', id=IKOV_LOC.FIREWARRIOR_DOOR, effect=lambda op: False)
    expect(run_wait(fight.summon_warrior(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Door', id=IKOV_LOC.FIREWARRIOR_DOOR)
    expect(run_wait(fight.summon_warrior(scene.log))).to_be(False)
    expect(scene.logged('scene holds nothing')).to_be(True)
    scene.locs = []

    def summon(op):
        scene.npc('Fire Warrior', ['Attack'], id=IKOV_NPC.FIRE_WARRIOR)

    scene.loc('Door', id=IKOV_LOC.FIREWARRIOR_DOOR, effect=summon)
    expect(run_wait(fight.summon_warrior(scene.log))).to_be(True)
    expect(run_wait(fight.summon_warrior(scene.log))).to_be(True)
    expect(fight.tally_nearby()).to_contain('Fire Warrior#')
    scene.chat.pages = ['continue']
    run_wait(fight.drain_dialogue(scene.log))
    expect(scene.chat.is_open()).to_be(False)
    scene.chat.pages = [['Unmatched option']]
    run_wait(fight.drain_dialogue(scene.log))
    expect(scene.logged('would not drain')).to_be(True)


test('summoning distinguishes missing doors, refused clicks and an absent warrior', summoning_and_dialogue)


def fight_world():
    scene = world()
    for name in ['escape_pocket', 'wear_fear_pendant', 'arm_for_the_warrior', 'walk_to_fire_door', 'summon_warrior']:
        spy_on(fight, name, impl=answer(True))
    scene.wear(IKOV_NAME.ICE_ARROWS)
    return scene


def warrior_prerequisites():
    scene = world()
    for name in ['escape_pocket', 'wear_fear_pendant', 'arm_for_the_warrior']:
        step = spy_on(fight, name, impl=answer(False))
        expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
        step.mock_implementation(answer(True))
    walk = spy_on(fight, 'walk_to_fire_door', impl=answer(False))
    lever = spy_on(fight, 'pull_trap_lever', impl=answer(False))
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    lever.mock_implementation(answer(True))
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    walk.mock_implementation(answer(True))
    summon = spy_on(fight, 'summon_warrior', impl=answer(False))
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    summon.mock_implementation(answer(True))
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    expect(scene.logged('never joined')).to_be(True)


test('the warrior fight recovers the trap lever and rejects a warrior that never appears', warrior_prerequisites)


def warrior_victory():
    scene = fight_world()

    def defeated(op):
        scene.npcs = []

    scene.npc('Fire Warrior', ['Attack'], id=IKOV_NPC.FIRE_WARRIOR, effect=defeated)
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(True)
    expect(scene.logged('down after 1 shots')).to_be(True)
    expect(scene.ticks >= 4).to_be(True)


test('four missing ticks after an engaged warrior confirm victory', warrior_victory)


def warrior_failures():
    scene = fight_world()
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    pending.mock_return_value(False)
    scene.npc('Fire Warrior', ['Attack'], id=IKOV_NPC.FIRE_WARRIOR, effect=lambda op: False)
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    expect(scene.logged('refused an Attack click')).to_be(True)
    expect(scene.logged('outlived')).to_be(True)
    scene.worn = []
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)
    expect(scene.logged('nothing left to shoot')).to_be(True)
    scene.item(5, IKOV_NAME.ICE_ARROWS)
    scene.later(lambda: scene.npcs.clear())
    scene.fighting = True
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(True)
    expect(scene.logged('nocked')).to_be(True)
    scene.fighting = False
    scene.npc('Fire Warrior', ['Attack'], id=IKOV_NPC.FIRE_WARRIOR)
    scene.chat.pages = ['continue']
    expect(run_wait(fight.fight_fire_warrior(scene.log))).to_be(False)


test('warrior fights yield to events, report refusals and exhaustion, and nock swept arrows', warrior_failures)


def lucien():
    scene = world()
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(False)
    scene.item(1, IKOV_NAME.PENDANT_ARMADYL)
    scene.walk_ok = False
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(False)
    scene.walk_ok = True
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(False)
    expect(scene.logged('outlived')).to_be(True)
    scene.npc('Lucien', ['Attack'], id=IKOV_NPC.LUCIEN_HOSTILE, effect=lambda op: False)
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(False)
    scene.npcs = []

    def defeated(op):
        scene.npcs = []

    scene.npc('Lucien', ['Attack'], id=IKOV_NPC.LUCIEN_HOSTILE, effect=defeated)
    scene.chat.pages = ['continue']
    scene.main_modal = 123
    expect(run_wait(fight.kill_lucien(scene.log))).to_be(True)
    expect(scene.logged('banished after 1 attacks')).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('Lucien requires the Armadyl pendant and five missing ticks after engagement', lucien)

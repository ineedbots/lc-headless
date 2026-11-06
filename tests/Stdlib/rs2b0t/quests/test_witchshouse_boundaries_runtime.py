"""Witch's House inventory, mouse, shapeshifter and guarded garden boundaries."""

from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.entities import npcs
from rs2004.quests.defs.witchshouse import garden, house, patrol
from rs2004.quests.defs.witchshouse.areas import EXPERIMENT_IDS, WH_LOC, WH_NPC, WH_OBJ, WH_TILE


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def house_items():
    scene = Scene(WH_TILE.POT)
    prompt = spy_on(house, 'prompt_loc', impl=answer(True))
    expect(run_wait(house.take_door_key(scene.log))).to_be(False)
    scene.item(WH_OBJ.DOOR_KEY, 'Key')
    expect(run_wait(house.take_door_key(scene.log))).to_be(True)
    expect(run_wait(house.drop_stale_magnet(scene.log))).to_be(True)
    scene.item(WH_OBJ.MAGNET, 'Magnet', effect=lambda op: False)
    expect(run_wait(house.drop_stale_magnet(scene.log))).to_be(False)
    scene.take(WH_OBJ.MAGNET)
    scene.item(WH_OBJ.MAGNET, 'Magnet', effect=lambda op: scene.take(WH_OBJ.MAGNET))
    expect(run_wait(house.drop_stale_magnet(scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(house.fetch_magnet(scene.log))).to_be(False)
    scene.walk_ok = True
    open = spy_on(house, 'open_container', impl=answer(False))
    expect(run_wait(house.fetch_magnet(scene.log))).to_be(False)
    open.mock_implementation(answer(True))
    scene.later(lambda: scene.item(WH_OBJ.MAGNET, 'Magnet'))
    expect(run_wait(house.fetch_magnet(scene.log))).to_be(True)
    expect(run_wait(house.fetch_magnet(scene.log))).to_be(True)


test('the door key and magnet require delivered inventory and stale magnets can be dropped', house_items)


def mouse():
    scene = Scene(WH_TILE.PORCH)
    expect(run_wait(house.lure_mouse(scene.log))).to_be(False)
    scene.item(WH_OBJ.CHEESE, 'Cheese', effect=lambda op: False)
    expect(run_wait(house.lure_mouse(scene.log))).to_be(False)
    scene.take(WH_OBJ.CHEESE)
    scene.item(WH_OBJ.CHEESE, 'Cheese', effect=lambda op: scene.npc('Mouse', id=WH_NPC.MOUSE))
    expect(run_wait(house.lure_mouse(scene.log))).to_be(True)
    scene.npcs = []
    scene.loc('Hole', id=WH_LOC.MOUSE_HOLE)
    scene.pack = []
    scene.item(WH_OBJ.CHEESE, 'Cheese', on_use=lambda target: scene.take(WH_OBJ.CHEESE))
    expect(run_wait(house.lure_mouse(scene.log))).to_be(False)
    scene.item(WH_OBJ.CHEESE, 'Cheese', on_use=lambda target: scene.npc('Mouse', id=WH_NPC.MOUSE))
    expect(run_wait(house.lure_mouse(scene.log))).to_be(True)
    scene.item(WH_OBJ.MAGNET, 'Magnet', on_use=lambda target: False)
    expect(run_wait(house.unlock_back_door(scene.log))).to_be(False)
    scene.take(WH_OBJ.MAGNET)
    scene.item(WH_OBJ.MAGNET, 'Magnet')
    expect(run_wait(house.unlock_back_door(scene.log))).to_be(False)
    scene.take(WH_OBJ.MAGNET)
    scene.item(WH_OBJ.MAGNET, 'Magnet', on_use=lambda target: scene.say(house.ALREADY_UNLOCKED))
    expect(run_wait(house.unlock_back_door(scene.log))).to_be(True)


test('cheese can lure the mouse through use or Drop and a fitted magnet unlocks the back door', mouse)


def diary():
    scene = Scene(WH_TILE.PORCH)
    house.reset_diary_state()
    expect(house.diary_wanted()).to_be(True)
    scene.walk_ok = False
    expect(run_wait(house.fetch_diary(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(house.fetch_diary(scene.log))).to_be(False)
    scene.on_ground(WH_OBJ.DIARY, 'Diary', effect=lambda op: False)
    expect(run_wait(house.fetch_diary(scene.log))).to_be(False)
    expect(house.diary_wanted()).to_be(False)
    scene.ground = []
    scene.on_ground(WH_OBJ.DIARY, 'Diary')
    expect(run_wait(house.fetch_diary(scene.log))).to_be(True)
    expect(run_wait(house.fetch_diary(scene.log))).to_be(True)
    scene.take(WH_OBJ.DIARY)
    expect(run_wait(house.read_diary(scene.log))).to_be(False)
    scene.item(WH_OBJ.DIARY, 'Diary', effect=lambda op: False)
    expect(run_wait(house.read_diary(scene.log))).to_be(False)
    scene.take(WH_OBJ.DIARY)
    scene.item(WH_OBJ.DIARY, 'Diary')
    expect(run_wait(house.read_diary(scene.log))).to_be(False)
    scene.main_modal = 123
    expect(run_wait(house.read_diary(scene.log))).to_be(True)
    expect(house.diary_state.read).to_be(True)


test('the diary retry latch records missing spawns and a successful book modal', diary)


def shapeshifter():
    scene = Scene(WH_TILE.BALL)
    spy_on(event_signal, 'pending', returns=False)
    ready = spy_on(garden, 'ready_strikes', impl=answer(False))
    expect(run_wait(garden.kill_experiment(scene.log))).to_be(False)
    ready.mock_implementation(answer(True))
    enter = spy_on(garden, 'enter_shed', impl=answer(False))
    expect(run_wait(garden.kill_experiment(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    expect(run_wait(garden.kill_experiment(scene.log))).to_be(False)
    scene.on_ground(WH_OBJ.BALL, 'Ball', effect=lambda op: False)
    expect(run_wait(garden.summon_experiment(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(WH_OBJ.BALL, 'Ball', effect=lambda op: True)
    expect(run_wait(garden.summon_experiment(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(WH_OBJ.BALL, 'Ball', effect=lambda op: scene.npc('Experiment', ['Attack'], id=EXPERIMENT_IDS[0]))
    expect(run_wait(garden.summon_experiment(scene.log))).to_be(True)
    cover = spy_on(garden, 'at_cover', returns=True)

    def strike(at, target, log):
        scene.say(garden.KILLED)
        return True
        yield

    cast = spy_on(garden, 'cast_strike', impl=strike)
    expect(run_wait(garden.fight_experiment(scene.log))).to_be(True)
    expect(run_wait(garden.kill_experiment(scene.log))).to_be(True)
    scene.npcs = []
    expect(run_wait(garden.fight_experiment(scene.log))).to_be(False)
    scene.npc('Experiment', ['Attack'], id=EXPERIMENT_IDS[-1])
    trap = spy_on(garden, 'trap_experiment', impl=answer(None))
    expect(run_wait(garden.fight_experiment(scene.log))).to_be(False)
    trap.mock_implementation(answer(garden.BEAR_COVER))
    cast.mock_implementation(answer(False))
    expect(run_wait(garden.fight_experiment(scene.log))).to_be(False)


test('touching the ball resumes a shapeshifter fight and only the kill message confirms victory', shapeshifter)


def trap():
    scene = Scene(WH_TILE.BALL)
    spy_on(event_signal, 'pending', returns=False)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    target = scene.npc('Experiment', ['Attack'], id=EXPERIMENT_IDS[-1], targets_me=True)
    stub(target, size=2, network_tile=lambda: garden.EXPERIMENT_TRAP)
    cover = spy_on(garden, 'take_strike_cover', impl=answer(False))
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    cover.mock_implementation(answer(True))
    expect(run_wait(garden.trap_experiment(scene.log))).to_equal(garden.BEAR_COVER)
    target.size = 1
    expect(run_wait(garden.trap_experiment(scene.log))).to_equal(garden.EXPERIMENT_COVER)
    target.network_tile = lambda: garden.CORNER_APPROACH
    spell = spy_on(garden, 'strike_spell', returns=None)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    spell.mock_return_value('Wind strike')
    spy_on(direct_navigator, 'walk', returns=True)
    spy_on(garden, 'at_cover', returns=True)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    expect(scene.logged('did not enter')).to_be(True)


test('large shapeshifter forms use bear cover while small forms are lured to the northeast trap', trap)


def garden_walk():
    scene = Scene(patrol.GARDEN_ENTRY)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(npcs, 'all', impl=lambda: scene.npcs)
    walk = spy_on(direct_navigator, 'walk_to', impl=answer(False))
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    walk.mock_implementation(scene._walk)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    expect(scene.logged('waiting behind the hedge')).to_be(True)
    scene.at = patrol.GARDEN_ENTRY
    spy_on(patrol, 'safe_crossing', returns=True)
    click = spy_on(direct_navigator, 'walk', returns=False)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    scene.at = patrol.GARDEN_ENTRY
    click.mock_return_value(True)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    expect(scene.logged('returning to cover')).to_be(True)
    scene.at = patrol.GARDEN_ENTRY
    click.mock_implementation(lambda at: setattr(scene, 'at', at) or True)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(True)
    scene.at = Tile(2910, 3468, 0)
    expect(run_wait(patrol.walk_garden(patrol.GARDEN_ENTRY, scene.log))).to_be(True)


test('garden travel waits behind hedges, retreats on stalled movement and follows the corridor', garden_walk)


def garden_recovery():
    scene = Scene(WH_TILE.BALL)
    walk = spy_on(garden, 'walk_garden', impl=answer(False))
    door = spy_on(garden, 'cross_teleport_door', impl=answer(False))
    expect(run_wait(garden.enter_shed(scene.log))).to_be(True)
    expect(run_wait(garden.leave_garden(scene.log))).to_be(False)
    door.mock_implementation(answer(True))
    expect(run_wait(garden.leave_garden(scene.log))).to_be(False)
    walk.mock_implementation(answer(True))
    expect(run_wait(garden.leave_garden(scene.log))).to_be(True)
    scene.at = WH_TILE.BALL
    scene.walk_ok = False
    expect(run_wait(garden.take_ball(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(garden.take_ball(scene.log))).to_be(False)
    scene.on_ground(WH_OBJ.BALL, 'Ball', effect=lambda op: False)
    expect(run_wait(garden.take_ball(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(WH_OBJ.BALL, 'Ball')
    expect(run_wait(garden.take_ball(scene.log))).to_be(True)
    expect(run_wait(garden.take_ball(scene.log))).to_be(True)
    scene.item(WH_OBJ.SHED_KEY, 'Shed key')
    expect(run_wait(garden.fountain_key(scene.log))).to_be(True)
    scene.at = WH_TILE.PORCH
    walk.mock_implementation(answer(False))
    expect(run_wait(garden.take_ball(scene.log))).to_be(True)
    scene.take(WH_OBJ.BALL)
    expect(run_wait(garden.take_ball(scene.log))).to_be(False)
    expect(run_wait(garden.enter_shed(scene.log))).to_be(False)
    walk.mock_implementation(answer(True))
    door.mock_implementation(answer(False))
    expect(run_wait(garden.take_ball(scene.log))).to_be(False)


test('garden recovery handles shed exits, absent ball spawns and refused ground takes', garden_recovery)


def trap_cast():
    scene = Scene(WH_TILE.BALL)
    pending = spy_on(event_signal, 'pending', returns=False)
    target = scene.npc('Experiment', ['Attack'], id=EXPERIMENT_IDS[-1], targets_me=False)
    stub(target, size=1, network_tile=lambda: garden.CORNER_APPROACH)
    cover = spy_on(garden, 'take_strike_cover', impl=answer(False))
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    cover.mock_implementation(answer(True))
    spy_on(garden, 'strike_spell', returns='Wind strike')
    cast = spy_on(game, 'cast_on_npc', returns=False)
    spy_on(direct_navigator, 'walk', returns=True)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()
    cast.mock_return_value(True)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()

    def enter_trap():
        target.network_tile = lambda: garden.EXPERIMENT_TRAP

    def spent(*args):
        scene.take(558)
        scene.later(enter_trap)
        return True

    scene.item(558, 'Mind rune')
    cast.mock_implementation(spent)
    spy_on(garden, 'at_cover', returns=False)
    expect(run_wait(garden.trap_experiment(scene.log))).to_equal(garden.EXPERIMENT_COVER)
    target.network_tile = lambda: garden.CORNER_APPROACH

    def broken(*args):
        raise RuntimeError('interrupted cast')

    cast.mock_implementation(broken)
    try:
        run_wait(garden.trap_experiment(scene.log))
        expect(False).to_be(True)
    except RuntimeError:
        expect(True).to_be(True)
    stub(target, targets_me=lambda: True)
    pending.mock_return_value(True)
    expect(run_wait(garden.trap_experiment(scene.log))).to_be_null()


test('shapeshifter lure requires a settled cast and steps back even after a cast exception', trap_cast)


def patrol_boundaries():
    scene = Scene(WH_TILE.PORCH)
    expect(patrol.garden_legs(scene.at, patrol.FOUNTAIN_STAND)).to_be_null()
    scene.walk_ok = False
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    scene.walk_ok = True
    spy_on(event_signal, 'pending', returns=True)
    spy_on(npcs, 'all', returns=[])
    spy_on(direct_navigator, 'walk_to', impl=scene._walk)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)
    scene.at = Tile(2910, 3468, 0)
    spy_on(direct_navigator, 'walk_to', impl=answer(False))
    expect(run_wait(patrol.walk_garden(patrol.GARDEN_ENTRY, scene.log))).to_be(False)
    scene.at = Tile(1, 1, 0)
    expect(run_wait(patrol.walk_garden(patrol.FOUNTAIN_STAND, scene.log))).to_be(False)


test('patrol walking rejects off-corridor positions, unreachable entry and random event interruptions', patrol_boundaries)

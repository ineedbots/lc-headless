"""Digsite excavation, winches, chemical mixing and exams against fake game facades."""

from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.digsite import caves, common, exams, supplies
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_LOC, DIG_NPC, DIG_TILE, DIG_SOIL_IDS
from rs2004.quests.defs.digsite.journal import DIG_STAGE
from rs2004.reach import reach
from rs2004.trade import shop


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def give(scene, id):
    def effect(*args):
        scene.item(id, 'Quest item')
    return effect


def land(scene, at):
    def effect(*args):
        scene.at = at
    return effect


def id_dialogue():
    scene = Scene(DIG_TILE.STUDENTS)
    scene.walk_ok = False
    expect(run_wait(common.talk_to_npc_id(123, DIG_TILE.EXAMINER, [], scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(common.talk_to_npc_id(123, DIG_TILE.EXAMINER, [], scene.log))).to_be(False)
    scene.npc('Student', id=123)
    op = spy_on(reach, 'entity_op', impl=answer('unreachable'))
    expect(run_wait(common.talk_to_npc_id(123, DIG_TILE.EXAMINER, [], scene.log))).to_be(False)
    op.mock_implementation(answer('done'))
    scene.chat.pages = ['continue']
    expect(run_wait(common.talk_to_npc_id(123, DIG_TILE.EXAMINER, [], scene.log))).to_be(True)
    scene.chat.pages = ['continue']
    expect(run_wait(common.talk_to_npc_id(123, DIG_TILE.EXAMINER, [], scene.log, True))).to_be(True)
    expect(op.calls[-1][0]().id).to_be(123)


test('Digsite conversations select NPC id and report an unreachable speaker', id_dialogue)


def prompts():
    scene = Scene()
    expect(run_wait(common.drive_until_held(lambda: False, [], scene.log, 1200))).to_be(False)
    scene.main_modal = 42
    scene.chat.pages = ['continue']
    scene.later(give(scene, 123))
    expect(run_wait(common.drive_until_held(lambda: scene.has(123), [], scene.log))).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('Digsite goals drive chat and dismiss main modals until the item arrives', prompts)


def npc_and_loc_use():
    for is_npc in [False, True]:
        scene = Scene(DIG_TILE.STUDENTS)
        fn = common.use_on_npc_id if is_npc else common.use_on_loc_ids
        target = 123 if is_npc else [123]
        args = [456, target, DIG_TILE.EXAMINER, lambda: scene.has(789), scene.log]
        scene.walk_ok = False
        expect(run_wait(fn(*args))).to_be(False)
        scene.walk_ok = True
        expect(run_wait(fn(*args))).to_be(False)
        if is_npc:
            scene.npc('Student', id=123)
        else:
            scene.loc('Specimen', id=123)
        scene.item(456, 'Tool', on_use=lambda target: False)
        expect(run_wait(fn(*args))).to_be(False)
        scene.pack = []
        scene.item(456, 'Tool', on_use=give(scene, 789))
        expect(run_wait(fn(*args))).to_be(True)
        expect(run_wait(fn(*args))).to_be(True)
        expect(scene.has(789)).to_be(True)
        restore_all()


test('using Digsite tools requires both the id-matched target and the held tool', npc_and_loc_use)


def shaft_exit():
    scene = Scene(DIG_TILE.STUDENTS)
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(True)
    scene.at = DIG_TILE.ARCENIA_WEST
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(False)
    scene.loc('Rope', ['Climb-up'], tile=DIG_TILE.ARCENIA_WEST, dist=2)
    scene.walk_ok = False
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Climb-up'], dist=1, effect=lambda op: False)
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Rope', ['Climb-up'], dist=1, effect=land(scene, DIG_TILE.STUDENTS))
    expect(run_wait(common.climb_out_of_cave(scene.log))).to_be(True)
    expect(scene.at).to_equal(DIG_TILE.STUDENTS)


test('shaft ropes retry failed climbs and confirm arrival above ground', shaft_exit)


def winches():
    scene = Scene(DIG_TILE.STUDENTS)
    arrived = lambda: scene.at == DIG_TILE.ARCENIA_WEST
    args = [DIG_LOC.WINCH_PRIVATE, DIG_TILE.WINCH_PRIVATE_STAND, arrived, scene.log]
    scene.walk_ok = False
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    scene.loc('Winch', ['Operate'], id=DIG_LOC.WINCH_PRIVATE, effect=lambda op: False)
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    scene.locs = []
    scene.loc('Winch', ['Operate'], id=DIG_LOC.WINCH_PRIVATE)
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    expect(scene.logged('pack has none')).to_be(True)
    scene.item(DIG_ID.ROPE, 'Rope', on_use=lambda target: False)
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    scene.pack = []
    scene.item(DIG_ID.ROPE, 'Rope')
    expect(run_wait(caves.descend_winch(*args))).to_be(False)
    expect(scene.logged('would not tie')).to_be(True)
    scene.pack = []

    def tie(target):
        scene.take(DIG_ID.ROPE)
        scene.at = DIG_TILE.ARCENIA_WEST

    scene.item(DIG_ID.ROPE, 'Rope', on_use=tie)
    expect(run_wait(caves.descend_winch(*args))).to_be(True)
    expect(run_wait(caves.descend_winch(*args))).to_be(True)
    scene.at = DIG_TILE.STUDENTS
    scene.locs = []
    scene.loc('Winch', ['Operate'], id=DIG_LOC.WINCH_PRIVATE, effect=land(scene, DIG_TILE.ARCENIA_WEST))
    expect(run_wait(caves.descend_winch(*args))).to_be(True)


test('winches distinguish an unroped bucket from a landed descent', winches)


def roots():
    scene = Scene(DIG_TILE.ARCENIA_WEST)
    scene.walk_ok = False
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(False)
    scene.on_ground(DIG_ID.ARCENIA_ROOT, 'Root', dist=2, effect=lambda op: False)
    scene.walk_ok = False
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(DIG_ID.ARCENIA_ROOT, 'Root')
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(True)
    expect(run_wait(caves.grab_arcenia(scene.log))).to_be(True)


test('arcenia roots are searched at both anchors and taken into the pack', roots)


def western_errands():
    scene = Scene(DIG_TILE.STUDENTS)
    descend = spy_on(caves, 'descend_winch', impl=answer(False))
    expect(run_wait(caves.west_shaft_leg(True, True).run(scene.log))).to_be(False)
    scene.at = DIG_TILE.ARCENIA_WEST
    talk = spy_on(caves, 'talk_to_npc_id', impl=answer(True))
    expect(run_wait(caves.west_shaft_leg(True, True).run(scene.log))).to_be(False)
    expect(scene.logged('kept his key')).to_be(True)

    def key(*args):
        scene.item(DIG_ID.CHEST_KEY, 'Key')
        return True
        yield

    talk.mock_implementation(key)
    scene.on_ground(DIG_ID.ARCENIA_ROOT, 'Root')
    out = spy_on(caves, 'climb_out_of_cave', impl=answer(False))
    expect(run_wait(caves.west_shaft_leg(True, True).run(scene.log))).to_be(True)
    expect(scene.logged('climb out did not land')).to_be(True)
    expect(len(out.calls)).to_be(1)


test('west shaft errands report progress even when the final climb needs a retry', western_errands)


def chest():
    scene = Scene(DIG_TILE.STUDENTS)
    fn = caves.chest_leg().run
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Chest', id=DIG_LOC.CHEST_SHUT)
    scene.item(DIG_ID.CHEST_KEY, 'Key', on_use=lambda target: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.pack = []
    scene.item(DIG_ID.CHEST_KEY, 'Key')
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Chest', ['Search'], id=DIG_LOC.CHEST_OPEN, effect=lambda op: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Chest', ['Search'], id=DIG_LOC.CHEST_OPEN, effect=give(scene, DIG_ID.POWDER))
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(run_wait(fn(scene.log))).to_be(True)


test('the river chest must open before powder can be searched', chest)


def barrel_and_mixing():
    scene = Scene(DIG_TILE.STUDENTS)
    fn = caves.barrel_leg().run
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.item(DIG_ID.VIAL, 'Vial', on_use=give(scene, DIG_ID.LIQUID))
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.loc('Barrel', id=DIG_LOC.BARREL)
    scene.item(DIG_ID.TROWEL, 'Trowel')
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(run_wait(caves.mix_items(1, 2, 3, scene.log))).to_be(False)
    scene.item(1, 'First', on_use=lambda target: False)
    scene.item(2, 'Second')
    expect(run_wait(caves.mix_items(1, 2, 3, scene.log))).to_be(False)
    scene.take(2)
    scene.item(2, 'Second', on_use=give(scene, 3))
    expect(run_wait(caves.mix_step('Mix', 1, 2, 3).run(scene.log))).to_be(True)
    expect(run_wait(caves.mix_items(1, 2, 3, scene.log))).to_be(True)
    expect(scene.has(3)).to_be(True)


test('the barrel needs a vial and trowel and mixing tries both item directions', barrel_and_mixing)


def blasting():
    scene = Scene(DIG_TILE.STUDENTS)
    descend = spy_on(caves, 'descend_winch', impl=answer(False))
    for pour in [True, False]:
        expect(run_wait(caves.blast_leg(pour).run(scene.log))).to_be(False)
    scene.at = DIG_TILE.TABLET
    expect(run_wait(caves.blast_leg(False).run(scene.log))).to_be(True)
    scene.at = DIG_TILE.BRICK_STAND
    scene.walk_ok = False
    scene.at = Tile(scene.at.x + 1, scene.at.z, scene.at.level)
    expect(run_wait(caves.blast_leg(True).run(scene.log))).to_be(False)
    scene.at = DIG_TILE.BRICK_STAND
    scene.walk_ok = True
    expect(run_wait(caves.blast_leg(True).run(scene.log))).to_be(False)
    scene.loc('Brick', id=DIG_LOC.BRICK)
    expect(run_wait(caves.blast_leg(True).run(scene.log))).to_be(False)
    expect(run_wait(caves.blast_leg(False).run(scene.log))).to_be(False)
    scene.item(DIG_ID.COMPOUND, 'Compound', on_use=lambda target: False)
    scene.item(DIG_ID.TINDERBOX, 'Tinderbox', on_use=lambda target: False)
    expect(run_wait(caves.blast_leg(True).run(scene.log))).to_be(False)
    expect(run_wait(caves.blast_leg(False).run(scene.log))).to_be(False)
    scene.pack = []
    scene.item(DIG_ID.COMPOUND, 'Compound', on_use=lambda target: scene.take(DIG_ID.COMPOUND))
    expect(run_wait(caves.blast_leg(True).run(scene.log))).to_be(True)
    scene.item(DIG_ID.TINDERBOX, 'Tinderbox')
    expect(run_wait(caves.blast_leg(False).run(scene.log))).to_be(False)
    scene.take(DIG_ID.TINDERBOX)
    scene.item(DIG_ID.TINDERBOX, 'Tinderbox', on_use=land(scene, DIG_TILE.TABLET))
    expect(run_wait(caves.blast_leg(False).run(scene.log))).to_be(True)
    expect(scene.at).to_equal(DIG_TILE.TABLET)


test('blasting requires the exact brick stand and confirms compound use and the explosion', blasting)


def tablet_and_exam_errands():
    scene = Scene(DIG_TILE.STUDENTS)
    descend = spy_on(caves, 'descend_winch', impl=answer(False))
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(False)
    scene.at = DIG_TILE.TABLET
    scene.walk_ok = False
    # Standing on the destination is already a successful walk; fail from another cave tile.
    scene.at = Tile(DIG_TILE.TABLET.x + 3, DIG_TILE.TABLET.z, 0)
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(False)
    scene.on_ground(DIG_ID.STONE_TABLET, 'Tablet', effect=lambda op: False)
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(False)
    scene.ground = []
    scene.on_ground(DIG_ID.STONE_TABLET, 'Tablet')
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(True)
    expect(run_wait(caves.tablet_leg().run(scene.log))).to_be(True)
    expect(caves.leave_cave_step().run).to_be(common.climb_out_of_cave)
    talk = spy_on(exams, 'talk_to_npc_id', impl=answer(False))
    expect(run_wait(exams.stamp_letter().run(scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    scene.item(DIG_ID.STAMPED_LETTER, 'Letter')
    expect(run_wait(exams.stamp_letter().run(scene.log))).to_be(True)
    expect(run_wait(exams.replace_trowel().run(scene.log))).to_be(True)
    for stage in [DIG_STAGE.SECOND_EXAM, DIG_STAGE.THIRD_EXAM]:
        talk.mock_implementation(answer(False))
        expect(run_wait(exams.study_with_students(stage).run(scene.log))).to_be(False)
        scene.item(DIG_ID.OPAL, 'Opal')
        talk.mock_implementation(answer(True))
        expect(run_wait(exams.study_with_students(stage).run(scene.log))).to_be(True)


test('the tablet is taken after blasting and exam conversations track actual progress', tablet_and_exam_errands)


GATHERING = [
    [supplies, supplies.take_panning_tray, DIG_ID.TRAY_EMPTY, 0, True],
    [supplies, supplies.take_specimen_jar, DIG_ID.SPECIMEN_JAR, DIG_LOC.SAMPLE_SACKS, False],
    [exams, exams.search_bush().run, DIG_ID.ROCK_SAMPLE_PURPLE, DIG_LOC.BUSH_SAMPLE, False],
]


def gathering(module, fn, product, loc_id, ground):
    scene = Scene(DIG_TILE.EXAMINER)
    scene.walk_ok = False
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(fn(scene.log))).to_be(False)
    if ground:
        scene.on_ground(product, 'Quest item', effect=lambda op: False)
    else:
        scene.loc('Container', ['Search'], id=loc_id, effect=lambda op: False)
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.ground = []
    scene.locs = []
    if ground:
        scene.on_ground(product, 'Quest item')
    else:
        scene.loc('Container', ['Search'], id=loc_id, effect=give(scene, product))
    expect(run_wait(fn(scene.log))).to_be(True)
    expect(run_wait(fn(scene.log))).to_be(True)


test_each(GATHERING)('Digsite gathering confirms its item and handles missing spawns: %s %s', gathering)


def herblore_shop():
    scene = Scene(DIG_TILE.EXAMINER)
    scene.walk_ok = False
    fn = supplies.herblore_kit(True, True).run
    expect(run_wait(fn(scene.log))).to_be(False)
    scene.walk_ok = True
    opened = spy_on(shop, 'open', impl=answer(False))
    expect(run_wait(fn(scene.log))).to_be(False)
    opened.mock_implementation(answer(True))
    bought = spy_on(shop, 'buy', impl=answer(False))
    spy_on(shop, 'close', impl=answer(True))
    expect(run_wait(fn(scene.log))).to_be(False)
    expect(len(bought.calls)).to_be(2)
    scene.item(DIG_ID.VIAL, 'Vial')
    scene.item(DIG_ID.PESTLE, 'Pestle')
    expect(run_wait(fn(scene.log))).to_be(True)


test('the herblore shop buys both requested tools and checks the pack afterwards', herblore_shop)


def pickpocket():
    scene = Scene(DIG_TILE.WORKMEN)
    scene.goal = False
    pending = spy_on(event_signal, 'pending', returns=True)
    scene.walk_ok = False
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(False)
    scene.npc('Workman', ['Steal-from'], id=DIG_NPC.WORKMAN)

    def refused(*args, **kwargs):
        scene.say('You are stunned')
        return 'unreachable'
        yield

    op = spy_on(reach, 'entity_op', impl=refused)
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(False)

    def stolen(*args, **kwargs):
        scene.goal = True
        return 'done'
        yield

    op.mock_implementation(stolen)
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(True)
    expect(run_wait(supplies.pickpocket_workman(lambda: scene.goal, scene.log))).to_be(True)
    expect(supplies.STEAL_SETTLED('You find a specimen brush')).to_be(True)
    expect(supplies.STEAL_SETTLED('Nothing happened')).to_be(False)


test('workman pockets yield to events, recover from stuns and stop once the wanted item lands', pickpocket)


def panning():
    scene = Scene(DIG_TILE.EXAMINER)
    scene.goal = False
    tray = spy_on(supplies, 'take_panning_tray', impl=answer(False))
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    tray.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    scene.walk_ok = True
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    pending.mock_return_value(False)
    scene.item(DIG_ID.TRAY_EMPTY, 'Tray')
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    scene.loc('Panning point', ['Look'], id=DIG_LOC.PANNING_POINT, effect=lambda op: False)
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Panning point', ['Look'], id=DIG_LOC.PANNING_POINT,
              effect=lambda op: scene.chat.pages.append('continue'))
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(False)
    expect(supplies.digsite_state.tea_wanted).to_be(True)
    scene.locs = []

    def searched(op):
        scene.take(DIG_ID.TRAY_MUD)
        scene.goal = True

    def filled(op):
        scene.item(DIG_ID.TRAY_MUD, 'Muddy tray', effect=searched)

    scene.loc('Panning point', ['Look'], id=DIG_LOC.PANNING_POINT, effect=filled)
    scene.chat.pages = ['continue']
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(True)
    expect(run_wait(supplies.pan_until(lambda: scene.goal, scene.log))).to_be(True)


test('panning recognizes the tea refusal and searches the filled tray before another pan', panning)


def digging():
    scene = Scene(DIG_TILE.STUDENTS)
    zone = Fake(stand=scene.at, min_x=scene.at.x - 1, max_x=scene.at.x + 1,
                min_z=scene.at.z - 1, max_z=scene.at.z + 1)
    scene.goal = False
    scene.walk_ok = False
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    scene.walk_ok = True
    pending = spy_on(event_signal, 'pending', returns=True)
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    pending.mock_return_value(False)
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    scene.item(DIG_ID.TROWEL, 'Trowel')
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    scene.loc('Soil', id=DIG_SOIL_IDS[0], tile=zone.stand)
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    expect(scene.logged('three digs')).to_be(True)
    scene.take(DIG_ID.TROWEL)
    scene.item(DIG_ID.TROWEL, 'Trowel', on_use=lambda target: False)
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(False)
    scene.take(DIG_ID.TROWEL)
    scene.item(DIG_ID.TROWEL, 'Trowel', on_use=lambda target: setattr(scene, 'goal', True))
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(True)
    expect(run_wait(supplies.dig_until(zone, lambda: scene.goal, scene.log))).to_be(True)


test('excavation rejects missing tools, wrong soil and three refusals then confirms the find', digging)


def dropping_spoil():
    scene = Scene(DIG_TILE.STUDENTS)
    for i in range(28):
        scene.item(999, 'Spoil')
    run_wait(common.drop_spoil(scene.log))
    expect(scene.logged('spoil')).to_be(True)
    scene.pack = []
    for i in range(28):
        scene.item(DIG_ID.SPECIMEN_BRUSH, 'Brush', effect=drop_one(scene, DIG_ID.SPECIMEN_BRUSH))
    run_wait(common.drop_spoil(scene.log))
    expect(scene.logged('surplus')).to_be(True)
    expect(len(scene.pack)).to_be(24)
    run_wait(common.drop_spoil(scene.log))
    expect(len(scene.pack)).to_be(24)


def drop_one(scene, id):
    def dropped(op):
        scene.pack.pop()
    return dropped


test('spoil dropping preserves one brush and stops as soon as the requested slots are free', dropping_spoil)

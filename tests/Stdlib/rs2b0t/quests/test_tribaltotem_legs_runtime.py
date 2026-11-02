"""Tribal Totem's parcel, security lock, trapped stairs and chest against Scene facades."""

import _core
import rs2004.quests.defs.tribaltotem as totem
from rs2004.dialogue import chat_dialog, modals
from rs2004.game import reader
from rs2004.reach import reach
from rs2004.tabs import quests


def answer(value):
    return value
    yield


def world(at=None):
    scene = Scene(at if at is not None else totem.COMBO_STAND)
    scene.prompt_ids = []

    def operate(name, op, near, expect, within=10, id=None, expect_ms=12000, refused=None, log=None):
        scene.prompt_ids.append(id)
        result = yield from scene._loc_op(name, op, near, expect, within, id, expect_ms, refused, log)
        return result

    spy_on(reach, 'loc_op', impl=operate)
    return scene


def read_progress():
    scene = world()
    scene.status = 'complete'
    progress = run_wait(totem.read_tribal_totem_progress())
    expect(progress.stage).to_be(totem.TOTEM_STAGE.COMPLETE)
    expect('combo' in progress.flags).to_be(True)
    scene.status = 'not_started'
    expect(run_wait(totem.read_tribal_totem_progress()).stage).to_be(totem.TOTEM_STAGE.NOT_STARTED)
    scene.status = 'unknown'
    expect(run_wait(totem.read_tribal_totem_progress())).to_be_null()
    scene.status = 'in_progress'
    spy_on(quests, 'journal', impl=lambda name: answer(['I teleported myself inside']))
    scene.main_modal = 123
    expect(run_wait(totem.read_tribal_totem_progress()).stage).to_be(totem.TOTEM_STAGE.TELEPORTED)
    expect(scene.main_modal).to_be(-1)
    expect(scene.ticks).to_be(1)
    expect(run_wait(totem.read_tribal_totem_progress()).stage).to_be(totem.TOTEM_STAGE.TELEPORTED)
    expect(scene.ticks).to_be(1)
    spy_on(quests, 'journal', impl=lambda name: answer(['unrecognized journal']))
    expect(run_wait(totem.read_tribal_totem_progress())).to_be_null()


test('Tribal Totem reads journal status and closes the journal after parsing', read_progress)


def label_pickup():
    scene = world(totem.DEPOT_STAND)
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.take_label(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    before = scene.clock
    expect(run_wait(totem.take_label(scene.log))).to_be(False)
    expect(scene.clock - before >= 20000).to_be(True)

    def investigate(name, op):
        expect((name, op)).to_equal(('Crate', 'Investigate'))
        scene.item(totem.LABEL_OBJ, 'Address label')

    scene.loc_op_effect = investigate
    expect(run_wait(totem.take_label(scene.log))).to_be(True)
    expect(scene.prompt_ids).to_equal([totem.HORN_CRATE, totem.HORN_CRATE, totem.HORN_CRATE])
    expect(scene.has(totem.LABEL_OBJ)).to_be(True)
    count = len(scene.loc_ops)
    expect(run_wait(totem.take_label(scene.log))).to_be(True)
    expect(len(scene.loc_ops)).to_be(count)


test('Tribal Totem investigates the mansion crate and confirms the label in the pack', label_pickup)


def relabel():
    scene = world(totem.DEPOT_STAND)
    label = scene.item(totem.LABEL_OBJ, 'Address label', on_use=lambda target: False)
    scene.walk_ok = False
    expect(run_wait(totem.mark_crate(scene.log))).to_be(False)
    scene.walk_ok = True
    scene.loc('Crate', id=totem.HORN_CRATE, dist=0)
    expect(run_wait(totem.mark_crate(scene.log))).to_be(False)
    crate = scene.loc('Crate', id=totem.TELEPORT_CRATE)
    expect(run_wait(totem.mark_crate(scene.log))).to_be(False)
    label._fields['use_on'] = lambda target: True
    before = scene.clock
    expect(run_wait(totem.mark_crate(scene.log))).to_be(False)
    expect(scene.clock - before >= 30000).to_be(True)
    expect(scene.has(totem.LABEL_OBJ)).to_be(True)

    def paste(target):
        expect(target).to_be(crate)
        scene.take(totem.LABEL_OBJ)
        return True

    label._fields['use_on'] = paste
    expect(run_wait(totem.mark_crate(scene.log))).to_be(True)
    expect(scene.has(totem.LABEL_OBJ)).to_be(False)


test('Tribal Totem relabels the teleport crate by id and waits for label consumption', relabel)


def click_lock(scene, button):
    scene.buttons.append(button)
    if not scene.click_ok:
        return False
    if button == totem.CONFIRM:
        scene.main_modal = -1
        if scene.accept:
            scene.say('The combination seems correct.')
        return True
    for index in range(4):
        if button in [totem.DIAL_UP[index], totem.DIAL_DOWN[index]]:
            if scene.echo:
                delta = 1 if button == totem.DIAL_UP[index] else -1
                scene.dials[index] = chr((ord(scene.dials[index]) - ord('A') + delta) % 26 + ord('A'))
            return True
    return False


def lock_world():
    scene = world()
    scene.dials = ['A', 'A', 'A', 'A']
    scene.buttons = []
    scene.click_ok = True
    scene.echo = True
    scene.accept = True
    spy_on(modals, 'main', impl=lambda: scene.main_modal)
    spy_on(reader, 'component_text', impl=lambda component: scene.dials[totem.DIAL_TEXT.index(component)])
    spy_on(_core, 'click_component', impl=lambda button: click_lock(scene, button))

    def open_lock(name, op):
        expect((name, op)).to_equal(('Door', 'Open'))
        scene.main_modal = totem.DOOR_UI

    scene.loc_op_effect = open_lock
    return scene


def dial_text():
    scene = lock_world()
    for text, expected in [(None, None), ('', None), ('   ', None), ('7', None), ('@red@A', None), (' z ', 'Z')]:
        scene.dials[0] = text
        expect(totem.dial_letter(0)).to_be(expected)


test('Tribal Totem accepts only readable alphabetic dial text', dial_text)


def dial_routes():
    scene = lock_world()
    expect(run_wait(totem.set_dial(0, 'A', scene.log))).to_be(True)
    expect(scene.buttons).to_equal([])
    expect(run_wait(totem.set_dial(0, 'Z', scene.log))).to_be(True)
    expect(scene.buttons).to_equal([totem.DIAL_DOWN[0]])
    scene.buttons = []
    expect(run_wait(totem.set_dial(0, 'B', scene.log))).to_be(True)
    expect(scene.buttons).to_equal([totem.DIAL_UP[0], totem.DIAL_UP[0]])
    scene.dials[1] = 'A'
    scene.buttons = []
    expect(run_wait(totem.set_dial(1, 'N', scene.log))).to_be(True)
    expect(scene.buttons).to_equal([totem.DIAL_UP[1]] * 13)
    expect(scene.dials).to_equal(['B', 'N', 'A', 'A'])


test('Tribal Totem turns dials by the shortest route, including wraparound and ties', dial_routes)


def dial_failures():
    scene = lock_world()
    scene.dials[0] = None
    expect(run_wait(totem.set_dial(0, 'K', scene.log))).to_be(False)
    expect(scene.logged('not readable')).to_be(True)
    expect(scene.buttons).to_equal([])
    scene.dials[0] = 'A'
    scene.click_ok = False
    expect(run_wait(totem.set_dial(0, 'K', scene.log))).to_be(False)
    expect(scene.dials[0]).to_be('A')
    scene.click_ok = True
    scene.echo = False
    before = scene.clock
    expect(run_wait(totem.set_dial(0, 'K', scene.log))).to_be(False)
    expect(scene.clock - before).to_be(3000)
    expect(scene.logged('did not move off A')).to_be(True)

    def bounce(button):
        scene.buttons.append(button)
        scene.dials[0] = 'B' if scene.dials[0] == 'A' else 'A'
        return True

    scene.buttons = []
    spy_on(_core, 'click_component', impl=bounce)
    expect(run_wait(totem.set_dial(0, 'C', scene.log))).to_be(False)
    expect(len(scene.buttons)).to_be(totem.LETTERS + 1)


test('Tribal Totem bounds dial retries when clicks fail, stall or echo the wrong values', dial_failures)


def solve_lock():
    scene = lock_world()
    expect(run_wait(totem.solve_combination(scene.log))).to_be(True)
    expect(''.join(scene.dials)).to_be(totem.COMBINATION)
    expect(scene.buttons[-1]).to_be(totem.CONFIRM)
    expect(scene.prompt_ids).to_equal([totem.COMBO_DOOR])
    expect(scene.main_modal).to_be(-1)


test('Tribal Totem enters KURT and confirms acceptance from the server message', solve_lock)


def lock_failures():
    scene = lock_world()
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.solve_combination(scene.log))).to_be(False)
    expect(scene.logged('never raised its lock')).to_be(True)
    expect(scene.buttons).to_equal([])
    scene = lock_world()
    scene.dials[2] = None
    expect(run_wait(totem.solve_combination(scene.log))).to_be(False)
    expect(scene.main_modal).to_be(-1)
    expect(totem.CONFIRM in scene.buttons).to_be(False)
    scene = lock_world()
    scene.dials = ['K', 'U', 'R', 'T']
    scene.click_ok = False
    expect(run_wait(totem.solve_combination(scene.log))).to_be(False)
    expect(scene.buttons).to_equal([totem.CONFIRM])
    expect(scene.main_modal).to_be(-1)
    scene = lock_world()
    scene.accept = False
    scene.say('The combination seems correct.')
    before = scene.clock
    expect(run_wait(totem.solve_combination(scene.log))).to_be(False)
    expect(scene.clock - before >= 8000).to_be(True)
    expect(scene.logged('refused the combination')).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('Tribal Totem closes a failed lock and rejects modal closure or stale success messages as proof', lock_failures)


def stairs():
    scene = world(totem.STAIRS_STAND)
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.disarm_trap(scene.log))).to_be(False)
    expect(run_wait(totem.climb_stairs(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    before = scene.clock
    expect(run_wait(totem.disarm_trap(scene.log))).to_be(False)
    expect(scene.clock - before >= 15000).to_be(True)
    expect(run_wait(totem.climb_stairs(scene.log))).to_be(False)
    expect(scene.at.level).to_be(0)
    scene.main_texts = ['You find a TRAP IN THESE STAIRS.']
    expect(run_wait(totem.disarm_trap(scene.log))).to_be(True)
    scene.main_texts = []
    spy_on(chat_dialog, 'texts', impl=lambda: ['You find a trap in these stairs.'])
    expect(run_wait(totem.disarm_trap(scene.log))).to_be(True)

    def climb(name, op):
        expect((name, op)).to_equal(('Stairs', 'Climb-up'))
        scene.at = totem.CHEST_STAND

    scene.loc_op_effect = climb
    ticks = scene.ticks
    expect(run_wait(totem.climb_stairs(scene.log))).to_be(True)
    expect(scene.ticks - ticks).to_be(2)
    expect(scene.prompt_ids[-1]).to_be(totem.TRAP_STAIRS)


test('Tribal Totem detects the trap in either modal and verifies the stairs reach level one', stairs)


def chest():
    scene = world(totem.CHEST_STAND)
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.empty_chest(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(totem.empty_chest(scene.log))).to_be(False)
    expect(scene.loc_ops[-1]).to_equal(('Chest', 'Open'))

    def loot(name, op):
        if op == 'Open':
            scene.loc('Chest', id=totem.CHEST_OPEN)
        if op == 'Search':
            scene.item(totem.TOTEM_OBJ, 'Tribal totem')

    scene.loc('Chest', id=totem.CHEST_SHUT)
    scene.loc_op_effect = loot
    expect(run_wait(totem.empty_chest(scene.log))).to_be(True)
    expect(scene.prompt_ids[-2:]).to_equal([totem.CHEST_SHUT, totem.CHEST_OPEN])
    expect(scene.has(totem.TOTEM_OBJ)).to_be(True)
    scene.take(totem.TOTEM_OBJ)
    scene.loc_ops = []
    scene.loc_op_effect = None
    before = scene.clock
    expect(run_wait(totem.empty_chest(scene.log))).to_be(False)
    expect(scene.loc_ops).to_equal([('Chest', 'Search')])
    expect(scene.clock - before >= 12000).to_be(True)


test('Tribal Totem opens the chest then searches its new id, confirming the totem pickup', chest)


def take_totem():
    scene = world()
    scene.at = None
    expect(run_wait(totem.take_totem(scene.log))).to_be(False)
    scene.item(totem.TOTEM_OBJ, 'Tribal totem')
    expect(run_wait(totem.take_totem(scene.log))).to_be(True)
    expect(scene.loc_ops).to_equal([])
    scene = world(totem.STAIRS_STAND)
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.take_totem(scene.log))).to_be(False)
    expect(scene.loc_ops).to_equal([('Stairs', 'Investigate')])
    scene.loc_op_status = 'done'
    scene.main_texts = ['You find a trap in these stairs.']
    expect(run_wait(totem.take_totem(scene.log))).to_be(False)
    expect(scene.loc_ops[-1]).to_equal(('Stairs', 'Climb-up'))

    scene = world(totem.STAIRS_STAND)

    def retrieve(name, op):
        if op == 'Investigate':
            scene.main_texts = ['You find a trap in these stairs.']
        elif op == 'Climb-up':
            scene.at = totem.CHEST_STAND
        elif op == 'Open':
            scene.loc('Chest', id=totem.CHEST_OPEN)
        elif op == 'Search':
            scene.item(totem.TOTEM_OBJ, 'Tribal totem')

    scene.loc_op_effect = retrieve
    expect(run_wait(totem.take_totem(scene.log))).to_be(True)
    expect(scene.loc_ops).to_equal([('Stairs', 'Investigate'), ('Stairs', 'Climb-up'), ('Chest', 'Open'), ('Chest', 'Search')])
    expect(scene.has(totem.TOTEM_OBJ)).to_be(True)
    scene = world(totem.CHEST_STAND)
    scene.loc_op_status = 'missing'
    expect(run_wait(totem.take_totem(scene.log))).to_be(False)
    expect(scene.loc_ops).to_equal([('Chest', 'Open')])


test('Tribal Totem retrieves the totem in trap, climb, open, search order and resumes upstairs', take_totem)

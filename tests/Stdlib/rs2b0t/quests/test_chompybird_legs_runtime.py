"""Big Chompy Bird Hunting's legs against spied facades: the box-driving dialogue, the fletching chain, the chest and
bellows, the bait, the hunt, the roast and the talks with Rantz, each through its success and its failures."""

import _core
import rs2004.quests.defs.chompybird as cb
import rs2004.quests.defs.chompybird.arrows as arrows
import rs2004.quests.defs.chompybird.cook as cook
import rs2004.quests.defs.chompybird.dialogue as dialogue
import rs2004.quests.defs.chompybird.hunt as hunt
import rs2004.quests.defs.chompybird.journal as journal
import rs2004.quests.defs.chompybird.supplies as supplies
from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import reader
from rs2004.geometry import Tile
from rs2004.quests.defs.chompybird.areas import CB_ID, CB_LOC, CB_LOC_ID, CB_NAME, CB_NPC, CB_STAGE, CB_TILE, in_cave
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.exec.primitives import LineRule
from rs2004.quests.food import quest_food
from rs2004.tabs import quests
from rs2004.traversal import traversal

FAR_OFF = Tile(2700, 3050, 0)
MODAL = 100
SEASONED = {CB_ID.POTATO: 1, CB_ID.CABBAGE: 1, CB_ID.EQUA: 1, CB_ID.ONION: 1, CB_ID.TOMATO: 1, CB_ID.DOOGLE: 1}


def _reset():
    cook.cook_state.kids_asked = False
    hunt.chest_state.refused = False
    journal.last_good = None
    event_signal.set_interrupt(None)


def _no_food_chosen():
    stub(quest_food, name=None)


before_each(_reset)
before_each(_no_food_chosen)
after_each(_reset)


def run(gen):
    return run_wait(gen)


def refuse(*args):
    return False


def gives(scene, id, name):
    def effect(*args):
        scene.item(id, name)
    return effect


def chats(scene, pages):
    def effect(*args):
        scene.chat.pages = list(pages)
    return effect


def counted(clicks, result):
    def effect(*args):
        clicks.append(args)
        return result
    return effect


def discard_one(scene, id):
    rows = [i for i in scene.pack if i.id == id]
    scene.pack.remove(rows[0])


def walk_without_moving(dest, radius=0, attempts=0, timeout_ms=0, log=None):
    return True
    yield


def merged(first, second):
    out = {}
    for key, value in first.items():
        out[key] = value
    for key, value in second.items():
        out[key] = value
    return out


def snap(stage, inv_ids=None, inv=None, bank=None, bank_ids=None, worn=None, worn_ids=None, bank_known=True, free_slots=20):
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': inv if inv is not None else {'coins': 2000, 'bronze axe': 1},
        'inv_ids': inv_ids if inv_ids is not None else {},
        'worn': worn if worn is not None else set(),
        'worn_ids': worn_ids if worn_ids is not None else set(),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': bank if bank is not None else {},
        'bank_ids': bank_ids if bank_ids is not None else {},
        'bank_known': bank_known,
        'tile': CB_TILE.RANTZ,
        'free_slots': free_slots,
    })


# The box-driving dialogue.

def clear_box_with_nothing_up():
    scene = Scene(CB_TILE.RANTZ)
    clicks = spy_on(_core, 'click_component')
    expect(run(dialogue.clear_box())).to_be(False)
    expect(clicks.called()).to_be(False)
    expect(scene.ticks).to_be(0)


test('clearing a box with nothing up does nothing', clear_box_with_nothing_up)


def clear_box_clicks_continue():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_modal = MODAL
    spy_on(reader, 'main_modal_button_near_text', returns=77)
    clicks = spy_on(_core, 'click_component')
    expect(run(dialogue.clear_box())).to_be(True)
    expect(clicks.calls).to_equal([(77,)])
    expect(scene.main_modal).to_be(MODAL)


test('a box with a continue button has it clicked', clear_box_clicks_continue)


def clear_box_closes_without_a_button():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_modal = MODAL
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    clicks = spy_on(_core, 'click_component')
    expect(run(dialogue.clear_box())).to_be(True)
    expect(clicks.called()).to_be(False)
    expect(scene.main_modal).to_be(-1)


test('a box with no continue button is closed instead', clear_box_closes_without_a_button)


def box_text_flattens():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_texts = ['  What   BUGS', 'wants ']
    expect(dialogue.box_text()).to_be('what bugs wants')


test('box text is flattened and lower-cased', box_text_flattens)


def talk_skips_a_met_goal():
    scene = Scene(CB_TILE.RANTZ)
    expect(run(dialogue.talk_boxes('Rantz', Record({'expect': lambda: True}), scene.log))).to_be(True)
    expect(scene.lines).to_have_length(0)


test('a goal already met needs no talk', talk_skips_a_met_goal)


def talk_clears_a_stale_box_first():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_modal = MODAL
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    expect(run(dialogue.talk_boxes('Rantz', Record({}), scene.log))).to_be(False)
    expect(scene.main_modal).to_be(-1)
    expect(scene.logged("no 'Rantz' nearby")).to_be(True)


test('a box left up is cleared before a talk, and nobody to talk to fails it', talk_clears_a_stale_box_first)


def drives_through_a_real_talk_click():
    scene = Scene(CB_TILE.RANTZ)
    scene.npc('Rantz', ['Talk-to'], effect=chats(scene, ['continue', ['No', 'Yes'], 'continue']))
    expect(run(dialogue.talk_boxes('Rantz', Record({'prefer': ['Yes']}), scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Yes'])
    expect(scene.chat.pages).to_have_length(0)


test('a talk opens the chat, continues, picks and ends after the quiet', drives_through_a_real_talk_click)


def talk_never_opened():
    scene = Scene(CB_TILE.RANTZ)
    scene.npc('Rantz', ['Talk-to'], effect=refuse)
    expect(run(dialogue.talk_boxes('Rantz', Record({}), scene.log))).to_be(False)
    expect(scene.logged("'Rantz' never opened a dialogue")).to_be(True)


test('a talk click that never opens a chat fails it', talk_never_opened)


def once_options_are_spent():
    scene = Scene(CB_TILE.RANTZ)
    question = 'How do we make the chompys come?'
    scene.chat.pages = [[question, 'Ok, thanks.'], [question, 'Ok, thanks.']]
    drive = Record({'prefer': [question, 'Ok, thanks.'], 'once': [question]})
    expect(run(dialogue.drive_boxes(drive, scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal([question, 'Ok, thanks.'])


test('a one-shot option is only picked the once', once_options_are_spent)


def rules_read_the_spoken_line():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.shown = ['Who be there?']
    scene.chat.pages = ['continue', ['Bugs', 'Fycie']]
    drive = Record({'rules': [LineRule('who be there', 'Fycie')], 'prefer': ['Bugs']})
    expect(run(dialogue.drive_boxes(drive, scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Fycie'])


test('a line rule beats the preference list', rules_read_the_spoken_line)


def strict_stops_on_an_unknown_menu():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.shown = ['Make stabbers?']
    scene.chat.pages = ['continue', ["Er, make you're own 'stabbers'!", 'Later']]
    expect(run(dialogue.drive_boxes(Record({'prefer': ['Yes']}), scene.log))).to_be(False)
    expect(scene.chat.chosen).to_have_length(0)
    expect(scene.logged("no rule or preference matched [Er, make you're own 'stabbers'! | Later] after \"Make stabbers?\"")).to_be(True)


test('a menu nothing matches stops rather than taking a refusal', strict_stops_on_an_unknown_menu)


def not_strict_takes_the_last():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.pages = [['First', 'Last']]
    expect(run(dialogue.drive_boxes(Record({'strict': False}), scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Last'])


test('a driver that is not strict falls through to the last option', not_strict_takes_the_last)


def objbox_counts_as_acting():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_modal = MODAL
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    expect(run(dialogue.drive_boxes(Record({}), scene.log))).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('an objbox on main is clicked through and ends the chain after the quiet', objbox_counts_as_acting)


def event_ends_the_chat():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.pages = ['continue']
    event_signal.set_interrupt(lambda: True)
    expect(run(dialogue.drive_boxes(Record({}), scene.log))).to_be(False)
    expect(scene.chat.pages).to_have_length(1)


test('a runtime event ends the conversation at once', event_ends_the_chat)


def goal_landing_ends_the_chat():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.pages = [['Take it'], 'continue']
    scene.chat.on_choose = gives(scene, CB_ID.BOW, CB_NAME.BOW)
    drive = Record({'prefer': ['Take it'], 'expect': lambda: scene.has(CB_ID.BOW)})
    expect(run(dialogue.drive_boxes(drive, scene.log))).to_be(True)
    expect(scene.chat.pages).to_have_length(1)


test('the goal landing ends the chain with pages still to go', goal_landing_ends_the_chat)


def quiet_without_the_goal():
    scene = Scene(CB_TILE.RANTZ)
    scene.chat.pages = ['continue']
    drive = Record({'expect': lambda: False})
    expect(run(dialogue.drive_boxes(drive, scene.log))).to_be(False)
    expect(scene.clock).to_be_less_than(30000)


test('a chain gone quiet without its goal fails before the deadline', quiet_without_the_goal)


def deadline_with_nothing_said():
    scene = Scene(CB_TILE.RANTZ)
    expect(run(dialogue.drive_boxes(Record({'ms': 3000}), scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(3000)

    scene = Scene(CB_TILE.RANTZ)
    expect(run(dialogue.drive_boxes(Record({'ms': 3000, 'expect': lambda: False}), scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(3000)


test('a chat that never opens runs out its window', deadline_with_nothing_said)


# Fletching.

def walk_to_skips_a_short_trip():
    scene = Scene(CB_TILE.ACHEY)
    expect(run(arrows.walk_to(Tile(2628, 2974, 0), 2, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)
    expect(run(arrows.walk_to(Tile(2628, 2974, 1), 2, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(1)


test('a walk within the radius stays put, and another level always walks', walk_to_skips_a_short_trip)


def chops_a_log():
    scene = Scene(FAR_OFF)
    scene.loc(CB_LOC.ACHEY, ['Chop'], effect=gives(scene, CB_ID.ACHEY_LOGS, CB_NAME.ACHEY_LOGS))
    expect(run(arrows.chop_achey(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.ACHEY])
    expect(scene.has(CB_ID.ACHEY_LOGS)).to_be(True)


test('a chop walks to the grove and lands a log', chops_a_log)


def chop_failures():
    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(arrows.chop_achey(scene.log))).to_be(False)

    scene = Scene(CB_TILE.ACHEY)
    expect(run(arrows.chop_achey(scene.log))).to_be(False)
    expect(scene.logged('no Achey Tree')).to_be(True)

    scene = Scene(CB_TILE.ACHEY)
    scene.loc(CB_LOC.ACHEY, ['Chop'], effect=refuse)
    expect(run(arrows.chop_achey(scene.log))).to_be(False)

    scene = Scene(CB_TILE.ACHEY)
    scene.loc(CB_LOC.ACHEY, ['Chop'])
    expect(run(arrows.chop_achey(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(40000)


test('a chop fails on a blocked walk, no tree, a refused click or no log in its window', chop_failures)


def wolf_scene(at):
    scene = Scene(at)
    spy_on(npcs, 'all', impl=lambda: list(scene.npcs))
    return scene


def wolf_falls(scene, leaves_bones):
    def fall():
        scene.npcs = []
        if leaves_bones:
            scene.on_ground(CB_ID.WOLF_BONES, CB_NAME.WOLF_BONES)
    return fall


def wolf_fights(scene, leaves_bones):
    def effect(op):
        scene.fighting = True
        scene.later(wolf_falls(scene, leaves_bones))
    return effect


def bones_on_the_floor_save_a_fight():
    scene = wolf_scene(CB_TILE.WOLVES)
    scene.on_ground(CB_ID.WOLF_BONES, CB_NAME.WOLF_BONES)
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(True)
    expect(scene.has(CB_ID.WOLF_BONES)).to_be(True)
    expect(scene.ticks).to_be(0)


test('bones already on the floor save a fight', bones_on_the_floor_save_a_fight)


def bones_that_will_not_lift():
    scene = wolf_scene(CB_TILE.WOLVES)
    scene.on_ground(CB_ID.WOLF_BONES, CB_NAME.WOLF_BONES, effect=refuse)
    expect(run(arrows.take_bones(0))).to_be(False)

    scene = wolf_scene(CB_TILE.WOLVES)
    scene.on_ground(CB_ID.WOLF_BONES, CB_NAME.WOLF_BONES, effect=counted([], True))
    expect(run(arrows.take_bones(0))).to_be(False)


test('bones that refuse the click or never reach the pack are not taken', bones_that_will_not_lift)


def kills_a_wolf():
    scene = wolf_scene(FAR_OFF)
    scene.npc(CB_NPC.WOLF, ['Attack'], effect=wolf_fights(scene, True))
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.WOLVES])
    expect(scene.has(CB_ID.WOLF_BONES)).to_be(True)


test('a wolf is walked to, fought and its bones picked up', kills_a_wolf)


def wolf_failures():
    scene = wolf_scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)

    scene = wolf_scene(CB_TILE.WOLVES)
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)
    expect(scene.logged('no Wolf in reach')).to_be(True)

    scene = wolf_scene(CB_TILE.WOLVES)
    scene.npc(CB_NPC.WOLF, ['Attack'], effect=refuse)
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)

    scene = wolf_scene(CB_TILE.WOLVES)
    scene.npc(CB_NPC.WOLF, ['Attack'])
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)
    expect(scene.logged('outlasted')).to_be(False)

    scene = wolf_scene(CB_TILE.WOLVES)
    scene.fighting = True
    scene.npc(CB_NPC.WOLF, ['Attack'])
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)
    expect(scene.logged('the wolf outlasted its fight window')).to_be(True)

    scene = wolf_scene(CB_TILE.WOLVES)
    scene.npc(CB_NPC.WOLF, ['Attack'], effect=wolf_fights(scene, False))
    expect(run(arrows.kill_wolf_for_bones(scene.log))).to_be(False)
    expect(scene.logged('the wolf left no bones')).to_be(True)


test('a wolf fails on a blocked walk, no wolf, a refused click, no fight, a long fight or no bones', wolf_failures)


def arrow_chain_at_each_pack():
    full = {CB_ID.ARROW: supplies.ARROW_TARGET}
    expect(arrows.arrow_step(snap(5, full), 70)).to_be_null()

    tipped = arrows.arrow_step(snap(5, {CB_ID.FLIGHTED: 6, CB_ID.ARROWTIPS: 6}), 70)
    expect(tipped.product).to_be(CB_NAME.ARROW)

    low = arrows.arrow_step(snap(5, {CB_ID.FLIGHTED: 6}), 4)
    expect(low.kind).to_be('wait')
    expect(low.reason).to_contain('Crafting 5 (have 4)')

    chisel = arrows.arrow_step(snap(5, {CB_ID.FLIGHTED: 6, CB_ID.WOLF_BONES: 1}), 70)
    expect(chisel.item).to_be(CB_NAME.CHISEL)
    expect(chisel.product).to_be(CB_NAME.ARROWTIPS)

    expect(arrows.arrow_step(snap(5, {CB_ID.FLIGHTED: 6}), 70).run).to_be(arrows.kill_wolf_for_bones)
    expect(arrows.arrow_step(snap(5, {}), 70).run).to_be(arrows.chop_achey)
    expect(arrows.arrow_step(snap(5, {CB_ID.ACHEY_LOGS: 1}), 70).item).to_be(CB_NAME.KNIFE)

    feathered = arrows.arrow_step(snap(5, {CB_ID.SHAFT: 6, CB_ID.FEATHER: 24}), 70)
    expect(feathered.product).to_be(CB_NAME.FLIGHTED)

    short = arrows.arrow_step(snap(5, {CB_ID.SHAFT: 6, CB_ID.FEATHER: 3}), 70)
    expect(short.reason).to_be('no feathers to flight the ogre arrow shafts with')


test('the arrow chain names the next move for each pack', arrow_chain_at_each_pack)


def feathers_cover_what_is_left():
    expect(arrows.feathers_needed(snap(5, {}))).to_be(supplies.ARROW_TARGET * 4)
    expect(arrows.feathers_needed(snap(5, {CB_ID.ARROW: 6, CB_ID.FLIGHTED: 2}))).to_be(16)
    expect(arrows.feathers_needed(snap(5, {CB_ID.ARROW: 20}))).to_be(0)


test('feathers are only wanted for arrows not yet flighted', feathers_cover_what_is_left)


# The ogre chest.

def unlocks(scene):
    def effect(op):
        scene.locs = []
        scene.loc(CB_LOC.CHEST_OPEN, ['Search'], id=CB_LOC_ID.CHEST_OPEN, effect=gives(scene, CB_ID.BELLOWS_EMPTY, 'Ogre bellows'))
    return effect


def says_empty(scene):
    def effect(op):
        scene.say('You find nothing in the ogre chest.')
    return effect


def chest_already_done():
    scene = Scene(FAR_OFF)
    scene.item(CB_ID.BELLOWS1, 'Ogre bellows')
    expect(run(hunt.open_chest(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('bellows in the pack need no chest', chest_already_done)


def chest_unlock_then_search():
    scene = Scene(FAR_OFF)
    scene.loc(CB_LOC.CHEST_LOCKED, ['Unlock'], id=CB_LOC_ID.CHEST, effect=unlocks(scene))
    expect(run(hunt.open_chest(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.CHEST])
    expect(scene.has(CB_ID.BELLOWS_EMPTY)).to_be(True)
    expect(hunt.chest_state.refused).to_be(False)


test('the chest is walked to, unlocked and searched', chest_unlock_then_search)


def chest_empty_refuses():
    scene = Scene(CB_TILE.CHEST)
    scene.loc(CB_LOC.CHEST_OPEN, ['Search'], id=CB_LOC_ID.CHEST_OPEN, effect=says_empty(scene))
    expect(run(hunt.open_chest(scene.log))).to_be(False)
    expect(hunt.chest_state.refused).to_be(True)
    expect(scene.logged('already owns a pair')).to_be(True)


test('an empty chest marks the refusal that pays for the bank trip', chest_empty_refuses)


def chest_failures():
    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(hunt.open_chest(scene.log))).to_be(False)

    scene = Scene(CB_TILE.CHEST)
    expect(run(hunt.open_chest(scene.log))).to_be(False)
    expect(scene.logged('no ogre chest at (2638,9397)')).to_be(True)

    scene = Scene(CB_TILE.CHEST)
    scene.loc(CB_LOC.CHEST_OPEN, ['Search'], id=CB_LOC_ID.CHEST_OPEN, effect=refuse)
    expect(run(hunt.open_chest(scene.log))).to_be(False)

    scene = Scene(CB_TILE.CHEST)
    scene.loc(CB_LOC.CHEST_LOCKED, ['Unlock'], id=CB_LOC_ID.CHEST, effect=refuse)
    expect(run(hunt.open_chest(scene.log))).to_be(False)
    expect(hunt.chest_state.refused).to_be(False)


test('the chest fails on a blocked walk, no chest or a refused click', chest_failures)


def chest_strength_rolls_run_out():
    scene = Scene(CB_TILE.CHEST)
    clicks = []
    scene.loc(CB_LOC.CHEST_LOCKED, ['Unlock'], id=CB_LOC_ID.CHEST, effect=counted(clicks, True))
    expect(run(hunt.open_chest(scene.log))).to_be(False)
    expect(clicks).to_have_length(6)
    expect(scene.logged('gave up no bellows')).to_be(True)
    expect(hunt.chest_state.refused).to_be(False)


test('six failed strength rolls give up without calling the chest empty', chest_strength_rolls_run_out)


# Bellows and toads.

def filled_bellows(scene, targets):
    def on_use(target):
        targets.append(target.index)
        scene.item(CB_ID.TOAD, CB_NAME.TOAD)
    return scene.item(CB_ID.BELLOWS3, 'Ogre bellows', on_use=on_use)


def fills(scene, targets):
    def on_use(target):
        targets.append(target.name)
        scene.take(CB_ID.BELLOWS_EMPTY)
        filled_bellows(scene, targets)
    return on_use


def swamp_with_empty_bellows():
    scene = Scene(FAR_OFF)
    targets = []
    scene.item(CB_ID.BELLOWS_EMPTY, 'Ogre bellows', on_use=fills(scene, targets))
    scene.loc(CB_LOC.BUBBLES, ['Use'], tile=CB_TILE.BUBBLE)
    return scene, targets


def fills_at_the_bubble_by_the_bank():
    scene, targets = swamp_with_empty_bellows()
    scene.loc(CB_LOC.BUBBLES, ['Use'], tile=Tile(2590, 2955, 0), dist=1)
    expect(run(hunt.fill_bellows(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.SWAMP])
    expect(targets).to_equal([CB_LOC.BUBBLES])
    expect(scene.has(CB_ID.BELLOWS3)).to_be(True)


test('the bellows fill at the bubble beside the bank, not the nearest', fills_at_the_bubble_by_the_bank)


def fill_failures():
    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS3, 'Ogre bellows')
    expect(run(hunt.fill_bellows(scene.log))).to_be(True)
    expect(scene.ticks).to_be(0)

    scene = Scene(CB_TILE.SWAMP)
    expect(run(hunt.fill_bellows(scene.log))).to_be(False)
    expect(scene.logged('no ogre bellows to fill')).to_be(True)

    scene, targets = swamp_with_empty_bellows()
    scene.walk_ok = False
    expect(run(hunt.fill_bellows(scene.log))).to_be(False)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS_EMPTY, 'Ogre bellows')
    scene.loc(CB_LOC.BUBBLES, ['Use'], tile=Tile(2590, 2955, 0), dist=1)
    expect(run(hunt.fill_bellows(scene.log))).to_be(False)
    expect(scene.logged('no usable Swamp bubbles beside (2598,2962)')).to_be(True)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS_EMPTY, 'Ogre bellows', on_use=refuse)
    scene.loc(CB_LOC.BUBBLES, ['Use'], tile=CB_TILE.BUBBLE)
    expect(run(hunt.fill_bellows(scene.log))).to_be(False)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS_EMPTY, 'Ogre bellows')
    scene.loc(CB_LOC.BUBBLES, ['Use'], tile=CB_TILE.BUBBLE)
    expect(run(hunt.fill_bellows(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(10000)


test('a fill fails on no bellows, a blocked walk, no bubble in reach, a refused use or no gas', fill_failures)


def inflates_after_filling():
    scene, targets = swamp_with_empty_bellows()
    toad = scene.npc(CB_NPC.TOAD)
    expect(run(hunt.inflate_one(0, scene.log))).to_be(True)
    expect(targets).to_equal([CB_LOC.BUBBLES, toad.index])
    expect(scene.has(CB_ID.TOAD)).to_be(True)


test('empty bellows are filled, then used on a toad', inflates_after_filling)


def inflate_failures():
    scene = Scene(CB_TILE.SWAMP)
    expect(run(hunt.inflate_one(0, scene.log))).to_be(False)
    expect(scene.logged('no ogre bellows to fill')).to_be(True)

    scene = Scene(FAR_OFF)
    scene.item(CB_ID.BELLOWS2, 'Ogre bellows')
    scene.walk_ok = False
    expect(run(hunt.inflate_one(0, scene.log))).to_be(False)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS2, 'Ogre bellows')
    expect(run(hunt.inflate_one(0, scene.log))).to_be(False)
    expect(scene.logged('no Swamp toad in reach')).to_be(True)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS1, 'Ogre bellows', on_use=refuse)
    scene.npc(CB_NPC.TOAD)
    expect(run(hunt.inflate_one(0, scene.log))).to_be(False)

    scene = Scene(CB_TILE.SWAMP)
    scene.item(CB_ID.BELLOWS1, 'Ogre bellows')
    scene.npc(CB_NPC.TOAD)
    expect(run(hunt.inflate_one(0, scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(12000)


test('an inflate fails on no bellows, a blocked walk, no toad, a refused use or no bait', inflate_failures)


def catches_up_to_the_ceiling():
    scene = Scene(CB_TILE.SWAMP)
    targets = []
    filled_bellows(scene, targets)
    near = scene.npc(CB_NPC.TOAD)
    far = scene.npc(CB_NPC.TOAD)
    expect(run(hunt.catch_toad(scene.log))).to_be(True)
    expect(scene.pack[1:]).to_have_length(3)
    expect(targets).to_equal([near.index, far.index, near.index])


test('bait is caught from toad to toad up to the three the quest allows', catches_up_to_the_ceiling)


def catch_gives_up():
    scene = Scene(CB_TILE.SWAMP)
    clicks = []
    scene.item(CB_ID.BELLOWS3, 'Ogre bellows', on_use=counted(clicks, True))
    scene.npc(CB_NPC.TOAD)
    expect(run(hunt.catch_toad(scene.log))).to_be(False)
    expect(clicks).to_have_length(5)


test('five inflates with nothing to show fail the catch', catch_gives_up)


# The bait.

def toad_item(scene):
    def effect(op):
        discard_one(scene, CB_ID.TOAD)
        scene.npc(CB_NAME.TOAD)
    return scene.item(CB_ID.TOAD, CB_NAME.TOAD, effect=effect)


def toad_that_hops_away(scene):
    def effect(op):
        discard_one(scene, CB_ID.TOAD)
    return scene.item(CB_ID.TOAD, CB_NAME.TOAD, effect=effect)


def drops_a_toad_from_the_clearing():
    scene = Scene(FAR_OFF)
    toad_item(scene)
    scene.main_modal = MODAL
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    expect(run(hunt.drop_bait(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.BAIT])
    expect(hunt.bait_placed()).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('bait is walked to the clearing and dropped there', drops_a_toad_from_the_clearing)


def drop_failures():
    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.drop_bait(scene.log))).to_be(False)
    expect(scene.logged('no Bloated toad to place')).to_be(True)

    scene = Scene(FAR_OFF)
    toad_item(scene)
    scene.walk_ok = False
    expect(run(hunt.drop_bait(scene.log))).to_be(False)

    scene = Scene(FAR_OFF)
    toad_item(scene)
    spy_on(traversal, 'walk_resilient', impl=walk_without_moving)
    expect(run(hunt.drop_bait(scene.log))).to_be(False)
    expect(scene.logged('not standing inside the bait clearing')).to_be(True)
    expect(scene.has(CB_ID.TOAD)).to_be(True)

    scene = Scene(CB_TILE.BAIT)
    scene.item(CB_ID.TOAD, CB_NAME.TOAD, effect=refuse)
    expect(run(hunt.drop_bait(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    scene.item(CB_ID.TOAD, CB_NAME.TOAD)
    expect(run(hunt.drop_bait(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(8000)


test('a drop fails on no toad, a blocked walk, the wrong spot, a refused click or a toad kept', drop_failures)


def keeps_bait_from_each_start():
    scene = Scene(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    expect(run(hunt.keep_bait_down(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(FAR_OFF)
    scene.npc(CB_NAME.TOAD)
    scene.item(CB_ID.TOAD, CB_NAME.TOAD)
    expect(run(hunt.keep_bait_down(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.BAIT])
    expect(scene.has(CB_ID.TOAD)).to_be(True)

    scene = Scene(CB_TILE.BAIT)
    toad_item(scene)
    expect(run(hunt.keep_bait_down(scene.log))).to_be(True)
    expect(scene.has(CB_ID.TOAD)).to_be(False)
    expect(hunt.bait_placed()).to_be(True)


test('placed bait is left alone, and a toad in the pack is put down', keeps_bait_from_each_start)


def keep_bait_failures():
    scene = Scene(FAR_OFF)
    expect(run(hunt.keep_bait_down(scene.log))).to_be(False)
    expect(scene.logged('no ogre bellows to fill')).to_be(True)

    scene = Scene(FAR_OFF)
    scene.item(CB_ID.TOAD, CB_NAME.TOAD)
    scene.no_walk = [CB_TILE.BAIT]
    expect(run(hunt.keep_bait_down(scene.log))).to_be(False)
    expect(scene.walks).to_equal([CB_TILE.BAIT])

    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.keep_bait_down(scene.log))).to_be(False)
    expect(scene.logged('no ogre bellows to fill')).to_be(True)


test('no toad to catch or no way to the clearing leaves no bait', keep_bait_failures)


def rantz_miss_lines():
    expect(hunt.rantz_missed('Rantz keeps missing the bird')).to_be(True)
    expect(hunt.rantz_missed("De'ese arrows are RUBBISH!")).to_be(True)
    expect(hunt.rantz_missed('Rantz hits the bird')).to_be(False)


test("either of Rantz's lines counts as a miss", rantz_miss_lines)


def says_miss(scene):
    def effect():
        scene.say('Rantz keeps missing the chompy bird.')
    return effect


def removes_bait(scene):
    def effect():
        scene.npcs = []
    return effect


def watches_the_miss():
    scene = Scene(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    scene.later(says_miss(scene))
    expect(run(hunt.watch_rantz_shoot(scene.log))).to_be(True)
    expect(scene.logged('Rantz shot at the chompy and missed')).to_be(True)


test("the watch ends on Rantz's miss", watches_the_miss)


def rebaits_when_the_toad_goes():
    scene = Scene(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    toad_item(scene)
    scene.later(removes_bait(scene))
    scene.later(says_miss(scene))
    expect(run(hunt.watch_rantz_shoot(scene.log))).to_be(True)
    expect(scene.has(CB_ID.TOAD)).to_be(False)
    expect(scene.logged('re-baiting')).to_be(False)


test('a toad gone without a shot is replaced', rebaits_when_the_toad_goes)


def watch_failures():
    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.watch_rantz_shoot(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    expect(run(hunt.watch_rantz_shoot(scene.log))).to_be(False)
    expect(len([line for line in scene.lines if 're-baiting' in line])).to_be(4)
    expect(scene.clock).to_be(240000)


test('no bait, or four quiet minutes, fails the watch', watch_failures)


# The hunt.

def plucks(scene):
    def effect(op):
        scene.on_ground(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY)
    return effect


def dead_bird(scene, effect=None):
    scene.npcs = []
    scene.npc(CB_NPC.CHOMPY, ['Pluck'], effect=effect if effect is not None else plucks(scene))


def falls(scene):
    def fall():
        dead_bird(scene)
    return fall


def lands(scene, effect):
    def land():
        scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=effect)
    return land


def shot_plan(scene, plan, clicks):
    """Each Attack queues the plan's next happening, for the player's next wait."""
    def effect(op):
        clicks.append(op)
        if len(plan) > 0:
            scene.later(plan.pop(0))
    return effect


def armed(at):
    scene = Scene(at)
    scene.wear(CB_NAME.BOW, CB_ID.BOW)
    scene.wear(CB_NAME.ARROW, CB_ID.ARROW)
    return scene


def quiver_empties(scene):
    def effect():
        scene.worn = [w for w in scene.worn if w.id != CB_ID.ARROW]
    return effect


def quiver_empties_onto_the_floor(scene):
    def effect():
        scene.worn = [w for w in scene.worn if w.id != CB_ID.ARROW]
        scene.on_ground(CB_ID.ARROW, CB_NAME.ARROW)
    return effect


def hunt_with_a_carcass():
    scene = Scene(CB_TILE.BAIT)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(scene.ticks).to_be(0)


test('a carcass in the pack needs no hunt', hunt_with_a_carcass)


def hunt_plucks_a_found_bird():
    scene = Scene(CB_TILE.BAIT)
    dead_bird(scene)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(scene.has(CB_ID.RAW_CHOMPY)).to_be(True)


test('a bird already down is plucked without arming', hunt_plucks_a_found_bird)


def hunt_shoots_a_landed_bird():
    scene = armed(CB_TILE.BAIT)
    clicks = []
    scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=shot_plan(scene, [falls(scene)], clicks))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(clicks).to_equal(['Attack'])
    expect(scene.has(CB_ID.RAW_CHOMPY)).to_be(True)
    expect(scene.walks).to_have_length(0)


test('a bird in range is shot and plucked', hunt_shoots_a_landed_bird)


def hunt_baits_for_a_bird():
    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    clicks = []
    scene.later(lands(scene, shot_plan(scene, [falls(scene)], clicks)))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(clicks).to_have_length(1)
    expect(scene.has(CB_ID.RAW_CHOMPY)).to_be(True)


test('with no bird about it baits, waits for a landing and shoots', hunt_baits_for_a_bird)


def hunt_bird_dies_during_the_wait():
    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    scene.later(falls(scene))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(scene.has(CB_ID.RAW_CHOMPY)).to_be(True)


test('a bird that dies while waiting is plucked with no shot', hunt_bird_dies_during_the_wait)


def hunt_refills_a_dry_quiver():
    scene = armed(CB_TILE.BAIT)
    clicks = []
    scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=shot_plan(scene, [quiver_empties_onto_the_floor(scene), falls(scene)], clicks))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(clicks).to_have_length(2)
    expect(scene.has(CB_ID.RAW_CHOMPY)).to_be(True)
    expect(len([w for w in scene.worn if w.id == CB_ID.ARROW])).to_be(1)


test('a quiver run dry mid-fight is refilled from the floor and the bird shot again', hunt_refills_a_dry_quiver)


def hunt_dry_with_nothing_to_recover():
    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=shot_plan(scene, [quiver_empties(scene)], []))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(scene.logged('no Ogre arrow to quiver')).to_be(True)
    expect(scene.logged('the chompy outlasted its shot window')).to_be(True)


test('a dry quiver with no arrows to find abandons the shot', hunt_dry_with_nothing_to_recover)


def hunt_recovers_before_arming():
    scene = Scene(CB_TILE.BAIT)
    scene.wear(CB_NAME.BOW, CB_ID.BOW)
    scene.on_ground(CB_ID.ARROW, CB_NAME.ARROW)
    scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=shot_plan(scene, [falls(scene)], []))
    expect(run(hunt.hunt_chompy(scene.log))).to_be(True)
    expect(len([w for w in scene.worn if w.id == CB_ID.ARROW])).to_be(1)


test('with no arrows anywhere on the player it picks spent ones up first', hunt_recovers_before_arming)


def hunt_failures():
    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(scene.logged('no Ogre bow to wield')).to_be(True)

    scene = armed(CB_TILE.BAIT)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(scene.logged('no ogre bellows to fill')).to_be(True)

    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NPC.CHOMPY, ['Attack'], effect=refuse)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)


test('a hunt fails with no bow, no bait or a refused shot', hunt_failures)


def hunt_rounds_run_out():
    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NPC.CHOMPY, ['Attack'])
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(len([line for line in scene.lines if 'outlasted its shot window' in line])).to_be(4)

    scene = armed(CB_TILE.BAIT)
    scene.npc(CB_NAME.TOAD)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(len([line for line in scene.lines if 're-baiting' in line])).to_be(4)

    scene = armed(CB_TILE.BAIT)
    for n in range(4):
        toad_that_hops_away(scene)
    expect(run(hunt.hunt_chompy(scene.log))).to_be(False)
    expect(scene.has(CB_ID.TOAD)).to_be(False)


test('four rounds of long shots, quiet bait or vanishing bait fail the hunt', hunt_rounds_run_out)


def pluck_failures():
    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.pluck_chompy(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    dead_bird(scene, refuse)
    expect(run(hunt.pluck_chompy(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    dead_bird(scene, counted([], True))
    expect(run(hunt.pluck_chompy(scene.log))).to_be(False)
    expect(scene.logged('the pluck left no raw chompy')).to_be(True)

    scene = Scene(CB_TILE.BAIT)
    dead_bird(scene, counted([], True))
    scene.on_ground(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, effect=refuse)
    expect(run(hunt.pluck_chompy(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    dead_bird(scene, counted([], True))
    scene.on_ground(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, effect=counted([], True))
    expect(run(hunt.pluck_chompy(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(8000)


test('a pluck fails on no bird, a refused click, no carcass or a carcass that will not lift', pluck_failures)


def lifts_one_stack(scene):
    def effect(op):
        scene.ground.pop(0)
        scene.item(CB_ID.ARROW, CB_NAME.ARROW)
    return effect


def recovers_at_most_four_stacks():
    scene = Scene(CB_TILE.BAIT)
    for n in range(5):
        scene.on_ground(CB_ID.ARROW, CB_NAME.ARROW, effect=lifts_one_stack(scene))
    expect(run(hunt.recover_arrows())).to_be(True)
    expect(scene.ground).to_have_length(1)
    expect(scene.pack).to_have_length(4)


test('spent arrows are recovered four stacks at a time', recovers_at_most_four_stacks)


def recover_failures():
    scene = Scene(CB_TILE.BAIT)
    expect(run(hunt.recover_arrows())).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    scene.on_ground(CB_ID.ARROW, CB_NAME.ARROW, effect=refuse)
    expect(run(hunt.recover_arrows())).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    scene.on_ground(CB_ID.ARROW, CB_NAME.ARROW, effect=counted([], True))
    expect(run(hunt.recover_arrows())).to_be(False)


test('no arrows, a refused take or an arrow that never lands recovers nothing', recover_failures)


def arming():
    scene = Scene(CB_TILE.BAIT)
    scene.item(CB_ID.BOW, CB_NAME.BOW)
    scene.item(CB_ID.ARROW, CB_NAME.ARROW)
    expect(run(hunt.arm_for_chompy(scene.log))).to_be(True)
    expect(scene.pack).to_have_length(0)
    expect(scene.worn).to_have_length(2)

    scene = Scene(CB_TILE.BAIT)
    scene.item(CB_ID.BOW, 'A bow that will not wield')
    expect(run(hunt.arm_for_chompy(scene.log))).to_be(False)

    scene = Scene(CB_TILE.BAIT)
    scene.wear(CB_NAME.BOW, CB_ID.BOW)
    expect(run(hunt.arm_for_chompy(scene.log))).to_be(False)
    expect(scene.logged('no Ogre arrow to quiver')).to_be(True)

    scene = Scene(CB_TILE.BAIT)
    scene.wear(CB_NAME.BOW, CB_ID.BOW)
    scene.item(CB_ID.ARROW, 'An arrow that will not quiver')
    expect(run(hunt.arm_for_chompy(scene.log))).to_be(False)


test('arming wields the bow and quivers the arrows, or says which is missing', arming)


# The roast.

def spit_scene(at):
    scene = Scene(at)
    scene.loc(CB_LOC.SPIT, ['Use'], id=CB_LOC_ID.SPIT_EMPTY)
    return scene


def roasted(scene):
    def on_use(target):
        scene.take(CB_ID.RAW_CHOMPY)
        scene.item(CB_ID.SEASONED_CHOMPY, CB_NAME.SEASONED_CHOMPY)
    return on_use


def burns(scene, drops):
    def on_use(target):
        scene.take(CB_ID.RAW_CHOMPY)
        scene.item(CB_ID.RUINED_CHOMPY, CB_NAME.RUINED_CHOMPY, effect=counted(drops, True))
    return on_use


def box_says(scene, text):
    def on_use(target):
        scene.main_modal = MODAL
        scene.main_texts = [text]
    return on_use


def roasts_a_chompy():
    scene = spit_scene(FAR_OFF)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, on_use=roasted(scene))
    expect(run(cook.cook_chompy(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.SPIT])
    expect(scene.has(CB_ID.SEASONED_CHOMPY)).to_be(True)


test('the chompy is walked to the empty spit and roasted', roasts_a_chompy)


def roast_already_done():
    scene = Scene(FAR_OFF)
    scene.item(CB_ID.SEASONED_CHOMPY, CB_NAME.SEASONED_CHOMPY)
    expect(run(cook.cook_chompy(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('a seasoned chompy in the pack needs no roast', roast_already_done)


def burnt_is_dropped():
    scene = spit_scene(CB_TILE.SPIT)
    drops = []
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, on_use=burns(scene, drops))
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(scene.logged('the chompy burnt')).to_be(True)
    expect(drops).to_equal([('Drop',)])


test('a burnt chompy is dropped and fails the roast', burnt_is_dropped)


def roast_wants_the_kids():
    cook.cook_state.kids_asked = True
    scene = spit_scene(CB_TILE.SPIT)
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, on_use=box_says(scene, 'You need to find out what Bugs wants.'))
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(scene.logged('the spit wants the kids asked first')).to_be(True)
    expect(cook.cook_state.kids_asked).to_be(False)
    expect(scene.main_modal).to_be(-1)
    expect(scene.clock).to_be_less_than(25000)


test('a spit that wants the kids asked sends the leg back to them', roast_wants_the_kids)


def roast_short_of_ingredients():
    cook.cook_state.kids_asked = True
    scene = spit_scene(CB_TILE.SPIT)
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, on_use=box_says(scene, "You don't have all the ingredients."))
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(cook.cook_state.kids_asked).to_be(True)
    expect(scene.logged('the spit wants')).to_be(False)
    expect(scene.main_modal).to_be(-1)
    expect(scene.clock).to_be_less_than(25000)


test('a spit short of ingredients fails at once and keeps the kids asked', roast_short_of_ingredients)


def roast_failures():
    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(cook.cook_chompy(scene.log))).to_be(False)

    scene = Scene(CB_TILE.SPIT)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY)
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(scene.logged('the ogre spit-roast is still busy')).to_be(True)

    scene = spit_scene(CB_TILE.SPIT)
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(scene.logged('no Raw chompy to roast')).to_be(True)

    scene = spit_scene(CB_TILE.SPIT)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY, on_use=refuse)
    expect(run(cook.cook_chompy(scene.log))).to_be(False)

    scene = spit_scene(CB_TILE.SPIT)
    scene.item(CB_ID.RAW_CHOMPY, CB_NAME.RAW_CHOMPY)
    expect(run(cook.cook_chompy(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(25000)


test('a roast fails on a blocked walk, a busy spit, no bird, a refused use or no result', roast_failures)


def seasoning_order():
    expect(cook.seasoning_step(snap(55, {})).name).to_be('pick a potato')

    equa = cook.seasoning_step(snap(55, {CB_ID.POTATO: 1, CB_ID.CABBAGE: 1}))
    expect(equa.kind).to_be('grab_ground')
    expect(equa.item).to_be(CB_NAME.EQUA)
    expect(equa.anchor).to_be(CB_TILE.EQUA)

    expect(cook.seasoning_step(snap(55, SEASONED))).to_be_null()


test('seasonings come in round-trip order, by patch or off the floor', seasoning_order)


def picks_a_patch():
    scene = Scene(FAR_OFF)
    scene.loc('null', ['Pick'], id=1161, effect=gives(scene, CB_ID.CABBAGE, CB_NAME.CABBAGE))
    step = cook.seasoning_step(snap(55, {CB_ID.POTATO: 1}))
    expect(step.name).to_be('pick a cabbage')
    expect(run(step.run(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.CABBAGE])
    expect(scene.has(CB_ID.CABBAGE)).to_be(True)


test('a patch is found by its id, since the cabbage has no name', picks_a_patch)


def patch_failures():
    pick = cook.pick_patch(1161, CB_NAME.CABBAGE, CB_ID.CABBAGE, CB_TILE.CABBAGE)

    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(pick(scene.log))).to_be(False)

    scene = Scene(CB_TILE.CABBAGE)
    scene.loc('Not this one', ['Pick'], id=312)
    expect(run(pick(scene.log))).to_be(False)
    expect(scene.logged('no Cabbage patch in reach of (2645,2958)')).to_be(True)

    scene = Scene(CB_TILE.CABBAGE)
    scene.loc('null', ['Pick'], id=1161, effect=refuse)
    expect(run(pick(scene.log))).to_be(False)

    scene = Scene(CB_TILE.CABBAGE)
    scene.loc('null', ['Pick'], id=1161)
    expect(run(pick(scene.log))).to_be(False)
    expect(scene.clock).to_be_greater_than_or_equal(10000)


test('a pick fails on a blocked walk, the wrong patch, a refused click or no crop', patch_failures)


def asks_both_children():
    scene = Scene(FAR_OFF)
    scene.npc(CB_NPC.BUGS, ['Talk-to'], effect=chats(scene, ['continue']))
    scene.npc(CB_NPC.FYCIE, ['Talk-to'], effect=chats(scene, ['continue']))
    expect(run(cook.ask_kids(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.BUGS, CB_TILE.FYCIE])
    expect(cook.cook_state.kids_asked).to_be(True)


test('both children are walked to and asked', asks_both_children)


def kids_failures():
    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(cook.ask_kids(scene.log))).to_be(False)
    expect(cook.cook_state.kids_asked).to_be(False)

    scene = Scene(CB_TILE.BUGS)
    scene.npc(CB_NPC.BUGS, ['Talk-to'], effect=chats(scene, ['continue']))
    expect(run(cook.ask_kids(scene.log))).to_be(False)
    expect(scene.logged('Fycie did not answer')).to_be(True)
    expect(cook.cook_state.kids_asked).to_be(False)


test('a blocked walk or a child who will not answer leaves them unasked', kids_failures)


# Rantz.

def rantz_scene():
    scene = Scene(FAR_OFF)
    scene.npc(CB_NPC.RANTZ, ['Talk-to'])
    return scene


def talk_rantz_paths():
    scene = Scene(FAR_OFF)
    expect(run(cb.talk_rantz(Record({'expect': lambda: True}), scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(cb.talk_rantz(Record({}), scene.log))).to_be(False)
    expect(scene.walks).to_equal([CB_TILE.RANTZ])


test('Rantz is skipped once the goal is met, and a blocked walk fails the talk', talk_rantz_paths)


def agrees_to_stabbers():
    scene = rantz_scene()
    scene.chat.pages = ['continue', ["Er, make you're own 'stabbers'!", cb.STABBERS[1]], 'continue']
    expect(run(cb.start_quest(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.RANTZ])
    expect(scene.chat.chosen).to_equal([cb.STABBERS[1]])


test('the quest is started by agreeing to the stabbers, not refusing', agrees_to_stabbers)


def hands_arrows_over():
    scene = rantz_scene()
    scene.item(CB_ID.ARROW, CB_NAME.ARROW, count=6)
    scene.chat.pages = [[cb.TOADIES, cb.THANKS], [cb.TOADIES, cb.THANKS]]

    def takes(text):
        scene.take(CB_ID.ARROW)

    scene.chat.on_choose = takes
    expect(run(cb.give_arrows(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal([cb.TOADIES, cb.THANKS])


test('the arrows go over with the toadies question asked just once', hands_arrows_over)


def arrows_kept():
    scene = rantz_scene()
    scene.item(CB_ID.ARROW, CB_NAME.ARROW, count=6)
    scene.chat.pages = ['continue']
    expect(run(cb.give_arrows(scene.log))).to_be(False)
    expect(scene.logged('Rantz did not take the six ogre arrows')).to_be(True)


test('arrows still in the pack mean Rantz did not take them', arrows_kept)


def toad_talks():
    for leg, chain in [[cb.ask_toadies, [[cb.TOADIES, cb.THANKS], [cb.TOADIES, cb.THANKS]]], [cb.show_toad, [[cb.THANKS]]], [cb.show_chompy, [[cb.THANKS]]]]:
        scene = rantz_scene()
        scene.chat.pages = list(chain)
        expect(run(leg(scene.log))).to_be(True)
        expect(scene.chat.chosen[-1]).to_be(cb.THANKS)


test('the toad and chompy talks end on the thanks', toad_talks)


def lends_on_the_last_page(scene):
    def effect(text):
        if 'strong' in text:
            scene.item(CB_ID.BOW, CB_NAME.BOW)
    return effect


def bow_paths():
    scene = rantz_scene()
    scene.item(CB_ID.BOW, CB_NAME.BOW)
    expect(run(cb.get_bow(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = rantz_scene()
    scene.wear(CB_NAME.BOW, CB_ID.BOW)
    expect(run(cb.get_bow(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = rantz_scene()
    scene.chat.pages = [['No thanks', 'Come on, let me have a go'], ['No', "I'm actually quite strong"]]
    scene.chat.on_choose = lends_on_the_last_page(scene)
    expect(run(cb.get_bow(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Come on, let me have a go', "I'm actually quite strong"])

    scene = rantz_scene()
    scene.chat.pages = ['continue']
    expect(run(cb.get_bow(scene.log))).to_be(False)


test('a bow in hand is the only proof the loan landed', bow_paths)


def takes_the_chompy(scene):
    def effect(text):
        scene.take(CB_ID.SEASONED_CHOMPY)
    return effect


def handing_over():
    scene = rantz_scene()
    expect(run(cb.hand_over(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = rantz_scene()
    scene.item(CB_ID.SEASONED_CHOMPY, CB_NAME.SEASONED_CHOMPY)
    scene.chat.pages = ['continue', [cb.THANKS]]
    scene.chat.on_choose = takes_the_chompy(scene)
    expect(run(cb.hand_over(scene.log))).to_be(True)
    expect(scene.has(CB_ID.SEASONED_CHOMPY)).to_be(False)


test('the seasoned chompy gone from the pack is what ends the handover', handing_over)


def gives_both_tools(scene):
    def effect(text):
        scene.item(CB_ID.KNIFE, CB_NAME.KNIFE)
        scene.item(CB_ID.CHISEL, CB_NAME.CHISEL)
    return effect


def bugs_sells_tools():
    scene = Scene(FAR_OFF)
    scene.chat.pages = [['No thanks', "Ok, I'll give you 10 bright pretties."], 'continue']
    scene.chat.on_choose = gives_both_tools(scene)
    expect(run(cb.buy_tools(scene.log))).to_be(True)
    expect(scene.walks).to_equal([CB_TILE.BUGS])

    scene = Scene(FAR_OFF)
    scene.walk_ok = False
    expect(run(cb.buy_tools(scene.log))).to_be(False)


test('Bugs sells the tools, unless the walk there is blocked', bugs_sells_tools)


# The steps decide() builds.

def kit_steps():
    wanted = {'rune scimitar': 1}
    expect(cb.kit_step(snap(5))).to_be_null()

    withdraw = cb.kit_step(snap(5, bank=wanted))
    expect(withdraw.kind).to_be('withdraw')
    expect(withdraw.items).to_equal([{'name': 'Rune scimitar', 'qty': 1}])

    expect(cb.kit_step(snap(5, bank=wanted, bank_known=False)).kind).to_be('scan_bank')

    scene = Scene(CB_TILE.RANTZ)
    scene.item(1333, 'Rune scimitar')
    wear = cb.kit_step(snap(5, inv={'rune scimitar': 1}))
    expect(wear.name).to_be('wear Rune scimitar')
    expect(run(wear.run(scene.log))).to_be(True)
    expect(scene.worn).to_have_length(1)


test('the melee kit is worn from the pack, withdrawn, or scanned for', kit_steps)


def bellows_steps():
    expect(cb.bellows_step(snap(20, {CB_ID.BELLOWS1: 1}))).to_be_null()
    expect(cb.bellows_step(snap(20)).run).to_be(hunt.open_chest)

    hunt.chest_state.refused = True
    expect(cb.bellows_step(snap(20, bank_known=False)).kind).to_be('scan_bank')
    expect(cb.bellows_step(snap(20, bank_ids={CB_ID.BELLOWS2: 1})).items[0]['id']).to_be(CB_ID.BELLOWS2)
    expect(cb.bellows_step(snap(20)).kind).to_be('wait')


test('bellows come from the chest, then the bank, then a stated wait', bellows_steps)


def shooting_steps():
    bow = {CB_ID.BOW: 1}
    expect(cb.shooting_leg(snap(45)).run).to_be(cb.get_bow)
    expect(cb.shooting_leg(snap(45, bow)).reason).to_be('no knife or chisel to fletch more ogre arrows with')
    expect(cb.shooting_leg(snap(45, bow, bank_known=False)).kind).to_be('scan_bank')

    tools = cb.shooting_leg(snap(45, bow, bank_ids={CB_ID.KNIFE: 1, CB_ID.CHISEL: 1}))
    expect([i['id'] for i in tools.items]).to_equal([CB_ID.KNIFE, CB_ID.CHISEL])

    expect(cb.shooting_leg(snap(45, {CB_ID.BOW: 1, CB_ID.ARROW: 6, CB_ID.BELLOWS3: 1}))).to_be_null()
    expect(cb.has_arrows(snap(45, {}, worn_ids=set([CB_ID.ARROW])))).to_be(True)
    expect(cb.has_bow(snap(45, {}, worn_ids=set([CB_ID.BOW])))).to_be(True)


test('a shot wants the bow, then arrows and tools, then bellows', shooting_steps)


def refletching_after_the_loan():
    tooled = {CB_ID.BOW: 1, CB_ID.KNIFE: 1, CB_ID.CHISEL: 1}

    axe = cb.shooting_leg(snap(45, tooled, inv={'coins': 2000}))
    expect(axe.kind).to_be('buy')
    expect(axe.item).to_be('Bronze axe')

    feathers = cb.shooting_leg(snap(45, tooled))
    expect(feathers.kind).to_be('buy')
    expect(feathers.item).to_be(CB_NAME.FEATHER)


test('a short quiver past the loan still needs an axe and feathers before fletching', refletching_after_the_loan)


def cook_steps():
    expect(cb.cook_leg(snap(55)).run).to_be(cook.ask_kids)

    cook.cook_state.kids_asked = True
    expect(cb.cook_leg(snap(55)).name).to_be('pick a potato')

    hunting = merged(SEASONED, {CB_ID.BOW: 1, CB_ID.ARROW: 6, CB_ID.BELLOWS3: 1})
    expect(cb.cook_leg(snap(55, hunting)).run).to_be(hunt.hunt_chompy)

    no_bellows = merged(SEASONED, {CB_ID.BOW: 1, CB_ID.ARROW: 6})
    expect(cb.cook_leg(snap(55, no_bellows)).run).to_be(hunt.open_chest)

    roast = merged(SEASONED, {CB_ID.RAW_CHOMPY: 1})
    expect(cb.cook_leg(snap(55, roast)).run).to_be(cook.cook_chompy)
    expect(cb.decide(snap(60, roast)).run).to_be(cook.cook_chompy)


test('the cook leg asks, seasons, hunts a lost bird and roasts', cook_steps)


def stage_steps():
    expect(cb.decide(snap(10, bank_known=False)).kind).to_be('scan_bank')
    expect(cb.decide(snap(25, {CB_ID.BELLOWS3: 1})).run).to_be(hunt.watch_rantz_shoot)
    expect(cb.decide(snap(25)).run).to_be(hunt.open_chest)
    expect(cb.decide(snap(45)).run).to_be(cb.get_bow)
    expect(cb.decide(snap(50)).run).to_be(cb.get_bow)


test('each stage leads with what is still missing', stage_steps)


def readiness_warnings():
    scene = Scene(CB_TILE.RANTZ)
    expect(cb.warn_readiness()).to_be_null()

    scene.stats = {'crafting': 4}
    expect(cb.warn_readiness()).to_be('untested below Crafting 5 (the chisel refuses wolf bones below it)')

    scene.stats = {'crafting': 4, 'strength': 10}
    expect(cb.warn_readiness()).to_contain(' and a melee kit')


test('readiness names the crafting and combat the quest was not tested below', readiness_warnings)


# Supplies.

def loadout_at_each_pack():
    expect(supplies.loadout_step(snap(5, bank_known=False)).kind).to_be('scan_bank')
    expect(supplies.loadout_step(snap(5))).to_be_null()

    cramped = {'coins': 500, 'bronze axe': 1, 'junk': 1}
    expect(supplies.loadout_step(snap(5, inv=cramped, free_slots=2)).kind).to_be('deposit')
    tidy = {'coins': 500, 'bronze axe': 1}
    expect(supplies.loadout_step(snap(5, inv=tidy, free_slots=2))).to_be_null()

    short = {'coins': 100, 'bronze axe': 1}
    expect(supplies.loadout_step(snap(5, inv=short, bank={'coins': 700})).items).to_equal([{'name': 'Coins', 'qty': 700}])
    expect(supplies.loadout_step(snap(5, inv=short, bank={'coins': 9000})).items).to_equal([{'name': 'Coins', 'qty': 1900}])

    no_axe = {'coins': 500}
    expect(supplies.loadout_step(snap(5, inv=no_axe, bank={'steel axe': 1})).items).to_equal([{'name': 'Steel axe', 'qty': 1}])
    buy = supplies.loadout_step(snap(5, inv=no_axe))
    expect(buy.kind).to_be('buy')
    expect(buy.item).to_be('Bronze axe')
    expect(supplies.loadout_step(snap(5, inv=no_axe), False)).to_be_null()


test('the loadout tidies the pack, then takes coins and an axe', loadout_at_each_pack)


def loadout_food():
    quest_food.name = '  Trout '
    expect(supplies.selected_food()).to_be('Trout')
    expect(supplies.keep_list()[-1]).to_be('trout')
    expect(supplies.loadout_step(snap(5, bank={'trout': 9})).items).to_equal([{'name': 'Trout', 'qty': supplies.FOOD_TARGET}])
    expect(supplies.loadout_step(snap(5, inv={'coins': 500, 'bronze axe': 1, 'trout': 2}))).to_be_null()
    expect(supplies.loadout_step(snap(5))).to_be_null()

    quest_food.name = '   '
    expect(supplies.selected_food()).to_be_null()


test('food is withdrawn and kept when one is chosen', loadout_food)


def tool_steps():
    both = {CB_ID.KNIFE: 1, CB_ID.CHISEL: 1}
    expect(supplies.tool_step(snap(5, both))).to_be_null()
    expect(supplies.tools_held(snap(5, both))).to_be(True)
    expect(supplies.tools_held(snap(5, {CB_ID.KNIFE: 1}))).to_be(False)
    expect(supplies.tool_step(snap(5, bank_known=False)).kind).to_be('scan_bank')
    expect(supplies.tool_step(snap(5, bank_ids={CB_ID.KNIFE: 1}))).to_be_null()

    chisel = supplies.tool_step(snap(5, {CB_ID.KNIFE: 1}, bank_ids={CB_ID.CHISEL: 1}))
    expect(chisel.items).to_equal([{'name': CB_NAME.CHISEL, 'qty': 1, 'id': CB_ID.CHISEL}])


test('tools come from the bank only when it holds every missing one', tool_steps)


def feather_steps():
    expect(supplies.feathers_step(snap(5, {CB_ID.FEATHER: 8}), 8)).to_be_null()
    expect(supplies.feathers_step(snap(5, bank_known=False), 8).kind).to_be('scan_bank')
    expect(supplies.feathers_step(snap(5, inv={'junk': 1}, free_slots=0), 8).kind).to_be('deposit')
    expect(supplies.feathers_step(snap(5, {CB_ID.FEATHER: 2}, bank_ids={CB_ID.FEATHER: 3}), 8).items[0]['qty']).to_be(3)

    buy = supplies.feathers_step(snap(5, {CB_ID.FEATHER: 2}), 8)
    expect(buy.qty).to_be(6)
    expect(buy.est_gp).to_be(24)
    expect(buy.shop.npc).to_be('Gerrant')


test('feathers come from the bank, then Gerrant', feather_steps)


def no_ids_read_as_nothing():
    bare = snap(5)
    bare.inv_ids = None
    bare.bank_ids = None
    bare.bank = None
    expect(supplies.held_id(bare, CB_ID.KNIFE)).to_be(0)
    expect(supplies.banked_id(bare, CB_ID.KNIFE)).to_be(0)
    expect(supplies.banked(bare, 'coins')).to_be(0)


test('a snapshot with no ids or bank reads as holding nothing', no_ids_read_as_nothing)


def cave_bounds():
    expect(in_cave(CB_TILE.BUGS)).to_be(True)
    expect(in_cave(CB_TILE.RANTZ)).to_be(False)
    expect(in_cave(None)).to_be(False)


test('the cave is told from the surface', cave_bounds)


# The journal.

def journal_says(lines):
    def read(name):
        return lines
        yield
    return read


def journal_statuses():
    scene = Scene(CB_TILE.RANTZ)
    scene.status = 'complete'
    expect(run(journal.read_chompy_progress()).stage).to_be(CB_STAGE.COMPLETE)

    scene.status = 'not_started'
    expect(run(journal.read_chompy_progress()).stage).to_be(CB_STAGE.NOT_STARTED)

    scene.status = 'unknown'
    expect(run(journal.read_chompy_progress())).to_be_null()


test('the quest tab answers for a finished, unstarted or unknown quest', journal_statuses)


def journal_keeps_the_last_good_page():
    Scene(CB_TILE.RANTZ)
    spy_on(quests, 'journal', impl=journal_says(['I showed Rantz the chompy']))
    expect(run(journal.read_chompy_progress()).stage).to_be(CB_STAGE.TOLD_TO_COOK)

    spy_on(quests, 'journal', impl=journal_says([]))
    expect(run(journal.read_chompy_progress()).stage).to_be(CB_STAGE.TOLD_TO_COOK)


test('an unreadable page falls back on the last good stage', journal_keeps_the_last_good_page)


def journal_closes_a_box():
    scene = Scene(CB_TILE.RANTZ)
    scene.main_modal = MODAL
    spy_on(quests, 'journal', impl=journal_says([]))
    expect(run(journal.read_chompy_progress())).to_be_null()
    expect(scene.main_modal).to_be(-1)
    expect(scene.ticks).to_be(1)


test('a box up during the read is closed', journal_closes_a_box)


def journal_markers():
    expect(journal.parse_chompy_journal(['nothing recognizable'])).to_be_null()
    stage = journal.parse_chompy_journal(["I agreed to get Rants some 'stabbers'", "I've killed a chompy bird!"]).stage
    expect(stage).to_be(CB_STAGE.KILLED_CHOMPY)


test('the newest marker on the page wins', journal_markers)

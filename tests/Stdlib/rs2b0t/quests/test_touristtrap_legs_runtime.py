"""Tourist Trap's legs against spied facades, up to the rescue: the strict dialogue driver, the camp, the mine, both
jails, Al Shabim's prototype and the stolen plans, each through its success and its failures."""

import rs2004.quests.defs.touristtrap as tt
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.navigation import reachability
from rs2004.quests.defs.touristtrap import ITEM, LOC, NPC

after_each(lambda: event_signal.set_interrupt(None))

CAMP = Tile(3290, 3025, 0)
UPPER = Tile(3290, 3033, 1)
DESERT = Tile(3260, 3050, 0)
MINE_IN = Tile(3278, 9420, 0)
LOWER = Tile(3303, 9416, 0)
DEEP = tt.DEEP_CART
CELL = tt.SURFACE_JAIL
TENT = Tile(3170, 3048, 0)
BEDABIN = tt.BEDABIN_TENT_APPROACH


def run(gen):
    return run_wait(gen)


def moves_to(scene, tile):
    def effect(op):
        scene.at = tile
    return effect


def chats(scene, pages):
    def effect(op):
        scene.chat.pages = list(pages)
    return effect


def answered_moves_to(scene, tile, option):
    """A click that asks one question, and answering it moves the player."""
    def choose(text):
        scene.at = tile
        scene.chat.on_choose = None

    def effect(op):
        scene.chat.pages = [[option]]
        scene.chat.on_choose = choose
    return effect


def dress(scene, outfit):
    for name in outfit:
        scene.wear(name)


# The strict dialogue driver.

def strict_choice_matches_whitespace_and_case():
    expect(tt.strict_tourist_trap_choice(['  Yes   PLEASE. ', 'No'], ['yes please.'])).to_be('  Yes   PLEASE. ')
    expect(tt.strict_tourist_trap_choice(['No'], ['yes please.'])).to_be_null()


test('choices match whatever their spacing and case, and nothing else', strict_choice_matches_whitespace_and_case)


def drives_to_the_end():
    scene = Scene(CAMP)
    scene.chat.pages = ['continue', ['Other', 'Pick me'], 'continue']
    expect(run(tt.drive_strict_dialog(['Pick me'], scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Pick me'])
    expect(scene.chat.pages).to_have_length(0)


test('the driver continues, picks, and ends when the dialogue shuts', drives_to_the_end)


def never_guesses():
    scene = Scene(CAMP)
    scene.chat.pages = [['New wording']]
    expect(run(tt.drive_strict_dialog(['Old wording'], scene.log))).to_be(False)
    expect(scene.logged('unrecognized options [New wording]')).to_be(True)
    expect(scene.chat.chosen).to_have_length(0)


test('a changed menu stops the driver rather than guessing', never_guesses)


def driver_stops_for_events_and_refusals():
    scene = Scene(CAMP)
    scene.chat.pages = ['continue']
    event_signal.set_interrupt(lambda: True)
    expect(run(tt.drive_strict_dialog([], scene.log))).to_be(False)
    event_signal.set_interrupt(None)

    def refuse(*args):
        return False
        yield

    scene = Scene(CAMP)
    scene.chat.pages = ['continue']
    spy_on(chat_dialog, 'continue_', impl=refuse)
    expect(run(tt.drive_strict_dialog([], scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.chat.pages = [['Pick me']]
    spy_on(chat_dialog, 'choose_option', impl=refuse)
    expect(run(tt.drive_strict_dialog(['Pick me'], scene.log))).to_be(False)


test('the driver stops for a runtime event, a refused continue or a refused pick', driver_stops_for_events_and_refusals)


def until_spans_the_gaps():
    scene = Scene(CAMP)
    state = {'done': False}

    def finish():
        state['done'] = True

    scene.later(lambda: None)
    scene.later(finish)
    expect(run(tt.drive_strict_dialog([], scene.log, lambda: state['done']))).to_be(True)
    expect(scene.ticks).to_be(2)


test('with a goal, a shut dialogue is only a gap until the goal holds', until_spans_the_gaps)


def driver_is_bounded():
    scene = Scene(CAMP)
    expect(run(tt.drive_strict_dialog([], scene.log, lambda: False))).to_be(False)
    expect(scene.logged('exceeded its bounded step count')).to_be(True)
    expect(scene.ticks).to_be(140)

    # A dialogue that stays open with nothing to press.
    scene = Scene(CAMP)
    spy_on(chat_dialog, 'is_open', returns=True)
    expect(run(tt.drive_strict_dialog([], scene.log))).to_be(False)
    expect(scene.ticks).to_be(140)


test('a goal that never holds, or a stuck dialogue, runs out of steps', driver_is_bounded)


def draining():
    scene = Scene(CAMP)
    expect(run(tt.drain_interaction_dialog([], scene.log))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.drain_interaction_dialog(['Yes'], scene.log))).to_be(False)

    scene = Scene(CAMP)
    expect(run(tt.drain_interaction_dialog([], scene.log, lambda: True))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.drain_interaction_dialog([], scene.log, lambda: False))).to_be(False)

    scene = Scene(CAMP)
    scene.chat.pages = [['Yes']]
    expect(run(tt.drain_interaction_dialog(['Yes'], scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Yes'])


test('with no dialogue, the drain answers by what the leg wanted; with one it drives it', draining)


def small_helpers():
    scene = Scene(CAMP)
    scene.chat.shown = ['the winch turns']
    expect(tt.dialog_matches(tt.any_phrase('WINCH'))).to_be(True)
    expect(tt.dialog_matches(tt.any_phrase('barrel'))).to_be(False)
    expect(tt.talk_action(['Trade', 'Talk-to'])).to_be('Talk-to')
    expect(tt.talk_action(['Trade'])).to_be_null()


test('the phrase test ignores case, and the talk option is found by its prefix', small_helpers)


def walking():
    scene = Scene(CAMP)
    expect(run(tt.walk(CAMP, 1, scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    # The same x and z on another level is no arrival.
    above = Tile(CAMP.x, CAMP.z, 1)
    expect(run(tt.walk(above, 1, scene.log))).to_be(True)
    expect(scene.walks).to_equal([above])


test('a walk is skipped only when already close on the same level', walking)


def talk_strict_paths():
    scene = Scene(CAMP)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA, effect=chats(scene, [['Yes']]))
    expect(run(tt.talk_strict(NPC.IRENA, CAMP, ['Yes'], scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(['Yes'])

    # The dialogue is already up, so no walk and no click.
    scene = Scene(CAMP)
    scene.chat.pages = ['continue']
    expect(run(tt.talk_strict(NPC.IRENA, tt.IRENA, [], scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(CAMP)
    scene.walk_ok = False
    expect(run(tt.talk_strict(NPC.IRENA, tt.IRENA, [], scene.log))).to_be(False)

    scene = Scene(CAMP)
    expect(run(tt.talk_strict([NPC.SLAVE, NPC.ESCAPED_SLAVE], CAMP, [], scene.log))).to_be(False)
    expect(scene.logged(f'no Tourist Trap NPC [{NPC.SLAVE},{NPC.ESCAPED_SLAVE}]')).to_be(True)

    # Someone of that id who cannot be talked to does not count.
    scene = Scene(CAMP)
    scene.npc('Irena', ['Attack'], id=NPC.IRENA)
    expect(run(tt.talk_strict(NPC.IRENA, CAMP, [], scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA, effect=lambda op: False)
    expect(run(tt.talk_strict(NPC.IRENA, CAMP, [], scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA)
    expect(run(tt.talk_strict(NPC.IRENA, CAMP, [], scene.log))).to_be(False)


test('talking walks, clicks and drives, and fails at each of those', talk_strict_paths)


def interact_loc_paths():
    scene = Scene(CAMP)
    scene.loc('Gate', ['Open'], tile=CAMP, id=1, effect=chats(scene, [['Yes']]))
    expect(run(tt.interact_loc([1], 'Open', CAMP, scene.log, ['Yes']))).to_be(True)

    scene = Scene(DESERT)
    scene.walk_ok = False
    expect(run(tt.interact_loc([1], 'Open', CAMP, scene.log))).to_be(False)

    # A goal met during the walk needs no click, even with the loc left behind.
    scene = Scene(CAMP)
    expect(run(tt.interact_loc([1], 'Open', CAMP, scene.log, [], lambda: True))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.interact_loc([1, 2], 'Open', CAMP, scene.log))).to_be(False)
    expect(scene.logged("no Tourist Trap loc [1,2] offering 'Open'")).to_be(True)

    # The right id, but too far from the anchor.
    scene = Scene(CAMP)
    scene.loc('Gate', ['Open'], tile=Tile(CAMP.x + 9, CAMP.z, 0), id=1)
    expect(run(tt.interact_loc([1], 'Open', CAMP, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.loc('Gate', ['Open'], tile=CAMP, id=1, effect=lambda op: False)
    expect(run(tt.interact_loc([1], 'Open', CAMP, scene.log))).to_be(False)


test('a loc is clicked near its anchor, unless the goal is met or it cannot be', interact_loc_paths)


def use_on_loc_paths():
    scene = Scene(CAMP)
    scene.loc('Cart', tile=CAMP, id=1)
    scene.item(5, 'Barrel')
    expect(run(tt.use_item_on_loc('Barrel', [1], CAMP, scene.log))).to_be(True)

    scene = Scene(DESERT)
    scene.walk_ok = False
    expect(run(tt.use_item_on_loc('Barrel', [1], CAMP, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.loc('Cart', tile=CAMP, id=1)
    expect(run(tt.use_item_on_loc('Barrel', [1], CAMP, scene.log))).to_be(False)
    expect(scene.logged("cannot use 'Barrel'")).to_be(True)

    scene = Scene(CAMP)
    scene.item(5, 'Barrel')
    expect(run(tt.use_item_on_loc('Barrel', [1], CAMP, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.loc('Cart', tile=CAMP, id=1)
    scene.item(5, 'Barrel', on_use=lambda target: False)
    expect(run(tt.use_item_on_loc('Barrel', [1], CAMP, scene.log))).to_be(False)


test('an item is used on a loc only with both at hand', use_on_loc_paths)


def use_on_npc_paths():
    scene = Scene(CAMP)
    scene.npc('Ana', id=NPC.ANA)
    scene.item(5, 'Barrel')
    expect(run(tt.use_item_on_npc('Barrel', NPC.ANA, CAMP, scene.log))).to_be(True)

    scene = Scene(DESERT)
    scene.walk_ok = False
    expect(run(tt.use_item_on_npc('Barrel', NPC.ANA, CAMP, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.item(5, 'Barrel')
    expect(run(tt.use_item_on_npc('Barrel', NPC.ANA, CAMP, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.npc('Ana', id=NPC.ANA)
    scene.item(5, 'Barrel', on_use=lambda target: False)
    expect(run(tt.use_item_on_npc('Barrel', NPC.ANA, CAMP, scene.log))).to_be(False)


test('an item is used on an NPC only with both at hand', use_on_npc_paths)


# What's worn.

def equipment_rules():
    scene = Scene(CAMP)
    for name in tt.DESERT_OUTFIT:
        scene.item(1, name)
    scene.item(2, ITEM.PICKAXE)
    scene.wear('Rune platebody')
    expect(run(tt.wear_desert_loadout(scene.log))).to_be(True)
    expect([i.name for i in scene.worn]).to_equal(list(tt.DESERT_OUTFIT) + [ITEM.PICKAXE])

    scene = Scene(CAMP)
    expect(run(tt.wear_slave_loadout(scene.log))).to_be(False)
    expect(scene.logged(f"could not equip required Tourist Trap item '{ITEM.SLAVE_SHIRT}'")).to_be(True)

    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.wear(ITEM.PICKAXE)
    expect(run(tt.wear_slave_disguise_only(scene.log))).to_be(True)
    expect(scene.worn).to_have_length(4)

    scene = Scene(CAMP)
    dress(scene, tt.DESERT_OUTFIT)
    expect(run(tt.wear_desert_outfit_for_space(scene.log))).to_be(True)


test('the required clothes go on, and anything the camp forbids comes off', equipment_rules)


def stuck_gear():
    def stuck(name):
        return False
        yield

    scene = Scene(CAMP)
    scene.wear('Rune platebody')
    spy_on(equipment, 'unequip', impl=stuck)
    expect(run(tt.ensure_equipment([], [], scene.log))).to_be(False)
    expect(scene.logged("could not safely remove 'Rune platebody'")).to_be(True)


test('forbidden gear that will not come off stops the leg', stuck_gear)


def combat_waits():
    scene = Scene(CAMP)
    expect(run(tt.wait_out_combat(1000))).to_be(True)

    scene = Scene(CAMP)
    scene.fighting = True
    expect(run(tt.wait_out_combat(1200))).to_be(False)
    expect(scene.ticks).to_be(2)

    scene = Scene(CAMP)
    scene.fighting = True
    event_signal.set_interrupt(lambda: True)
    expect(run(tt.wait_out_combat(1200))).to_be(False)
    expect(scene.ticks).to_be(0)


test('combat is waited out up to a deadline, or until a runtime event', combat_waits)


# The pass, Irena and the captain.

def shantay_south():
    scene = Scene(tt.SHANTAY_NORTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS, effect=answered_moves_to(scene, tt.SHANTAY_SOUTH_APPROACH, "Yeah, that poster doesn't scare me!"))
    expect(run(tt.cross_shantay_pass(scene.log))).to_be(True)

    scene = Scene(tt.SHANTAY_NORTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS, effect=chats(scene, [["Yeah, that poster doesn't scare me!"]]))
    expect(run(tt.cross_shantay_pass(scene.log))).to_be(False)
    expect(scene.chat.chosen).to_have_length(1)

    scene = Scene(CAMP)
    scene.walk_ok = False
    expect(run(tt.cross_shantay_pass(scene.log))).to_be(False)

    scene = Scene(tt.SHANTAY_NORTH_APPROACH)
    expect(run(tt.cross_shantay_pass(scene.log))).to_be(False)

    scene = Scene(tt.SHANTAY_NORTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS, effect=chats(scene, [['Unknown']]))
    expect(run(tt.cross_shantay_pass(scene.log))).to_be(False)


test('crossing south answers the warning and proves it by the tile', shantay_south)


def shantay_north():
    scene = Scene(tt.SHANTAY_SOUTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS, effect=moves_to(scene, tt.SHANTAY_NORTH_APPROACH))
    expect(run(tt.cross_shantay_pass_north(scene.log))).to_be(True)

    scene = Scene(DESERT)
    scene.walk_ok = False
    expect(run(tt.cross_shantay_pass_north(scene.log))).to_be(False)

    scene = Scene(tt.SHANTAY_SOUTH_APPROACH)
    expect(run(tt.cross_shantay_pass_north(scene.log))).to_be(False)

    scene = Scene(tt.SHANTAY_SOUTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS, effect=chats(scene, [['Unknown']]))
    expect(run(tt.cross_shantay_pass_north(scene.log))).to_be(False)

    # The click lands and the player stays south.
    scene = Scene(tt.SHANTAY_SOUTH_APPROACH)
    scene.loc('Shantay pass', ['Go-through'], tile=tt.SHANTAY_PASS, id=LOC.SHANTAY_PASS)
    expect(run(tt.cross_shantay_pass_north(scene.log))).to_be(False)


test('crossing north needs the pass loc and an arrival', shantay_north)


def irena_starts():
    scene = Scene(tt.IRENA)
    scene.npc('Irena', ['Talk-to'], id=NPC.IRENA, effect=chats(scene, [[tt.IRENA_START[0]], [tt.IRENA_START[2]]]))
    expect(run(tt.start_with_irena(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal([tt.IRENA_START[0], tt.IRENA_START[2]])


test('Irena starts the quest with her exact options', irena_starts)


def captain_scene():
    scene = Scene(tt.CAPTAIN)

    def duel(op):
        scene.fighting = True
        scene.later(lambda: None)

    scene.npc('Captain', ['Talk-to'], id=NPC.CAPTAIN, effect=duel)
    return scene


def captain_paths():
    # Already fighting, so no provocation; the fight ends and the key drops.
    scene = Scene(tt.CAPTAIN)
    scene.fighting = True

    def ends():
        scene.fighting = False
        scene.item(1, ITEM.METAL_KEY)

    scene.later(lambda: None)
    scene.later(ends)
    expect(run(tt.provoke_and_defeat_captain(scene.log))).to_be(True)
    expect(scene.talks).to_have_length(0)

    # The taunt starts the duel, which runs past the wait.
    scene = captain_scene()
    expect(run(tt.provoke_and_defeat_captain(scene.log))).to_be(False)

    scene = Scene(tt.CAPTAIN)
    expect(run(tt.provoke_and_defeat_captain(scene.log))).to_be(False)

    # The taunt goes through and no duel comes.
    scene = Scene(tt.CAPTAIN)
    scene.npc('Captain', ['Talk-to'], id=NPC.CAPTAIN, effect=chats(scene, [[tt.CAPTAIN_DUEL[0]]]))
    expect(run(tt.provoke_and_defeat_captain(scene.log))).to_be(False)
    expect(scene.logged('did not enter the guaranteed duel')).to_be(True)


test('the captain is provoked unless already fighting, and his key proves the win', captain_paths)


# The camp.

def camp_gate():
    scene = Scene(DESERT)
    scene.loc('Gate', ['Open'], tile=tt.CAMP_GATE, id=LOC.CAMP_GATE[0], effect=moves_to(scene, CAMP))
    expect(run(tt.enter_camp(scene.log))).to_be(True)

    scene = Scene(DESERT)
    scene.walk_ok = False
    expect(run(tt.enter_camp(scene.log))).to_be(False)

    # Refused at the gate, still out in the sand.
    scene = Scene(tt.CAMP_GATE)
    scene.loc('Gate', ['Open'], tile=tt.CAMP_GATE, id=LOC.CAMP_GATE[0], effect=moves_to(scene, DESERT))
    expect(run(tt.enter_camp(scene.log))).to_be(False)


test('entering the camp is proved by the area', camp_gate)


def leaving_camp():
    scene = Scene(CAMP)
    for name in tt.DESERT_OUTFIT:
        scene.item(1, name)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.loc('Gate', ['Open'], tile=tt.CAMP_GATE, id=LOC.CAMP_GATE[0], effect=moves_to(scene, DESERT))
    expect(run(tt.leave_camp(scene.log))).to_be(True)
    expect([i.name for i in scene.worn]).to_equal(tt.DESERT_OUTFIT)

    # No desert clothes left: the slave disguise comes off and the gate still opens.
    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.loc('Gate', ['Open'], tile=tt.CAMP_GATE, id=LOC.CAMP_GATE[0], effect=moves_to(scene, DESERT))
    expect(run(tt.leave_camp(scene.log))).to_be(True)
    expect(scene.worn).to_have_length(0)

    # No way to the gate.
    scene = Scene(CAMP)
    scene.walk_ok = False
    expect(run(tt.leave_camp(scene.log))).to_be(False)

    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    spy_on(equipment, 'unequip', impl=lambda name: run_nothing(False))
    expect(run(tt.leave_camp(scene.log))).to_be(False)


def run_nothing(value):
    return value
    yield


test('the gate is left in desert clothes, or at least out of slave clothes', leaving_camp)


def ladder():
    scene = Scene(CAMP)
    scene.loc('Ladder', ['Climb-up'], tile=tt.CAMP_LADDER, id=LOC.LADDER_UP, effect=moves_to(scene, UPPER))
    expect(run(tt.climb_camp_ladder(True, scene.log))).to_be(True)

    scene = Scene(UPPER)
    above = Tile(tt.CAMP_LADDER.x, tt.CAMP_LADDER.z, 1)
    scene.loc('Ladder', ['Climb-down'], tile=above, id=LOC.LADDER_DOWN, effect=moves_to(scene, CAMP))
    expect(run(tt.climb_camp_ladder(False, scene.log))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.climb_camp_ladder(True, scene.log))).to_be(False)

    scene = Scene(CAMP)
    scene.loc('Ladder', ['Climb-up'], tile=tt.CAMP_LADDER, id=LOC.LADDER_UP)
    expect(run(tt.climb_camp_ladder(True, scene.log))).to_be(False)


test('the ladder is proved by the level it reaches', ladder)


def slave_trades():
    scene = Scene(tt.SLAVE)
    scene.npc('Slave', ['Talk-to'], id=NPC.ESCAPED_SLAVE, effect=chats(scene, [[tt.SLAVE_TRADE[1]]]))
    expect(run(tt.slave_unlock_and_trade(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal([tt.SLAVE_TRADE[1]])


test('the slave is unlocked and traded with in one interaction', slave_trades)


def lost_outfit_scene():
    scene = Scene(tt.SLAVE)
    dress(scene, tt.DESERT_OUTFIT)
    scene.wear(ITEM.PICKAXE)
    return scene


def replacing_the_outfit():
    scene = Scene(tt.SLAVE)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = lost_outfit_scene()

    def trade(text):
        for name in tt.SLAVE_OUTFIT:
            scene.item(1, name)

    scene.chat.on_choose = trade
    scene.npc('Slave', ['Talk-to'], tile=tt.SLAVE, id=NPC.SLAVE, effect=chats(scene, [["Yes, I'll trade."]]))
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(True)
    expect(scene.logged('received the complete shirt, robe, and boots')).to_be(True)
    expect(scene.logged(f'missing={ITEM.SLAVE_SHIRT}|{ITEM.SLAVE_ROBE}|{ITEM.SLAVE_BOOTS}')).to_be(True)


test('a lost slave outfit is traded back from the slave', replacing_the_outfit)


def replacing_the_outfit_fails():
    # Cannot dress for the walk there.
    scene = Scene(tt.SLAVE)
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)

    scene = lost_outfit_scene()
    scene.at = CAMP
    scene.walk_ok = False
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)

    scene = lost_outfit_scene()
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)
    expect(scene.logged('no male slave 825/826')).to_be(True)

    scene = lost_outfit_scene()
    scene.npc('Slave', ['Talk-to'], tile=tt.SLAVE, id=NPC.SLAVE, effect=lambda op: False)
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)

    scene = lost_outfit_scene()
    scene.npc('Slave', ['Talk-to'], tile=tt.SLAVE, id=NPC.SLAVE)
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)
    expect(scene.logged('male-slave dialogue did not open')).to_be(True)

    scene = lost_outfit_scene()
    scene.npc('Slave', ['Talk-to'], tile=tt.SLAVE, id=NPC.SLAVE, effect=chats(scene, [['Unknown']]))
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)

    scene = lost_outfit_scene()
    scene.npc('Slave', ['Talk-to'], tile=tt.SLAVE, id=NPC.SLAVE, effect=chats(scene, ['continue']))
    expect(run(tt.replace_lost_slave_outfit(scene.log))).to_be(False)
    expect(scene.logged('dialogue ended without a complete outfit')).to_be(True)


test('replacing the outfit fails at each of its steps', replacing_the_outfit_fails)


# The mine.

def entering_mine():
    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.loc('Door', ['Open'], tile=tt.MINE_ENTRANCE, id=LOC.SURFACE_MINE_DOOR[0], effect=moves_to(scene, MINE_IN))
    expect(run(tt.enter_mine(scene.log))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.enter_mine(scene.log))).to_be(False)

    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.enter_mine(scene.log))).to_be(False)

    scene = Scene(CAMP)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.loc('Door', ['Open'], tile=tt.MINE_ENTRANCE, id=LOC.SURFACE_MINE_DOOR[0])
    expect(run(tt.enter_mine(scene.log))).to_be(False)


test('the mine needs the disguise and an arrival', entering_mine)


def exit_door(scene, effect):
    scene.loc('Door', ['Open'], tile=tt.MINE_EXIT_DOOR, id=LOC.UNDERGROUND_MINE_DOOR[0], effect=effect)


def leaving_mine():
    scene = Scene(MINE_IN)
    dress(scene, tt.SLAVE_OUTFIT)
    exit_door(scene, moves_to(scene, CAMP))
    expect(run(tt.leave_mine(scene.log))).to_be(True)

    # From the lower mine, by the cave first.
    scene = Scene(LOWER)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.loc('Cave', ['Walk through'], tile=tt.CAVE_INNER_LANDING, id=LOC.MINE_CAVE[0], effect=moves_to(scene, tt.CAVE_OUTER_LANDING))
    exit_door(scene, moves_to(scene, CAMP))
    expect(run(tt.leave_mine(scene.log))).to_be(True)


test('the mine is left by its door, crossing the cave from the lower mine', leaving_mine)


def leaving_mine_fails():
    scene = Scene(MINE_IN)
    expect(run(tt.leave_mine(scene.log))).to_be(False)

    # The cave will not take the player.
    scene = Scene(LOWER)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.leave_mine(scene.log))).to_be(False)

    scene = Scene(DEEP)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.leave_mine(scene.log))).to_be(False)

    scene = Scene(MINE_IN)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.walk_ok = False
    expect(run(tt.leave_mine(scene.log))).to_be(False)
    expect(scene.logged('could not reach the inside stand')).to_be(True)

    scene = Scene(MINE_IN)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.leave_mine(scene.log))).to_be(False)
    expect(scene.logged('did not expose its Open action')).to_be(True)

    scene = Scene(MINE_IN)
    dress(scene, tt.SLAVE_OUTFIT)
    exit_door(scene, lambda op: False)
    expect(run(tt.leave_mine(scene.log))).to_be(False)

    scene = Scene(MINE_IN)
    dress(scene, tt.SLAVE_OUTFIT)
    exit_door(scene, None)
    expect(run(tt.leave_mine(scene.log))).to_be(False)


test('leaving the mine fails at each of its steps', leaving_mine_fails)


def cave_guard_paths():
    post = Tile(3280, 9418, 0)
    scene = Scene(tt.CAVE_GUARD)
    scene.npc('Guard', ['Talk-to'], tile=post, id=828, effect=chats(scene, [[tt.CAVE_GUARD_DIALOG[0]]]))
    expect(run(tt.ask_cave_guard(scene.log))).to_be(True)

    # No guard at his post: walk there and let the next pass ask.
    scene = Scene(LOWER)
    expect(run(tt.ask_cave_guard(scene.log))).to_be(False)
    expect(scene.walks).to_equal([tt.CAVE_GUARD])

    scene = Scene(LOWER)
    scene.walk_ok = False
    expect(run(tt.ask_cave_guard(scene.log))).to_be(False)

    # A guard off his post is not the cave's.
    scene = Scene(LOWER)
    scene.npc('Guard', ['Talk-to'], tile=LOWER, id=828)
    expect(run(tt.ask_cave_guard(scene.log))).to_be(False)
    expect(scene.walks).to_equal([tt.CAVE_GUARD])

    scene = Scene(tt.CAVE_GUARD)
    scene.npc('Guard', ['Talk-to'], tile=post, id=829, effect=lambda op: False)
    expect(run(tt.ask_cave_guard(scene.log))).to_be(False)

    scene = Scene(tt.CAVE_GUARD)
    scene.npc('Guard', ['Talk-to'], tile=post, id=829)
    expect(run(tt.ask_cave_guard(scene.log))).to_be(False)


test('the cave guard is asked at his post', cave_guard_paths)


def pineapple_paths():
    post = Tile(3280, 9418, 0)
    scene = Scene(tt.CAVE_GUARD)
    scene.npc('Guard', tile=post, id=828)
    scene.item(1, ITEM.PINEAPPLE)
    expect(run(tt.give_pineapple(scene.log))).to_be(True)

    scene = Scene(LOWER)
    scene.walk_ok = False
    expect(run(tt.give_pineapple(scene.log))).to_be(False)

    scene = Scene(tt.CAVE_GUARD)
    scene.item(1, ITEM.PINEAPPLE)
    expect(run(tt.give_pineapple(scene.log))).to_be(False)


test('the pineapple goes to the guard', pineapple_paths)


def cave_scene(start, effect=None):
    scene = Scene(start)
    scene.loc('Cave', ['Walk through'], tile=start, id=LOC.MINE_CAVE[0], effect=effect)
    return scene


def crossing_cave():
    scene = Scene(tt.CAVE_OUTER_LANDING)
    scene.loc('Cave', ['Walk through'], tile=tt.CAVE_OUTER_LANDING, id=LOC.MINE_CAVE[0], effect=moves_to(scene, tt.CAVE_INNER_LANDING))
    expect(run(tt.cross_mine_cave(True, scene.log))).to_be(True)

    # Two tries fail on the way, and the third lands.
    scene = Scene(tt.CAVE_INNER_LANDING)
    tries = []

    def third(op):
        tries.append(op)
        if len(tries) == 3:
            scene.at = tt.CAVE_OUTER_LANDING

    scene.loc('Cave', ['Walk through'], tile=tt.CAVE_INNER_LANDING, id=LOC.MINE_CAVE[0], effect=third)
    expect(run(tt.cross_mine_cave(False, scene.log))).to_be(True)
    expect(scene.logged('attempt 2/3 was interrupted')).to_be(True)

    scene = cave_scene(tt.CAVE_OUTER_LANDING)
    expect(run(tt.cross_mine_cave(True, scene.log))).to_be(False)
    expect(scene.logged('after 3 attempts')).to_be(True)

    scene = cave_scene(tt.CAVE_OUTER_LANDING)
    event_signal.set_interrupt(lambda: True)
    expect(run(tt.cross_mine_cave(True, scene.log))).to_be(False)
    expect(scene.lines).to_have_length(0)


test('the cave is proved by its exact landing, over up to three tries', crossing_cave)


# The surface jail.

def window(scene, effect=None):
    scene.loc('Window', ['Search'], tile=tt.CELL_WINDOW, id=LOC.WINDOW, effect=effect)


def cell_window():
    scene = Scene(CELL)
    window(scene, chats(scene, [["Yes, I'll bend the bar."]]))
    expect(run(tt.search_cell_window(scene.log))).to_be(True)

    scene = Scene(CELL)
    expect(run(tt.search_cell_window(scene.log))).to_be(False)
    expect(scene.logged('no cell window')).to_be(True)

    # The outer window, a tile west, can't be reached from the cell.
    scene = Scene(CELL)
    scene.loc('Window', ['Search'], tile=Tile(tt.CELL_WINDOW.x - 1, tt.CELL_WINDOW.z, 0), id=LOC.WINDOW)
    expect(run(tt.search_cell_window(scene.log))).to_be(False)

    scene = Scene(CELL)
    window(scene, lambda op: False)
    expect(run(tt.search_cell_window(scene.log))).to_be(False)


test('only the inside window, with its bar, gets the player out', cell_window)


def rock_climb(scene):
    """The four rocks from the cell's outside to the desert, each a step west."""
    path = [Tile(3282, 3037, 0), Tile(3279, 3038, 0), Tile(3277, 3039, 0), Tile(3273, 3040, 0)]

    def step(op):
        scene.at = path.pop(0)

    scene.loc('Rock', ['Climb-to'], tile=Tile(3282, 3037, 0), id=2694, effect=lambda op: step_and_ask(scene, step))
    scene.loc('Rock', ['Climb-to'], tile=Tile(3279, 3038, 0), id=2695, effect=step)
    scene.loc('Rock', ['Climb-to'], tile=Tile(3277, 3039, 0), id=2696, effect=step)
    scene.loc('Rock', ['Climb down'], tile=Tile(3273, 3040, 0), id=2697, effect=step)


def step_and_ask(scene, step):
    scene.chat.pages = [["Yes, I'll give it a try."]]
    step('Climb-to')


def outdoor_rocks():
    scene = Scene(Tile(3283, 3032, 0))
    rock_climb(scene)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(True)
    expect(scene.at.x).to_be_less_than(3274)
    expect(scene.chat.chosen).to_equal(["Yes, I'll give it a try."])


test('the rocks west of the window lead to the desert, each only westward', outdoor_rocks)


def cell_then_rocks():
    scene = Scene(CELL)
    window(scene, answered_moves_to(scene, Tile(3283, 3032, 0), "Yes, I'll bend the bar."))
    rock_climb(scene)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(True)


test('in the cell the window comes first', cell_then_rocks)


def jail_failures():
    scene = Scene(CELL)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)

    scene = Scene(Tile(3283, 3032, 0))
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)
    expect(scene.logged('no next outbound surface-jail rock')).to_be(True)

    scene = Scene(Tile(3283, 3032, 0))
    scene.loc('Rock', ['Climb-to'], tile=Tile(3282, 3037, 0), id=2695, effect=lambda op: False)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)

    # A rock whose question has no known answer.
    scene = Scene(Tile(3283, 3032, 0))
    scene.loc('Rock', ['Climb-to'], tile=Tile(3282, 3037, 0), id=2695, effect=chats(scene, [['Unknown']]))
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)

    scene = Scene(Tile(3283, 3032, 0))
    scene.loc('Rock', ['Climb down'], tile=Tile(3273, 3040, 0), id=2697, effect=chats(scene, [['Unknown']]))
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)

    # No tile at all, as during a region change.
    scene = Scene(None)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)

    # A rock that keeps taking the click and never moves the player.
    scene = Scene(Tile(3283, 3032, 0))
    scene.loc('Rock', ['Climb-to'], tile=Tile(3282, 3037, 0), id=2695)
    expect(run(tt.escape_surface_jail(scene.log))).to_be(False)


test('the climb fails on a refused rock, an unknown question, or no way on', jail_failures)


# The punishment mine.

def fill_pack(scene, count, name='Junk', id=999):
    for n in range(count):
        scene.item(id, name)


def droppable(scene, id, name):
    scene.item(id, name, actions=['Drop'], effect=lambda op: scene.take(id))


def junk_dropping():
    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 27)
    droppable(scene, 1, ITEM.KEBAB)
    expect(run(tt.drop_punishment_junk_until(1, scene.log))).to_be(True)
    expect(scene.has(1)).to_be(False)

    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 28)
    expect(run(tt.drop_punishment_junk_until(1, scene.log))).to_be(False)
    expect(scene.logged('cannot safely free 1')).to_be(True)

    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 27)
    scene.item(1, ITEM.KEBAB, effect=lambda op: False)
    expect(run(tt.drop_punishment_junk_until(1, scene.log))).to_be(False)

    # The click lands and the item stays.
    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 27)
    scene.item(1, ITEM.KEBAB)
    expect(run(tt.drop_punishment_junk_until(1, scene.log))).to_be(False)


test('only the listed junk is dropped, in its order', junk_dropping)


def rock_counting():
    scene = Scene(tt.UNDERGROUND_JAIL)
    scene.item(tt.PUNISHMENT_ROCK_ID, 'Rock', count=4)
    scene.item(968, 'Rock', count=9)
    expect(tt.punishment_rock_count()).to_be(4)


test('only punishment rocks count, not common rock of the same name', rock_counting)


def rowdy_scene():
    scene = Scene(tt.ROWDY_SLAVE)
    spy_on(game, 'set_combat_style', returns=True)
    return scene


def rowdy_drops(scene, name_index):
    def effect(op):
        scene.fighting = False
        scene.on_ground(tt.SLAVE_OUTFIT_DROP_IDS[name_index], tt.SLAVE_OUTFIT[name_index])
    return effect


def rowdy_recovery():
    scene = rowdy_scene()
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(True)
    expect(scene.lines).to_have_length(0)

    # The shirt is worn and comes off for his death script; the robe and boots drop.
    scene = rowdy_scene()
    scene.wear(ITEM.SLAVE_SHIRT)
    scene.npc('Rowdy slave', ['Attack'], tile=tt.ROWDY_SLAVE, id=NPC.ROWDY_SLAVE, effect=rowdy_drops(scene, 1))
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)
    expect(scene.worn).to_have_length(0)
    expect(scene.has(tt.SLAVE_OUTFIT_DROP_IDS[1])).to_be(True)
    expect(scene.logged(f"defeating the Rowdy slave for '{ITEM.SLAVE_ROBE}'")).to_be(True)
    expect(scene.logged(f"did not produce '{ITEM.SLAVE_BOOTS}'")).to_be(True)

    # All three pieces lie on the ground from earlier kills.
    scene = rowdy_scene()
    for n in range(3):
        scene.on_ground(tt.SLAVE_OUTFIT_DROP_IDS[n], tt.SLAVE_OUTFIT[n])
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(True)
    expect(tt.live_has_slave_outfit()).to_be(True)


test('the outfit is beaten out of the Rowdy slave a piece at a time', rowdy_recovery)


def rowdy_failures():
    scene = rowdy_scene()
    fill_pack(scene, 28)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)
    expect(scene.logged('cannot safely free')).to_be(True)

    scene = rowdy_scene()
    scene.wear(ITEM.SLAVE_SHIRT)

    def stuck(name):
        return False
        yield

    spy_on(equipment, 'unequip', impl=stuck)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)
    expect(scene.logged('could not move')).to_be(True)

    scene = rowdy_scene()
    scene.on_ground(tt.SLAVE_OUTFIT_DROP_IDS[0], ITEM.SLAVE_SHIRT, effect=lambda op: False)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)

    # Take goes through and nothing arrives.
    scene = rowdy_scene()
    scene.on_ground(tt.SLAVE_OUTFIT_DROP_IDS[0], ITEM.SLAVE_SHIRT, effect=lambda op: True)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)

    scene = rowdy_scene()
    scene.at = LOWER
    scene.walk_ok = False
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)

    scene = rowdy_scene()
    scene.npc('Rowdy slave', ['Attack'], tile=tt.ROWDY_SLAVE, id=NPC.ROWDY_SLAVE, effect=lambda op: False)
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)

    # Fighting already, for as long as the wait lasts, and no Rowdy slave free.
    scene = rowdy_scene()
    scene.fighting = True
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)
    expect(scene.logged(f"did not produce '{ITEM.SLAVE_SHIRT}'")).to_be(True)

    # Someone else is fighting him.
    scene = rowdy_scene()
    scene.npc('Rowdy slave', ['Attack'], tile=tt.ROWDY_SLAVE, id=NPC.ROWDY_SLAVE, others=True, effect=lambda op: expect(op).to_be('never'))
    expect(run(tt.recover_slave_outfit_from_rowdy(scene.log))).to_be(False)


test('recovering from the Rowdy slave fails at each of its steps', rowdy_failures)


def rock_slots():
    # A pickaxe held but not worn goes on.
    scene = Scene(tt.UNDERGROUND_JAIL)
    scene.item(1, ITEM.PICKAXE)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(True)
    expect(scene.worn).to_have_length(1)

    # None held: take the spawn.
    scene = Scene(tt.UNDERGROUND_JAIL)
    scene.on_ground(2, ITEM.PICKAXE)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(True)
    expect(scene.worn[0].name).to_be(ITEM.PICKAXE)

    # A full pack loses its kebabs for the spawn, then the hammer for the rocks.
    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 13)
    for n in range(14):
        droppable(scene, 1, ITEM.KEBAB)
    droppable(scene, 3, ITEM.HAMMER)
    scene.on_ground(2, ITEM.PICKAXE)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(True)
    expect(scene.has(1)).to_be(False)
    expect(scene.has(3)).to_be(False)


test('the punishment mine wants a wielded pickaxe and room for its rocks', rock_slots)


def rock_slot_failures():
    scene = Scene(tt.UNDERGROUND_JAIL)
    fill_pack(scene, 28)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(False)

    scene = Scene(tt.UNDERGROUND_JAIL)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(False)
    expect(scene.logged('no Bronze pickaxe held or available')).to_be(True)

    scene = Scene(tt.UNDERGROUND_JAIL)
    scene.on_ground(2, ITEM.PICKAXE, effect=lambda op: True)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(False)

    def stuck(name):
        return False
        yield

    scene = Scene(tt.UNDERGROUND_JAIL)
    scene.item(1, ITEM.PICKAXE)
    spy_on(equipment, 'equip', impl=stuck)
    expect(run(tt.free_punishment_rock_slots(scene.log))).to_be(False)
    expect(scene.logged('could not wield')).to_be(True)


test('the punishment mine fails with no pickaxe or none that wields', rock_slot_failures)


def jail_scene(rocks=0):
    scene = Scene(tt.UNDERGROUND_JAIL)
    dress(scene, tt.SLAVE_OUTFIT)
    scene.wear(ITEM.PICKAXE)
    spy_on(reachability, 'can_reach', returns=True)
    if rocks > 0:
        scene.item(tt.PUNISHMENT_ROCK_ID, 'Rock', count=rocks)
    return scene


def mine_one(scene):
    def effect(op):
        scene.item(tt.PUNISHMENT_ROCK_ID, 'Rock')
    return effect


def underground_escape():
    scene = jail_scene(14)
    scene.loc('Rocks', ['Mine'], id=LOC.PUNISHMENT_ROCK, effect=mine_one(scene))
    scene.loc('Gate', ['Open'], id=LOC.PUNISHMENT_GATE[0], effect=moves_to(scene, MINE_IN))
    expect(run(tt.escape_underground_jail(scene.log))).to_be(True)
    expect(tt.punishment_rock_count()).to_be(15)


test('fifteen rocks open the punishment gate', underground_escape)


def underground_waits_for_a_rock():
    scene = jail_scene(14)
    scene.at = Tile(3290, 9450, 0)

    def respawn():
        scene.loc('Rocks', ['Mine'], id=LOC.PUNISHMENT_ROCK, effect=mine_one(scene))

    scene.later(respawn)
    scene.loc('Gate', ['Open'], id=LOC.PUNISHMENT_GATE[0], effect=moves_to(scene, MINE_IN))
    expect(run(tt.escape_underground_jail(scene.log))).to_be(True)
    expect(scene.walks).to_equal([tt.UNDERGROUND_JAIL])


test('with no reachable vein, the player waits at the jail for one to come back', underground_waits_for_a_rock)


def underground_failures():
    # The outfit cannot be recovered.
    scene = Scene(tt.UNDERGROUND_JAIL)
    spy_on(game, 'set_combat_style', returns=True)
    fill_pack(scene, 28)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    # No pickaxe to be had.
    scene = Scene(tt.UNDERGROUND_JAIL)
    dress(scene, tt.SLAVE_OUTFIT)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)
    expect(scene.logged('no Bronze pickaxe')).to_be(True)

    # A vein beyond the gate is never clicked; the walk back fails.
    scene = jail_scene(14)
    spy_on(reachability, 'can_reach', returns=False)
    scene.loc('Rocks', ['Mine'], id=LOC.PUNISHMENT_ROCK, effect=lambda op: expect(op).to_be('never'))
    scene.walk_ok = False
    scene.at = Tile(3290, 9450, 0)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    scene = jail_scene(14)
    scene.loc('Rocks', ['Mine'], id=LOC.PUNISHMENT_ROCK, effect=lambda op: False)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    # The swing never gets a rock.
    scene = jail_scene(14)
    scene.loc('Rocks', ['Mine'], id=LOC.PUNISHMENT_ROCK)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    scene = jail_scene(15)
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    scene = jail_scene(15)
    scene.loc('Gate', ['Open'], id=LOC.PUNISHMENT_GATE[0], effect=chats(scene, [['Unknown']]))
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)

    # The gate takes the click and stays shut.
    scene = jail_scene(15)
    scene.loc('Gate', ['Open'], id=LOC.PUNISHMENT_GATE[0])
    expect(run(tt.escape_underground_jail(scene.log))).to_be(False)


test('the punishment mine fails at each of its steps', underground_failures)


# Al Shabim.

def al_scene(effect=None):
    scene = Scene(tt.AL_SHABIM)
    scene.npc('Al Shabim', ['Talk-to'], tile=tt.AL_SHABIM, id=NPC.AL_SHABIM, effect=effect)
    return scene


def al_gives(scene, name, option):
    def effect(op):
        scene.chat.pages = [[option]]

    def choose(text):
        scene.item(1, name)

    scene.chat.on_choose = choose
    scene.npcs = []
    scene.npc('Al Shabim', ['Talk-to'], tile=tt.AL_SHABIM, id=NPC.AL_SHABIM, effect=effect)


def al_conversations():
    scene = al_scene()
    al_gives(scene, ITEM.BEDABIN_KEY, tt.AL_PINEAPPLE[1])
    expect(run(tt.ask_al_for_pineapple_deal(scene.log))).to_be(True)

    scene = al_scene()
    al_gives(scene, ITEM.BEDABIN_KEY, "I've lost the key!")
    expect(run(tt.ask_al_for_lost_key(scene.log))).to_be(True)

    scene = al_scene()
    al_gives(scene, ITEM.BEDABIN_KEY, "I've lost the key and the plans!")
    expect(run(tt.ask_al_for_lost_key_and_plans(scene.log))).to_be(True)

    scene = al_scene()
    al_gives(scene, ITEM.BEDABIN_KEY, "I've lost the key and the plans!")
    expect(run(tt.ask_al_for_lost_plans_and_tip(scene.log))).to_be(True)

    scene = al_scene()
    al_gives(scene, ITEM.PINEAPPLE, 'I am looking for a pineapple.')
    expect(run(tt.recover_pineapple_from_al(scene.log))).to_be(True)


test('Al Shabim gives each thing for its exact option', al_conversations)


# The plans.

def plans_scene(start=None):
    scene = Scene(start if start is not None else UPPER)
    scene.loc('Bookcase', ['Search'], tile=tt.SIAD_BOOKCASE, id=LOC.BOOKCASE)
    scene.npc('Siad', ['Talk-to'], id=NPC.SIAD, effect=chats(scene, [[tt.SIAD_DISTRACTION[0]]]))
    scene.loc('Chest', ['Open'], tile=tt.SIAD_CHEST, id=LOC.CHEST, effect=lambda op: scene.item(1, ITEM.PLANS) and None)
    return scene


def steals_plans():
    scene = plans_scene()
    expect(run(tt.steal_technical_plans(scene.log))).to_be(True)
    expect(scene.has(1)).to_be(True)
    expect(scene.at).to_equal(Tile(3292, 3034, 1))

    # From the ground floor, by the ladder.
    scene = plans_scene(CAMP)
    scene.loc('Ladder', ['Climb-up'], tile=tt.CAMP_LADDER, id=LOC.LADDER_UP, effect=moves_to(scene, UPPER))
    expect(run(tt.steal_technical_plans(scene.log))).to_be(True)

    scene = Scene(UPPER)
    scene.item(1, ITEM.PLANS)
    expect(run(tt.steal_technical_plans(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('the bookcase, a chat with Siad and the chest give the plans', steals_plans)


def plans_failures():
    scene = plans_scene(CAMP)
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.locs = [l for l in scene.locs if l.id != LOC.BOOKCASE]
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.npcs = []
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.no_walk = [Tile(3292, 3034, 1)]
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.locs = [l for l in scene.locs if l.id != LOC.CHEST]
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.locs = [l for l in scene.locs if l.id != LOC.CHEST]
    scene.loc('Chest', ['Open'], tile=tt.SIAD_CHEST, id=LOC.CHEST, effect=chats(scene, [['Unknown']]))
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)

    scene = plans_scene()
    scene.locs = [l for l in scene.locs if l.id != LOC.CHEST]
    scene.loc('Chest', ['Open'], tile=tt.SIAD_CHEST, id=LOC.CHEST)
    expect(run(tt.steal_technical_plans(scene.log))).to_be(False)


test('stealing the plans fails at each of its steps', plans_failures)


def camp_keys():
    scene = Scene(UPPER)
    scene.loc('Desk', ['Search'], tile=tt.SIAD_DESK, id=LOC.SIAD_DESK, effect=lambda op: scene.item(1, ITEM.METAL_KEY) and None)
    expect(run(tt.recover_mining_camp_keys(scene.log))).to_be(True)

    scene = Scene(UPPER)
    scene.item(1, ITEM.METAL_KEY)
    expect(run(tt.recover_mining_camp_keys(scene.log))).to_be(True)

    scene = Scene(CAMP)
    expect(run(tt.recover_mining_camp_keys(scene.log))).to_be(False)

    scene = Scene(UPPER)
    expect(run(tt.recover_mining_camp_keys(scene.log))).to_be(False)

    scene = Scene(UPPER)
    scene.loc('Desk', ['Search'], tile=tt.SIAD_DESK, id=LOC.SIAD_DESK)
    expect(run(tt.recover_mining_camp_keys(scene.log))).to_be(False)


test("Siad's desk gives back the metal key", camp_keys)


def showing_plans():
    scene = al_scene()
    scene.item(1, ITEM.PLANS, on_use=chats(scene, [[tt.AL_PLANS[0]], [tt.AL_PLANS[1]]]))
    expect(run(tt.show_plans_to_al(scene.log))).to_be(True)
    expect(scene.chat.chosen).to_equal(tt.AL_PLANS)

    scene = al_scene()
    scene.at = DESERT
    scene.walk_ok = False
    expect(run(tt.show_plans_to_al(scene.log))).to_be(False)

    scene = al_scene()
    expect(run(tt.show_plans_to_al(scene.log))).to_be(False)


test('the plans are shown to Al Shabim', showing_plans)


# The prototype.

def tent_scene():
    scene = Scene(BEDABIN)
    scene.item(1, ITEM.PLANS, on_use=moves_to(scene, TENT))
    scene.npc('Bedabin guard', id=NPC.BEDABIN_GUARD)
    return scene


def tent_entry():
    scene = tent_scene()
    expect(run(tt.enter_prototype_tent(scene.log))).to_be(True)

    scene = tent_scene()
    scene.at = DESERT
    scene.walk_ok = False
    expect(run(tt.enter_prototype_tent(scene.log))).to_be(False)
    expect(scene.logged('could not reach the Bedabin')).to_be(True)

    scene = tent_scene()
    scene.npcs = []
    expect(run(tt.enter_prototype_tent(scene.log))).to_be(False)
    expect(scene.logged('could not show the technical plans')).to_be(True)

    scene = Scene(BEDABIN)
    scene.npc('Bedabin guard', id=NPC.BEDABIN_GUARD)
    scene.item(1, ITEM.PLANS, on_use=chats(scene, [['Unknown']]))
    expect(run(tt.enter_prototype_tent(scene.log))).to_be(False)

    scene = Scene(BEDABIN)
    scene.npc('Bedabin guard', id=NPC.BEDABIN_GUARD)
    scene.item(1, ITEM.PLANS)
    expect(run(tt.enter_prototype_tent(scene.log))).to_be(False)


test('showing the guard the plans lets the player into the tent', tent_entry)


def tent_exit():
    scene = Scene(BEDABIN)
    expect(run(tt.exit_prototype_tent(scene.log))).to_be(True)

    scene = Scene(TENT)
    scene.loc('Door', ['Walk-through'], tile=tt.BEDABIN_TENT_APPROACH, id=LOC.BEDABIN_TENT_DOOR, effect=moves_to(scene, BEDABIN))
    expect(run(tt.exit_prototype_tent(scene.log))).to_be(True)

    scene = Scene(TENT)
    expect(run(tt.exit_prototype_tent(scene.log))).to_be(False)

    scene = Scene(TENT)
    scene.loc('Door', ['Walk-through'], tile=tt.BEDABIN_TENT_APPROACH, id=LOC.BEDABIN_TENT_DOOR)
    expect(run(tt.exit_prototype_tent(scene.log))).to_be(False)


test('the tent is left by its door', tent_exit)


def anvil_scene(on_use=None):
    scene = Scene(TENT)
    scene.loc('Anvil', tile=tt.EXPERIMENTAL_ANVIL, id=LOC.ANVIL)
    scene.item(1, ITEM.BAR, on_use=on_use)
    return scene


def forging():
    scene = anvil_scene()
    scene.item(2, ITEM.DART_TIP)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('a held tip needs no forging', forging)


def forge_makes_a_tip():
    scene = Scene(TENT)
    scene.loc('Anvil', tile=tt.EXPERIMENTAL_ANVIL, id=LOC.ANVIL)

    def forge(target):
        scene.chat.pages = [[tt.ANVIL_DIALOG[0]]]

    def choose(text):
        scene.item(2, ITEM.DART_TIP)

    scene.chat.on_choose = choose
    scene.item(1, ITEM.BAR, on_use=forge)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(True)
    expect(scene.has(2)).to_be(True)


test('the anvil dialogue makes the tip', forge_makes_a_tip)


def forge_from_outside():
    scene = tent_scene()
    scene.loc('Anvil', tile=tt.EXPERIMENTAL_ANVIL, id=LOC.ANVIL)

    def forge(target):
        scene.item(2, ITEM.DART_TIP)

    scene.item(3, ITEM.BAR, on_use=forge)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(True)


test('from outside the tent the guard comes first', forge_from_outside)


def forge_wastes_a_bar():
    scene = Scene(TENT)
    scene.loc('Anvil', tile=tt.EXPERIMENTAL_ANVIL, id=LOC.ANVIL)

    def forge(target):
        scene.chat.pages = ['continue']
        scene.say('You waste the bronze bar.')

    scene.item(1, ITEM.BAR, on_use=forge)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)
    expect(scene.logged('bronze bar wasted')).to_be(True)


test('a wasted bar is reported by the message it gets', forge_wastes_a_bar)


def stale_waste_line_is_ignored():
    scene = Scene(TENT)
    scene.say('You waste the bronze bar.')
    mark = game_messages.mark()
    expect(tt.forge_bar_wasted_since(mark)).to_be(False)
    scene.say('An unlucky accident.')
    expect(tt.forge_bar_wasted_since(mark)).to_be(True)


test('an earlier waste line does not count against this bar', stale_waste_line_is_ignored)


def forge_failures():
    scene = tent_scene()
    scene.npcs = []
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)

    scene = anvil_scene()
    scene.at = Tile(3167, 3048, 0)
    scene.walk_ok = False
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)

    # The anvil asks something the driver does not know.
    scene = anvil_scene(lambda target: None)
    scene.pack = []
    scene.item(1, ITEM.BAR, on_use=chats(scene, [['Unknown']]))
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)
    expect(scene.logged('unrecognized options')).to_be(True)

    scene = Scene(TENT)
    scene.loc('Anvil', tile=tt.EXPERIMENTAL_ANVIL, id=LOC.ANVIL)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)

    scene = anvil_scene(lambda target: False)
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)

    # Nothing answers the bar.
    scene = anvil_scene()
    expect(run(tt.forge_prototype_tip(scene.log))).to_be(False)


test('forging fails with no way in, no way to the anvil, no bar, or no answer', forge_failures)


def fletching():
    scene = Scene(TENT)
    scene.item(1, ITEM.DART_TIP)

    def fletch(target):
        scene.item(2, ITEM.DART)

    scene.item(3, ITEM.FEATHER, count=10, on_use=fletch)
    expect(run(tt.fletch_prototype_dart(scene.log))).to_be(True)

    scene = Scene(TENT)
    scene.item(1, ITEM.DART_TIP)
    scene.item(3, ITEM.FEATHER, count=9)
    expect(run(tt.fletch_prototype_dart(scene.log))).to_be(False)

    scene = Scene(TENT)
    scene.item(1, ITEM.DART_TIP)
    scene.item(3, ITEM.FEATHER, count=10, on_use=lambda target: False)
    expect(run(tt.fletch_prototype_dart(scene.log))).to_be(False)

    scene = Scene(TENT)
    scene.item(1, ITEM.DART_TIP)
    scene.item(3, ITEM.FEATHER, count=10, on_use=chats(scene, [['Unknown']]))
    expect(run(tt.fletch_prototype_dart(scene.log))).to_be(False)

    # The feathers are eaten and no dart comes.
    scene = Scene(TENT)
    scene.item(1, ITEM.DART_TIP)
    scene.item(3, ITEM.FEATHER, count=10)
    expect(run(tt.fletch_prototype_dart(scene.log))).to_be(False)


test('only the dart itself proves the fletching', fletching)


def giving_the_dart():
    scene = al_scene()

    def give(target):
        scene.item(9, ITEM.PINEAPPLE)

    scene.item(1, ITEM.DART, on_use=give)
    expect(run(tt.give_prototype_to_al(scene.log))).to_be(True)

    scene = Scene(TENT)
    expect(run(tt.give_prototype_to_al(scene.log))).to_be(False)

    scene = al_scene()
    scene.at = DESERT
    scene.walk_ok = False
    expect(run(tt.give_prototype_to_al(scene.log))).to_be(False)

    scene = al_scene()
    expect(run(tt.give_prototype_to_al(scene.log))).to_be(False)

    scene = al_scene()
    scene.item(1, ITEM.DART)
    expect(run(tt.give_prototype_to_al(scene.log))).to_be(False)


test('the dart earns the pineapple', giving_the_dart)


# Back through the mine, for a lost disguise.

def deep_return():
    scene = Scene(DEEP)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))
    expect(run(tt.return_from_deep_mine(scene.log))).to_be(True)

    scene = Scene(DEEP)
    expect(run(tt.return_from_deep_mine(scene.log))).to_be(False)

    scene = Scene(DEEP)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART)
    expect(run(tt.return_from_deep_mine(scene.log))).to_be(False)


test('the deep cart rides back to the lower mine', deep_return)


def punishment_return_scene(area, with_ana=False, ana_on_use=None):
    scene = Scene(area)
    if with_ana:
        scene.item(7, ITEM.ANA_BARREL, on_use=ana_on_use)
    return scene


def cave_captures(scene, anchor):
    scene.loc('Cave', ['Walk through'], tile=anchor, id=LOC.MINE_CAVE[0], effect=moves_to(scene, tt.UNDERGROUND_JAIL))


def sends_ana(scene):
    def effect(target):
        scene.take(7)
    return effect


def lifts_ana(scene):
    def effect(target):
        scene.take(7)
        scene.chat.pages = [[tt.LIFT_GUARD_DIALOG[0]]]
    return effect


def punishment_returns():
    # From the entrance: straight to the cave.
    scene = punishment_return_scene(MINE_IN)
    cave_captures(scene, Tile(3281, 9415, 0))
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(True)

    # From the lower mine with Ana: she goes on the lift first.
    scene = punishment_return_scene(LOWER)
    scene.item(7, ITEM.ANA_BARREL, on_use=lifts_ana(scene))
    scene.loc('Bucket', tile=tt.LIFT_BUCKET, id=LOC.LIFT_BUCKET)
    cave_captures(scene, Tile(3286, 9415, 0))
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(True)
    expect(scene.has(7)).to_be(False)

    # From the deep mine with Ana: she goes down the cart, then the player follows.
    scene = punishment_return_scene(DEEP)
    scene.item(7, ITEM.ANA_BARREL, on_use=sends_ana(scene))
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART, effect=answered_moves_to(scene, LOWER, 'Yes, of course.'))
    cave_captures(scene, Tile(3286, 9415, 0))
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(True)
    expect(scene.has(7)).to_be(False)


test('the walk to capture sends Ana ahead so the guards do not take her', punishment_returns)


def punishment_return_failures():
    scene = Scene(CAMP)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # Ana will not go on the cart.
    scene = punishment_return_scene(DEEP, True)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # The cart takes her, but she stays in the pack.
    scene = punishment_return_scene(DEEP, True)
    scene.loc('Cart', ['Search'], tile=DEEP, id=LOC.MINE_CART)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # She went down, and the cart never moves the player.
    scene = punishment_return_scene(DEEP)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    scene = punishment_return_scene(LOWER, True)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    scene = punishment_return_scene(LOWER, True)
    scene.loc('Bucket', tile=tt.LIFT_BUCKET, id=LOC.LIFT_BUCKET)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # The guard answers, and she stays in the pack.
    scene = punishment_return_scene(LOWER)
    scene.loc('Bucket', tile=tt.LIFT_BUCKET, id=LOC.LIFT_BUCKET)
    scene.item(7, ITEM.ANA_BARREL, on_use=chats(scene, [[tt.LIFT_GUARD_DIALOG[0]]]))
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # No cave to walk through.
    scene = punishment_return_scene(MINE_IN)
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)

    # The guards let the player through.
    scene = punishment_return_scene(MINE_IN)
    scene.loc('Cave', ['Walk through'], tile=Tile(3281, 9415, 0), id=LOC.MINE_CAVE[0])
    expect(run(tt.return_to_punishment_mine_for_outfit(scene.log))).to_be(False)


test('the walk to capture fails at each of its steps', punishment_return_failures)

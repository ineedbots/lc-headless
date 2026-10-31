"""Death Plateau's legs against spied facades: Harold's room and dice, Burthorpe's stairs, Saba's cave, Tenzing's
door, the IOU, the stone balls and the certificates, each through its success and its failures."""

import _core
import rs2004.quests.defs.deathplateau as dp
import rs2004.quests.defs.deathplateau.harold as harold
import rs2004.quests.defs.deathplateau.nav as nav
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import ModalButton, game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.deathplateau import read_iou
from rs2004.quests.defs.deathplateau.areas import DEATH_DICE_MAIN, DEATH_ITEM, DENULTH_FINISH, PEDESTALS, TILE
from rs2004.traversal import traversal

HAROLD_ROOM = Tile(2905, 3539, 1)
CORRIDOR = Tile(2907, 3544, 1)
CASTLE_TOP = Tile(2900, 3566, 1)
INN_TOP = Tile(2914, 3542, 1)
GROUND = Tile(2900, 3540, 0)
SABA_CAVE = Tile(2270, 4759, 0)
SECRET_PATH = Tile(2830, 3580, 0)


def result(value):
    return value
    yield


class Burthorpe:
    """The player about Burthorpe, the inn and the mountain, with the pack, the scene, the chat and Harold's dice."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.chat_open = False
        self.continues = 0
        self.options = []
        self.main = -1
        self.count_dialog = False
        self.buttons = []
        self.texts = []
        self.messages = []
        self.closed = 0
        self.clicked = []
        self.lines = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'count', impl=lambda name: sum([i.count for i in self.pack if i.name == name]))
        spy_on(inventory, 'is_full', impl=lambda: len(self.pack) >= 28)
        spy_on(inventory, 'free', impl=lambda: 28 - len(self.pack))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(traversal, 'walk_to', impl=self.walk)
        spy_on(chat_dialog, 'is_open', impl=lambda: self.chat_open)
        spy_on(chat_dialog, 'can_continue', impl=lambda: self.continues > 0)
        spy_on(chat_dialog, 'continue_', impl=self.continue_)
        spy_on(chat_dialog, 'options', impl=lambda: self.options)
        spy_on(modals, 'is_open', impl=lambda: self.main != -1)
        spy_on(modals, 'close_if_open', impl=self.close_modal)
        spy_on(reader, 'modals', impl=lambda: Record({'main': self.main, 'chat': -1, 'side': -1}))
        spy_on(reader, 'count_dialog_open', impl=lambda: self.count_dialog)
        spy_on(reader, 'modal_buttons', impl=lambda root: self.buttons)
        spy_on(reader, 'main_modal_texts', impl=lambda: self.texts)
        spy_on(reader, 'main_modal_button_near_text', returns=-1)
        spy_on(_core, 'close_interfaces', impl=self.close)
        spy_on(_core, 'click_component', impl=self.click)
        spy_on(game_messages, 'mark', impl=lambda: len(self.messages))
        spy_on(game_messages, 'since', impl=lambda mark: [Fake(text=t) for t in self.messages[mark:]])
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(dp, 'settle_scene', impl=instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, tile, *args, **kwargs):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def continue_(self):
        self.continues -= 1
        return True
        yield

    def close(self):
        self.closed += 1
        self.main = -1
        self.chat_open = False

    def close_modal(self):
        self.main = -1
        return True
        yield

    def click(self, com):
        self.clicked.append(com)
        return True

    def hold(self, id, name='Item', count=1, interact=None, use_on=None, actions=None):
        held = Fake(id=id, name=name, count=count, actions=lambda: actions if actions is not None else ['Read'],
                    interact=interact if interact is not None else (lambda op: True),
                    use_on=use_on if use_on is not None else (lambda other: True))
        self.pack.append(held)
        return held

    def drop(self, id):
        self.pack = [held for held in self.pack if held.id != id]

    def loc(self, name, ops, interact=None, tile=None):
        made = Fake(id=1, name=name, actions=lambda: ops, distance=lambda: 1, tile=lambda: tile if tile is not None else self.at,
                    interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go


def reads_shut_menu_first():
    town = Burthorpe(GROUND)
    events = []
    state = {'combo': False}
    town.chat_open = True

    def close():
        events.append('close')
        town.chat_open = False

    def read(op):
        events.append(f'read:{op}')
        # The server refuses a held op behind an open dialogue.
        if not town.chat_open:
            state['combo'] = True
        return True

    def items():
        if state['combo']:
            return [Fake(id=DEATH_ITEM.COMBINATION.id, count=1, name='Combination')]
        return [Fake(id=DEATH_ITEM.IOU.id, count=1, name='Iou', actions=lambda: ['Read'], interact=read)]
    spy_on(inventory, 'items', impl=items)
    spy_on(_core, 'close_interfaces', impl=close)
    expect(run_wait(read_iou(town.log))).to_be(True)
    expect(events).to_equal(['close', 'read:Read'])


test("reading the IOU shuts Harold's menu first, since the server ignores a held op behind it", reads_shut_menu_first)


def reads_the_iou_through_its_boxes():
    town = Burthorpe(GROUND)
    town.hold(DEATH_ITEM.COMBINATION.id, 'Combination')
    expect(run_wait(read_iou(town.log))).to_be(True)
    town.pack = []
    expect(run_wait(read_iou(town.log))).to_be(False)
    expect(town.logged('no IOU to read')).to_be(True)
    town.hold(DEATH_ITEM.IOU.id, 'Iou', actions=[])
    expect(run_wait(read_iou(town.log))).to_be(False)
    expect(town.logged('could not use IOU')).to_be(True)
    town.pack = []
    town.hold(DEATH_ITEM.IOU.id, 'Iou', interact=lambda op: False)
    expect(run_wait(read_iou(town.log))).to_be(False)
    town.pack = []
    spy_on(dp, 'drive_dialog', impl=lambda prefer, log: result(True))
    spy_on(reader, 'main_modal_button_near_text', returns=77)

    def reads(op):
        town.continues = 1
        town.main = DEATH_DICE_MAIN
        return True
    town.hold(DEATH_ITEM.IOU.id, 'Iou', interact=reads)

    def answers(com):
        town.clicked.append(com)
        town.main = -1
        town.drop(DEATH_ITEM.IOU.id)
        town.hold(DEATH_ITEM.COMBINATION.id, 'Combination')
        return True
    spy_on(_core, 'click_component', impl=answers)
    expect(run_wait(read_iou(town.log))).to_be(True)
    expect(town.clicked).to_equal([77])

    town.pack = []

    def reads_closed(op):
        town.main = DEATH_DICE_MAIN
        town.chat_open = True
        return True
    town.hold(DEATH_ITEM.IOU.id, 'Iou', interact=reads_closed)
    spy_on(reader, 'main_modal_button_near_text', returns=-1)

    def drives(prefer, log):
        town.chat_open = False
        return True
        yield
    spy_on(dp, 'drive_dialog', impl=drives)
    expect(run_wait(read_iou(town.log))).to_be(False)
    expect(town.closed > 0).to_be(True)


test('the IOU read clicks its objbox away, or shuts the scroll, until the combination arrives', reads_the_iou_through_its_boxes)


def enters_harolds_room():
    town = Burthorpe(HAROLD_ROOM)
    expect(harold.inside_harold_room(HAROLD_ROOM)).to_be(True)
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(True)
    town.at = Tile(3200, 3200, 0)
    town.walk_ok = False
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(False)
    town.walk_ok = True
    town.at = GROUND
    spy_on(harold, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(False)
    expect(town.logged("could not stand on Harold's door tile")).to_be(True)

    def into_room(tile, radius, log):
        town.at = HAROLD_ROOM
        return True
        yield
    spy_on(harold, 'walk_to', impl=into_room)
    town.at = GROUND
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(True)
    spy_on(harold, 'walk_to', impl=lambda tile, radius, log: result(True))
    spy_on(harold, 'prompt_loc', impl=lambda step, log: result(False))
    town.at = CORRIDOR
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(False)
    expect(town.logged("still outside Harold's room")).to_be(True)

    def knocks(step, log):
        town.at = HAROLD_ROOM
        return True
        yield
    spy_on(harold, 'prompt_loc', impl=knocks)
    town.at = CORRIDOR
    expect(run_wait(harold.enter_harold_room(town.log))).to_be(True)

    spy_on(harold, 'enter_harold_room', impl=lambda log: result(False))
    expect(run_wait(harold.talk_in_harold_room(DENULTH_FINISH, town.log))).to_be(False)
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(True))
    spy_on(harold, 'talk_at', impl=lambda stop, log: result(True))
    expect(run_wait(harold.talk_in_harold_room(DENULTH_FINISH, town.log))).to_be(True)


test("Harold's room is entered by knocking from the door's own tile", enters_harolds_room)


def buys_harold_ale():
    town = Burthorpe(HAROLD_ROOM)
    expect(run_wait(harold.give_ale_to_harold(town.log))).to_be(False)
    expect(town.logged('no Asgarnian ale')).to_be(True)
    town.hold(DEATH_ITEM.ASGARNIAN_ALE.id, 'Asgarnian ale')
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(False))
    expect(run_wait(harold.give_ale_to_harold(town.log))).to_be(False)
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(True))
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(harold.give_ale_to_harold(town.log))).to_be(False)
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
    spy_on(harold, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
    expect(run_wait(harold.give_ale_to_harold(town.log))).to_be(False)
    expect(town.logged('never took the ale')).to_be(True)

    def drinks(expect_, prefer, log, ms=30000):
        town.drop(DEATH_ITEM.ASGARNIAN_ALE.id)
        return expect_()
        yield
    spy_on(harold, 'drive_until', impl=drinks)
    spy_on(harold, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(harold.give_ale_to_harold(town.log))).to_be(True)

    town.pack = []
    town.hold(DEATH_ITEM.BLURBERRY_SPECIAL.id, 'Blurberry special')
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(harold.give_blurberry_to_harold(town.log))).to_be(False)
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
    spy_on(harold, 'drive_boxes', impl=lambda expect_, ms, prefer=None, log=None: result(False))
    expect(run_wait(harold.give_blurberry_to_harold(town.log))).to_be(False)


test('Harold takes the ale he asked for, and the cocktail before the gamble', buys_harold_ale)


def button(com, label, pause, hidden=False):
    return ModalButton(com, label, '', hidden, pause)


def presses_armed_buttons():
    town = Burthorpe(HAROLD_ROOM)
    town.main = DEATH_DICE_MAIN
    expect(harold.dice_open()).to_be(True)
    expect(harold.roll_button()).to_be(None)
    expect(harold.armed(harold.roll_button)).to_be(False)
    expect(run_wait(harold.press_when_armed(harold.roll_button, _core.click_component, lambda: False, 'Roll Dice', town.log))).to_be(False)
    expect(town.logged('never came out of hiding')).to_be(True)
    town.buttons = [button(30, 'Roll Dice', False), button(31, 'Continue', True)]
    expect(harold.dice_state()).to_contain('30:Roll Dice')
    expect(harold.continue_button().com_id).to_be(31)
    expect(run_wait(harold.press_when_armed(harold.roll_button, _core.click_component, lambda: False, 'Roll Dice', town.log))).to_be(False)
    expect(town.logged('three presses')).to_be(True)
    expect(town.clicked).to_equal([30, 30, 30])

    def hides(com):
        town.buttons = [button(30, 'Roll Dice', False, True)]
        return True
    spy_on(_core, 'click_component', impl=hides)
    expect(run_wait(harold.press_when_armed(harold.roll_button, _core.click_component, lambda: True, 'Roll Dice', town.log))).to_be(True)
    town.buttons = [button(30, 'Roll Dice', False)]
    state = {'armed': True}

    def find():
        if state['armed']:
            state['armed'] = False
            return button(30, 'Roll Dice', False)
        return None
    expect(run_wait(harold.press_when_armed(find, _core.click_component, lambda: True, 'Roll Dice', town.log))).to_be(True)

    town.main = -1
    run_wait(harold.close_dice_if_open(town.log))
    expect(town.closed).to_be(0)
    town.main = DEATH_DICE_MAIN
    spy_on(_core, 'close_interfaces', returns=None)
    run_wait(harold.close_dice_if_open(town.log))
    expect(town.logged('would not close')).to_be(True)


test("the dice panel's buttons are pressed only once armed, and three dead presses give up", presses_armed_buttons)


def drains_the_round_tail():
    town = Burthorpe(HAROLD_ROOM)
    town.options = ['Would you like to gamble?']
    run_wait(harold.drain_round_tail(town.log))
    town.options = []
    town.continues = 2
    spy_on(harold, 'drive_boxes', impl=lambda expect_, ms, prefer=None, log=None: result(True))
    state = {'calls': 0}

    def clears(expect_, ms, prefer=None, log=None):
        state['calls'] += 1
        town.continues = 0
        return True
        yield
    spy_on(harold, 'drive_boxes', impl=clears)
    run_wait(harold.drain_round_tail(town.log))
    expect(state['calls']).to_be(1)


test("the settle queue's boxes are clicked away until it goes quiet or Harold offers a menu", drains_the_round_tail)


class Dice:
    """Harold's gamble as play_round sees it: the bet prompt, the dice panel, its buttons and the verdict."""

    def __init__(self, town, win=True, pays=True, iou=False):
        self.town = town
        self.win = win
        self.pays = pays
        self.iou = iou
        self.coins = town.hold(995, 'Coins', 500)

    def bet(self, value):
        self.town.count_dialog = False
        self.town.main = DEATH_DICE_MAIN
        self.town.buttons = [button(30, 'Roll Dice', False), button(31, 'Continue', True, True)]
        return True

    def press(self, com):
        if com == 30:
            self.town.buttons = [button(30, 'Roll Dice', False, True), button(31, 'Continue', True)]
            self.town.texts = ['You win!'] if self.win else ['You lose']
            return True
        self.town.main = -1
        if self.win and self.pays:
            self.coins.count = self.coins.count + 100
        if self.iou:
            self.town.hold(DEATH_ITEM.IOU.id, 'Iou')
        return True


def plays_rounds():
    town = Burthorpe(HAROLD_ROOM)
    spy_on(harold, 'drain_round_tail', impl=lambda log: result(None))
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
    spy_on(harold, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')
    expect(town.logged('never led to the bet prompt')).to_be(True)
    town.count_dialog = True
    spy_on(_core, 'answer_count', returns=False)
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')
    expect(town.logged('refused to enter a bet')).to_be(True)
    town.messages = []

    spy_on(_core, 'answer_count', impl=lambda value: closes_prompt(town))

    def refuses(expect_, prefer, log, ms=30000):
        if not town.count_dialog:
            town.messages.append('You cannot bet that much')
        return expect_()
        yield
    spy_on(harold, 'drive_until', impl=refuses)
    expect(run_wait(harold.play_round(5000, town.log))).to_be('abort')
    expect(town.logged('never opened the dice; You cannot bet that much')).to_be(True)

    for win, pays, iou, want in [[True, True, False, 'win'], [False, True, False, 'loss'], [True, False, False, 'abort'], [True, True, True, 'iou']]:
        town = Burthorpe(HAROLD_ROOM)
        spy_on(harold, 'drain_round_tail', impl=lambda log: result(None))
        spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
        spy_on(harold, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
        dice = Dice(town, win, pays, iou)
        town.count_dialog = True
        spy_on(_core, 'answer_count', impl=dice.bet)
        spy_on(_core, 'click_component', impl=dice.press)
        expect([run_wait(harold.play_round(101, town.log)), want, win, pays, iou]).to_equal([want, want, win, pays, iou])

    town = Burthorpe(HAROLD_ROOM)
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
    spy_on(harold, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
    town.main = DEATH_DICE_MAIN
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')
    town.buttons = [button(30, 'Roll Dice', False), button(31, 'Continue', True, True)]

    def rolls(com):
        town.buttons = [button(30, 'Roll Dice', False, True), button(31, 'Continue', True, True)]
        return True
    spy_on(_core, 'click_component', impl=rolls)
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')
    expect(town.logged('no verdict came')).to_be(True)
    town.buttons = [button(30, 'Roll Dice', False), button(31, 'Continue', True, True)]

    def stuck_verdict(com):
        town.buttons = [button(30, 'Roll Dice', False, True), button(31, 'Continue', True)]
        return True
    spy_on(_core, 'click_component', impl=stuck_verdict)
    expect(run_wait(harold.play_round(101, town.log))).to_be('abort')


test('a round answers the bet, rolls, takes the verdict and reads it as a win, a loss, an IOU or a failure', plays_rounds)


def closes_prompt(town):
    town.count_dialog = False
    return True


def gambles_for_the_iou():
    town = Burthorpe(HAROLD_ROOM)
    town.hold(DEATH_ITEM.IOU.id, 'Iou')
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(True)
    town.pack = []
    spy_on(harold, 'give_blurberry_to_harold', impl=lambda log: result(False))
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(False)
    spy_on(harold, 'give_blurberry_to_harold', impl=lambda log: result(True))
    spy_on(harold, 'close_dice_if_open', impl=lambda log: result(None))
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(False)
    expect(town.logged('out of coins')).to_be(True)
    town.hold(995, 'Coins', 2000)
    rounds = []

    def plays(bet, log):
        rounds.append(bet)
        if len(rounds) == 3:
            town.hold(DEATH_ITEM.IOU.id, 'Iou')
            return 'iou'
        return 'loss'
        yield
    spy_on(harold, 'play_round', impl=plays)
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(True)
    expect(rounds).to_equal([101, 202, 404])
    town.drop(DEATH_ITEM.IOU.id)
    spy_on(harold, 'play_round', impl=lambda bet, log: result('abort'))
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(False)
    spy_on(harold, 'play_round', impl=lambda bet, log: result('win'))
    town.at = CORRIDOR
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(False))
    expect(run_wait(harold.gamble_with_harold(town.log))).to_be(False)

    def crashes(bet, log):
        raise ValueError('lost the panel')
        yield
    spy_on(harold, 'play_round', impl=crashes)
    town.at = HAROLD_ROOM
    expect(lambda: run_wait(harold.gamble_with_harold(town.log))).to_throw('lost the panel')

    town.at = HAROLD_ROOM
    town.hold(DEATH_ITEM.COMBINATION.id, 'Combination')
    expect(run_wait(harold.reclaim_iou_from_harold(town.log))).to_be(True)
    town.pack = []
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(False))
    expect(run_wait(harold.reclaim_iou_from_harold(town.log))).to_be(False)
    spy_on(harold, 'enter_harold_room', impl=lambda log: result(True))
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(harold.reclaim_iou_from_harold(town.log))).to_be(False)
    spy_on(harold, 'open_dialogue', impl=lambda npc, log: result(True))
    spy_on(harold, 'drain_round_tail', impl=lambda log: result(None))
    spy_on(harold, 'drive_until', impl=lambda expect_, prefer, log, ms=30000: result(expect_()))
    expect(run_wait(harold.reclaim_iou_from_harold(town.log))).to_be(False)
    expect(town.logged('ended without a paper')).to_be(True)


test("the stake climbs past Harold's purse round by round until he writes the IOU, which he writes again when lost", gambles_for_the_iou)


def climbs_burthorpes_stairs():
    town = Burthorpe(GROUND)
    expect(nav.in_inn_band(GROUND)).to_be(True)
    expect(nav.stairs_bottom_for(CASTLE_TOP)).to_equal(TILE.CASTLE_STAIRS_BOTTOM)
    expect(nav.stairs_top_for(INN_TOP)).to_equal(TILE.INN_STAIRS_TOP)
    spy_on(game, 'tile', returns=None)
    expect(run_wait(nav.climb_one_flight('Climb-up', TILE.INN_STAIRS_BOTTOM, 1, town.log))).to_be(False)
    spy_on(game, 'tile', impl=lambda: town.at)
    town.at = INN_TOP
    expect(run_wait(nav.climb_one_flight('Climb-up', TILE.INN_STAIRS_BOTTOM, 1, town.log))).to_be(True)
    town.at = Tile(2950, 3550, 0)
    town.walk_ok = False
    expect(run_wait(nav.climb_one_flight('Climb-up', TILE.INN_STAIRS_BOTTOM, 1, town.log))).to_be(False)
    expect(town.logged('could not approach stairs stand')).to_be(True)
    expect(town.logged('no Stairs/Staircase')).to_be(True)
    town.walk_ok = True
    town.loc('stair', ['Climb-up'], interact=lambda op: False)
    expect(run_wait(nav.climb_one_flight('Climb-up', TILE.INN_STAIRS_BOTTOM, 1, town.log))).to_be(False)
    town.locs = []
    town.loc('Staircase', ['Climb-up'], interact=town.moves(INN_TOP))
    town.at = TILE.INN_STAIRS_BOTTOM
    expect(run_wait(nav.climb_one_flight('Climb-up', TILE.INN_STAIRS_BOTTOM, 1, town.log))).to_be(True)

    town.at = GROUND
    expect(run_wait(nav.descend_to_ground(town.log))).to_be(True)
    town.at = INN_TOP
    town.locs = []
    expect(run_wait(nav.descend_to_ground(town.log))).to_be(False)
    town.loc('Staircase', ['Climb-down'], interact=town.moves(GROUND))
    town.at = INN_TOP
    expect(run_wait(nav.descend_to_ground(town.log))).to_be(True)

    spy_on(game, 'tile', returns=None)
    expect(run_wait(nav.ascend_to_dest_floor(INN_TOP, town.log))).to_be(False)
    spy_on(game, 'tile', impl=lambda: town.at)
    town.at = INN_TOP
    expect(run_wait(nav.ascend_to_dest_floor(INN_TOP, town.log))).to_be(True)
    town.at = CASTLE_TOP
    spy_on(nav, 'descend_to_ground', impl=lambda log: result(False))
    expect(run_wait(nav.ascend_to_dest_floor(Tile(2914, 3540, 2), town.log))).to_be(False)
    spy_on(nav, 'descend_to_ground', impl=lambda log: result(True))
    town.walk_ok = False
    expect(run_wait(nav.ascend_to_dest_floor(Tile(2914, 3540, 2), town.log))).to_be(False)
    expect(town.logged('could not reach stairs bottom')).to_be(True)
    town.walk_ok = True
    town.at = GROUND
    spy_on(nav, 'climb_one_flight', impl=lambda op, stand, level, log: result(True))
    expect(run_wait(nav.ascend_to_dest_floor(Tile(2914, 3540, 1), town.log))).to_be(True)


test("the inn's and the castle's stairs are climbed by their own names, never a wall ladder", climbs_burthorpes_stairs)


def walks_between_floors():
    town = Burthorpe(GROUND)
    expect(run_wait(nav.walk_to(GROUND, 2, town.log))).to_be(True)
    town.at = INN_TOP
    spy_on(nav, 'descend_to_ground', impl=lambda log: result(False))
    expect(run_wait(nav.walk_to(Tile(2900, 3520, 0), 2, town.log))).to_be(False)

    def downs(log):
        town.at = GROUND
        return True
        yield
    spy_on(nav, 'descend_to_ground', impl=downs)
    expect(run_wait(nav.walk_to(Tile(2900, 3520, 0), 2, town.log))).to_be(True)
    town.at = GROUND
    spy_on(nav, 'ascend_to_dest_floor', impl=lambda dest, log: result(False))
    expect(run_wait(nav.walk_to(HAROLD_ROOM, 2, town.log))).to_be(False)

    def ups(dest, log):
        town.at = dest
        return True
        yield
    spy_on(nav, 'ascend_to_dest_floor', impl=ups)
    expect(run_wait(nav.walk_to(HAROLD_ROOM, 2, town.log))).to_be(True)
    town.at = GROUND
    expect(run_wait(nav.walk_to(Tile(2890, 3530, 0), 2, town.log))).to_be(True)

    spy_on(nav, 'talk_through', impl=lambda npc, prefer, log: result(True))
    spy_on(nav, 'walk_to', impl=lambda dest, radius, log: result(False))
    expect(run_wait(nav.talk_at(DENULTH_FINISH, town.log))).to_be(False)
    spy_on(nav, 'walk_to', impl=lambda dest, radius, log: result(True))
    town.at = GROUND
    expect(run_wait(nav.talk_at(DENULTH_FINISH, town.log))).to_be(True)
    stop = Record({'npc': 'Harold', 'anchor': HAROLD_ROOM, 'prefer': []})
    spy_on(nav, 'ascend_to_dest_floor', impl=lambda dest, log: result(False))
    expect(run_wait(nav.talk_at(stop, town.log))).to_be(False)
    spy_on(nav, 'ascend_to_dest_floor', impl=lambda dest, log: result(True))
    expect(run_wait(nav.talk_at(stop, town.log))).to_be(True)

    town.walk_ok = False
    expect(run_wait(nav.walk_secret_path(TILE.SCOUT, town.log))).to_be(False)


test('a walk changes floors through the ground, never inn to castle upstairs, and a talk climbs to its NPC', walks_between_floors)


def crosses_into_sabas_cave_and_tenzings_hut():
    town = Burthorpe(GROUND)
    expect(run_wait(dp.leave_saba_cave(town.log))).to_be(True)
    town.at = SABA_CAVE
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.leave_saba_cave(town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    expect(run_wait(dp.leave_saba_cave(town.log))).to_be(False)
    expect(town.logged('no Cave Exit')).to_be(True)
    town.loc('Cave Exit', [], interact=lambda op: False)
    expect(run_wait(dp.leave_saba_cave(town.log))).to_be(False)
    town.locs = []
    town.loc('Cave Exit', ['Exit'], interact=town.moves(GROUND))
    expect(run_wait(dp.leave_saba_cave(town.log))).to_be(True)

    town.at = SABA_CAVE
    expect(run_wait(dp.enter_saba_cave(town.log))).to_be(True)
    town.at = GROUND
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.enter_saba_cave(town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    town.locs = []
    expect(run_wait(dp.enter_saba_cave(town.log))).to_be(False)
    expect(town.logged('no Cave Entrance')).to_be(True)
    town.loc('Cave Entrance', ['Enter'], interact=lambda op: False)
    expect(run_wait(dp.enter_saba_cave(town.log))).to_be(False)
    town.locs = []
    town.loc('Cave Entrance', ['Enter'], interact=town.moves(SABA_CAVE))
    expect(run_wait(dp.enter_saba_cave(town.log))).to_be(True)

    town.at = GROUND
    town.npcs = [Fake(name='Tenzing', distance=lambda: 2)]
    expect(run_wait(dp.open_tenzing_door(town.log))).to_be(True)
    town.npcs = []
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.open_tenzing_door(town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    town.locs = []
    expect(run_wait(dp.open_tenzing_door(town.log))).to_be(True)
    town.loc('Door', ['Open'], interact=lambda op: False)
    expect(run_wait(dp.open_tenzing_door(town.log))).to_be(False)
    town.locs = []

    def knocks(op):
        town.chat_open = True
        return True
    town.loc('Door', ['Open'], interact=knocks)
    driven = []
    spy_on(dp, 'drive_dialog', impl=lambda prefer, log: result(driven.append(prefer)))
    expect(run_wait(dp.open_tenzing_door(town.log))).to_be(True)
    expect(driven[0][0]).to_be("I'm not the milkman")


test("Saba's cave is entered and left by its own ops, and Tenzing's door is knocked past the milkman", crosses_into_sabas_cave_and_tenzings_hut)


def places_the_stone_balls():
    town = Burthorpe(PEDESTALS[0].at)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    on_ground = {}
    spy_on(ground_items, 'query', impl=querying(lambda: [Fake(id=b[1], name='Stone ball', distance=lambda: 1, tile=b[2], interact=b[3]) for b in ball_rows(town, on_ground)]))
    for ped in PEDESTALS:
        on_ground[ped.at] = ped.ball_id
    expect(dp.all_pedestals_correct()).to_be(True)
    expect(run_wait(dp.solve_stone_mechanism(town.log))).to_be(True)
    expect(town.logged('already correctly placed')).to_be(True)

    on_ground.clear()
    expect(run_wait(dp.take_ground_ball(PEDESTALS[0].ball_id, PEDESTALS[0].at, town.log))).to_be(False)
    expect(town.logged('not on the ground')).to_be(True)
    town.hold(PEDESTALS[0].ball_id, 'Stone ball')
    expect(run_wait(dp.take_ground_ball(PEDESTALS[0].ball_id, PEDESTALS[0].at, town.log))).to_be(True)
    town.pack = []
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.take_ground_ball(PEDESTALS[0].ball_id, PEDESTALS[0].at, town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    expect(run_wait(dp.solve_stone_mechanism(town.log))).to_be(False)
    expect(town.logged('cannot find blue ball')).to_be(True)

    for ped in PEDESTALS:
        town.hold(ped.ball_id, 'Stone ball')

    def mechanisms():
        return [Fake(id=0, name='Stone Mechanism', actions=lambda: [], distance=lambda: 1, tile=(lambda t: lambda: t)(ped.at)) for ped in PEDESTALS]
    spy_on(locs, 'query', impl=querying(mechanisms))

    for held in town.pack:
        held._fields['use_on'] = placer(town, on_ground, held.id)
    expect(run_wait(dp.solve_stone_mechanism(town.log))).to_be(True)
    expect(town.logged('stone mechanism complete')).to_be(True)

    on_ground.clear()
    on_ground[PEDESTALS[0].at] = PEDESTALS[1].ball_id
    town.pack = []
    expect(run_wait(dp.solve_stone_mechanism(town.log))).to_be(False)
    expect(town.logged('removing wrong ball')).to_be(True)


def placer(town, on_ground, ball_id):
    def use(mech):
        on_ground[mech.tile()] = ball_id
        town.drop(ball_id)
        return True
    return use


def ball_rows(town, on_ground):
    rows = []
    for at, id in on_ground.items():
        rows.append([at, id, (lambda t: lambda: t)(at), lambda op: True])
    return rows


test('the five balls go on their own pedestals, a wrong one taken off first', places_the_stone_balls)


def scouts_and_hands_in():
    town = Burthorpe(GROUND)
    spy_on(dp, 'on_secret_path', impl=lambda tile: False)
    spy_on(dp, 'walk_secret_path', impl=lambda dest, log: result(False))
    expect(run_wait(dp.scout_secret_path(town.log))).to_be(False)
    spy_on(dp, 'on_secret_path', impl=lambda tile: True)
    expect(run_wait(dp.scout_secret_path(town.log))).to_be(False)
    expect(run_wait(dp.hand_in_to_denulth(town.log))).to_be(False)
    spy_on(dp, 'walk_secret_path', impl=lambda dest, log: result(True))
    town.chat_open = True
    spy_on(dp, 'drive_dialog', impl=lambda prefer, log: result(True))
    expect(run_wait(dp.scout_secret_path(town.log))).to_be(True)

    spy_on(dp, 'on_secret_path', impl=lambda tile: False)
    town.at = SABA_CAVE
    spy_on(dp, 'leave_saba_cave', impl=lambda log: result(False))
    expect(run_wait(dp.hand_in_to_denulth(town.log))).to_be(False)
    spy_on(dp, 'leave_saba_cave', impl=lambda log: result(True))
    spy_on(dp, 'talk_at', impl=lambda stop, log: result(True))
    expect(run_wait(dp.hand_in_to_denulth(town.log))).to_be(True)
    town.at = GROUND
    spy_on(dp, 'walk_secret_path', impl=lambda dest, log: result(False))
    expect(run_wait(dp.hand_in_to_denulth(town.log))).to_be(False)


test('the scout walks the secret path into its trigger, and the hand-in walks back off it to Denulth', scouts_and_hands_in)


def drains_until_done():
    town = Burthorpe(GROUND)
    expect(run_wait(dp.drain_until(lambda: True, town.log))).to_be(True)
    town.continues = 1
    town.options = []
    expect(run_wait(dp.drain_until(lambda: town.continues == 0, town.log))).to_be(True)
    town.chat_open = True
    town.options = ['A', 'B']

    def drives(prefer, log):
        town.chat_open = False
        town.options = []
        return True
        yield
    spy_on(dp, 'drive_dialog', impl=drives)
    expect(run_wait(dp.drain_until(lambda: False, town.log))).to_be(False)
    town.main = DEATH_DICE_MAIN
    spy_on(reader, 'main_modal_button_near_text', returns=12)
    state = {'done': False}

    def answers(com):
        town.main = -1
        state['done'] = True
        return True
    spy_on(_core, 'click_component', impl=answers)
    expect(run_wait(dp.drain_until(lambda: state['done'], town.log))).to_be(True)
    town.main = DEATH_DICE_MAIN
    spy_on(reader, 'main_modal_button_near_text', returns=-1)
    expect(run_wait(dp.drain_until(lambda: False, town.log, 3))).to_be(False)
    expect(town.closed > 0).to_be(True)


test("a drain clicks chat, menus and the objbox until its goal holds or everything is quiet", drains_until_done)


def gets_and_gives_the_certificate():
    town = Burthorpe(TILE.DENULTH)
    town.hold(DEATH_ITEM.ENTRANCE_CERT.id, 'Certificate')
    expect([run_wait(dp.take_entrance_cert_from_ground(town.log)), 'cert 1']).to_equal([True, 'cert 1'])
    expect([run_wait(dp.get_entrance_cert_from_denulth(town.log)), 'cert 2']).to_equal([True, 'cert 2'])
    town.pack = []
    for i in range(28):
        town.hold(1, 'Junk')
    expect(run_wait(dp.take_entrance_cert_from_ground(town.log))).to_be(False)
    expect(town.logged('pack full')).to_be(True)
    town.pack = []
    expect(run_wait(dp.take_entrance_cert_from_ground(town.log))).to_be(False)
    town.ground = [Fake(id=DEATH_ITEM.ENTRANCE_CERT.id, name='Certificate', distance=lambda: 1, tile=lambda: TILE.DENULTH, interact=lambda op: False)]
    expect(run_wait(dp.take_entrance_cert_from_ground(town.log))).to_be(False)

    def picks(op):
        town.ground = []
        town.hold(DEATH_ITEM.ENTRANCE_CERT.id, 'Certificate')
        return True
    town.ground = [Fake(id=DEATH_ITEM.ENTRANCE_CERT.id, name='Certificate', distance=lambda: 1, tile=lambda: TILE.DENULTH, interact=picks)]
    expect([run_wait(dp.get_entrance_cert_from_denulth(town.log)), 'cert 3']).to_equal([True, 'cert 3'])

    town.pack = []
    town.ground = []
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.get_entrance_cert_from_denulth(town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    for i in range(28):
        town.hold(1, 'Junk')
    expect(run_wait(dp.get_entrance_cert_from_denulth(town.log))).to_be(False)
    expect(town.logged('need a free inventory slot')).to_be(True)
    town.pack = []
    spy_on(dp, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(dp.get_entrance_cert_from_denulth(town.log))).to_be(False)

    def grants(npc, log):
        town.hold(DEATH_ITEM.ENTRANCE_CERT.id, 'Certificate')
        return True
        yield
    spy_on(dp, 'open_dialogue', impl=grants)
    spy_on(dp, 'drain_until', impl=lambda done, log, max_=40: result(done()))
    expect([run_wait(dp.get_entrance_cert_from_denulth(town.log)), 'cert 4']).to_equal([True, 'cert 4'])

    town.pack = []

    def drops(npc, log):
        town.ground = [Fake(id=DEATH_ITEM.ENTRANCE_CERT.id, name='Certificate', distance=lambda: 1, tile=lambda: TILE.DENULTH, interact=picks)]
        return True
        yield
    spy_on(dp, 'open_dialogue', impl=drops)
    state = {'first': True}

    def ground_after_walk(done, log, max_=40):
        return done()
        yield
    spy_on(dp, 'drain_until', impl=ground_after_walk)
    spy_on(dp, 'take_entrance_cert_from_ground', impl=lambda log: take_second(town, state, picks))
    expect([run_wait(dp.get_entrance_cert_from_denulth(town.log)), 'cert 5']).to_equal([True, 'cert 5'])

    town.pack = []
    spy_on(dp, 'get_entrance_cert_from_denulth', impl=lambda log: result(False))
    expect(run_wait(dp.give_cert_to_dunstan(town.log))).to_be(False)
    town.hold(DEATH_ITEM.ENTRANCE_CERT.id, 'Certificate')
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(False))
    expect(run_wait(dp.give_cert_to_dunstan(town.log))).to_be(False)
    spy_on(dp, 'walk_to', impl=lambda tile, radius, log: result(True))
    spy_on(dp, 'open_dialogue', impl=lambda npc, log: result(False))
    expect(run_wait(dp.give_cert_to_dunstan(town.log))).to_be(False)

    spy_on(dp, 'open_dialogue', impl=lambda npc, log: result(True))

    def takes_cert(done, log, max_=40):
        town.drop(DEATH_ITEM.ENTRANCE_CERT.id)
        return done()
        yield
    spy_on(dp, 'drain_until', impl=takes_cert)
    expect([run_wait(dp.give_cert_to_dunstan(town.log)), 'cert 6']).to_equal([True, 'cert 6'])


def take_second(town, state, picks):
    if state['first']:
        state['first'] = False
        return False
    town.ground = []
    town.hold(DEATH_ITEM.ENTRANCE_CERT.id, 'Certificate')
    return True
    yield


test("Denulth's certificate is taken into a free slot or off the floor, and given to Dunstan", gets_and_gives_the_certificate)


def recorder(called, name):
    def run(*args):
        called.append(name)
        return True
        yield
    return run


def runs_the_custom_steps_decide_builds():
    town = Burthorpe(GROUND)
    called = []
    for name in ['talk_at', 'talk_in_harold_room', 'enter_saba_cave', 'leave_saba_cave', 'open_tenzing_door']:
        spy_on(dp, name, impl=recorder(called, name))
    from rs2004.quests.defs.deathplateau.journal import DP_FLAG, DP_STAGE
    from rs2004.quests.engine.types import QuestProgress, QuestSnapshot

    def snap(stage, flags=None, inv_ids=None, inv=None, bank=None):
        return QuestSnapshot(journal='in_progress', stage=stage, progress=QuestProgress(stage, set(flags or [])), inv=inv or {},
                             inv_ids=inv_ids or {}, bank=bank or {}, bank_ids={}, bank_known=True, tile=GROUND, free_slots=20)
    steps = [
        dp.decide(snap(DP_STAGE.STARTED)),
        dp.decide(snap(DP_STAGE.SPOKEN_EOHRIC)),
        dp.decide(snap(DP_STAGE.SPOKEN_HAROLD)),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR)),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA])),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING])),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY, DP_FLAG.ENTRANCE_CERT, DP_FLAG.GIVEN_CERT],
                       inv_ids={DEATH_ITEM.IRON_BAR.id: 1}, inv={'iron bar': 1})),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY, DP_FLAG.ENTRANCE_CERT, DP_FLAG.GIVEN_CERT],
                       inv_ids={DEATH_ITEM.IRON_BAR.id: 1, DEATH_ITEM.CLIMBING_BOOTS.id: 1}, inv={'iron bar': 1, 'climbing boots': 1})),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY, DP_FLAG.ENTRANCE_CERT, DP_FLAG.GIVEN_CERT],
                       inv_ids={DEATH_ITEM.SPIKED_BOOTS.id: 1, DEATH_ITEM.BREAD.id: 10, DEATH_ITEM.TROUT.id: 10},
                       inv={'spiked boots': 1, 'bread': 10, 'trout': 10})),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SUPPLIES])),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.GOT_MAP])),
        dp.decide(snap(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SCOUTED], inv_ids={DEATH_ITEM.COMBINATION.id: 1}, inv={'combination': 1})),
    ]
    for step in steps:
        expect(step.kind).to_be('custom')
        run_wait(step.run(town.log))
    expect(len(called) >= len(steps)).to_be(True)


test("decide's own runners talk to the right NPC and take the right door or cave", runs_the_custom_steps_decide_builds)

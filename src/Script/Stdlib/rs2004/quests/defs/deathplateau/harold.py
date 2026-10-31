"""Ported from rs2b0t's src/bot/api/ai/quests/defs/deathplateau/harold.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.deathplateau.areas import DEATH_DICE_MAIN, DEATH_ITEM, HAROLD_DOOR, HAROLD_PURSE_START, MAX_BET, TILE
from rs2004.quests.defs.deathplateau.nav import talk_at, walk_to
from rs2004.quests.exec.primitives import drive_dialog, open_dialogue
from rs2004.quests.exec.prompts import drive_boxes, drive_until, prompt_loc
from rs2004.traversal import traversal

__all__ = ['inside_harold_room', 'enter_harold_room', 'talk_in_harold_room', 'give_ale_to_harold', 'give_blurberry_to_harold', 'close_dice_if_open', 'next_stake', 'purse_after', 'gamble_with_harold', 'reclaim_iou_from_harold']


def held(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def coins():
    return inventory.count('Coins')


def combination_found():
    return held(DEATH_ITEM.IOU.id) > 0 or held(DEATH_ITEM.COMBINATION.id) > 0


# Why: the room is an L, x2905..2906 for z3536..3539 widening to x2907 for z3540..3542, and the room east of it opens onto the corridor with no door.
# Why: a bounding box that swallowed the east room called a stop 2 tiles east of Harold "arrived", with a wall between him and the talk.
def inside_harold_room(tile):
    """Harold's bedroom, which the door at (2906,3543) is the only way into."""
    if not tile or tile.level != 1 or tile.x < 2905 or tile.z < 3536 or tile.z > 3542:
        return False
    return (tile.x <= 2907 if tile.z >= 3540 else tile.x <= 2906)


# Why: `death_harold_door` picks which half of its script to run with `~check_axis`, which for a south-facing wall compares your z with the door's and nothing else.
# Why: clicked from z3544 it takes the leaving branch and teleports you onto the door tile without knocking, so the stand is the door's own tile.
def enter_harold_room(log):
    """Knock, wait for "Come in!", and be teleported into the bedroom."""
    if inside_harold_room(game.tile()):
        return True
    here = game.tile()
    _c1 = here and TILE.HAROLD.distance_to(here) > 64
    if _c1:
        _w2 = yield from traversal.walk_resilient(TILE.INN_STAIRS_BOTTOM, radius=2, attempts=3, timeout_ms=300000, log=log)
        _c1 = not (_w2)
    if _c1:
        return False
    stand = Tile(HAROLD_DOOR.x, HAROLD_DOOR.z, HAROLD_DOOR.level)
    _w3 = yield from walk_to(stand, 0, log)
    if not (_w3) and not inside_harold_room(game.tile()):
        log(f'could not stand on Harold\'s door tile ({stand.x},{stand.z})')
        return False
    if inside_harold_room(game.tile()):
        return True
    yield from prompt_loc(Record({
        'name': 'Door',
        'op': 'Open',
        'id': HAROLD_DOOR.id,
        'near': stand,
        'within': 6,
        'expect': lambda: inside_harold_room(game.tile()),
        'expect_ms': 25000,
    }), log)
    # Why: `Reach` reports 'retry' on a crossing that landed, because the teleport happens after its own wait, so your tile is the only oracle.
    if inside_harold_room(game.tile()):
        return True
    log(f'still outside Harold\'s room at {game.tile()}')
    return False


def talk_in_harold_room(stop, log):
    """Enter the bedroom, then run one of Harold's conversations from inside it."""
    _w4 = yield from enter_harold_room(log)
    if not (_w4):
        return False
    _result5 = yield from talk_at(stop, log)
    return _result5


# the ale
ALE_MS = 45000


def give_ale_to_harold(log):
    """Hand Harold the Asgarnian ale his `harold_drink` branch asks for."""
    if held(DEATH_ITEM.ASGARNIAN_ALE.id) == 0:
        log('no Asgarnian ale in the pack to give Harold')
        return False
    _w6 = yield from enter_harold_room(log)
    if not (_w6):
        return False
    _w7 = yield from open_dialogue('Harold', log)
    if not (_w7):
        return False

    def drunk():
        return held(DEATH_ITEM.ASGARNIAN_ALE.id) == 0

    # Why: the branch ends on the 3-way menu that offers the gamble, so the drive stops when the ale leaves the pack.
    _w8 = yield from drive_until(drunk, ['Can I buy you a drink?'], log, ALE_MS)
    if not (_w8):
        log('Harold never took the ale')
        return False
    # Why: the branch signs off on the menu, and a menu left standing is a chat modal the next step's clicks get dropped behind.
    yield from drive_dialog(['Can I buy you a drink?'], log)
    return True


def give_blurberry_to_harold(log):
    drink = ([item for item in [DEATH_ITEM.BLURBERRY_SPECIAL, DEATH_ITEM.PREMADE_BLURBERRY_SPECIAL] if held(item.id) > 0] or [None])[0]
    if not drink:
        log('need a Blurberry special before gambling with Harold')
        return False
    _w10 = yield from enter_harold_room(log)
    _c9 = not (_w10)
    if not _c9:
        _w11 = yield from open_dialogue('Harold', log)
        _c9 = not (_w11)
    if _c9:
        return False
    before = held(drink.id)

    def ready():
        return any([("i fink i've had enough" in text.lower()) or (held(drink.id) < before and ('now that hit the spot' in text.lower())) for text in chat_dialog.texts()])

    _w12 = yield from drive_boxes(ready, ALE_MS, ['Can I buy you a drink?'], log)
    if not (_w12):
        return False
    yield from drive_dialog([], log)
    return True


# the dice
def dice_open():
    return reader.modals().main == DEATH_DICE_MAIN


# Why: the live harness surfaces a bounded number of log lines per poll, so one line per button would only ever show the last.
def dice_state():
    return ', '.join([f"{b.com_id}:{b.label or b.menu}{(' pause' if b.pause else '')}{(' hidden' if b.hidden else '')}" for b in reader.modal_buttons(DEATH_DICE_MAIN)])


# Why: `com_28` is `buttontype=normal` and `com_30` is `buttontype=pause`, and both pack ids are the server's own, so match on label and pause flag.
def roll_button():
    return ([b for b in reader.modal_buttons(DEATH_DICE_MAIN) if not b.pause and b.label.lower().startswith('roll dice')] or [None])[0]


def continue_button():
    return ([b for b in reader.modal_buttons(DEATH_DICE_MAIN) if b.pause] or [None])[0]


ROLL_ARMED_MS = 20000
PRESS_MS = 3000
SETTLE_MS = 30000


# Why: `death_dice` is on the engine's do-not-auto-close list, so a round that bails with it up leaves a main modal nothing shuts and the next round can't talk past it.
def close_dice_if_open(log):
    """Shut the dice interface if a round left it open."""
    if not dice_open():
        return
    # Why: `Player.closeModal` drops a script suspended on `p_pausebutton`, so the close both clears the screen and frees Harold for the next round.
    _core.close_interfaces()
    _w13 = yield from execution.delay_until(lambda: not dice_open(), 3000)
    if not (_w13):
        log('Harold gamble: the dice interface would not close')


def armed(find):
    button = find()
    return button is not None and not button.hidden


# Why: the client sends one RESUME_PAUSEBUTTON per interface open and silently refuses later presses, and `Player.runScript` silently drops an `if_button` that arrives while Harold is still delayed.
# Why: each press waits for its layer to be unhidden, the same `if_sethide` the script arms the button with.
def press_when_armed(find, press, landed, what, log):
    _w14 = yield from execution.delay_until(lambda: armed(find), ROLL_ARMED_MS)
    if not (_w14):
        log(f'Harold gamble: the {what} button never came out of hiding; panel shows [{dice_state()}]')
        return False
    for attempt in range(3):
        button = find()
        if not button or button.hidden:
            return landed()
        press(button.com_id)
        _w15 = yield from execution.delay_until(landed, PRESS_MS)
        if _w15:
            return True
    log(f'Harold gamble: three presses on {what} changed nothing')
    return False


# Why: the settle queue speaks in bursts, a line then an objbox page with a tick of nothing between, so one quiet poll proves nothing.
def drain_round_tail(log):
    """Click away everything `haroldgamble_end` says after the interface closes."""

    def busy():
        return chat_dialog.is_open() or chat_dialog.can_continue() or modals.is_open()

    deadline = _core.step_time() + SETTLE_MS
    quiet = 0
    while _core.step_time() < deadline and quiet < 4:
        # Why: a menu means the queue is done and Harold has started a fresh conversation.
        if len(chat_dialog.options()) > 0:
            return
        if busy():
            quiet = 0
            yield from drive_boxes(lambda: not busy(), SETTLE_MS, [], log)
            continue
        quiet += 1
        yield from execution.delay_ticks(1)


def play_round(bet, log):
    """One round: answer the bet, wait out Harold's roll, roll, and take the verdict."""
    _w16 = yield from open_dialogue('Harold', log)
    if not (_w16):
        return 'abort'
    # Why: `harold_gamble` runs `if_close` before `p_countdialog`, so the chat closing is a step in the chain.
    _w17 = yield from drive_until(lambda: reader.count_dialog_open() or dice_open(), ['Would you like to gamble?'], log, 30000)
    if not (_w17):
        log('Harold gamble: the gamble option never led to the bet prompt')
        return 'abort'
    if reader.count_dialog_open():
        if not _core.answer_count(bet):
            log(f'Harold gamble: the client refused to enter a bet of {bet}')
            return 'abort'
        yield from execution.delay_until(lambda: not reader.count_dialog_open(), 3000)
    mark = game_messages.mark()
    # Why: 2 `~chatnpc` pages stand between the bet and `if_openmain`, and a refused bet answers in one of them instead.
    _w18 = yield from drive_until(dice_open, [], log, 20000)
    if not (_w18):
        said = ' / '.join([line.text for line in game_messages.since(mark)])
        log(f"Harold gamble: a bet of {bet} never opened the dice{(f'; {said}' if said else '')}")
        return 'abort'
    before = coins()
    _w19 = yield from press_when_armed(roll_button, _core.click_component, lambda: not armed(roll_button), 'Roll Dice', log)
    if not (_w19):
        return 'abort'
    _w20 = yield from execution.delay_until(lambda: armed(continue_button), ROLL_ARMED_MS)
    if not (_w20):
        log(f'Harold gamble: the roll landed but no verdict came; panel shows [{dice_state()}]')
        return 'abort'
    # Why: `player_roll` writes the verdict into the panel before it unhides the Continue layer, and pressing Continue removes the panel.
    won = any([('you win' in text.lower()) for text in reader.main_modal_texts()])
    _w21 = yield from press_when_armed(continue_button, _core.click_component, lambda: not dice_open(), 'Continue', log)
    if not (_w21):
        return 'abort'
    yield from drain_round_tail(log)
    log(f"Harold gamble: {('won' if won else 'lost')} {bet}, coins {before} → {coins()}")
    if combination_found():
        return 'iou'
    if not won:
        return 'loss'
    if coins() <= before:
        log(f'Harold gamble: a win of {bet} paid nothing and left no IOU')
        return 'abort'
    return 'win'


MAX_ROUNDS = 25


# Why: `death_ig_commander.rs2` gives Harold 100gp when Denulth starts the quest, and `dice_winnings` only writes `harold_lostall` (the IOU) when `harold_gold - bet` goes below zero on a win.
# Why: every loss hands him the stake, so a fixed bet can't bankrupt him after the first: 101 against a purse of 201 pays out and the loop never ends.
# Why: `%death_bits` is not transmitted, so the purse is tracked from the stake and the verdict.
def next_stake(purse, pack):
    """The stake that bankrupts a purse this size, as far as the pack and `harold_gamble`'s ceiling allow."""
    return min(MAX_BET, pack, purse + 1)


# Why: a win Harold could pay proves his purse was larger than the stake and nothing more, so the estimate goes up and hits the ceiling in a few rounds.
def purse_after(purse, stake, result):
    """The purse the round's verdict implies."""
    return (purse + stake if result == 'loss' else min(MAX_BET, purse * 2 + 1))


def gamble_with_harold(log):
    """Roll against Harold, raising the stake past his purse, until he writes the IOU."""
    if combination_found():
        return True
    _w22 = yield from give_blurberry_to_harold(log)
    if not (_w22):
        return False
    purse = HAROLD_PURSE_START
    round_ = 1
    while round_ <= MAX_ROUNDS and not combination_found():
        bet = next_stake(purse, coins())
        if bet <= 0:
            log(f'Harold gamble: out of coins after {round_ - 1} rounds')
            return False
        log(f'Harold gamble round {round_}: staking {bet} against a purse read as {purse}')
        result = None
        try:
            result = yield from play_round(bet, log)
        except Exception as e:
            yield from close_dice_if_open(log)
            raise e
        yield from close_dice_if_open(log)
        if result == 'iou':
            break
        if result == 'abort':
            return combination_found()
        purse = purse_after(purse, bet, result)
        _c23 = not inside_harold_room(game.tile())
        if _c23:
            _w24 = yield from enter_harold_room(log)
            _c23 = not (_w24)
        if _c23:
            return False
        round_ += 1
    log(f'Harold gamble done: iou={held(DEATH_ITEM.IOU.id)} coins={coins()}')
    return combination_found()


# Why: `harold_reclaim_iou` runs itself off the front of any `opnpc1` once the quest is past `death_given_iou` and neither paper is in the pack, so the conversation only has to be opened and answered.
def reclaim_iou_from_harold(log):
    """Ask Harold to write the IOU out again."""
    if combination_found():
        return True
    _w25 = yield from enter_harold_room(log)
    if not (_w25):
        return False
    _w26 = yield from open_dialogue('Harold', log)
    if not (_w26):
        return False
    _w27 = yield from drive_until(combination_found, [], log, SETTLE_MS)
    if not (_w27):
        log('Harold gamble: the reclaim conversation ended without a paper')
    yield from drain_round_tail(log)
    return combination_found()

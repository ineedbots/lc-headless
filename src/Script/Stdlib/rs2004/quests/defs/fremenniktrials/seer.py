"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/seer.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.fremenniktrials.areas import FT_ID, FT_LOC, FT_TILE, PEER, in_puzzle_room, in_seer_east, in_seer_west
from rs2004.quests.defs.fremenniktrials.supplies import combine, walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.quests.exec.prompts import prompt_loc, settle_scene, use_on_loc
from rs2004.reach import reach

__all__ = ['PEER_BANK', 'seer_step', 'riddle_answer']

COMBO = Record({
    'ROOT': 10051,
    'LETTER': [10095, 10096, 10097, 10098],
    'DOWN': [10099, 10101, 10103, 10105],
    'UP': [10100, 10102, 10104, 10106],
    'ENTER': 10109,
})
ALPHABET = 26
# Why: the plaque wraps its lines, so a second riddle line reaches here with a '|' where its break was; riddle_answer flattens those first.
RIDDLES = [
    [['my first is in mage, but not in wizard', 'powerful tool you will possess'], 'MIND'],
    [['my first is in tar, but not in a swamp', 'wears more rings the older'], 'TREE'],
    [['my first is in the well, but not at sea', 'when stolen from you causes you death'], 'LIFE'],
    [['my first is in fish, but not in the sea', 'cannot die as long as it has food'], 'FIRE'],
    [['my first is in water, and also in tea', 'crushes mountains, drains rivers'], 'TIME'],
    [['my first is in wizard, but not in a mage', 'helps to make bread, let birds fly'], 'WIND'],
]
# Why: once Thorvald's trial is open Peer leads with the deposit offer, and taking it never starts his own.
PEER_START = ['Ask about becoming a Fremennik', 'Yes']
PEER_BANK = ['Ask about depositing your equipment', 'Bank your equipment', 'Yes']


def holding(id):
    return inventory.count_by_id(id) > 0


def carried(snap, id):
    return snap.inv_ids.get(id, 0) if snap.inv_ids is not None else 0


BUCKETS = [FT_ID.BUCKET_EMPTY, FT_ID.BUCKET_1, FT_ID.BUCKET_2, FT_ID.BUCKET_3, FT_ID.BUCKET_4, FT_ID.BUCKET_5]
JUGS = [FT_ID.JUG_EMPTY, FT_ID.JUG_1, FT_ID.JUG_2, FT_ID.JUG_3]


def level(ids, snap):
    """How full the carried vessel is, or -1 when it isn't carried."""
    return ([_i for _i, id in enumerate(ids) if carried(snap, id) > 0] or [-1])[0]


def seer_step(snap):
    """Peer's trial: enter empty-handed, solve the lock riddle, then cross the puzzle floor."""
    if has_flag(snap.progress, 'seer-done'):
        return None
    if not has_flag(snap.progress, 'seer-started'):
        return Record({'kind': 'talk', 'stop': PEER(PEER_START)})
    if in_puzzle_room(snap.tile):
        return puzzle_floor(snap)
    if in_seer_east(snap.tile):
        return east_room(snap)
    if in_seer_west(snap.tile):
        return Record({'kind': 'custom', 'name': 'climb to the puzzle floor', 'run': climb_west})
    # Why: the trial refuses anyone carrying or wearing anything, and Peer's own spell is the only bank within reach.
    if len(snap.inv) > 0 or len(snap.worn) > 0:
        return Record({'kind': 'talk', 'stop': PEER(PEER_BANK)})
    return Record({'kind': 'custom', 'name': "solve the lock on Peer's door", 'run': solve_riddle_and_enter})


# The puzzle floor
def puzzle_floor(snap):
    if carried(snap, FT_ID.SEERS_KEY) > 0:
        return Record({'kind': 'custom', 'name': 'take the trapdoor down to the locked door', 'run': go_down_east})
    if carried(snap, FT_ID.FROZEN_KEY) > 0:
        return use_on_loc_step(FT_ID.FROZEN_KEY, 'Cooking range', FT_LOC.RANGE, FT_TILE.PUZZLE_RANGE, lambda: holding(FT_ID.SEERS_KEY), 'melt the ice off the key')
    if carried(snap, FT_ID.SEALED_VASE_WATER) > 0:
        return use_on_loc_step(FT_ID.SEALED_VASE_WATER, 'Frozen table', FT_LOC.FROZEN_TABLE, FT_TILE.PUZZLE_FROZEN_TABLE, lambda: holding(FT_ID.FROZEN_KEY), 'freeze the sealed vase until it shatters')
    if carried(snap, FT_ID.VASE_WATER) > 0 and carried(snap, FT_ID.VASE_LID) > 0:
        return combine(FT_ID.VASE_LID, FT_ID.VASE_WATER, FT_ID.SEALED_VASE_WATER, 'screw the lid onto the full vase')
    if carried(snap, FT_ID.VASE) > 0 and carried(snap, FT_ID.VASE_LID) > 0:
        return use_on_loc_step(FT_ID.VASE, 'Tap', FT_LOC.TAP, FT_TILE.PUZZLE_TAP, lambda: holding(FT_ID.VASE_WATER), 'fill the vase from the tap')
    if carried(snap, FT_ID.VASE) > 0:
        return Record({'kind': 'custom', 'name': 'take the trapdoor down to the mural', 'run': go_down_east})
    if carried(snap, FT_ID.RED_DISK) < 2:
        return collect_disks(snap)
    return measure_water(snap)


# Why: the bookcase and both mounted heads stop giving once their disk is in the mural, so the order here is also the recovery order.
def collect_disks(snap):
    goop = carried(snap, FT_ID.RED_GOOP) > 0
    wooden = carried(snap, FT_ID.WOODEN_DISK) > 0
    if carried(snap, FT_ID.RED_DISK) == 0 and not goop and not wooden:
        return loc_step("Unicorn's head", 'Study', FT_LOC.UNICORN_HEAD, FT_TILE.PUZZLE_UNICORN, lambda: holding(FT_ID.RED_DISK), 'take the red disk from the unicorn head')
    if not wooden and not goop:
        return loc_step("Bull's head", 'Study', FT_LOC.BULL_HEAD, FT_TILE.PUZZLE_BULL, lambda: holding(FT_ID.WOODEN_DISK), 'take the wooden disk from the bull head')
    if goop:
        return combine(FT_ID.RED_GOOP, FT_ID.WOODEN_DISK, FT_ID.RED_DISK, 'paint the wooden disk red')
    if carried(snap, FT_ID.RED_HERRING) == 0:
        return loc_step('Bookcase', 'Search', FT_LOC.BOOKCASE, FT_TILE.PUZZLE_BOOKCASE, lambda: holding(FT_ID.RED_HERRING), 'find the red herring behind the books')
    return use_on_loc_step(FT_ID.RED_HERRING, 'Cooking range', FT_LOC.RANGE, FT_TILE.PUZZLE_RANGE, lambda: holding(FT_ID.RED_GOOP), 'cook the red herring for its dye')


# Why: the chest's balance opens on 4 fifths, and the only vessels in the room hold 3 and 5.
def measure_water(snap):
    """Fill the 5-bucket to 4 using the 3-jug, then trade it for the vase."""
    jug = level(JUGS, snap)
    bucket = level(BUCKETS, snap)
    if jug < 0:
        return search_chest()
    if bucket < 0:
        return open_cupboard()
    if bucket == 4:
        return use_on_loc_step(FT_ID.BUCKET_4, 'Chest', FT_LOC.SCALES_CHEST, FT_TILE.PUZZLE_SCALES, lambda: holding(FT_ID.VASE), 'balance the scales with a four-fifths bucket')
    if bucket == 5:
        return use_on_loc_step(FT_ID.BUCKET_5, 'Drain', FT_LOC.DRAIN, FT_TILE.PUZZLE_DRAIN, lambda: holding(FT_ID.BUCKET_EMPTY), 'empty the bucket down the drain')
    if jug > 0 and (bucket == 0 or jug == 3):
        poured = min(5, bucket + jug)
        return combine(JUGS[jug], BUCKETS[bucket], BUCKETS[poured], 'pour the jug into the bucket')
    return use_on_loc_step(JUGS[jug], 'Tap', FT_LOC.TAP, FT_TILE.PUZZLE_TAP, lambda: holding(FT_ID.JUG_3), 'fill the jug from the tap')


def search_chest():
    def _fn1(log):
        yield from open_container(FT_LOC.SEER_CHEST_SHUT, FT_LOC.SEER_CHEST_OPEN, FT_TILE.PUZZLE_CHEST, log)
        status = yield from reach.loc_op('Chest', 'Search', FT_TILE.PUZZLE_CHEST, lambda: holding(FT_ID.JUG_EMPTY), within=4, expect_ms=15000, log=log)
        return status == 'done'
    return Record({'kind': 'custom', 'name': 'open the chest and take the jug', 'run': _fn1})


def open_cupboard():
    def _fn2(log):
        yield from open_container(FT_LOC.CUPBOARD_SHUT, FT_LOC.CUPBOARD_OPEN, FT_TILE.PUZZLE_CUPBOARD, log)
        status = yield from reach.loc_op('Cupboard', 'Search', FT_TILE.PUZZLE_CUPBOARD, lambda: holding(FT_ID.BUCKET_EMPTY), within=4, expect_ms=15000, log=log)
        return status == 'done'
    return Record({'kind': 'custom', 'name': 'open the cupboard and take the bucket', 'run': _fn2})


def _loc_in_range(id):
    return locs.query().where(lambda l: l.id == id).within(5).nearest()


def _shut_in_range(id):
    return locs.query().where(lambda l: l.id == id).action('Open').within(5).nearest()


# Why: a loc that transforms keeps its old id for a tick, so the Search that follows waits for the open id.
def open_container(shut_id, open_id, near, log):
    if _loc_in_range(open_id) is not None:
        return
    if not _shut_in_range(shut_id):
        yield from walk_to(near, 1, log)
        yield from settle_scene()
    shut = _shut_in_range(shut_id)
    if shut and (shut.interact('Open')):
        yield from execution.delay_until(lambda: _loc_in_range(open_id) is not None, 6000)


# The mural room, one floor below the second door
def east_room(snap):
    if carried(snap, FT_ID.SEERS_KEY) > 0:
        return Record({'kind': 'custom', 'name': 'unlock the far door', 'run': unlock_exit})
    if carried(snap, FT_ID.RED_DISK) > 0:
        return Record({'kind': 'custom', 'name': 'press a red disk into the mural', 'run': press_disk})
    # Why: the mural hands the lid back to anyone whose 2 disks are already in it, so gate this on still needing one.
    if carried(snap, FT_ID.VASE) > 0 and carried(snap, FT_ID.VASE_LID) == 0:
        return loc_step('Abstract mural', 'Study', FT_LOC.MURAL, FT_TILE.MURAL_STAND, lambda: holding(FT_ID.VASE_LID), 'take the vase lid out of the mural')
    return Record({'kind': 'custom', 'name': 'climb back to the puzzle floor', 'run': climb_east})


def press_disk(log):
    before = inventory.count_by_id(FT_ID.RED_DISK)
    _result3 = yield from use_on_loc(FT_ID.RED_DISK, Record({'name': 'Abstract mural', 'near': FT_TILE.MURAL_STAND, 'id': FT_LOC.MURAL, 'within': 4}), [], lambda: inventory.count_by_id(FT_ID.RED_DISK) < before, log)
    return _result3


# Step builders
# Why: Both mounted heads open `~mesbox`, and the disk appears only after it is continued.
def loc_step(name, op, id, near, expect, label):
    return Record({
        'kind': 'custom',
        'name': label,
        'run': lambda log: prompt_loc(Record({'name': name, 'op': op, 'near': near, 'id': id, 'within': 4, 'expect': expect, 'expect_ms': 20000}), log),
    })


def use_on_loc_step(item_id, name, id, near, expect, label):
    return Record({
        'kind': 'custom',
        'name': label,
        'run': lambda log: use_on_loc(item_id, Record({'name': name, 'near': near, 'id': id, 'within': 4}), [], expect, log),
    })


def climb(near, id, log):
    status = yield from reach.loc_op('Ladder', 'Climb-up', near, lambda: in_puzzle_room(game.tile()), id=id, log=log)
    return status == 'done'


def climb_west(log):
    return climb(FT_TILE.SEER_UP_LADDER, FT_LOC.SEER_UP_LADDER, log)


def climb_east(log):
    return climb(FT_TILE.SEER_DOWN_LADDER, FT_LOC.SEER_DOWN_LADDER, log)


# Why: the east trapdoor starts shut and `loc_change` gives it the same id as the western one, so the search radius keeps them apart.
def go_down_east(log):
    _w4 = yield from walk_to(FT_TILE.PUZZLE_EAST_TRAPDOOR, 0, log)
    if not (_w4):
        return False
    yield from settle_scene()

    def find_open():
        return locs.query().where(lambda l: l.id == FT_LOC.TRAPDOOR_OPEN).action('Climb-down').within(3).nearest()

    shut = locs.query().where(lambda l: l.id == FT_LOC.TRAPDOOR_SHUT).action('Open').within(3).nearest()
    if shut:
        if not (shut.interact('Open')):
            return False
        yield from execution.delay_until(lambda: find_open() is not None, 6000)
    open = find_open()
    if not open:
        log('the east trapdoor never opened')
        return False
    if not (open.interact('Climb-down')):
        return False
    _result5 = yield from execution.delay_until(lambda: in_seer_east(game.tile()), 8000)
    return _result5


def unlock_exit(log):
    _w6 = yield from walk_to(FT_TILE.SEER_DOOR2_INNER, 0, log)
    if not (_w6):
        return False
    yield from settle_scene()
    door = locs.query().where(lambda l: l.id == FT_LOC.SEER_DOOR2).within(4).nearest()
    key = ([i for i in inventory.items() if i.id == FT_ID.SEERS_KEY] or [None])[0]
    if not door or not key:
        log('no locked door or no key in range')
        return False
    if not (key.use_on(door)):
        return False
    _result7 = yield from execution.delay_until(lambda: not holding(FT_ID.SEERS_KEY), 8000)
    return _result7


# The riddle lock
def riddle_answer(text):
    flat = ' '.join(text.lower().replace('|', ' ').split())
    for phrases, answer in RIDDLES:
        if any([phrase in flat for phrase in phrases]):
            return answer
    return None


def set_dial(index, letter, log):
    target = ord(letter) - 65
    for press in range(ALPHABET + 1):
        _v11 = reader.component_text(COMBO.LETTER[index])
        shown = ((_v11 if _v11 is not None else 'A')).strip().upper()
        if not shown:
            return False
        if ord(shown) - 65 == target:
            return True
        current = ord(shown) - 65
        up = (target - current + ALPHABET) % ALPHABET
        down = (current - target + ALPHABET) % ALPHABET
        if not _core.click_component((COMBO.UP[index] if up <= down else COMBO.DOWN[index])):
            log(f'could not press dial {index + 1}')
            return False
        yield from execution.delay_until(lambda: (reader.component_text(COMBO.LETTER[index]) or '').strip().upper() != shown, 3000)
    return False


def solve_riddle_and_enter(log):
    """Read the plaque, dial the answer, then walk through the door the lock guarded."""
    _w12 = yield from walk_to(FT_TILE.SEER_DOOR1, 0, log)
    if not (_w12):
        return False
    yield from settle_scene()

    def find():
        return locs.query().where(lambda l: l.id == FT_LOC.SEER_DOOR1).action('Open').within(4).nearest()

    door = find()
    if not door:
        log('no combination-lock door in range')
        return False
    mark = game_messages.mark()
    if not (door.interact('Open')):
        return False
    _w13 = yield from execution.delay_until(lambda: in_seer_west(game.tile()), 5000)
    if _w13:
        return True
    spoken = yield from read_riddle(log)
    if spoken is None:
        return False
    answer = riddle_answer(spoken)
    if not answer:
        log(f'the plaque did not match any known riddle: "{spoken.strip()}"')
        return False
    log(f'the lock\'s riddle answers {answer}')
    for i in range(4):
        _w14 = yield from set_dial(i, answer[i], log)
        if not (_w14):
            return False
    if not _core.click_component(COMBO.ENTER):
        return False
    _w15 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, 'solved the riddle'), 8000)
    if not (_w15):
        log('the lock rejected the answer')
        return False
    yield from modals.close_if_open()
    again = find()
    if not again or not (again.interact('Open')):
        return False
    _result16 = yield from execution.delay_until(lambda: in_seer_west(game.tile()), 8000)
    return _result16


# Why: Read both plaque boxes before continuing; they contain the only copy of the answer.
def read_riddle(log):
    spoken = ''
    deadline = _core.step_time() + 40000
    while _core.step_time() < deadline and reader.modals().main != COMBO.ROOT:
        if chat_dialog.is_open():
            spoken += ' ' + ' '.join(chat_dialog.texts())
        options = chat_dialog.options()
        if len(options) > 0:
            pick = pick_preferred(options, ['Read the riddle'])
            if not pick:
                log(f"the lock offered [{' | '.join(options)}] with no way to read the riddle")
                return None
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
    if reader.modals().main != COMBO.ROOT:
        log('the combination lock never opened')
        return None
    return spoken

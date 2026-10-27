"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/basement.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.ernest.areas import EC_ID, EC_NAME, EC_TILE
from rs2004.quests.exec.prompts import settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal


__all__ = ['REGION_BOX', 'in_alcove', 'basement_region', 'DOOR_OPEN', 'CHAIN', 'leave_manor_basement', 'fetch_oil_can']

# Why: the 7 components the 9 puzzle doors cut the basement into, from a flood over the baked collision pack with the doors closed.
# Why: the boxes are pairwise disjoint, so a tile alone names a room.
REGION_BOX = Record({
    'entry': Record({'min_x': 3100, 'max_x': 3118, 'min_z': 9745, 'max_z': 9757}),
    'r1r4': Record({'min_x': 3105, 'max_x': 3112, 'min_z': 9758, 'max_z': 9767}),
    'r2': Record({'min_x': 3100, 'max_x': 3104, 'min_z': 9763, 'max_z': 9767}),
    'r5': Record({'min_x': 3100, 'max_x': 3104, 'min_z': 9758, 'max_z': 9762}),
    'r3': Record({'min_x': 3096, 'max_x': 3099, 'min_z': 9763, 'max_z': 9767}),
    'r6': Record({'min_x': 3096, 'max_x': 3099, 'min_z': 9758, 'max_z': 9762}),
    'r9': Record({'min_x': 3090, 'max_x': 3099, 'min_z': 9753, 'max_z': 9757}),
})
ALCOVE_BOX = Record({'min_x': 3091, 'max_x': 3096, 'min_z': 3354, 'max_z': 3363})


def in_alcove(tile):
    """Pure, so `decide()` can branch on the snapshot tile without a client."""
    return bool(tile) and tile.level == 0 and tile.x >= ALCOVE_BOX.min_x and tile.x <= ALCOVE_BOX.max_x and tile.z >= ALCOVE_BOX.min_z and tile.z <= ALCOVE_BOX.max_z


def basement_region(tile):
    if not tile or tile.level != 0:
        return 'outside'
    for name, box in REGION_BOX._fields.items():
        if tile.x >= box.min_x and tile.x <= box.max_x and tile.z >= box.min_z and tile.z <= box.max_z:
            return name
    return 'outside'


A = 1 << 0
B = 1 << 1
C = 1 << 2
D = 1 << 3
E = 1 << 4
F = 1 << 5
DOOR_OPEN = Record({
    '1to2': lambda b: not (b & A) and not (b & B) and not not (b & D) and not not (b & E) and not not (b & F),
    '2to3': lambda b: not (b & B) and not not (b & D) and not not (b & F),
    '4to5': lambda b: not not (b & A) and not not (b & B) and not not (b & D),
    '5to6': lambda b: not not (b & D),
    '8to9': lambda b: not (b & E) and not not (b & F),
    '2to5': lambda b: not (b & A) and not (b & B) and not not (b & C) and not not (b & D) and not (b & E) and not not (b & F),
    '3to6': lambda b: not (b & B) and not not (b & D) and not (b & F),
    '4to7': lambda b: not not (b & A) and not not (b & B) and not (b & C) and not (b & D) and not (b & E) and not (b & F),
    '5to8': lambda b: (not (b & C) and not not (b & D)) or (not (b & A) and not (b & B) and not not (b & C) and not not (b & D) and not (b & E) and not not (b & F)),
})
LEVER_TILE = Record({
    'A': Tile(3108, 9745, 0),
    'B': Tile(3118, 9752, 0),
    'C': Tile(3112, 9760, 0),
    'D': Tile(3108, 9767, 0),
    'E': Tile(3097, 9767, 0),
    'F': Tile(3096, 9765, 0),
})
DOOR_SIDE = Record({
    '1to2': Record({'near': Tile(3105, 9765, 0), 'far': Tile(3104, 9765, 0)}),
    '2to3': Record({'near': Tile(3100, 9765, 0), 'far': Tile(3099, 9765, 0)}),
    '4to5': Record({'near': Tile(3105, 9760, 0), 'far': Tile(3104, 9760, 0)}),
    '5to6': Record({'near': Tile(3100, 9760, 0), 'far': Tile(3099, 9760, 0)}),
    '8to9': Record({'near': Tile(3100, 9755, 0), 'far': Tile(3099, 9755, 0)}),
    '2to5': Record({'near': Tile(3102, 9763, 0), 'far': Tile(3102, 9762, 0)}),
    '3to6': Record({'near': Tile(3097, 9763, 0), 'far': Tile(3097, 9762, 0)}),
    '4to7': Record({'near': Tile(3108, 9758, 0), 'far': Tile(3108, 9757, 0)}),
    '5to8': Record({'near': Tile(3102, 9758, 0), 'far': Tile(3102, 9757, 0)}),
})


def pull(lever, to):
    return (Record({'kind': 'pull', 'lever': lever, 'to': to}))


def cross(door, from_):
    return (Record({
        'kind': 'door',
        'door': door,
        'stand': (DOOR_SIDE.get(door).near if from_ == 'near' else DOOR_SIDE.get(door).far),
        'arrive': (DOOR_SIDE.get(door).far if from_ == 'near' else DOOR_SIDE.get(door).near),
    }))


CHAIN = [
    pull('B', 'down'),
    pull('A', 'down'),
    cross('4to7', 'far'),
    pull('D', 'down'),
    cross('4to5', 'near'),
    cross('5to8', 'near'),
    pull('B', 'up'),
    pull('A', 'up'),
    cross('5to8', 'far'),
    cross('5to6', 'near'),
    cross('3to6', 'far'),
    pull('F', 'down'),
    pull('E', 'down'),
    cross('2to3', 'far'),
    cross('1to2', 'far'),
    pull('C', 'down'),
    cross('1to2', 'near'),
    cross('2to3', 'near'),
    pull('E', 'up'),
    cross('2to3', 'far'),
    cross('2to5', 'near'),
    cross('5to8', 'near'),
    cross('8to9', 'near'),
]

def _lever_position(text):
    words = text.lower().rstrip('.').split()
    if len(words) == 5 and words[:3] == ['you', 'pull', 'lever'] and words[3] in ['a', 'b', 'c', 'd', 'e', 'f'] and words[4] in ['up', 'down']:
        return words[4]
    return None


def PULLED(text):
    return _lever_position(text) is not None


def PULLED_UP(text):
    return _lever_position(text) == 'up'

DOOR_LOCKED = 'this door is locked'


def held(id):
    return inventory.count_by_id(id)


def here():
    return game.tile()


# Why: these levers never change model, so the chat line is the only oracle.
# Why: [oploc1] reads the bit before toggling, so the line names the resulting state.
def set_lever(lever, want, log):
    """Pull a lever until the server confirms the wanted state."""
    stand = LEVER_TILE.get(lever)
    for attempt in range(4):
        yield from sustain.run()
        _w1 = yield from traversal.walk_resilient(stand, radius=1, attempts=4, timeout_ms=90000, log=log)
        if not (_w1):
            log(f'could not reach lever {lever} at ({stand.x},{stand.z})')
            return False
        yield from settle_scene()
        loc = locs.query().name(f'Lever {lever}').action('Pull').within(3).nearest()
        if not loc:
            log(f'no \'Lever {lever}\' in the scene at ({stand.x},{stand.z})')
            return False
        mark = game_messages.mark()
        if not (loc.interact('Pull')):
            continue
        _w2 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, PULLED), 6000)
        if not (_w2):
            continue
        now = ('up' if game_messages.saw_since(mark, PULLED_UP) else 'down')
        log(f'lever {lever} is now {now}')
        if now == want:
            return True
    log(f'could not force lever {lever} {want}')
    return False


def cross_door(move, log):
    """Cross one puzzle door. `open_and_close_door2` teleports you through and shuts it behind you, so the tell is the region change."""
    want = basement_region(move.arrive)
    if basement_region(here()) == want:
        return 'crossed'
    _w3 = yield from traversal.walk_resilient(move.stand, radius=1, attempts=4, timeout_ms=90000, log=log)
    if not (_w3):
        log(f'could not reach the {move.door} stand ({move.stand.x},{move.stand.z})')
        return 'failed'
    yield from settle_scene()
    door = locs.query().name('Door').action('Open').within(3).nearest()
    if not door:
        log(f'no {move.door} in the scene')
        return 'failed'
    mark = game_messages.mark()
    if not (door.interact('Open')):
        return 'failed'
    yield from execution.delay_until(lambda: basement_region(here()) == want or game_messages.saw_since(mark, DOOR_LOCKED), 6000)
    if basement_region(here()) == want:
        log(f'crossed {move.door} into {want}')
        return 'crossed'
    return ('locked' if game_messages.saw_since(mark, DOOR_LOCKED) else 'failed')


def run_move(move, log):

    if move.kind == 'pull':
        _c4 = yield from set_lever(move.lever, move.to, log)
    else:
        _w5 = yield from cross_door(move, log)
        _c4 = (_w5) == 'crossed'
    return _c4


def invert(move):
    """The inverse of a pull is the same pull; the inverse of a crossing is its mirror."""
    if move.kind == 'pull':
        return Record({'kind': 'pull', 'lever': move.lever, 'to': ('down' if move.to == 'up' else 'up')})
    return Record({'kind': 'door', 'door': move.door, 'stand': move.arrive, 'arrive': move.stand})


executed = 0


def unwind(log):
    global executed
    """Retrace the executed prefix, which lands back at the ladder with every lever up."""
    log(f'unwinding {executed} chain move(s) back to the ladder')
    for i in range(executed - 1, 0 - 1, -1):
        _w6 = yield from run_move(invert(CHAIN[i]), log)
        if not (_w6):
            log(f'unwind stalled at move {i}')
            return
        executed = i
    executed = 0


def enter_basement(log):
    if basement_region(here()) != 'outside':
        return True
    _w7 = yield from traversal.walk_resilient(EC_TILE.LADDER_DOWN_STAND, radius=1, attempts=4, timeout_ms=300000, log=log)
    if not (_w7):
        log('could not reach the ladder alcove — is the bookcase crossing in transports.json?')
        return False
    yield from settle_scene()
    status = yield from reach.loc_op('Ladder', 'Climb-down', EC_TILE.LADDER_DOWN_STAND, lambda: basement_region(here()) != 'outside', log=log)
    yield from settle_scene()
    return status == 'done' and basement_region(here()) != 'outside'


# Why: only `entry` and `r9` can be left from here; everything else needs an unwind and only `fetchOilCan` knows how far the chain got.
# Why: a process that starts stranded mid-maze can't know the lever bits, and the ladder that resets them is out of reach, so it says so and stops.
def leave_basement(log):
    """Walk out of the basement, or report that the position is unrecoverable."""
    if basement_region(here()) == 'outside':
        return True
    if basement_region(here()) == 'r9':
        back = invert(CHAIN[len(CHAIN) - 1])
        _w8 = yield from cross_door(back, log)
        if (_w8) != 'crossed':
            return False
    if basement_region(here()) != 'entry':
        log(f'stranded in {basement_region(here())} with unknown lever state — cannot climb out')
        return False
    status = yield from reach.loc_op('Ladder', 'Climb-up', EC_TILE.LADDER_UP_STAND, lambda: basement_region(here()) == 'outside', log=log)
    yield from settle_scene()
    return status == 'done' and basement_region(here()) == 'outside'


# Why: the nav crossing exists, but the executor gets one look at the scene and arriving here is a scripted teleport.
# Why: every loc query is empty for about a tick after a teleport, so one miss blacklists the edge and strands the bot in a pocket with no other exit.
# Why: Reach retries.
def leave_alcove(log):
    """Pull the alcove lever back into the manor."""
    if not in_alcove(here()):
        return True
    yield from sustain.run()
    _w9 = yield from traversal.walk_resilient(EC_TILE.ALCOVE_LEVER, radius=1, attempts=4, timeout_ms=90000, log=log)
    if not (_w9):
        log('could not reach the alcove lever')
        return False
    yield from settle_scene()
    status = yield from reach.loc_op('Lever', 'Pull', EC_TILE.ALCOVE_LEVER, lambda: not in_alcove(here()), expect_ms=8000, log=log)
    yield from settle_scene()
    if status == 'done' and not in_alcove(here()):
        log('pulled the alcove lever back into the manor')
        return True
    log('the alcove lever did not open the bookcase')
    return False


def leave_manor_basement(log):
    """Out of the basement and out of the alcove, 2 pockets, one exit each."""
    _w10 = yield from leave_basement(log)
    if not (_w10):
        return False
    _result11 = yield from leave_alcove(log)
    return _result11


def take_oil_can(log):
    _w12 = yield from traversal.walk_resilient(EC_TILE.OIL_CAN_SPAWN, radius=1, attempts=4, timeout_ms=60000, log=log)
    if not (_w12):
        return False
    yield from settle_scene()
    can = ground_items.query().name(EC_NAME.OIL_CAN).within(6).nearest()
    if not can:
        log('no Oil can on the floor of the west room')
        return False
    if not (can.interact('Take')):
        return False
    _result13 = yield from execution.delay_until(lambda: held(EC_ID.OIL_CAN) > 0, 8000)
    return _result13


def fetch_oil_can(log):
    global executed
    """Bookcase, ladder, the fixed chain, the can, and back out. Every exit resets `%ernestlever` (~reset_haunted_levers), so a pass always starts all-up."""
    if held(EC_ID.OIL_CAN) > 0:
        _result14 = yield from leave_manor_basement(log)
        return _result14
    for pass_ in range(3):
        yield from sustain.run()
        # Leaving through the ladder resets the levers; merely being in entry does not.
        left = yield from leave_basement(log)
        if not left:
            return False
        _w17 = yield from enter_basement(log)
        if not (_w17):
            return False
        # The preceding exit ran ~reset_haunted_levers, so the chain starts from all-up.
        executed = 0
        failed = False
        for move in CHAIN:
            yield from sustain.run()
            _w18 = yield from run_move(move, log)
            if not (_w18):
                log(f'chain move {executed} failed — restarting the pass')
                failed = True
                break
            executed += 1
        _c19 = failed
        if not _c19:
            _w20 = yield from take_oil_can(log)
            _c19 = not (_w20)
        if _c19:
            yield from unwind(log)
            continue
        # Why: the can is this step's deliverable, so the return value reads the can.
        # Why: a false here re-enters the maze for a leg that already succeeded, and `decide()`'s escape branch retries the way out anyway.
        yield from leave_manor_basement(log)
        return held(EC_ID.OIL_CAN) > 0
    log('three passes of the lever chain and still no oil can')
    return False

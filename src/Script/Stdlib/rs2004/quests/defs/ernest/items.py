"""Ported from rs2b0t's src/bot/api/ai/quests/defs/ernest/items.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.ernest.areas import EC_ID, EC_NAME, EC_TILE
from rs2004.quests.exec.prompts import prompt_loc, settle_scene, use_on_loc
from rs2004.traversal import traversal


__all__ = ['in_closet', 'leave_closet', 'fetch_rubber_tube', 'fetch_pressure_gauge']

def held(id):
    return inventory.count_by_id(id)


def take_spawn(id, name, at, log):
    """Walk to a ground spawn and take it."""
    if held(id) > 0:
        return True
    _w1 = yield from traversal.walk_resilient(at, radius=1, attempts=4, timeout_ms=180000, log=log)
    if not (_w1):
        log(f'could not reach the {name} spawn at ({at.x},{at.z},{at.level})')
        return False
    yield from settle_scene()
    item = ground_items.query().name(name).within(6).nearest()
    if not item:
        log(f'no {name} on the ground at ({at.x},{at.z},{at.level})')
        return False
    if not (item.interact('Take')):
        return False
    _result2 = yield from execution.delay_until(lambda: held(id) > 0, 8000)
    return _result2


def dig_closet_key(log):
    """Dig the compost heap. `op1=Search` answers "I'm not looking through that with my hands!". The key is an oplocu with a spade, re-issued whenever none is held."""
    if held(EC_ID.CLOSET_KEY) > 0:
        return True
    _result3 = yield from use_on_loc(EC_ID.SPADE, Record({'name': 'Compost heap', 'near': EC_TILE.COMPOST_STAND}), [], lambda: held(EC_ID.CLOSET_KEY) > 0, log)
    return _result3


CLOSET_BOX = Record({'min_x': 3108, 'max_x': 3112, 'min_z': 3366, 'max_z': 3368})


def in_closet(tile):
    """Pure, so `decide()` can branch on the snapshot tile without a client."""
    return bool(tile) and tile.level == 0 and tile.x >= CLOSET_BOX.min_x and tile.x <= CLOSET_BOX.max_x and tile.z >= CLOSET_BOX.min_z and tile.z <= CLOSET_BOX.max_z


# Why: the closet is a sealed 10-tile room, `open_and_close_door2` shuts the door behind whoever crosses it and `op1=Open` answers "The door is locked".
# Why: the key is the only way in and out, and it is never consumed.
def cross_closet_door(want, log):
    """Cross the closet door in the named direction."""

    def done():
        return in_closet(game.tile()) == (want == 'in')

    if done():
        return True
    if held(EC_ID.CLOSET_KEY) == 0:
        log(f'no key in the pack — cannot get {want} of the closet')
        return False
    _result4 = yield from use_on_loc(EC_ID.CLOSET_KEY, Record({'name': 'Door', 'near': (EC_TILE.CLOSET_STAND if want == 'in' else EC_TILE.CLOSET_INSIDE), 'within': 4}), [], done, log)
    return _result4


# Why: nothing routes out of the closet, so any leg that starts in there has to key its way out before it walks anywhere.
# Why: `decide()` calls this ahead of everything else, including the bank trip.
def leave_closet(log):
    """Key out of the closet before any leg that walks."""
    yield from sustain.run()
    _result5 = yield from cross_closet_door('out', log)
    return _result5


def fetch_rubber_tube(log):
    if held(EC_ID.RUBBER_TUBE) > 0:
        _result6 = yield from cross_closet_door('out', log)
        return _result6
    yield from sustain.run()
    if held(EC_ID.SPADE) == 0:
        log('no spade in the pack — cannot dig the compost heap')
        return False
    _w7 = yield from dig_closet_key(log)
    if not (_w7):
        log('the compost heap did not give up a key')
        return False
    yield from sustain.run()
    _w8 = yield from cross_closet_door('in', log)
    if not (_w8):
        log('the closet door did not open to the key')
        return False
    yield from settle_scene()
    _w9 = yield from take_spawn(EC_ID.RUBBER_TUBE, EC_NAME.RUBBER_TUBE, EC_TILE.RUBBER_TUBE_SPAWN, log)
    if not (_w9):
        # Leaving matters more than the tube; stranded in here, every later leg burns its budget failing to walk out.
        yield from cross_closet_door('out', log)
        return False
    _result10 = yield from cross_closet_door('out', log)
    return _result10


# Why: `[oploc1,hauntedfountain]` runs 2 `~chatplayer` lines before the `inv_add`, so the gauge only lands once the dialogue has been continued twice.
# Why: waiting on the item without driving the box never sees it, hence `promptLoc` over a bare op.

BITTEN = 'something in the water bites you'


# Why: `bitten` is the only proof the piranhas are alive; a search that never landed looks the same as one that did.
# Why: mistaking a reach refusal for a bite re-poisons the fountain.
def search_fountain(log):
    """Search the fountain; `bitten` means the piranhas are still alive."""
    for attempt in range(3):
        _w11 = yield from traversal.walk_resilient(EC_TILE.FOUNTAIN_STAND, radius=1, attempts=3, timeout_ms=120000, log=log)
        if not (_w11):
            log('could not reach the fountain stand')
            return 'unknown'
        yield from settle_scene()
        mark = game_messages.mark()
        got = yield from prompt_loc(Record({
            'name': 'Fountain',
            'op': 'Search',
            'near': EC_TILE.FOUNTAIN_STAND,
            'expect': lambda: held(EC_ID.PRESSURE_GAUGE) > 0,
            'expect_ms': 12000,
        }), log)
        if got:
            return 'gauge'
        if game_messages.saw_since(mark, BITTEN):
            return 'bitten'
        log(f"fountain search landed nothing — said: [{' | '.join([m.text for m in game_messages.since(mark)])}]")
    return 'unknown'


def poison_fountain(log):
    if held(EC_ID.POISONED_FISH_FOOD) == 0:
        _w12 = yield from take_spawn(EC_ID.POISON, EC_NAME.POISON, EC_TILE.POISON_SPAWN, log)
        if not (_w12):
            return False
        yield from sustain.run()
        _w13 = yield from take_spawn(EC_ID.FISH_FOOD, EC_NAME.FISH_FOOD, EC_TILE.FISH_FOOD_SPAWN, log)
        if not (_w13):
            return False
        poison = ([i for i in inventory.items() if i.id == EC_ID.POISON] or [None])[0]
        food = ([i for i in inventory.items() if i.id == EC_ID.FISH_FOOD] or [None])[0]
        if not poison or not food:
            log('poison or fish food went missing before they could be combined')
            return False
        if not (poison.use_on(food)):
            return False
        _w14 = yield from execution.delay_until(lambda: held(EC_ID.POISONED_FISH_FOOD) > 0, 8000)
        if not (_w14):
            log('combining the poison and the fish food produced nothing')
            return False
    yield from sustain.run()
    # The pour runs a 5-tick message chain before the varp flips.
    _result15 = yield from use_on_loc(EC_ID.POISONED_FISH_FOOD, Record({'name': 'Fountain', 'near': EC_TILE.FOUNTAIN_STAND}), [], lambda: held(EC_ID.POISONED_FISH_FOOD) == 0, log)
    return _result15


# Why: `%haunted_manor_fountain_poisoned` is unreadable, and a fountain poisoned on an earlier run hands the gauge straight over, so the search comes first.
# Why: the wrong guess costs one hitpoint.
def fetch_pressure_gauge(log):
    """Fetch the pressure gauge, poisoning the fountain if the search comes back bitten."""
    if held(EC_ID.PRESSURE_GAUGE) > 0:
        return True
    yield from sustain.run()
    first = yield from search_fountain(log)
    if first == 'gauge':
        log('the fountain was already poisoned')
        return True
    log(('piranhas are still alive — poisoning the fountain' if first == 'bitten' else 'the fountain would not answer — poisoning it anyway'))
    _w16 = yield from poison_fountain(log)
    if not (_w16):
        return held(EC_ID.PRESSURE_GAUGE) > 0
    # Why: the pour runs a 5-tick message chain before the varp flips, and a search that races it comes back bitten.
    # Why: the return reads the gauge; a false with the gauge in the pack sends the bot round again.
    yield from execution.delay_ticks(6)
    attempt = 0
    while attempt < 3 and held(EC_ID.PRESSURE_GAUGE) == 0:
        yield from search_fountain(log)
        attempt += 1
    # The gauge can land a tick after the op returns; without the wait a leg that worked reports failure.
    yield from execution.delay_until(lambda: held(EC_ID.PRESSURE_GAUGE) > 0, 5000)
    return held(EC_ID.PRESSURE_GAUGE) > 0

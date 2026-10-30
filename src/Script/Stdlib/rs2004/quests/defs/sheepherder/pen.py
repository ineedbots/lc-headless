"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/pen.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.game import game
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.sheepherder.areas import BONES_OBJ, FEED_OBJ, FURNACE_LOC, FURNACE_STAND, GATE_INSIDE, GATE_LOC, GATE_OUTSIDE, PEN, PROD, PROD_OBJ, PROD_SPAWN, in_box, sheep_name
from rs2004.quests.defs.sheepherder.herd import clear_refusal, herd_to_pen, sheep_in_pen
from rs2004.quests.exec.prompts import held_id, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['enter_pen', 'leave_pen', 'fetch_prod', 'pen_and_kill', 'incinerate']

CROSS_MS = 8000


def inside_pen():
    return in_box(PEN, game.tile())


def gate_loc():
    return locs.query().where(lambda loc: (loc.id in GATE_LOC)).action('Open').within(4).nearest()


# Why: the gate is a `p_teleport`: you land on the far side and the loc reverts 3 ticks later, so where you're standing is the only oracle.
def cross_gate(stand, want, log):
    if want():
        return True
    _w1 = yield from traversal.walk_resilient(stand, radius=0, attempts=3, timeout_ms=90000, log=log)
    if not (_w1):
        return False
    if want():
        return True
    gate = gate_loc()
    if not gate:
        log(f'sheepherder: no enclosure gate at ({stand.x},{stand.z})')
        return False
    if not (gate.interact('Open')):
        return False
    crossed = yield from execution.delay_until(want, CROSS_MS)
    yield from clear_refusal()
    if crossed:
        yield from settle_scene()
    return crossed


def enter_pen(log):
    return cross_gate(GATE_OUTSIDE, inside_pen, log)


def leave_pen(log):
    return cross_gate(GATE_INSIDE, lambda: not inside_pen(), log)


def fetch_prod(log):
    """The barn prod, which sits inside the enclosure and so is fetched wearing the suit."""
    if held_id(PROD_OBJ) == 0:
        _w2 = yield from enter_pen(log)
        if not (_w2):
            return False
        _w3 = yield from traversal.walk_resilient(PROD_SPAWN, radius=1, attempts=3, timeout_ms=90000, log=log)
        if not (_w3):
            return False
        prod = ground_items.query().where(lambda item: item.id == PROD_OBJ).within(8).nearest()
        if not prod:
            log(f'sheepherder: no {PROD} on the barn floor at ({PROD_SPAWN.x},{PROD_SPAWN.z})')
            return False
        if not (prod.interact('Take')):
            return False
        _w4 = yield from execution.delay_until(lambda: held_id(PROD_OBJ) > 0, 8000)
        if not (_w4):
            return False
    _result5 = yield from equipment.equip(PROD)
    return _result5


def bones_on_ground(id):
    return ground_items.query().where(lambda item: item.id == id).within(12).nearest()


def take_bones(n, log):
    id = BONES_OBJ[n]
    for attempt in range(4):
        if held_id(id) > 0:
            return True
        bones = ground_items.query().where(lambda item: item.id == id).within(12).nearest()
        if not bones:
            yield from execution.delay_ticks(2)
            continue
        at = bones.tile()
        _w6 = yield from traversal.walk_resilient(at, radius=1, attempts=2, timeout_ms=30000, log=log)
        if not (_w6):
            continue
        still = ground_items.query().where(lambda item: item.id == id).within(12).nearest()
        if still and (still.interact('Take')):
            yield from execution.delay_until(lambda: held_id(id) > 0, 6000)
    if held_id(id) > 0:
        return True
    log(f'sheepherder: no remains from {sheep_name(n)} to pick up')
    return False


# Why: the sheep in the enclosure is a 150-tick `npc_add`, so the kill runs in the same leg as the herd; a decide() round trip loses the sheep and costs another 40 pushes.
def poison(n, log):
    if held_id(BONES_OBJ[n]) > 0:
        return True
    _w7 = yield from enter_pen(log)
    if not (_w7):
        return False
    sheep = sheep_in_pen(n)
    if not sheep:
        _result8 = yield from take_bones(n, log)
        return _result8
    _w9 = yield from traversal.walk_resilient(sheep.tile(), radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w9):
        return False
    feed = ([item for item in inventory.items() if item.id == FEED_OBJ] or [None])[0]
    target = sheep_in_pen(n)
    if not feed or not target:
        log(f'sheepherder: no feed in the pack or {sheep_name(n)} gone from the enclosure')
        return False
    log(f'sheepherder: feeding the poison to {sheep_name(n)}')
    if not (feed.use_on(target)):
        return False
    bones_id = BONES_OBJ[n]
    yield from execution.delay_until(lambda: bones_on_ground(bones_id) is not None, 10000)
    yield from clear_refusal()
    _result10 = yield from take_bones(n, log)
    return _result10


def pen_and_kill(n, log):
    """Herd this sheep in, kill it, and leave holding its remains."""
    if held_id(BONES_OBJ[n]) > 0:
        return True
    if bones_on_ground(BONES_OBJ[n]):
        _result11 = yield from take_bones(n, log)
        return _result11
    if sheep_in_pen(n):
        _result12 = yield from poison(n, log)
        return _result12
    _c13 = inside_pen()
    if _c13:
        _w14 = yield from leave_pen(log)
        _c13 = not (_w14)
    if _c13:
        return False
    _w15 = yield from herd_to_pen(n, log)
    if not (_w15):
        return False
    _result16 = yield from poison(n, log)
    return _result16


# Why: `incinerate_bones` deletes the remains, waits 3 ticks and then sets the bits, so a leg that stops when the pack empties hands `decide()` a journal still reading "now I must kill it".
BURNT = 'remains burn to dust'


def incinerate(n, log):
    _w17 = yield from enter_pen(log)
    if not (_w17):
        return False
    log(f'sheepherder: burning the remains of {sheep_name(n)}')
    mark = game_messages.mark()
    burnt = yield from use_on_loc(BONES_OBJ[n], Record({'name': 'Furnace', 'near': FURNACE_STAND, 'id': FURNACE_LOC, 'within': 6}), [], lambda: held_id(BONES_OBJ[n]) == 0, log)
    if not burnt:
        return False
    _result18 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, BURNT), 8000)
    return _result18

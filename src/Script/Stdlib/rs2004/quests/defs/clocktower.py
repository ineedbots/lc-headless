"""Ported from rs2b0t's src/bot/api/ai/quests/defs/clocktower.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.game import direct_navigator, game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.engine.types import QuestModule, QuestProgress, has_flag
from rs2004.quests.exec.primitives import is_underground, walk_with_hops
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene, use_on_loc
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['COG_STAGE', 'COG_OBJ', 'parse_clock_tower_journal', 'read_clock_tower_progress', 'gather_water', 'decide', 'clocktower']

QUEST = 'Clock Tower'
COG_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'ALL_PLACED': 5, 'COMPLETE': 6})
COG_OBJ = Record({'white': 20, 'black': 21, 'blue': 22, 'red': 23})
RAT_POISON_OBJ = 24
# Why: every spindle renders "Clock spindle" and all 4 colours stand within 3 tiles on tower level 0, so only the id tells the working one from a decoy.
SPINDLE_LOC = {'red': 29, 'black': 30, 'white': 31, 'blue': 32}
LEVER_SHUT = 33
LEVER_OPEN = 35
PEN_GATE = 37
RAT_GATE = 39
FOOD_TROUGH = 40
SECRET_WALL = 1586
COLOURS = ['blue', 'black', 'white', 'red']
# Why: black is the only cog whose spindle is underground, so its round trip never climbs; white is last because its leg has to poison the rats first.
FETCH_ORDER = ['black', 'red', 'blue', 'white']
BUCKET = 'Bucket'
WATER = 'Bucket of water'
KOJO = Record({
    'npc': 'Brother Kojo',
    'anchor': Tile(2569, 3249, 0),
    'leash': 6,
    'prefer': ['OK old monk, what can I do?', 'Yes'],
})
CELLAR_TOP = Tile(2566, 3243, 0)
CELLAR_FOOT = Tile(2566, 9643, 0)
WHITE_ROOM_LADDER = Tile(2575, 9656, 0)
BLUE_ROOM_LADDER = Tile(2572, 9632, 0)
SPINDLE_STAND = {
    'red': Tile(2569, 3243, 0),
    'blue': Tile(2570, 3240, 1),
    'white': Tile(2567, 3242, 2),
    'black': Tile(2571, 9642, 0),
}
COG_SPAWN = {
    'black': Tile(2613, 9639, 0),
    'red': Tile(2583, 9613, 0),
    'blue': Tile(2574, 9633, 0),
    'white': Tile(2577, 9655, 0),
}
POISON_SPAWN = Tile(2564, 9662, 0)
# Why: z 9660 and south is the cage; the lever corridor is the single row at z 9661.
LEVER_STAND = Tile(2591, 9661, 0)
PEN_GATE_OUTSIDE = Tile(2596, 9657, 0)
PEN_GATE_INSIDE = Tile(2595, 9657, 0)
TROUGH_STAND = Tile(2585, 9654, 0)
RAT_GATE_STAND = Tile(2579, 9656, 0)
SECRET_WALL_STAND = Tile(2576, 9631, 0)
WELL_STAND = Tile(2611, 3254, 0)
BUCKET_SPAWN = Tile(2616, 3255, 0)
QUEST_BANK = Tile(2655, 3283, 0)
# Why: `crossHops` picks the nearest stand by raw distance, and from the red cog that's the sealed blue-room ladder, which loops "unreachable" forever, so the cog-room ladders are left out.
HOPS = [
    Record({'stand': CELLAR_TOP, 'loc_name': 'Ladder', 'op': 'Climb-down', 'arrive': CELLAR_FOOT}),
    Record({'stand': CELLAR_FOOT, 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': CELLAR_TOP}),
]


def all_placed():
    return set([f'placed-{c}' for c in COLOURS])


def parse_clock_tower_journal(lines):
    text = normalize_journal(lines)
    if ('quest complete!' in text):
        return QuestProgress(COG_STAGE.COMPLETE, all_placed())
    # Why: the reward page drops the 4 per-cog lines, so its own line is the only evidence they are all in.
    if ('i have placed all four cogs successfully' in text):
        return QuestProgress(COG_STAGE.ALL_PLACED, all_placed())
    if ('agreed to help him repair the clock' in text):
        flags = set()
        for colour in COLOURS:
            if (f'successfully placed the {colour} cog' in text):
                flags.add(f'placed-{colour}')
        return QuestProgress(COG_STAGE.STARTED, flags)
    if ('i can start this quest by talking to brother kojo' in text):
        return QuestProgress(COG_STAGE.NOT_STARTED, set())
    return None


def read_clock_tower_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(COG_STAGE.COMPLETE, all_placed())
    if status == 'not_started':
        return QuestProgress(COG_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(QUEST)
    progress = parse_clock_tower_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress


def in_white_room(t):
    return is_underground(t) and t.x >= 2574 and t.x <= 2578 and t.z >= 9655 and t.z <= 9658


def in_pen(t):
    return is_underground(t) and t.x >= 2579 and t.x <= 2595 and t.z >= 9652 and t.z <= 9660


def in_blue_room(t):
    return is_underground(t) and t.x >= 2571 and t.x <= 2575 and t.z >= 9630 and t.z <= 9633


POCKETS = [
    Record({'name': 'white', 'inside': in_white_room, 'stand': WHITE_ROOM_LADDER}),
    Record({'name': 'blue', 'inside': in_blue_room, 'stand': BLUE_ROOM_LADDER}),
]


# Why: a pocket ladder is only right from inside its own pocket, so the leg climbs it itself and `crossHops` never gets the choice.
def leave_pocket(log, keep=None):
    here = game.tile()
    if not here:
        return False
    pocket = ([p for p in POCKETS if p.inside(here)] or [None])[0]
    if not pocket or pocket.name == keep:
        return True
    log(f'clocktower: climbing out of the {pocket.name} cog room')
    _w2 = yield from traversal.walk_resilient(pocket.stand, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w2):
        return False
    ladder = locs.query().name('Ladder').action('Climb-up').within(4).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        log(f'clocktower: no ladder out of the {pocket.name} cog room at ({pocket.stand.x},{pocket.stand.z})')
        return False

    def _fn4():
        t = game.tile()
        return t is not None and not is_underground(t)
    _result3 = yield from execution.delay_until(_fn4, 10000)
    return _result3


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


def cog_on_floor(colour):
    return ground_items.query().where(lambda g: g.id == getattr(COG_OBJ, colour)).within(8).nearest()


def take_cog(colour, log):
    if held_id(getattr(COG_OBJ, colour)) > 0:
        return True
    cog = cog_on_floor(colour)
    if not cog:
        log(f'clocktower: no {colour} cog on the floor at ({COG_SPAWN[colour].x},{COG_SPAWN[colour].z})')
        return False
    if not (cog.interact('Take')):
        return False
    # Why: a refusal arrives as a mesbox, so the wait has to drive it shut before anything else can act.
    _result5 = yield from drive_until(lambda: held_id(getattr(COG_OBJ, colour)) > 0, [], log, 8000)
    return _result5


# Why: the cog is red hot until cooled and pouring spends the bucket, so try the Take first and let the refusal ask for the water.
def take_black_cog(log):
    _w6 = yield from take_cog('black', log)
    if _w6:
        return True
    cog = cog_on_floor('black')
    water = inventory.first(WATER)
    if not cog or not water:
        log(f'clocktower: black cog still hot and no {WATER} to cool it')
        return False
    log('clocktower: pouring water over the black cog')
    if not (water.use_on(cog)):
        return False
    _w7 = yield from drive_until(lambda: not inventory.contains(WATER), [], log, 8000)
    if not (_w7):
        log('clocktower: the water never poured')
        return False
    _result8 = yield from take_cog('black', log)
    return _result8


def open_pen_gate(log):
    if loc_by_id(LEVER_OPEN, 8):
        return True
    _w9 = yield from walk_with_hops(LEVER_STAND, 2, HOPS, log)
    if not (_w9):
        return False
    if loc_by_id(LEVER_OPEN, 8):
        return True
    lever = loc_by_id(LEVER_SHUT, 8)
    if not lever:
        log(f'clocktower: no rat-cage lever at ({LEVER_STAND.x},{LEVER_STAND.z})')
        return False
    log('clocktower: pulling the rat-cage lever')
    if not (lever.interact('Pull')):
        return False
    _result10 = yield from execution.delay_until(lambda: loc_by_id(LEVER_OPEN, 8) is not None, 6000)
    return _result10


# Why: the lever opens the gate at runtime, so the last tile is a scene step the baked pathfinder never sees.
def enter_pen(log):
    here = game.tile()
    if here and in_pen(here):
        return True
    _w11 = yield from open_pen_gate(log)
    if not (_w11):
        return False
    _w12 = yield from walk_with_hops(PEN_GATE_OUTSIDE, 0, HOPS, log)
    if not (_w12):
        return False
    yield from direct_navigator.walk_to(PEN_GATE_INSIDE, 0, 6000)
    landed = game.tile()
    if not landed or not in_pen(landed):
        log('clocktower: the rat-cage gate did not let us through')
        return False
    return True


# Why: the lever deletes the gate while holding it open, so walk out first; the Open op (`check_axis` grants it from the caged side only) is for a gate that has re-shut.
def leave_pen(log):
    def outside():
        t = game.tile()
        return t is not None and not in_pen(t)

    _w13 = yield from traversal.walk_resilient(PEN_GATE_INSIDE, radius=0, attempts=3, timeout_ms=60000, log=log)
    if not (_w13):
        return False
    yield from direct_navigator.walk_to(PEN_GATE_OUTSIDE, 0, 6000)
    if outside():
        return True
    gate = loc_by_id(PEN_GATE, 4)
    if not gate or not (gate.interact('Open')):
        log('clocktower: cannot leave the rat cage — the gate is neither open nor openable from here')
        return False
    _result14 = yield from execution.delay_until(outside, 6000)
    return _result14


# Why: the rats are map spawns on a 50-tick respawn, so counting them never says if they're poisoned; the gate's refusal is the only client-visible test.
def cross_rat_gate(log):
    _w15 = yield from traversal.walk_resilient(RAT_GATE_STAND, radius=0, attempts=3, timeout_ms=60000, log=log)
    if not (_w15):
        return False
    gate = loc_by_id(RAT_GATE, 4)
    if not gate:
        log(f'clocktower: no rat-room gate at ({RAT_GATE_STAND.x},{RAT_GATE_STAND.z})')
        return False
    if not (gate.interact('Go-through')):
        return False

    def _fn16():
        t = game.tile()
        return t is not None and in_white_room(t)
    # The gate's mesbox suspends the crossing until its continue is acknowledged.
    crossed = yield from drive_until(_fn16, [], log, 6000)
    if crossed:
        # Why: the gate teleports you, and every obj query reads blank for about a tick after the region changes.
        yield from settle_scene()
    return crossed


def take_poison(log):
    if held_id(RAT_POISON_OBJ) > 0:
        return True
    _w17 = yield from walk_with_hops(POISON_SPAWN, 2, HOPS, log)
    if not (_w17):
        return False
    poison = ground_items.query().where(lambda g: g.id == RAT_POISON_OBJ).within(8).nearest()
    if not poison:
        log(f'clocktower: no Rat poison at ({POISON_SPAWN.x},{POISON_SPAWN.z})')
        return False
    if not (poison.interact('Take')):
        return False
    _result18 = yield from execution.delay_until(lambda: held_id(RAT_POISON_OBJ) > 0, 8000)
    return _result18


def enter_white_room(log):
    here = game.tile()
    if here and in_white_room(here):
        return True
    # Why: the poison spawn is in the tower cellar, which the cage can't walk back to, so carry it in before the gate refuses.
    _c19 = not (here and in_pen(here))
    if _c19:
        _w20 = yield from take_poison(log)
        _c19 = not (_w20)
    if _c19:
        return False
    _w21 = yield from enter_pen(log)
    if not (_w21):
        return False
    _w22 = yield from cross_rat_gate(log)
    if _w22:
        return True
    if held_id(RAT_POISON_OBJ) == 0:
        log('clocktower: the rat gate is still shut and the pack holds no poison — leaving to fetch some')
        yield from leave_pen(log)
        yield from execution.delay_ticks(2)
        return False
    log('clocktower: poisoning the rats at the food trough')
    poured = yield from use_on_loc(RAT_POISON_OBJ, Record({'name': 'Food trough', 'near': TROUGH_STAND, 'id': FOOD_TROUGH}), [], lambda: held_id(RAT_POISON_OBJ) == 0, log)
    if not poured:
        return False
    _result23 = yield from cross_rat_gate(log)
    return _result23


def enter_blue_room(log):
    here = game.tile()
    if here and in_blue_room(here):
        return True
    _w24 = yield from walk_with_hops(SECRET_WALL_STAND, 1, HOPS, log)
    if not (_w24):
        return False
    wall = loc_by_id(SECRET_WALL, 4)
    if not wall:
        log(f'clocktower: no secret wall at ({SECRET_WALL_STAND.x},{SECRET_WALL_STAND.z})')
        return False
    log('clocktower: pushing the secret wall into the blue cog room')
    if not (wall.interact('Push')):
        return False

    def _fn25():
        t = game.tile()
        return t is not None and in_blue_room(t)
    _w26 = yield from execution.delay_until(_fn25, 8000)
    if not (_w26):
        return False
    yield from settle_scene()
    return True


def fetch_leg(colour):
    def _fn27(log):
        _w28 = yield from leave_pocket(log, colour)
        if not (_w28):
            return False
        if colour == 'white':
            _w29 = yield from enter_white_room(log)
            if not (_w29):
                return False
        elif colour == 'blue':
            _w30 = yield from enter_blue_room(log)
            if not (_w30):
                return False
        else:
            _w31 = yield from walk_with_hops(COG_SPAWN[colour], 2, HOPS, log)
            if not (_w31):
                return False
        if colour == 'white' or colour == 'blue':
            _w32 = yield from traversal.walk_resilient(COG_SPAWN[colour], radius=1, attempts=3, timeout_ms=60000, log=log)
            if not (_w32):
                return False
        result = yield from (take_black_cog(log) if colour == 'black' else take_cog(colour, log))
        return result
    return _fn27


def place_leg(colour):
    def place(log):
        cog_colour = colour
        _w34 = yield from leave_pocket(log)
        if not (_w34):
            return False
        _w35 = yield from walk_with_hops(SPINDLE_STAND[cog_colour], 1, HOPS, log)
        if not (_w35):
            return False
        log(f'clocktower: fitting the {cog_colour} cog to its spindle')
        _result36 = yield from use_on_loc(getattr(COG_OBJ, cog_colour), Record({'name': 'Clock spindle', 'near': SPINDLE_STAND[cog_colour], 'id': SPINDLE_LOC[cog_colour], 'within': 4}), [], lambda: held_id(getattr(COG_OBJ, cog_colour)) == 0, log)
        return _result36
    return place


def held_cog(snap):
    for colour in FETCH_ORDER:
        _v37 = (snap.inv_ids or {}).get(getattr(COG_OBJ, colour))
        if ((_v37 if _v37 is not None else 0)) > 0:
            return colour
    return None


# Why: one ground spawn is the only bucket near the tower and no Ardougne shop stocks one, so check the bank first; a taken spawn spins the step until it respawns.
def gather_water(snap):
    if not (BUCKET.lower() in snap.inv):
        if snap.bank_known != True:
            return Record({'kind': 'scan_bank'})
        _v38 = (snap.bank or {}).get(BUCKET.lower())
        if ((_v38 if _v38 is not None else 0)) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': BUCKET, 'qty': 1}]})
        return Record({'kind': 'grab_ground', 'item': BUCKET, 'anchor': BUCKET_SPAWN, 'wait_if_missing': True})
    return Record({
        'kind': 'use_on',
        'item': BUCKET,
        'target_kind': 'loc',
        'target': 'Well',
        'anchor': WELL_STAND,
        'product': WATER,
    })


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': KOJO})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': 'Clock Tower journal stage unavailable'})
    held = held_cog(snap)
    if held is not None:
        if has_flag(progress, f'placed-{held}'):
            return Record({'kind': 'wait', 'reason': f'carrying a {held} cog whose spindle is already filled'})
        return Record({'kind': 'custom', 'name': f'place the {held} cog', 'run': place_leg(held)})
    next_ = ([colour for colour in FETCH_ORDER if not has_flag(progress, f'placed-{colour}')] or [None])[0]
    if next_ is None:
        return Record({'kind': 'talk', 'stop': KOJO})
    if next_ == 'black' and not (WATER.lower() in snap.inv):
        return gather_water(snap)
    return Record({'kind': 'custom', 'name': f'fetch the {next_} cog', 'run': fetch_leg(next_)})


clocktower = QuestModule(
    record=quest_record('cog'),
    resume_at=lambda tile: in_white_room(tile) or in_blue_room(tile) or in_pen(tile),
    bank=QUEST_BANK,
    hops=HOPS,
    tools=['cog', 'rat poison', 'bucket', 'bucket of water'],
    read_progress=read_clock_tower_progress,
    decide=decide,
)

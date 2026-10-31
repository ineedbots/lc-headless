"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dwarfcannon/repair.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import ground_items, locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.dwarfcannon.areas import CANNON_PARTS, CAVE_HOPS, DWARF_CHILD, MC_LOC, MC_OBJ, MC_TILE, RAILINGS
from rs2004.quests.exec.primitives import is_underground, talk_through, walk_with_hops
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.traversal import traversal

__all__ = ['walk_to', 'fix_railings', 'fetch_remains', 'in_cave', 'rescue_child', 'CANNON_CYCLE', 'cannon_outcome', 'repair_cannon']

def walk_to(tile, radius, log):
    here = game.tile()
    if here and here.level == tile.level and tile.distance_to(here) <= radius:
        return True
    _result1 = yield from traversal.walk_resilient(tile, radius=radius, attempts=3, timeout_ms=180000, log=log)
    return _result1


# Why: the content sets a `%mcannonmulti` bit and leaves the loc alone, so nothing in the scene tells a fixed railing from a broken one; the message is the only oracle.
RAILING_DONE = lambda text: 'already fixed this railing' in text.lower() or 'replace the railing with no problems' in text.lower()
# Why: `stat_random` can refuse below max Crafting, and the refusal only costs a few hitpoints, so repeat the attempt.
RAILING_FAILED = 'fail and cut yourself trying'


def fix_one(entry, log):
    """Repair one railing; true when it is fixed or was already."""
    _w3 = yield from walk_to(entry.at, 2, log)
    if not (_w3):
        return False
    for attempt in range(6):
        yield from settle_scene()
        railing = locs.query().where(lambda l: l.id == entry.id).nearest()
        if not railing:
            log(f'no railing loc {entry.id} at ({entry.at.x},{entry.at.z})')
            return False
        mark = game_messages.mark()
        if not (railing.interact('Inspect')):
            return False
        yield from drive_until(lambda: game_messages.saw_since(mark, RAILING_DONE) or game_messages.saw_since(mark, RAILING_FAILED), ['Try to replace the railing.'], log, 20000)
        if game_messages.saw_since(mark, RAILING_DONE):
            return True
        yield from execution.delay_ticks(1)
    return False


def fix_railings(log):
    """Walk the 6 broken railings in order and replace each."""
    for entry in RAILINGS:
        _w4 = yield from fix_one(entry, log)
        if not (_w4):
            log(f'railing {entry.id} did not take — moving on and letting the journal decide')
        yield from execution.delay_ticks(1)
    return True


# Why: `needsHop` is a z >= 5000 test, so `crossHops` never fires for the tower.
# Why: `~climb_ladder` passes `movecoord(coord(), 0, 1, 0)`, so the landing is your own tile 1 level up, and the tile above each ladder loc is blocked by the ladder.
def climb(stand, op, to_level, log):
    """Climb one ladder from a stand beside it and wait for the level to change."""
    _w5 = yield from walk_to(stand, 1, log)
    if not (_w5):
        return False
    yield from settle_scene()
    ladder = locs.query().name('Ladder').action(op).within(4).nearest()
    if not ladder:
        log(f'no Ladder offering \'{op}\' at ({stand.x},{stand.z},{stand.level})')
        return False
    if not (ladder.interact(op)):
        return False
    _result6 = yield from execution.delay_until(lambda: (game.tile().level if game.tile() is not None else None) == to_level, 8000)
    return _result6


# Why: neither tower ladder carries a usable transports edge in either direction, so a step that climbs up and stops leaves the walker on a floor it can never route off.
def leave_tower(log):
    """Climb back down to ground level from wherever in the tower we are."""
    _v8 = (game.tile().level if game.tile() is not None else None)
    _c7 = ((_v8 if _v8 is not None else 0)) == 2
    if _c7:
        _w9 = yield from climb(MC_TILE.TOWER_L2_DOWN, 'Climb-down', 1, log)
        _c7 = not (_w9)
    if _c7:
        return False
    _v11 = (game.tile().level if game.tile() is not None else None)
    _c10 = ((_v11 if _v11 is not None else 0)) == 1
    if _c10:
        _w12 = yield from climb(MC_TILE.TOWER_L1_DOWN, 'Climb-down', 0, log)
        _c10 = not (_w12)
    if _c10:
        return False
    _v13 = (game.tile().level if game.tile() is not None else None)
    return ((_v13 if _v13 is not None else 0)) == 0


def fetch_remains(log):
    """Climb the Black Guard watchtower, take the dwarf remains, and come back down."""
    if inventory.contains(MC_OBJ.REMAINS.name):
        _result14 = yield from leave_tower(log)
        return _result14
    _v16 = (game.tile().level if game.tile() is not None else None)
    _c15 = ((_v16 if _v16 is not None else 0)) == 0
    if _c15:
        _w17 = yield from climb(MC_TILE.TOWER_LADDER, 'Climb-up', 1, log)
        _c15 = not (_w17)
    if _c15:
        return False
    _v19 = (game.tile().level if game.tile() is not None else None)
    _c18 = ((_v19 if _v19 is not None else 0)) == 1
    if _c18:
        _w20 = yield from climb(MC_TILE.TOWER_L1_LADDER, 'Climb-up', 2, log)
        _c18 = not (_w20)
    if _c18:
        return False
    _w21 = yield from walk_to(MC_TILE.REMAINS, 2, log)
    if not (_w21):
        return False
    yield from settle_scene()
    drop = ground_items.query().name(MC_OBJ.REMAINS.name).within(8).nearest()
    if not drop:
        log('no Dwarf remains on the tower floor')
        return False
    if not (drop.interact('Take')):
        return False
    _w22 = yield from execution.delay_until(lambda: inventory.contains(MC_OBJ.REMAINS.name), 8000)
    if not (_w22):
        return False
    _result23 = yield from leave_tower(log)
    return _result23


def in_cave(tile):
    return (is_underground(tile) if tile else False)


# Why: no transports edge carries either telejump, so findPath calls the cave unreachable from outside and the mainland from inside; the module's own hops are the only crossing.
def rescue_child(rescued, log):
    """Enter the goblin cave, free Gilob's son from the crate, and leave by the mud pile."""
    if rescued:
        _result24 = yield from walk_with_hops(MC_TILE.COMMANDER, 4, list(CAVE_HOPS), log)
        return _result24
    _c25 = not in_cave(game.tile())
    if _c25:
        _w26 = yield from walk_with_hops(MC_TILE.CAVE_ARRIVE, 6, list(CAVE_HOPS), log)
        _c25 = not (_w26)
    if _c25:
        return False
    _w27 = yield from walk_to(MC_TILE.CRATE, 2, log)
    if not (_w27):
        return False
    yield from settle_scene()
    crate = locs.query().where(lambda l: l.id == MC_LOC.CRATE).nearest()
    if not crate:
        log(f'no crate loc {MC_LOC.CRATE} at ({MC_TILE.CRATE.x},{MC_TILE.CRATE.z})')
        return False
    if not (crate.interact('Search')):
        return False
    # The crate spawns the youngster and opens his dialogue in one script, and its last line sets the stage, so drain it.
    yield from execution.delay_ticks(2)
    yield from talk_through(DWARF_CHILD.npc, DWARF_CHILD.prefer, log)
    return True


# Why: only `mes` lines reach GameMessages and the "working order" line is a `~chatplayer` dialogue, so the stage reaching 8 is the terminal oracle and the next decide() reads it.
# Why: `oploc1` only falls to its else branch and this line when %mcannon is neither 6 nor 7, so it's the one client-visible proof the repair is over.
CANNON_DONE = 'strange dwarf contraption'
CANNON_FIXED = 'manage to fix it'
CANNON_ALREADY = 'already fixed this part'
CYCLE_LINES = ['manage to fix it', 'already fixed this part', 'too hard you fail to fix', "can't quite find the problem", 'strange dwarf contraption']
CANNON_CYCLE = lambda text: any([line in text.lower() for line in CYCLE_LINES])
OUTCOMES = [[CANNON_DONE, 'done'], [CANNON_FIXED, 'fixed'], [CANNON_ALREADY, 'already']]


def cannon_outcome(text):
    """Classify one Inspect's message; anything else is worth another Inspect."""
    hit = ([entry for entry in OUTCOMES if entry[0] in text.lower()] or [None])[0]
    return hit[1] if hit is not None else 'retry'


# Why: the repair menu offers all 5 components on every Inspect, so a preference list re-picks its first entry forever and every later pass answers "You've already fixed this part of the cannon."
def inspect_for(part, log):
    """Inspect once and answer for one named component; `null` drives no menu."""
    yield from settle_scene()
    cannon = locs.query().where(lambda l: l.id == MC_LOC.BROKEN_CANNON).nearest()
    if not cannon:
        log(f'no broken cannon loc {MC_LOC.BROKEN_CANNON} in the shed')
        return 'retry'
    mark = game_messages.mark()
    if not (cannon.interact('Inspect')):
        return 'retry'
    yield from drive_until(lambda: game_messages.saw_since(mark, CANNON_CYCLE), (['None'] if part is None else [part]), log, 8000)
    hit = ([entry for entry in OUTCOMES if game_messages.saw_since(mark, entry[0])] or [None])[0]
    return hit[1] if hit is not None else 'retry'


def repair_cannon(log):
    """Repair all 4 damaged components, then Inspect once more to close the stage."""
    _w32 = yield from walk_to(MC_TILE.CANNON, 2, log)
    if not (_w32):
        return False
    for part in CANNON_PARTS:
        for attempt in range(5):
            outcome = yield from inspect_for(part, log)
            if outcome == 'done':
                log('the cannon is repaired and the stage has moved on — leaving the loop')
                return True
            if outcome != 'retry':
                log(f'{part.lower()}: {outcome}')
                break
            yield from execution.delay_ticks(1)
    # Why: the 4th component leaves the stage at 7; the Inspect after it, finding all 4 bits set, flips it to 8.
    yield from inspect_for(None, log)
    return True

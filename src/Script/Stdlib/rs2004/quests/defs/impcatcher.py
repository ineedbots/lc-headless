"""Ported from rs2b0t's src/bot/api/ai/quests/defs/impcatcher.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
import random as _random
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import QuestModule
from rs2004.traversal import traversal


__all__ = ['IMP_BEADS', 'MIZGOG', 'IMP_SPAWNS', 'IMP_STAND', 'IMP_FIELD', 'search_target', 'idle_progress', 'nearest_reachable', 'pick_imp', 'tally_names', 'imp_census', 'gather_bead', 'decide', 'impcatcher']

IMP_BEADS = [
    Record({'name': 'Red bead', 'id': 1470}),
    Record({'name': 'Yellow bead', 'id': 1472}),
    Record({'name': 'Black bead', 'id': 1474}),
    Record({'name': 'White bead', 'id': 1476}),
]
# Why: Mizgog's third option ends with "Give me a quest!", so a substring match on that alone clicks the sarcastic branch; the polite line goes first.
MIZGOG = Record({
    'npc': 'Wizard Mizgog',
    'anchor': Tile(3103, 3163, 2),
    'leash': 6,
    'prefer': ['Give me a quest please.', 'Give me a quest!'],
})
IMP_SPAWNS = [
    Tile(2632, 3202, 0),
    Tile(2625, 3203, 0),
    Tile(2639, 3206, 0),
    Tile(2630, 3210, 0),
    Tile(2625, 3217, 0),
    Tile(2633, 3222, 0),
    Tile(2639, 3230, 0),
    Tile(2629, 3233, 0),
    Tile(2633, 3243, 0),
]
FIELD_LEVEL = 0
# Why: the 9 spawns lie in a 14x41 strip, so this tile is within 21 of every one and inside `SEARCH_RADIUS` of the lot.
IMP_STAND = Tile(2632, 3222, 0)
# Why: the strip-to-tower route crosses Karamja, which has no bank, so a coin top-up there walks the bot off its route.
KARAMJA = Record({'min_x': 2740, 'max_x': 2970, 'min_z': 3020, 'max_z': 3230})
SHIP_FARE = 30
COIN_RESERVE = 200
COIN_FLOOR = SHIP_FARE * 2
# Why: `wanderrange=27` plus a `map_findsquare(npc_coord, 0, 20)` teleport puts an imp anywhere in this box; one outside it is another cluster's.
# Why: the z 3180 floor keeps the next cluster south (tops out at z 3134) from pulling the bot 70 tiles off this one.
IMP_FIELD = Record({'min_x': 2600, 'max_x': 2665, 'min_z': 3180, 'max_z': 3265})
IMP = 'Imp'
SEARCH_RADIUS = 50
BEAD_RADIUS = 30
ENGAGE_RADIUS = 6
LOST_RADIUS = 12
REACH_STEPS = 20000
# Why: imps wander and teleport far enough that standing still watches empty ground, so an idle bot sweeps the strip.
SEARCH_IDLE_MS = 6000
SEARCH_STEP_MIN = 8
SEARCH_STEP_MAX = 20
SEARCH_ROLLS = 6
KILL_MS = 30000
TAKE_MS = 6000
FAR_WALK_MS = 420000
SWEEP_WALK_MS = 45000


def held_count(snap, bead):
    if snap.inv_ids is not None and len(snap.inv_ids) > 0:
        _v1 = (snap.inv_ids or {}).get(bead.id)
        return (_v1 if _v1 is not None else 0)
    _v2 = snap.inv.get(bead.name.lower())
    return (_v2 if _v2 is not None else 0)


def banked_count(snap, bead):
    if snap.bank_ids is not None and len(snap.bank_ids) > 0:
        _v3 = (snap.bank_ids or {}).get(bead.id)
        return (_v3 if _v3 is not None else 0)
    _v4 = (snap.bank or {}).get(bead.name.lower())
    return (_v4 if _v4 is not None else 0)


def missing_beads(snap):
    return [bead for bead in IMP_BEADS if held_count(snap, bead) == 0]


def in_field(tile):
    return tile.level == FIELD_LEVEL and tile.x >= IMP_FIELD.min_x and tile.x <= IMP_FIELD.max_x and tile.z >= IMP_FIELD.min_z and tile.z <= IMP_FIELD.max_z


def clamp(value, low, high):
    return min(high, max(low, value))


# Why: a random point in the box bounces the bot across the strip; a random heading from here sweeps ground it hasn't looked at yet.
# Why: the field rectangle knows no terrain, so a heading can aim at an unreachable tile; 1 sweep in 6 burned 42s on one.
def search_target(here, random, reachable=None):
    """A tile to sweep towards: a random heading from `here`, held inside the field and probed for reach."""
    if not here or not in_field(here):
        return IMP_STAND
    for roll in range(SEARCH_ROLLS):
        heading = random() * 2 * math.pi
        stride = SEARCH_STEP_MIN + random() * (SEARCH_STEP_MAX - SEARCH_STEP_MIN)
        target = Tile(clamp(round(here.x + math.cos(heading) * stride), IMP_FIELD.min_x, IMP_FIELD.max_x), clamp(round(here.z + math.sin(heading) * stride), IMP_FIELD.min_z, IMP_FIELD.max_z), FIELD_LEVEL)
        if not reachable or reachable(target):
            return target
    return IMP_STAND


# Why: Returning success without available work loops this step at about 20 ms until the watchdog stops it.
# Why: in-combat is one such condition (an imp `pickImp` refuses can hold it forever), so it's left out.
def idle_progress(target, event_pending):
    """Whether the idle wait found something for the next tick to act on."""
    return target is not None and not event_pending


def wanted_bead_ids():
    return set([bead.id for bead in [bead for bead in IMP_BEADS if inventory.count_by_id(bead.id) == 0]])


# Why: Imps teleport up to 20 tiles and may die behind scenery, so skip unreachable drops without consuming the step budget.
def nearest_reachable(candidates, reachable):
    """The closest drop the scene can path to."""
    _v5 = ([item for item in sorted(list(candidates), key=lambda a: a.distance) if reachable(item.tile)] or [None])[0]
    return (_v5 if _v5 is not None else None)


def shuffled(items, random):
    out = list(items)
    for i in range(len(out) - 1, 0, -1):
        j = math.floor(random() * (i + 1))
        out[i], out[j] = [out[j], out[i]]
    return out


# Why: 20 bots each taking the nearest imp queue on the same one, so the target is drawn at random.
# Why: first reachable of a shuffled list is the same uniform pick as filter-then-choose and usually costs a single scene BFS where a filter costs 1 per candidate.
def pick_imp(candidates, reachable, random=None):
    """A random imp in the field that nobody else is fighting and the scene can path to."""
    if random is None:
        random = _random.random
    free = [imp for imp in candidates if in_field(imp.tile) and not imp.contested]
    _v6 = ([imp for imp in shuffled(free, random) if reachable(imp.tile)] or [None])[0]
    return (_v6 if _v6 is not None else None)


# Why: zero imps looks the same whether a filter ate them, the spawns are dead or the zone never streamed, and each has a different fix.
def tally_names(names):
    """NPC names in the scene, counted, most numerous first."""
    if len(names) == 0:
        return 'nothing'
    counts = {}
    for name in names:
        key = (name if name is not None else '?')
        _v7 = counts.get(key)
        counts[key] = ((_v7 if _v7 is not None else 0)) + 1

    return ', '.join([((f'{name} x{count}' if count > 1 else name)) for name, count in sorted(list(counts.items()), key=lambda row: (-row[1], row[0]))])


def imp_census(candidates, reachable):
    """How many imps survive each filter, for the log line when none does."""
    inside = [imp for imp in candidates if in_field(imp.tile)]
    free = [imp for imp in inside if not imp.contested]
    refused = [imp.distance for imp in [imp for imp in free if not reachable(imp.tile)]]
    return Record({
        'scene': len(candidates),
        'in_field': len(inside),
        'free': len(free),
        'reachable': len(free) - len(refused),
        'nearest_refused': (None if len(refused) == 0 else min(refused)),
    })


def scene_reachable(tile):
    return reachability.can_reach(tile, adjacent_ok=True, max_steps=REACH_STEPS)


def bead_on_ground(wanted):
    drops = ground_items.query().where(lambda item: (item.id in wanted)).action('Take').within(BEAD_RADIUS).results()
    _v11 = (nearest_reachable([(Record({'item': drop, 'tile': drop.tile(), 'distance': drop.distance()})) for drop in drops], scene_reachable).item if nearest_reachable([(Record({'item': drop, 'tile': drop.tile(), 'distance': drop.distance()})) for drop in drops], scene_reachable) is not None else None)
    return (_v11 if _v11 is not None else None)


def imp_candidates():
    return [(Record({
        'item': npc,
        'index': npc.index,
        'tile': npc.tile(),
        'distance': npc.distance(),
        'contested': npc.targets_another_player(),
    })) for npc in npcs.query().name(IMP).action('Attack').within(SEARCH_RADIUS).results()]


def take_bead(bead, log):
    if inventory.free() == 0:
        log('the pack is full, so a dropped bead cannot be taken')
        return False
    id = bead.id
    where = bead.tile()
    _c12 = bead.distance() > 1
    if _c12:
        _w13 = yield from traversal.walk_resilient(where, radius=1, attempts=2, timeout_ms=60000, log=log)
        _c12 = not (_w13)
    if _c12:
        return False
    drop = ground_items.query().where(lambda item: item.id == id).action('Take').within(BEAD_RADIUS).nearest()
    if not drop:
        log(f'the {(bead.name if bead.name is not None else id)} at ({where.x},{where.z}) was taken by someone else')
        return False
    before = inventory.count_by_id(id)
    if not (drop.interact('Take')):
        return False
    took = yield from execution.delay_until(lambda: inventory.count_by_id(id) > before, TAKE_MS)
    if took:
        log(f'picked up {(drop.name if drop.name is not None else id)}')
    return took


def kill_imp(imp, log):
    index = imp.index

    def live():
        return (([npc for npc in npcs.all() if npc.index == index and npc.name == IMP] or [None])[0] if ([npc for npc in npcs.all() if npc.index == index and npc.name == IMP] or [None])[0] is not None else None)

    _c14 = imp.distance() > ENGAGE_RADIUS
    if _c14:
        _w15 = yield from traversal.walk_resilient(imp.tile(), radius=2, attempts=2, timeout_ms=90000, log=log)
        _c14 = not (_w15)
    if _c14:
        return False
    target = live()
    if not target:
        return False
    if not (target.interact('Attack')):
        log(f'Attack on imp {index} was rejected')
        return False
    # Why: `ai_queue2,imp` rolls a 1-in-10 teleport on every hit the imp survives, so a fight that stalls is normal.
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline:
        yield from sustain.run()
        if event_signal.pending():
            return False
        npc = live()
        if not npc:
            log(f'imp {index} died')
            return True
        if npc.distance() > LOST_RADIUS:
            log(f'imp {index} teleported out of the fight')
            return False
        if npc.targets_another_player():
            log(f'imp {index} was taken over by another player')
            return False
        yield from execution.delay_ticks(1)
    log(f'imp {index} outlived {KILL_MS / 1000}s of combat')
    return False


# Why: the volcano blocks the middle, so standing still watches one arc; walking the ring is the respawn wait.
def search_for_imps(census, log):
    here = game.tile()
    neighbours = (f' · scene holds {tally_names([npc.name for npc in npcs.query().within(SEARCH_RADIUS).results()])}' if census.scene == 0 else '')
    seen = f'no imp to fight within {SEARCH_RADIUS} tiles' + f' ({census.scene} in scene, {census.in_field} in the field, {census.free} free, {census.reachable} reachable' + f"{('' if census.nearest_refused is None else f', closest refused {census.nearest_refused} tiles off')}){neighbours}"
    if not here or not in_field(here):
        log(f'{seen} — walking to the south-Ardougne strip at ({IMP_STAND.x},{IMP_STAND.z})')
        _result16 = yield from traversal.walk_resilient(IMP_STAND, radius=2, attempts=3, timeout_ms=FAR_WALK_MS, log=log)
        return _result16
    # Why: a short wait catches an imp about to respawn or wander in, cheaper than a walk.
    yield from execution.delay_until(lambda: pick_imp(imp_candidates(), scene_reachable) is not None or event_signal.pending(), SEARCH_IDLE_MS)
    if idle_progress(pick_imp(imp_candidates(), scene_reachable), event_signal.pending()):
        return True
    target = search_target(here, _random.random, scene_reachable)
    log(f'{seen} — sweeping to ({target.x},{target.z})')
    _result17 = yield from traversal.walk_resilient(target, radius=2, attempts=2, timeout_ms=SWEEP_WALK_MS, log=log)
    return _result17


def farm_beads(log):
    """One unit of bead farming: take a drop, kill an imp, or close on the field."""
    wanted = wanted_bead_ids()
    if len(wanted) == 0:
        return True
    bead = bead_on_ground(wanted)
    if bead:
        _result18 = yield from take_bead(bead, log)
        return _result18
    candidates = imp_candidates()
    imp = pick_imp(candidates, scene_reachable)
    if imp:
        _result19 = yield from kill_imp(imp.item, log)
        return _result19
    _result20 = yield from search_for_imps(imp_census(candidates, scene_reachable), log)
    return _result20


def on_karamja(tile):
    return tile is not None and tile is not None and tile.x >= KARAMJA.min_x and tile.x <= KARAMJA.max_x and tile.z >= KARAMJA.min_z and tile.z <= KARAMJA.max_z


BEAD_IDS = [bead.id for bead in IMP_BEADS]


def gather_bead(snap, need=1):
    missing = missing_beads(snap)
    if len(missing) == 0:
        return Record({'kind': 'wait', 'reason': 'every bead is already held'})
    # Why: an unread bank may hold a bead from an earlier run, which is 50 imp kills cheaper than farming another.
    if not snap.bank_known:
        return Record({'kind': 'scan_bank'})
    if snap.free_slots is not None and snap.free_slots < len(missing):
        return Record({'kind': 'deposit', 'keep': ['coins'], 'keep_ids': BEAD_IDS, 'exact_keep': True})
    banked = [bead for bead in missing if banked_count(snap, bead) > 0]
    if len(banked) > 0:
        return Record({
            'kind': 'withdraw',
            'items': [({'name': bead.name, 'id': bead.id, 'qty': 1}) for bead in banked],
        })
    # Why: fetch the fare before boarding; a top-up on Karamja sails home for coins and never kills an imp.
    _v21 = snap.inv.get('coins')
    coins = (_v21 if _v21 is not None else 0)
    if coins < COIN_FLOOR and not on_karamja(snap.tile) and snap.bank_coins > 0:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': 'Coins', 'qty': min(COIN_RESERVE - coins, snap.bank_coins)}],
        })
    return Record({
        'kind': 'custom',
        'name': f"kill imps for {', '.join([bead.name for bead in missing])}",
        'run': farm_beads,
    })


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    # Why: the imp drop table is unconditional, so beads can be farmed before talking to Mizgog.
    # Why: the strip is 625 of walking and 2 ship fares from him, so gathering first pays that once.
    if len(missing_beads(snap)) > 0:
        return gather_bead(snap)
    return Record({'kind': 'talk', 'stop': MIZGOG})


impcatcher = QuestModule(**{
    'record': ([record for record in QUESTS if record.id == 'imp'] or [None])[0],
    'bank': 'nearest',
    'owns_inventory': True,
    'grind': [IMP],
    'gather': {_k: _v for _k, _v in [[bead.name.lower(), gather_bead] for bead in IMP_BEADS]},
    'decide': decide,
})

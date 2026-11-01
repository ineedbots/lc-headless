"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/pockets.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.regicide.seams import REGICIDE_POCKETS, REGICIDE_SEAMS
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['ARDOUGNE', 'FOREST_STAGE', 'GATE_STAGE', 'pocket_at', 'plan_route', 'climb_out_of_pit', 'travel_tirannwn']

ARDOUGNE = 'ardougne'
# Why: `%regicide_quest < ^regicide_spoken_tracker2` refuses every Dense forest with "You can see no way to get past this", and `arandar_gate` refuses southbound until the deed is reported.
FOREST_STAGE = 8
GATE_STAGE = 13
by_z = {}
for pocket in REGICIDE_POCKETS:
    for z, x0, x1 in pocket.spans:
        _v1 = by_z.get(z)
        row = (_v1 if _v1 is not None else [])
        row.append(Record({'pocket': pocket.name, 'x0': x0, 'x1': x1}))
        by_z[z] = row


def pocket_at(tile):
    """Which pocket a Tirannwn tile sits in, or undefined for anything the palisade doesn't seal in."""
    if not tile or tile.level != 0:
        return None
    for span in by_z.get(tile.z, []):
        if tile.x >= span.x0 and tile.x <= span.x1:
            return span.pocket
    return None


def usable(seam, from_, stage):
    if seam.kind == 'forest':
        return stage >= FOREST_STAGE
    # Why: the palisade opens northbound at any stage, `coordz(coord) < coordz(loc_coord)` being the only test on the way out, and southbound once Iorwerth has been told the deed is done.
    if seam.kind == 'gate':
        return from_ != ARDOUGNE or stage >= GATE_STAGE
    return True


def plan_route(from_, to, stage):
    """The chain of crossings from one pocket to another, or null when the quest stage seals every route."""
    if from_ == to:
        return []
    prev = {}
    queue = [from_]
    seen = set([from_])
    while len(queue) > 0:
        at = queue.pop(0)
        if at == to:
            legs = []
            cursor = to
            while cursor != from_:
                leg = prev.get(cursor)
                legs.insert(0, leg)
                cursor = leg.from_.pocket
            return legs
        for seam in REGICIDE_SEAMS:
            here = (((seam.sides[0] if seam.sides[0].pocket == at else None)) if seam.directed else ([side for side in seam.sides if side.pocket == at] or [None])[0])
            if here is None or not usable(seam, at, stage):
                continue
            for other in seam.sides:
                if other.pocket == at or (other.pocket in seen):
                    continue
                seen.add(other.pocket)
                prev[other.pocket] = Record({'seam': seam, 'from_': here, 'to': other})
                queue.append(other.pocket)
    return None


CROSS_MS = 10000
MAX_LEGS = 40
# Why: the pitfall, the tripwire and the sticks all roll `stat_random(agility, ...)` and a fail leaves you where you were or in the pit below, so one send is one roll.
# Why: 8 because the sticks roll `stat_random(agility, 30, 155)`, under a coin flip even at 70, and a 4-try budget fails the leg outright about 1 run in 10.
CROSS_TRIES = 8
STAND_TRIES = 3
STAND_MS = 45000
# Why: a crossing's bank is metres away inside the same pocket, so the walk to it stays out of the transport graph; left open, the navigator answered a blocked gate stand with a ship to Karamja.
LOCAL_WALK = {'use_teleport_catalog': False, 'policy': {'use_teleports': False}}
CROSS_FAILS = 3
HAND_HOLDS = 3927


def walk_with(dest, radius, attempts, timeout_ms, log, options):
    """A resilient walk with a leg's own routing options, which are walk_resilient's keywords."""
    fields = {'radius': radius, 'attempts': attempts, 'timeout_ms': timeout_ms, 'log': log}
    for key, value in options.items():
        fields[key] = value
    return traversal.walk_resilient(dest, **fields)


# Why: `pocketAt` returns undefined outside Tirannwn, while the graph calls that region ARDOUGNE; normalize them before checking arrival.
def standing_in():
    _v2 = pocket_at(game.tile())
    return (_v2 if _v2 is not None else ARDOUGNE)


def seam_loc(seam):
    return locs.query().where(lambda loc: loc.id == seam.loc_id and abs(loc.tile().x - seam.x) <= 1 and abs(loc.tile().z - seam.z) <= 1).within(12).nearest()


def climb_out_of_pit(log):
    """Climb out of a spike pit, back to the forest floor beside it. Why: a failed pitfall jump teleports you into mapsquare 36_150 with 15 damage and the protruding rocks are the only loc there, so every other leg reads "unreachable" until this has run."""
    rocks = locs.query().where(lambda loc: loc.id == HAND_HOLDS).action('Climb').within(24).nearest()
    if not rocks:
        log('fell into a spike pit with no protruding rocks in reach')
        return False
    if not (rocks.interact('Climb')):
        return False
    out = yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9000, CROSS_MS)
    if out:
        now = game.tile()
        log(f'climbed out of the pit at ({(now.x if now is not None else None)},{(now.z if now is not None else None)})')
    return out


def cross_seam(leg, log, options):
    """Cross one seam. True only once the pocket has changed. Why: the op walks you before its script resolves and the pitfall's agility roll drops a failure into a spike pit, both of which look like movement, so the pocket is the only signal. `regicide_move_trap_woodspring` p_walks a failed sticks roll to a tile beside the loc, sometimes the far side of the barrier, so a failure spends an attempt inside the loop and keeps the crossing."""
    stand = Tile(leg.from_.stand.x, leg.from_.stand.z, 0)
    walk_fails = 0
    for attempt in range(CROSS_TRIES):
        if standing_in() == leg.to.pocket:
            return True
        _v4 = (game.tile().z if game.tile() is not None else None)
        _c3 = ((_v4 if _v4 is not None else 0)) > 9000
        if _c3:
            _w5 = yield from climb_out_of_pit(log)
            _c3 = not (_w5)
        if _c3:
            return False
        # Why: a failed jump is 15 damage and a fall, the tripwires poison and the sticks hit for 8, so a crossing retried 8 times is a fight the walk between attempts can't pay for.
        yield from sustain.run()
        _w7 = yield from walk_with(stand, 1, 3, STAND_MS, log, options if leg.from_.pocket == ARDOUGNE else LOCAL_WALK)
        if not (_w7):
            # Why: bounded separately from the roll budget, because a walk that can't answer burns its full timeout every attempt while a failed roll costs a couple of ticks.
            walk_fails += 1
            if walk_fails >= STAND_TRIES:
                log(f'could not stand at ({stand.x},{stand.z}) to take {leg.seam.op} {leg.seam.loc} after {walk_fails} tries')
                return False
            log(f'could not stand at ({stand.x},{stand.z}) — retrying from ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)})')
            continue
        yield from settle_scene()
        loc = seam_loc(leg.seam)
        if not loc:
            log(f'no {leg.seam.loc} at ({leg.seam.x},{leg.seam.z}) — retrying')
            continue
        if not (loc.interact(leg.seam.op)):
            continue
        _w8 = yield from execution.delay_until(lambda: standing_in() == leg.to.pocket, CROSS_MS)
        if _w8:
            now = game.tile()
            log(f'{leg.seam.op} {leg.seam.loc} → {leg.to.pocket} ({(now.x if now is not None else None)},{(now.z if now is not None else None)})')
            return True
        now = game.tile()
        log(f'{leg.seam.op} {leg.seam.loc} @({leg.seam.x},{leg.seam.z}) left us at ({(now.x if now is not None else None)},{(now.z if now is not None else None)}) — retrying')
    log(f'{CROSS_TRIES} tries at {leg.seam.op} {leg.seam.loc} without reaching {leg.to.pocket}')
    return False


def travel_tirannwn(dest, radius, stage, log, options=None):
    """Walk to `dest`, crossing whatever seals its pocket off from this one. Why: a component report over the quest's anchors fails every pair inside Tirannwn, so a plain `walkResilient` reports "unreachable" for anything past a crossing. Inside one pocket the navigator is still the right tool, so each round tries it."""
    if options is None:
        options = {}
    cross_fails = 0
    for hop in range(MAX_LEGS):
        here = game.tile()
        if here and here.level == dest.level and dest.distance_to(here) <= radius:
            return True
        _v10 = (here.z if here is not None else None)
        _c9 = ((_v10 if _v10 is not None else 0)) > 9000
        if _c9:
            _w11 = yield from climb_out_of_pit(log)
            _c9 = not (_w11)
        if _c9:
            return False
        _v12 = pocket_at(game.tile())
        from_ = (_v12 if _v12 is not None else ARDOUGNE)
        _v13 = pocket_at(dest)
        to = (_v13 if _v13 is not None else ARDOUGNE)
        if from_ == to:
            _result14 = yield from walk_with(dest, radius, 3, 180000, log, options if from_ == ARDOUGNE else LOCAL_WALK)
            return _result14
        route = plan_route(from_, to, stage)
        if route is None or len(route) == 0:
            # Why: the seam graph is derived from the collision pack and the pathfinder's edges, so it's the conservative half of what the live walker can do and can't see a door the derivation had no reason to trust. Where it has no chain, ask the navigator before giving up.
            log(f'no crossing chain from {from_} to {to} at stage {stage} — asking the navigator')
            _result16 = yield from walk_with(dest, radius, 2, 180000, log, options if from_ == ARDOUGNE else LOCAL_WALK)
            return _result16
        _w18 = yield from cross_seam(route[0], log, options)
        if not (_w18):
            # Why: a trap that refused the crossing has usually moved you, sometimes into a different pocket, so the next round replans from the new tile, where the leg's route may still be open.
            cross_fails += 1
            if cross_fails >= CROSS_FAILS:
                log(f'{cross_fails} crossings refused on the way to ({dest.x},{dest.z}) — giving up')
                return False
            _v19 = pocket_at(game.tile())
            log(f'crossing {route[0].seam.loc} refused — replanning from {(_v19 if _v19 is not None else ARDOUGNE)}')
    log(f'{MAX_LEGS} crossings without reaching ({dest.x},{dest.z})')
    return False


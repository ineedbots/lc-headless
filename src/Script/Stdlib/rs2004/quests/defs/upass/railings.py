"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/railings.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.navigation import navigator, reachability
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC
from rs2004.quests.defs.upass.verdict import said_since, verdict_since
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['OUT_OF_CAGES', 'TO_RAILINGS', 'outstanding_crossing', 'take_next_crossing', 'reach_loose_railings']

# Why: The six-crossing route is fixed; a free search also sees inaccessible ledges, tunnels, bridges, and cages.
# Why: Two ledges tie at distance one, so preserve the exact loc tile instead of using `nearest()`.
# Why: Regicide reuses this chain from the well corridor; the mud loc itself has no routable pocket.
OUT_OF_CAGES = [
    Record({
    'what': 'the cage into the mud cell',
    'stand': Tile(2393, 9655, 0),
    'at': Tile(2393, 9655, 0),
    'loc': UP_LOC.RAILINGS_LOCKED,
    'op': 'Pick-lock',
    'lands': Tile(2393, 9654, 0),
}),
    Record({
    'what': 'the spade dig south out of the cells',
    'stand': Tile(2393, 9651, 0),
    'at': Tile(2393, 9650, 0),
    'loc': UP_LOC.MUD_DIG,
    'op': 'Dig',
    'item': UP_ITEM.SPADE,
    'lands': Tile(2392, 9646, 0),
}),
    Record({
    'what': 'the ledge south out of the mud pocket',
    'stand': Tile(2375, 9644, 0),
    'at': Tile(2374, 9644, 0),
    'loc': UP_LOC.LEDGE,
    'op': 'Cross',
    'lands': Tile(2374, 9638, 0),
}),
]
TO_RAILINGS = list(OUT_OF_CAGES) + [Record({
    'what': 'the first thieving railing',
    'stand': Tile(2380, 9619, 0),
    'at': Tile(2380, 9619, 0),
    'loc': UP_LOC.RAILINGS_HARD,
    'op': 'Pick-lock',
    'lands': Tile(2381, 9619, 0),
}), Record({
    'what': 'the second thieving railing',
    'stand': Tile(2403, 9620, 0),
    'at': Tile(2404, 9620, 0),
    'loc': UP_LOC.RAILINGS_HARD,
    'op': 'Pick-lock',
    'lands': Tile(2404, 9620, 0),
}), Record({
    'what': 'the pipe into the loose railings',
    'via': [Tile(2420, 9617, 0)],
    'stand': Tile(2419, 9605, 0),
    'at': Tile(2417, 9605, 0),
    'loc': UP_LOC.PIPE_AREA2,
    'op': 'Squeeze-through',
    'lands': Tile(2412, 9605, 0),
})]


# Why: Step identity uses the name, so include the crossing index to reset attempts after each successful crossing.
# Why: the client's flood, because `decide` is synchronous. Out of the loaded scene reads unreachable, same as "not crossed yet", so the outstanding crossing is the first whose landing can't be reached and whose stand can.
def outstanding_crossing(chain=None):
    if chain is None:
        chain = TO_RAILINGS
    return ([step for step in chain if not reachability.can_reach(step.lands) and reachability.can_reach(step.stand)] or [None])[0]


def take_next_crossing(log, chain=None):
    """Take one crossing, the one you're in position for."""
    if chain is None:
        chain = TO_RAILINGS
    step = outstanding_crossing(chain)
    if step is None:
        me = game.tile()
        log(f'pass: ({(me.x if me is not None else None)},{(me.z if me is not None else None)}) is in position for no crossing of the run')
        return False
    _result2 = yield from take(step, log)
    return _result2


CROSS_MS = 12000
QUIET_MS = 1800


def can_walk_to(to):
    me = game.tile()
    return me is not None and navigator.find_path(me, to, policy={'use_teleports': False}).ok


def take(step, log):
    for stone in (step.via if step.via is not None else []):
        yield from traversal.walk_resilient(stone, radius=2, attempts=1, timeout_ms=30000)
    _w3 = yield from traversal.walk_resilient(step.stand, radius=0, attempts=2, timeout_ms=30000)
    if not (_w3):
        log(f'pass: could not stand on ({step.stand.x},{step.stand.z}) for {step.what}')
        return False
    # Why: by its own tile: both (2374,9644) and (2374,9643) are 1 tile from the stand and only the first can be crossed from there.
    named = locs.query().where(lambda l: l.id == step.loc and l.tile().x == step.at.x and l.tile().z == step.at.z)
    loc = ((named.action(step.op) if step.item is None else named)).nearest()
    if not loc:
        log(f'pass: {step.loc} is not at ({step.at.x},{step.at.z}) from ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)})')
        return False
    mark = game_messages.mark()
    # Why: `[oplocu,upass_mud]` carries no op the client can send. The crossing is a spade used on it.
    if step.item is None:
        sent = loc.interact(step.op)
    else:
        item = ([inv for inv in inventory.items() if inv.id == step.item.id] or [None])[0]
        sent = item is not None and item.use_on(loc)
    if not sent:
        what = f'the {step.item.name}' if step.item else f"'{step.op}'"
        log(f'pass: {what} would not send at {step.what}')
        return False
    yield from execution.delay_until(lambda: verdict_since(mark) is not None, QUIET_MS)
    said = verdict_since(mark)
    if said == 'refused':
        log(f"pass: {step.what} refused — {said_since(mark, 2)}")
        return False

    def _fn6():
        t = game.tile()
        return t is not None and t.x == step.lands.x and t.z == step.lands.z
    yield from execution.delay_until(_fn6, (CROSS_MS if said == 'crossing' else QUIET_MS))
    yield from settle_scene()
    now = game.tile()
    done = can_walk_to(step.lands)
    log(f"pass: {step.what} → ({(now.x if now is not None else None)},{(now.z if now is not None else None)}){('' if done else ' — but it did not land')}" + (('' if said is None else f' [{said}]')))
    return done


def reach_loose_railings(log):
    """Walk the cage corridor down to the loose railings, one named crossing at a time. Why: a step whose landing you can already walk to has happened, so the run resumes from wherever it is; the 6 crossings are one-way and in one order."""
    # Why: a run that doesn't apply from here says so once. The outstanding step is the first whose landing can't be walked to, and if its stand can't be either you're off the chain, past its far end from the unicorn area.
    pending = [step for step in TO_RAILINGS if not can_walk_to(step.lands)]
    next_ = pending[0] if len(pending) > 0 else None
    if next_ is not None and not can_walk_to(next_.stand):
        me = game.tile()
        log(f'pass: ({(me.x if me is not None else None)},{(me.z if me is not None else None)}) is not on the run to the loose railings —' + f' {len(pending)} crossing(s) outstanding and ({next_.stand.x},{next_.stand.z}) for {next_.what} is not walkable from here')
        return False
    for round in range(3):
        outstanding = 0
        for step in TO_RAILINGS:
            if can_walk_to(step.lands):
                continue
            outstanding += 1
            _w11 = yield from take(step, log)
            if not (_w11):
                break
        if outstanding == 0:
            return True
    last = TO_RAILINGS[len(TO_RAILINGS) - 1]
    return can_walk_to(last.lands)


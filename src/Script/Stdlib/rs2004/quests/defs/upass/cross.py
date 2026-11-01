"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/cross.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.navigation import navigator
from rs2004.quests.defs.upass.route import UPASS_AREAS, UPASS_CROSSINGS
from rs2004.quests.defs.upass.verdict import said_since, verdict_since
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['area_at', 'chain_from', 'cross_once']

# Why: Resolve the current area once instead of repeatedly scoring distance, walls, and spent crossings.
USED_ON = {
    2275: Record({'item': 954, 'name': 'Rope'}),
    2276: Record({'item': 954, 'name': 'Rope'}),
    3216: Record({'item': 952, 'name': 'Spade'}),
}
TABLE_LEVEL = 0
CROSS_MS = 12000
QUIET_MS = 1800
# Why: the pipe's script holds you still on its blocked tile between its moves, so stillness says nothing; only the move does.
FORCED_MOVE_TICKS = 16


def here():
    return game.tile()


def routes(from_, to):
    return navigator.find_path(from_, to, policy={'use_teleports': False}).ok


def area_at(me):
    """Current walkable area, or null on blocked tiles such as the ledge column."""
    for area in UPASS_AREAS:
        if routes(me, area.anchor):
            return area.area
    return None


def chain_from(from_, goal):
    """The first crossing along the shortest chain of areas from `from` to `goal`, or null when there is none."""
    if from_ == goal:
        return None
    seen = set([from_])
    frontier = []
    for edge in UPASS_CROSSINGS:
        if edge.from_ == from_ and not (edge.to in seen):
            seen.add(edge.to)
            frontier.append(Record({'area': edge.to, 'first': edge}))
    while len(frontier) > 0:
        hit = ([step for step in frontier if step.area == goal] or [None])[0]
        if hit:
            return hit.first
        next_ = []
        for step in frontier:
            for edge in UPASS_CROSSINGS:
                if edge.from_ == step.area and not (edge.to in seen):
                    seen.add(edge.to)
                    next_.append(Record({'area': edge.to, 'first': step.first}))
        frontier = next_
    return None


def operate(edge, log):
    """Send the crossing's op, or use the item it wants on the loc."""
    # Why: a row of identical locs ties by Chebyshev distance, and the ledge's stand is 1 from both (2374,9644) and its diagonal (2374,9643), where the server answers "I can't reach that!". The op has to go to the cardinal one. This departs from rs2b0t, whose tie went the right way.
    found = locs.query().where(lambda l: l.id == edge.loc).within(8).results()
    loc = (sorted(found, key=lambda l: abs(l.tile().x - edge.stand.x) + abs(l.tile().z - edge.stand.z)) or [None])[0]
    if not loc:
        log(f'pass: loc {edge.loc} is not in the scene from ({(here().x if here() is not None else None)},{(here().z if here() is not None else None)})')
        return False
    use = USED_ON.get(edge.loc)
    if use:
        item = ([inv for inv in inventory.items() if inv.id == use.item] or [None])[0]
        if not item:
            log(f'pass: the crossing at ({edge.stand.x},{edge.stand.z}) wants a {use.name} and the pack has none')
            return False
        return item.use_on(loc)
    return loc.interact(edge.op)


def wait_out_forced_move(me):
    """Waits for a forced move to carry you off me, and gives whether one did."""
    for tick in range(FORCED_MOVE_TICKS):
        yield from execution.delay_ticks(1)
        now = here()
        if now is not None and (now.x != me.x or now.z != me.z):
            yield from settle_scene()
            return True
    return False


def cross_once(dest, log):
    """Take one crossing out of the current area toward `dest`. Returns 'crossed' when the area changed, 'same' when it did not, and 'nowhere' when there is no chain."""
    me = here()
    if not me:
        return 'nowhere'
    # Why: every area in the table is level 0, so on the level-1 platforms no anchor matches and the "off the graph" branch would walk at level-0 anchors from level 1. `PLATFORM_LINKS` covers up there.
    if me.level != TABLE_LEVEL or dest.level != TABLE_LEVEL:
        return 'nowhere'
    from_ = area_at(me)
    if from_ is None:
        # Why: a pipe runs 2 exactmoves and a telejump, so a crossing judged mid-animation leaves you on its blocked tile for a few ticks, and walking at anchors from there lost the walk that should have followed. This departs from rs2b0t.
        moved = yield from wait_out_forced_move(me)
        if moved:
            return 'crossed'
        # Why: standing on a tile the pack calls blocked, so nothing about the graph applies until the nearest anchor puts you back on it.
        log(f'pass: ({me.x},{me.z}) is not on the walkable graph — stepping back onto it')
        for area in UPASS_AREAS:
            _w2 = yield from traversal.walk_resilient(area.anchor, radius=2, attempts=1, timeout_ms=15000)
            if _w2:
                return 'crossed'
        return 'nowhere'
    goal = area_at(dest)
    if goal is None:
        log(f'pass: ({dest.x},{dest.z}) is in no area the route knows')
        return 'nowhere'
    if from_ == goal:
        return 'nowhere'
    edge = chain_from(from_, goal)
    if not edge:
        log(f'pass: no chain of crossings from {from_} to {goal}')
        return 'nowhere'
    log(f'pass: in {from_}, heading for {goal} — {edge.op} {edge.loc} from ({edge.stand.x},{edge.stand.z}), lands ({edge.lands.x},{edge.lands.z}) in {edge.to}')
    _w3 = yield from traversal.walk_resilient(edge.stand, radius=0, attempts=1, timeout_ms=20000)
    if not (_w3):
        log(f'pass: could not stand on ({edge.stand.x},{edge.stand.z})')
        return 'same'
    mark = game_messages.mark()
    if not operate(edge, log):
        return 'same'
    # Why: the script says what it did in the tick the op resolves, and only a crossing is worth waiting out.
    yield from execution.delay_until(lambda: verdict_since(mark) is not None, QUIET_MS)
    said = verdict_since(mark)
    if said == 'refused' or said == 'failed':
        log(f"pass: {edge.op} {edge.loc} {said} — {said_since(mark, 2)}")
        return 'same'

    # Why: `delayUntil` polls every frame and can't await, so watch the landing tile and ask the area once after.
    def _fn5():
        t = here()
        return t is not None and t.x == edge.lands.x and t.z == edge.lands.z and t.level == edge.lands.level
    yield from execution.delay_until(_fn5, (CROSS_MS if said == 'crossing' else QUIET_MS))
    yield from settle_scene()
    _v6 = here()
    now = (_v6 if _v6 is not None else me)
    landed = area_at(now)
    if landed == edge.to:
        log(f'pass: {edge.op} {edge.loc} → ({now.x},{now.z}), now in {landed}')
        return 'crossed'
    log(f"pass: {edge.op} {edge.loc} left the character in {(landed if landed is not None else 'no area')} at ({now.x},{now.z}), wanted {edge.to}" + f" — it said: {said_since(mark, 3) or 'nothing'}")
    return 'same'


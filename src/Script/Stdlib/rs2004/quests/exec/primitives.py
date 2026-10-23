"""Talking to NPCs and getting to them: rs2b0t's api/ai/quests/exec/primitives.ts (MIT, see thirdparty/rs2b0t).
The quest engine builds on these, and bots outside quests use them too. Each takes a log function, which may be a
bot's self.log."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.reach import reach, talk_op
from rs2004.tabs import clean_text
from rs2004.traversal import traversal

__all__ = [
    'talk_op', 'pick_preferred', 'LineRule', 'pick_by_line', 'is_underground', 'needs_hop', 'LadderHop', 'NpcStop',
    'walk_with_hops', 'goto_npc', 'DIALOG_GAP_MS', 'drive_dialog', 'DIALOGUE_OPEN_MS', 'open_dialogue', 'talk_through',
    'talk_strict', 'talk_choosing_by',
]

# Underground maps sit 6400 tiles north of the surface; anything past z 5000 is below ground.
UNDERGROUND_Z = 5000


def pick_preferred(options, prefer):
    """The first option holding a preferred fragment, trying the fragments in order (case-insensitive), or None."""
    for p in prefer:
        wanted = p.lower()
        for o in options:
            if wanted in o.lower():
                return o
    return None


class LineRule:
    """Choose the option holding choose when the NPC's last line holds when_line (lower case)."""

    def __init__(self, when_line, choose):
        self.when_line = when_line
        self.choose = choose


def _flatten_lines(lines):
    return ' '.join(clean_text(' '.join(lines)).replace('|', ' ').split()).lower()


def pick_by_line(lines, options, rules):
    """The option the first matching LineRule names, longest when_line first, or None."""
    said = _flatten_lines(lines)
    if len(said) == 0:
        return None
    # Why: longest-first matching, so an overlapping shorter phrase such as "ar cur" can't win on a line that also contains "cur tanath".
    for rule in sorted(list(rules), key=lambda r: len(r.when_line), reverse=True):
        if rule.when_line.lower() in said:
            wanted = rule.choose.lower()
            for o in options:
                if wanted in o.lower():
                    return o
            return None
    return None


def is_underground(t):
    return t.z >= UNDERGROUND_Z


def needs_hop(here, anchor):
    return is_underground(here) != is_underground(anchor)


class LadderHop:
    """A ladder between the surface and underground: stand by it, op the loc_name loc, and arrive. open is the op
    that opens it first, a trapdoor's say, and walk the long-walk destination when stand is behind a door the
    route can't pin."""

    def __init__(self, stand, loc_name, op, arrive, open=None, walk=None):
        self.stand = stand
        self.loc_name = loc_name
        self.op = op
        self.arrive = arrive
        self.open = open
        self.walk = walk


class NpcStop:
    """Where to find an NPC: its anchor tile and how far it wanders (leash), the options to prefer when talking,
    tiles to walk through on the way (approach), and how long a lull in its dialogue may last (gap_ms)."""

    def __init__(self, npc, anchor, leash, prefer, approach=None, gap_ms=None):
        self.npc = npc
        self.anchor = anchor
        self.leash = leash
        self.prefer = prefer
        self.approach = approach
        # Why: a scene that walks an npc somewhere and animates it goes quiet for longer than a page turn, and the default tolerance ends the drive mid-scene.
        self.gap_ms = gap_ms


def _hop_ladder(hop, log):
    def find(op):
        stand = hop.stand
        return locs.query().name(hop.loc_name).action(op).where(lambda l: l.tile().distance_to(stand) <= 3).nearest()

    ladder = find(hop.op)
    if not ladder and hop.open is not None:
        closed = find(hop.open)
        if closed and closed.interact(hop.open):
            yield from execution.delay_ticks(2)
            ladder = find(hop.op)
            if not ladder:
                yield from execution.delay_ticks(2)
                ladder = find(hop.op)
    if not ladder:
        log(f"no '{hop.loc_name}' offering '{hop.op}' near ({hop.stand.x},{hop.stand.z})")
        return False
    if not ladder.interact(hop.op):
        return False

    def arrived():
        t = game.tile()
        return t is not None and t.level == hop.arrive.level and hop.arrive.distance_to(t) <= 5

    result = yield from execution.delay_until(arrived, 8000)
    return result


def _cross_hops(here, dest, hops, log):
    if not needs_hop(here, dest):
        return here
    near = [h for h in hops if is_underground(h.stand) == is_underground(here)]
    hop = (sorted(near, key=lambda h: h.stand.distance_to(here)) or [None])[0]
    if hop is None:
        log(f'no hop from ({here.x},{here.z}) toward z {dest.z}; trying the baked graph')
        return here
    walk_to = hop.walk if hop.walk is not None else hop.stand
    if hop.stand.distance_to(here) > 2:
        walked = yield from traversal.walk_resilient(walk_to, radius=2, attempts=3, log=log)
        if not walked:
            return None
    here = game.tile() or here
    if hop.walk is not None and hop.stand.distance_to(here) > 2:
        walked = yield from traversal.walk_resilient(hop.stand, radius=1, attempts=3, log=log)
        if not walked:
            return None
    hopped = yield from _hop_ladder(hop, log)
    if not hopped:
        return None
    return game.tile()


def walk_with_hops(dest, radius, hops, log):
    """Walks to dest, climbing the nearest of hops first when dest is on the other side of the ground. Use with
    yield from."""
    start = game.tile()
    if not start:
        return False
    here = yield from _cross_hops(start, dest, hops, log)
    if not here:
        return False
    if here.level != dest.level or dest.distance_to(here) > radius:
        result = yield from traversal.walk_resilient(dest, radius=radius, attempts=3, log=log)
        return result
    return True


def goto_npc(stop, hops, log):
    """Walks to an NpcStop, through its approach tiles, and True once the NPC is inside its leash. Use with yield
    from."""
    here = game.tile()
    if not here:
        return False

    def npc_near():
        n = npcs.query().name(stop.npc).nearest()
        return n is not None and n.distance() <= stop.leash

    hopped = yield from _cross_hops(here, stop.anchor, hops, log)
    if not hopped:
        return False
    here = hopped
    approach_failed = False
    for wp in stop.approach or []:
        if wp.distance_to(here) > 2:
            walked = yield from traversal.walk_resilient(wp, radius=2, attempts=2, timeout_ms=45000, log=log)
            here = game.tile() or here
            if not walked:
                approach_failed = True
                break
    if not approach_failed and stop.anchor.distance_to(here) > 1:
        yield from traversal.walk_resilient(stop.anchor, radius=1, attempts=2, timeout_ms=45000, log=log)
        here = game.tile() or here
    off = stop.anchor.distance_to(here)
    if is_underground(here) and is_underground(stop.anchor) and off > 2 and off <= 20:
        back = None
        for h in hops:
            if is_underground(h.stand) == is_underground(here):
                back = h
                break
        if back is not None:
            log(f'trapped landing at ({here.x},{here.z}); could not reach the anchor, climbing back to re-roll')
            if back.stand.distance_to(here) > 1:
                yield from traversal.walk_resilient(back.stand, radius=1, attempts=3, log=log)
            yield from _hop_ladder(back, log)
        return False
    if approach_failed:
        return False
    return npc_near()


# A page turn's worth of quiet; a scene that walks an npc about wants its stop to name more.
DIALOG_GAP_MS = 1500


def _dialog_up():
    return chat_dialog.is_open() or chat_dialog.can_continue()


def drive_dialog(prefer, log, gap_ms=None):
    """Clicks through an open dialogue, choosing the preferred options and the last when none is, until it closes
    or stays quiet for gap_ms. True when it closed. Use with yield from."""
    if gap_ms is None:
        gap_ms = DIALOG_GAP_MS
    for _ in range(120):
        if event_signal.pending():
            return False
        if not _dialog_up():
            reopened = yield from execution.delay_until(_dialog_up, gap_ms)
            if not reopened:
                break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        opts = chat_dialog.options()
        if len(opts) > 0:
            pick = pick_preferred(opts, prefer)
            if not pick:
                log(f"WARN: no preferred option in [{' | '.join(opts)}]; taking the last")
            yield from chat_dialog.choose_option(pick if pick is not None else opts[-1])
            yield from execution.delay_ticks(2)
            continue
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()


DIALOGUE_OPEN_MS = 8000


def open_dialogue(npc_name, log):
    """Talks to the nearest NPC of that name, opening a door it stands behind. True once a dialogue is up. Use
    with yield from."""
    if _dialog_up():
        return True

    def find():
        return npcs.query().name(npc_name).where(lambda n: talk_op(n.actions()) is not None).nearest()

    npc = find()
    if not npc:
        log(f"no '{npc_name}' nearby to talk to")
        return False
    # Why: an NPC who wandered behind a shut door is in the scene and inside the leash yet unreachable, so Reach opens the door.
    status = yield from reach.entity_op(find, talk_op(npc.actions()), _dialog_up, open_when_unreachable=True, expect_ms=DIALOGUE_OPEN_MS, what=npc_name, log=log)
    if status != 'done':
        log(f"'{npc_name}' never opened a dialogue")
        return False
    return True


def talk_through(npc_name, prefer, log, gap_ms=None):
    """open_dialogue, then drive_dialog. Use with yield from."""
    opened = yield from open_dialogue(npc_name, log)
    if not opened:
        return False
    result = yield from drive_dialog(prefer, log, gap_ms)
    return result


# Why: guessing bites: several ogres offer "I have come to kill you" as the alternative.
def talk_strict(npc_name, prefer, log):
    """Like talk_through, but abandons the dialogue instead of guessing when no preferred option matches. Use
    with yield from."""
    result = yield from talk_choosing_by(npc_name, [], prefer, log)
    return result


def talk_choosing_by(npc_name, rules, prefer, log):
    """Drives a dialogue whose right option depends on what the NPC said: the LineRules first, then prefer. False
    when neither matches. Use with yield from."""
    opened = yield from open_dialogue(npc_name, log)
    if not opened:
        return False
    spoken = []
    for _ in range(120):
        if event_signal.pending():
            return False
        opts = chat_dialog.options()
        # Why: the options page is itself made of text components, so capturing the NPC's line while an option list is up would overwrite the phrase the rules match against.
        if len(opts) == 0 and chat_dialog.is_open():
            texts = chat_dialog.texts()
            if len(texts) > 0:
                spoken = texts
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if len(opts) > 0:
            pick = pick_by_line(spoken, opts, rules)
            if pick is None:
                pick = pick_preferred(opts, prefer)
            if not pick:
                log(f"no rule or preference matched [{' | '.join(opts)}] after \"{' '.join(spoken)}\"")
                return False
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            break
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()

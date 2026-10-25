"""The legs quests are made of, beyond one step: rs2b0t's api/ai/quests/exec/legs.ts (MIT, see thirdparty/rs2b0t).
Opening a container, climbing, walking to and talking with an NPC, combining two items, and a conversation that runs
until its goal lands."""

import time

from rs2004 import execution
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.exec.prompts import LocPrompt, drive_choice, prompt_loc, settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['CLIMB_MS', 'WALK_MS', 'open_container', 'climb', 'walk_and_talk', 'combine_by_id', 'talk_and_close', 'talk_until']

CLIMB_MS = 12000
WALK_MS = 120000


def _now_ms():
    return time.time() * 1000


def _loc_with_id(id, within):
    return locs.query().within(within).where(lambda l: l.id == id).nearest()


# Why: the scene keeps the shut id for a tick after the Open lands, so one check calls a successful open a failure.
def open_container(name, shut_id, open_id, stand, log):
    """Opens a shut container and waits for its open twin to appear in the scene. Use with yield from."""
    for attempt in range(3):
        if _loc_with_id(open_id, 6) is not None:
            return True
        prompt = LocPrompt(name, 'Open', stand, lambda: _loc_with_id(open_id, 6) is not None, within=6, id=shut_id)
        yield from prompt_loc(prompt, log)
        yield from settle_scene()
    if _loc_with_id(open_id, 6) is not None:
        return True
    log(f'the shut {name.lower()} ({shut_id}) never became {open_id}')
    return False


def climb(loc_id, op, stand, arrive, log):
    """Climbs a loc that changes level, proven by the arrival level. Use with yield from."""
    here = game.tile()
    if here is not None and here.level == arrive.level:
        return True
    walked = yield from traversal.walk_resilient(stand, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not walked:
        return False
    loc = locs.query().action(op).within(4).where(lambda l: l.id == loc_id).nearest()
    if loc is None:
        log(f"no loc {loc_id} offering '{op}' near ({stand.x},{stand.z})")
        return False
    if not loc.interact(op):
        log(f"loc {loc_id} refused '{op}'")
        return False

    def arrived():
        t = game.tile()
        return t is not None and t.level == arrive.level

    yield from execution.delay_until(arrived, CLIMB_MS)
    yield from settle_scene()
    if arrived():
        return True
    log(f"'{op}' on loc {loc_id} never reached level {arrive.level}")
    return False


# Why: talk_through never walks, and goto_npc's shared hop calls a stand 2 tiles off "arrived" without moving.
def walk_and_talk(stop, prefer, log):
    """Walks to a stop and drives its dialogue. Use with yield from."""
    here = game.tile()
    if here is None or stop.anchor.distance_to(here) > stop.leash or here.level != stop.anchor.level:
        yield from traversal.walk_resilient(stop.anchor, radius=2, attempts=3, timeout_ms=WALK_MS, log=log)
    status = yield from reach.npc_dialog(stop.npc, stop.anchor, log=log)
    if status != 'done':
        log(f'could not open a dialogue with {stop.npc} ({status})')
        return False
    driven = yield from drive_choice(list(prefer), log)
    return driven


def _held_count(id):
    return sum([item.count for item in inventory.items() if item.id == id])


def _first_with_id(id):
    for item in inventory.items():
        if item.id == id:
            return item
    return None


# Why: opheldu is declared on one item of a pair and the client can't tell which, so a one-direction combine fails on
# half the recipes.
def combine_by_id(a_id, b_id, product_id, log):
    """Uses one carried item on another and waits for the product, trying both directions. Use with yield from."""
    if _held_count(product_id) > 0:
        return True
    for use_id, onto_id in [(a_id, b_id), (b_id, a_id)]:
        source = _first_with_id(use_id)
        target = _first_with_id(onto_id)
        if source is None or target is None:
            log(f'cannot combine {a_id} with {b_id} — one of them is not in the pack')
            return False
        if source.use_on(target):
            made = yield from execution.delay_until(lambda: _held_count(product_id) > 0, 8000)
            if made:
                return True
    log(f'combining {a_id} with {b_id} produced no {product_id}')
    return False


# Why: a conversation that signs off with ~mesbox leaves a main modal up, and it silently swallows the next leg's
# player, npc or trade click.
def talk_and_close(stop, prefer, log):
    """Walks to a stop, drives its dialogue, and clears whatever modal it signed off with. Use with yield from."""
    ok = yield from walk_and_talk(stop, prefer, log)
    if modals.main() != -1:
        yield from modals.close()
    return ok


# Why: ~mesbox and ~objbox build a main modal no dialogue driver can see, and the curator and the king both use them
# mid-conversation, so a chat-only driver stalls on the first one.
def talk_until(stop, prefer, expect, log, ms=45000):
    """Drives a conversation that mixes chat with mesboxes, until the goal lands. Use with yield from."""
    if expect():
        return True
    yield from walk_and_talk(stop, prefer, log)
    deadline = _now_ms() + ms
    while _now_ms() < deadline and not expect():
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drive_choice(list(prefer), log)
            continue
        if modals.main() != -1:
            yield from modals.close()
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    # Why: the closing mesbox stays up after the goal lands, and a main modal blocks the next leg's player interaction.
    if modals.main() != -1:
        yield from modals.close()
    if not expect():
        log(f'{stop.npc} conversation ended without the expected result')
    return expect()

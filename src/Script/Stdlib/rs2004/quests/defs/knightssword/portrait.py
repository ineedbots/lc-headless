"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/portrait.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.knightssword.areas import KS_ID, KS_TILE, VYVIN_APPROACHES
from rs2004.quests.exec.prompts import loc_near, settle_scene
from rs2004.traversal import traversal


__all__ = ['vyvin_too_close', 'should_wait_out', 'best_approach', 'fetch_portrait']

VYVIN_LEASH = 1
ATTEMPTS = 60
# Why: Vyvin has `wanderrange=8` in a room barely wider than that, so he is adjacent most of the time.
# Why: Treat the position check as a hint; blocking on it repeats until the watchdog stops the quest.
# Passes that may be skipped on Vyvin's position alone.
MAX_SKIPS = 4
REFUSALS_BEFORE_RETREAT = 3


def vyvin_too_close(here, vyvin):
    if not here or not vyvin:
        return False
    return Tile.from_tile(here).distance_to(vyvin) <= VYVIN_LEASH


def should_wait_out(skips, here, vyvin):
    """After `MAX_SKIPS` passes the search happens regardless."""
    return skips < MAX_SKIPS and vyvin_too_close(here, vyvin)


# Why: both approaches sit south of the cupboard, so with Sir Vyvin directly south neither is clear and only time helps.
# Why: with him off to one side only the far tile is clear, so take the far one.
def best_approach(approaches, vyvin):
    """Pick the approach tile furthest from Sir Vyvin."""
    if not vyvin:
        return approaches[0]
    return (sorted(list(approaches), key=lambda b: b.distance_to(vyvin), reverse=True) or [None])[0]


def vyvin_tile():
    vyvin = npcs.query().name('Sir Vyvin').nearest()
    return vyvin.tile() if vyvin is not None else None


# Why: the engine dedupes identical sub-log lines within a step, so the text has to vary or repeats vanish.
# Why: a silent cupboard stuck at 2271 means an illegal approach, and this line is how you spot it.
def describe(pass_):
    """The refusal line for one search pass."""
    here = game.tile()
    vyvin = vyvin_tile()
    cupboards = [f"{c.tile().x},{c.tile().z}:{c.id}:{'/'.join([_x for _x in c.actions() if _x])}" for c in locs.query().name('Cupboard').within(8).results()]
    return f"pass {pass_} me={(f'{here.x},{here.z},{here.level}' if here else '?')}" + f" vyvin={(f'{vyvin.x},{vyvin.z}' if vyvin else 'absent')}" + f" cupboards=[{' '.join(cupboards)}]"


def dismiss_refusal():
    """A caught search leaves a mesbox up that has to go before the next click."""
    i = 0
    while i < 4 and chat_dialog.can_continue():
        yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
        i += 1


# Why: `vyvincupboardshut` is `forceapproach=east` at rotation 1, so the only legal approach is its south side.
# Why: Open turns it into `vyvincupboardopen`, which is the one that Searches.
# Why: the oracle is whether the portrait lands; Vyvin's position is read a tick before the click and re-checked server-side after the walk.
def fetch_portrait(log):
    if inventory.count_by_id(KS_ID.PORTRAIT) > 0:
        return True
    _w2 = yield from traversal.walk_resilient(KS_TILE.VYVIN_ROOM, radius=1, attempts=4, timeout_ms=300000, log=log)
    if not (_w2):
        log("could not reach Sir Vyvin's room")
        return False
    yield from settle_scene()
    skips = 0
    refusals = 0
    for i in range(ATTEMPTS):
        # Why: he wanders on a timer and can camp the tile south of the cupboard, within 1 tile of both approaches.
        # Why: vacating the approach gives him somewhere to go.
        if refusals >= REFUSALS_BEFORE_RETREAT:
            refusals = 0
            log('stepping away to give Sir Vyvin room to wander')
            yield from traversal.walk_resilient(KS_TILE.VYVIN_RETREAT, radius=1, attempts=2, timeout_ms=90000, log=log)
            yield from execution.delay_ticks(10)
        stand = best_approach(VYVIN_APPROACHES, vyvin_tile())
        here = game.tile()
        if not here or stand.distance_to(here) != 0 or here.level != stand.level:
            yield from traversal.walk_resilient(stand, radius=0, attempts=3, timeout_ms=90000, log=log)
            yield from settle_scene()
        if inventory.count_by_id(KS_ID.PORTRAIT) > 0:
            return True
        yield from dismiss_refusal()
        shut = loc_near('Cupboard', 'Open', 5)
        if shut:
            shut.interact('Open')
            yield from execution.delay_ticks(2)
            continue
        open = loc_near('Cupboard', 'Search', 5)
        if not open:
            log('no Cupboard in reach of the stand')
            yield from execution.delay_ticks(2)
            continue
        if should_wait_out(skips, game.tile(), vyvin_tile()):
            skips += 1
            yield from execution.delay_ticks(2)
            continue
        skips = 0
        open.interact('Search')
        _w3 = yield from execution.delay_until(lambda: inventory.count_by_id(KS_ID.PORTRAIT) > 0, 5000)
        if _w3:
            return True
        refusals += 1
        # Why: only blame Vyvin when he's in range; a search can fail on its own and mislabelling it sends the next reader hunting him.
        blocked = vyvin_too_close(game.tile(), vyvin_tile())
        log(f"{('Sir Vyvin was watching' if blocked else 'search did not land')} — {describe(i)}")
        yield from execution.delay_ticks(4)
    log('never got a clear look at the cupboard')
    return False

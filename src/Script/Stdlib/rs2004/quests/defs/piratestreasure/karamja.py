"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/karamja.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.quests.defs.piratestreasure.areas import BANANA_TREE_IDS, LUTHAS, PT_ID, PT_LOC, PT_TILE
from rs2004.quests.defs.piratestreasure.crate import CRATE_FULL, search_banana_crate
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.traversal import traversal


__all__ = ['on_karamja', 'fill_crate', 'ship_crate']

KARAMJA_BOX = Record({'min_x': 2870, 'max_x': 2970, 'min_z': 3110, 'max_z': 3210})


def on_karamja(tile):
    """True on Musa Point and the plantation, generously bounded."""
    return bool(tile) and tile.level == 0 and tile.x >= KARAMJA_BOX.min_x and tile.x <= KARAMJA_BOX.max_x and tile.z >= KARAMJA_BOX.min_z and tile.z <= KARAMJA_BOX.max_z


def held(id):
    return inventory.count_by_id(id)


# Why: Searching the crate reveals untransmitted state before a resumed run buys another rum.
def stash_rum(log):
    """Put the rum in the plantation crate, unless it is already in there."""
    yield from sustain.run()
    state = yield from search_banana_crate(log)
    if (state.rum if state is not None else None):
        log('the rum is already in the crate')
        return True
    if held(PT_ID.RUM) == 0:
        log('no rum in the pack to stash')
        return False
    _result1 = yield from use_on_loc(PT_ID.RUM, Record({'name': 'Crate', 'near': PT_TILE.BANANA_CRATE, 'within': 6, 'id': PT_LOC.BANANA_CRATE}), [], lambda: held(PT_ID.RUM) == 0, log)
    return _result1


def pick_bananas(want, log):
    """Search trees until the pack holds `want` bananas or the grove runs dry."""
    if held(PT_ID.BANANA) >= want:
        return held(PT_ID.BANANA)
    _w2 = yield from traversal.walk_resilient(PT_TILE.BANANA_GROVE, radius=4, attempts=3, timeout_ms=180000, log=log)
    if not (_w2):
        log('could not reach the banana grove')
        return held(PT_ID.BANANA)
    attempt = 0
    while attempt < 40 and held(PT_ID.BANANA) < want and not inventory.is_full():
        attempt += 1
        yield from sustain.run()
        yield from settle_scene()
        tree = locs.query().action('Search').where(lambda l: (l.id in BANANA_TREE_IDS)).within(20).nearest()
        if not tree:
            log('no bearing Banana Tree in range of the grove anchor')
            break
        before = held(PT_ID.BANANA)
        if not (tree.interact('Search')):
            continue
        yield from execution.delay_until(lambda: held(PT_ID.BANANA) > before, 4000)

    log(f'picked {held(PT_ID.BANANA)} bananas')
    return held(PT_ID.BANANA)


# Why: the crate's own message names the count, so the loop never keeps a tally the client could be wrong about.
def fill_crate(log):
    """Fill the plantation crate to 10 bananas."""
    for pass_ in range(CRATE_FULL):
        state = yield from search_banana_crate(log)
        if not state:
            return False
        if state.bananas >= CRATE_FULL:
            return True
        want = CRATE_FULL - state.bananas
        _w3 = yield from pick_bananas(want, log)
        if (_w3) == 0:
            log('the grove gave up no bananas')
            return False
        yield from sustain.run()
        _w4 = yield from traversal.walk_resilient(PT_TILE.BANANA_CRATE, radius=2, attempts=3, timeout_ms=180000, log=log)
        if not (_w4):
            return False
        yield from settle_scene()
        packed = 0
        while packed < want and held(PT_ID.BANANA) > 0:
            before = held(PT_ID.BANANA)
            _w5 = yield from use_on_loc(PT_ID.BANANA, Record({'name': 'Crate', 'near': PT_TILE.BANANA_CRATE, 'within': 6, 'id': PT_LOC.BANANA_CRATE}), [], lambda: held(PT_ID.BANANA) < before, log)
            if not (_w5):
                break
            packed += 1
    done = yield from search_banana_crate(log)
    return done is not None and done.bananas >= CRATE_FULL


# Why: the journal reads `store-job` throughout the re-smuggle, so `decide()` can't sequence this; the leg runs to completion on its own.
# Why: it ends on the mainland so the next decide tick is never stranded on the wrong side of the water.
def ship_crate(log):
    """Read the crate, stash, fill and ship it, then cross back to Port Sarim."""
    yield from sustain.run()
    state = yield from search_banana_crate(log)
    if not state:
        return False
    if not state.rum:
        if held(PT_ID.RUM) == 0:
            log('the crate is empty and no rum is carried — crossing back to Port Sarim')
            yield from traversal.walk_resilient(PT_TILE.WYDIN, radius=4, attempts=3, timeout_ms=300000, log=log)
            return False
        # Why: `banana_crate.rs2` answers "Why would I want to do that?" once Luthas has shipped a crate and cleared the employed bit, so a second smuggle re-hires first; the refusal is the only sign.
        _w6 = yield from stash_rum(log)
        if not (_w6):
            log('the crate refused the rum — re-hiring at the plantation')
            _w7 = yield from traversal.walk_resilient(LUTHAS.anchor, radius=2, attempts=3, timeout_ms=120000, log=log)
            if not (_w7):
                return False
            _w8 = yield from talk_strict(LUTHAS.npc, LUTHAS.prefer, log)
            if not (_w8):
                return False
            _w9 = yield from stash_rum(log)
            if not (_w9):
                log('the crate still refused the rum after re-hiring')
                return False
        state = yield from search_banana_crate(log)
        if not (state.rum if state is not None else None):
            log('the rum did not land in the crate')
            return False
    _c10 = state.bananas < CRATE_FULL
    if _c10:
        _w11 = yield from fill_crate(log)
        _c10 = not (_w11)
    if _c10:
        return False
    yield from sustain.run()
    _w12 = yield from traversal.walk_resilient(LUTHAS.anchor, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w12):
        return False
    _w13 = yield from talk_strict(LUTHAS.npc, LUTHAS.prefer, log)
    if not (_w13):
        return False
    after = yield from search_banana_crate(log)
    if not after or after.rum:
        log('Luthas did not ship the crate')
        return False
    log('the crate has sailed — crossing back to Port Sarim')
    yield from traversal.walk_resilient(PT_TILE.WYDIN, radius=4, attempts=3, timeout_ms=300000, log=log)
    return True

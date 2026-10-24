"""Getting a trail's tools: the spade off its spawn, the coordinate trio from the professor, Murphy and Brother Kojo,
a row's extra item, and a crossing's toll. rs2b0t's api/ai/clues/AcquireTools.ts (MIT, see thirdparty/rs2b0t). The
functions are Waits, used with yield from."""

import time

from rs2004 import execution
from rs2004.entities import ground_items
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.exec.primitives import goto_npc, talk_through
from rs2004.trade import shop
from rs2004.traversal import traversal
from rs2004.clues.data import CLUE_DB
from rs2004.clues.tools import KOJO, KOJO_EXIT, MURPHY, PROFESSOR, SPADE_NAME, SPADE_SPAWNS, TRIO, extra_item_shop, gate_item_shop, next_coord_tool

COINS = 'Coins'
SPADE_OBJ_ID = 952
WALK_ATTEMPTS = 4
WALK_TIMEOUT_MS = 120000
TAKE_WAIT_MS = 3000
TOOL_WAIT_MS = 3000
CHAIN_GUARD = 8
HOP_ATTEMPTS = 4
HOP_TIMEOUT_MS = 90000
HOP_ARRIVE_RADIUS = 4
CHAIN_DEADLINE_MS = 480000


def _held(name):
    return inventory.first(name) is not None


def has_all_trio():
    return all([_held(n) for n in TRIO])


def has_coord_clue_held():
    return any([(CLUE_DB.get(i.id) or {}).get('needs_sextant') == True for i in inventory.items()])


def _indented(log):
    return lambda m: log(f'  {m}')


def _travel_to_stop(stop, log):
    yield from traversal.walk_resilient(stop.anchor, radius=HOP_ARRIVE_RADIUS, attempts=HOP_ATTEMPTS, timeout_ms=HOP_TIMEOUT_MS, log=_indented(log))
    reached = yield from goto_npc(stop, [], log)
    return reached


def _is_spade(g):
    return g.id == SPADE_OBJ_ID or (g.name or '').lower() == 'spade'


def ensure_spade(log):
    """Picks up a spade off the nearer of its two spawns."""
    if _held(SPADE_NAME):
        return True
    here = game.tile()
    spawns = sorted(SPADE_SPAWNS, key=lambda s: s.distance_to(here)) if here is not None else list(SPADE_SPAWNS)
    for spawn in spawns:
        if event_signal.pending():
            return False
        log(f'acquiring a spade: walking to ({spawn.x},{spawn.z})')
        yield from traversal.walk_resilient(spawn, radius=1, attempts=WALK_ATTEMPTS, timeout_ms=WALK_TIMEOUT_MS, log=_indented(log))
        spade = ground_items.query().where(_is_spade).nearest()
        if spade is not None:
            if spade.distance() > 1:
                yield from traversal.walk_resilient(spade.tile(), radius=1, attempts=2, timeout_ms=WALK_TIMEOUT_MS, log=_indented(log))
            spade.interact('Take')
            got = yield from execution.delay_until(lambda: _held(SPADE_NAME), TAKE_WAIT_MS)
            if got:
                log('got a spade')
                return True
        log(f'no spade at ({spawn.x},{spawn.z}): trying the next spawn')
    return False


def _buy(shop_source, name, count, log):
    """Walks to the counter and buys count of name: how many arrived."""
    reached = yield from traversal.walk_resilient(shop_source.stand, radius=HOP_ARRIVE_RADIUS, attempts=WALK_ATTEMPTS, timeout_ms=WALK_TIMEOUT_MS,
                                                  log=_indented(log))
    if event_signal.pending() or not reached:
        return 0
    opened = yield from shop.open(shop_source.npc)
    if not opened:
        log(f"{shop_source.npc}'s shop did not open: leaving '{name}' unacquired")
        return 0
    before = inventory.count(name)
    got = yield from shop.buy(name, count)
    yield from shop.close()
    if got > 0:
        landed = yield from execution.delay_until(lambda: inventory.count(name) > before, TOOL_WAIT_MS)
        if landed:
            return inventory.count(name) - before
    log(f"{shop_source.npc} had no '{name}' in stock")
    return 0


# Why: bank prep withdraws a row's extra items when the bank has one, and without this the trail abandons over 18gp.
def ensure_extra_items(names, log):
    """Buys the extra items a clue row lists in items, today the Baxtorian rope. True when one was bought."""
    bought = False
    for name in names:
        if _held(name):
            continue
        if event_signal.pending():
            return bought
        source = extra_item_shop(name)
        if source is None:
            log(f"no shop known for '{name}': cannot acquire it")
            continue
        if inventory.count(COINS) < source.cost:
            log(f"need ~{source.cost} coins for '{name}' and hold {inventory.count(COINS)}: skipping the shop trip")
            continue
        log(f'acquiring {name}: walking to {source.npc} at ({source.stand.x},{source.stand.z})')
        got = yield from _buy(source, name, 1, log)
        if got > 0:
            log(f'bought {name}')
            bought = True
    return bought


# Why: missing comes from the walker's own diagnosis, so this only fires for a crossing the bot planned to use, and
# coins are skipped because no counter sells them.
def ensure_gate_items(missing, log):
    """Buys the crossing tolls the walker says a route is short of; missing has name and count."""
    bought = False
    for want in missing:
        if event_signal.pending():
            return bought
        if want.name.lower() == COINS.lower():
            log(f'route needs {want.count} more {COINS}: no shop sells those')
            continue
        source = gate_item_shop(want.name)
        if source is None:
            log(f"route is short {want.count}x '{want.name}' and no counter is known for it")
            continue
        price = source.cost * want.count
        if inventory.count(COINS) < price:
            log(f"need ~{price} coins for {want.count}x '{want.name}' and hold {inventory.count(COINS)}")
            continue
        log(f"route is short {want.count}x '{want.name}': buying from {source.npc} at ({source.stand.x},{source.stand.z})")
        got = yield from _buy(source, want.name, want.count, log)
        if got > 0:
            log(f'bought {got}x {want.name}')
            bought = True
    return bought


def _now_ms():
    return time.time() * 1000


def ensure_coord_tools(log):
    """The sextant, watch and chart, in the order the professor's chain hands them out. Needs a coordinate clue
    held, since that's what the NPCs answer to."""
    if has_all_trio():
        return True
    if not has_coord_clue_held():
        log('coord-tool chain needs a coordinate clue held: skipping')
        return False
    deadline = _now_ms() + CHAIN_DEADLINE_MS
    for _ in range(CHAIN_GUARD):
        if has_all_trio():
            break
        if event_signal.pending():
            return False
        if _now_ms() > deadline:
            log('coord-tools: chain exceeded its time budget: abandoning (likely a stuck door en route)')
            return False
        need = next_coord_tool(_held('Sextant'), _held('Watch'), _held('Chart'))
        if need is None:
            break
        if need == 'sextant':
            log('coord-tools: learning from the professor, then Murphy for the sextant')
            reached = yield from _travel_to_stop(PROFESSOR, log)
            if reached:
                yield from talk_through(PROFESSOR.npc, PROFESSOR.prefer, log)
            if event_signal.pending():
                return False
            reached = yield from _travel_to_stop(MURPHY, log)
            if reached:
                yield from talk_through(MURPHY.npc, MURPHY.prefer, log)
            yield from execution.delay_until(lambda: _held('Sextant'), TOOL_WAIT_MS)
            if not _held('Sextant'):
                log('coord-tools: Murphy did not yield a sextant: abandoning the chain')
                return False
        elif need == 'watch':
            log('coord-tools: Brother Kojo for the watch')
            reached = yield from _travel_to_stop(KOJO, log)
            if reached:
                yield from talk_through(KOJO.npc, KOJO.prefer, log)
            yield from execution.delay_until(lambda: _held('Watch'), TOOL_WAIT_MS)
            if not _held('Watch'):
                log('coord-tools: Kojo did not yield a watch: abandoning the chain')
                return False
        else:
            log('coord-tools: back to the professor for the chart')
            here = game.tile()
            if here is not None and KOJO.anchor.distance_to(here) <= 15:
                log(f'coord-tools: exiting the Clock Tower via ({KOJO_EXIT.x},{KOJO_EXIT.z}) to dodge the locked door')
                yield from traversal.walk_resilient(KOJO_EXIT, radius=1, attempts=3, timeout_ms=60000, log=_indented(log))
            reached = yield from _travel_to_stop(PROFESSOR, log)
            if reached:
                yield from talk_through(PROFESSOR.npc, PROFESSOR.prefer, log)
            yield from execution.delay_until(lambda: _held('Chart'), TOOL_WAIT_MS)
            if not _held('Chart'):
                log('coord-tools: the professor did not yield a chart: abandoning the chain')
                return False
    return has_all_trio()

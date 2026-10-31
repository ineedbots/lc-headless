"""Running one quest step: rs2b0t's api/ai/quests/exec/steps.ts (MIT, see thirdparty/rs2b0t). execute_step takes a step
from rs2004.quests.engine.types and gives True when it worked."""

from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.bot import is_generator
from rs2004.catalogs.gathering import bank_distance
from rs2004.catalogs.mining import QUEST_ROCK_TYPES, ROCK_TYPES
from rs2004.dialogue import modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.navigation import navigator
from rs2004.quests.engine.provisioning import buy_purse_top_up
from rs2004.quests.exec.primitives import goto_npc, talk_through
from rs2004.trade import shop
from rs2004.traversal import nearest_banks, traversal

__all__ = ['BANK_CANDIDATES', 'reachable_bank', 'open_bank_leg', 'ensure_at', 'run_maybe', 'rock_type_of', 'execute_step']

# How deep into the straight-line shortlist to look before giving up.
BANK_CANDIDATES = 6


def _bank_tile(bank_row):
    t = bank_row['tile']
    return Tile(t['x'], t['z'], t['level'])


# Why: from the Lumbridge respawn the 3 closest banks by air, Al Kharid, Shantay Pass and the Duel Arena, sit behind the
# same 10gp toll gate, and the navigator prunes a fare it can't pay.
# Why: a bot that has died can't reach any of those, and the first bank it can walk to is 3rd on the list, so the
# navigator is asked for path costs.
def reachable_bank(from_, log):
    """The nearest bank measured by walking cost."""
    candidates = [_bank_tile(b) for b in nearest_banks(from_)[0:BANK_CANDIDATES]]
    best_tile = None
    best_cost = 0
    for tile in candidates:
        # Why: stopping once a known route beats the next candidate's crow-flight is exact on open ground, as a walk is
        # never shorter than its straight line.
        # Why: a ladder or a ship can beat that line, so this can settle for a bank short of the cheapest.
        # Why: it can never settle for an unreachable bank, as nothing breaks the loop until a path has been found.
        # Why: the common case stays at 1 or 2 pathfinds instead of 6.
        if best_tile is not None and bank_distance(from_, tile) >= best_cost:
            break
        path = navigator.find_path(from_, tile)
        if path.ok and (best_tile is None or path.cost < best_cost):
            best_tile = tile
            best_cost = path.cost
    if best_tile is not None:
        return best_tile
    log(f'no bank answered a path from ({from_.x},{from_.z}), trying the closest anyway')
    return candidates[0] if len(candidates) > 0 else None


def open_bank_leg(no_bank_msg, override, log):
    """Opens the bank at override, or at the nearest one the walker can reach. Use with yield from."""
    bank_tile = override
    if bank_tile is None:
        here = game.tile()
        bank_tile = reachable_bank(here, log) if here is not None else None
    if bank_tile is None:
        log(no_bank_msg)
        return False
    # Why: banking.open honours Shantay's Bank chest (plus its continue) and other non-booth access.
    # Why: hardcoding "Bank booth" / Use-quickly looped forever at Shantay during Tourist Trap buys.
    opened = yield from banking.open(stand=bank_tile, log=log)
    return opened


# Why: distance_to is a plan distance, so the floor below a first-storey shop reads as 4 tiles from it (the Magic Guild
# counter was directly overhead while the step failed 23 times).
def ensure_at(anchor, radius, log):
    """Walks within radius of anchor, on its level, unless already there. Use with yield from."""
    here = game.tile()
    if here is not None and here.level == anchor.level and anchor.distance_to(here) <= radius:
        return True
    walked = yield from traversal.walk_resilient(anchor, radius=radius, attempts=3, timeout_ms=90000, log=log)
    return walked


def run_maybe(result):
    """The result of a call that may be a generator, such as a custom step's run. Use with yield from."""
    if is_generator(result):
        result = yield from result
    return result


def _try_take(item):
    before = inventory.count(item)
    g = ground_items.query().name(item).within(12).nearest()
    if g is None or not g.interact('Take'):
        return False
    taken = yield from execution.delay_until(lambda: inventory.count(item) > before, 8000)
    return taken


def _grab_ground(step, log):
    # Why: arriving at the spawn isn't a take; Cook's egg logged grab success with an empty pen.
    # Why: re-query after the walk and Take if it's there, otherwise the gather is still outstanding.
    taken = yield from _try_take(step.item)
    if taken:
        return True
    walked = yield from ensure_at(step.anchor, 2, log)
    if not walked:
        return False
    taken = yield from _try_take(step.item)
    if taken:
        return True
    if step.wait_if_missing:
        # Why: rs2b0t paused 2 ticks, so a quest whose only spawn another pick had just emptied failed 8 steps inside one
        # respawn and parked 3 times: Plague City's single bucket spawn gave the quest up in 15 seconds. It waits here.
        respawned = yield from _await_spawn(step.item)
        if respawned:
            taken = yield from _try_take(step.item)
            return taken
    return False


# Long enough for a ground spawn's respawn, which the server counts in ticks; upkeep is pumped meanwhile.
RESPAWN_WAIT_TICKS = 200


def _await_spawn(item):
    from rs2004.catalogs.tasks import sustain
    for _ in range(RESPAWN_WAIT_TICKS):
        if ground_items.query().name(item).within(12).nearest() is not None:
            return True
        if execution.event_signal.pending():
            return False
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return False


def _pick_loc(step, log):
    before = inventory.count(step.item)
    loc = locs.query().name(step.loc).action(step.op).within(10).nearest()
    if loc is None:
        walked = yield from ensure_at(step.anchor, 2, log)
        return walked
    if not loc.interact(step.op):
        return False
    picked = yield from execution.delay_until(lambda: inventory.count(step.item) > before, 8000)
    return picked


def _interact_loc(step, log):
    loc = locs.query().name(step.loc).action(step.op).within(10).nearest()
    if loc is None:
        walked = yield from ensure_at(step.anchor, 2, log)
        return walked
    if not loc.interact(step.op):
        return False
    if step.expect_item is not None:
        got = yield from execution.delay_until(lambda: inventory.contains(step.expect_item), 8000)
        return got
    yield from execution.delay_ticks(3)
    return True


def _await_product(step, before_product):
    if step.product is not None:
        made = yield from execution.delay_until(lambda: inventory.count(step.product) > before_product, 10000)
        return made
    yield from execution.delay_ticks(3)
    return True


def _use_on(step, log):
    if step.target_kind == 'item':
        held = inventory.first(step.item)
        if held is None:
            log(f"use_on: no '{step.item}' in the pack")
            return False
        target_item = inventory.first(step.target)
        if target_item is None:
            log(f"use_on: no '{step.target}' in the pack")
            return False
        before_product = inventory.count(step.product) if step.product is not None else 0
        if not held.use_on(target_item):
            return False
        made = yield from _await_product(step, before_product)
        return made
    walked = yield from ensure_at(step.anchor, 4, log)
    if not walked:
        return False
    held = inventory.first(step.item)
    if held is None:
        log(f"use_on: no '{step.item}' in the pack")
        return False
    if step.target_kind == 'npc':
        target = npcs.query().name(step.target).within(10).nearest()
    else:
        target = locs.query().name(step.target).within(10).nearest()
    if target is None:
        log(f"use_on: no '{step.target}' near the anchor")
        return False
    before_product = inventory.count(step.product) if step.product is not None else 0
    if not held.use_on(target):
        return False
    made = yield from _await_product(step, before_product)
    return made


def _withdraw(step, log):
    opened = yield from open_bank_leg('withdraw: no known bank', step.bank, log)
    if not opened:
        return False
    ok = True
    for it in step.items:
        id = it.get('id')
        if id is None:
            withdrawn = yield from bank.withdraw_x(it['name'], it['qty'])
        else:
            withdrawn = yield from bank.withdraw_x_by_id(id, it['qty'])
        if not withdrawn:
            exact = '' if id is None else f' (id {id})'
            log(f"withdraw: '{it['name']}'{exact} x{it['qty']} failed")
            ok = False
    if not step.leave_open:
        yield from modals.close()
    return ok


def _deposit(step, log):
    opened = yield from open_bank_leg('deposit: no known bank', step.bank, log)
    if not opened:
        return False
    keep_ids = set(step.keep_ids or [])
    keep = [k.lower() for k in step.keep]
    exact = step.exact_keep

    def unkept(name, id):
        if id in keep_ids:
            return False
        n = name.lower()
        for k in keep:
            if (n == k) if exact else (k in n):
                return False
        return True

    yield from bank.deposit_all_matching(unkept)
    if not step.leave_open:
        yield from modals.close()
    return True


def _buy(step, log):
    before = inventory.count(step.item)
    purse = buy_purse_top_up(inventory.count('Coins'), step.est_gp)
    if purse['need']:
        # Why: reachable_bank picks by walking cost, and Shilo's teller has no booth behind its map icon, so
        # banking.open needs the npc access the location declares.
        opened = yield from open_bank_leg('buy: no known bank for coins', step.bank, log)
        if not opened:
            return False
        # Why: withdraw_x adds its count on top of the pack, so asking for the full target draws it twice (Legends'
        # float plus a guild estimate carried 110k into a level-187 demon fight).
        yield from bank.withdraw_x('Coins', purse['draw'])
        yield from modals.close()
        if inventory.count('Coins') < step.est_gp:
            log(f'buy: bank could not cover {step.est_gp} gp for {step.item}')
            return False
    walked = yield from ensure_at(step.shop.anchor, 3, log)
    if not walked:
        return False
    opened = yield from shop.open(step.shop.npc)
    if not opened:
        log(f"buy: could not open {step.shop.npc}'s shop near the anchor")
        return False
    yield from shop.buy(step.item, step.qty)
    yield from shop.close()
    return inventory.count(step.item) > before


def rock_type_of(rock):
    """The ROCK_TYPES key for a rock or its ore: 'Iron ore' is 'Iron'."""
    return rock[:-4] if rock.lower().endswith(' ore') else rock


def _mine_rock(step, log):
    before = inventory.count(step.item)
    rock_type = rock_type_of(step.rock)
    rock_ids = ROCK_TYPES.get(rock_type)
    if rock_ids is None:
        rock_ids = QUEST_ROCK_TYPES.get(rock_type)
    if rock_ids is None:
        log(f"mine_rock: no rock-id mapping for '{rock_type}'")
        return False
    id_set = set(rock_ids)
    rock = locs.query().where(lambda l: l.id in id_set).action('Mine').within(10).nearest()
    if rock is None:
        walked = yield from ensure_at(step.anchor, 3, log)
        return walked
    if not rock.interact('Mine'):
        return False
    mined = yield from execution.delay_until(lambda: inventory.count(step.item) > before, 20000)
    return mined


def execute_step(step, hops, log):
    """Runs the step, walking across hops where a walk needs them. True when it worked. Use with yield from."""
    kind = step.kind
    if kind == 'talk':
        reached = yield from goto_npc(step.stop, hops, log)
        if not reached:
            return False
        talked = yield from talk_through(step.stop.npc, step.stop.prefer, log, step.stop.gap_ms)
        return talked
    if kind == 'grab_ground':
        result = yield from _grab_ground(step, log)
        return result
    if kind == 'pick_loc':
        result = yield from _pick_loc(step, log)
        return result
    if kind == 'interact_loc':
        result = yield from _interact_loc(step, log)
        return result
    if kind == 'use_on':
        result = yield from _use_on(step, log)
        return result
    if kind == 'equip':
        result = yield from equipment.equip(step.item)
        return result
    if kind == 'scan_bank':
        result = yield from open_bank_leg('scan_bank: no known bank', step.bank, log)
        return result
    if kind == 'withdraw':
        result = yield from _withdraw(step, log)
        return result
    if kind == 'deposit':
        result = yield from _deposit(step, log)
        return result
    if kind == 'buy':
        result = yield from _buy(step, log)
        return result
    if kind == 'mine_rock':
        result = yield from _mine_rock(step, log)
        return result
    if kind == 'custom':
        result = yield from run_maybe(step.run(log))
        return result
    if kind == 'wait':
        yield from execution.delay_ticks(2)
        return True
    if kind == 'done':
        return True
    log(f'unknown step kind {repr(kind)}')
    return False

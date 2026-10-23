"""Thieving: East Ardougne's Baker's stall, the market's pickpocket targets, and the rules a thiever banks and
eats by. Ported from rs2b0t's api/thieving/CakeStall.ts, cakeStallData.ts, stealRules.ts and targets.ts (MIT,
see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.pack import count_matching
from rs2004.catalogs.record import Record
from rs2004.catalogs.tables import PICKPOCKET_TARGETS
from rs2004.entities import locs
from rs2004.events import events
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal

# The stall, the two tiles it's robbed from, and where to run to.
STALL_TILE = Tile(2667, 3310, 0)
STAND = Tile(2668, 3312, 0)
STAND_ALT = Tile(2669, 3310, 0)
FLEE_TILE = Tile(2655, 3298, 0)
STALL_NAME = "Baker's stall"
STALL_OP = 'Steal from'
CAKE_ITEMS = ['cake', 'bread', 'chocolate slice']
# After combat the market's stalls refuse a thief this long.
LOCKOUT_TICKS = 10
RESET_AFTER_REFUSALS = 3

STEAL_DEADLINE_MS = 90000
CLAIM_TIMEOUT_MS = 15000
NEAR_STALL = 2
RESOLVE_MS = 2400
RESTOCK_WAIT_MS = 8000
ATTEMPT_TEXT = 'you attempt to steal'
LOCKOUT_TEXT = "can't steal from the market stall during combat"


def classify_steal(gained, combat, lockout_seen, attempt_seen):
    """How a steal went: 'success', 'caught', 'lockout', 'refused' or 'timeout'."""
    if gained:
        return 'success'
    if combat:
        return 'caught'
    if lockout_seen:
        return 'lockout'
    if attempt_seen:
        return 'refused'
    return 'timeout'


def should_reset(consecutive_refusals):
    """Whether a watched stand is given up for the other one."""
    return consecutive_refusals >= RESET_AFTER_REFUSALS


# Where each of the market's pickpocket targets is worked, and how far from it they wander.
SPOTS = {
    'Guard': Record({'anchor': Tile(2661, 3306, 0), 'leash': 19}),
    'Knight of Ardougne': Record({'anchor': Tile(2661, 3306, 0), 'leash': 29}),
    'Paladin': Record({'anchor': Tile(2655, 3311, 0), 'leash': 12}),
    'Hero': Record({'anchor': Tile(2657, 3311, 0), 'leash': 17}),
}
HOSTILE_NAMES = ['Guard', 'Knight of Ardougne', 'Paladin', 'Hero']


def target_spot(target):
    return SPOTS.get(target, SPOTS['Guard'])


def required_thieving(target):
    """The Thieving level a pickpocket target needs; 1 for one the table lacks."""
    for entry in PICKPOCKET_TARGETS:
        if entry.name == target:
            return entry.level
    return 1


def is_hostile_attacker(candidate, max_distance):
    """A market guard or knight that's fighting you, and near: one with name, in_combat, distance, actions and
    targets_another_player, as values or methods."""
    def read(name):
        value = getattr(candidate, name, None)
        return value() if callable(value) else value

    name = read('name')
    return (name is not None and name in HOSTILE_NAMES and read('in_combat') and not read('targets_another_player')
            and read('distance') <= max_distance and 'Attack' in (read('actions') or []))


def choose_target(candidates_nearest_first, reachable):
    """The nearest reachable candidate as target, or, when none is, the nearest as blocked: a Record of both."""
    for candidate in candidates_nearest_first:
        if reachable(candidate):
            return Record({'target': candidate, 'blocked': None})
    blocked = candidates_nearest_first[0] if candidates_nearest_first else None
    return Record({'target': None, 'blocked': blocked})


THIEVER_BANKING_OPTIONS = ['None', 'Auto']
# A failed pickpocket stuns you this many ticks; the next click can only walk after them.
STUN_COMBAT_TICKS = 9


def next_withdraw_chunk(need):
    """The next withdrawal toward need more: ('x', count) above 10, else ('op', 'Withdraw-10', -5 or -1), or None."""
    if need <= 0:
        return None
    if need > 10:
        return ('x', need)
    if need >= 10:
        return ('op', 'Withdraw-10')
    if need >= 5:
        return ('op', 'Withdraw-5')
    return ('op', 'Withdraw-1')


def withdraw_to(name, target, count_in_inv=None):
    """Withdraws the item until the backpack holds target, or the bank or backpack stops it. The units withdrawn.
    Use with yield from."""
    count = count_in_inv if count_in_inv is not None else (lambda: inventory.count(name))
    start = count()
    for _ in range(40):
        if count() >= target or inventory.is_full():
            break
        before = count()
        need = target - before
        chunk = next_withdraw_chunk(need)
        if chunk is None:
            break
        if chunk[0] == 'x':
            withdrew = yield from bank.withdraw_x(name, chunk[1])
            if withdrew and count() > before:
                continue
            fallback = next_withdraw_chunk(min(need, 10))
            if fallback is None or fallback[0] != 'op':
                break
            chunk = fallback
        bank.withdraw(name, chunk[1])
        gained = yield from execution.delay_until(lambda: count() > before, 2500)
        if not gained:
            break
    return count() - start


def close_bank_and_confirm_count(expected, count):
    """Closes the bank and waits for the backpack to show expected. Use with yield from."""
    closed = yield from bank.close()
    if not closed:
        return False
    yield from execution.delay_ticks(1)
    confirmed = yield from execution.delay_until(lambda: count() >= expected, 3000)
    return confirmed


def auto_food_banking(mode):
    return mode.strip().lower() == 'auto'


def food_matches(name, keyword):
    wanted = keyword.strip().lower()
    return len(wanted) > 0 and wanted in (name or '').lower()


def count_food(items, keyword):
    return sum([i.count for i in items if food_matches(i.name, keyword)])


def should_restock_food(enabled, food_count, restock_at, bankable_pack_full):
    return enabled and (food_count <= restock_at or bankable_pack_full)


def safe_to_steal(hp_fraction, eat_at, food_count):
    return hp_fraction >= eat_at or food_count > 0


def can_steal_now(food_count, hp, min_eat_hp, suicide):
    """Suicide mode steals on with no food and no rest."""
    return suicide or food_count > 0 or hp > min_eat_hp


def carried_cakes():
    """The stall's food in the backpack."""
    return count_matching(inventory.items(), CAKE_ITEMS)


def needs_cake_restock(target):
    """Whether the stall still owes the backpack food, as steal_cakes measures it."""
    return not inventory.is_full() and carried_cakes() < target


def _stocked_stall():
    return locs.query().name(STALL_NAME).action(STALL_OP).where(lambda l: l.tile().distance_to(STALL_TILE) <= 3).nearest()


# What the server said since the last steal. One subscription for the VM: a steal_cakes the random event
# guardian drops can't unsubscribe, since pocketpy has no finally.
_seen = {'attempt': False, 'lockout': False, 'listening': False}


def _hear(e):
    text = (e.text or '').lower()
    if ATTEMPT_TEXT in text:
        _seen['attempt'] = True
    if LOCKOUT_TEXT in text:
        _seen['lockout'] = True


def _listen():
    if not _seen['listening']:
        _seen['listening'] = True
        events.on('chat_message', _hear)


def steal_cakes(abort, set_status, log, fill_to=None, should_eat=None, locked_out_until=None, on_steal=None, on_reset=None):
    """Steals from the Baker's stall until the backpack is full, or holds fill_to of its food. Gives 'stocked',
    'combat' (caught, or attacked), 'aborted' (abort() or should_eat()) or 'no-progress' after 90 s. Use with
    yield from."""
    _listen()
    stand = STAND
    refusals = 0
    self_lockout = 0
    deadline = _core.step_time() + STEAL_DEADLINE_MS
    while _core.step_time() < deadline:
        if abort() or (should_eat is not None and should_eat()):
            return 'aborted'
        if game.in_combat():
            return 'combat'
        if inventory.is_full() or (fill_to is not None and carried_cakes() >= fill_to):
            log(f'stocked {carried_cakes()} stall food ({inventory.used()} slots)')
            return 'stocked'

        until = max(locked_out_until() if locked_out_until is not None else 0, self_lockout)
        if game.tick() < until:
            set_status('waiting out the post-combat steal lockout')
            yield from execution.delay_until(lambda: game.tick() >= until or abort(), 12000)
            continue

        here = game.tile()
        if here is not None and stand.distance_to(here) > 0:
            yield from traversal.walk_to(stand, radius=0, timeout_ms=CLAIM_TIMEOUT_MS, log=lambda m: log(f'  {m}'))
            now = game.tile()
            if now is None or STALL_TILE.distance_to(now) > NEAR_STALL:
                log('claim fell short' + (f' at ({now.x},{now.z})' if now is not None else '') + '; not stealing from the market side')
                yield from execution.delay_ticks(1)
                continue

        stall = _stocked_stall()
        if stall is None:
            log('stall emptied; waiting for the restock')
            yield from execution.delay_until(lambda: _stocked_stall() is not None or abort(), RESTOCK_WAIT_MS)
            continue

        _seen['attempt'] = False
        _seen['lockout'] = False
        before = carried_cakes()
        if fill_to is not None:
            set_status(f'stealing cake ({before}/{fill_to})')
        else:
            set_status(f'stealing cake ({inventory.used()}/{inventory.used() + inventory.free()} slots)')
        if not stall.interact(STALL_OP):
            refusals += 1
            yield from execution.delay_ticks(1)
        else:
            yield from execution.delay_until(lambda: carried_cakes() > before or game.in_combat() or _seen['lockout'], RESOLVE_MS)
            outcome = classify_steal(carried_cakes() > before, game.in_combat(), _seen['lockout'], _seen['attempt'])
            if outcome == 'success':
                refusals = 0
                if on_steal is not None:
                    on_steal()
                continue
            if outcome == 'caught':
                return 'combat'
            if outcome == 'lockout':
                self_lockout = game.tick() + LOCKOUT_TICKS
                continue
            refusals += 1

        if should_reset(refusals):
            stand = STAND if stand == STAND_ALT else STAND_ALT
            set_status('watched; swapping stands')
            log(f'{refusals} refused steals; swapping to the stand at ({stand.x},{stand.z})')
            if on_reset is not None:
                on_reset()
            refusals = 0
    return 'no-progress'

"""Shantay to the queen and back: rs2b0t's scripts/JiveKQ/route.ts (MIT, see thirdparty/rs2b0t). The Wait functions
are used with yield from."""

import time

from bots.jivekq.loadout import DUELING_RINGS, PASS
from bots.jivekq.loot import step_to
from bots.jivekq.policy import SURFACE, UPPER, in_lair, in_nest, near

CAMELOT = Tile(2757, 3478, 0)
DUEL_ARENA = Tile(3315, 3235, 0)
SHANTAY = Tile(3304, 3120, 0)
DUEL_ARENA_OPTION = 'Al Kharid Duel Arena.'
DISCLAIMER = 1848
GATE = 4031
# The rope's loc before and after it's tied, at each entrance.
ROPE_SPOT = {'surface': 3827, 'upper': 3830}
ROPE_TIED = {'surface': 3828, 'upper': 3831}


def walk(tile, radius, log):
    if near(game.tile(), tile, radius):
        return True
    arrived = yield from traversal.walk_resilient(tile, radius=radius, attempts=2, timeout_ms=90000, max_budget=120000, policy=traversal.pure_walk, log=log)
    return arrived


def step(tile):
    return step_to(tile)


def camelot():
    """Teleports to Camelot, giving up on the wait early if a hit lands."""
    if near(game.tile(), CAMELOT, 4):
        return True
    hp = skills.effective('hitpoints')
    if not game.teleport('Camelot'):
        return False
    yield from execution.delay_until_ticks(lambda: near(game.tile(), CAMELOT, 4) or skills.effective('hitpoints') < hp, 4)
    return near(game.tile(), CAMELOT, 4)


def _arena_option():
    return DUEL_ARENA_OPTION in chat_dialog.options()


def duel_arena():
    """Rubs a Ring of dueling to the Duel Arena; refuses at 31 hp or under, where a hit on the way could kill."""
    if near(game.tile(), DUEL_ARENA, 4):
        return True
    if not _arena_option():
        ring = None
        for i in inventory.items():
            if i.id in DUELING_RINGS:
                ring = i
                break
        hp = skills.effective('hitpoints')
        if ring is None or not ring.interact('Rub'):
            return False
        yield from execution.delay_until_ticks(lambda: _arena_option() or skills.effective('hitpoints') < hp, 3)
        if skills.effective('hitpoints') <= 31:
            return False
    chose = yield from chat_dialog.choose_option(DUEL_ARENA_OPTION)
    if not chose:
        return False
    hp = skills.effective('hitpoints')
    yield from execution.delay_until_ticks(lambda: near(game.tile(), DUEL_ARENA, 4) or skills.effective('hitpoints') < hp, 4)
    return near(game.tile(), DUEL_ARENA, 4)


def buy_pass(log):
    if inventory.count_by_id(PASS) > 0:
        return True
    arrived = yield from walk(SHANTAY, 2, log)
    if not arrived:
        return False
    opened = yield from shop.open('Shantay')
    if not opened:
        return False
    bought = yield from shop.buy('Shantay pass', 1)
    yield from shop.close()
    if bought != 1:
        raise RuntimeError('Could not buy a Shantay pass')
    log('bought Shantay pass')
    return True


def _past_gate():
    here = game.tile()
    return here is not None and here.z < 3117


def _discard_disclaimer():
    item = None
    for i in inventory.items():
        if i.id == DISCLAIMER:
            item = i
            break
    if item is None:
        return True
    if not item.interact('Drop'):
        return False
    dropped = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(DISCLAIMER) == 0, 2)
    return dropped


def pass_gate(log):
    """Through the Shantay Pass on the prepared pass, answering the poster, and drops the disclaimer it hands over."""
    if _past_gate():
        done = yield from _discard_disclaimer()
        return done
    if inventory.count_by_id(PASS) == 0:
        raise RuntimeError('Prepared Shantay pass missing')
    arrived = yield from walk(SHANTAY, 2, log)
    if not arrived:
        return False
    gate = locs.query().where(lambda l: l.id == GATE).nearest()
    if gate is None or not gate.interact('Go-through'):
        return False
    deadline = time.time() + 25
    while time.time() < deadline:
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        elif len(chat_dialog.options()) > 0:
            yield from chat_dialog.choose_option("Yeah, that poster doesn't scare me!")
        elif _past_gate():
            done = yield from _discard_disclaimer()
            return done
        else:
            yield from execution.delay_ticks(1)
    return False


def rope_ready(gate):
    return locs.query().where(lambda l: l.id == ROPE_TIED[gate]).nearest() is not None


def place_rope(gate, log):
    if rope_ready(gate):
        return True
    loc = locs.query().where(lambda l: l.id == ROPE_SPOT[gate]).nearest()
    rope = inventory.first('Rope')
    if loc is None or rope is None or not rope.use_on(loc):
        return False
    tied = yield from execution.delay_until(lambda: rope_ready(gate), 4000)
    if not tied:
        return False
    log(f'placed {gate} rope')
    return True


def descend(gate):
    loc = locs.query().where(lambda l: l.id == ROPE_TIED[gate]).nearest()
    if loc is None or not loc.interact('Climb-down'):
        return False
    if gate == 'surface':
        down = yield from execution.delay_until_ticks(lambda: in_nest(game.tile()), 3)
    else:
        down = yield from execution.delay_until_ticks(lambda: in_lair(game.tile()), 3)
    return down


def gate_tile(gate):
    return SURFACE if gate == 'surface' else UPPER

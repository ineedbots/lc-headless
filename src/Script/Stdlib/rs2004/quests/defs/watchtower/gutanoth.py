"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/gutanoth.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.navigation import navigator
from rs2004.quests.defs.watchtower.areas import WT_CAVES, WT_ITEM, WT_LOC, WT_NPC, WT_TILE, watchtower_area
from rs2004.quests.defs.watchtower.scene import settle_scene
from rs2004.quests.exec.primitives import drive_dialog, talk_strict, talk_through
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['CHASM_TOLL', 'show_relic_to_guard', 'steal_rock_cake', 'cross_battlement', 'leave_lower_city', 'jump_back', 'ask_riddle', 'answer_riddle', 'gold_gate_needs_payment', 'cross_east_gate', 'leave_east_gate', 'leave_city']

CHASM_TOLL = 20


def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def loc_near(id, op, within=8):
    return locs.query().where(lambda loc: loc.id == id).action(op).within(within).nearest()


# Why: an op that opens a dialogue does so a tick later.
# Why: Wait for dialogue to appear before selecting an NPC, or the driver may start an unrelated conversation.
def await_dialogue(what, log):
    """Wait for the dialogue an op opened."""
    _w1 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if _w1:
        return True
    log(f'{what} did not open a dialogue')
    return False


def past_relic_gate():
    """West of the relic gate is inside the city; the guard throws you east onto the hill."""
    tile = game.tile()
    return tile is not None and tile.x <= 2503 and tile.z >= 3058 and tile.z <= 3066


def offer_relic(log):
    _w2 = yield from traversal.walk_resilient(WT_TILE.GATE_RELIC_STAND, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w2):
        return False
    guard = npcs.query().name(WT_NPC.OGRE_GUARD).nearest()
    relic = ([item for item in inventory.items() if item.id == WT_ITEM.OGRE_RELIC.id] or [None])[0]
    if not guard or not relic:
        log('no ogre guard at the north-west gate, or no relic in the pack')
        return False
    if not (relic.use_on(guard)):
        return False
    _w3 = yield from await_dialogue('the north-west gate guard', log)
    if _w3:
        yield from talk_through(WT_NPC.OGRE_GUARD, [], log)
    _result4 = yield from execution.delay_until(lambda: past_relic_gate(), 10000)
    return _result4


def show_relic_to_guard(log):
    if held_id(WT_ITEM.OGRE_RELIC.id) == 0:
        log('no Ogre relic in the pack')
        return False
    _w5 = yield from offer_relic(log)
    if _w5:
        yield from settle_scene()
        return True
    # First contact only records that he wants a sign of friendship and throws you down the hill; the crossing needs a second approach.
    log('guard threw us down the hill — returning to show the relic again')
    _w6 = yield from offer_relic(log)
    if not (_w6):
        return False
    yield from settle_scene()
    return True


def steal_rock_cake(log):
    if held_id(WT_ITEM.ROCK_CAKE.id) > 0:
        return True
    for attempt in range(8):
        # Re-assert the stand each pass: the trader wanders, and being pushed within 3 tiles of him turns every steal into a refusal.
        _w7 = yield from traversal.walk_resilient(WT_TILE.ROCK_CAKE_STALL, radius=0, attempts=3, timeout_ms=300000, log=log)
        if not (_w7):
            return False
        stall = loc_near(WT_LOC.ROCK_CAKE_STALL, 'Steal-From', 6)
        if stall and (stall.interact('Steal-From')):
            _w8 = yield from execution.delay_until(lambda: held_id(WT_ITEM.ROCK_CAKE.id) > 0, 6000)
            if _w8:
                return True
        # The counter swaps to its empty form for 12 ticks after a theft.
        yield from execution.delay_ticks(6)
    log('could not steal a rock cake — the ogre trader may be guarding the stall')
    return False


def cross_battlement(log):
    if watchtower_area(game.tile()) == 'lowerCity':
        return True
    _w9 = yield from traversal.walk_resilient(WT_TILE.BATTLEMENT_GUARD, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w9):
        return False
    guard = npcs.query().name(WT_NPC.OGRE_GUARD).nearest()
    if not guard:
        log('no battlement guard in range')
        return False
    # Why: he ignores the cake until he has asked for a gift, as opnpcu only accepts it once the market bits are 1, so the talk comes first.
    # Why: talking while already holding the cake completes the exchange in one go.
    if guard.interact('Talk-to'):
        _w10 = yield from await_dialogue('the battlement guard', log)
        if _w10:
            # The unmatched option here is "Not if I can help it."
            yield from talk_strict(WT_NPC.OGRE_GUARD, ['But I am a friend to ogres...'], log)
    _w11 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'lowerCity', 10000)
    if _w11:
        yield from settle_scene()
        return True
    # Otherwise he has only asked; hand the cake over now.
    cake = ([item for item in inventory.items() if item.id == WT_ITEM.ROCK_CAKE.id] or [None])[0]
    if cake and (cake.use_on(guard)):
        _w12 = yield from await_dialogue('the battlement guard', log)
        if _w12:
            yield from drive_dialog([], log)
    _w13 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'lowerCity', 10000)
    if _w13:
        yield from settle_scene()
        return True
    # Handing the cake over normally auto-climbs; climb it ourselves if it did not.
    wall = loc_near(WT_LOC.BATTLEMENT, 'Climb-over', 8)
    if not wall or not (wall.interact('Climb-over')):
        return False
    _w14 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'lowerCity', 10000)
    if not (_w14):
        return False
    yield from settle_scene()
    return True


def leave_lower_city(log):
    """The battlement climbs both ways once the market gift is paid."""
    if watchtower_area(game.tile()) != 'lowerCity':
        return True
    _w15 = yield from traversal.walk_resilient(WT_TILE.BATTLEMENT_INSIDE, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w15):
        return False
    wall = loc_near(WT_LOC.BATTLEMENT, 'Climb-over', 8)
    if not wall or not (wall.interact('Climb-over')):
        log('no battlement in range to climb back over')
        return False
    _w16 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'lowerCity', 12000)
    if not (_w16):
        return False
    yield from settle_scene()
    return True


def jump_chasm(log):
    if watchtower_area(game.tile()) == 'cityGuard':
        return True
    if held_id(WT_ITEM.COINS.id) < CHASM_TOLL:
        log(f'need {CHASM_TOLL} gp for the chasm toll')
        return False
    _w17 = yield from cross_battlement(log)
    if not (_w17):
        return False
    _w18 = yield from traversal.walk_resilient(WT_TILE.JUMP_STAND, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w18):
        return False
    rock = loc_near(WT_LOC.JUMP_IN, 'Jump-From', 6)
    if not rock or not (rock.interact('Jump-From')):
        log('no Jump-From rock at the chasm — the level-1 loc may not be clickable from level 0')
        return False
    _w19 = yield from await_dialogue('the chasm guard', log)
    if not (_w19):
        return False
    _w20 = yield from talk_strict(WT_NPC.OGRE_GUARD, ["Okay, I'll pay it."], log)
    if not (_w20):
        return False
    _w21 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'cityGuard', 12000)
    if not (_w21):
        return False
    yield from settle_scene()
    return True


def jump_back(log):
    if watchtower_area(game.tile()) != 'cityGuard':
        return True
    _w22 = yield from traversal.walk_resilient(WT_TILE.JUMP_BACK_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w22):
        return False
    rock = loc_near(WT_LOC.JUMP_OUT, 'Jump-From', 6)
    if not rock or not (rock.interact('Jump-From')):
        log('no Jump-From rock back out of the city-guard pocket')
        return False
    _w23 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'cityGuard', 12000)
    if not (_w23):
        return False
    yield from settle_scene()
    return True


def ask_riddle(log):
    _w24 = yield from jump_chasm(log)
    if not (_w24):
        return False
    _w25 = yield from reach.npc_dialog(WT_NPC.CITY_GUARD, WT_TILE.CITY_GUARD, log=log)
    if (_w25) != 'done':
        return False
    # The unmatched option here is "I am an ogre killer come to destroy you!"
    _result26 = yield from talk_strict(WT_NPC.CITY_GUARD, ['I seek passage into the skavid caves.', 'I have lost the map you gave me.'], log)
    return _result26


def answer_riddle(log):
    if held_id(WT_ITEM.DEATH_RUNE.id) == 0:
        log('no Death rune to answer the riddle with')
        return False
    _w27 = yield from jump_chasm(log)
    if not (_w27):
        return False
    _w28 = yield from traversal.walk_resilient(WT_TILE.CITY_GUARD, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w28):
        return False
    guard = npcs.query().name(WT_NPC.CITY_GUARD).nearest()
    rune = ([item for item in inventory.items() if item.id == WT_ITEM.DEATH_RUNE.id] or [None])[0]
    if not guard or not rune or not (rune.use_on(guard)):
        return False
    _w29 = yield from await_dialogue('the city guard', log)
    if _w29:
        yield from talk_through(WT_NPC.CITY_GUARD, [], log)
    _result30 = yield from execution.delay_until(lambda: held_id(WT_ITEM.SKAVID_MAP.id) > 0, 10000)
    return _result30


# Why: the east gate is the only way to cave 6's side of the city, and its guard wants a bar of gold.
# Why: like the relic gate he refuses first contact and throws you down the hill, so the crossing takes 2 approaches.
# Why: the region beyond overlaps the battlement side geographically, so membership is decided by asking the pathfinder.
def past_east_gate():
    """True once past the east gate."""
    here = game.tile()
    if not here:
        return False
    cave6 = ([cave for cave in WT_CAVES if cave.index == 6] or [None])[0]
    return navigator.find_path(here, cave6.stand).ok


def through_east_gate():
    tile = game.tile()
    return tile is not None and tile.z <= 3027 and tile.x >= 2540


def back_out_of_east_gate():
    tile = game.tile()
    return tile is not None and tile.z >= 3029


def offer_gold_bar(log):
    _w31 = yield from traversal.walk_resilient(WT_TILE.EAST_GATE_STAND, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w31):
        return False
    guard = npcs.query().name(WT_NPC.OGRE_GUARD).nearest()
    bar = ([item for item in inventory.items() if item.id == WT_ITEM.GOLD_BAR.id] or [None])[0]
    if not guard or not bar:
        log('no ogre guard at the east gate, or no gold bar in the pack')
        return False
    if not (bar.use_on(guard)):
        return False
    _w32 = yield from await_dialogue('the east gate guard', log)
    if _w32:
        yield from talk_through(WT_NPC.OGRE_GUARD, [], log)
    _result33 = yield from execution.delay_until(through_east_gate, 10000)
    return _result33


def cross_east_gate(log, paid=False):
    _w34 = past_east_gate()
    if _w34:
        remember_gate_payment(False)
        return True
    if paid or gold_gate_needs_payment() == False or held_id(WT_ITEM.GOLD_BAR.id) == 0:
        _w35 = yield from traversal.walk_resilient(WT_TILE.EAST_GATE_STAND, radius=1, attempts=3, timeout_ms=180000, log=log)
        if not (_w35):
            return False
        gate = loc_near(WT_LOC.GATE_EAST, 'Open', 6)
        mark = game_messages.mark()
        if not gate or not (gate.interact('Open')):
            return False

        def crossed():
            return (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) <= 3027 and (((game.tile().x if game.tile() is not None else None) if (game.tile().x if game.tile() is not None else None) is not None else 0)) >= 2540

        yield from execution.delay_until(lambda: crossed() or chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drive_dialog([], log)
        _w36 = yield from execution.delay_until(crossed, 4000)
        if _w36:
            yield from settle_scene()
            _w37 = past_east_gate()
            if _w37:
                remember_gate_payment(False)
                return True

        if game_messages.saw_since(mark, 'guard pushes you outside the city'):
            remember_gate_payment(True)
        log('east gate did not open; a gold bar is needed if the guard refused passage')
        return False
    _w38 = yield from offer_gold_bar(log)
    if _w38:
        remember_gate_payment(False)
        yield from settle_scene()
        return True
    log('east gate guard threw us down the hill; returning to pay again')
    _w39 = yield from offer_gold_bar(log)
    if not (_w39):
        return False
    remember_gate_payment(False)
    yield from settle_scene()
    return True


def leave_east_gate(log):
    """Once the bar is paid the gate is an ordinary door, so the way out is Open."""
    if not past_east_gate():
        return True
    _w38 = yield from traversal.walk_resilient(WT_TILE.EAST_GATE_INSIDE, radius=1, attempts=3, timeout_ms=120000, log=log)
    if not (_w38):
        return False
    gate = loc_near(WT_LOC.GATE_EAST, 'Open', 6)
    if not gate or not (gate.interact('Open')):
        log('no east gate in range to open')
        return False
    _w39 = yield from execution.delay_until(back_out_of_east_gate, 12000)
    if not (_w39):
        return False
    yield from settle_scene()
    return True


def gold_gate_needs_payment():
    name = game.my_name()
    return (gate_payments.get(name) if name else None)



def remember_gate_payment(needed):
    name = game.my_name()
    if name:
        gate_payments[name] = needed



def leave_city(log):
    _w43 = past_east_gate()
    result = yield from leave_east_gate(log) if _w43 else leave_lower_city(log)
    return result



gate_payments = {}

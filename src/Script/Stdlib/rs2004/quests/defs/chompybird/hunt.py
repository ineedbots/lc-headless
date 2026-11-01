"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/hunt.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.chompybird.areas import ANY_BELLOWS, BELLOWS_IDS, CB_ID, CB_LOC, CB_LOC_ID, CB_NAME, CB_NPC, CB_TILE, in_bait_zone
from rs2004.quests.defs.chompybird.arrows import walk_to
from rs2004.quests.defs.chompybird.dialogue import clear_box
from rs2004.quests.exec.prompts import settle_scene

__all__ = ['chest_state', 'open_chest', 'catch_toad', 'watch_rantz_shoot', 'hunt_chompy']

def held(id):
    return inventory.count_by_id(id)


def held_bellows():
    return ([id for id in ANY_BELLOWS if held(id) > 0] or [None])[0]


def held_filled_bellows():
    return ([id for id in BELLOWS_IDS if held(id) > 0] or [None])[0]


def rantz_missed(text):
    lowered = text.lower()
    return 'rantz keeps missing' in lowered or "de'ese arrows are rubbish" in lowered
# Why: The chest refuses replacements while bellows are banked, so that message triggers a bank trip.
chest_state = Record({'refused': False})
CHEST_EMPTY = 'find nothing in the ogre chest'


# Why: the chest's `Unlock` is a strength roll that drains a level when it fails, so one attempt proves nothing about the rock.
def open_chest(log):
    """Lift the rock and search the ogre chest for the bellows."""
    if held_bellows() is not None:
        return True
    _w1 = yield from walk_to(CB_TILE.CHEST, 3, log)
    if not (_w1):
        return False
    mark = game_messages.mark()
    for attempt in range(6):
        if not (held_bellows() is None):
            break
        yield from settle_scene()
        yield from clear_box()
        if game_messages.saw_since(mark, CHEST_EMPTY):
            chest_state.refused = True
            log('the chest is empty — the account already owns a pair of bellows')
            return False
        open = locs.query().where(lambda l: l.id == CB_LOC_ID.CHEST_OPEN).within(8).nearest()
        if open:
            if not (open.interact('Search')):
                return False
            yield from execution.delay_until(lambda: held_bellows() is not None or game_messages.saw_since(mark, CHEST_EMPTY), 8000)
            continue
        locked = locs.query().where(lambda l: l.id == CB_LOC_ID.CHEST).within(8).nearest()
        if not locked:
            log(f'no ogre chest at ({CB_TILE.CHEST.x},{CB_TILE.CHEST.z})')
            return False
        if not (locked.interact('Unlock')):
            return False
        yield from execution.delay_until(lambda: locs.query().where(lambda l: l.id == CB_LOC_ID.CHEST_OPEN).within(8).exists(), 8000)
    yield from clear_box()
    if held_bellows() is None:
        log('the ogre chest gave up no bellows — the account may already own a pair')
        return False
    return True


# Why: the pool is a block of unwalkable floor, and `nearest()` picks a bubble in the middle with no cardinally adjacent tile, so the op is sent, accepted and never lands.
def fill_bellows(log):
    """Suck a full charge of swamp gas into the bellows."""
    if held(CB_ID.BELLOWS3) > 0:
        return True
    id = held_bellows()
    if id is None:
        log('no ogre bellows to fill')
        return False
    _w2 = yield from walk_to(CB_TILE.SWAMP, 2, log)
    if not (_w2):
        return False
    yield from settle_scene()
    bubbles = locs.query().name(CB_LOC.BUBBLES).where(lambda l: l.tile().distance_to(CB_TILE.BUBBLE) <= 1).within(6).nearest()
    bellows = ([i for i in inventory.items() if i.id == id] or [None])[0]
    if not bubbles or not bellows:
        log(f'no usable Swamp bubbles beside ({CB_TILE.SWAMP.x},{CB_TILE.SWAMP.z})')
        return False
    if not (bellows.use_on(bubbles)):
        return False
    _result3 = yield from execution.delay_until(lambda: held(CB_ID.BELLOWS3) > 0, 10000)
    return _result3


# Why: a toad standing in the pool can't be reached, so a failed inflate tries the next one out.
def inflate_one(pick, log):
    _c4 = held_filled_bellows() is None
    if _c4:
        _w5 = yield from fill_bellows(log)
        _c4 = not (_w5)
    if _c4:
        return False
    id = held_filled_bellows()
    if id is None:
        log('the bellows took no swamp gas')
        return False
    _w6 = yield from walk_to(CB_TILE.SWAMP, 2, log)
    if not (_w6):
        return False
    yield from settle_scene()
    toads = npcs.query().name(CB_NPC.TOAD).within(12).results()
    toad = toads[pick % len(toads)] if len(toads) > 0 else None
    bellows = ([i for i in inventory.items() if i.id == id] or [None])[0]
    if not toad or not bellows:
        log('no Swamp toad in reach of the pool')
        return False
    before = held(CB_ID.TOAD)
    if not (bellows.use_on(toad)):
        return False
    _result7 = yield from execution.delay_until(lambda: held(CB_ID.TOAD) > before, 12000)
    return _result7


# Why: a placed toad lasts about 100 ticks and only 1 roll in 6 brings a chompy, so one toad per pool trip spends the run walking.
# Why: 3 is the ceiling; inflating a fourth lets one of the others hop away.
def catch_toad(log):
    """Fill the pack with bait, up to the 3 the quest lets you carry."""
    for attempt in range(5):
        if not (held(CB_ID.TOAD) < 3):
            break
        yield from inflate_one(attempt, log)
    return held(CB_ID.TOAD) > 0


def bait_placed():
    return npcs.query().name(CB_NAME.TOAD).within(16).exists()


def drop_bait(log):
    """Put a bloated toad down in the clearing Rantz pointed at."""
    if held(CB_ID.TOAD) == 0:
        log('no Bloated toad to place')
        return False
    _c8 = not in_bait_zone(game.tile())
    if _c8:
        _w9 = yield from walk_to(CB_TILE.BAIT, 1, log)
        _c8 = not (_w9)
    if _c8:
        return False
    yield from settle_scene()
    if not in_bait_zone(game.tile()):
        log('not standing inside the bait clearing — the toad would be refused')
        return False
    toad = ([i for i in inventory.items() if i.id == CB_ID.TOAD] or [None])[0]
    if not toad:
        return False
    before = held(CB_ID.TOAD)
    # Why: `iop1` on a bloated toad is the quest's placement op, so Drop here puts it down in the clearing.
    if not (toad.interact('Drop')):
        return False
    placed = yield from execution.delay_until(lambda: held(CB_ID.TOAD) < before, 8000)
    yield from clear_box()
    return placed


# Why: Rantz only fires while you're inside 20 tiles of him and the pool is 35 tiles the other way, so the bait check is made from the clearing.
def keep_bait_down(log):
    if not in_bait_zone(game.tile()):
        _c10 = held(CB_ID.TOAD) == 0
        if _c10:
            _w11 = yield from catch_toad(log)
            _c10 = not (_w11)
        if _c10:
            return False
        _w12 = yield from walk_to(CB_TILE.BAIT, 1, log)
        if not (_w12):
            return False
        yield from settle_scene()
    if bait_placed():
        return True
    _c13 = held(CB_ID.TOAD) == 0
    if _c13:
        _w14 = yield from catch_toad(log)
        _c13 = not (_w14)
    if _c13:
        return False
    _result15 = yield from drop_bait(log)
    return _result15


def chompy_alive():
    return npcs.query().name(CB_NPC.CHOMPY).action('Attack').within(16).exists()


def chompy_dead():
    return npcs.query().name(CB_NPC.CHOMPY).action('Pluck').within(16).exists()


# Why: Rantz only fires while you're inside 20 tiles of him, so the wait happens beside the clearing.
def watch_rantz_shoot(log):
    """Bait the clearing and stand by until Rantz has fired and missed."""
    mark = game_messages.mark()
    for round in range(4):
        _w16 = yield from keep_bait_down(log)
        if not (_w16):
            return False
        fired = yield from execution.delay_until(lambda: game_messages.saw_since(mark, rantz_missed) or not bait_placed(), 60000)
        if game_messages.saw_since(mark, rantz_missed):
            log('Rantz shot at the chompy and missed')
            return True
        if not fired:
            log('nothing came to the bait in a minute — re-baiting')
    return game_messages.saw_since(mark, rantz_missed)


# Why: every shot drops its arrow at the bird's feet, so the 6 the quest leaves you are re-usable and a dry quiver is a short walk.
def recover_arrows():
    """Pick the spent arrows up off the floor."""
    taken = False
    for stack in range(4):
        spent = ground_items.query().name(CB_NAME.ARROW).within(16).nearest()
        if not spent:
            break
        before = held(CB_ID.ARROW)
        if not (spent.interact('Take')):
            break
        _w17 = yield from execution.delay_until(lambda: held(CB_ID.ARROW) > before, 8000)
        if not (_w17):
            break
        taken = True
    return taken


def arm_for_chompy(log):
    """Bow in hand and ogre arrows in the quiver."""
    if not equipment.contains(CB_NAME.BOW):
        if held(CB_ID.BOW) == 0:
            log('no Ogre bow to wield')
            return False
        _w18 = yield from equipment.equip(CB_NAME.BOW)
        if not (_w18):
            return False
    if not equipment.contains(CB_NAME.ARROW):
        if held(CB_ID.ARROW) == 0:
            log('no Ogre arrow to quiver')
            return False
        _w19 = yield from equipment.equip(CB_NAME.ARROW)
        if not (_w19):
            return False
    return True


def pluck_chompy(log):
    dead = npcs.query().name(CB_NPC.CHOMPY).action('Pluck').within(16).nearest()
    if not dead:
        return False
    if not (dead.interact('Pluck')):
        return False
    _w20 = yield from execution.delay_until(lambda: ground_items.query().name(CB_NAME.RAW_CHOMPY).within(12).exists(), 12000)
    if not (_w20):
        log('the pluck left no raw chompy on the floor')
        return False
    carcass = ground_items.query().name(CB_NAME.RAW_CHOMPY).within(12).nearest()
    if not carcass or not (carcass.interact('Take')):
        return False
    _result21 = yield from execution.delay_until(lambda: held(CB_ID.RAW_CHOMPY) > 0, 8000)
    return _result21


# Why: the chompy flees anything within 2 tiles of it, and its spawn only lasts 100 ticks, so the shot is taken from range as soon as one lands.
def hunt_chompy(log):
    """Bait, shoot and pluck one chompy bird."""
    if held(CB_ID.RAW_CHOMPY) > 0:
        return True
    for round in range(4):
        if chompy_dead():
            _result22 = yield from pluck_chompy(log)
            return _result22
        if not equipment.contains(CB_NAME.ARROW) and held(CB_ID.ARROW) == 0:
            yield from recover_arrows()
        _w23 = yield from arm_for_chompy(log)
        if not (_w23):
            return False
        if not chompy_alive():
            _w24 = yield from keep_bait_down(log)
            if not (_w24):
                return False
            _w25 = yield from execution.delay_until(lambda: chompy_alive() or chompy_dead() or not bait_placed(), 60000)
            if not (_w25):
                log('nothing came to the bait in a minute — re-baiting')
                continue
            if not chompy_alive() and not chompy_dead():
                continue
        bird = npcs.query().name(CB_NPC.CHOMPY).action('Attack').within(16).nearest()
        if bird and not (bird.interact('Attack')):
            return False
        # Why: every shot spends an arrow and the quiver holds what the fletching leg could make, so a dry quiver mid-fight is answered by picking the spent arrows back up.
        deadline = _core.step_time() + 60000
        while _core.step_time() < deadline and not chompy_dead():
            if not equipment.contains(CB_NAME.ARROW):
                yield from recover_arrows()
                _w26 = yield from arm_for_chompy(log)
                if not (_w26):
                    break
                again = npcs.query().name(CB_NPC.CHOMPY).action('Attack').within(16).nearest()
                if again:
                    again.interact('Attack')
            yield from execution.delay_ticks(2)
        if chompy_dead():
            _result27 = yield from pluck_chompy(log)
            return _result27
        log('the chompy outlasted its shot window')
    return held(CB_ID.RAW_CHOMPY) > 0

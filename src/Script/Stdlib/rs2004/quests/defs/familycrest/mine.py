"""Ported from rs2b0t's src/bot/api/ai/quests/defs/familycrest/mine.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.familycrest.areas import FC_ID, FC_ITEM, FC_LOC, in_perfect_gold_zone
from rs2004.quests.exec.prompts import held_id, settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['mine_region', 'enter_gold_mine', 'leave_gold_mine', 'PERFECT_ORE_NEEDED', 'mine_perfect_gold', 'FURNACE_STAND', 'smelt_perfect_bars', 'craft_perfect_jewellery']

def LEVER_UP(text):
    return text.strip().lower() in ['the lever is now up', 'the lever is now up.']


def LEVER_DOWN(text):
    return text.strip().lower() in ['the lever is now down', 'the lever is now down.']


DOOR_LOCKED = 'this door is locked'
LEVER_LOC = Record({
    'north': Record({'down': 2421, 'up': 2422}),
    'south': Record({'down': 2423, 'up': 2424}),
    'north_room': Record({'down': 2425, 'up': 2426}),
})


# Why: the 4 components come from a flood over the collision pack with all doors removed; z-ranges are disjoint and the gold room is the only thing east of x=2727, so a tile names the region.
def mine_region(tile):
    """Which of the mine's 4 lever-door regions a tile is in."""
    if not tile or tile.level != 0 or tile.x < 2688 or tile.x > 2751 or tile.z < 9664 or tile.z > 9727:
        return 'outside'
    if tile.x >= 2728:
        return 'gold'
    if tile.z <= 9671:
        return 'south'
    if tile.z >= 9711:
        return 'north_room'
    return 'main'


LEVER = {
    'north': Record({'at': Tile(2722, 9710, 0), 'stand': Tile(2722, 9709, 0), 'ids': LEVER_LOC.north}),
    'south': Record({'at': Tile(2724, 9669, 0), 'stand': Tile(2723, 9670, 0), 'ids': LEVER_LOC.south}),
    'north_room': Record({'at': Tile(2722, 9718, 0), 'stand': Tile(2723, 9717, 0), 'ids': LEVER_LOC.north_room}),
}
DOOR = Record({
    'g2h1': Record({
    'label': 'north-up/south-down door',
    'sides': Record({
    'main': Record({'stand': Tile(2722, 9672, 0), 'to': 'south'}),
    'south': Record({'stand': Tile(2722, 9671, 0), 'to': 'main'}),
}),
}),
    'h2': Record({
    'label': 'both-levers-up door',
    'sides': Record({
    'main': Record({'stand': Tile(2719, 9672, 0), 'to': 'south'}),
    'south': Record({'stand': Tile(2719, 9671, 0), 'to': 'main'}),
}),
}),
    'h2g1': Record({
    'label': 'north-down/south-up door',
    'sides': Record({
    'main': Record({'stand': Tile(2723, 9710, 0), 'to': 'north_room'}),
    'north_room': Record({'stand': Tile(2723, 9711, 0), 'to': 'main'}),
}),
}),
    'i2h1': Record({
    'label': 'gold-room door',
    'sides': Record({
    'main': Record({'stand': Tile(2727, 9690, 0), 'to': 'gold'}),
    'gold': Record({'stand': Tile(2728, 9690, 0), 'to': 'main'}),
}),
}),
})


def here():
    return game.tile()


# Why: `loc_change(..., 500)` reverts the lever to its down model after 5 minutes with the varp bit still set, so the chat line on the pull is the oracle.
def set_lever(key, want, log):
    """Pull a lever until the server confirms the wanted state."""
    spot = LEVER[key]
    for attempt in range(4):
        yield from sustain.run()
        _w1 = yield from traversal.walk_resilient(spot.stand, radius=1, attempts=4, timeout_ms=90000, log=log)
        if not (_w1):
            log(f'could not reach the {key} lever stand')
            return False
        yield from settle_scene()
        lever = locs.query().where(lambda l: l.id == spot.ids.down or l.id == spot.ids.up).action('Pull').within(3).nearest()
        if not lever:
            log(f'no {key} lever in the scene at ({spot.at.x},{spot.at.z})')
            return False
        mark = game_messages.mark()
        if not (lever.interact('Pull')):
            continue
        settled = yield from execution.delay_until(lambda: game_messages.saw_since(mark, LEVER_UP) or game_messages.saw_since(mark, LEVER_DOWN), 6000)
        if not settled:
            continue
        now = ('up' if game_messages.saw_since(mark, LEVER_UP) else 'down')
        log(f'{key} lever is now {now}')
        if now == want:
            return True
    log(f'could not force the {key} lever {want}')
    return False


# Why: `open_and_close_door2` teleports you through and shuts the door behind, so the tell is the region change; `'locked'` means the lever combination is wrong and the caller re-plans.
def cross_door(door, from_, log):
    """Open one of the mine's doors and confirm the crossing."""
    side = door.sides.get(from_)
    if not side:
        return 'failed'
    _w2 = yield from traversal.walk_resilient(side.stand, radius=0, attempts=4, timeout_ms=90000, log=log)
    if not (_w2):
        log(f'could not reach the {door.label} stand ({side.stand.x},{side.stand.z})')
        return 'failed'
    yield from settle_scene()
    shut = locs.query().name('Door').action('Open').within(3).nearest()
    if not shut:
        log(f'no {door.label} in the scene')
        return 'failed'
    mark = game_messages.mark()
    if not (shut.interact('Open')):
        return 'failed'
    yield from execution.delay_until(lambda: mine_region(here()) == side.to or game_messages.saw_since(mark, DOOR_LOCKED), 6000)
    if mine_region(here()) == side.to:
        log(f'crossed the {door.label} into {side.to}')
        return 'crossed'
    if game_messages.saw_since(mark, DOOR_LOCKED):
        return 'locked'
    return 'failed'


# Why: the chain is the shortest a BFS over the collision pack found; levers are set, never read, so a restart anywhere converges, and every room was entered with the lever state that opens the way back.
def reach_perfect_gold(log):
    """Walk the levers-and-doors chain from wherever we are to the gold room."""
    for _pass in range(3):
        # Ogres line the lever route and hellhounds guard the rocks; a step this long pumps the eat hook itself.
        yield from sustain.run()
        region = mine_region(here())
        if region == 'gold':
            return True
        if region == 'outside':
            log('not in the gold mine')
            return False
        # Recovery: these rooms were entered with the lever state that opens the door back out, so one attempt is enough.
        if region == 'north_room':
            _w3 = yield from cross_door(DOOR.h2g1, 'north_room', log)
            if (_w3) != 'crossed':
                return False
            region = 'main'
        if region == 'south':
            _w5 = yield from cross_door(DOOR.g2h1, 'south', log)
            _c4 = (_w5) == 'crossed'
            if not _c4:
                _w6 = yield from cross_door(DOOR.h2, 'south', log)
                _c4 = (_w6) == 'crossed'
            back = _c4
            if not back:
                return False
            region = 'main'
        # Why: the south lever can't be seen from here, so trying both doors tells us where it stands.
        _w7 = yield from set_lever('north', 'up', log)
        if not (_w7):
            return False
        south_lever = None
        _w8 = yield from cross_door(DOOR.g2h1, 'main', log)
        if (_w8) == 'crossed':
            south_lever = 'down'
        else:
            _w10 = yield from cross_door(DOOR.h2, 'main', log)
            if (_w10) == 'crossed':
                south_lever = 'up'
            else:
                log('neither south door opened with the north lever up')
                return False
        log(f'south lever was {south_lever}')
        # 2. south lever up, back north through the both-up door.
        _w11 = yield from set_lever('south', 'up', log)
        if not (_w11):
            return False
        _w12 = yield from cross_door(DOOR.h2, 'south', log)
        if (_w12) != 'crossed':
            return False
        # 3. north lever down opens the north room.
        _w13 = yield from set_lever('north', 'down', log)
        if not (_w13):
            return False
        _w14 = yield from cross_door(DOOR.h2g1, 'main', log)
        if (_w14) != 'crossed':
            return False
        # 4. north-room lever up, and back out the way we came in.
        _w15 = yield from set_lever('north_room', 'up', log)
        if not (_w15):
            return False
        _w16 = yield from cross_door(DOOR.h2g1, 'north_room', log)
        if (_w16) != 'crossed':
            return False
        # 5. north lever back up, south again, south lever down.
        _w17 = yield from set_lever('north', 'up', log)
        if not (_w17):
            return False
        _w18 = yield from cross_door(DOOR.h2, 'main', log)
        if (_w18) != 'crossed':
            return False
        _w19 = yield from set_lever('south', 'down', log)
        if not (_w19):
            return False
        _w20 = yield from cross_door(DOOR.g2h1, 'south', log)
        if (_w20) != 'crossed':
            return False
        # 6. north up, south down, north-room up, the gold-room door.
        _w21 = yield from cross_door(DOOR.i2h1, 'main', log)
        if (_w21) == 'crossed':
            return True
        log('gold-room door refused — re-running the lever chain')
    return False


def enter_gold_mine(log):
    if mine_region(here()) != 'outside':
        return True
    status = yield from reach.loc_op('Ladder', 'Climb-down', FC_LOC.MINE_LADDER, lambda: mine_region(here()) != 'outside', log=log)
    if status != 'done':
        return False
    yield from settle_scene()
    return mine_region(here()) != 'outside'


def leave_gold_mine(log):
    region = mine_region(here())
    if region == 'outside':
        return True
    if region != 'main':
        log(f'cannot climb out from the {region} room — walking back to the ladder side first')
        if region == 'gold':
            yield from cross_door(DOOR.i2h1, 'gold', log)
        elif region == 'north_room':
            yield from cross_door(DOOR.h2g1, 'north_room', log)
        else:
            # The south lever can't be seen from here, so try both doors, as the entry does.
            _w22 = yield from cross_door(DOOR.g2h1, 'south', log)
            if (_w22) != 'crossed':
                yield from cross_door(DOOR.h2, 'south', log)
    if mine_region(here()) != 'main':
        return False
    status = yield from reach.loc_op('Ladder', 'Climb-up', FC_LOC.MINE_LANDING, lambda: mine_region(here()) == 'outside', log=log)
    return status == 'done' and mine_region(here()) == 'outside'


PERFECT_ORE_NEEDED = 2


# Why: `inzone` tests the player's tile, so a boundary rock mined from outside the box gives ordinary gold ore and the smelt makes the wrong bar.
def mine_perfect_gold(log):
    """Mine perfect gold."""
    if held_id(FC_ID.PERFECT_GOLD_ORE) >= PERFECT_ORE_NEEDED:
        return True
    _c23 = mine_region(here()) != 'gold'
    if _c23:
        _w24 = yield from reach_perfect_gold(log)
        _c23 = not (_w24)
    if _c23:
        return False
    for attempt in range(30):
        yield from sustain.run()
        if held_id(FC_ID.PERFECT_GOLD_ORE) >= PERFECT_ORE_NEEDED:
            return True
        _c25 = not in_perfect_gold_zone(here())
        if _c25:
            _w26 = yield from traversal.walk_resilient(FC_LOC.GOLD_STAND, radius=0, attempts=3, timeout_ms=60000, log=log)
            _c25 = not (_w26)
        if _c25:
            log('could not stand inside the perfect-gold zone')
            return False
        yield from settle_scene()
        rock = locs.query().where(lambda l: l.id == 2098 or l.id == 2099).action('Mine').within(6).nearest()
        if not rock:
            yield from execution.delay_ticks(3)
            continue
        before = held_id(FC_ID.PERFECT_GOLD_ORE)
        if not (rock.interact('Mine')):
            continue
        yield from execution.delay_until(lambda: held_id(FC_ID.PERFECT_GOLD_ORE) > before, 20000)
    return held_id(FC_ID.PERFECT_GOLD_ORE) >= PERFECT_ORE_NEEDED


# Why: the moulds and Avan are in Al Kharid, so smelting at Ardougne walks the same 600 tiles twice; this is the south side, since `furnace1` is `forceapproach=east` and the east stand never routes.
FURNACE_STAND = Tile(3272, 3183, 0)


def at_furnace(log):
    _result27 = yield from traversal.walk_resilient(FURNACE_STAND, radius=2, attempts=4, timeout_ms=180000, log=log)
    return _result27


# Why: ore on a furnace smelts one bar with no interface, and `perfect_gold_ore` carries `smeltsto=perfect_gold_bar`, so the wrong metal can't be picked.
def smelt_perfect_bars(log):
    """Smelt the perfect gold ore into bars."""
    if held_id(FC_ID.PERFECT_GOLD_ORE) == 0:
        return held_id(FC_ID.PERFECT_GOLD_BAR) > 0
    _w28 = yield from at_furnace(log)
    if not (_w28):
        return False
    for attempt in range(8):
        if not (held_id(FC_ID.PERFECT_GOLD_ORE) > 0):
            break
        yield from settle_scene()
        ore = ([i for i in inventory.items() if i.id == FC_ID.PERFECT_GOLD_ORE] or [None])[0]
        furnace = locs.query().name('Furnace').within(10).nearest()
        if not ore or not furnace:
            log('no Furnace in reach of the Ardougne stand')
            return False
        before = held_id(FC_ID.PERFECT_GOLD_BAR)
        if not (ore.use_on(furnace)):
            continue
        yield from execution.delay_until(lambda: held_id(FC_ID.PERFECT_GOLD_BAR) > before, 12000)
    log(f'smelted {held_id(FC_ID.PERFECT_GOLD_BAR)}x {FC_ITEM.PERFECT_GOLD_BAR}')
    return held_id(FC_ID.PERFECT_GOLD_ORE) == 0


# Why: the panel's placeholders carry the live product's name, and `crafting_gold` substitutes the perfect bar whenever one is held, so "Ruby ring" is the thing to click.
def craft_perfect_jewellery(log):
    """Craft the jewellery Avan asked for."""
    wants = [
        Record({'product': 'Ruby ring', 'id': FC_ID.PERFECT_RUBY_RING}),
        Record({'product': 'Ruby necklace', 'id': FC_ID.PERFECT_RUBY_NECKLACE}),
    ]
    for want in wants:
        if held_id(want.id) > 0:
            continue
        if held_id(FC_ID.PERFECT_GOLD_BAR) == 0:
            log(f'no {FC_ITEM.PERFECT_GOLD_BAR} left to make the {want.product}')
            return False
        if inventory.count_by_id(FC_ID.RUBY) == 0:
            log(f'no {FC_ITEM.RUBY} left to set into the {want.product}')
            return False
        _w29 = yield from at_furnace(log)
        if not (_w29):
            return False
        yield from settle_scene()
        bar = ([i for i in inventory.items() if i.id == FC_ID.PERFECT_GOLD_BAR] or [None])[0]
        furnace = locs.query().name('Furnace').within(10).nearest()
        if not bar or not furnace:
            log('no Furnace in reach of the Ardougne stand')
            return False
        if not (bar.use_on(furnace)):
            return False
        _w30 = yield from execution.delay_until(lambda: chat_dialog.is_main_make_panel(), 8000)
        if not (_w30):
            log('the gold-crafting panel did not open — are both moulds in the pack?')
            return False
        _w31 = yield from chat_dialog.make_from_panel(want.product, 'Make')
        if not (_w31):
            log(f"'{want.product}' is not on the panel — products: [{', '.join(chat_dialog.main_make_products())}]")
            return False
        _w32 = yield from execution.delay_until(lambda: held_id(want.id) > 0, 12000)
        if not (_w32):
            log(f'making the {want.product} did not produce a perfect one')
            return False
        log(f'made the perfect {want.product.lower()}')
    return held_id(FC_ID.PERFECT_RUBY_RING) > 0 and held_id(FC_ID.PERFECT_RUBY_NECKLACE) > 0

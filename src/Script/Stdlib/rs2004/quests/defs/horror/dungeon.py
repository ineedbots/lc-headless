"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/dungeon.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.horror.areas import HD_ID, HD_ITEM, HD_LOC, HD_TILE
from rs2004.quests.defs.horror.lighthouse import in_basement
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.traversal import traversal

__all__ = ['in_cavern', 'open_wall_and_descend', 'exit_after_quest']

SLOTS = [
    Record({'id': HD_ID.AIR_RUNE, 'item': HD_ITEM.AIR_RUNE}),
    Record({'id': HD_ID.WATER_RUNE, 'item': HD_ITEM.WATER_RUNE}),
    Record({'id': HD_ID.EARTH_RUNE, 'item': HD_ITEM.EARTH_RUNE}),
    Record({'id': HD_ID.FIRE_RUNE, 'item': HD_ITEM.FIRE_RUNE}),
    Record({'id': HD_ID.DAGGER, 'item': HD_ITEM.DAGGER}),
    Record({'id': HD_ID.ARROW, 'item': HD_ITEM.ARROW}),
]
def PLACED(text):
    lower = text.lower()
    return ('you place a' in lower) and ('into the slot in the wall' in lower)


NO_SPACE = 'there is no space to put'


def _z():
    here = game.tile()
    return here.z if here is not None else 0


def in_cavern(tile):
    return tile is not None and tile.level == 0 and tile.x >= 2496 and tile.x <= 2559 and tile.z >= 4608 and tile.z <= 4671


def ladder_at(where):
    """Two "Iron ladder" locs share the basement; only the tile tells them apart."""
    return locs.query().name(HD_LOC.LADDER).where(lambda l: l.tile().distance_to(where) <= 1).nearest()


# Why: The south side consumes one of each elemental rune, a stab/slash weapon, and an arrow; the north side refuses the search.
def load_wall(log):
    """Load the strange wall; returns the slots it could not fill."""
    _w1 = yield from traversal.walk_resilient(HD_TILE.WALL_SOUTH, radius=1, attempts=4, timeout_ms=120000, log=log)
    if not (_w1):
        log('could not reach the south face of the strange wall')
        return None
    yield from settle_scene()
    missing = []
    for slot in SLOTS:
        wall = locs.query().name(HD_LOC.WALL).action('Study').within(6).nearest()
        if not wall:
            log('no studiable section of the strange wall in reach')
            return None
        held = inventory.first(slot.item)
        if not held:
            # Why: every slot consumes its item, so a missing one is usually already in the wall; failing here would leave the arrow behind it unplaced, so note it and let the door judge.
            missing.append(slot.item)
            continue
        mark = game_messages.mark()
        if not (held.use_on(wall)):
            continue
        # Why: "I don't think I'll get that back if I put it in there." lands a tick after the use-on and the Yes/No a tick later, so `driveUntil` keeps answering until the message lands; a filled slot skips both.
        answered = yield from drive_until(lambda: game_messages.saw_since(mark, PLACED) or game_messages.saw_since(mark, NO_SPACE), ['Yes'], log, 15000)
        if not answered:
            # The next pass re-reads the wall, and a filled slot says so at once.
            log(f'the wall did not answer the {slot.item} — moving on')
            continue
        log((f'placed the {slot.item}' if game_messages.saw_since(mark, PLACED) else f'{slot.item} slot was already filled'))
    if len(missing) > 0:
        log(f"nothing left in the pack for: {', '.join(missing)} — assuming already placed")
    return missing


CANNOT_MOVE = 'cannot see any way to move'


def open_wall_and_descend(log):
    """Open the far-right section and drop into the cavern. It only answers from the south once all 6 slots are filled."""
    if in_cavern(game.tile()):
        return True
    if not in_basement(game.tile()):
        log('not in the lighthouse basement')
        return False
    if _z() < 4627:
        missing = yield from load_wall(log)
        if missing is None:
            return False
        door = locs.query().name(HD_LOC.WALL).action('Open').where(lambda l: l.tile().z >= 4627 and l.tile().x >= 2516).nearest()
        if not door:
            log('no openable section of the strange wall in reach')
            return False
        mark = game_messages.mark()
        if not (door.interact('Open')):
            return False
        through = yield from execution.delay_until(lambda: _z() >= 4627, 8000)
        if not through:
            if not game_messages.saw_since(mark, CANNOT_MOVE):
                log('the wall did not open')
            elif len(missing) > 0:
                # Why: only the door can tell a slot whose item is gone from one already filled.
                log(f"the wall still has empty slots — {', '.join(missing)} must be re-sourced")
            else:
                log('the wall still has empty slots')
            return False
        yield from settle_scene()
    _w3 = yield from traversal.walk_resilient(HD_TILE.BASEMENT_DOWN, radius=2, attempts=4, timeout_ms=120000, log=log)
    if not (_w3):
        return False
    yield from settle_scene()
    ladder = ladder_at(HD_TILE.BASEMENT_DOWN)
    if not ladder:
        log('no iron ladder down to the cavern')
        return False
    if not (ladder.interact('Climb')):
        return False
    _w4 = yield from execution.delay_until(lambda: in_cavern(game.tile()), 10000)
    if not (_w4):
        log('the ladder did not land in the cavern')
        return False
    yield from settle_scene()
    return True


# Why: completing teleports you into the post-quest cavern, a level-1 pocket of mapsquare 39_156 whose only exit is its iron ladder to the lighthouse ground floor.
# Why: retaliation stays off so the level-100 dagannoths below don't start a fight on the way home.
def in_postquest_cavern(tile):
    return tile is not None and tile.level == 1 and tile.x >= 2496 and tile.x <= 2559 and tile.z >= 9984 and tile.z <= 10047

def in_lighthouse(tile):
    if not tile or tile.level < 0 or tile.level > 2 or tile.z < 3636 or tile.z > 3644:
        return False
    if tile.z == 3636:
        return tile.x == 2509
    inset = (2 if tile.z == 3637 or tile.z == 3644 else (1 if tile.z == 3638 or tile.z == 3643 else 0))
    return tile.x >= 2505 + inset and tile.x <= 2512 - inset

def leave_lighthouse(log):
    yield from settle_scene()
    for i in range(2):
        here = game.tile()
        if not here:
            return False
        if here.level == 0:
            break
        stairs = locs.query().name(HD_LOC.STAIRS).action('Climb-down').within(12).where(lambda loc: loc.tile().level == here.level).nearest()
        if not stairs or not (stairs.interact('Climb-down')):
            return False

        def _fn1():
            tile = game.tile()
            return tile is not None and tile.level < here.level
        _w2 = yield from execution.delay_until(_fn1, 8000)
        if not (_w2):
            return False
        yield from settle_scene()
    doorway = HD_TILE.REAL_LIGHTHOUSE_L0.translate(0, -1)
    _w3 = yield from traversal.walk_resilient(doorway, radius=0, attempts=3, timeout_ms=30000, log=log)
    if not (_w3):
        return False
    yield from settle_scene()
    door = locs.query().name(HD_LOC.DOORWAY).action('Walk-through').where(lambda loc: loc.tile().equals(doorway)).nearest()
    if not door or not (door.interact('Walk-through')):
        return False

    def _fn4():
        tile = game.tile()
        return tile is not None and HD_TILE.LIGHTHOUSE_DOOR.equals(tile)
    _w5 = yield from execution.delay_until(_fn4, 8000)
    if not (_w5):
        return False
    yield from settle_scene()
    _result6 = yield from traversal.walk_resilient(HD_TILE.CAUSEWAY_SOUTH, radius=1, attempts=3, timeout_ms=180000, log=log)
    return _result6

def exit_after_quest(log):
    """Walk out of the finished quest's cavern."""
    here = game.tile()
    if not here:
        return False
    if not in_postquest_cavern(here):
        if in_lighthouse(here):
            result = yield from leave_lighthouse(log)
            return result
        return True
    game.set_auto_retaliate(False)
    try:
        result = yield from _climb_out(log)
    except Exception as e:
        game.set_auto_retaliate(True)
        raise e
    game.set_auto_retaliate(True)
    return result


def _climb_out(log):
    walked = yield from traversal.walk_resilient(HD_TILE.POSTQUEST_LADDER, radius=2, attempts=4, timeout_ms=120000, log=log)
    if not walked:
        log('could not reach the ladder out of the post-quest cavern')
        return False
    yield from settle_scene()
    ladder = ladder_at(HD_TILE.POSTQUEST_LADDER)
    if not ladder or not (ladder.interact('Climb')):
        log('no iron ladder out of the post-quest cavern')
        return False
    landed = yield from execution.delay_until(lambda: in_lighthouse(game.tile()), 10000)
    if not landed:
        return False
    yield from settle_scene()
    result = yield from leave_lighthouse(log)
    return result

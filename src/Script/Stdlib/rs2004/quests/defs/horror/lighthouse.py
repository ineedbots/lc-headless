"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/lighthouse.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.horror.areas import HD_ID, HD_ITEM, HD_LOC, HD_TILE
from rs2004.quests.defs.horror.journal import HD_FLAG
from rs2004.quests.exec.prompts import settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['in_quest_lighthouse', 'in_basement', 'repair_bridge', 'enter_lighthouse', 'climb_to_light', 'repair_light', 'descend_to_basement']

def in_quest_lighthouse(tile):
    return tile is not None and tile.x >= 2432 and tile.x <= 2495 and tile.z >= 4544 and tile.z <= 4607


def in_basement(tile):
    return tile is not None and tile.level == 1 and tile.x >= 2496 and tile.x <= 2559 and tile.z >= 4608 and tile.z <= 4671


def clear_mesbox():
    """`~mesbox` puts a modal message box up; nothing else advances until it is cleared."""
    for i in range(4):
        if not ((chat_dialog.can_continue() or chat_dialog.is_open())):
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)


# Why: the spots sit on opposite banks and the walk between is the navigator's `Cross` op; success is the plank count, since `oplocu` deletes plank and nails and the refusals ("You need 4 steel nails", "already fixed this half") delete nothing.
def repair_bridge(log):
    """Repair both halves of the storm-broken bridge, a plank and 4 nails each."""
    spots = [['west', HD_TILE.BRIDGE_WEST], ['east', HD_TILE.BRIDGE_EAST]]
    for side, stand in spots:
        _w1 = yield from traversal.walk_resilient(stand, radius=1, attempts=4, timeout_ms=300000, log=log)
        if not (_w1):
            log(f'could not stand on the {side} bridge spot')
            return False
        yield from settle_scene()
        spot = locs.query().name(HD_LOC.BRIDGE).where(lambda l: l.tile().equals(stand)).nearest()
        if not spot:
            log(f'no bridge spot at ({stand.x},{stand.z})')
            return False
        plank = inventory.first(HD_ITEM.PLANK)
        if not plank:
            log('no plank left for the bridge')
            return False
        before = inventory.count_by_id(HD_ID.PLANK)
        if not (plank.use_on(spot)):
            return False
        built = yield from execution.delay_until(lambda: inventory.count_by_id(HD_ID.PLANK) < before, 10000)
        yield from clear_mesbox()
        if not built:
            # An already-built half refuses without consuming, the normal resume path, so carry on to the other side.
            log(f'the {side} half took no plank (already built, or nails short)')
        else:
            log(f'{side} half of the bridge built')
    return True


def enter_lighthouse(log):
    """Walk through the lighthouse doorway; `oploc1` teleports you into the broken copy in mapsquare 38_71."""
    if in_quest_lighthouse(game.tile()):
        return True
    status = yield from reach.loc_op(HD_LOC.DOORWAY, 'Walk-through', HD_TILE.LIGHTHOUSE_DOOR, lambda: in_quest_lighthouse(game.tile()), log=log)
    yield from settle_scene()
    return status == 'done' and in_quest_lighthouse(game.tile())


def climb(name, op, near, arrive, log):
    if arrive():
        return True
    status = yield from reach.loc_op(name, op, near, arrive, log=log)
    if status != 'done':
        return False
    yield from settle_scene()
    return arrive()


def _level(default):
    here = game.tile()
    return here.level if here is not None else default


def at_level(level):
    return lambda: _level(-1) == level


# Why: the middle staircase's op1 raises a Climb Up / Climb Down choice whose down branch teleports 2 tiles sideways once the light is repaired, so both hops use the explicit ops.
def climb_to_light(log):
    """Climb from the ground floor to the lamp room of the broken copy."""
    _w2 = yield from climb(HD_LOC.STAIRS, 'Climb-up', HD_TILE.QUEST_STAIRS_BASE, at_level(1), log)
    if not (_w2):
        return False
    _result3 = yield from climb(HD_LOC.STAIRS, 'Climb-up', HD_TILE.QUEST_STAIRS_L1, at_level(2), log)
    return _result3


# Why: the torch refuses the tinderbox until tarred ("The torch does not seem to be flammable..."), the last application teleports you into the live lighthouse, and the tinderbox isn't consumed, so leaving the copy is the proof it caught.
def repair_light(flags, log):
    """Apply tar, glass and light to the lamp."""
    _w4 = yield from traversal.walk_resilient(HD_TILE.QUEST_LIGHT, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    steps = [
        Record({
        'item': HD_ITEM.SWAMP_TAR,
        'id': HD_ID.SWAMP_TAR,
        'flag': HD_FLAG.TAR,
        'done': lambda: inventory.count_by_id(HD_ID.SWAMP_TAR) == 0,
    }),
        Record({
        'item': HD_ITEM.MOLTEN_GLASS,
        'id': HD_ID.MOLTEN_GLASS,
        'flag': HD_FLAG.GLASS,
        'done': lambda: inventory.count_by_id(HD_ID.MOLTEN_GLASS) == 0,
    }),
        Record({
        'item': HD_ITEM.TINDERBOX,
        'id': HD_ID.TINDERBOX,
        'flag': HD_FLAG.LIGHT,
        'done': lambda: not in_quest_lighthouse(game.tile()),
    }),
    ]
    for step in steps:
        if (step.flag in flags) or inventory.count_by_id(step.id) == 0:
            continue
        mechanism = locs.query().name(HD_LOC.LIGHT).within(8).nearest()
        held = inventory.first(step.item)
        if not mechanism or not held:
            log(f'no lighting mechanism in reach, or no {step.item} to use on it')
            return False
        if not (held.use_on(mechanism)):
            return False
        _w5 = yield from execution.delay_until(step.done, 10000)
        if not (_w5):
            log(f'the mechanism did not take the {step.item}')
            return False
        log(f'{step.item} applied to the lighting mechanism')
        if not in_quest_lighthouse(game.tile()):
            return True
    yield from execution.delay_ticks(3)
    return not in_quest_lighthouse(game.tile())


# Why: repairing teleports into the live lighthouse's lamp room, its staircase routes back into the copy at level 1, and only the copy's ground floor has the iron ladder down.
def descend_to_basement(log):
    """Descend from wherever the repair left the player to the basement."""
    if in_basement(game.tile()):
        return True
    if _level(0) == 2:
        stairs = (HD_TILE.QUEST_STAIRS_L2 if in_quest_lighthouse(game.tile()) else HD_TILE.REAL_STAIRS_L2)
        _w6 = yield from climb(HD_LOC.STAIRS, 'Climb-down', stairs, at_level(1), log)
        if not (_w6):
            return False
    if _level(0) == 1 and not in_basement(game.tile()):
        _w7 = yield from climb(HD_LOC.STAIRS, 'Climb-down', HD_TILE.QUEST_STAIRS_L1, at_level(0), log)
        if not (_w7):
            return False
    if not in_quest_lighthouse(game.tile()):
        # Back outside at ground level: the doorway is the only way in again.
        _w8 = yield from enter_lighthouse(log)
        if not (_w8):
            return False
    _result9 = yield from climb(HD_LOC.LADDER, 'Climb', HD_TILE.QUEST_LADDER, lambda: in_basement(game.tile()), log)
    return _result9

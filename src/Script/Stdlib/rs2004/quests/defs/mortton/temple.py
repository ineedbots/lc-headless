"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/temple.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs
from rs2004.execution import event_signal
from rs2004.game import game, reader, skills
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_LOC, SM_LOC_ID, SM_TILE, SM_VARP, is_temple_wall
from rs2004.quests.defs.mortton.supplies import perm_serum_vial_id, serum_vial_id
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['temple_repaired', 'temple_resources', 'temple_sanctity', 'SANCTITY_TO_LIGHT', 'SANCTITY_TO_SANCTIFY_SERUM', 'material_sets', 'altar_unlit', 'altar_lit', 'repair_temple', 'light_altar', 'sanctify_oil', 'sacred_oil_doses', 'sanctify_serum']

REPAIR = 'Repair'
REINFORCE = 'Reinforce'
WALL_RADIUS = 8
EAT_AT_MISSING = 12
BUILD_GUARD = 3000
IDLE_TO_RECLICK = 3
# Why: the leg builds sanctity before it strikes, and the climb from cold is about 200 ticks on its own, so the budget covers both.
LIGHT_GUARD = 500
OUT_OF_RESOURCES = 'material resource pool'


def temple_repaired():
    return reader.varp(SM_VARP.TEMPLE_REPAIRED)


def temple_resources():
    return reader.varp(SM_VARP.TEMPLE_RESOURCES)


def temple_sanctity():
    return reader.varp(SM_VARP.TEMPLE_SANCTITY)


SANCTITY_TO_LIGHT = 10
SANCTITY_TO_SANCTIFY_SERUM = 20
# Why: the walls stay rebuilt for 9000 ticks as world state, so a bot can arrive at a finished temple with none of the sanctity the altar wants, which only its own building earns.
SANCTITY_TARGET = 25


# Why: carried material only becomes pool points on a successful build tick, so a zero pool can still have material to build with.
def material_sets():
    """Sets of plank, brick and five paste in the pack."""
    return min(inventory.count_by_id(SM_ID.PLANK), inventory.count_by_id(SM_ID.LIMESTONE_BRICK), (inventory.count_by_id(SM_ID.SWAMP_PASTE) // 5))


def wall_offering(op):
    return locs.query().where(lambda l: is_temple_wall(l.id)).action(op).within(WALL_RADIUS).nearest()


def wall_at(tile):
    return locs.query().where(lambda l: is_temple_wall(l.id) and l.tile().x == tile.x and l.tile().z == tile.z).within(WALL_RADIUS).nearest()


def altar(id, op=None):
    query = locs.query().where(lambda l: l.id == id).within(WALL_RADIUS)
    return ((query if op is None else query.action(op))).nearest()


def altar_unlit():
    return altar(SM_LOC_ID.ALTAR_UNLIT, 'Light')


def altar_lit():
    return altar(SM_LOC_ID.ALTAR_LIT)


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: the temple refuses in `~mesbox`, which is `if_openchat` ending in `p_pausebutton`, so the paused script holds the player until it's answered.
def box_text():
    """Whatever box is up, and what it said."""
    if reader.modals().chat == -1 and reader.modals().main == -1:
        return None
    return ' '.join(list(reader.chat_modal_texts()) + list(reader.main_modal_texts()))


def clear_box():
    """Continue the current box, regardless of modal type."""
    if chat_dialog.can_continue():
        yield from chat_dialog.continue_()
        return
    yield from modals.close_if_open()


def stand_inside(log):
    here = game.tile()
    if here and SM_TILE.TEMPLE_INSIDE.distance_to(here) <= 2:
        return True
    _w1 = yield from traversal.walk_resilient(SM_TILE.TEMPLE_INSIDE, radius=2, attempts=3, timeout_ms=240000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    return True


# Why: one click on a wall starts a server-side `p_oploc(3)` loop that keeps building on its own, so the bot re-clicks only once that loop has stopped.
# Why: the loop never leaves its loc and a level-10 wall has no next stage, so left alone it drains the pool into a finished wall; the target is followed by tile and dropped once it stops offering Repair.
def repair_temple(log):
    """Build the temple shell until the fire altar appears."""
    if inventory.count_by_id(SM_ID.HAMMER) == 0:
        log('no hammer in the pack — the temple refuses every repair')
        return False
    _w2 = yield from stand_inside(log)
    if not (_w2):
        return False
    game.set_auto_retaliate(True)
    idle = 0
    last_tick = -1
    reported = -1
    target = None
    # Why: a temple another run left finished reads 100% before this character has built anything, and only a build tick moves `%morttonquest` on.
    built = False
    last_sanctity = temple_sanctity()
    last_pool = temple_resources()
    for i in range(BUILD_GUARD):
        if event_signal.pending():
            log('yielding to a random event mid-build')
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        built = built or temple_sanctity() > last_sanctity or temple_resources() < last_pool
        last_sanctity = temple_sanctity()
        last_pool = temple_resources()
        if built and temple_repaired() >= 100 and altar_unlit() is not None:
            log(f'temple rebuilt — sanctity {temple_sanctity()}%, pool {temple_resources()}%')
            return True
        box = box_text()
        if box is not None:
            dry = OUT_OF_RESOURCES in box.lower()
            yield from clear_box()
            if dry:
                # The refusal comes as 2 boxes; leave neither on the screen.
                yield from execution.delay_ticks(1)
                yield from clear_box()
                log(f'out of building materials at {temple_repaired()}% repaired, pool {temple_resources()}%')
                return False
            idle = 0
            continue
        if hungry():
            yield from sustain.run()
            idle = 0
            continue
        if now - reported >= 100:
            reported = now
            log(f'building: repaired {temple_repaired()}% pool {temple_resources()}% sanctity {temple_sanctity()}%' + f' bricks {inventory.count_by_id(SM_ID.LIMESTONE_BRICK)} planks {inventory.count_by_id(SM_ID.PLANK)}' + f' paste {inventory.count_by_id(SM_ID.SWAMP_PASTE)}')
        # Why: Reinforce is only worth staying on when every piece is finished and the loop is holding the overlay open until the stage flips.
        any_repair = wall_offering(REPAIR)
        held = (None if target is None else wall_at(target))
        held_op = (None if held is None else (REPAIR if (REPAIR in held.actions()) else (REINFORCE if any_repair is None and (REINFORCE in held.actions()) else None)))
        if held is not None and held_op is not None:
            if game.in_combat() or game.animating():
                idle = 0
                continue
            idle += 1
            if idle < IDLE_TO_RECLICK:
                continue
            idle = 0
            held.interact(held_op)
            yield from execution.delay_ticks(2)
            continue
        # The target is finished, or there never was one: move to whatever still wants work.
        wall = (any_repair if any_repair is not None else wall_offering(REINFORCE))
        if not wall:
            _w3 = yield from stand_inside(log)
            if not (_w3):
                return False
            continue
        idle = 0
        target = Record({'x': wall.tile().x, 'z': wall.tile().z})
        wall.interact((REINFORCE if any_repair is None else REPAIR))
        yield from execution.delay_ticks(2)
    log(f'build guard hit at {temple_repaired()}% repaired')
    return temple_repaired() >= 100


# Why: lighting is its own 3-tick server loop with a firemaking roll, so one click is enough and the wait is on the loc changing type.
# Why: the altar is `loc_change(templefire_altar_nofire, 99)`, armed by a build tick and reverting 99 ticks later, so any errand between rebuild and strike comes back to a broken altar.
def light_altar(log):
    """Strike the rebuilt altar until the sacred flame catches, re-arming it when it has gone cold."""
    if altar_lit() is not None:
        return True
    if inventory.count_by_id(SM_ID.TINDERBOX) == 0:
        log('no tinderbox in the pack — the altar cannot be lit')
        return False
    _w4 = yield from stand_inside(log)
    if not (_w4):
        return False
    last_tick = -1
    reported = -1
    for i in range(LIGHT_GUARD):
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if altar_lit() is not None:
            yield from clear_box()
            return True
        # The refusals are `~mesbox`, so the loop answers boxes.
        if box_text() is not None:
            yield from clear_box()
            continue
        if now - reported >= 100:
            reported = now
            log(f'lighting: sanctity {temple_sanctity()}% pool {temple_resources()}%')
        # A cold altar means the arming timer ran out, and low sanctity means this character has not built enough of the temple itself; a build tick answers both.
        dry = temple_resources() == 0 and material_sets() == 0
        sanctity = temple_sanctity()
        ready = sanctity >= SANCTITY_TARGET or (sanctity >= SANCTITY_TO_LIGHT and dry)
        cold = (altar_unlit() if ready else None)
        # Why: the wall's own build loop animates the player without pause, so gating the strike on "not animating" never fires it, only the build re-click waits for a quiet tick.
        if cold:
            cold.interact('Light')
            yield from execution.delay_ticks(2)
            continue
        if dry and sanctity < SANCTITY_TO_LIGHT:
            log(f'sanctity is {sanctity}% with an empty pool — the altar wants {SANCTITY_TO_LIGHT}%')
            return False
        if game.animating() or game.in_combat():
            continue
        # Why: Repair first, since shades knock the shell down while the bot is away and only a rebuilt shell arms the altar.
        _v5 = wall_offering(REPAIR)
        wall = (_v5 if _v5 is not None else wall_offering(REINFORCE))
        if not wall:
            log('the altar is broken and no wall is in reach to re-arm it')
            return False
        wall.interact((REPAIR if (REPAIR in wall.actions()) else REINFORCE))
        yield from execution.delay_ticks(2)
    yield from clear_box()
    log('the sacred flame never caught')
    return False


def sanctify_oil(log):
    """Put a vial of olive oil into the sacred flame."""
    oil = ([id for id in [SM_ID.OLIVE_OIL4, SM_ID.OLIVE_OIL3, SM_ID.OLIVE_OIL2] if inventory.count_by_id(id) > 0] or [None])[0]
    if oil is None:
        log('no olive oil of two doses or more in the pack')
        return False
    before = sacred_oil_doses()
    _result6 = yield from use_on_loc(oil, Record({
        'name': SM_LOC.ALTAR_LIT,
        'near': SM_TILE.TEMPLE_INSIDE,
        'id': SM_LOC_ID.ALTAR_LIT,
        'within': WALL_RADIUS,
    }), [], lambda: sacred_oil_doses() > before, log)
    return _result6


def sacred_oil_doses():
    return inventory.count_by_id(SM_ID.SACRED_OIL4) * 4 + inventory.count_by_id(SM_ID.SACRED_OIL3) * 3 + inventory.count_by_id(SM_ID.SACRED_OIL2) * 2 + inventory.count_by_id(SM_ID.SACRED_OIL1)


# Why: sanctifying converts every dose in the vial at no cost, and one dose of the result sets a villager's permanent bit, so the endgame conversation never needs another serum.
def sanctify_serum(log):
    """Turn a vial of serum 207 into serum 207(p) in the sacred flame."""
    if perm_serum_vial_id() is not None:
        return True
    vial = serum_vial_id()
    if vial is None:
        log('no serum 207 left to sanctify')
        return False
    if temple_sanctity() < SANCTITY_TO_SANCTIFY_SERUM:
        log(f'sanctity is {temple_sanctity()}% — the flame wants {SANCTITY_TO_SANCTIFY_SERUM}% for the serum')
        return False
    _result7 = yield from use_on_loc(vial, Record({
        'name': SM_LOC.ALTAR_LIT,
        'near': SM_TILE.TEMPLE_INSIDE,
        'id': SM_LOC_ID.ALTAR_LIT,
        'within': WALL_RADIUS,
    }), [], lambda: perm_serum_vial_id() is not None, log)
    return _result7

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/arrows.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.chompybird.areas import CB_ID, CB_LOC, CB_NAME, CB_NPC, CB_TILE
from rs2004.quests.defs.chompybird.supplies import ARROW_TARGET, held_id
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['TIPS_CRAFTING', 'walk_to', 'feathers_needed', 'arrow_step']

TIPS_CRAFTING = 5

def held(id):
    return inventory.count_by_id(id)


def walk_to(tile, radius, log):
    here = game.tile()
    if here and here.level == tile.level and tile.distance_to(here) <= radius:
        return True
    _result1 = yield from traversal.walk_resilient(tile, radius=radius, attempts=3, timeout_ms=180000, log=log)
    return _result1


def ground_bones():
    return ground_items.query().name(CB_NAME.WOLF_BONES).within(14).nearest()


def take_bones(before):
    bones = ground_bones()
    if not bones:
        return False
    if not (bones.interact('Take')):
        return False
    _result2 = yield from execution.delay_until(lambda: held(CB_ID.WOLF_BONES) > before, 8000)
    return _result2


# Why: the achey trees stand in a loose grove, so the query is the search and the anchor is only where the walk starts.
def chop_achey(log):
    """One chop of the nearest achey tree."""
    _w3 = yield from walk_to(CB_TILE.ACHEY, 6, log)
    if not (_w3):
        return False
    yield from settle_scene()
    tree = locs.query().name(CB_LOC.ACHEY).action('Chop').within(12).nearest()
    if not tree:
        log('no Achey Tree offering Chop near the grove')
        return False
    before = held(CB_ID.ACHEY_LOGS)
    if not (tree.interact('Chop')):
        return False
    _result4 = yield from execution.delay_until(lambda: held(CB_ID.ACHEY_LOGS) > before, 40000)
    return _result4


# Why: a wolf isn't aggressive to a quest-ready account, so you have to start the fight.
def kill_wolf_for_bones(log):
    """Kill one wolf and pick its bones up."""
    before = held(CB_ID.WOLF_BONES)
    _w5 = yield from take_bones(before)
    if _w5:
        return True
    _w6 = yield from walk_to(CB_TILE.WOLVES, 6, log)
    if not (_w6):
        return False
    yield from settle_scene()
    wolf = npcs.query().name(CB_NPC.WOLF).action('Attack').within(14).nearest()
    if not wolf:
        log('no Wolf in reach of the Feldip pack')
        return False
    index = wolf.index
    if not (wolf.interact('Attack')):
        return False
    _w7 = yield from execution.delay_until(lambda: game.in_combat(), 8000)
    if not (_w7):
        return False
    _w8 = yield from execution.delay_until(lambda: not any([n.index == index for n in npcs.all()]), 120000)
    if not (_w8):
        log('the wolf outlasted its fight window')
        return False
    yield from settle_scene()
    _w9 = yield from take_bones(before)
    if not (_w9):
        log('the wolf left no bones in reach')
        return False
    return True


def use_on(item, target, product):
    return (Record({
        'kind': 'use_on',
        'item': item,
        'target_kind': 'item',
        'target': target,
        'anchor': CB_TILE.ACHEY,
        'product': product,
    }))


# Why: every fletch action caps at 6, so a target above 6 is 2 passes and the decide() loop repeats them.
def feathers_needed(snap):
    """Feathers this pack still has to spend to reach `ARROW_TARGET`."""
    outstanding = ARROW_TARGET - held_id(snap, CB_ID.ARROW) - held_id(snap, CB_ID.FLIGHTED)
    return max(0, outstanding) * 4


def arrow_step(snap, crafting_level=None):
    """The next arrow-making move, or null once `ARROW_TARGET` ogre arrows are held."""
    arrows = held_id(snap, CB_ID.ARROW)
    remaining = ARROW_TARGET - arrows
    if remaining <= 0:
        return None
    flighted = held_id(snap, CB_ID.FLIGHTED)
    tips = held_id(snap, CB_ID.ARROWTIPS)
    shafts = held_id(snap, CB_ID.SHAFT)
    feathers = held_id(snap, CB_ID.FEATHER)
    logs = held_id(snap, CB_ID.ACHEY_LOGS)
    bones = held_id(snap, CB_ID.WOLF_BONES)
    if flighted > 0 and tips > 0:
        return use_on(CB_NAME.ARROWTIPS, CB_NAME.FLIGHTED, CB_NAME.ARROW)
    # Why: below Crafting 5 the chisel is refused in a message box, which no step reads, so the tips would fail
    # silently until the quest parked, and a wolf's bones are no use. This departs from rs2b0t.
    crafting = crafting_level if crafting_level is not None else skills.level('crafting')
    if flighted > 0 and crafting < TIPS_CRAFTING:
        return Record({'kind': 'wait', 'reason': f'wolf bone arrowtips need Crafting {TIPS_CRAFTING} (have {crafting})'})
    if flighted > 0:
        return (use_on(CB_NAME.CHISEL, CB_NAME.WOLF_BONES, CB_NAME.ARROWTIPS) if bones > 0 else Record({'kind': 'custom', 'name': 'kill a wolf for bones', 'run': kill_wolf_for_bones}))
    # Why: flighting spends 4 feathers per shaft and caps at 6 arrows, so build the shafts up first; feathering 3 at a time wastes 12 of the 25 Fycie sells.
    batch = min(6, remaining)
    if shafts < batch:
        return (use_on(CB_NAME.KNIFE, CB_NAME.ACHEY_LOGS, CB_NAME.SHAFT) if logs > 0 else Record({'kind': 'custom', 'name': 'chop an achey tree', 'run': chop_achey}))
    if feathers >= 4:
        return use_on(CB_NAME.FEATHER, CB_NAME.SHAFT, CB_NAME.FLIGHTED)
    # Why: decide() tops the feathers up before this runs, so reaching here means the shop leg is still outstanding.
    return Record({'kind': 'wait', 'reason': 'no feathers to flight the ogre arrow shafts with'})

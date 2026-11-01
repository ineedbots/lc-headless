"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/common.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_TILE, in_dig_cave
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import drive_choice, settle_scene
from rs2004.quests.food import quest_food
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['WALK_MS', 'held_id', 'banked_id', 'held_or_banked', 'walk_to', 'npc_by_id', 'loc_by_ids', 'loc_by_id_action', 'talk_to_npc_id', 'drive_until_held', 'use_on_loc_ids', 'use_on_npc_id', 'is_spoil', 'drop_spoil', 'climb_out_of_cave', 'tile_of']

WALK_MS = 180000
DIALOGUE_MS = 12000
CLIMB_MS = 15000


def held_id(snap, id):
    return snap.inv_ids.get(id, 0) if snap.inv_ids is not None else 0


def banked_id(snap, id):
    """Return unknown until the bank has been read, instead of treating it as empty."""
    if not snap.bank_known or snap.bank_ids is None:
        return 0
    return snap.bank_ids.get(id, 0)


def held_or_banked(snap, id):
    return held_id(snap, id) + banked_id(snap, id)


def walk_to(dest, radius, log):
    here = game.tile()
    if here and here.level == dest.level and dest.distance_to(here) <= radius:
        return True
    _result2 = yield from traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=WALK_MS, log=log)
    return _result2


def npc_by_id(id, within=16):
    return npcs.query().where(lambda n: n.id == id).within(within).nearest()


def loc_by_ids(ids, within=12, extra=None):
    set_ = set(ids)
    return locs.query().where(lambda l: (l.id in set_) and (extra is None or extra(l))).within(within).nearest()


def loc_by_id_action(ids, op, within=12):
    set_ = set(ids)
    return locs.query().where(lambda l: (l.id in set_)).action(op).within(within).nearest()


# Why: every Digsite student displays as "Student" and both workmen as "Digsite workman", so `Reach.npcDialog` could open the wrong conversation.
def talk_to_npc_id(npc_id, anchor, prefer, log, guess_when_unmatched=False):
    """Walk to an anchor and drive one NPC's dialogue, matched by server id."""
    _c3 = not npc_by_id(npc_id, 12)
    if _c3:
        _w4 = yield from walk_to(anchor, 4, log)
        _c3 = not (_w4)
    if _c3:
        return False
    yield from settle_scene()

    def find():
        return npc_by_id(npc_id, 16)

    if not find():
        log(f'no npc {npc_id} within sixteen tiles of ({anchor.x},{anchor.z})')
        return False
    status = yield from reach.entity_op(find, 'Talk-to', lambda: chat_dialog.is_open() or chat_dialog.can_continue(), open_when_unreachable=True, expect_ms=DIALOGUE_MS, what=f'npc {npc_id}', log=log)
    if status != 'done':
        log(f'npc {npc_id} never opened a dialogue ({status})')
        return False
    # Why: the Examiner's exams offer a different wrong-answer set for every errand not yet run, and abandoning mid-exam leaves the conversation open forever.
    if guess_when_unmatched:
        result = yield from drive_dialog(list(prefer), log)
        return result
    result = yield from drive_choice(list(prefer), log)
    return result


def drive_until_held(expect, prefer, log, ms=45000):
    """Drive prompts until a goal lands, answering mesboxes as well as chat."""
    deadline = _core.step_time() + ms
    while _core.step_time() < deadline and not expect():
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drive_choice(list(prefer), log)
            continue
        if modals.is_open():
            yield from modals.close()
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    yield from modals.close_if_open()
    return expect()


def use_on_loc_ids(item_id, loc_ids, stand, expect, log, prefer=None):
    """Use a held item on a loc matched by id, then answer whatever prompt it raised."""
    if prefer is None:
        prefer = []
    if expect():
        return True
    _w5 = yield from walk_to(stand, 1, log)
    if not (_w5):
        return False
    yield from settle_scene()
    target = loc_by_ids(loc_ids, 8)
    item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
    if not target or not item:
        log(f"no loc {'/'.join([str(id) for id in loc_ids])} or no item {item_id} at ({stand.x},{stand.z})")
        return False
    if not (item.use_on(target)):
        return False
    _result7 = yield from drive_until_held(expect, prefer, log)
    return _result7


def use_on_npc_id(item_id, npc_id, anchor, expect, log, prefer=None):
    """Use a held item on an NPC matched by id, then answer whatever prompt it raised."""
    if prefer is None:
        prefer = []
    if expect():
        return True
    _c8 = not npc_by_id(npc_id, 10)
    if _c8:
        _w9 = yield from walk_to(anchor, 3, log)
        _c8 = not (_w9)
    if _c8:
        return False
    yield from settle_scene()
    target = npc_by_id(npc_id, 16)
    item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
    if not target or not item:
        log(f'no npc {npc_id} or no item {item_id} near ({anchor.x},{anchor.z})')
        return False
    # Why: `opnpcu` has the server path to the npc; a client-side chase of a wandering student burns the walk budget on a moving target.
    if not (item.use_on(target)):
        return False
    _result11 = yield from drive_until_held(expect, prefer, log)
    return _result11


KEEP_IDS = set([
    DIG_ID.COINS,
    DIG_ID.TROWEL,
    DIG_ID.SPECIMEN_JAR,
    DIG_ID.SPECIMEN_BRUSH,
    DIG_ID.TRAY_EMPTY,
    DIG_ID.TRAY_MUD,
    DIG_ID.CHISEL,
    DIG_ID.TINDERBOX,
    DIG_ID.PESTLE,
    DIG_ID.VIAL,
    DIG_ID.CHARCOAL,
    DIG_ID.GROUND_CHARCOAL,
    DIG_ID.ARCENIA_ROOT,
    DIG_ID.CHEST_KEY,
    DIG_ID.ROPE,
    DIG_ID.CUP_OF_TEA,
    DIG_ID.OPAL,
    DIG_ID.UNCUT_OPAL,
    DIG_ID.POWDER,
    DIG_ID.AMMONIUM_NITRATE,
    DIG_ID.LIQUID,
    DIG_ID.NITROGLYCERIN,
    DIG_ID.PRE_CHARCOAL,
    DIG_ID.POST_CHARCOAL,
    DIG_ID.COMPOUND,
    DIG_ID.TALISMAN,
    DIG_ID.EXPERT_SCROLL,
    DIG_ID.STONE_TABLET,
    DIG_ID.PLAIN_LETTER,
    DIG_ID.STAMPED_LETTER,
    DIG_ID.CERT_1,
    DIG_ID.CERT_2,
    DIG_ID.CERT_3,
    DIG_ID.ROCK_SAMPLE_GREEN,
    DIG_ID.ROCK_SAMPLE_ORANGE,
    DIG_ID.ROCK_SAMPLE_PURPLE,
])


# Why: every volatile chemical answers Drop with an explosion for up to 65 damage, so this list denies by default and includes the chemicals.
def is_spoil(item):
    """Whether an inventory slot is spoil this quest can throw away."""
    if (item.id in KEEP_IDS):
        return False
    food = quest_food.name.strip().lower() if quest_food.name is not None else ''
    return not food or (item.name.lower() if item.name is not None else None) != food


# Why: pickpocketing for one rock sample turns up 5 specimen brushes and 3 ropes, and each surplus copy takes a slot the level 3 dig needs free.
KEEP_LIMIT = {
    DIG_ID.SPECIMEN_BRUSH: 1,
    DIG_ID.SPECIMEN_JAR: 1,
    DIG_ID.TROWEL: 1,
    DIG_ID.TRAY_EMPTY: 1,
    DIG_ID.TRAY_MUD: 1,
    DIG_ID.CHISEL: 1,
    DIG_ID.TINDERBOX: 1,
    DIG_ID.PESTLE: 1,
    DIG_ID.VIAL: 1,
    DIG_ID.CUP_OF_TEA: 1,
    DIG_ID.ARCENIA_ROOT: 1,
    DIG_ID.ROPE: 2,
}


def drop_spoil(log, keep_free=4):
    """Drop dig and panning spoil so the next dig has a free slot. Nothing here throws."""
    if inventory.free() >= keep_free:
        return
    seen = {}
    for item in inventory.items():
        if inventory.free() >= keep_free:
            return
        nth = seen.get(item.id, 0) + 1
        seen[item.id] = nth
        surplus = item.id in KEEP_LIMIT and nth > KEEP_LIMIT[item.id]
        if not surplus and not is_spoil(item):
            continue
        if item.interact('Drop'):
            log(f"dropped {('surplus' if surplus else 'spoil')}: {(item.name if item.name is not None else item.id)}")
            yield from execution.delay_ticks(1)


def climb_out_of_cave(log):
    """Climb the shaft rope back to the surface. Both shafts' ropes are named "Rope"."""
    here = game.tile()
    if not in_dig_cave(here):
        return True
    for attempt in range(3):
        if not (in_dig_cave(game.tile())):
            break
        rope = locs.query().name('Rope').action('Climb-up').within(40).nearest()
        if not rope:
            log('no shaft rope in the scene to climb')
            return False
        _c14 = rope.distance() > 1
        if _c14:
            _w15 = yield from walk_to(rope.tile(), 1, log)
            _c14 = not (_w15)
        if _c14:
            continue
        again = locs.query().name('Rope').action('Climb-up').within(4).nearest()
        if not again or not (again.interact('Climb-up')):
            continue
        yield from execution.delay_until(lambda: not in_dig_cave(game.tile()), CLIMB_MS)
        yield from settle_scene()
    if not in_dig_cave(game.tile()):
        return True
    log('the climb out of the dig shaft never reached the surface')
    return False


def tile_of(snap):
    """For the branches that must escape a shaft first."""
    return snap.tile

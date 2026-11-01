"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/supplies.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items
from rs2004.execution import event_signal
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_ITEM, DIG_LOC, DIG_NPC, DIG_SOIL_IDS, DIG_TILE
from rs2004.quests.defs.digsite.common import banked_id, drive_until_held, drop_spoil, held_id, loc_by_id_action, loc_by_ids, npc_by_id, talk_to_npc_id, walk_to
from rs2004.quests.exec.prompts import drive_choice, settle_scene
from rs2004.quests.food import quest_food
from rs2004.reach import reach
from rs2004.trade import shop

__all__ = ['SHOP', 'digsite_state', 'reset_digsite_state', 'kit', 'buy', 'herblore_kit', 'take_panning_tray', 'take_specimen_jar', 'pickpocket_workman', 'pan_until', 'dig_until']

COIN_LOW = 200
COIN_FLOAT = 5000
FOOD_TARGET = 8
FOOD_LOW = 3
SHOP = Record({
    'GENERAL': Record({'npc': 'Shop keeper', 'anchor': DIG_TILE.GENERAL_STORE}),
    'TEA': Record({'npc': 'Tea seller', 'anchor': DIG_TILE.TEA_SELLER}),
    'HERBLORE': Record({'npc': 'Jatix', 'anchor': DIG_TILE.JATIX}),
})
# Why: the panning invite is a `%itexam_bits` bit the client never sees and the guide's greeting wraps across components, so the pan attempt itself is the oracle.
digsite_state = Record({'tea_wanted': False})


def reset_digsite_state():
    digsite_state.tea_wanted = False


# Why: `ownsInventory` opts the module out of the engine's coin and food withdrawal, so both are drawn here.
def kit(snap):
    """The coin and food top-up, or null when the pack is ready."""
    coins_held = held_id(snap, DIG_ID.COINS)
    coins_banked = banked_id(snap, DIG_ID.COINS)
    need_coins = coins_held < COIN_LOW and coins_banked > 0
    food_name = quest_food.name.strip() if quest_food.name is not None else None
    food_held = snap.inv.get(food_name.lower(), 0) if food_name else 0
    food_banked = snap.bank.get(food_name.lower(), 0) if food_name and snap.bank is not None else 0
    need_food = bool(food_name) and food_held < FOOD_LOW and food_banked > 0
    if not need_coins and not need_food:
        return None
    items = []
    if need_coins:
        items.append({'name': DIG_ITEM.COINS, 'qty': min(COIN_FLOAT, coins_banked), 'id': DIG_ID.COINS})
    if need_food and food_name:
        items.append({'name': food_name, 'qty': min(FOOD_TARGET - food_held, food_banked)})
    return Record({'kind': 'withdraw', 'items': items, 'bank': DIG_TILE.VARROCK_BANK})


def buy(item, qty, shop, est_gp):
    return Record({
        'kind': 'buy',
        'item': item,
        'qty': qty,
        'shop': Record({'npc': shop.npc, 'anchor': shop.anchor}),
        'est_gp': est_gp,
    })


# Why: Jatix is 400 tiles from the site and the only counter in reach that stocks either, so one trip buys both.
def herblore_kit(need_vial, need_pestle):
    """The vial and the pestle, from the nearest herblore counter, in a single visit."""
    wanted = [_x for _x in [(DIG_ITEM.VIAL if need_vial else ''), (DIG_ITEM.PESTLE if need_pestle else '')] if _x]

    def _fn1(log):
        _w2 = yield from walk_to(SHOP.HERBLORE.anchor, 3, log)
        if not (_w2):
            return False
        _w3 = yield from shop.open(SHOP.HERBLORE.npc)
        if not (_w3):
            log(f'no {SHOP.HERBLORE.npc} shop at ({SHOP.HERBLORE.anchor.x},{SHOP.HERBLORE.anchor.z})')
            return False
        if need_vial:
            yield from shop.buy(DIG_ITEM.VIAL, 1)
        if need_pestle:
            yield from shop.buy(DIG_ITEM.PESTLE, 1)
        yield from shop.close()
        got_vial = not need_vial or inventory.count_by_id(DIG_ID.VIAL) > 0
        got_pestle = not need_pestle or inventory.count_by_id(DIG_ID.PESTLE) > 0
        if not got_vial or not got_pestle:
            log(f'the herblore counter was short (vial={got_vial}, pestle={got_pestle})')
        return got_vial and got_pestle
    return Record({'kind': 'custom', 'name': f"buy {' and '.join(wanted)} from {SHOP.HERBLORE.npc}", 'run': _fn1})


def take_panning_tray(log):
    """The lone panning tray spawn sits on a blocked tile, so the Take is clicked from the tile north of it."""
    if inventory.count_by_id(DIG_ID.TRAY_EMPTY) + inventory.count_by_id(DIG_ID.TRAY_MUD) > 0:
        return True
    _w4 = yield from walk_to(DIG_TILE.TRAY_SPAWN_STAND, 0, log)
    if not (_w4):
        return False
    yield from settle_scene()
    tray = ground_items.query().where(lambda g: g.id == DIG_ID.TRAY_EMPTY).within(3).nearest()
    if not tray:
        log('no panning tray on the ground at (3369,3378) — it respawns, so this retries')
        yield from execution.delay_ticks(4)
        return False
    if not (tray.interact('Take')):
        return False
    _result5 = yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.TRAY_EMPTY) > 0, 8000)
    return _result5


def take_specimen_jar(log):
    """The sacks beside the southern dig hold a specimen jar for anyone not already carrying one."""
    if inventory.count_by_id(DIG_ID.SPECIMEN_JAR) > 0:
        return True
    _w6 = yield from walk_to(DIG_TILE.SACKS_STAND, 1, log)
    if not (_w6):
        return False
    yield from settle_scene()
    sacks = loc_by_id_action([DIG_LOC.SAMPLE_SACKS], 'Search', 6)
    if not sacks:
        log('no sample sacks within six tiles of (3359,3399)')
        return False
    if not (sacks.interact('Search')):
        return False
    _result7 = yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.SPECIMEN_JAR) > 0, [], log, 15000)
    return _result7


def STEAL_SETTLED(text):
    lower = text.lower()
    return 'you steal' in lower or 'you find a specimen brush' in lower or 'you fail to pick' in lower or 'stunned' in lower


PICKPOCKET_MS = 8 * 60000
# Why: a pocket hands over 4 pairs of gloves and 6 brushes on the way to 2 ropes, and tidying only at 4 free slots hands the cave legs a full pack.
SPOIL_FREE = 10


# Why: the specimen brush has no other source ("we have a bit of a shortage of those at the moment") and the green student's rock sample is only ever a pocket.
def pickpocket_workman(want, log):
    """Steal from digsite workmen until the goal lands, dropping the spade-and-bucket spoil as it comes."""
    if want():
        return True
    _c8 = not npc_by_id(DIG_NPC.WORKMAN, 10)
    if _c8:
        _w9 = yield from walk_to(DIG_TILE.WORKMEN, 5, log)
        _c8 = not (_w9)
    if _c8:
        return False
    deadline = _core.step_time() + PICKPOCKET_MS
    while _core.step_time() < deadline and not want():
        if event_signal.pending():
            return want()
        yield from modals.close_if_open()
        yield from drop_spoil(log, SPOIL_FREE)
        if not npc_by_id(DIG_NPC.WORKMAN, 14):
            yield from walk_to(DIG_TILE.WORKMEN, 4, log)
            yield from settle_scene()
            continue
        mark = game_messages.mark()
        target = npc_by_id(DIG_NPC.WORKMAN, 14)
        status = yield from reach.entity_op(lambda: npc_by_id(DIG_NPC.WORKMAN, 14), 'Steal-from', lambda: want() or modals.is_open() or game_messages.saw_since(mark, STEAL_SETTLED), expect_ms=12000, what='digsite workman', log=log)
        # Why: the nearest workman is often inside a fenced dig site and the server refuses a pocket it can't path to; walking to his own tile lets the baked graph find the gate.
        if status == 'unreachable' and target:
            yield from walk_to(target.tile(), 2, log)
        if game_messages.saw_since(mark, 'stunned'):
            yield from execution.delay_ticks(9)
        yield from execution.delay_ticks(1)
    yield from modals.close_if_open()
    yield from drop_spoil(log, SPOIL_FREE)
    if want():
        return True
    log(f'{round(PICKPOCKET_MS / 60000)}min of pickpocketing did not turn up what the quest needs')
    return False


PAN_MS = 10 * 60000


def pan_until(want, log):
    """Pan and search the tray until the wanted object lands."""
    if want():
        return True
    _w10 = yield from take_panning_tray(log)
    if not (_w10):
        return False
    _w11 = yield from walk_to(DIG_TILE.PANNING_STAND, 1, log)
    if not (_w11):
        return False
    deadline = _core.step_time() + PAN_MS
    while _core.step_time() < deadline and not want():
        if event_signal.pending():
            return want()
        # Why: every pan and search ends in an objbox, and leaving it up makes the next click's "did a dialogue open?" read the last one.
        for i in range(4):
            if not (chat_dialog.can_continue()):
                break
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
        yield from modals.close_if_open()
        yield from drop_spoil(log, SPOIL_FREE)
        mud = ([i for i in inventory.items() if i.id == DIG_ID.TRAY_MUD] or [None])[0]
        if mud:
            if mud.interact('Search'):
                yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.TRAY_MUD) == 0, 10000)
            yield from execution.delay_ticks(1)
            continue
        if inventory.count_by_id(DIG_ID.TRAY_EMPTY) == 0:
            _w12 = yield from take_panning_tray(log)
            if not (_w12):
                return want()
            continue
        yield from settle_scene()
        point = loc_by_id_action([DIG_LOC.PANNING_POINT], 'Look', 8)
        if not point:
            yield from walk_to(DIG_TILE.PANNING_STAND, 1, log)
            continue
        if not (point.interact('Look')):
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_until(lambda: inventory.count_by_id(DIG_ID.TRAY_MUD) > 0 or chat_dialog.is_open() or chat_dialog.can_continue(), 12000)
        # Why: a filled tray is the success oracle and lands before the objbox, so the dialogue test only means anything while the tray is still empty.
        if inventory.count_by_id(DIG_ID.TRAY_MUD) > 0:
            continue
        if chat_dialog.is_open() or chat_dialog.can_continue():
            tea_before = inventory.count_by_id(DIG_ID.CUP_OF_TEA)
            yield from drive_choice(['So how do I become invited then?', "I've some here that you can have."], log)
            yield from modals.close_if_open()
            if inventory.count_by_id(DIG_ID.CUP_OF_TEA) < tea_before:
                digsite_state.tea_wanted = False
                log('the panning guide took the tea at the water')
                continue
            digsite_state.tea_wanted = True
            log('the panning guide refused the pan — he wants a cup of tea')
            return want()
    yield from modals.close_if_open()
    yield from drop_spoil(log, SPOIL_FREE)
    return want()


DIG_MS = 12 * 60000
DUG_THROUGH = 'you dig through the earth'
DIG_SETTLED = 'you find'


# Why: `[oplocu,_digsite_soil]` picks the exam level from the soil's own coordinate, so a soil loc a tile outside the zone is a different site with a different refusal.
def dig_until(zone, want, log):
    """Use the trowel on soil inside one dig zone until the wanted object lands."""
    if want():
        return True
    _w13 = yield from walk_to(zone.stand, 0, log)
    if not (_w13):
        return False
    deadline = _core.step_time() + DIG_MS
    refusals = 0
    while _core.step_time() < deadline and not want():
        if event_signal.pending():
            return want()
        yield from drive_choice([], log)
        yield from modals.close_if_open()
        yield from drop_spoil(log, SPOIL_FREE)
        trowel = ([i for i in inventory.items() if i.id == DIG_ID.TROWEL] or [None])[0]
        if not trowel:
            log('no trowel in the pack to dig with')
            return False
        yield from settle_scene()

        def _fn14(l):
            t = l.tile()
            return t.x >= zone.min_x and t.x <= zone.max_x and t.z >= zone.min_z and t.z <= zone.max_z
        soil = loc_by_ids(DIG_SOIL_IDS, 2, _fn14)
        if not soil:
            log(f'no diggable soil inside x {zone.min_x}..{zone.max_x}, z {zone.min_z}..{zone.max_z}')
            yield from walk_to(zone.stand, 0, log)
            continue
        mark = game_messages.mark()
        if not (trowel.use_on(soil)):
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_until(lambda: want() or modals.is_open() or chat_dialog.is_open() or chat_dialog.can_continue() or game_messages.saw_since(mark, DUG_THROUGH), 15000)
        # Why: a workman within 10 tiles turns every refusal into a `~chatnpcnoturn` line with no game message, so a missing "You dig through the earth" is what says the pack is short a jar, a brush or a certificate.
        if want() or game_messages.saw_since(mark, DUG_THROUGH):
            refusals = 0
            # Why: the find lands 6 ticks after that message and you're delayed until it does, so a trowel clicked on the message is dropped and the loop pays a full timeout.
            yield from execution.delay_until(lambda: want() or game_messages.saw_since(mark, DIG_SETTLED), 12000)
        else:
            refusals += 1
            if refusals >= 3:
                for line in game_messages.since(mark):
                    log(f'dig refused: {line.text}')
                log(f'three digs at ({zone.stand.x},{zone.stand.z}) turned no earth — the site refused them')
                yield from drive_choice([], log)
                yield from modals.close_if_open()
                return False
        yield from execution.delay_ticks(1)
    yield from modals.close_if_open()
    yield from drop_spoil(log, SPOIL_FREE)
    return want()

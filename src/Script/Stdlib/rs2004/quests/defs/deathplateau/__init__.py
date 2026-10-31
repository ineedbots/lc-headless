"""Ported from rs2b0t's src/bot/api/ai/quests/defs/deathplateau/index.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.defs.deathplateau.areas import ALE_PRICE, ALL_BALL_IDS, BALL_PICKUP, BLURBERRY_SHOP, COIN_FLOAT, DEATH_ITEM, DENULTH_FINISH, DENULTH_START, DUNSTAN_SPIKES, EOHRIC_GUARD, EOHRIC_HAROLD_REFUSED, FALADOR_WEST_BANK, GAMBLE_STAKE_FLOAT, HAROLD_DUTY, PEDESTALS, SABA_PATH, TENZING_HELP, TENZING_SUPPLIES, TILE, TOSTIG_SHOP
from rs2004.quests.defs.deathplateau.harold import close_dice_if_open, gamble_with_harold, give_ale_to_harold, inside_harold_room, reclaim_iou_from_harold, talk_in_harold_room
from rs2004.quests.defs.deathplateau.journal import DEATH_PLATEAU_QUEST, DP_FLAG, DP_STAGE, normalize_journal, parse_death_plateau_journal, read_death_plateau_progress
from rs2004.quests.defs.deathplateau.nav import on_secret_path, talk_at, walk_secret_path, walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import drive_dialog, open_dialogue
from rs2004.quests.exec.prompts import settle_scene

__all__ = ['DEATH_PLATEAU_QUEST', 'DP_FLAG', 'DP_STAGE', 'parse_death_plateau_journal', 'read_death_plateau_progress', 'normalize_journal', 'ALL_BALL_IDS', 'DEATH_ITEM', 'FALADOR_WEST_BANK', 'PEDESTALS', 'TILE', 'close_dice_if_open', 'inside_harold_room', 'equip_floor', 'effective_map', 'decide', 'deathplateau']


# snapshot helpers
def held_name(snap, name):
    count = snap.inv.get(name.lower())
    return count if count is not None else 0


def held_id(snap, id):
    count = snap.inv_ids.get(id) if snap.inv_ids is not None else None
    return count if count is not None else 0


def banked_name(snap, name):
    count = snap.bank.get(name.lower()) if snap.bank is not None else None
    return count if count is not None else 0


def banked_id(snap, id):
    count = snap.bank_ids.get(id) if snap.bank_ids is not None else None
    return count if count is not None else 0


def live_id(id):
    return sum([i.count for i in [i for i in inventory.items() if i.id == id]])


def any_ball_held(snap):
    return sum([held_id(snap, id) for id in ALL_BALL_IDS])


def in_saba_cave(tile):
    return tile is not None and tile is not None and tile.x >= 2255 and tile.x <= 2285 and tile.z >= 4740 and tile.z <= 4775


def equip_floor(snap, progress):
    """Inventory-aware equip-room floor (can outrank a stale journal mid-step)."""
    _v1 = (progress.stage if progress is not None else None)
    stage = (_v1 if _v1 is not None else DP_STAGE.NOT_STARTED)
    if held_id(snap, DEATH_ITEM.COMBINATION.id) > 0 and stage < DP_STAGE.FOUND_COMBO:
        stage = DP_STAGE.FOUND_COMBO
    if held_id(snap, DEATH_ITEM.IOU.id) > 0 and stage < DP_STAGE.GIVEN_IOU:
        stage = DP_STAGE.GIVEN_IOU
    if any_ball_held(snap) > 0 and stage < DP_STAGE.FOUND_COMBO:
        stage = DP_STAGE.FOUND_COMBO
    return stage


def map_flag(progress, name):
    return has_flag(progress, name)


def effective_map(snap, progress):
    """Inventory can prove map milestones the journal has not yet rewritten."""

    def f(name):
        return map_flag(progress, name)

    climbing = held_id(snap, DEATH_ITEM.CLIMBING_BOOTS.id) > 0
    spiked = held_id(snap, DEATH_ITEM.SPIKED_BOOTS.id) > 0
    cert = held_id(snap, DEATH_ITEM.ENTRANCE_CERT.id) > 0
    secret_map = held_id(snap, DEATH_ITEM.SECRET_MAP.id) > 0
    scouted = f(DP_FLAG.SCOUTED)
    got_map = scouted or f(DP_FLAG.GOT_MAP) or secret_map
    supplies = got_map or f(DP_FLAG.SUPPLIES)
    given_cert = supplies or f(DP_FLAG.GIVEN_CERT) or spiked
    entrancecert = given_cert or f(DP_FLAG.ENTRANCE_CERT) or cert
    smithy = entrancecert or f(DP_FLAG.SMITHY)
    tenzing = smithy or f(DP_FLAG.TENZING) or climbing or spiked
    saba = tenzing or f(DP_FLAG.SABA)
    return Record({
        'saba': saba,
        'tenzing': tenzing,
        'smithy': smithy,
        'entrancecert': entrancecert,
        'given_cert': given_cert,
        'supplies': supplies,
        'got_map': got_map,
        'scouted': scouted,
    })


# banking / loadout
KEEP = [
    'coins',
    DEATH_ITEM.ASGARNIAN_ALE.name.lower(),
    DEATH_ITEM.BLURBERRY_SPECIAL.name.lower(),
    DEATH_ITEM.IOU.name.lower(),
    DEATH_ITEM.COMBINATION.name.lower(),
    DEATH_ITEM.SECRET_MAP.name.lower(),
    DEATH_ITEM.CLIMBING_BOOTS.name.lower(),
    DEATH_ITEM.SPIKED_BOOTS.name.lower(),
    DEATH_ITEM.ENTRANCE_CERT.name.lower(),
    DEATH_ITEM.BREAD.name.lower(),
    DEATH_ITEM.TROUT.name.lower(),
    DEATH_ITEM.IRON_BAR.name.lower(),
    'stone ball',
]


def scan_bank():
    return Record({'kind': 'scan_bank', 'bank': FALADOR_WEST_BANK})


def withdraw(items):
    return Record({'kind': 'withdraw', 'items': items, 'bank': FALADOR_WEST_BANK})


def deposit_keep(keep=None):
    if keep is None:
        keep = KEEP
    return Record({'kind': 'deposit', 'keep': keep, 'bank': FALADOR_WEST_BANK, 'exact_keep': True})


def make_space(snap, slots):
    if snap.free_slots is not None and snap.free_slots >= slots:
        return None
    junk = any([not (n in KEEP) for n in list(list(snap.inv.keys()))])
    if junk:
        return deposit_keep()
    return Record({'kind': 'deposit', 'keep': ['coins'], 'bank': FALADOR_WEST_BANK, 'exact_keep': True})


def source_coins(snap, need):
    if held_name(snap, 'Coins') >= need:
        return None
    if not snap.bank_known:
        return scan_bank()
    in_bank = banked_name(snap, 'Coins')
    if in_bank <= 0:
        return Record({'kind': 'wait', 'reason': 'need coins for Death Plateau'})
    _v2 = make_space(snap, (1 if held_name(snap, 'Coins') == 0 else 0))
    return (_v2 if _v2 is not None else withdraw([{'name': 'Coins', 'qty': min(COIN_FLOAT, in_bank)}]))


def source_named(snap, name, id, qty):
    have = max(held_name(snap, name), held_id(snap, id))
    if have >= qty:
        return None
    if not snap.bank_known:
        return scan_bank()
    short = qty - have
    in_bank = max(banked_name(snap, name), banked_id(snap, id))
    if in_bank <= 0:
        return Record({'kind': 'wait', 'reason': f'need {qty}× {name} in bank for Death Plateau'})
    _v3 = make_space(snap, short)
    return (_v3 if _v3 is not None else withdraw([{'name': name, 'qty': min(short, in_bank), 'id': id}]))


def source_cocktail(snap):
    drinks = [DEATH_ITEM.BLURBERRY_SPECIAL, DEATH_ITEM.PREMADE_BLURBERRY_SPECIAL]
    if any([held_id(snap, drink.id) > 0 for drink in drinks]):
        return None
    if not snap.bank_known:
        return scan_bank()
    banked = ([drink for drink in drinks if banked_id(snap, drink.id) > 0] or [None])[0]
    _v5 = make_space(snap, 1)
    if _v5 is not None:
        return _v5
    if banked:
        return withdraw([{'id': banked.id, 'name': banked.name, 'qty': 1}])
    return Record({'kind': 'buy', 'item': DEATH_ITEM.BLURBERRY_SPECIAL.name, 'qty': 1, 'shop': BLURBERRY_SHOP, 'est_gp': 30})


def normalize_pack(snap):
    return (deposit_keep() if any([not (n in KEEP) for n in list(list(snap.inv.keys()))]) else None)


# custom runners
def leave_saba_cave(log):
    if not in_saba_cave(game.tile()):
        return True
    _w6 = yield from walk_to(TILE.SABA_EXIT, 3, log)
    if not (_w6):
        return False
    _v7 = locs.query().name('Cave Exit').action('Exit').within(8).nearest()
    exit = (_v7 if _v7 is not None else locs.query().name('Cave Exit').within(8).nearest())
    if not exit:
        log('no Cave Exit in Saba cave')
        return False
    _v8 = ([a for a in exit.actions() if ('exit' in a.lower() or 'climb' in a.lower() or 'enter' in a.lower())] or [None])[0]
    op = (_v8 if _v8 is not None else (exit.actions() or [None])[0])
    if not op or not (exit.interact(op)):
        return False
    _result9 = yield from execution.delay_until(lambda: not in_saba_cave(game.tile()), 8000)
    return _result9


def enter_saba_cave(log):
    if in_saba_cave(game.tile()):
        return True
    _w10 = yield from walk_to(TILE.SABA_ENTRANCE, 2, log)
    if not (_w10):
        return False
    yield from settle_scene()
    entrance = locs.query().name('Cave Entrance').within(8).nearest()
    if not entrance:
        log('no Cave Entrance near Saba')
        return False
    _v11 = ([a for a in entrance.actions() if ('enter' in a.lower() or 'climb' in a.lower() or 'search' in a.lower())] or [None])[0]
    op = (_v11 if _v11 is not None else (entrance.actions() or [None])[0])
    if not op or not (entrance.interact(op)):
        return False
    _result12 = yield from execution.delay_until(lambda: in_saba_cave(game.tile()), 8000)
    return _result12


def open_tenzing_door(log):
    if npcs.query().name('Tenzing').within(6).nearest():
        return True
    _w13 = yield from walk_to(TILE.TENZING_DOOR, 2, log)
    if not (_w13):
        return False
    door = locs.query().name('Door').within(6).nearest()
    if not door:
        return True
    if not (door.interact('Open')):
        return False
    # After Saba: knock, "No milk today!", auto "I'm not the milkman", open.
    _w14 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 3000)
    if _w14:
        yield from drive_dialog(["I'm not the milkman", 'I need your help'], log)
    yield from execution.delay_ticks(2)
    return True


def read_iou(log):
    if live_id(DEATH_ITEM.COMBINATION.id) > 0:
        return True
    iou = ([i for i in inventory.items() if i.id == DEATH_ITEM.IOU.id] or [None])[0]
    if not iou:
        log('no IOU to read')
        return False
    # opheld1 death_iou: Read replaces the IOU with the Combination plus chat/objbox.
    _v15 = ([a for a in iou.actions() if ('read' in a.lower())] or [None])[0]
    op = (_v15 if _v15 is not None else (iou.actions() or [None])[0])
    # Why: the server runs a held op as a protected script, which an open dialogue refuses without a word, and the gamble ends on Harold's fresh menu.
    # Why: rs2b0t's webclient click closed that menu on its way; a packet doesn't, so the read waits behind it until it's shut.
    if chat_dialog.is_open() or chat_dialog.can_continue() or reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if not op or not (iou.interact(op)):
        log(f"could not {(op if op is not None else 'use')} IOU")
        return False
    for i in range(30):
        if live_id(DEATH_ITEM.COMBINATION.id) > 0 and not chat_dialog.is_open() and not chat_dialog.can_continue():
            # Combination granted; close leftover handwriting scroll if open.
            yield from modals.close_if_open()
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if chat_dialog.is_open():
            yield from drive_dialog([], log)
            continue
        if reader.modals().main != -1:
            # objbox "You have found the combination!" or leftover scroll.
            cont = reader.main_modal_button_near_text('Click here to continue')
            if cont > 0:
                _core.click_component(cont)
            else:
                _core.close_interfaces()
            yield from execution.delay_ticks(2)
            continue
        yield from execution.delay_ticks(1)
    log(f'read IOU done, combo={live_id(DEATH_ITEM.COMBINATION.id)}')
    return live_id(DEATH_ITEM.COMBINATION.id) > 0


def ball_on_tile(at, ball_id=None):
    def _fn16(item):
        t = item.tile()
        if t.x != at.x or t.z != at.z or t.level != at.level:
            return False
        return ((item.id in ALL_BALL_IDS) if ball_id is None else item.id == ball_id)
    return ground_items.query().where(_fn16).within(20).nearest() is not None


def all_pedestals_correct():
    return all([ball_on_tile(p.at, p.ball_id) for p in PEDESTALS])


def take_ground_ball(ball_id, near, log):
    if live_id(ball_id) > 0:
        return True
    _w17 = yield from walk_to(near, 2, log)
    if not (_w17):
        return False
    yield from settle_scene()
    g = ground_items.query().where(lambda item: item.id == ball_id).within(10).nearest()
    if not g:
        log(f'stone ball {ball_id} not on the ground near ({near.x},{near.z})')
        return False
    if not (g.interact('Take')):
        return False
    _result18 = yield from execution.delay_until(lambda: live_id(ball_id) > 0, 6000)
    return _result18


# Why: the content order is blue (2894,3562), yellow (2895,3562), red (2894,3563), purple (2895,3563), green (2895,3564).
# Why: the balls are placed one at a time from the ground or the pack, so all 5 needn't be held at once.
def solve_stone_mechanism(log):
    """Place the 5 coloured balls on the mechanism."""
    if all_pedestals_correct():
        log('all stone balls already correctly placed')
        return True
    # Clear wrong balls off pedestals first.
    for ped in PEDESTALS:
        if ball_on_tile(ped.at, ped.ball_id) or not ball_on_tile(ped.at):
            continue
        _w19 = yield from walk_to(ped.at, 2, log)
        if not (_w19):
            return False
        wrong = ground_items.query().where(lambda item: (item.id in ALL_BALL_IDS) and item.tile().x == ped.at.x and item.tile().z == ped.at.z).within(8).nearest()
        if wrong:
            log(f'removing wrong ball from ({ped.at.x},{ped.at.z})')
            wrong.interact('Take')
            yield from execution.delay_until(lambda: not ball_on_tile(ped.at) or live_id(wrong.id) > 0, 5000)
    for ped in PEDESTALS:
        if ball_on_tile(ped.at, ped.ball_id):
            continue
        # Source the ball: inv, then the ground pile, then anywhere nearby.
        if live_id(ped.ball_id) <= 0:
            pile = ([b for b in BALL_PICKUP if b.id == ped.ball_id] or [None])[0]
            _v20 = (pile.at if pile is not None else None)
            _w21 = yield from take_ground_ball(ped.ball_id, (_v20 if _v20 is not None else ped.at), log)
            if not (_w21):
                # Maybe sitting on another pedestal after a previous wrong place.
                stray = ground_items.query().where(lambda item: item.id == ped.ball_id).within(16).nearest()
                if stray:
                    _w22 = yield from walk_to(Tile(stray.tile().x, stray.tile().z, stray.tile().level), 2, log)
                    if not (_w22):
                        return False
                    stray.interact('Take')
                    _w23 = yield from execution.delay_until(lambda: live_id(ped.ball_id) > 0, 6000)
                    if not (_w23):
                        return False
                else:
                    log(f'cannot find {ped.color} ball to place')
                    return False
        _w24 = yield from walk_to(ped.at, 2, log)
        if not (_w24):
            return False
        yield from settle_scene()

        # Exact loc_coord match, content drops the ball on the mechanism tile; nearest() within 1 hit the wrong pedestal (6 mechanisms in a 2x3 grid).
        def _fn25(loc):
            t = loc.tile()
            return t.x == ped.at.x and t.z == ped.at.z and t.level == ped.at.level
        mech = locs.query().name('Stone Mechanism').where(_fn25).within(10).nearest()
        ball = ([i for i in inventory.items() if i.id == ped.ball_id] or [None])[0]
        if not mech or not ball:
            log(f'no Stone Mechanism or {ped.color} ball at ({ped.at.x},{ped.at.z})')
            return False
        log(f'placing {ped.color} ball on mechanism at {mech.tile()}')
        if not (ball.use_on(mech)):
            return False
        _w26 = yield from execution.delay_until(lambda: ball_on_tile(ped.at, ped.ball_id), 8000)
        if not (_w26):
            # Content drops at loc_coord, accept any ball of this id within 1 of ped.
            ok = ground_items.query().where(lambda item: item.id == ped.ball_id and item.tile().distance_to(ped.at) <= 1).within(8).nearest() is not None
            if not ok:
                log(f'{ped.color} ball did not land on pedestal')
                return False
    if all_pedestals_correct():
        log('stone mechanism complete, door should unlock')
        yield from execution.delay_ticks(2)
        return True
    return False


def scout_secret_path(log):
    _c27 = not on_secret_path(game.tile())
    if _c27:
        _w28 = yield from walk_secret_path(TILE.STILE_NORTH, log)
        _c27 = not (_w28)
    if _c27:
        return False
    _w29 = yield from walk_secret_path(TILE.SCOUT, log)
    if not (_w29):
        return False
    yield from settle_scene()
    # Zone script fires chat once the tile is entered with got_map.
    _w30 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 5000)
    if _w30:
        yield from drive_dialog([], log)
    return True


def hand_in_to_denulth(log):
    _c31 = on_secret_path(game.tile())
    if _c31:
        _w32 = yield from walk_secret_path(TILE.STILE_SOUTH, log)
        _c31 = not (_w32)
    if _c31:
        return False
    _c33 = in_saba_cave(game.tile())
    if _c33:
        _w34 = yield from leave_saba_cave(log)
        _c33 = not (_w34)
    if _c33:
        return False
    _w35 = yield from walk_secret_path(TILE.DENULTH, log)
    if not (_w35):
        return False
    _result36 = yield from talk_at(DENULTH_FINISH, log)
    return _result36


def drain_until(done, log, max_=40):
    """Drain chat + objbox until quiet or `done()` is true."""
    for i in range(max_):
        if done():
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if chat_dialog.is_open() and len(chat_dialog.options()) > 0:
            yield from drive_dialog([], log)
            continue
        if reader.modals().main != -1:
            cont = reader.main_modal_button_near_text('Click here to continue')
            if cont > 0:
                _core.click_component(cont)
            else:
                _core.close_interfaces()
            yield from execution.delay_ticks(2)
            continue
        if not chat_dialog.is_open():
            yield from execution.delay_ticks(1)
            if done() or (not chat_dialog.is_open() and reader.modals().main == -1):
                return done()
        yield from execution.delay_ticks(1)
    return done()


def take_entrance_cert_from_ground(log):
    """Certificate dropped underfoot when Denulth grants it into a full pack."""
    if live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0:
        return True
    if inventory.is_full():
        log('pack full, cannot take entrance certificate from the ground')
        return False
    _v37 = ground_items.query().where(lambda item: item.id == DEATH_ITEM.ENTRANCE_CERT.id).within(8).nearest()
    drop = (_v37 if _v37 is not None else ground_items.query().name(DEATH_ITEM.ENTRANCE_CERT.name).within(8).nearest())
    if not drop:
        return False
    log(f'taking entrance certificate from the ground at {drop.tile()}')
    if not (drop.interact('Take')):
        return False
    _result38 = yield from execution.delay_until(lambda: live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0, 8000)
    return _result38


def get_entrance_cert_from_denulth(log):
    """Denulth auto-runs denulth_cert when map is spoken_smithy..got_entrancecert."""
    if live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0:
        return True
    # Prior full-pack grant leaves the cert on the floor near Denulth.
    _w39 = yield from take_entrance_cert_from_ground(log)
    if _w39:
        return True
    for attempt in range(3):
        _w40 = yield from walk_to(TILE.DENULTH, 2, log)
        if not (_w40):
            return False
        yield from settle_scene()
        # Retry floor loot after walking over (drop may only stream in scene).
        _w41 = yield from take_entrance_cert_from_ground(log)
        if _w41:
            return True
        # decide() should have made space; refuse to talk while full so the cert doesn't drop again.
        if inventory.is_full() or inventory.free() < 1:
            log('need a free inventory slot before Denulth gives the certificate')
            return False
        _w42 = yield from open_dialogue('Denulth', log)
        if not (_w42):
            yield from execution.delay_ticks(2)
            continue
        _w43 = yield from drain_until(lambda: live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0 or ground_items.query().where(lambda i: i.id == DEATH_ITEM.ENTRANCE_CERT.id).within(6).nearest() is not None, log)
        if _w43:
            if live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0:
                log(f'entrance cert, held={live_id(DEATH_ITEM.ENTRANCE_CERT.id)}')
                return True
            # Server dumped it underfoot despite free-slot check (race / inv_add).
            _w44 = yield from take_entrance_cert_from_ground(log)
            if _w44:
                return True
    log(f'entrance cert, held={live_id(DEATH_ITEM.ENTRANCE_CERT.id)}')
    if live_id(DEATH_ITEM.ENTRANCE_CERT.id) > 0:
        return True
    _result45 = yield from take_entrance_cert_from_ground(log)
    return _result45


def give_cert_to_dunstan(log):
    """Give cert to Dunstan, map flag given_cert; may immediately offer the spiked boots bargain."""
    if live_id(DEATH_ITEM.ENTRANCE_CERT.id) <= 0:
        _result46 = yield from get_entrance_cert_from_denulth(log)
        return _result46
    _w47 = yield from walk_to(TILE.DUNSTAN, 2, log)
    if not (_w47):
        return False
    _w48 = yield from open_dialogue('Dunstan', log)
    if not (_w48):
        return False
    # Cert is consumed on talk when map is got_entrancecert.
    before = live_id(DEATH_ITEM.ENTRANCE_CERT.id)
    yield from drain_until(lambda: live_id(DEATH_ITEM.ENTRANCE_CERT.id) < before or live_id(DEATH_ITEM.SPIKED_BOOTS.id) > 0, log)
    log(f'gave cert, cert={live_id(DEATH_ITEM.ENTRANCE_CERT.id)} spiked={live_id(DEATH_ITEM.SPIKED_BOOTS.id)}')
    return live_id(DEATH_ITEM.ENTRANCE_CERT.id) < before or live_id(DEATH_ITEM.SPIKED_BOOTS.id) > 0


# decide
def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def decide(snap):
    """Pure decide from journal stage, map flags and inventory. The equip-room track runs before the map track so pack space is free for balls."""
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    progress = snap.progress
    if progress is None and snap.journal == 'in_progress':
        return Record({'kind': 'wait', 'reason': 'Death Plateau journal stage unavailable'})
    stage = equip_floor(snap, progress)
    map = effective_map(snap, progress)
    if stage >= DP_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if stage >= DP_STAGE.GIVEN_IOU and held_id(snap, DEATH_ITEM.COMBINATION.id) == 0:
        if held_id(snap, DEATH_ITEM.IOU.id) > 0:
            return custom('read the IOU (combination on the back)', read_iou)
        if not snap.bank_known:
            return scan_bank()
        paper = ([item for item in [DEATH_ITEM.COMBINATION, DEATH_ITEM.IOU] if banked_id(snap, item.id) > 0] or [None])[0]
        if paper:
            _v50 = make_space(snap, 1)
            return (_v50 if _v50 is not None else withdraw([{'id': paper.id, 'name': paper.name, 'qty': 1}]))
    # finish: both tracks done
    if stage >= DP_STAGE.UNLOCKED_DOOR and map.scouted:
        if held_id(snap, DEATH_ITEM.SECRET_MAP.id) == 0 and not map.scouted:
            pass
        # Need map + combination in pack for the hand-in bits.
        if held_id(snap, DEATH_ITEM.COMBINATION.id) == 0:
            # Already unlocked without the paper, Denulth still asks for it; reclaim from Harold.
            return custom('reclaim combination from Harold', reclaim_iou_from_harold)
        if held_id(snap, DEATH_ITEM.SECRET_MAP.id) == 0:
            def _fn51(log):
                _w52 = yield from open_tenzing_door(log)
                if not (_w52):
                    return False
                _result53 = yield from talk_at(TENZING_SUPPLIES, log)
                return _result53
            return custom('reclaim secret way map from Tenzing', _fn51)
        return custom('give map and combination to Denulth', hand_in_to_denulth)
    # equip-room track
    if stage < DP_STAGE.UNLOCKED_DOOR:
        if stage == DP_STAGE.NOT_STARTED or snap.journal == 'not_started':
            _v54 = normalize_pack(snap)
            _v55 = (_v54 if _v54 is not None else source_coins(snap, 200))
            return (_v55 if _v55 is not None else custom('start Death Plateau with Denulth', lambda log: talk_at(DENULTH_START, log)))
        if stage == DP_STAGE.STARTED:
            return custom('ask Eohric about the night guard', lambda log: talk_at(EOHRIC_GUARD, log))
        if stage == DP_STAGE.SPOKEN_EOHRIC:
            return custom("confront Harold about last night's duty", lambda log: talk_in_harold_room(HAROLD_DUTY, log))
        if stage == DP_STAGE.SPOKEN_HAROLD:
            return custom('tell Eohric that Harold will not talk', lambda log: talk_at(EOHRIC_HAROLD_REFUSED, log))
        if stage == DP_STAGE.SPOKEN_EOHRIC2:
            if held_id(snap, DEATH_ITEM.ASGARNIAN_ALE.id) == 0:
                _v56 = source_coins(snap, ALE_PRICE + 50)
                _v57 = (_v56 if _v56 is not None else make_space(snap, 1))
                return (_v57 if _v57 is not None else Record({
                    'kind': 'buy',
                    'item': DEATH_ITEM.ASGARNIAN_ALE.name,
                    'qty': 1,
                    'shop': TOSTIG_SHOP,
                    'est_gp': ALE_PRICE,
                }))
            return custom('buy Harold an Asgarnian ale', give_ale_to_harold)
        if stage == DP_STAGE.GIVEN_ALE:
            cocktail = source_cocktail(snap)
            _v58 = source_coins(snap, GAMBLE_STAKE_FLOAT + (((cocktail.est_gp if cocktail.est_gp is not None else 0) if (cocktail.kind if cocktail is not None else None) == 'buy' else 0)))
            _v59 = (_v58 if _v58 is not None else cocktail)
            return (_v59 if _v59 is not None else custom('give Harold a Blurberry special and gamble for the IOU', gamble_with_harold))
        if stage == DP_STAGE.GIVEN_IOU:
            if held_id(snap, DEATH_ITEM.IOU.id) == 0 and held_id(snap, DEATH_ITEM.COMBINATION.id) == 0:
                return custom('reclaim IOU from Harold', reclaim_iou_from_harold)
            if held_id(snap, DEATH_ITEM.COMBINATION.id) == 0:
                return custom('read the IOU (combination on the back)', read_iou)
        if stage >= DP_STAGE.GIVEN_IOU and stage < DP_STAGE.UNLOCKED_DOOR:
            if held_id(snap, DEATH_ITEM.COMBINATION.id) == 0 and held_id(snap, DEATH_ITEM.IOU.id) > 0:
                return custom('read the IOU (combination on the back)', read_iou)
            # One custom step picks and places; balls already on correct pedestals aren't in the pack, so don't require all 5 held.
            _v60 = make_space(snap, 5)
            return (_v60 if _v60 is not None else custom('solve the stone ball mechanism', solve_stone_mechanism))
    # map track
    if not map.scouted:
        if not map.saba:
            def _fn61(log):
                _w62 = yield from enter_saba_cave(log)
                if not (_w62):
                    return False
                _w63 = yield from talk_at(SABA_PATH, log)
                if not (_w63):
                    return False
                _result64 = yield from leave_saba_cave(log)
                return _result64
            return custom('ask Saba about another path', _fn61)
        if not map.tenzing:
            # Tenzing hands climbing boots, need 1 free slot or they hit the floor.
            def _fn65(log):
                _c66 = in_saba_cave(game.tile())
                if _c66:
                    _w67 = yield from leave_saba_cave(log)
                    _c66 = not (_w67)
                if _c66:
                    return False
                _w68 = yield from open_tenzing_door(log)
                if not (_w68):
                    return False
                _result69 = yield from talk_at(TENZING_HELP, log)
                return _result69
            _v70 = make_space(snap, 1)
            return (_v70 if _v70 is not None else custom('ask Tenzing for the secret way', _fn65))
        if not map.smithy:
            def _fn71(log):
                _c72 = in_saba_cave(game.tile())
                if _c72:
                    _w73 = yield from leave_saba_cave(log)
                    _c72 = not (_w73)
                if _c72:
                    return False
                _result74 = yield from talk_at(DUNSTAN_SPIKES, log)
                return _result74
            return custom('ask Dunstan to spike the climbing boots', _fn71)
        if not map.entrancecert or (map.entrancecert and held_id(snap, DEATH_ITEM.ENTRANCE_CERT.id) == 0 and not map.given_cert):
            # Denulth grants the certificate via inv_add, full pack drops it.
            _v75 = make_space(snap, 1)
            return (_v75 if _v75 is not None else custom("get Dunstan's son signed up with Denulth (certificate)", get_entrance_cert_from_denulth))
        if not map.given_cert:
            return custom('give Dunstan the entrance certificate', give_cert_to_dunstan)
        # Spiked boots + supplies for Tenzing.
        if not map.supplies:
            if held_id(snap, DEATH_ITEM.SPIKED_BOOTS.id) == 0:
                need_bar = source_named(snap, DEATH_ITEM.IRON_BAR.name, DEATH_ITEM.IRON_BAR.id, 1)
                if need_bar:
                    return need_bar
                if held_id(snap, DEATH_ITEM.CLIMBING_BOOTS.id) == 0:
                    def _fn76(log):
                        _w77 = yield from open_tenzing_door(log)
                        if not (_w77):
                            return False
                        _result78 = yield from talk_at(TENZING_SUPPLIES, log)
                        return _result78
                    return custom('reclaim climbing boots from Tenzing', _fn76)
                return custom('have Dunstan spike the climbing boots', lambda log: talk_at(Record({
                    'npc': 'Dunstan',
                    'anchor': TILE.DUNSTAN,
                    'leash': 8,
                    'prefer': ['Yes, but I still want them.'],
                }), log))
            need_bread = source_named(snap, DEATH_ITEM.BREAD.name, DEATH_ITEM.BREAD.id, 10)
            if need_bread:
                return need_bread
            need_trout = source_named(snap, DEATH_ITEM.TROUT.name, DEATH_ITEM.TROUT.id, 10)
            if need_trout:
                return need_trout

            def _fn79(log):
                _w80 = yield from open_tenzing_door(log)
                if not (_w80):
                    return False
                _result81 = yield from talk_at(TENZING_SUPPLIES, log)
                return _result81
            return custom('deliver supplies and spiked boots to Tenzing', _fn79)
        if not map.got_map:
            # Supplies flag without map, talk again for the map hand-over.
            if held_id(snap, DEATH_ITEM.SECRET_MAP.id) == 0:
                def _fn82(log):
                    _w83 = yield from open_tenzing_door(log)
                    if not (_w83):
                        return False
                    _result84 = yield from talk_at(TENZING_SUPPLIES, log)
                    return _result84
                return custom('get the secret way map from Tenzing', _fn82)
        if held_id(snap, DEATH_ITEM.SECRET_MAP.id) == 0 and map.got_map:
            def _fn85(log):
                _w86 = yield from open_tenzing_door(log)
                if not (_w86):
                    return False
                _result87 = yield from talk_at(TENZING_SUPPLIES, log)
                return _result87
            return custom('reclaim secret way map from Tenzing', _fn85)
        return custom('scout the secret path north of Tenzing', scout_secret_path)
    return Record({'kind': 'wait', 'reason': f'Death Plateau unhandled state stage={stage}'})


deathplateau = QuestModule(**{
    'record': quest_record('death'),
    'bank': FALADOR_WEST_BANK,
    'owns_inventory': True,
    'coin_float': COIN_FLOAT,
    'read_progress': read_death_plateau_progress,
    'decide': decide,
})

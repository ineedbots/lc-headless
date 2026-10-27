"""Ported from rs2b0t's src/bot/api/ai/quests/defs/goblindiplomacy.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.primitives import goto_npc, talk_through
from rs2004.quests.exec.steps import execute_step
from rs2004.quests.food import quest_food
from rs2004.traversal import traversal


__all__ = ['GOBLIN_DIPLOMACY_COIN_TARGET', 'GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE', 'goblin_mail_gather_step', 'decide', 'goblindiplomacy']

DRAYNOR_BANK = Tile(3093, 3243, 0)
BARTENDER = Record({
    'npc': 'Bartender',
    'anchor': Tile(3045, 3257, 0),
    'leash': 8,
    'prefer': ['Not very busy in here today, is it?'],
})
GENERAL = Record({
    'npc': 'General Wartface',
    'anchor': Tile(2957, 3510, 0),
    'leash': 6,
    'prefer': ['Do you want me to pick an armour colour for you?'],
})
AGGIE_ANCHOR = Tile(3086, 3259, 0)
AGGIE_RED = Record({
    'npc': 'Aggie',
    'anchor': AGGIE_ANCHOR,
    'leash': 6,
    'prefer': [
    'Can you make dyes for me please?',
    'What do you need to make red dye?',
    'Okay, make me some red dye please.',
],
})
AGGIE_YELLOW = Record({
    'npc': 'Aggie',
    'anchor': AGGIE_ANCHOR,
    'leash': 6,
    'prefer': [
    'Can you make dyes for me please?',
    'What do you need to make yellow dye?',
    'Okay, make me some yellow dye please.',
],
})
AGGIE_BLUE = Record({
    'npc': 'Aggie',
    'anchor': AGGIE_ANCHOR,
    'leash': 6,
    'prefer': [
    'Can you make dyes for me please?',
    'What do you need to make blue dye?',
    'Okay, make me some blue dye please.',
],
})
WYSON = Record({
    'npc': 'Wyson the gardener',
    'anchor': Tile(3027, 3379, 0),
    'leash': 10,
    'prefer': ["I'm looking for woad leaves.", 'How about 20 coins?'],
})
GOBLIN_FARM = Tile(2958, 3507, 0)
ONION_PATCH = Tile(3188, 3267, 0)
PORT_SARIM_SHOP = Record({'npc': 'Wydin', 'anchor': Tile(3014, 3204, 0)})
VARROCK_FUNDING_MAN = Tile(3240, 3405, 0)
AL_KHARID_FUNDING_MAN = Tile(3279, 3188, 0)
KEBAB_SELLER = Tile(3272, 3182, 0)
GOBLIN_DIPLOMACY_COIN_TARGET = 200
GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE = 100
FALLBACK_FOOD = 'Kebab'
AL_KHARID_TOLL = 10
AL_KHARID_ENTRY_CASH = AL_KHARID_TOLL + 3
GOBLIN_DIPLOMACY_FUNDING_TARGET = GOBLIN_DIPLOMACY_COIN_TARGET + AL_KHARID_TOLL
FUNDING_MAN_LEASH = 24
SAFE_PICKPOCKET_HP = 3
FUNDING_STALL_MS = 120000
FUNDING_REGEN_WAIT_MS = 60000
GOBLIN_REATTACK_MS = 5000
GOBLIN_REJECT_MS = 15000
GOBLIN_DISENGAGE_GRACE_MS = 5000
goblin_mail_target_index = None
goblin_mail_target_engaged = False
goblin_mail_last_attack_at = 0
goblin_mail_disengaged_at = 0
goblin_mail_rejected_target_index = None
goblin_mail_rejected_until = 0
goblin_mail_owner = None


def release_goblin_mail_target():
    global goblin_mail_disengaged_at, goblin_mail_last_attack_at, goblin_mail_target_engaged, goblin_mail_target_index
    goblin_mail_target_index = None
    goblin_mail_target_engaged = False
    goblin_mail_last_attack_at = 0
    goblin_mail_disengaged_at = 0


def reset_goblin_mail_combat():
    global goblin_mail_rejected_target_index, goblin_mail_rejected_until
    release_goblin_mail_target()
    goblin_mail_rejected_target_index = None
    goblin_mail_rejected_until = 0


def has(snap, name):
    return ((snap.inv.get(name) if snap.inv.get(name) is not None else 0)) > 0


def qty(snap, name):
    return (snap.inv.get(name) if snap.inv.get(name) is not None else 0)


def combat_food_names():
    configured = quest_food.name.strip()
    return list(list({_k: _v for _k, _v in [[name.lower(), name] for name in [name for name in [configured, FALLBACK_FOOD] if bool(name)]]}.values()))


def live_combat_food_count():
    return sum([inventory.count(food) for food in combat_food_names()])


def live_item(name):
    _v1 = ([item for item in inventory.items() if item.name.lower() == name.lower()] or [None])[0]
    return (_v1 if _v1 is not None else None)


def in_goblin_mail_field(tile):
    return tile is not None and tile is not None and tile.level == GOBLIN_FARM.level and max(abs(tile.x - GOBLIN_FARM.x), abs(tile.z - GOBLIN_FARM.z)) <= 18


def in_al_kharid_funding_area(tile):
    return tile is not None and tile.level == 0 and tile.x >= 3230 and tile.x <= 3330 and tile.z >= 3120 and tile.z <= 3227


def funding_man(anchor):
    return npcs.query().name('Man').action('Pickpocket').where(lambda npc: npc.tile().distance_to(anchor) <= FUNDING_MAN_LEASH).nearest()


def reach_funding_man(anchor, log):
    _w2 = yield from traversal.walk_resilient(anchor, radius=6, attempts=4, timeout_ms=180000, log=log)
    if not (_w2):
        return False
    _c3 = funding_man(anchor)
    if not _c3:
        _w4 = yield from execution.delay_until(lambda: funding_man(anchor) is not None, 15000)
        _c3 = (_w4)
    if _c3:
        return True
    log(f'no pickpocketable Man returned within {FUNDING_MAN_LEASH} tiles of ({anchor.x},{anchor.z})')
    return False


def clear_funding_dialog():
    pages = 0
    while pages < 12 and chat_dialog.can_continue():
        yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
        pages += 1


def pickpocket_funding_man(anchor, log):
    man = funding_man(anchor)
    if not man:
        _w5 = yield from reach_funding_man(anchor, log)
        if not (_w5):
            return False
        man = funding_man(anchor)
    if not man:
        return False
    coins_before = inventory.count('Coins')
    xp_before = skills.xp('thieving')
    hp_before = skills.effective('hitpoints')
    if not (man.interact('Pickpocket')):
        yield from execution.delay_ticks(2)
        return True
    resolved = yield from execution.delay_until(lambda: inventory.count('Coins') > coins_before or skills.xp('thieving') > xp_before or skills.effective('hitpoints') < hp_before or chat_dialog.can_continue(), 8000)
    if not resolved:
        log(f'pickpocketing Man at {man.tile()} produced no coin, XP, health, or dialogue change')
        yield from execution.delay_ticks(2)
        return True
    yield from clear_funding_dialog()
    if skills.effective('hitpoints') < hp_before:
        yield from execution.delay_ticks(8)
    return True


def buy_one_kebab(log):
    _w6 = yield from traversal.walk_resilient(KEBAB_SELLER, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w6):
        return False
    seller = npcs.query().name('Kebab seller').action('Talk-to').within(8).nearest()
    if not seller:
        log(f'no talkable Kebab seller near ({KEBAB_SELLER.x},{KEBAB_SELLER.z})')
        return False
    before = inventory.count(FALLBACK_FOOD)
    if not (seller.interact('Talk-to')):
        return False
    for step in range(40):
        if inventory.count(FALLBACK_FOOD) > before:
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            yes = ([option for option in options if option.strip().lower() == 'yes please.'] or [None])[0]
            _c7 = not yes
            if not _c7:
                _w8 = yield from chat_dialog.choose_option(yes)
                _c7 = not (_w8)
            if _c7:
                log(f"Kebab seller offered unexpected options: [{' | '.join(options)}]")
                return False
        yield from execution.delay_ticks(1)
    log('Kebab seller did not complete a purchase within 40 dialogue steps')
    return False


def eat_funding_kebab():
    kebab = live_item(FALLBACK_FOOD)
    if not kebab:
        return False
    before = inventory.count(FALLBACK_FOOD)
    if not (kebab.interact('Eat')):
        return False
    _result9 = yield from execution.delay_until(lambda: inventory.count(FALLBACK_FOOD) < before, 5000)
    return _result9


def eat_carried_combat_food():
    def _fn10(candidate):
        name = candidate.name.lower()


        return name is not None and any([food.lower() == name for food in combat_food_names()]) and any([(action.lower() == 'eat' or action.lower() == 'drink') for action in candidate.actions()])

    def _fn11(candidate):
        name = candidate.name.lower()


        return name is not None and any([food.lower() == name for food in combat_food_names()]) and any([(action.lower() == 'eat' or action.lower() == 'drink') for action in candidate.actions()])
    item = ([_x for _x in inventory.items() if _fn11(_x)] or [None])[0]
    if not item:
        return False


    action = ([candidate for candidate in item.actions() if (candidate.lower() == 'eat' or candidate.lower() == 'drink')] or [None])[0]
    if not action:
        return False
    before = live_combat_food_count()
    if not (item.interact(action)):
        return False
    _result12 = yield from execution.delay_until(lambda: live_combat_food_count() < before, 5000)
    return _result12


def restore_funding_health(can_buy_kebabs, log):
    while skills.effective('hitpoints') < SAFE_PICKPOCKET_HP:
        _w13 = yield from eat_carried_combat_food()
        if _w13:
            continue
        if can_buy_kebabs and inventory.count('Coins') > 0:
            _w15 = yield from buy_one_kebab(log)
            _c14 = not (_w15)
            if not _c14:
                _w16 = yield from eat_funding_kebab()
                _c14 = not (_w16)
            if _c14:
                return False
            continue
        log(f'waiting up to {FUNDING_REGEN_WAIT_MS / 1000}s for {SAFE_PICKPOCKET_HP} Hitpoints before another Man pickpocket')
        _w17 = yield from execution.delay_until(lambda: skills.effective('hitpoints') >= SAFE_PICKPOCKET_HP, FUNDING_REGEN_WAIT_MS)
        if not (_w17):
            log(f'still below {SAFE_PICKPOCKET_HP} Hitpoints with no usable food or Kebab funds — pausing funding')
            return False
    return True


def farm_funding_coins(anchor, target, can_buy_kebabs, log):
    _w18 = yield from reach_funding_man(anchor, log)
    if not (_w18):
        return False
    reported_hundreds = (inventory.count('Coins') // 100)
    last_evidence_at = _core.step_time()
    while inventory.count('Coins') < target:
        coins_before = inventory.count('Coins')
        xp_before = skills.xp('thieving')
        hp_before = skills.effective('hitpoints')
        _w20 = yield from restore_funding_health(can_buy_kebabs, log)
        _c19 = not (_w20)
        if not _c19:
            _w21 = yield from pickpocket_funding_man(anchor, log)
            _c19 = not (_w21)
        if _c19:
            return False
        if inventory.count('Coins') != coins_before or skills.xp('thieving') != xp_before or skills.effective('hitpoints') != hp_before:
            last_evidence_at = _core.step_time()
        elif _core.step_time() - last_evidence_at >= FUNDING_STALL_MS:
            log(f'no cash, Thieving XP, or Hitpoints change for {FUNDING_STALL_MS / 1000}s at the verified Man')
            return False
        hundreds = (inventory.count('Coins') // 100)
        if hundreds > reported_hundreds:
            reported_hundreds = hundreds
            log(f"Goblin Diplomacy funding: {inventory.count('Coins')}/{target} gp")
    return True


def earn_goblin_diplomacy_coins(log):
    if inventory.count('Coins') >= GOBLIN_DIPLOMACY_FUNDING_TARGET:
        return True
    if not in_al_kharid_funding_area(game.tile()):
        if inventory.count('Coins') < AL_KHARID_ENTRY_CASH:
            log(f'earning {AL_KHARID_ENTRY_CASH} gp for the Al Kharid toll and a food reserve')
            _w22 = yield from farm_funding_coins(VARROCK_FUNDING_MAN, AL_KHARID_ENTRY_CASH, False, log)
            if not (_w22):
                return False
        _w23 = yield from traversal.walk_resilient(AL_KHARID_FUNDING_MAN, radius=6, attempts=4, timeout_ms=240000, log=log)
        if not (_w23):
            return False
        if not in_al_kharid_funding_area(game.tile()):
            log('did not cross the Al Kharid toll gate into the verified Man/Kebab area')
            return False
    log(f'pickpocketing the Al Kharid Man to {GOBLIN_DIPLOMACY_FUNDING_TARGET} gp, buying exact Kebabs when hurt')
    _result24 = yield from farm_funding_coins(AL_KHARID_FUNDING_MAN, GOBLIN_DIPLOMACY_FUNDING_TARGET, True, log)
    return _result24


def food_acquisition_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    mail = ['goblin mail', 'orange goblin mail', 'blue goblin mail']
    with_food = ['coins'] + list(mail) + list([name.lower() for name in combat_food_names()])
    has_spillover = any([not (name.lower() in with_food) for name in list(list(snap.inv.keys()))])
    return Record({
        'kind': 'deposit',
        'keep': (with_food if has_spillover else ['coins'] + list(mail)),
        'bank': DRAYNOR_BANK,
        'exact_keep': True,
    })


# Why: the coins buy Aggie's dyes, so they stay a requirement; the food never was one, and a free quest fought at low level against goblins pays for it in slots the mail needs.
def goblin_mail_gather_step(snap, need=1):
    held_coins = qty(snap, 'coins')
    if not in_goblin_mail_field(snap.tile):
        reset_goblin_mail_combat()
    make_mail_space = food_acquisition_space(snap, max(1, need) + ((0 if held_coins > 0 else 1)))
    if make_mail_space:
        return make_mail_space
    if held_coins >= GOBLIN_DIPLOMACY_QUEST_COIN_RESERVE:
        return Record({'kind': 'custom', 'name': 'farm goblin mail', 'run': farm_goblin_mail})
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': DRAYNOR_BANK})
    if held_coins < GOBLIN_DIPLOMACY_COIN_TARGET and snap.bank_coins > 0:
        return Record({
            'kind': 'withdraw',
            'items': [{'name': 'Coins', 'qty': min(GOBLIN_DIPLOMACY_COIN_TARGET - held_coins, snap.bank_coins)}],
            'bank': DRAYNOR_BANK,
        })
    return Record({'kind': 'custom', 'name': f'earn {GOBLIN_DIPLOMACY_COIN_TARGET} gp', 'run': earn_goblin_diplomacy_coins})


def farm_goblin_mail(log):
    # A disengage grace period or a kill without a mail drop is still part of the same gathering attempt.
    # Returning every tick let the quest watchdog park it before the five-second combat grace expired.
    before = inventory.count('Goblin mail')
    deadline = _core.step_time() + 90000
    while _core.step_time() < deadline:
        if execution.event_signal.pending():
            return False
        if inventory.count('Goblin mail') > before:
            return True
        yield from _farm_goblin_mail_tick(log)
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return inventory.count('Goblin mail') > before


def _farm_goblin_mail_tick(log):
    global goblin_mail_disengaged_at, goblin_mail_last_attack_at, goblin_mail_owner, goblin_mail_target_engaged, goblin_mail_target_index
    owner = game.my_name()
    if goblin_mail_owner != owner or not in_goblin_mail_field(game.tile()):
        reset_goblin_mail_combat()
        goblin_mail_owner = owner
    drop = ground_items.query().name('Goblin mail').within(15).nearest()
    if drop:
        reset_goblin_mail_combat()
        before = inventory.count('Goblin mail')
        if not (drop.interact('Take')):
            log(f'could not take goblin mail at {drop.tile()} (actions {drop.actions()})')
            yield from execution.delay_ticks(2)
            return False
        _result25 = yield from execution.delay_until(lambda: inventory.count('Goblin mail') > before, 6000)
        return _result25

    def reject_goblin(goblin):
        global goblin_mail_rejected_target_index, goblin_mail_rejected_until
        goblin_mail_rejected_target_index = goblin.index
        goblin_mail_rejected_until = _core.step_time() + GOBLIN_REJECT_MS
        release_goblin_mail_target()

    def tracked_goblin():
        if goblin_mail_target_index is None:
            return None
        for npc in npcs.all():
            if npc.index != goblin_mail_target_index or npc.name != 'Goblin':
                continue
            if npc.distance() > 15 or npc.tile().distance_to(GOBLIN_FARM) > 18:
                continue
            for action in npc.actions():
                if action.lower() == 'attack':
                    return npc
        return None

    had_engaged_target = goblin_mail_target_index is not None and goblin_mail_target_engaged
    goblin = tracked_goblin()
    if not goblin and had_engaged_target:
        yield from sustain.run()
        yield from execution.delay_ticks(2)
        release_goblin_mail_target()
        return False
    attacker = npcs.query().name('Goblin').action('Attack').within(15).where(lambda npc: npc.targets_me() and npc.tile().distance_to(GOBLIN_FARM) <= 18).nearest()
    if attacker and (attacker.index != goblin_mail_target_index or goblin is None):
        goblin_mail_target_index = attacker.index
        goblin_mail_target_engaged = False
        goblin_mail_last_attack_at = 0
        goblin_mail_disengaged_at = 0
        goblin = attacker
        log(f'Goblin {attacker.index} attacked first — switching the lock to it')
    if goblin and (not goblin.valid() or (goblin.health == 0 and goblin.max_health > 0)):
        yield from sustain.run()
        yield from execution.delay_ticks(2)
        release_goblin_mail_target()
        return False
    if goblin and (goblin.targets_another_player() or (goblin.in_combat and not goblin_mail_target_engaged and not goblin.targets_me() and not game.in_combat())):
        log(f'Goblin {goblin.index} belongs to another player — releasing it')
        reject_goblin(goblin)
        goblin = None
    if goblin and goblin_mail_target_engaged and not game.in_combat() and not goblin.targets_me():
        if goblin_mail_disengaged_at == 0:
            goblin_mail_disengaged_at = _core.step_time()
        if _core.step_time() - goblin_mail_disengaged_at < GOBLIN_DISENGAGE_GRACE_MS:
            yield from sustain.run()
            yield from execution.delay_ticks(1)
            return False
        log(f'combat with live Goblin {goblin.index} made no progress for {GOBLIN_DISENGAGE_GRACE_MS / 1000}s — choosing another target')
        reject_goblin(goblin)
        goblin = None
    if not goblin:
        rejected_index = (goblin_mail_rejected_target_index if _core.step_time() < goblin_mail_rejected_until else None)
        goblin = npcs.query().name('Goblin').action('Attack').within(15).where(lambda n: not n.in_combat and not n.targets_another_player() and n.index != rejected_index and n.tile().distance_to(GOBLIN_FARM) <= 18 and reachability.can_reach(n.tile(), adjacent_ok=True)).nearest()
        if goblin:
            goblin_mail_target_index = goblin.index
            goblin_mail_target_engaged = False
            goblin_mail_last_attack_at = 0
            goblin_mail_disengaged_at = 0
            log(f'holding Goblin {goblin.index} until it dies')
    if goblin:
        if game.in_combat() or goblin.targets_me():
            goblin_mail_target_engaged = True
            goblin_mail_disengaged_at = 0
            yield from sustain.run()
            yield from execution.delay_ticks(1)
            return False
        if _core.step_time() - goblin_mail_last_attack_at < GOBLIN_REATTACK_MS:
            yield from sustain.run()
            yield from execution.delay_ticks(2)
            return False
        if not (goblin.interact('Attack')):
            log(f'Attack on Goblin {goblin.index} was rejected — choosing another target')
            reject_goblin(goblin)
            yield from execution.delay_ticks(2)
            return False
        goblin_mail_last_attack_at = _core.step_time()
        attack_deadline = _core.step_time() + 8000
        attack_observed = False
        while _core.step_time() < attack_deadline:
            yield from sustain.run()
            live = tracked_goblin()
            if live is None or game.in_combat() or live.targets_me() or live.targets_another_player():
                attack_observed = True
                break
            yield from execution.delay_ticks(1)
        if not attack_observed:
            log(f'Attack on Goblin {goblin.index} produced no combat within 8s — choosing another target')
            reject_goblin(goblin)
            return False
        live = tracked_goblin()
        if live is not None and live.targets_another_player():
            log(f'Goblin {live.index} engaged another player after our attack — releasing it')
            reject_goblin(live)
            return False
        if live is None:
            release_goblin_mail_target()
            return False
        goblin_mail_target_engaged = goblin_mail_target_engaged or game.in_combat() or live.targets_me()
        if goblin_mail_target_engaged:
            goblin_mail_disengaged_at = 0
        return False
    release_goblin_mail_target()
    yield from traversal.walk_resilient(GOBLIN_FARM, radius=4, attempts=2, timeout_ms=90000, log=log)
    return False


def make_blue_dye(log):
    if inventory.contains('Blue dye'):
        return True
    if inventory.count('Woad leaf') < 2:
        if inventory.count('Coins') < 20:
            log('need ~20 coins for woad leaves')
            return False
        _w26 = yield from goto_npc(WYSON, [], log)
        if not (_w26):
            return False
        yield from talk_through(WYSON.npc, WYSON.prefer, log)
        return False
    if inventory.count('Coins') < 5:
        log('need ~5 coins for blue dye')
        return False
    _w27 = yield from goto_npc(AGGIE_BLUE, [], log)
    if not (_w27):
        return False
    yield from talk_through(AGGIE_BLUE.npc, AGGIE_BLUE.prefer, log)
    _result28 = yield from execution.delay_until(lambda: inventory.contains('Blue dye'), 8000)
    return _result28


def make_orange_dye(log):
    if inventory.contains('Orange dye'):
        return True
    if not inventory.contains('Red dye'):
        if inventory.count('Redberries') < 3:
            before = inventory.count('Redberries')
            _result29 = yield from execute_step(Record({'kind': 'buy', 'item': 'Redberries', 'qty': 3 - before, 'shop': PORT_SARIM_SHOP, 'est_gp': 60}), [], log)
            # Wydin stocks one berry. An empty shelf must wait for restocking before retrying the quest step.
            if inventory.count('Redberries') == before:
                yield from execution.delay_ticks(20)
            return _result29
        if inventory.count('Coins') < 5:
            log('need ~5 coins for red dye')
            return False
        _w30 = yield from goto_npc(AGGIE_RED, [], log)
        if not (_w30):
            return False
        yield from talk_through(AGGIE_RED.npc, AGGIE_RED.prefer, log)
        return False
    if not inventory.contains('Yellow dye'):
        if inventory.count('Onion') < 2:
            _result31 = yield from execute_step(Record({'kind': 'pick_loc', 'loc': 'Onion', 'op': 'Pick', 'item': 'Onion', 'anchor': ONION_PATCH}), [], log)
            return _result31
        if inventory.count('Coins') < 5:
            log('need ~5 coins for yellow dye')
            return False
        _w32 = yield from goto_npc(AGGIE_YELLOW, [], log)
        if not (_w32):
            return False
        yield from talk_through(AGGIE_YELLOW.npc, AGGIE_YELLOW.prefer, log)
        return False
    _result33 = yield from execute_step(Record({
        'kind': 'use_on',
        'item': 'Red dye',
        'target_kind': 'item',
        'target': 'Yellow dye',
        'anchor': AGGIE_ANCHOR,
        'product': 'Orange dye',
    }), [], log)
    return _result33


def decide(snap):
    global goblin_mail_owner
    if snap.journal == 'complete':
        reset_goblin_mail_combat()
        goblin_mail_owner = None
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': BARTENDER})
    plain_mail = qty(snap, 'goblin mail')
    orange_mail = has(snap, 'orange goblin mail')
    blue_mail = has(snap, 'blue goblin mail')
    if has(snap, 'orange dye') and not orange_mail and plain_mail >= 1:
        return Record({
            'kind': 'use_on',
            'item': 'Orange dye',
            'target_kind': 'item',
            'target': 'Goblin mail',
            'anchor': GENERAL.anchor,
            'product': 'Orange goblin mail',
        })
    if has(snap, 'blue dye') and not blue_mail and plain_mail >= 2:
        return Record({
            'kind': 'use_on',
            'item': 'Blue dye',
            'target_kind': 'item',
            'target': 'Goblin mail',
            'anchor': GENERAL.anchor,
            'product': 'Blue goblin mail',
        })
    return Record({'kind': 'talk', 'stop': GENERAL})


def _fn34():
    return ['goblin mail', 'dye', 'woad', 'redberries', 'onion', 'coins'] + list([name.lower() for name in combat_food_names()])


goblindiplomacy = QuestModule(**{
    'record': ([r for r in QUESTS if r.id == 'gobdip'] or [None])[0],
    'bank': DRAYNOR_BANK,
    'sustain': Record({'foods': [FALLBACK_FOOD], 'eat_below_hp': 0.6}),
    'tools': _fn34,
    'grind': ['Goblin'],
    'gather': Record({
    'goblin mail': goblin_mail_gather_step,
    'orange dye': lambda snap, need: (Record({'kind': 'custom', 'name': 'make orange dye', 'run': make_orange_dye})),
    'blue dye': lambda snap, need: (Record({'kind': 'custom', 'name': 'make blue dye', 'run': make_blue_dye})),
}),
    'decide': decide,
})

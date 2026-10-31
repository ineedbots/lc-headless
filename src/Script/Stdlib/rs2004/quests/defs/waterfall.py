"""Ported from rs2b0t's src/bot/api/ai/quests/defs/waterfall.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs._items import ITEM_DB
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.exec.primitives import NpcStop, talk_through, walk_with_hops
from rs2004.quests.exec.steps import execute_step
from rs2004.quests.food import quest_food
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests
from rs2004.traversal import traversal
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.data import quest_record

__all__ = ['WATERFALL_STAGE', 'waterfall_area', 'waterfall_dungeon_entry_readiness', 'parse_waterfall_journal', 'read_waterfall_stage', 'waterfall_funding_target', 'source_food', 'decide', 'waterfall']

WATERFALL_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 1,
    'SPOKEN_TO_HUDON': 2,
    'READ_BOOK': 3,
    'ENTERED_TOMB': 4,
    'ENTERED_WATERFALL': 5,
    'ENTERED_PUZZLE': 6,
    'RAISED_FLOOR': 8,
    'COMPLETE': 10,
})
ITEM = Record({
    'BOOK': Record({'id': 292, 'name': 'Book on baxtorian'}),
    'GOLRIE_KEY': Record({'id': 293, 'name': 'A key'}),
    'PEBBLE': Record({'id': 294, 'name': "Glarial's pebble"}),
    'AMULET': Record({'id': 295, 'name': "Glarial's amulet"}),
    'FULL_URN': Record({'id': 296, 'name': "Glarial's urn"}),
    'EMPTY_URN': Record({'id': 297, 'name': "Glarial's urn"}),
    'BAXTORIAN_KEY': Record({'id': 298, 'name': 'A key'}),
    'WATER_RUNE': Record({'id': 555, 'name': 'Water rune'}),
    'AIR_RUNE': Record({'id': 556, 'name': 'Air rune'}),
    'EARTH_RUNE': Record({'id': 557, 'name': 'Earth rune'}),
    'COINS': Record({'id': 995, 'name': 'Coins'}),
    'KEBAB': Record({'id': 1971, 'name': 'Kebab'}),
    'ROPE': Record({'id': 954, 'name': 'Rope'}),
})
RUNES = [ITEM.AIR_RUNE, ITEM.EARTH_RUNE, ITEM.WATER_RUNE]
FOOD_TARGET = 8
# Why: refilling on any shortfall walked back to Ardougne for 1 fish mid-route.
FOOD_LOW = 3
RUNE_TARGET = 6
RUNE_UNIT_BUDGET = 24
BETTY_RETURN_FARE = 60
EASTERN_SUPPLY_FARE = 60
CASH_FLOAT = 500
# Why: the entry, crate, south-door route is 80 tiles (nav cost 89 with 3 weighted door edges), and at the pack's ~9 kg 40% covers about 105 running tiles through the fire-giant lane.
DUNGEON_RUN_ENERGY = 40
LOC = Record({
    'RAFT': 1987,
    'BOOKCASE': 1989,
    'GOLRIE_CRATE': 1990,
    'GOLRIE_GATE': 1991,
    'TOMBSTONE': 1992,
    'COFFIN': 1993,
    'CHEST_CLOSED': 1994,
    'CHEST_OPEN': 1995,
    'CROSSING_ROCK': 1996,
    'BAXTORIAN_CRATE': 1999,
    'ENTRY_DOOR': 2000,
    'KEYED_DOOR': 2002,
    'PILLAR': 2004,
    'GLARIAL_STATUE': 2006,
    'LEDGE_DOOR': 2010,
    'CHALICE': 2014,
    'DEAD_TREE': 2020,
    'BARREL': 2022,
})
ARDOUGNE_BANK = Tile(2616, 3332, 0)
AEMAD_SHOP = Record({'npc': 'Aemad', 'anchor': Tile(2614, 3293, 0)})
BETTY_SHOP = Record({'npc': 'Betty', 'anchor': Tile(3012, 3259, 0)})
VARROCK_MAN = Tile(3240, 3405, 0)
AL_KHARID_MAN = Tile(3279, 3188, 0)
KEBAB_SELLER = Tile(3272, 3182, 0)
AL_KHARID_TOLL = 10
AL_KHARID_ENTRY_CASH = AL_KHARID_TOLL + 3
SAFE_PICKPOCKET_HP = 3
FUNDING_MAN_LEASH = 24
FUNDING_STALL_MS = 120000
ALMERA = NpcStop('Almera', Tile(2522, 3498, 0), 6, ['How can I help?'])
WATERFALL_HOPS = [
    Record({'stand': Tile(2533, 3156, 0), 'loc_name': 'Ladder', 'op': 'Climb-down', 'arrive': Tile(2533, 9556, 0)}),
    Record({'stand': Tile(2533, 9556, 0), 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': Tile(2533, 3156, 0)}),
]
RAFT_STAND = Tile(2509, 3493, 0)
HUDON_STAND = Tile(2511, 3481, 0)
MOUND_SWIM_STAND = Tile(2512, 3476, 0)
BOOKCASE_STAND = Tile(2519, 3426, 1)
GOLRIE_CRATE_STAND = Tile(2548, 9565, 0)
GOLRIE_GATE_STAND = Tile(2515, 9574, 0)
GOLRIE_STAND = Tile(2515, 9581, 0)
TOMBSTONE_STAND = Tile(2558, 3444, 0)
CHEST_STAND = Tile(2530, 9845, 0)
COFFIN_STAND = Tile(2542, 9810, 0)
# Why: directional ladder 1757 only takes an approach from its east tile, and an exact stand keeps the hostile approach inside Traversal's sustain loop.
TOMB_LADDER_STAND = Tile(2557, 9844, 0)
ROCK_STAND = Tile(2512, 3477, 0)
ENTRY_DOOR_STAND = Tile(2575, 9861, 0)
# Why: the crate's south interaction tile (2589,9887) touches the level-45 giant skeleton at (2589,9886); the west tile can still search and sits outside its 1-tile aggro range.
BAXTORIAN_CRATE_STAND = Tile(2588, 9888, 0)
SOUTH_DOOR_STAND = Tile(2568, 9892, 0)
SOUTH_DOOR_NORTH_STAND = Tile(2568, 9894, 0)
PUZZLE_DOOR_STAND = Tile(2566, 9900, 0)
PUZZLE_DOOR_NORTH_STAND = Tile(2566, 9902, 0)
PILLAR_STAND = Tile(2563, 9911, 0)
STATUE_STAND = Tile(2565, 9915, 0)
RAISED_ROOM_STAND = Tile(2603, 9906, 0)


def waterfall_area(tile):
    if not tile:
        return 'unknown'
    x = tile.x
    z = tile.z
    if x >= 2598 and x <= 2620 and z >= 9905 and z <= 9930:
        return 'raisedRoom'
    if x >= 2558 and x <= 2572 and z >= 9907 and z <= 9920:
        return 'puzzleRoom'
    if x >= 2490 and x <= 2630 and z >= 9850 and z <= 9950:
        return 'waterfallDungeon'
    if x >= 2500 and x <= 2570 and z >= 9780 and z < 9850:
        return 'glarialTomb'
    if x >= 2480 and x <= 2570 and z >= 9500 and z <= 9650:
        return 'tgvDungeon'
    if x >= 2505 and x <= 2518 and z >= 3474 and z <= 3486:
        return 'hudonMound'
    if x >= 2505 and x <= 2518 and z >= 3466 and z <= 3473:
        return 'fallsTreeBank'
    if x >= 2505 and x <= 2518 and z >= 3460 and z <= 3465:
        return 'fallsLedge'
    return 'mainland'


def waterfall_dungeon_entry_readiness(energy, current_hp, base_hp, run_enabled):
    if energy < DUNGEON_RUN_ENERGY:
        return 'waitForEnergy'
    if current_hp < base_hp:
        return 'heal'
    if not run_enabled:
        return 'enableRun'
    return 'ready'


def parse_waterfall_journal(lines):
    text = normalize_journal(lines)
    # Later entries keep the earlier history, so match newest first.
    if ('quest complete!' in text):
        return WATERFALL_STAGE.COMPLETE
    if ('worked out how to raise the floor' in text) or ('now i just need to retrieve the treasure' in text):
        return WATERFALL_STAGE.RAISED_FLOOR
    if ('it is floating out of reach' in text) or ("i'll need to work out how to get to it" in text):
        return WATERFALL_STAGE.ENTERED_PUZZLE
    if ('used it to enter baxtorian falls' in text):
        return WATERFALL_STAGE.ENTERED_WATERFALL
    if ('managed to enter the tomb of glarial' in text):
        return WATERFALL_STAGE.ENTERED_TOMB
    if ("the book also mentions glarial's tomb" in text):
        return WATERFALL_STAGE.READ_BOOK
    if ('i found hudon a short raft ride down the river' in text):
        return WATERFALL_STAGE.SPOKEN_TO_HUDON
    if ('i spoke to almera in a house close to the baxtorian waterfall' in text):
        return WATERFALL_STAGE.STARTED
    if ('i can start this quest' in text):
        return WATERFALL_STAGE.NOT_STARTED
    return None


def read_waterfall_stage():
    status = quests.status('Waterfall Quest')
    if status == 'complete':
        return WATERFALL_STAGE.COMPLETE
    if status == 'not_started':
        return WATERFALL_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    # Varp 65 never reaches a revision-274 client, so the rendered journal is the stage oracle.
    _w1 = yield from quests.journal('Waterfall Quest')
    stage = parse_waterfall_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


def count_id(map, id):
    _v2 = (map.get(id) if map is not None else None)
    return (_v2 if _v2 is not None else 0)


def held_count(snap, item):
    return (count_id(snap.inv_ids, item.id) if snap.inv_ids else ((snap.inv.get(item.name.lower()) if snap.inv.get(item.name.lower()) is not None else 0)))


def held(snap, item):
    return held_count(snap, item) > 0


def worn(snap, item):
    return ((item.id in snap.worn_ids) if snap.worn_ids else (item.name.lower() in snap.worn))


def banked(snap, item):
    return (count_id(snap.bank_ids, item.id) if snap.bank_ids else (((snap.bank.get(item.name.lower()) if snap.bank is not None else None) if (snap.bank.get(item.name.lower()) if snap.bank is not None else None) is not None else 0)))


def owned(snap, item):
    return held_count(snap, item) + banked(snap, item) + ((1 if worn(snap, item) else 0))


def live_item(item):
    _v3 = ([candidate for candidate in inventory.items() if candidate.id == item.id] or [None])[0]
    return (_v3 if _v3 is not None else None)


def live_count(item):
    return sum([candidate.count for candidate in [candidate for candidate in inventory.items() if candidate.id == item.id]])


def live_worn(item):
    return any([candidate.id == item.id for candidate in equipment.items()])


def withdraw(items, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    return Record({'kind': 'withdraw', 'items': items, 'bank': bank})


def withdraw_exact(item, qty, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    return withdraw([{'name': item.name, 'id': item.id, 'qty': qty}], bank)


def scan_bank(bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    return Record({'kind': 'scan_bank', 'bank': bank})


def coins_held(snap):
    return held_count(snap, ITEM.COINS)


def remaining_waterfall_cash(snap):
    # Why: food comes from the bank, so the purse only covers the rope, runes and fares.
    rope = (0 if owned(snap, ITEM.ROPE) > 0 else 20)
    runes = sum([max(0, RUNE_TARGET - owned(snap, rune)) * RUNE_UNIT_BUDGET for rune in RUNES])
    # Why: stage 0 can't buy runes yet, and a restart beside Betty still needs the later fare since the quest leaves and comes back west.
    rune_fare = (BETTY_RETURN_FARE if runes > 0 else 0)
    return CASH_FLOAT + rope + runes + rune_fare


def live_coins():
    return live_count(ITEM.COINS)


def in_al_kharid_funding_area(tile):
    return tile is not None and tile.level == 0 and tile.x >= 3230 and tile.x <= 3330 and tile.z >= 3120 and tile.z <= 3227


def funding_man(anchor):
    return npcs.query().name('Man').action('Pickpocket').where(lambda npc: npc.tile().distance_to(anchor) <= FUNDING_MAN_LEASH).nearest()


def reach_funding_man(anchor, log):
    _w4 = yield from traversal.walk_resilient(anchor, radius=6, attempts=4, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    if funding_man(anchor):
        return True
    _w5 = yield from execution.delay_until(lambda: funding_man(anchor) is not None, 15000)
    if _w5:
        return True
    log(f'no pickpocketable Man returned within {FUNDING_MAN_LEASH} tiles of ({anchor.x},{anchor.z})')
    return False


def clear_funding_continues():
    for pages in range(12):
        if not (chat_dialog.can_continue()):
            break
        yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)


def pickpocket_funding_man(anchor, log):
    man = funding_man(anchor)
    if not man:
        _w6 = yield from reach_funding_man(anchor, log)
        if not (_w6):
            return False
        man = funding_man(anchor)
    if not man:
        return False
    coins_before = live_coins()
    xp_before = skills.xp('thieving')
    hp_before = skills.effective('hitpoints')
    if not (man.interact('Pickpocket')):
        return False
    resolved = yield from execution.delay_until(lambda: live_coins() > coins_before or skills.xp('thieving') > xp_before or skills.effective('hitpoints') < hp_before or chat_dialog.can_continue(), 8000)
    if not resolved:
        log(f'pickpocketing Man at {man.tile()} produced no coin, XP, health, or dialogue change')
        # A walking target can step away after the packet is accepted; re-query the live NPC.
        yield from execution.delay_ticks(2)
        return True
    yield from clear_funding_continues()
    if skills.effective('hitpoints') < hp_before:
        # A failed level-1 Man pickpocket stuns for 8 ticks.
        yield from execution.delay_ticks(8)
    return True


def buy_funding_kebab(log):
    _w7 = yield from traversal.walk_resilient(KEBAB_SELLER, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w7):
        return False
    seller = npcs.query().name('Kebab seller').action('Talk-to').within(8).nearest()
    if not seller:
        log(f'no talkable Kebab seller near ({KEBAB_SELLER.x},{KEBAB_SELLER.z})')
        return False
    kebabs_before = live_count(ITEM.KEBAB)
    if not (seller.interact('Talk-to')):
        return False
    for step in range(40):
        if live_count(ITEM.KEBAB) > kebabs_before:
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            choice = ([option for option in options if option.strip().lower() == 'yes please.'] or [None])[0]
            if not choice:
                log(f"Kebab seller offered unexpected options: [{' | '.join(options)}]")
                return False
            _w8 = yield from chat_dialog.choose_option(choice)
            if not (_w8):
                return False
            yield from execution.delay_ticks(1)
            continue
        yield from execution.delay_ticks(1)
    log('Kebab seller accepted no exact purchase within 40 dialogue steps')
    return False


def eat_funding_kebab():
    kebab = live_item(ITEM.KEBAB)
    if not kebab:
        return False
    before = live_count(ITEM.KEBAB)
    if not (kebab.interact('Eat')):
        return False
    _result9 = yield from execution.delay_until(lambda: live_count(ITEM.KEBAB) < before, 5000)
    return _result9


def restore_funding_health(kebabs_available, log):
    while skills.effective('hitpoints') < SAFE_PICKPOCKET_HP:
        if kebabs_available and live_coins() > 0:
            _w11 = yield from buy_funding_kebab(log)
            _c10 = not (_w11)
            if not _c10:
                _w12 = yield from eat_funding_kebab()
                _c10 = not (_w12)
            if _c10:
                return False
            continue
        log(f'waiting for {SAFE_PICKPOCKET_HP} Hitpoints before another Man pickpocket')
        yield from execution.delay_until(lambda: skills.effective('hitpoints') >= SAFE_PICKPOCKET_HP, 0)
    return True


def farm_waterfall_coins(anchor, target, kebabs_available, log):
    _w13 = yield from reach_funding_man(anchor, log)
    if not (_w13):
        return False
    reported_hundreds = (live_coins() // 100)
    last_evidence_at = _core.step_time()
    while live_coins() < target:
        coins_before = live_coins()
        xp_before = skills.xp('thieving')
        hp_before = skills.effective('hitpoints')
        _w14 = yield from restore_funding_health(kebabs_available, log)
        if not (_w14):
            return False
        _w15 = yield from pickpocket_funding_man(anchor, log)
        if not (_w15):
            return False
        if live_coins() != coins_before or skills.xp('thieving') != xp_before or skills.effective('hitpoints') != hp_before:
            last_evidence_at = _core.step_time()
        elif _core.step_time() - last_evidence_at >= FUNDING_STALL_MS:
            log(f'no cash, Thieving XP, or Hitpoints change for {FUNDING_STALL_MS // 1000}s at the verified Man')
            return False
        hundreds = (live_coins() // 100)
        if hundreds > reported_hundreds:
            reported_hundreds = hundreds
            log(f'Waterfall funding: {live_coins()}/{target} gp')
    return True


def waterfall_funding_target(minimum, return_bank):
    return_fare = AL_KHARID_TOLL + ((EASTERN_SUPPLY_FARE if return_bank.x < 3100 else 0))
    return minimum + return_fare


def fund_waterfall_coins(minimum, return_bank, log):
    if live_coins() >= minimum and not in_al_kharid_funding_area(game.tile()):
        return True
    if not in_al_kharid_funding_area(game.tile()):
        if live_coins() < AL_KHARID_ENTRY_CASH:
            log(f'earning the {AL_KHARID_TOLL} gp Al Kharid toll and a food reserve from a Varrock Man')
            _w16 = yield from farm_waterfall_coins(VARROCK_MAN, AL_KHARID_ENTRY_CASH, False, log)
            if not (_w16):
                return False
        if live_coins() >= minimum:
            return True
        _w17 = yield from traversal.walk_resilient(AL_KHARID_MAN, radius=6, attempts=4, timeout_ms=240000, log=log)
        if not (_w17):
            return False
        if not in_al_kharid_funding_area(game.tile()):
            log('did not cross the Al Kharid toll gate into the verified Man/Kebab area')
            return False
    # Returning to Varrock only pays the gate; the western supply bank costs the 2 30-gp ship edges on the safe route.
    target = waterfall_funding_target(minimum, return_bank)
    log(f'pickpocketing the Al Kharid Man to {target} gp, buying exact Kebabs below {SAFE_PICKPOCKET_HP} HP')
    _w18 = yield from farm_waterfall_coins(AL_KHARID_MAN, target, True, log)
    if not (_w18):
        return False
    _w19 = yield from traversal.walk_resilient(return_bank, radius=3, attempts=4, timeout_ms=300000, log=log)
    if not (_w19):
        return False
    if live_coins() < minimum:
        log(f'returned from self-funding with {live_coins()} gp, below the required {minimum}')
        return False
    return True


def ensure_coins(snap, minimum=None, bank=None):
    if minimum is None:
        minimum = CASH_FLOAT
    if bank is None:
        bank = ARDOUGNE_BANK
    if coins_held(snap) >= minimum:
        return None
    available = banked(snap, ITEM.COINS)
    if available <= 0:
        return Record({
            'kind': 'custom',
            'name': f'earn {minimum} gp for Waterfall supplies',
            'run': lambda log: fund_waterfall_coins(minimum, bank, log),
        })
    return withdraw_exact(ITEM.COINS, min(max(minimum - coins_held(snap), 1), available), bank)


def source_rope(snap, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    if held(snap, ITEM.ROPE):
        return None
    if not snap.bank_known:
        return scan_bank(bank)
    if banked(snap, ITEM.ROPE) > 0:
        return withdraw_exact(ITEM.ROPE, 1, bank)
    coins = ensure_coins(snap, CASH_FLOAT, bank)
    return (coins if coins is not None else Record({'kind': 'buy', 'item': ITEM.ROPE.name, 'qty': 1, 'shop': AEMAD_SHOP, 'est_gp': 20}))


# Why: food is whatever the player chose, drawn from the bank; the old shop runs for 15 Bread and 10 Tea carried a level-3 account with an empty bank.
def food_item():
    """The configured food as an id and name, or null when it names nothing the item db knows."""
    name = (quest_food.name.strip() if quest_food.name is not None else None)
    if not name:
        return None
    record = ([item for item in ITEM_DB if item['name'].lower() == name.lower()] or [None])[0]
    return (Record({'id': record['id'], 'name': record['name']}) if record else None)


def with_food(ids):
    """Keep ids plus whatever the player eats, so a normalize pass never banks the food."""
    food = food_item()
    return (list(ids) + [food.id] if food else ids)


def source_food(snap, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    food = food_item()
    if not food:
        return Record({'kind': 'wait', 'reason': 'no food selected for the Waterfall dungeon'})
    held = held_count(snap, food)
    if held > FOOD_LOW:
        return None
    missing = FOOD_TARGET - held
    if not snap.bank_known:
        return scan_bank(bank)
    in_bank = banked(snap, food)
    if in_bank <= 0:
        return Record({'kind': 'wait', 'reason': f'no {food.name} in the bank for the Waterfall dungeon'})
    if snap.free_slots is not None and snap.free_slots < missing:
        return Record({'kind': 'wait', 'reason': f'need {missing} free slots for {food.name}'})
    return withdraw_exact(food, min(missing, in_bank), bank)


def near_betty(snap):
    tile = snap.tile
    return tile is not None and tile is not None and max(abs(tile.x - BETTY_SHOP.anchor.x), abs(tile.z - BETTY_SHOP.anchor.z)) <= 16


def source_puzzle_runes(snap):
    if not snap.bank_known:
        return scan_bank()
    # Empty every useful bank stack before Betty, or an earlier missing rune triggers a shop trip before a later free stack is seen.
    bank_withdrawals = []
    for rune in RUNES:
        missing = RUNE_TARGET - held_count(snap, rune)
        in_bank = banked(snap, rune)
        if missing > 0 and in_bank > 0:
            bank_withdrawals.append({'name': rune.name, 'id': rune.id, 'qty': min(missing, in_bank)})
    if len(bank_withdrawals) > 0:
        return withdraw(bank_withdrawals)
    missing_runes = [entry for entry in [(Record({'rune': rune, 'missing': max(0, RUNE_TARGET - held_count(snap, rune))})) for rune in RUNES] if entry.missing > 0]
    if len(missing_runes) == 0:
        return None
    # Why: Betty's price rises as stock sells and 24 gp per rune is the server's hard cap.
    # Why: the cash float plus both paid ship edges are reserved before departure, so later per-stack decisions never bounce back to the bank.
    purchase_budget = sum([entry.missing * RUNE_UNIT_BUDGET for entry in missing_runes])
    reserve = CASH_FLOAT + ((0 if near_betty(snap) else BETTY_RETURN_FARE))
    coins = ensure_coins(snap, reserve + purchase_budget)
    if coins:
        return coins
    _o20 = missing_runes[0]
    rune = _o20.rune
    missing = _o20.missing
    return Record({
        'kind': 'buy',
        'item': rune.name,
        'qty': missing,
        'shop': BETTY_SHOP,
        'est_gp': missing * RUNE_UNIT_BUDGET,
    })


def inventory_has_outside_ids(snap, keep_ids):
    if snap.inv_ids:
        return any([not (id in keep_ids) for id in list(list(snap.inv_ids.keys()))])
    keep_names = set([ITEM.get(key).name.lower() for key in ITEM.keys() if ITEM.get(key).id in keep_ids])
    return any([not (name in keep_names) for name in list(list(snap.inv.keys()))])


MAX_LOADOUT_COUNT = {_k: _v for _k, _v in [
    [ITEM.BOOK.id, 1],
    [ITEM.GOLRIE_KEY.id, 1],
    [ITEM.PEBBLE.id, 1],
    [ITEM.AMULET.id, 1],
    [ITEM.FULL_URN.id, 1],
    [ITEM.EMPTY_URN.id, 1],
    [ITEM.BAXTORIAN_KEY.id, 1],
    [ITEM.WATER_RUNE.id, RUNE_TARGET],
    [ITEM.AIR_RUNE.id, RUNE_TARGET],
    [ITEM.EARTH_RUNE.id, RUNE_TARGET],
    [ITEM.ROPE.id, 1],
]}


def max_loadout_count(id):
    food = food_item()
    return (FOOD_TARGET if food and id == food.id else MAX_LOADOUT_COUNT.get(id))


def inventory_has_excess_kept_ids(snap, keep_ids):
    if not snap.inv_ids:
        return False

    def excess(id, count):
        maximum = max_loadout_count(id)
        return (id in keep_ids) and maximum is not None and count > maximum

    return any([excess(id, count) for id, count in snap.inv_ids.items()])


def strip_and_deposit(keep_ids, log, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK

    def deposit(leave_open):
        return execute_step(Record({
            'kind': 'deposit',
            'keep': [],
            'keep_ids': keep_ids,
            'exact_keep': True,
            'bank': bank,
            'leave_open': leave_open,
        }), WATERFALL_HOPS, log)

    # Clear the pack first so every worn slot can unequip even with a full inventory.
    _w27 = yield from deposit(False)
    if not (_w27):
        return False
    for item in equipment.items():
        _c28 = item.name
        if _c28:
            _w29 = yield from equipment.unequip(item.name)
            _c28 = not (_w29)
        if _c28:
            return False
    # Leave the final view open so QuestEngine refreshes its name and id bank caches before the next decision.
    _result30 = yield from deposit(True)
    return _result30


def normalize_loadout(snap, keep_ids, name, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    has_excess = inventory_has_excess_kept_ids(snap, keep_ids)
    has_equipment = len(snap.worn) > 0 or (((len(snap.worn_ids) if snap.worn_ids is not None else None) if (len(snap.worn_ids) if snap.worn_ids is not None else None) is not None else 0)) > 0
    if not has_equipment and not inventory_has_outside_ids(snap, keep_ids) and not has_excess:
        return None
    # Why: the bank API keeps an exact id but not a partial quantity, so anything over its phase limit means banking the pack and letting the planner withdraw exact quantities next snapshot.
    # Why: equipment gets the same empty-pack treatment so every worn slot has room to unequip before the final deposit.
    normalized_keep_ids = ([] if has_excess or has_equipment else keep_ids)
    return Record({'kind': 'custom', 'name': name, 'run': lambda log: strip_and_deposit(normalized_keep_ids, log, bank)})


START_KEEP = [ITEM.COINS.id, ITEM.ROPE.id]
BOOK_TRAVEL_KEEP = list(START_KEEP) + [ITEM.BOOK.id]
TOMB_KEEP = [ITEM.COINS.id, ITEM.PEBBLE.id, ITEM.AMULET.id, ITEM.FULL_URN.id, ITEM.BAXTORIAN_KEY.id]
TOMB_TRAVEL_KEEP = [ITEM.COINS.id, ITEM.PEBBLE.id]
DUNGEON_KEEP = [
    ITEM.COINS.id,
    ITEM.ROPE.id,
    ITEM.AMULET.id,
    ITEM.FULL_URN.id,
    ITEM.BAXTORIAN_KEY.id,
    ITEM.AIR_RUNE.id,
    ITEM.EARTH_RUNE.id,
    ITEM.WATER_RUNE.id,
]
FINAL_KEEP = [ITEM.COINS.id, ITEM.ROPE.id, ITEM.AMULET.id, ITEM.FULL_URN.id, ITEM.BAXTORIAN_KEY.id]


def board_raft(log, drive_hudon=False):
    _w31 = yield from traversal.walk_resilient(RAFT_STAND, radius=2, attempts=3, timeout_ms=120000, log=log)
    if not (_w31):
        return False
    raft = locs.query().where(lambda loc: loc.id == LOC.RAFT).action('Board').within(8).nearest()
    if not raft or not (raft.interact('Board')):
        return False
    if drive_hudon:
        yield from execution.delay_until(lambda: chat_dialog.can_continue(), 12000)
        # Why: stage 2 is set partway through the forced Hudon conversation, so finish it here or a gap between pages lets the engine walk off while the script is still suspended at stage 1.
        for page in range(14):
            if not (chat_dialog.can_continue()):
                break
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
    _result32 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'hudonMound', 12000)
    return _result32


def stage_one_leg(log):
    if waterfall_area(game.tile()) != 'hudonMound':
        _result33 = yield from board_raft(log, True)
        return _result33
    _w34 = yield from traversal.walk_resilient(HUDON_STAND, radius=2, attempts=2, timeout_ms=30000, log=log)
    if not (_w34):
        return False
    _result35 = yield from talk_through('Hudon', [], log)
    return _result35


def leave_hudon_mound(log):
    _w36 = yield from traversal.walk_resilient(MOUND_SWIM_STAND, radius=1, attempts=3, timeout_ms=30000, log=log)
    if not (_w36):
        return False
    rock = locs.query().where(lambda loc: loc.id == LOC.CROSSING_ROCK).action('Swim to').within(10).nearest()
    if not rock or not (rock.interact('Swim to')):
        return False
    _result37 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'mainland', 20000)
    return _result37


def read_book():
    book = live_item(ITEM.BOOK)
    if not book or not (book.interact('Read')):
        return False
    yield from execution.delay_until(lambda: reader.modals().main != -1, 5000)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return True


def book_leg(log):
    if live_count(ITEM.BOOK) > 0:
        _result38 = yield from read_book()
        return _result38
    if waterfall_area(game.tile()) == 'hudonMound':
        _result39 = yield from leave_hudon_mound(log)
        return _result39
    _w40 = yield from traversal.walk_resilient(BOOKCASE_STAND, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w40):
        return False
    shelf = locs.query().where(lambda loc: loc.id == LOC.BOOKCASE).action('Search').within(8).nearest()
    if not shelf or not (shelf.interact('Search')):
        return False
    _w41 = yield from execution.delay_until(lambda: live_count(ITEM.BOOK) > 0, 8000)
    if not (_w41):
        return False
    _result42 = yield from read_book()
    return _result42


def leave_tgv_dungeon(log):
    _result43 = yield from walk_with_hops(Tile(2533, 3156, 0), 3, WATERFALL_HOPS, log)
    return _result43


def pebble_leg(log):
    if live_count(ITEM.PEBBLE) > 0:
        _result44 = yield from leave_tgv_dungeon(log)
        return _result44
    if waterfall_area(game.tile()) != 'tgvDungeon':
        _w45 = yield from walk_with_hops(GOLRIE_CRATE_STAND, 2, WATERFALL_HOPS, log)
        if not (_w45):
            return False
    if live_count(ITEM.GOLRIE_KEY) == 0:
        _w46 = yield from traversal.walk_resilient(GOLRIE_CRATE_STAND, radius=2, attempts=3, timeout_ms=90000, log=log)
        if not (_w46):
            return False
        crate = locs.query().where(lambda loc: loc.id == LOC.GOLRIE_CRATE).action('Search').within(8).nearest()
        if not crate or not (crate.interact('Search')):
            return False
        _result47 = yield from execution.delay_until(lambda: live_count(ITEM.GOLRIE_KEY) > 0, 8000)
        return _result47
    tile = game.tile()
    if not tile or tile.z < 9576:
        _w48 = yield from traversal.walk_resilient(GOLRIE_GATE_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
        if not (_w48):
            return False
        gate = locs.query().where(lambda loc: loc.id == LOC.GOLRIE_GATE).within(6).nearest()
        key = live_item(ITEM.GOLRIE_KEY)
        if not gate or not key or not (key.use_on(gate)):
            return False
        _result49 = yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) >= 9576, 8000)
        return _result49
    _w50 = yield from traversal.walk_resilient(GOLRIE_STAND, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w50):
        return False
    _w51 = yield from talk_through('Golrie', [], log)
    if not (_w51):
        return False
    return live_count(ITEM.PEBBLE) > 0


def tomb_exit(log):
    _w52 = yield from traversal.walk_resilient(TOMB_LADDER_STAND, radius=0, attempts=3, timeout_ms=90000, log=log)
    if not (_w52):
        return False
    # Even with no food left, leaving now beats waiting in the armed-zombie corridor.
    yield from heal_to_full(log, 'Glarial tomb exit')
    ladder = locs.query().action('Climb-up').within(8).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        return False
    _result53 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) != 'glarialTomb', 12000)
    return _result53


def tomb_leg(log):
    if waterfall_area(game.tile()) != 'glarialTomb':
        _w54 = yield from traversal.walk_resilient(TOMBSTONE_STAND, radius=2, attempts=3, timeout_ms=180000, log=log)
        if not (_w54):
            return False
        stone = locs.query().where(lambda loc: loc.id == LOC.TOMBSTONE).within(8).nearest()
        pebble = live_item(ITEM.PEBBLE)
        if not stone or not pebble or not (pebble.use_on(stone)):
            return False
        _result55 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'glarialTomb', 15000)
        return _result55
    if live_count(ITEM.AMULET) == 0 and not live_worn(ITEM.AMULET):
        _w56 = yield from traversal.walk_resilient(CHEST_STAND, radius=2, attempts=3, timeout_ms=120000, log=log)
        if not (_w56):
            return False
        closed = locs.query().where(lambda loc: loc.id == LOC.CHEST_CLOSED).action('Open').within(8).nearest()
        if closed:
            if not (closed.interact('Open')):
                return False
            yield from execution.delay_ticks(2)
            return True
        open = locs.query().where(lambda loc: loc.id == LOC.CHEST_OPEN).action('Search').within(8).nearest()
        if not open or not (open.interact('Search')):
            return False
        _result57 = yield from execution.delay_until(lambda: live_count(ITEM.AMULET) > 0, 8000)
        return _result57
    if live_count(ITEM.FULL_URN) == 0:
        _w58 = yield from traversal.walk_resilient(COFFIN_STAND, radius=1, attempts=3, timeout_ms=120000, log=log)
        if not (_w58):
            return False
        coffin = locs.query().where(lambda loc: loc.id == LOC.COFFIN).action('Search').within(8).nearest()
        if not coffin or not (coffin.interact('Search')):
            return False
        _result59 = yield from execution.delay_until(lambda: live_count(ITEM.FULL_URN) > 0, 8000)
        return _result59
    _result60 = yield from tomb_exit(log)
    return _result60


def barrel_escape(log):
    if waterfall_area(game.tile()) != 'fallsLedge':
        return True
    barrel = locs.query().where(lambda loc: loc.id == LOC.BARREL).action('Get in').within(12).nearest()
    if not barrel:
        log('no Waterfall escape barrel is loaded on the ledge')
        return False
    if not (barrel.interact('Get in')):
        return False
    _result61 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'mainland', 15000)
    return _result61


def cross_keyed_door(stand, arrived, log):
    _w62 = yield from traversal.walk_resilient(stand, radius=1, attempts=3, timeout_ms=90000, log=log)
    if not (_w62):
        return False
    door = locs.query().where(lambda loc: loc.id == LOC.KEYED_DOOR).within(4).nearest()
    key = live_item(ITEM.BAXTORIAN_KEY)
    if not door or not key or not (key.use_on(door)):
        return False
    _result63 = yield from execution.delay_until(arrived, 12000)
    return _result63


def exit_waterfall_dungeon(log):
    area = waterfall_area(game.tile())
    if area == 'raisedRoom':
        # Take treasure without the urn is the safe washout: no damage, and an exit when the key is lost.
        chalice = locs.query().where(lambda loc: loc.id == LOC.CHALICE).action('Take treasure').within(12).nearest()
        if not chalice or not (chalice.interact('Take treasure')):
            return False
        _result64 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'mainland', 30000)
        return _result64
    if area == 'puzzleRoom':
        _w65 = yield from cross_keyed_door(PUZZLE_DOOR_NORTH_STAND, lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9902, log)
        if not (_w65):
            return False
        area = waterfall_area(game.tile())
    tile = game.tile()
    if (area == 'waterfallDungeon' or area == 'puzzleRoom') and tile and tile.z >= 9894:
        _w66 = yield from cross_keyed_door(SOUTH_DOOR_NORTH_STAND, lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9894, log)
        if not (_w66):
            return False
    if waterfall_area(game.tile()) == 'waterfallDungeon':
        _w67 = yield from traversal.walk_resilient(ENTRY_DOOR_STAND, radius=2, attempts=3, timeout_ms=120000, log=log)
        if not (_w67):
            return False
        door = locs.query().where(lambda loc: loc.id == LOC.ENTRY_DOOR).action('Open').within(8).nearest()
        if not door or not (door.interact('Open')):
            return False
        _w68 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'fallsLedge', 15000)
        if not (_w68):
            return False
    _result69 = yield from barrel_escape(log)
    return _result69


def heal_to_full(log, context):
    while skills.effective('hitpoints') < skills.level('hitpoints'):
        before = skills.effective('hitpoints')
        yield from sustain.run()
        if skills.effective('hitpoints') <= before:
            log(f'{context}: cannot reach full health without usable food')
            return False
    return True


def prepare_dungeon_sprint(log):
    logged_energy_wait = False
    while True:
        readiness = waterfall_dungeon_entry_readiness(game.energy(), skills.effective('hitpoints'), skills.level('hitpoints'), game.run_enabled())
        if readiness == 'waitForEnergy':
            if not logged_energy_wait:
                log(f'waiting on the safe Waterfall ledge for {DUNGEON_RUN_ENERGY}% run energy')
                logged_energy_wait = True
            yield from sustain.run()
            yield from execution.delay_ticks(5)
            continue
        if readiness == 'heal':
            _w70 = yield from heal_to_full(log, 'Waterfall dungeon entry')
            if _w70:
                continue
            yield from barrel_escape(log)
            return False
        if readiness == 'enableRun':
            _c71 = not game.set_run(True)
            if not _c71:
                _w72 = yield from execution.delay_until(lambda: game.run_enabled(), 3000)
                _c71 = not (_w72)
            if _c71:
                log('could not enable run before entering the Waterfall dungeon')
                return False
            continue
        return True


def falls_leg(log):
    area = waterfall_area(game.tile())
    if area == 'fallsLedge':
        _w73 = yield from prepare_dungeon_sprint(log)
        if not (_w73):
            return False
        door = locs.query().where(lambda loc: loc.id == LOC.LEDGE_DOOR).action('Open').within(6).nearest()
        if not door or not (door.interact('Open')):
            return False
        _result74 = yield from execution.delay_until(lambda: (waterfall_area(game.tile()) in ['waterfallDungeon', 'puzzleRoom', 'raisedRoom']), 15000)
        return _result74
    if area == 'fallsTreeBank':
        tree = locs.query().where(lambda loc: loc.id == LOC.DEAD_TREE).within(8).nearest()
        rope = live_item(ITEM.ROPE)
        if not tree or not rope or not (rope.use_on(tree)):
            return False
        _result75 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'fallsLedge', 10000)
        return _result75
    if area == 'hudonMound':
        _w76 = yield from traversal.walk_resilient(ROCK_STAND, radius=1, attempts=3, timeout_ms=45000, log=log)
        if not (_w76):
            return False
        rock = locs.query().where(lambda loc: loc.id == LOC.CROSSING_ROCK).within(10).nearest()
        rope = live_item(ITEM.ROPE)
        if not rock or not rope or not (rope.use_on(rock)):
            return False
        _result77 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'fallsTreeBank', 10000)
        return _result77
    _result78 = yield from board_raft(log)
    return _result78


def pillar_order(pillar):
    """rs2b0t's comparator by x then z, as a sort key."""
    at = pillar.tile()
    return at.x * 100000 + at.z


def place_rune(rune, pillar, log):
    item = live_item(rune)
    if not item:
        return True
    before = live_count(rune)
    message_mark = game_messages.mark()
    if not (item.use_on(pillar)):
        return False
    processed = yield from execution.delay_until(lambda: live_count(rune) < before or game_messages.saw_since(message_mark, 'you place the rune on the stand') or game_messages.saw_since(message_mark, 'you remember putting that type of rune there'), 8000)
    if not processed:
        tile = pillar.tile()
        log(rune.name + ' placement on (' + str(tile.x) + ',' + str(tile.z) + ') was not acknowledged')
        return False
    return True


def solve_pillars(log):
    _w79 = yield from traversal.walk_resilient(PILLAR_STAND, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w79):
        return False
    yield from execution.delay_until(lambda: locs.query().where(lambda loc: loc.id == LOC.PILLAR).within(20).count() == 6, 5000)
    pillars = sorted(locs.query().where(lambda loc: loc.id == LOC.PILLAR).within(20).results(), key=pillar_order)
    if len(pillars) != 6:
        log('pillar room loaded ' + str(len(pillars)) + '/6 pillars; waiting for a complete scene')
        return False
    # Why: varp 66 is server-only and a fresh trip starts with 6 of each rune, so after an interruption the runes held equal the unset pillars.
    # Why: replaying every placement is idempotent; set bits consume nothing and unset bits consume 1.
    for pillar in pillars:
        for rune in RUNES:
            _w80 = yield from place_rune(rune, pillar, log)
            if not (_w80):
                return False
    _w81 = yield from traversal.walk_resilient(STATUE_STAND, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w81):
        return False
    statue = locs.query().where(lambda loc: loc.id == LOC.GLARIAL_STATUE).within(6).nearest()
    amulet = live_item(ITEM.AMULET)
    if not statue or not amulet or not (amulet.use_on(statue)):
        return False
    _result82 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'raisedRoom', 20000)
    return _result82


def find_baxtorian_key(log):
    if live_count(ITEM.BAXTORIAN_KEY) > 0:
        return True
    _w83 = yield from traversal.walk_resilient(BAXTORIAN_CRATE_STAND, radius=0, attempts=3, timeout_ms=90000, log=log)
    if not (_w83):
        return False
    _w84 = yield from heal_to_full(log, 'Baxtorian crate')
    if not (_w84):
        yield from exit_waterfall_dungeon(log)
        return False
    crate = locs.query().where(lambda loc: loc.id == LOC.BAXTORIAN_CRATE).action('Search').within(8).nearest()
    if not crate or not (crate.interact('Search')):
        return False
    _result85 = yield from execution.delay_until(lambda: live_count(ITEM.BAXTORIAN_KEY) > 0, 8000)
    return _result85


def complete_quest(log):
    if waterfall_area(game.tile()) != 'raisedRoom':
        return False
    if inventory.free() < 5:
        log('raised room pack has fewer than five reward slots; taking the safe washout')
        _result86 = yield from exit_waterfall_dungeon(log)
        return _result86
    chalice = locs.query().where(lambda loc: loc.id == LOC.CHALICE).within(12).nearest()
    urn = live_item(ITEM.FULL_URN)
    if not chalice or not urn or not (urn.use_on(chalice)):
        return False
    _result87 = yield from execution.delay_until(lambda: quests.status('Waterfall Quest') == 'complete', 30000)
    return _result87


def dungeon_leg(stage, log):
    area = waterfall_area(game.tile())
    if area == 'raisedRoom':
        if stage < WATERFALL_STAGE.RAISED_FLOOR:
            return False
        done = yield from complete_quest(log)
        return done
    _w88 = yield from find_baxtorian_key(log)
    if not (_w88):
        return False
    tile = game.tile()
    if not tile:
        return False
    if stage >= WATERFALL_STAGE.RAISED_FLOOR and tile.x >= 2598:
        _w89 = yield from traversal.walk_resilient(RAISED_ROOM_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
        if not (_w89):
            return False
        _result90 = yield from execution.delay_until(lambda: waterfall_area(game.tile()) == 'raisedRoom', 5000)
        return _result90
    if stage >= WATERFALL_STAGE.RAISED_FLOOR and tile.z >= 9902:
        _result91 = yield from cross_keyed_door(PUZZLE_DOOR_NORTH_STAND, lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9902, log)
        return _result91
    if tile.z < 9894:
        _result92 = yield from cross_keyed_door(SOUTH_DOOR_STAND, lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) >= 9894, log)
        return _result92
    if tile.z < 9902:
        _result93 = yield from cross_keyed_door(PUZZLE_DOOR_STAND, lambda: ((((game.tile().x if game.tile() is not None else None) if (game.tile().x if game.tile() is not None else None) is not None else 0)) >= 2598 if stage >= WATERFALL_STAGE.RAISED_FLOOR else (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 0)) >= 9902), log)
        return _result93
    _result94 = yield from solve_pillars(log)
    return _result94


def prepare_tomb_entry(snap):
    bank = ARDOUGNE_BANK
    if not snap.bank_known:
        return scan_bank(bank)
    if not held(snap, ITEM.PEBBLE):
        travel_normalize = normalize_loadout(snap, with_food(TOMB_TRAVEL_KEEP), 'prepare a safe Glarial tomb recovery trip', bank)
        if travel_normalize:
            return travel_normalize
        travel_food = source_food(snap, bank)
        if travel_food:
            return travel_food
        if banked(snap, ITEM.PEBBLE) > 0:
            return withdraw_exact(ITEM.PEBBLE, 1, bank)
        return Record({'kind': 'custom', 'name': 'recover Glarial pebble from Golrie', 'run': pebble_leg})
    normalize = normalize_loadout(snap, with_food(TOMB_KEEP), 'strip prohibited items before Glarial tomb')
    if normalize:
        return normalize
    food = source_food(snap, bank)
    if food:
        return food
    # Why: surviving relics get banked on the exposed Golrie leg and brought into the tomb, so only the missing one is looted.
    surviving_relics = withdraw_banked_relics(snap, bank)
    if surviving_relics:
        return surviving_relics
    return Record({'kind': 'custom', 'name': 'loot Glarial amulet and urn', 'run': tomb_leg})


def recover_relics(snap):
    missing = [item for item in [ITEM.AMULET, ITEM.FULL_URN] if owned(snap, item) == 0]
    return (prepare_tomb_entry(snap) if len(missing) > 0 else None)


def resume_pebble_recovery(snap, area):
    if area != 'tgvDungeon' or not recover_relics(snap):
        return None
    return Record({'kind': 'custom', 'name': 'recover Glarial pebble from Golrie', 'run': pebble_leg})


def withdraw_banked_relics(snap, bank=None):
    if bank is None:
        bank = ARDOUGNE_BANK
    items = []
    for item in [ITEM.AMULET, ITEM.FULL_URN, ITEM.BAXTORIAN_KEY]:
        if not held(snap, item) and not worn(snap, item) and banked(snap, item) > 0:
            items.append({'name': item.name, 'id': item.id, 'qty': 1})
    return (withdraw(items, bank) if len(items) > 0 else None)


def prepare_dungeon(snap, final_trip):
    bank = ARDOUGNE_BANK
    if not snap.bank_known:
        return scan_bank(bank)
    relic_recovery = recover_relics(snap)
    if relic_recovery:
        return relic_recovery
    # Why: refilling food first narrows the pack to travel supplies, so a restart with leftover relics or runes can't fill it before the food and Rope are in.
    food0 = food_item()
    replenishing_food = food0 is not None and held_count(snap, food0) <= FOOD_LOW
    travel_normalize = normalize_loadout(snap, with_food((START_KEEP if replenishing_food else ((FINAL_KEEP if final_trip else DUNGEON_KEEP)))), ('prepare a safe final Waterfall trip' if final_trip else 'prepare a safe Waterfall dungeon trip'), bank)
    if travel_normalize:
        return travel_normalize
    food = source_food(snap, bank)
    if food:
        return food
    rope = source_rope(snap, bank)
    if rope:
        return rope
    normalize = normalize_loadout(snap, with_food((FINAL_KEEP if final_trip else DUNGEON_KEEP)), ('bank puzzle leftovers for the final trip' if final_trip else 'assemble the Waterfall dungeon loadout'))
    if normalize:
        return normalize
    relics = withdraw_banked_relics(snap, bank)
    if relics:
        return relics
    if not final_trip:
        runes = source_puzzle_runes(snap)
        if runes:
            return runes
    if not held(snap, ITEM.AMULET) and not worn(snap, ITEM.AMULET):
        return Record({'kind': 'wait', 'reason': "Glarial's amulet is not in the final loadout"})
    if not held(snap, ITEM.FULL_URN):
        return Record({'kind': 'wait', 'reason': "Glarial's full urn is not in the final loadout"})
    return None


def escape_unexpected_area(area):
    if area == 'hudonMound':
        return Record({'kind': 'custom', 'name': 'swim back from Hudon mound', 'run': leave_hudon_mound})
    if area == 'fallsLedge':
        return Record({'kind': 'custom', 'name': 'leave the Waterfall ledge by barrel', 'run': barrel_escape})
    if area == 'fallsTreeBank':
        return Record({'kind': 'wait', 'reason': 'cannot leave the Waterfall tree bank safely without Rope'})
    if area == 'tgvDungeon':
        return Record({'kind': 'custom', 'name': 'leave the Tree Gnome Village dungeon', 'run': leave_tgv_dungeon})
    if area == 'glarialTomb':
        return Record({'kind': 'custom', 'name': "leave Glarial's tomb", 'run': tomb_exit})
    if area == 'waterfallDungeon' or area == 'puzzleRoom' or area == 'raisedRoom':
        return Record({'kind': 'custom', 'name': 'leave the Waterfall dungeon safely', 'run': exit_waterfall_dungeon})
    return None


def stage_zero(snap, area):
    if area == 'unknown':
        return Record({'kind': 'wait', 'reason': 'player location unavailable'})
    escape = escape_unexpected_area(area)
    if escape:
        return escape
    bank = ARDOUGNE_BANK
    if not snap.bank_known:
        return scan_bank(bank)
    normalize = normalize_loadout(snap, with_food(START_KEEP), 'bank everything except Waterfall supplies', bank)
    if normalize:
        return normalize
    cash = ensure_coins(snap, remaining_waterfall_cash(snap), bank)
    if cash:
        return cash
    food = source_food(snap, bank)
    if food:
        return food
    rope = source_rope(snap, bank)
    if rope:
        return rope
    return Record({'kind': 'talk', 'stop': ALMERA})


def stage_two(snap, area):
    if area == 'hudonMound':
        return Record({'kind': 'custom', 'name': 'swim downstream to the tourist office', 'run': leave_hudon_mound})
    escape = escape_unexpected_area(area)
    if escape:
        return escape
    bank = ARDOUGNE_BANK
    if not snap.bank_known:
        return scan_bank(bank)
    normalize = normalize_loadout(snap, with_food(BOOK_TRAVEL_KEEP), 'prepare the Book on Baxtorian trip', bank)
    if normalize:
        return normalize
    food = source_food(snap)
    if food:
        return food
    if held(snap, ITEM.BOOK):
        return Record({'kind': 'custom', 'name': 'read the Book on Baxtorian', 'run': read_book})
    if banked(snap, ITEM.BOOK) > 0:
        return withdraw_exact(ITEM.BOOK, 1)
    return Record({'kind': 'custom', 'name': 'find and read the Book on Baxtorian', 'run': book_leg})


def stage_three(snap, area):
    if area == 'glarialTomb':
        return Record({'kind': 'custom', 'name': 'loot Glarial amulet and urn', 'run': tomb_leg})
    if area == 'tgvDungeon':
        return Record({'kind': 'custom', 'name': 'recover Glarial pebble from Golrie', 'run': pebble_leg})
    escape = escape_unexpected_area(area)
    if escape:
        return escape
    return prepare_tomb_entry(snap)


def stage_four(snap, area):
    if area == 'glarialTomb':
        return Record({'kind': 'custom', 'name': 'loot Glarial amulet and urn', 'run': tomb_leg})
    pebble_recovery = resume_pebble_recovery(snap, area)
    if pebble_recovery:
        return pebble_recovery
    if area == 'fallsLedge' and not held(snap, ITEM.AMULET) and not worn(snap, ITEM.AMULET):
        return Record({'kind': 'custom', 'name': 'leave the ledge without risking the amulet door', 'run': barrel_escape})
    if area == 'hudonMound' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'custom', 'name': 'swim back from Hudon mound', 'run': leave_hudon_mound})
    if area == 'fallsTreeBank' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'wait', 'reason': 'Rope missing on the one-way Waterfall crossing'})
    if area == 'hudonMound' or area == 'fallsTreeBank' or area == 'fallsLedge':
        return Record({'kind': 'custom', 'name': 'enter Baxtorian Falls', 'run': falls_leg})
    escape = escape_unexpected_area(area)
    if escape:
        return escape
    prep = prepare_dungeon(snap, False)
    return (prep if prep is not None else Record({'kind': 'custom', 'name': 'enter Baxtorian Falls', 'run': falls_leg}))


def stage_five_or_six(snap, stage, area):
    if area == 'waterfallDungeon' or area == 'puzzleRoom' or area == 'raisedRoom':
        return Record({
            'kind': 'custom',
            'name': ('solve the six rune pillars' if stage == WATERFALL_STAGE.ENTERED_PUZZLE else 'cross the Waterfall dungeon'),
            'run': lambda log: dungeon_leg(stage, log),
        })
    if area == 'glarialTomb':
        return Record({'kind': 'custom', 'name': 'finish recovering Glarial relics', 'run': tomb_leg})
    pebble_recovery = resume_pebble_recovery(snap, area)
    if pebble_recovery:
        return pebble_recovery
    if area == 'tgvDungeon':
        return Record({'kind': 'custom', 'name': 'leave the Tree Gnome Village dungeon', 'run': leave_tgv_dungeon})
    if area == 'fallsLedge' and not held(snap, ITEM.AMULET) and not worn(snap, ITEM.AMULET):
        return Record({'kind': 'custom', 'name': 'leave the ledge without risking the amulet door', 'run': barrel_escape})
    if area == 'hudonMound' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'custom', 'name': 'swim back from Hudon mound', 'run': leave_hudon_mound})
    if area == 'fallsTreeBank' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'wait', 'reason': 'Rope missing on the one-way Waterfall crossing'})
    if area != 'mainland':
        return Record({'kind': 'custom', 'name': 'cross into Baxtorian Falls', 'run': falls_leg})
    prep = prepare_dungeon(snap, False)
    return (prep if prep is not None else Record({'kind': 'custom', 'name': 'cross into Baxtorian Falls', 'run': falls_leg}))


def stage_eight(snap, area):
    if area == 'raisedRoom':
        if not held(snap, ITEM.FULL_URN) or ((snap.free_slots if snap.free_slots is not None else 0)) < 5:
            return Record({'kind': 'custom', 'name': 'wash out to recover the final loadout', 'run': exit_waterfall_dungeon})
        return Record({'kind': 'custom', 'name': "pour Glarial's ashes into the Chalice", 'run': complete_quest})
    if area == 'waterfallDungeon' or area == 'puzzleRoom':
        return Record({
            'kind': 'custom',
            'name': 'return directly to the raised Chalice room',
            'run': lambda log: dungeon_leg(WATERFALL_STAGE.RAISED_FLOOR, log),
        })
    if area == 'glarialTomb':
        return Record({'kind': 'custom', 'name': 'recover final Glarial relics', 'run': tomb_leg})
    pebble_recovery = resume_pebble_recovery(snap, area)
    if pebble_recovery:
        return pebble_recovery
    if area == 'tgvDungeon':
        return Record({'kind': 'custom', 'name': 'leave the Tree Gnome Village dungeon', 'run': leave_tgv_dungeon})
    if area == 'fallsLedge' and not held(snap, ITEM.AMULET) and not worn(snap, ITEM.AMULET):
        return Record({'kind': 'custom', 'name': 'leave the ledge without risking the amulet door', 'run': barrel_escape})
    if area == 'hudonMound' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'custom', 'name': 'swim back from Hudon mound', 'run': leave_hudon_mound})
    if area == 'fallsTreeBank' and not held(snap, ITEM.ROPE):
        return Record({'kind': 'wait', 'reason': 'Rope missing on the one-way Waterfall crossing'})
    if area != 'mainland':
        return Record({'kind': 'custom', 'name': 'return to the Waterfall dungeon', 'run': falls_leg})
    prep = prepare_dungeon(snap, True)
    return (prep if prep is not None else Record({'kind': 'custom', 'name': 'return to the Waterfall dungeon', 'run': falls_leg}))


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= WATERFALL_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Waterfall Quest journal stage unavailable'})
    area = waterfall_area(snap.tile)
    if snap.stage == WATERFALL_STAGE.NOT_STARTED:
        return stage_zero(snap, area)
    elif snap.stage == WATERFALL_STAGE.STARTED:
        if area == 'hudonMound':
            return Record({'kind': 'custom', 'name': 'speak to Hudon', 'run': stage_one_leg})
        if area != 'mainland':
            _v95 = escape_unexpected_area(area)
            return (_v95 if _v95 is not None else Record({'kind': 'wait', 'reason': 'cannot reach Almera raft from this area'}))
        bank = ARDOUGNE_BANK
        if not snap.bank_known:
            return scan_bank(bank)
        normalize = normalize_loadout(snap, with_food(START_KEEP), 'prepare the Almera raft trip', bank)
        if normalize:
            return normalize
        food = source_food(snap)
        if food:
            return food
        return Record({'kind': 'custom', 'name': 'board Almera raft and find Hudon', 'run': stage_one_leg})
    elif snap.stage == WATERFALL_STAGE.SPOKEN_TO_HUDON:
        return stage_two(snap, area)
    elif snap.stage == WATERFALL_STAGE.READ_BOOK:
        return stage_three(snap, area)
    elif snap.stage == WATERFALL_STAGE.ENTERED_TOMB:
        return stage_four(snap, area)
    elif snap.stage in [WATERFALL_STAGE.ENTERED_WATERFALL, WATERFALL_STAGE.ENTERED_PUZZLE]:
        return stage_five_or_six(snap, snap.stage, area)
    elif snap.stage == WATERFALL_STAGE.RAISED_FLOOR:
        return stage_eight(snap, area)
    else:
        return Record({'kind': 'wait', 'reason': 'unrecognized Waterfall Quest stage ' + str(snap.stage)})


waterfall = QuestModule(**{
    'record': quest_record('waterfall'),
    'bank': ARDOUGNE_BANK,
    'hops': WATERFALL_HOPS,
    'tools': ['glarial', 'a key', 'rope', 'book on baxtorian', 'air rune', 'earth rune', 'water rune', 'coins'],
    'owns_inventory': True,
    'read_stage': read_waterfall_stage,
    'sustain': Record({'foods': [], 'eat_below_hp': 1}),
    'decide': decide,
})

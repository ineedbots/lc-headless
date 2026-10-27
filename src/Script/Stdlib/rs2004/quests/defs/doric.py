"""Ported from rs2b0t's src/bot/api/ai/quests/defs/doric.ts (MIT, see thirdparty/rs2b0t)."""

import _core
import math
from rs2004 import execution
from rs2004.catalogs.mining import ROCK_TYPES
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs
from rs2004.execution import event_signal
from rs2004.game import game, reader, skills
from rs2004.geometry import Tile
from rs2004.interfaces import interfaces
from rs2004.items import equipment, inventory
from rs2004.navigation import reachability
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.exec.primitives import goto_npc, talk_strict
from rs2004.quests.journal_text import normalize_journal as journal_text
from rs2004.tabs import quests
from rs2004.traversal import traversal


__all__ = ['DORIC_STAGE', 'DORIC_ITEM', 'DORIC_PICKAXES', 'parse_doric_journal', 'decide_for_mining_level', 'decide', 'doric']

DORIC_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 10, 'COMPLETE': 100})
DORIC_ITEM = Record({
    'CLAY': {'name': 'Clay', 'id': 434, 'qty': 6},
    'COPPER': {'name': 'Copper ore', 'id': 436, 'qty': 4},
    'IRON': {'name': 'Iron ore', 'id': 440, 'qty': 2},
    'BRONZE_PICKAXE': Record({'name': 'Bronze pickaxe', 'id': 1265}),
})
PICKAXE_ID = Record({
    'Bronze pickaxe': 1265,
    'Iron pickaxe': 1267,
    'Steel pickaxe': 1269,
    'Adamant pickaxe': 1271,
    'Mithril pickaxe': 1273,
    'Rune pickaxe': 1275,
})
DORIC_PICKAXES = [Record({'name': name + ' pickaxe', 'id': PICKAXE_ID.get(name + ' pickaxe'), 'level': level}) for name, level in [('Rune', 41), ('Adamant', 31), ('Mithril', 21), ('Steel', 6), ('Iron', 1), ('Bronze', 1)]]
MATERIALS = [DORIC_ITEM.CLAY, DORIC_ITEM.COPPER, DORIC_ITEM.IRON]
MATERIAL_IDS = set([item.id for item in MATERIALS])
PICKAXE_IDS = set([item.id for item in DORIC_PICKAXES])
DORIC = Record({
    'npc': 'Doric',
    'anchor': Tile(2952, 3451, 0),
    'leash': 6,
    'prefer': ['I wanted to use your anvils.', 'Yes, I will get you materials.'],
})
BANKS = [Tile(2946, 3369, 0), Tile(3013, 3355, 0), Tile(3093, 3243, 0)]
ORE_ANCHORS = Record({'Clay': Tile(2986, 3240, 0), 'Copper': Tile(2978, 3247, 0), 'Iron': Tile(2972, 3239, 0)})
# Static bronze pickaxe on the table south of the Rimmington mine.
BRONZE_PICKAXE_SPAWN = Tile(2963, 3216, 0)
PICKAXE_RESPAWN_MS = 70000
ROCK_RESPAWN_MS = 30000


def parse_doric_journal(lines):
    text = journal_text(lines)
    if ('quest complete!' in text):
        return DORIC_STAGE.COMPLETE
    if ('i have spoken to doric' in text) and ('i need to collect some items' in text):
        return DORIC_STAGE.STARTED
    if ('i can start this quest by talking to' in text) and ('doric' in text):
        return DORIC_STAGE.NOT_STARTED
    return None


def read_doric_stage():
    status = quests.status("Doric's Quest")
    if status == 'complete':
        return DORIC_STAGE.COMPLETE
    if status == 'not_started':
        return DORIC_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    lines = yield from quests.journal("Doric's Quest")
    stage = parse_doric_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


def held_count(snap, item):
    if snap.inv_ids is not None:
        _v1 = (snap.inv_ids or {}).get(item.id)
        return (_v1 if _v1 is not None else 0)
    _v2 = snap.inv.get(item.name.lower())
    return (_v2 if _v2 is not None else 0)


def banked_count(snap, item):
    if snap.bank_ids is not None:
        _v3 = (snap.bank_ids or {}).get(item.id)
        return (_v3 if _v3 is not None else 0)
    _v4 = (snap.bank or {}).get(item.name.lower())
    return (_v4 if _v4 is not None else 0)


def pick_held(snap, pickaxe):
    if snap.inv_ids is not None or snap.worn_ids is not None:
        _v5 = (snap.inv_ids or {}).get(pickaxe.id)
        return ((_v5 if _v5 is not None else 0)) > 0 or (((pickaxe.id in (snap.worn_ids or set())) if (pickaxe.id in (snap.worn_ids or set())) is not None else False))
    name = pickaxe.name.lower()
    _v6 = snap.inv.get(name)
    return ((_v6 if _v6 is not None else 0)) > 0 or (name in snap.worn)


def pick_banked(snap, pickaxe):
    if snap.bank_ids is not None:
        _v7 = (snap.bank_ids or {}).get(pickaxe.id)
        return ((_v7 if _v7 is not None else 0)) > 0
    _v8 = (snap.bank or {}).get(pickaxe.name.lower())
    return ((_v8 if _v8 is not None else 0)) > 0


def best_usable_pickaxe(mining_level, available):
    _v9 = ([pickaxe for pickaxe in DORIC_PICKAXES if mining_level >= pickaxe.level and available(pickaxe)] or [None])[0]
    return (_v9 if _v9 is not None else None)


def nearest_bank(snap):
    if not snap.tile:
        return BANKS[2]
    return (sorted(list(BANKS), key=lambda a: a.distance_to(snap.tile)) or [None])[0]


def talk_at_stage(stage, action):
    def _fn10(log):
        log(f'journal stage {stage}: {action}')
        _w11 = yield from goto_npc(DORIC, [], log)
        if not (_w11):
            log(f'stage {stage}: could not reach Doric')
            return False
        _w12 = yield from talk_strict(DORIC.npc, DORIC.prefer, log)
        if not (_w12):
            log(f'stage {stage}: Doric dialogue did not complete')
            return False
        log(f'stage {stage}: finished Doric\'s dialogue; re-reading the journal')
        return True
    return Record({'kind': 'custom', 'name': f'stage {stage}: {action}', 'run': _fn10})


COINS_ID = 995
DORIC_REWARD_COINS = 180


# Why: Doric's script queues the quest-complete scroll before its final dialogue and coins, and a generic driver returns when the modal closes, so success waits for the coins and a drained queue.
def hand_in_materials(log):
    """Hand Doric his materials and drive the completion queue to the end."""
    _w13 = yield from goto_npc(DORIC, [], log)
    if not (_w13):
        log('stage 10: could not reach Doric for the material hand-in')
        return False
    coins_before = inventory.count_by_id(COINS_ID)
    materials_before = [inventory.count_by_id(item.id) for item in MATERIALS]
    dialogue_closed = yield from talk_strict(DORIC.npc, DORIC.prefer, log)
    materials_taken = all([inventory.count_by_id(item.id) <= materials_before[index] - item.qty for index, item in enumerate(MATERIALS)])
    reward_started = materials_taken or quests.status("Doric's Quest") == 'complete' or reader.modals().main != -1
    if not dialogue_closed and not reward_started:
        log('stage 10: Doric did not accept the materials')
        return False
    closed_reward_scroll = False
    quiet_reward_ticks = 0
    for guard in range(160):
        if reader.modals().main != -1:
            if not closed_reward_scroll:
                log('stage 10: closing the quest-complete scroll and continuing the server reward queue')
                closed_reward_scroll = True
            if not _core.close_interfaces():
                log('stage 10: could not close the quest-complete/reward modal')
                return False
            yield from execution.delay_ticks(1)
            continue
        if chat_dialog.can_continue():
            _w14 = yield from chat_dialog.continue_()
            if not (_w14):
                log("stage 10: could not continue Doric's post-completion dialogue")
                return False
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            log(f"stage 10: unexpected post-completion options [{' | '.join(options)}]")
            return False
        rewarded = inventory.count_by_id(COINS_ID) >= coins_before + DORIC_REWARD_COINS
        if rewarded and not chat_dialog.is_open():
            # Several quiet ticks: the server can pay the coins right before opening its final chat page.
            quiet_reward_ticks += 1
            if quiet_reward_ticks >= 3:
                log(f'stage 10: reward queue drained; received {DORIC_REWARD_COINS} coins')
                return True
            yield from execution.delay_ticks(1)
            continue
        quiet_reward_ticks = 0
        yield from execution.delay_ticks(1)
    log(f'stage 10: reward queue did not deliver {DORIC_REWARD_COINS} coins and drain')
    return False


def live_usable_pickaxe():
    level = skills.level('mining')
    _v15 = (([pickaxe for pickaxe in DORIC_PICKAXES if level >= pickaxe.level and (inventory.count_by_id(pickaxe.id) > 0 or any([item.id == pickaxe.id for item in equipment.items()]))] or [None])[0].name if ([pickaxe for pickaxe in DORIC_PICKAXES if level >= pickaxe.level and (inventory.count_by_id(pickaxe.id) > 0 or any([item.id == pickaxe.id for item in equipment.items()]))] or [None])[0] is not None else None)
    return (_v15 if _v15 is not None else None)


def mining_interrupted():
    return event_signal.pending() or chat_dialog.can_continue() or game.in_combat() or live_usable_pickaxe() is None


def nearby_rock(type_):
    ids = set(ROCK_TYPES.get(type_))
    return locs.query().where(lambda loc: (loc.id in ids) and reachability.can_reach(loc.tile(), adjacent_ok=True)).action('Mine').within(20).nearest()


def mine_one(type_, item, log):
    if inventory.is_full():
        log(f'{type_}: inventory is full before mining')
        return False
    pickaxe = live_usable_pickaxe()
    if not pickaxe:
        log(f'{type_}: no usable pickaxe in the inventory or equipment')
        return False
    rock = nearby_rock(type_)
    if not rock:
        log(f'{type_}: walking to the Rimmington mine')
        _w16 = yield from traversal.walk_resilient(ORE_ANCHORS.get(type_), radius=4, attempts=3, timeout_ms=120000, log=log)
        if not (_w16):
            log(f'{type_}: could not reach the Rimmington mine')
            return False
        rock = nearby_rock(type_)
    if not rock:
        log(f'{type_}: all nearby rocks are depleted; waiting for a respawn')
        yield from execution.delay_until(lambda: nearby_rock(type_) is not None or mining_interrupted(), ROCK_RESPAWN_MS)
        if mining_interrupted():
            return False
        rock = nearby_rock(type_)
    if not rock:
        log(f'{type_}: a rock respawn was taken by another player; retrying')
        return False
    before = inventory.count_by_id(item.id)
    log(f'{type_}: mining one with {pickaxe}')
    if not (rock.interact('Mine')):
        log(f'{type_}: Mine interaction failed or lost a player race')
        return False
    yield from execution.delay_until(lambda: inventory.count_by_id(item.id) > before or inventory.is_full() or mining_interrupted(), 20000)
    obtained = inventory.count_by_id(item.id) > before
    if obtained:
        log(f'{type_}: acquired {item.name}')
    elif event_signal.pending() or game.in_combat():
        log(f'{type_}: yielding immediately to a mining random event')
    else:
        log(f'{type_}: no {item.name} obtained; retrying after the interrupted/depleted swing')
    return obtained


def nearby_bronze_pickaxe():
    return ground_items.query().where(lambda item: item.id == DORIC_ITEM.BRONZE_PICKAXE.id).within(12).nearest()


def acquire_bronze_pickaxe(log):
    if live_usable_pickaxe():
        return True
    if inventory.is_full():
        log('pickaxe: inventory is full before pickup')
        return False
    pickaxe = nearby_bronze_pickaxe()
    if not pickaxe:
        log('pickaxe: walking to the free Rimmington bronze pickaxe spawn')
        _w17 = yield from traversal.walk_resilient(BRONZE_PICKAXE_SPAWN, radius=2, attempts=3, timeout_ms=120000, log=log)
        if not (_w17):
            log('pickaxe: could not reach the Rimmington spawn')
            return False
        pickaxe = nearby_bronze_pickaxe()
    if not pickaxe:
        log('pickaxe: spawn is empty; waiting for its bounded respawn')
        yield from execution.delay_until(lambda: nearby_bronze_pickaxe() is not None or event_signal.pending() or game.in_combat(), PICKAXE_RESPAWN_MS)
        if event_signal.pending() or game.in_combat():
            return False
        pickaxe = nearby_bronze_pickaxe()
    if not pickaxe:
        log('pickaxe: respawn was taken by another player; retrying')
        return False
    before = inventory.count_by_id(DORIC_ITEM.BRONZE_PICKAXE.id)
    if not (pickaxe.interact('Take')):
        log('pickaxe: Take interaction failed or lost a player race')
        return False
    obtained = yield from execution.delay_until(lambda: inventory.count_by_id(DORIC_ITEM.BRONZE_PICKAXE.id) > before or event_signal.pending(), 8000)
    if obtained and inventory.count_by_id(DORIC_ITEM.BRONZE_PICKAXE.id) > before:
        log('pickaxe: acquired the free Bronze pickaxe')
        return True
    return False


def drop_one_copper(log):
    before = inventory.count_by_id(DORIC_ITEM.COPPER.id)
    if before <= DORIC_ITEM.COPPER.qty:
        return True
    ore = ([item for item in inventory.items() if item.id == DORIC_ITEM.COPPER.id] or [None])[0]
    if not ore or not (ore.interact('Drop')):
        log('training: could not drop surplus Copper ore')
        return False
    dropped = yield from execution.delay_until(lambda: inventory.count_by_id(DORIC_ITEM.COPPER.id) < before, 5000)
    if dropped:
        log(f'training: dropped surplus Copper ore; retaining {DORIC_ITEM.COPPER.qty} for Doric')
    return dropped


def preserve_quest_items(bank):
    return Record({
        'kind': 'deposit',
        'keep': [],
        'keep_ids': list(MATERIAL_IDS) + list(PICKAXE_IDS),
        'bank': bank,
        'exact_keep': True,
    })


def has_depositable_item(snap):
    if snap.inv_ids is not None:
        return any([not (id in MATERIAL_IDS) and not (id in PICKAXE_IDS) for id in list(list(snap.inv_ids.keys()))])
    keeps = set(list([item.name.lower() for item in MATERIALS]) + list([item.name.lower() for item in DORIC_PICKAXES]))
    return any([not (name in keeps) for name in list(list(snap.inv.keys()))])


def make_space(snap, needed, bank):
    if snap.free_slots is None or snap.free_slots >= needed:
        return None
    if has_depositable_item(snap):
        return preserve_quest_items(bank)
    # Why: a restored account can have all 28 slots full of Doric items (surplus ore, spare picks, an unusable high-tier pick), so keeping every quantity would park forever.
    # Why: the exact set is banked too, and the next bank snapshot withdraws only the material deficits and 1 best usable pickaxe.
    return Record({'kind': 'deposit', 'keep': [], 'keep_ids': [], 'bank': bank, 'exact_keep': True})


def material_withdrawals(snap):
    withdrawals = []
    for item in MATERIALS:
        missing = max(0, item.qty - held_count(snap, item))
        available = min(missing, banked_count(snap, item))
        if available > 0:
            withdrawals.append({'name': item.name, 'id': item.id, 'qty': available})
    return withdrawals


def all_materials_held(snap):
    return all([held_count(snap, item) >= item.qty for item in MATERIALS])


def stage_ten(snap, mining_level, mining_xp):
    if all_materials_held(snap):
        return Record({
            'kind': 'custom',
            'name': 'stage 10: hand Doric 6 Clay, 4 Copper ore, and 2 Iron ore and collect the full reward',
            'run': hand_in_materials,
        })
    bank = nearest_bank(snap)
    if not snap.bank_known:
        return Record({'kind': 'scan_bank', 'bank': bank})
    withdrawals = material_withdrawals(snap)
    if len(withdrawals) > 0:
        space = make_space(snap, sum([item['qty'] for item in withdrawals]), bank)
        if space:
            return space
        return Record({'kind': 'withdraw', 'items': withdrawals, 'bank': bank})
    # Copper above 4 only trains Mining for iron. Drop 1 at a time so each iteration yields to the random-event supervisor.
    if held_count(snap, DORIC_ITEM.COPPER) > DORIC_ITEM.COPPER.qty:
        return Record({'kind': 'custom', 'name': 'drop one surplus training Copper ore', 'run': drop_one_copper})
    missing = [item for item in MATERIALS if held_count(snap, item) < item.qty]
    held_pickaxe = best_usable_pickaxe(mining_level, lambda pickaxe: pick_held(snap, pickaxe))
    if not held_pickaxe:
        bank_pickaxe = best_usable_pickaxe(mining_level, lambda pickaxe: pick_banked(snap, pickaxe))
        space = make_space(snap, 1, bank)
        if space:
            return space
        if bank_pickaxe:
            return Record({
                'kind': 'withdraw',
                'items': [{'name': bank_pickaxe.name, 'id': bank_pickaxe.id, 'qty': 1}],
                'bank': bank,
            })
        return Record({
            'kind': 'custom',
            'name': 'source a free Bronze pickaxe at Rimmington',
            'run': acquire_bronze_pickaxe,
        })
    space = make_space(snap, 1, bank)
    if space:
        return space
    if (DORIC_ITEM.CLAY in missing):
        return Record({
            'kind': 'custom',
            'name': f'mine Clay {held_count(snap, DORIC_ITEM.CLAY)}/{DORIC_ITEM.CLAY.qty}',
            'run': lambda log: mine_one('Clay', DORIC_ITEM.CLAY, log),
        })
    if (DORIC_ITEM.COPPER in missing):
        return Record({
            'kind': 'custom',
            'name': f'mine Copper ore {held_count(snap, DORIC_ITEM.COPPER)}/{DORIC_ITEM.COPPER.qty}',
            'run': lambda log: mine_one('Copper', DORIC_ITEM.COPPER, log),
        })
    if (DORIC_ITEM.IRON in missing) and mining_level < 15:
        return Record({
            'kind': 'custom',
            'name': f'train Mining {mining_level}/15 on Copper ({math.floor(mining_xp)} XP)',
            'run': lambda log: mine_one('Copper', DORIC_ITEM.COPPER, log),
        })
    if (DORIC_ITEM.IRON in missing):
        return Record({
            'kind': 'custom',
            'name': f'mine Iron ore {held_count(snap, DORIC_ITEM.IRON)}/{DORIC_ITEM.IRON.qty}',
            'run': lambda log: mine_one('Iron', DORIC_ITEM.IRON, log),
        })
    return Record({'kind': 'wait', 'reason': 'Doric material state could not be resolved'})


def decide_for_mining_level(snap, mining_level, mining_xp=0):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= DORIC_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': "Doric's Quest stage unavailable"})
    if snap.stage == DORIC_STAGE.NOT_STARTED:
        return talk_at_stage(0, 'ask Doric to use his anvils and accept the materials job')
    elif snap.stage == DORIC_STAGE.STARTED:
        return stage_ten(snap, mining_level, mining_xp)
    else:
        return Record({'kind': 'wait', 'reason': f'unrecognized Doric\'s Quest stage {snap.stage}'})


def decide(snap):
    return decide_for_mining_level(snap, skills.level('mining'), skills.xp('mining'))


doric = QuestModule(**{
    'record': ([record for record in QUESTS if record.id == 'doric'] or [None])[0],
    'bank': BANKS[0],
    'owns_inventory': True,
    'read_stage': read_doric_stage,
    'decide': decide,
})

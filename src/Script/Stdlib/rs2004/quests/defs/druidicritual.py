"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidicritual.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import direct_navigator, game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.exec.primitives import walk_with_hops
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['DRUIDIC_RITUAL_STAGE', 'parse_druidic_ritual_journal', 'druidic_ritual_area', 'decide', 'druidicritual']

DRUIDIC_RITUAL_STAGE = Record({'NOT_STARTED': 0, 'STARTED': 1, 'SPOKEN_TO_SANFEW': 2, 'GIVEN_INGREDIENTS': 3, 'COMPLETE': 4})


def parse_druidic_ritual_journal(lines):
    text = normalize_journal(lines)
    # Later entries keep earlier history, so match the newest first.
    if ('quest complete!' in text):
        return DRUIDIC_RITUAL_STAGE.COMPLETE
    if ('gave them to sanfew' in text) or ('claim my reward' in text):
        return DRUIDIC_RITUAL_STAGE.GIVEN_INGREDIENTS
    if ('sanfew told me for the ritual' in text):
        return DRUIDIC_RITUAL_STAGE.SPOKEN_TO_SANFEW
    if ('i should speak to sanfew' in text):
        return DRUIDIC_RITUAL_STAGE.STARTED
    if ('i can start this quest' in text):
        return DRUIDIC_RITUAL_STAGE.NOT_STARTED
    return None


def read_druidic_ritual_stage():
    status = quests.status('Druidic Ritual')
    if status == 'complete':
        return DRUIDIC_RITUAL_STAGE.COMPLETE
    if status == 'not_started':
        return DRUIDIC_RITUAL_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    # Why: druidquest is a server-only varp, so the rendered journal is the stage oracle.
    lines = yield from quests.journal('Druidic Ritual')
    stage = parse_druidic_ritual_journal(lines)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage


KAQEMEEX = Record({
    'npc': 'Kaqemeex',
    'anchor': Tile(2924, 3486, 0),
    'leash': 8,
    'prefer': ["I'm in search of a quest.", 'Ok, I will try and help.'],
})
SANFEW = Record({
    'npc': 'Sanfew',
    'anchor': Tile(2897, 3426, 1),
    'leash': 8,
    'prefer': ["I've been sent to help purify the Varrock stone circle.", "Ok, I'll do that then."],
})
FALADOR_WEST_BANK = Tile(2946, 3369, 0)
DUNGEON_SURFACE = Tile(2885, 3397, 0)
DUNGEON_LADDER = Tile(2884, 9797, 0)
CAULDRON_DOOR_OUTSIDE = Tile(2888, 9831, 0)
CAULDRON_DOOR_INSIDE = Tile(2890, 9831, 0)
CAULDRON_INSIDE = Tile(2892, 9831, 0)
CAULDRON_ID = 2142
SUIT_OF_ARMOUR_ID = 453
DRUIDIC_RITUAL_HOPS = [
    Record({'stand': DUNGEON_SURFACE, 'loc_name': 'Ladder', 'op': 'Climb-Down', 'arrive': DUNGEON_LADDER}),
    Record({'stand': DUNGEON_LADDER, 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': Tile(2884, 3397, 0)}),
]
# All 4 NPCs have a guaranteed raw-meat drop; the order is one continuous route from Falador through Lumbridge.
RITUAL_MEATS = [
    Record({'raw': 'Raw bear meat', 'enchanted': 'Enchanted bear', 'npc': 'Bear', 'npc_id': 105, 'anchor': Tile(3159, 3233, 0)}),
    Record({'raw': 'Raw rat meat', 'enchanted': 'Enchanted rat', 'npc': 'Giant rat', 'npc_id': 87, 'anchor': Tile(3206, 3175, 0)}),
    Record({'raw': 'Raw chicken', 'enchanted': 'Enchanted chicken', 'npc': 'Chicken', 'npc_id': 41, 'anchor': Tile(3228, 3298, 0)}),
    Record({'raw': 'Raw beef', 'enchanted': 'Enchanted beef', 'npc': 'Cow', 'npc_id': 81, 'anchor': Tile(3243, 3295, 0)}),
]
KEEP_ITEMS = []
for meat in RITUAL_MEATS:
    KEEP_ITEMS.extend([meat.raw.lower(), meat.enchanted.lower()])


def druidic_ritual_area(tile):
    if not tile:
        return 'unknown'
    if tile.x >= 2875 and tile.x <= 2950 and tile.z >= 9785 and tile.z <= 9865:
        return 'dungeon'
    return 'mainland'


def held(snap, name):
    return snap.inv.get(name.lower(), 0) > 0


def banked(snap, name):
    return (snap.bank or {}).get(name.lower(), 0)


def held_form(snap, meat):
    return held(snap, meat.raw) or held(snap, meat.enchanted)


def acquisition_space(snap, slots):
    if snap.free_slots is None or snap.free_slots >= slots:
        return None
    has_spillover = any([not (name in KEEP_ITEMS) for name in snap.inv])
    return Record({
        'kind': 'deposit',
        'keep': (KEEP_ITEMS if has_spillover else []),
        'bank': FALADOR_WEST_BANK,
        'exact_keep': True,
    })


def take_meat_drop(meat):
    drop = ground_items.query().name(meat.raw).within(15).nearest()
    if not drop or not (drop.interact('Take')):
        return False
    _result2 = yield from execution.delay_until(lambda: inventory.contains(meat.raw), 8000)
    return _result2


def wait_with_upkeep(expect, timeout_ms):
    deadline = _core.step_time() + timeout_ms
    while not expect():
        if _core.step_time() >= deadline:
            return False
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return True


def hunt_meat(meat, log):
    if inventory.contains(meat.raw) or inventory.contains(meat.enchanted):
        return True
    _w3 = yield from take_meat_drop(meat)
    if _w3:
        return True
    _w4 = yield from traversal.walk_resilient(meat.anchor, radius=7, attempts=3, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    _w5 = yield from take_meat_drop(meat)
    if _w5:
        return True
    if game.in_combat():
        yield from wait_with_upkeep(lambda: not game.in_combat(), 120000)
        _result6 = yield from take_meat_drop(meat)
        return _result6
    target = npcs.query().where(lambda n: n.id == meat.npc_id and not n.in_combat and not n.targets_another_player()).action('Attack').within(15).nearest()
    if not target:
        log(f'waiting for an available {meat.npc} at the guaranteed {meat.raw} source')
        yield from execution.delay_ticks(2)
        return False
    game.set_combat_style('strength')
    log(f'attacking {meat.npc} for {meat.raw}')
    if not (target.interact('Attack')):
        return False
    yield from wait_with_upkeep(lambda: ground_items.query().name(meat.raw).within(15).nearest() is not None or not target.valid(), 120000)
    _result7 = yield from take_meat_drop(meat)
    return _result7


def in_cauldron_room():
    tile = game.tile()
    return tile is not None and tile.x >= 2890 and tile.x <= 2896 and tile.z >= 9827 and tile.z <= 9835


def fight_living_suit(log):
    suit = npcs.query().where(lambda n: n.id == SUIT_OF_ARMOUR_ID).action('Attack').within(10).nearest()
    if not suit:
        return False
    if not game.in_combat():
        if not (suit.interact('Attack')):
            log('could not attack the animated Suit of armour — yielding safely')
            return True
        _w8 = yield from execution.delay_until(lambda: game.in_combat() or not suit.valid(), 5000)
        if not (_w8):
            log('the animated Suit of armour did not engage — yielding safely')
            return True
    log('defeating the animated Suit of armour guarding the cauldron')
    yield from wait_with_upkeep(lambda: not game.in_combat() or not suit.valid(), 120000)
    return True


def enter_cauldron_room(log):
    if in_cauldron_room():
        return True
    tile = game.tile()
    if not tile or druidic_ritual_area(tile) != 'dungeon':
        _result9 = yield from walk_with_hops(CAULDRON_DOOR_OUTSIDE, 1, DRUIDIC_RITUAL_HOPS, log)
        return False
    if CAULDRON_DOOR_OUTSIDE.distance_to(tile) > 2:
        _w10 = yield from traversal.walk_resilient(CAULDRON_DOOR_OUTSIDE, radius=1, attempts=3, timeout_ms=120000, log=log)
        if not (_w10):
            return False
    _w11 = yield from fight_living_suit(log)
    if _w11:
        return False
    door = locs.query().name('Prison door').action('Open').within(5).nearest()
    if door:
        log('opening the Prison door guarding the Cauldron of Thunder')
        if not (door.interact('Open')):
            return False
        yield from execution.delay_until(lambda: in_cauldron_room() or npcs.query().where(lambda n: n.id == SUIT_OF_ARMOUR_ID).within(10).nearest() is not None or locs.query().name('Prison door').action('Open').within(5).nearest() is None, 8000)
        if npcs.query().where(lambda n: n.id == SUIT_OF_ARMOUR_ID).within(10).nearest() is not None:
            return False
        if locs.query().name('Prison door').action('Open').within(5).nearest() is not None:
            return False
        # Why: the double-door script first moves an outside player onto the threshold, and the open leaf closes 3 server ticks later.
        yield from direct_navigator.walk_to(CAULDRON_DOOR_INSIDE, 0, 3000)
        return in_cauldron_room()
    _result12 = yield from traversal.walk_resilient(CAULDRON_INSIDE, radius=1, attempts=3, timeout_ms=60000, log=log)
    return _result12


def dip_meat(meat, log):
    if inventory.contains(meat.enchanted):
        return True
    if not inventory.contains(meat.raw):
        return False
    _w13 = yield from enter_cauldron_room(log)
    if not (_w13):
        return False
    cauldron = locs.query().where(lambda loc: loc.id == CAULDRON_ID).within(6).nearest()
    raw = inventory.first(meat.raw)
    if not cauldron or not raw:
        log(f'could not find {meat.raw} or the Cauldron of Thunder in its room')
        return False
    raw_before = inventory.count(meat.raw)
    enchanted_before = inventory.count(meat.enchanted)
    log(f'dipping {meat.raw} into the Cauldron of Thunder')
    if not (raw.use_on(cauldron)):
        return False
    _result14 = yield from execution.delay_until(lambda: inventory.count(meat.raw) < raw_before and inventory.count(meat.enchanted) > enchanted_before, 10000)
    return _result14


def leave_dungeon(log):
    tile = game.tile()
    if not tile or druidic_ritual_area(tile) != 'dungeon':
        return True
    _result15 = yield from walk_with_hops(DUNGEON_SURFACE, 2, DRUIDIC_RITUAL_HOPS, log)
    return _result15


def stage_two(snap):
    all_enchanted_held = all([held(snap, meat.enchanted) for meat in RITUAL_MEATS])
    if all_enchanted_held:
        return Record({'kind': 'talk', 'stop': SANFEW})
    missing_held = [meat for meat in RITUAL_MEATS if not held_form(snap, meat)]
    raw_held = ([meat for meat in RITUAL_MEATS if held(snap, meat.raw)] or [None])[0]
    area = druidic_ritual_area(snap.tile)
    if area == 'dungeon':
        if len(missing_held) > 0:
            return Record({
                'kind': 'custom',
                'name': 'leave the dungeon to recover missing ritual meat',
                'run': leave_dungeon,
            })
        if raw_held:
            return Record({
                'kind': 'custom',
                'name': f'dip {raw_held.raw} in the Cauldron of Thunder',
                'run': lambda log: dip_meat(raw_held, log),
            })
    if len(missing_held) > 0:
        if not snap.bank_known:
            return Record({'kind': 'scan_bank', 'bank': FALADOR_WEST_BANK})
        withdraw = []
        for meat in missing_held:
            if banked(snap, meat.enchanted) > 0:
                withdraw.append({'name': meat.enchanted, 'qty': 1})
            elif banked(snap, meat.raw) > 0:
                withdraw.append({'name': meat.raw, 'qty': 1})
        if len(withdraw) > 0:
            space = acquisition_space(snap, len(withdraw))
            return (space if space is not None else Record({'kind': 'withdraw', 'items': withdraw, 'bank': FALADOR_WEST_BANK}))
        space = acquisition_space(snap, 1)
        meat = missing_held[0]
        return (space if space is not None else Record({'kind': 'custom', 'name': f'hunt {meat.npc} for {meat.raw}', 'run': lambda log: hunt_meat(meat, log)}))
    if raw_held:
        return Record({
            'kind': 'custom',
            'name': f'dip {raw_held.raw} in the Cauldron of Thunder',
            'run': lambda log: dip_meat(raw_held, log),
        })
    return Record({'kind': 'wait', 'reason': 'ritual meat state is incomplete'})


def decide(snap):
    if snap.journal == 'complete' or ((snap.stage if snap.stage is not None else 0)) >= DRUIDIC_RITUAL_STAGE.COMPLETE:
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.stage is None:
        return Record({'kind': 'wait', 'reason': 'Druidic Ritual stage unavailable'})
    if snap.stage == DRUIDIC_RITUAL_STAGE.NOT_STARTED:
        return Record({'kind': 'talk', 'stop': KAQEMEEX})
    if snap.stage == DRUIDIC_RITUAL_STAGE.STARTED:
        return Record({'kind': 'talk', 'stop': SANFEW})
    if snap.stage == DRUIDIC_RITUAL_STAGE.SPOKEN_TO_SANFEW:
        return stage_two(snap)
    if snap.stage == DRUIDIC_RITUAL_STAGE.GIVEN_INGREDIENTS:
        return Record({'kind': 'talk', 'stop': KAQEMEEX})
    return Record({'kind': 'wait', 'reason': f'unrecognized Druidic Ritual stage {snap.stage}'})


druidicritual = QuestModule(
    record=quest_record('druid'),
    hops=DRUIDIC_RITUAL_HOPS,
    bank=FALADOR_WEST_BANK,
    grind=['Bear', 'Giant rat', 'Chicken', 'Cow', 'Suit of armour'],
    tools=KEEP_ITEMS,
    owns_inventory=True,
    read_stage=read_druidic_ritual_stage,
    decide=decide,
)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/eel.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.heroquest.areas import GERRANT, HERO_ID, HERO_LOC, HERO_NAMED, HERO_NPC, HERO_SHOP, HERO_TILE, VELRAK, in_deep_dungeon, in_velrak_cell
from rs2004.quests.defs.heroquest.state import anywhere, banked_id, food_name, held_food, held_id, live_item
from rs2004.quests.defs.trollstronghold.combat import fight
from rs2004.quests.exec.legs import combine_by_id, talk_until
from rs2004.quests.exec.prompts import cross_teleport_door
from rs2004.traversal import traversal

__all__ = ['identify_harralander', 'farm_harralander', 'kill_jailer', 'free_velrak', 'leave_deep_dungeon', 'fish_lava_eel', 'cook_lava_eel', 'ask_gerrant_for_slime', 'eel_step']

BAIT_TARGET = 60
DRUID_FOOD = 8
DRUID_MS = 600000
FISH_MS = 300000
RANGE_MS = 30000
JAILER_TICKS = 300


def withdraw(name, qty, id):
    return Record({'kind': 'withdraw', 'items': [{'name': name, 'qty': qty, 'id': id}]})


def identify_harralander(log):
    """Every unidentified herb is called Herb, so the pack is read by id and the Identify is clicked on it."""
    if inventory.count_by_id(HERO_ID.HARRALANDER) > 0:
        return True
    herb = live_item(HERO_ID.UNID_HARRALANDER)
    if not herb:
        log('no unidentified harralander in the pack')
        return False
    if not (herb.interact('Identify')):
        return False
    _result1 = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.HARRALANDER) > 0, 6000)
    return _result1


def druid():
    return npcs.query().where(lambda n: n.id == HERO_NPC.CHAOS_DRUID).nearest()


# Why: nothing sells harralander and it has no ground spawn, so the only source is the chaos druid herb table: 46 in 128 for a herb, 14 in 128 of that table for this one.
def farm_harralander(log):
    """Kill chaos druids in the Taverley dungeon until one drops an unidentified harralander."""

    def done():
        return inventory.count_by_id(HERO_ID.UNID_HARRALANDER) > 0 or inventory.count_by_id(HERO_ID.HARRALANDER) > 0

    if done():
        return True
    _w2 = yield from traversal.walk_resilient(HERO_TILE.CHAOS_DRUIDS, radius=4, attempts=3, timeout_ms=300000, log=log)
    if not (_w2):
        return False
    deadline = _core.step_time() + DRUID_MS
    kills = 0
    attacking = -1
    while _core.step_time() < deadline and not done():
        if event_signal.pending():
            log('herb farm: yielding to a random event')
            return False
        # Why: the herb is the work, every other drop is left where it falls.
        herb = ground_items.query().where(lambda g: g.id == HERO_ID.UNID_HARRALANDER).within(8).nearest()
        if herb:
            if herb.interact('Take'):
                yield from execution.delay_until(done, 6000)
            continue
        yield from sustain.run()
        target = druid()
        if not target:
            yield from execution.delay_ticks(2)
            continue
        if target.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if target.interact('Attack'):
            attacking = target.index
            kills += 1
        yield from execution.delay_ticks(1)
    if not done():
        log(f'no harralander after {round(DRUID_MS / 60000)} minutes of chaos druids ({kills} engagements)')
        return False
    log(f'harralander dropped after {kills} chaos druid engagements')
    return True


# Why: `jail_doors.rs2` answers Open with "This <name> is locked" outside and opens only for an oplocu with the right key: jail key for Velrak's cell, dusty key for the deep dungeon, neither consumed.
def kill_jailer(log):
    """Kill the Jailer and take the jail key he drops."""
    if inventory.count_by_id(HERO_ID.JAIL_KEY) > 0:
        return True
    _w3 = yield from traversal.walk_resilient(HERO_TILE.JAILER, radius=3, attempts=3, timeout_ms=300000, log=log)
    if not (_w3):
        return False

    def key():
        return ground_items.query().where(lambda g: g.id == HERO_ID.JAIL_KEY).within(10).nearest()

    def jailer():
        return npcs.query().where(lambda n: n.id == HERO_NPC.JAILER).nearest()

    _w4 = yield from fight(Record({
        'what': 'Jailer',
        'target': jailer,
        'won': lambda: key() is not None,
        'protect': 'melee',
        'guard': JAILER_TICKS,
    }), log)
    if not (_w4):
        return False
    # Why: the jail key lasts 100 ticks on the floor where every other drop lasts 200.
    drop = key()
    if not drop or not drop.interact('Take'):
        log('the Jailer is down but the jail key is not on the floor')
        return False
    _result7 = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.JAIL_KEY) > 0, 8000)
    return _result7


def cross_jail_door(entering, log):
    return cross_teleport_door(Record({
        'id': HERO_LOC.JAIL_DOOR,
        'stand': (HERO_TILE.JAIL_DOOR if entering else HERO_TILE.JAIL_DOOR_INNER),
        'is_far': lambda: entering == in_velrak_cell(game.tile()),
        'use_item': (HERO_ID.JAIL_KEY if entering else None),
        'stand_radius': 0,
        'log': log,
    }))


def free_velrak(log):
    """Unlock the cell, take Velrak's key, and come back out."""
    if inventory.count_by_id(HERO_ID.DUSTY_KEY) > 0:
        _result8 = yield from cross_jail_door(False, log)
        return _result8
    _w9 = yield from cross_jail_door(True, log)
    if not (_w9):
        return False
    _w10 = yield from talk_until(VELRAK, VELRAK.prefer, lambda: inventory.count_by_id(HERO_ID.DUSTY_KEY) > 0, log, 60000)
    if not (_w10):
        return False
    _result11 = yield from cross_jail_door(False, log)
    return _result11


def cross_deep_gate(entering, log):
    return cross_teleport_door(Record({
        'id': HERO_LOC.DEEP_GATE,
        'name': 'Gate',
        'stand': (HERO_TILE.DEEP_GATE if entering else HERO_TILE.DEEP_GATE_INNER),
        'is_far': lambda: entering == in_deep_dungeon(game.tile()),
        'use_item': (HERO_ID.DUSTY_KEY if entering else None),
        'stand_radius': 0,
        'log': log,
    }))


def leave_deep_dungeon(log):
    """Leave the deep dungeon, which opens from the inside without the key."""
    return cross_deep_gate(False, log)


# Why: the deep dungeon is a sealed pocket the navigator has no edge into, so a leg that ends inside strands every later bank, shop and range walk. This one enters, fishes and leaves in one step.
def fish_lava_eel(log):
    """The lava spots burn every other rod, net and harpoon, and refuse without bait."""
    if inventory.count_by_id(HERO_ID.RAW_LAVA_EEL) > 0:
        _result12 = yield from leave_deep_dungeon(log)
        return _result12
    _w13 = yield from cross_deep_gate(True, log)
    if not (_w13):
        return False
    caught = yield from fish_inside(log)
    left = yield from leave_deep_dungeon(log)
    return caught and left


def fish_inside(log):
    _w14 = yield from traversal.walk_resilient(HERO_TILE.LAVA_FISH, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w14):
        return False
    deadline = _core.step_time() + FISH_MS
    while _core.step_time() < deadline and inventory.count_by_id(HERO_ID.RAW_LAVA_EEL) == 0:
        if event_signal.pending():
            log('lava eel: yielding to a random event')
            return False
        if inventory.count_by_id(HERO_ID.FISHING_BAIT) == 0:
            log('out of fishing bait at the lava spot')
            return False
        spot = npcs.query().where(lambda n: n.id == HERO_NPC.LAVA_FISH).within(6).nearest()
        if not spot:
            log('no lava Fishing spot within six tiles')
            return False
        spot.interact('Bait')
        yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.RAW_LAVA_EEL) > 0, 20000)
    return inventory.count_by_id(HERO_ID.RAW_LAVA_EEL) > 0


# Why: the Taverley range sits in a pocket the baked graph has no door into, so Catherby's is the nearest cooking surface the walker can reach from the dungeon ladder.
def cook_lava_eel(log):
    """Cook the eel on the Catherby range, level 53, and it never burns."""
    if inventory.count_by_id(HERO_ID.LAVA_EEL) > 0:
        return True
    _w15 = yield from traversal.walk_resilient(HERO_TILE.CATHERBY_RANGE, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w15):
        return False
    raw = live_item(HERO_ID.RAW_LAVA_EEL)
    range_ = locs.query().name('Range').within(6).nearest()
    if not raw or not range_:
        log('no raw lava eel in the pack, or no Range within six tiles of the Catherby stand')
        return False
    if not (raw.use_on(range_)):
        return False
    _result16 = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.LAVA_EEL) > 0, RANGE_MS)
    return _result16


# Why: the slime lands between a `~mesbox` and a `~chatnpc` and a chat-only driver stalls on that modal, so the count in the pack is the only oracle that sees past it.
def ask_gerrant_for_slime(log):
    """Gerrant hands the slime over once, and only while none of slime, oil or oiled rod exists anywhere."""
    return talk_until(GERRANT, GERRANT.prefer, lambda: inventory.count_by_id(HERO_ID.SLIME) > 0, log, 60000)


def key_step(snap):
    """Jailer, jail key, Velrak, dusty key, null once the deep dungeon can be opened."""
    if held_id(snap, HERO_ID.DUSTY_KEY) > 0:
        return None
    if banked_id(snap, HERO_ID.DUSTY_KEY) > 0:
        return withdraw(HERO_NAMED.DUSTY_KEY, 1, HERO_ID.DUSTY_KEY)
    if held_id(snap, HERO_ID.JAIL_KEY) == 0:
        return (withdraw(HERO_NAMED.JAIL_KEY, 1, HERO_ID.JAIL_KEY) if banked_id(snap, HERO_ID.JAIL_KEY) > 0 else Record({'kind': 'custom', 'name': 'kill the Jailer for the jail key', 'run': kill_jailer}))
    return Record({'kind': 'custom', 'name': "free Velrak for the deep dungeon's key", 'run': free_velrak})


def eel_step(snap):
    """Slime, rod, bait, vial, herb, oil, oiled rod, keys, eel, fire. Each branch is a function of what is carried, so a restart anywhere in the chain picks it up where it stopped."""
    if anywhere(snap, HERO_ID.LAVA_EEL) > 0:
        return None
    if held_id(snap, HERO_ID.RAW_LAVA_EEL) > 0:
        return Record({'kind': 'custom', 'name': 'cook the lava eel at Catherby', 'run': cook_lava_eel})
    if banked_id(snap, HERO_ID.RAW_LAVA_EEL) > 0:
        return withdraw(HERO_NAMED.RAW_LAVA_EEL, 1, HERO_ID.RAW_LAVA_EEL)
    if held_id(snap, HERO_ID.OILY_ROD) > 0:
        if held_id(snap, HERO_ID.FISHING_BAIT) == 0:
            return (withdraw(HERO_NAMED.FISHING_BAIT, BAIT_TARGET, HERO_ID.FISHING_BAIT) if banked_id(snap, HERO_ID.FISHING_BAIT) > 0 else Record({
                'kind': 'buy',
                'item': HERO_NAMED.FISHING_BAIT,
                'qty': BAIT_TARGET,
                'shop': HERO_SHOP.GERRANT,
                'est_gp': 2000,
            }))
        _v17 = key_step(snap)
        return (_v17 if _v17 is not None else Record({'kind': 'custom', 'name': 'fish a lava eel in the Taverley dungeon', 'run': fish_lava_eel}))
    if banked_id(snap, HERO_ID.OILY_ROD) > 0:
        return withdraw(HERO_NAMED.OILY_ROD, 1, HERO_ID.OILY_ROD)
    if held_id(snap, HERO_ID.BLAMISH_OIL) > 0:
        if held_id(snap, HERO_ID.FISHING_ROD) > 0:
            return Record({
                'kind': 'custom',
                'name': 'rub the blamish oil into the fishing rod',
                'run': lambda log: combine_by_id(HERO_ID.BLAMISH_OIL, HERO_ID.FISHING_ROD, HERO_ID.OILY_ROD, log),
            })
        return (withdraw(HERO_NAMED.FISHING_ROD, 1, HERO_ID.FISHING_ROD) if banked_id(snap, HERO_ID.FISHING_ROD) > 0 else Record({'kind': 'buy', 'item': HERO_NAMED.FISHING_ROD, 'qty': 1, 'shop': HERO_SHOP.GERRANT, 'est_gp': 200}))
    if banked_id(snap, HERO_ID.BLAMISH_OIL) > 0:
        return withdraw(HERO_NAMED.BLAMISH_OIL, 1, HERO_ID.BLAMISH_OIL)
    if held_id(snap, HERO_ID.HARRALANDER_VIAL) > 0:
        if held_id(snap, HERO_ID.SLIME) > 0:
            return Record({
                'kind': 'custom',
                'name': 'mix the slime into the harralander potion',
                'run': lambda log: combine_by_id(HERO_ID.SLIME, HERO_ID.HARRALANDER_VIAL, HERO_ID.BLAMISH_OIL, log),
            })
        return (withdraw(HERO_NAMED.SLIME, 1, HERO_ID.SLIME) if banked_id(snap, HERO_ID.SLIME) > 0 else Record({'kind': 'custom', 'name': 'ask Gerrant for a jar of blamish slime', 'run': ask_gerrant_for_slime}))
    if banked_id(snap, HERO_ID.HARRALANDER_VIAL) > 0:
        return withdraw(HERO_NAMED.HARRALANDER_VIAL, 1, HERO_ID.HARRALANDER_VIAL)
    if held_id(snap, HERO_ID.HARRALANDER) > 0:
        if held_id(snap, HERO_ID.VIAL_WATER) > 0:
            return Record({
                'kind': 'custom',
                'name': 'mix the harralander into the vial of water',
                'run': lambda log: combine_by_id(HERO_ID.HARRALANDER, HERO_ID.VIAL_WATER, HERO_ID.HARRALANDER_VIAL, log),
            })
        return (withdraw(HERO_NAMED.VIAL_WATER, 1, HERO_ID.VIAL_WATER) if banked_id(snap, HERO_ID.VIAL_WATER) > 0 else Record({'kind': 'buy', 'item': HERO_NAMED.VIAL_WATER, 'qty': 1, 'shop': HERO_SHOP.AEMAD, 'est_gp': 200}))
    if banked_id(snap, HERO_ID.HARRALANDER) > 0:
        return withdraw(HERO_NAMED.HARRALANDER, 1, HERO_ID.HARRALANDER)
    if held_id(snap, HERO_ID.UNID_HARRALANDER) > 0:
        return Record({'kind': 'custom', 'name': 'identify the harralander', 'run': identify_harralander})
    if banked_id(snap, HERO_ID.UNID_HARRALANDER) > 0:
        return withdraw(HERO_NAMED.UNID_HERB, 1, HERO_ID.UNID_HARRALANDER)
    if held_food(snap) < DRUID_FOOD:
        return Record({'kind': 'withdraw', 'items': [{'name': food_name(), 'qty': DRUID_FOOD * 2}]})
    return Record({'kind': 'custom', 'name': 'farm chaos druids for a harralander', 'run': farm_harralander})

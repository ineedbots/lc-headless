"""Ported from rs2b0t's src/bot/api/ai/quests/defs/priestperil.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.places import in_ess_mine
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.tabs import quests
from rs2004.quests.exec.primitives import drive_dialog, goto_npc, is_underground, talk_through, walk_with_hops
from rs2004.quests.exec.steps import execute_step, open_bank_leg
from rs2004.quests.exec.prompts import settle_scene
from rs2004.quests.data import QUESTS
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['decide', 'priestperil']

GOLDEN_KEY_ID = 2944
IRON_KEY_ID = 2945
MURKY_ID = 2953
BLESSED_ID = 2954
MONK3_NPC_ID = 1046
ROALD = Record({'npc': 'King Roald', 'anchor': Tile(3222, 3476, 0), 'leash': 6, 'prefer': ['Sure.']})
DREZEL_CELL = Record({'npc': 'Drezel', 'anchor': Tile(3416, 3489, 2), 'leash': 3, 'prefer': []})
DREZEL_MAUS = Record({'npc': 'Drezel', 'anchor': Tile(3439, 9895, 0), 'leash': 4, 'prefer': []})
TEMPLE_DOOR_OUT = Tile(3406, 3488, 0)
TEMPLE_LOBBY = Tile(3412, 3487, 0)
DOG_TILE = Tile(3405, 9902, 0)
GATE1 = Tile(3405, 9895, 0)
GATE2 = Tile(3431, 9897, 0)
WELL_STAND = Tile(3423, 9889, 0)
CELL_DOOR = Tile(3415, 3489, 2)
CELL_DOOR_STAND = Tile(3414, 3489, 2)
COFFIN = Tile(3413, 3486, 2)
AUBURY_TILE = Tile(3253, 3402, 0)
VARROCK_EAST_BANK = Tile(3253, 3420, 0)
VARROCK_GENERAL = Record({'npc': 'Shop keeper', 'anchor': Tile(3218, 3414, 0)})
MONUMENTS = [
    Tile(3428, 9890, 0),
    Tile(3416, 9890, 0),
    Tile(3423, 9895, 0),
    Tile(3423, 9884, 0),
    Tile(3427, 9894, 0),
    Tile(3427, 9885, 0),
    Tile(3418, 9894, 0),
]
HOPS = [
    Record({
    'stand': Tile(3405, 3506, 0),
    'loc_name': 'Trapdoor',
    'op': 'Climb-down',
    'open': 'Open',
    'arrive': Tile(3405, 9907, 0),
}),
    Record({'stand': Tile(3405, 9907, 0), 'loc_name': 'Ladder', 'op': 'Climb-up', 'arrive': Tile(3405, 3507, 0)}),
]
KNOCK_PREFER = ['Roald sent me to check on Drezel.', 'Sure.']
CELL_STORY_PREFER = ['Tell me anyway.', 'Yes.']
QUEST_NAME = 'Priest in Peril'
ESSENCE_NEEDED = 50


def has(snap, name):
    return ((snap.inv.get(name) if snap.inv.get(name) is not None else 0)) > 0


def held_id(id):
    return any([i.id == id for i in inventory.items()])


def free_slots():
    return 28 - len(inventory.items())


def journal_complete():
    return quests.status(QUEST_NAME) == 'complete'


def walk_to(dest, radius, log):
    _result1 = yield from walk_with_hops(dest, radius, HOPS, log)
    return _result1


def reach_and_talk(stop, log):
    _w2 = yield from walk_to(stop.anchor, 2, log)
    if not (_w2):
        return False
    _result3 = yield from talk_through(stop.npc, stop.prefer, log)
    return _result3


def try_open(name, near, log):
    def closed():
        target = near
        return locs.query().name(name).action('Open').where(lambda l: l.tile().distance_to(target) <= 2).nearest()

    here = game.tile()
    if here and here.level == near.level and near.distance_to(here) <= 10 and closed() is None:
        return True
    _w4 = yield from walk_to(near, 3, log)
    if not (_w4):
        return False
    leaf = closed()
    if not leaf:
        return True
    if not (leaf.interact('Open')):
        return False
    _result5 = yield from execution.delay_until(lambda: closed() is None, 4000)
    return _result5


def inside_temple(t):
    if t.level >= 1:
        return True
    return t.x >= 3409 and t.x <= 3418 and t.z >= 3483 and t.z <= 3493


def enter_temple(log):
    here = game.tile()
    if here and inside_temple(here):
        return True
    _w6 = yield from walk_to(TEMPLE_DOOR_OUT, 1, log)
    if not (_w6):
        return False
    leaf = locs.query().name('Large door').action('Open').within(4).nearest()
    if not leaf:
        return False
    if not (leaf.interact('Open')):
        return False

    def _fn8():
        t = game.tile()
        return t is not None and inside_temple(t)
    _result7 = yield from execution.delay_until(_fn8, 6000)
    return _result7


def kill_target(npc, name):
    idx = npc.index
    _w9 = npc.interact('Attack')
    if not (_w9):
        return False
    _w10 = yield from execution.delay_until(lambda: game.in_combat(), 5000)
    if not (_w10):
        return False
    deadline = _core.step_time() + 90000
    while _core.step_time() < deadline:
        if not any([n.index == idx and name in (n.name or '').lower() for n in npcs.all()]):
            return True
        yield from sustain.run()
        yield from execution.delay_ticks(1)
    return False


def early_leg(log):
    log('priestperil: early phase — knock, dog, Roald')
    _w12 = yield from walk_to(TEMPLE_DOOR_OUT, 2, log)
    if not (_w12):
        return False
    door = locs.query().name('Large door').action('Knock-at').within(6).nearest()
    if door and (door.interact('Knock-at')):
        _w13 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 5000)
        if _w13:
            log('priestperil: knock dialogue open — driving agree chain')
            yield from drive_dialog(KNOCK_PREFER, log)
    _w14 = yield from walk_to(DOG_TILE, 8, log)
    if not (_w14):
        return False
    yield from settle_scene()
    dog = npcs.query().name('Temple guardian').action('Attack').within(12).nearest()
    if dog:
        log('priestperil: attacking Temple guardian')
        yield from kill_target(dog, 'temple guardian')
    _w15 = yield from goto_npc(ROALD, HOPS, log)
    if not (_w15):
        return False
    log('priestperil: reporting to King Roald')
    yield from talk_through('King Roald', ROALD.prefer, log)
    return False


def cell_story_leg(log):
    _w16 = yield from walk_to(CELL_DOOR_STAND, 2, log)
    if not (_w16):
        return False
    door = locs.query().name('Cell door').action('Talk-through').within(5).nearest()
    if not door:
        log('priestperil: no Cell door offering Talk-through at the cell')
        return False
    if not (door.interact('Talk-through')):
        return False
    _w17 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 5000)
    if not (_w17):
        return False
    _result18 = yield from drive_dialog(CELL_STORY_PREFER, log)
    return _result18


def monk_hunt_leg(log):
    _w19 = yield from walk_to(TEMPLE_LOBBY, 3, log)
    if not (_w19):
        return False
    drop = ground_items.query().name('Golden key').within(16).nearest()
    if drop:
        if not (drop.interact('Take')):
            return False
        yield from execution.delay_until(lambda: held_id(GOLDEN_KEY_ID), 6000)
        return False
    monk = npcs.query().where(lambda n: n.id == MONK3_NPC_ID).action('Attack').within(14).nearest()
    if not monk:
        log('priestperil: no key-dropping Monk of Zamorak (id 1046) in the temple — waiting on respawn')
        yield from execution.delay_ticks(4)
        return False
    log('priestperil: attacking Monk of Zamorak (id 1046) for the golden key')
    yield from kill_target(monk, 'monk of zamorak')
    return False


def spine_leg(log):
    here = game.tile()
    if here is None:
        return False
    if is_underground(here):
        dog = npcs.query().name('Temple guardian').action('Attack').within(20).nearest()
        if dog:
            _w20 = yield from walk_to(DOG_TILE, 6, log)
            if not (_w20):
                return False
            d = npcs.query().name('Temple guardian').action('Attack').within(12).nearest()
            _c21 = d
            if _c21:
                _w22 = yield from kill_target(d, 'temple guardian')
                _c21 = (_w22)
            if _c21:
                _w23 = yield from goto_npc(ROALD, HOPS, log)
                if not (_w23):
                    return False
                yield from talk_through('King Roald', ROALD.prefer, log)
                return False
        _w24 = yield from try_open('Gate', GATE1, log)
        if _w24:
            _w25 = yield from try_open('Gate', GATE2, log)
            if _w25:
                _result26 = yield from essence_leg(log)
                return _result26
        yield from walk_to(TEMPLE_DOOR_OUT, 3, log)
        return False
    _w27 = yield from enter_temple(log)
    if not (_w27):
        log('priestperil: temple door locked (stage < 4) — early phase')
        _result28 = yield from early_leg(log)
        return _result28
    log('priestperil: inside the temple (stage >= 4)')
    _w29 = yield from try_open('Cell door', CELL_DOOR, log)
    if _w29:
        _result30 = yield from water_leg(log)
        return _result30
    _result31 = yield from monk_hunt_leg(log)
    return _result31


def monument_leg(log):
    _w32 = yield from try_open('Gate', GATE1, log)
    if not (_w32):
        _w33 = yield from enter_temple(log)
        if not (_w33):
            return False
        yield from cell_story_leg(log)
        return False
    for t in MONUMENTS:
        if held_id(IRON_KEY_ID):
            break
        key = ([i for i in inventory.items() if i.id == GOLDEN_KEY_ID] or [None])[0]
        if not key:
            return False
        _w34 = yield from walk_to(t, 2, log)
        if not (_w34):
            return False
        monument = locs.query().name('Monument').where(lambda l: l.tile().distance_to(t) <= 2).nearest()
        if not monument:
            log(f'priestperil: no Monument at ({t.x},{t.z})')
            continue
        if not (key.use_on(monument)):
            continue
        yield from execution.delay_ticks(3)
    if held_id(IRON_KEY_ID):
        log('priestperil: iron key obtained')
    else:
        log('priestperil: golden key fit NO monument — iron key already claimed and lost?')
    return False


def unlock_leg(log):
    _w35 = yield from enter_temple(log)
    if not (_w35):
        return False
    _w36 = yield from walk_to(CELL_DOOR_STAND, 2, log)
    if not (_w36):
        return False
    door = locs.query().name('Cell door').where(lambda l: l.tile().level == 2 and l.tile().distance_to(CELL_DOOR) <= 2).nearest()
    key = ([i for i in inventory.items() if i.id == IRON_KEY_ID] or [None])[0]
    if not door or not key:
        return False
    if not (key.use_on(door)):
        return False
    yield from execution.delay_until(lambda: not held_id(IRON_KEY_ID), 8000)
    return False


def water_leg(log):
    here = game.tile()
    if here is None:
        return False
    if held_id(BLESSED_ID):
        _w37 = yield from enter_temple(log)
        if not (_w37):
            return False
        _w38 = yield from walk_to(COFFIN, 3, log)
        if not (_w38):
            return False
        coffin = locs.query().name('Coffin').where(lambda l: l.tile().level == 2).within(8).nearest()
        water = ([i for i in inventory.items() if i.id == BLESSED_ID] or [None])[0]
        if not coffin or not water:
            return False
        log('priestperil: water — pouring blessed water on the coffin (stage -> 7)')
        if not (water.use_on(coffin)):
            return False
        yield from execution.delay_until(lambda: not held_id(BLESSED_ID), 8000)
        _w39 = yield from try_open('Cell door', CELL_DOOR, log)
        if not (_w39):
            return False
        log('priestperil: water — telling Drezel the coffin is done (stage -> 8)')
        yield from reach_and_talk(DREZEL_CELL, log)
        return False
    if held_id(MURKY_ID):
        _w40 = yield from enter_temple(log)
        if not (_w40):
            return False
        _w41 = yield from try_open('Cell door', CELL_DOOR, log)
        if not (_w41):
            return False
        _w42 = yield from walk_to(DREZEL_CELL.anchor, 2, log)
        if not (_w42):
            return False
        drezel = npcs.query().name('Drezel').within(8).nearest()
        water = ([i for i in inventory.items() if i.id == MURKY_ID] or [None])[0]
        if not drezel or not water:
            return False
        log('priestperil: water — using murky water on Drezel to bless it')
        if not (water.use_on(drezel)):
            return False
        yield from execution.delay_until(lambda: held_id(BLESSED_ID), 10000)
        return False
    _w43 = yield from enter_temple(log)
    if not (_w43):
        return False
    _w44 = yield from try_open('Cell door', CELL_DOOR, log)
    if not (_w44):
        return False
    log('priestperil: water — talking Drezel (hint at 6, advances 7 -> 8)')
    yield from reach_and_talk(DREZEL_CELL, log)
    _w46 = yield from try_open('Gate', GATE1, log)
    _c45 = (_w46)
    if _c45:
        _w47 = yield from try_open('Gate', GATE2, log)
        _c45 = (_w47)
    if _c45:
        log('priestperil: water done — both gates open, handing to essence')
        _result48 = yield from essence_leg(log)
        return _result48
    if inventory.contains('Bucket'):
        _w49 = yield from try_open('Gate', GATE1, log)
        if not (_w49):
            return False
        log('priestperil: water — filling the Bucket at the Well')
        _w50 = yield from walk_to(WELL_STAND, 1, log)
        if not (_w50):
            return False
        well = locs.query().name('Well').within(6).nearest()
        bucket = inventory.first('Bucket')
        if not well or not bucket:
            log('priestperil: water — no Well/Bucket in reach at the stand')
            return False
        if not (bucket.use_on(well)):
            return False
        yield from execution.delay_until(lambda: held_id(MURKY_ID), 8000)
        return False
    _w51 = yield from execute_step(Record({'kind': 'withdraw', 'items': [{'name': 'Bucket', 'qty': 1}]}), HOPS, log)
    if not (_w51) or not inventory.contains('Bucket'):
        yield from execute_step(Record({'kind': 'buy', 'item': 'Bucket', 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': 15}), HOPS, log)
    return False


def bank_early_essence(log):
    log('priestperil: essence held but a gate is stage-locked — banking it until the essence phase')
    _w52 = yield from walk_to(TEMPLE_DOOR_OUT, 3, log)
    if not (_w52):
        return False
    _w53 = yield from open_bank_leg('priestperil: essence-bank — no known bank', VARROCK_EAST_BANK, log)
    if not (_w53):
        return False
    yield from bank.deposit_all_matching(lambda name, id: name.lower() == 'rune essence', log)
    yield from execution.delay_until(lambda: inventory.count('Rune essence') == 0, 6000)
    return False


def essence_leg(log):
    if journal_complete():
        # Why: the journal reads complete at %priestperil 60 but the Salve barrier wants 61 (@drezel_access_holy_barrier), which only fires once Drezel has no dagger to hand back.
        # Why: talk until he stops reclaiming: once when the dagger is held, twice when it's banked.
        for i in range(2):
            log('priestperil: post-quest Drezel talk (Salve barrier access)')
            _w54 = yield from reach_and_talk(DREZEL_MAUS, log)
            if not (_w54):
                break
            if inventory.contains('Wolfbane'):
                break
        return True
    if inventory.count('Rune essence') > 0:
        _w55 = yield from try_open('Gate', GATE1, log)
        if not (_w55):
            log('priestperil: Gate 1 refused during essence phase — mis-signalled essence in pack')
            _result56 = yield from bank_early_essence(log)
            return _result56
        _w57 = yield from try_open('Gate', GATE2, log)
        if not (_w57):
            log('priestperil: Gate 2 refused during essence phase — mis-signalled essence in pack')
            _result58 = yield from bank_early_essence(log)
            return _result58
        _w59 = yield from walk_to(DREZEL_MAUS.anchor, 2, log)
        if not (_w59):
            return False
        before = inventory.count('Rune essence')
        log(f'priestperil: essence — handing {before} to Drezel')
        yield from talk_through('Drezel', DREZEL_MAUS.prefer, log)
        yield from execution.delay_until(lambda: inventory.count('Rune essence') < before or journal_complete(), 10000)
        if journal_complete():
            yield from execution.delay_ticks(2)
            if inventory.contains('Wolfbane'):
                yield from reach_and_talk(DREZEL_MAUS, log)
            return True
        return False
    _w60 = yield from walk_to(TEMPLE_DOOR_OUT, 3, log)
    if not (_w60):
        return False
    want = min(max(free_slots() - 1, 1), ESSENCE_NEEDED)
    log(f'priestperil: essence — pack empty, withdrawing {want} from Varrock East bank')
    _w61 = yield from execute_step(Record({'kind': 'withdraw', 'items': [{'name': 'Rune essence', 'qty': want}], 'bank': VARROCK_EAST_BANK}), HOPS, log)
    if _w61:
        if inventory.count('Rune essence') > 0:
            return False
    log('priestperil: essence — bank dry, mining the shortfall via Aubury')
    _result62 = yield from mine_essence(log)
    return _result62


def mine_essence(log):
    here = game.tile()
    if here is None:
        return False
    if not in_ess_mine(here.x, here.z):
        if not any([('pickaxe' in (i.name if i.name is not None else '').lower()) for i in inventory.items()]):
            for pick in ['Bronze pickaxe', 'Iron pickaxe', 'Steel pickaxe']:
                yield from execute_step(Record({'kind': 'withdraw', 'items': [{'name': pick, 'qty': 1}], 'bank': VARROCK_EAST_BANK}), HOPS, log)
                if any([('pickaxe' in (i.name if i.name is not None else '').lower()) for i in inventory.items()]):
                    break
            if not any([('pickaxe' in (i.name if i.name is not None else '').lower()) for i in inventory.items()]):
                log('priestperil: no pickaxe held or banked — cannot mine essence (park)')
                return False
        _w63 = yield from walk_to(AUBURY_TILE, 4, log)
        if not (_w63):
            return False
        aubury = npcs.query().name('Aubury').action('Teleport').within(10).nearest()
        if not aubury:
            log('priestperil: no Aubury offering Teleport near his shop')
            return False
        if not (aubury.interact('Teleport')):
            return False

        def _fn64():
            t = game.tile()
            return t is not None and in_ess_mine(t.x, t.z)
        _w65 = yield from execution.delay_until(_fn64, 12000)
        if not (_w65):
            return False
    i = 0
    while i < 40 and free_slots() > 0:
        i += 1
        at = game.tile()
        if at is None or not in_ess_mine(at.x, at.z):
            log('priestperil: essence — left the mine mid-dig (random event?); yielding')
            return False
        rock = locs.query().name('Rune Essence').action('Mine').nearest()
        if not rock:
            yield from execution.delay_ticks(3)
            continue
        if not (rock.interact('Mine')):
            yield from execution.delay_ticks(2)
            continue

        def _fn66():
            if free_slots() == 0:
                return True
            t = game.tile()
            return t is None or not in_ess_mine(t.x, t.z)
        yield from execution.delay_until(_fn66, 30000)
    portal = locs.query().name('Portal').action('Use').nearest()
    if portal:
        portal.interact('Use')

        def _fn67():
            t = game.tile()
            return t is not None and not in_ess_mine(t.x, t.z)
        yield from execution.delay_until(_fn67, 12000)
    else:
        log('priestperil: essence — no Portal to leave the mine; retrying')
    return False


def gather_bucket():
    return Record({'kind': 'buy', 'item': 'Bucket', 'qty': 1, 'shop': VARROCK_GENERAL, 'est_gp': 15})


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    if snap.journal == 'not_started':
        return Record({'kind': 'talk', 'stop': ROALD})
    if has(snap, 'golden key'):
        return Record({'kind': 'custom', 'name': 'monument key swap', 'run': monument_leg})
    if has(snap, 'iron key'):
        return Record({'kind': 'custom', 'name': 'unlock the cell', 'run': unlock_leg})
    if has(snap, 'bucket of water'):
        return Record({'kind': 'custom', 'name': 'water chain', 'run': water_leg})
    if has(snap, 'rune essence'):
        return Record({'kind': 'custom', 'name': 'essence delivery', 'run': essence_leg})
    return Record({'kind': 'custom', 'name': 'locate phase', 'run': spine_leg})


priestperil = QuestModule(**{
    'record': quest_record('priestperil'),
    'bank': Tile(3253, 3420, 0),
    'food': 8,
    'grind': ['temple guardian', 'monk of zamorak'],
    'tools': ['golden key', 'iron key', 'bucket', 'wolfbane', 'rune essence', 'pickaxe', 'coins'],
    'gather': Record({'bucket': gather_bucket}),
    'hops': HOPS,
    'decide': decide,
})

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/doll.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.navigation import reachability
from rs2004.quests.defs.upass.areas import UP_AMULETS, UP_ITEM, UP_LOC, UP_NPC, UP_TILE, count_held, inside_iban_temple
from rs2004.quests.defs.upass.bridge import fight_until_gone, loc_by_id, take_drop, walk_to
from rs2004.quests.defs.upass.supplies import BOW_IDS
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene

__all__ = ['SPENT', 'rub_ashes', 'rub_shadow', 'rub_dove', 'fill_brew', 'burn_tomb', 'kill_kalrag', 'amulets_held', 'kill_demon', 'open_sealed_chest', 'search_cages', 'open_iban_door', 'throw_doll']

def rub_into_doll(element, log):
    """Rub an element into the doll."""
    held = ([item for item in inventory.items() if item.id == element.id] or [None])[0]
    doll = ([item for item in inventory.items() if item.id == UP_ITEM.DOLL.id] or [None])[0]
    if not held or not doll:
        log(f"missing {('the doll' if held else element.name)} to complete the doll")
        return False
    if not (held.use_on(doll)):
        return False
    _result1 = yield from drive_until(lambda: held_id(element.id) == 0, [], log, 20000)
    return _result1


def rub_ashes(log):
    return rub_into_doll(UP_ITEM.ASHES, log)


def rub_shadow(log):
    return rub_into_doll(UP_ITEM.SHADOW, log)


def rub_dove(log):
    return rub_into_doll(UP_ITEM.DOVE, log)


def fill_brew(log):
    """Bucket under the dwarves' brew barrel."""
    if held_id(UP_ITEM.DWARF_BREW.id) > 0:
        return True
    _w2 = yield from walk_to(UP_TILE.BREW_BARREL, 3, log)
    if not (_w2):
        return False
    yield from settle_scene()
    barrel = loc_by_id(UP_LOC.BREW_BARREL, None, 8)
    bucket = ([item for item in inventory.items() if item.id == UP_ITEM.BUCKET.id] or [None])[0]
    if not barrel or not bucket:
        log(f"missing {('an empty bucket' if barrel else 'the brew barrel')}")
        return False
    if not (bucket.use_on(barrel)):
        return False
    _result3 = yield from drive_until(lambda: held_id(UP_ITEM.DWARF_BREW.id) > 0, [], log, 12000)
    return _result3


# Why: the tomb only takes the brew with the doll in hand and only burns once soaked, so the pour and the light are 2 uses of the same loc, in that order.
def burn_tomb(log):
    """Pour the brew over Iban's tomb, then light it, and take the ashes."""
    if held_id(UP_ITEM.ASHES.id) > 0:
        return True
    _w4 = yield from walk_to(UP_TILE.IBAN_TOMB, 3, log)
    if not (_w4):
        return False
    yield from settle_scene()
    if held_id(UP_ITEM.DWARF_BREW.id) > 0:
        _v5 = loc_by_id(UP_LOC.IBAN_TOMB_L, None, 8)
        tomb = (_v5 if _v5 is not None else loc_by_id(UP_LOC.IBAN_TOMB_R, None, 8))
        brew = ([item for item in inventory.items() if item.id == UP_ITEM.DWARF_BREW.id] or [None])[0]
        if not tomb or not brew:
            log('no tomb to pour the brew over')
            return False
        if not (brew.use_on(tomb)):
            return False
        _w6 = yield from drive_until(lambda: held_id(UP_ITEM.DWARF_BREW.id) == 0, [], log, 15000)
        if not (_w6):
            log('the tomb would not take the brew')
            return False
    _v7 = loc_by_id(UP_LOC.IBAN_TOMB_L, None, 8)
    tomb = (_v7 if _v7 is not None else loc_by_id(UP_LOC.IBAN_TOMB_R, None, 8))
    tinderbox = ([item for item in inventory.items() if item.id == UP_ITEM.TINDERBOX.id] or [None])[0]
    if not tomb or not tinderbox:
        log(f"missing {('a tinderbox' if tomb else 'the tomb')} to burn the corpse")
        return False
    if not (tinderbox.use_on(tomb)):
        return False
    _result8 = yield from drive_until(lambda: held_id(UP_ITEM.ASHES.id) > 0, [], log, 20000)
    return _result8


# Why: a dead NPC leaves the scene, so "the target is gone" is the one completion signal that doesn't depend on a drop or a stale journal line.
def _npc_is(id):
    return lambda npc: npc.id == id


def kill_npc(npc_id, near, name, log):
    _w9 = yield from walk_to(near, 5, log)
    if not (_w9):
        return False
    yield from settle_scene()

    def find():
        return npcs.query().where(_npc_is(npc_id)).within(20).nearest()

    if find() is None:
        log(f'no {name} near ({near.x},{near.z}) — already dead this spawn')
        return True
    _w10 = yield from fight_until_gone(find, log)
    if not (_w10):
        return False
    # Why: these all wander, so one absent poll can be "walked out of the query", and a false kill sends the leg looking for a drop that was never made. It has to still be gone a moment later.
    yield from execution.delay_ticks(3)
    if find() is not None:
        log(f'{name} only wandered out of range')
        return False
    return True


def kill_kalrag(log):
    """Kalrag's fluids smear onto the doll on her death, so the doll has to be in the pack."""
    if held_id(UP_ITEM.DOLL.id) == 0:
        log('no doll of Iban in the pack — killing Kalrag now would waste the blood')
        return False
    _result11 = yield from kill_npc(UP_NPC.KALRAG, UP_TILE.KALRAG, 'Kalrag', log)
    return _result11


DEMONS = [
    Record({'npc': UP_NPC.DOOMION, 'amulet': UP_ITEM.AMULET_DOOMION, 'tile': UP_TILE.DOOMION, 'name': 'Doomion'}),
    Record({'npc': UP_NPC.HOLTHION, 'amulet': UP_ITEM.AMULET_HOLTHION, 'tile': UP_TILE.HOLTHION, 'name': 'Holthion'}),
    Record({'npc': UP_NPC.OTHAINIAN, 'amulet': UP_ITEM.AMULET_OTHAINIAN, 'tile': UP_TILE.OTHAINIAN, 'name': 'Othainian'}),
]


def amulets_held(snap):
    return count_held(snap, UP_AMULETS)


def kill_demon(log):
    """Kill whichever demon still owes an amulet, then take it off the floor."""
    owed = ([d for d in DEMONS if held_id(d.amulet.id) == 0] or [None])[0]
    if not owed:
        return True
    _w12 = yield from kill_npc(owed.npc, owed.tile, owed.name, log)
    if not (_w12):
        return False
    taken = yield from take_drop(owed.amulet.id, log)
    if not taken:
        log(f'{owed.name} died but no amulet came to the pack')
    return taken


def open_sealed_chest(log):
    """The 3 amulets unseal the chest that holds Iban's shadow."""
    if held_id(UP_ITEM.SHADOW.id) > 0:
        return True
    _w14 = yield from walk_to(UP_TILE.SEALED_CHEST, 3, log)
    if not (_w14):
        return False
    yield from settle_scene()
    chest = loc_by_id(UP_LOC.SEALED_CHEST, None, 8)
    op = ((chest.actions() if chest is not None else None) or [None])[0]
    if not chest or not op or not (chest.interact(op)):
        log('no sealed chest on the demons platform')
        return False
    _result15 = yield from drive_until(lambda: held_id(UP_ITEM.SHADOW.id) > 0, [], log, 20000)
    return _result15


# Why: the cage is an `aploc` whose script force-walks and returns in silence if you're more than 2 tiles from the loc's coordinate, so a radius of 3 satisfies the walk and fails the script. The approach is tight and the failure quotes the chat.
def search_cages(log):
    """Search the soulless cages for Iban's dove; the gauntlets stop the bite."""
    if held_id(UP_ITEM.DOVE.id) > 0:
        return True
    _w16 = yield from walk_to(UP_TILE.CAGE_DOVE, 1, log)
    if not (_w16):
        return False
    yield from settle_scene()
    cage = loc_by_id(UP_LOC.CAGE_DOVE, None, 8)
    op = ((cage.actions() if cage is not None else None) or [None])[0]
    if not cage or not op:
        at = game.tile()
        log(f'no soulless cage holding the dove within eight of ({(at.x if at is not None else None)},{(at.z if at is not None else None)})')
        return False
    mark = game_messages.mark()
    if not (cage.interact(op)):
        log(f'\'{op}\' would not send at the cage')
        return False
    _w17 = yield from drive_until(lambda: held_id(UP_ITEM.DOVE.id) > 0, [], log, 20000)
    if _w17:
        return True
    at = game.tile()
    said = ' / '.join([t for t in [m.text for m in game_messages.since(mark)] if not t.startswith('get ')][-3:])
    log(f"the cage gave no dove from ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — said: {said or 'nothing'}")
    return False


# Why: the doors only open for the robes of Zamorak and nothing else on. The script counts worn slots and wants 2, so the armour comes off here and goes back on after the throw. The robes drop from Iban disciples: level 13, 20 hitpoints, a dozen on the approach.
# Why: 13 disciples line the approach and `nearest()` can pick one through the temple wall, where the attack sends and nothing happens. Take them by distance but only where a cardinal neighbour is standable, give each a short wait, and say what happened when none dies.
def _slot_is(slot):
    return lambda npc: npc.index == slot


def robe_from_disciple(log):
    """Kill a disciple for both halves of the robe of Zamorak."""

    def dressed():
        return held_id(UP_ITEM.ZAM_TOP.id) > 0 and held_id(UP_ITEM.ZAM_BOTTOM.id) > 0

    if dressed():
        return True
    _w18 = yield from walk_to(UP_TILE.DISCIPLE, 6, log)
    if not (_w18):
        return False
    yield from settle_scene()

    def standable(npc):
        t = npc.tile()
        return any([reachability.can_reach(Tile(t.x + dx, t.z + dz, t.level), adjacent_ok=True, max_steps=600) for dx, dz in [[1, 0], [-1, 0], [0, 1], [0, -1]]])

    tried = []
    for round in range(4):
        if not (not dressed()):
            break
        target = (sorted([_x for _x in npcs.query().where(lambda npc: npc.id == UP_NPC.DISCIPLE).within(20).results() if standable(_x)], key=lambda a: a.distance()) or [None])[0]
        if not target:
            at = game.tile()
            log(f"no Iban disciple in reach of ({(at.x if at is not None else None)},{(at.z if at is not None else None)}) — tried {' '.join(tried) or 'none'}")
            return False
        where = target.tile()
        mark = game_messages.mark()
        # Why: disciples wander, so "no disciple on that tile" is satisfied by one walking away. The server index is the identity that dies.
        slot = target.index

        def gone():
            return npcs.query().where(_slot_is(slot)).nearest() is None

        _c20 = target.interact('Attack')
        if _c20:
            _w21 = yield from drive_until(gone, [], log, 45000)
            _c20 = _w21
        if _c20:
            for robe in [UP_ITEM.ZAM_TOP, UP_ITEM.ZAM_BOTTOM]:
                drop = ground_items.query().where(lambda item: item.id == robe.id).within(10).nearest()
                if drop and drop.interact('Take'):
                    yield from drive_until(lambda: held_id(robe.id) > 0, [], log, 10000)
            tried.append(f'({where.x},{where.z})dead')
            continue
        said = ''.join([t for t in [m.text for m in game_messages.since(mark)] if not t.startswith('get ')][-1:])
        tried.append(f"({where.x},{where.z}){said or 'nothing'}")
    if dressed():
        return True
    log(f"no pair of robes off four disciples — {' | '.join(tried)}")
    return False


# Why: the rope, spade, bucket, bow, arrows and the book from Kardia's chest are all used up by now. The pack reaches the temple with 4 or 5 free slots and the strip needs 6, so the spent kit goes on the floor.
# Why: cheapest to lose first, because Regicide walks the pass again with the bow, arrows, rope and spade, and no shop near Ardougne sells a spade. rs2b0t's order dropped it first, which its recipes hide by seeding one per quest, and a queue parked at "not equipped for Tirannwn". This departs from rs2b0t.
THROW_TRIES = 6
THROW_MS = 12000
SPENT = [UP_ITEM.HISTORY, UP_ITEM.BUCKET, UP_ITEM.ROPE, UP_ITEM.BRONZE_ARROW, UP_ITEM.SHORTBOW, UP_ITEM.SPADE]


def shed_spent_kit(need, log):
    dropped = []
    for spent in SPENT:
        if inventory.free() >= need:
            break
        item = ([i for i in inventory.items() if i.id == spent.id or (spent.id == UP_ITEM.SHORTBOW.id and (i.id in BOW_IDS))] or [None])[0]
        op = ([o for o in (item.actions() if item is not None else []) if ('drop' in o.lower())] or [None])[0]
        if item and op and item.interact(op):
            yield from execution.delay_ticks(1)
            dropped.append(spent.name)
    if len(dropped) > 0:
        log(f"dropped {', '.join(dropped)} to make room for the robes")


def wear_only_robes(log):
    """Strip to the robes: the door counts worn slots, so everything else has to come off first."""
    yield from shed_spent_kit(len(equipment.items()), log)
    for worn in equipment.items():
        name = worn.name
        _c22 = name is not None
        if _c22:
            _w23 = yield from equipment.unequip(name)
            _c22 = not (_w23)
        if _c22:
            log(f'could not take off {name}')
            return False
    for robe in [UP_ITEM.ZAM_TOP, UP_ITEM.ZAM_BOTTOM]:
        item = ([i for i in inventory.items() if i.id == robe.id] or [None])[0]
        op = ([o for o in (item.actions() if item is not None else []) if ('wear' in o.lower() or 'wield' in o.lower() or 'equip' in o.lower())] or [None])[0]
        if not item or not op or not (item.interact(op)):
            log(f'the {robe.name} would not go on')
            return False
        yield from execution.delay_ticks(2)
    return len(equipment.items()) == 2


# Why: opening a door swaps the loc to its open variant and you stay put, so the walk inside is a second step and standing on the temple floor is the only proof.
def open_iban_door(log):
    """Iban's temple doors, and the walk through them."""
    if not inside_iban_temple(game.tile()):
        def robed():
            on = equipment.items()
            return len(on) == 2 and all([i.id == UP_ITEM.ZAM_TOP.id or i.id == UP_ITEM.ZAM_BOTTOM.id for i in on])

        _c24 = not robed()
        if _c24:
            _w26 = yield from robe_from_disciple(log)
            _c25 = _w26
            if _c25:
                _w27 = yield from wear_only_robes(log)
                _c25 = _w27
            _c24 = not (_c25)
        if _c24:
            return False
        _w28 = yield from walk_to(UP_TILE.IBAN_DOOR, 3, log)
        if not (_w28):
            return False
        yield from settle_scene()
        _v29 = loc_by_id(UP_LOC.IBAN_DOOR_L, None, 8)
        shut = (_v29 if _v29 is not None else loc_by_id(UP_LOC.IBAN_DOOR_R, None, 8))
        op = ((shut.actions() if shut is not None else None) or [None])[0]
        if shut and op:
            if not (shut.interact(op)):
                log("the doors on Iban's temple would not open")
                return False
            # Why: the script force-moves you a tile west as it opens, so the door is the entry. There's no walk after: the pack has no walkable floor in the temple at all, altar and Iban's tile included.
            yield from drive_until(lambda: inside_iban_temple(game.tile()), [], log, 12000)
    if inside_iban_temple(game.tile()):
        return True
    at = game.tile()
    log(f'still outside the temple at ({(at.x if at is not None else None)},{(at.z if at is not None else None)})')
    return False


def throw_doll(log):
    """The doll into the pit of the damned."""
    if not inside_iban_temple(game.tile()):
        at = game.tile()
        log(f'not in the temple to throw the doll — standing at ({(at.x if at is not None else None)},{(at.z if at is not None else None)})')
        return False
    yield from settle_scene()
    # Why: no walk first. The temple floor isn't in the collision pack, so any radius approach reports unreachable from where you stand; a use-on-loc leaves the pathing to the server, which can see the floor.
    altar = loc_by_id(UP_LOC.IBAN_ALTAR, None, 16)
    doll = ([item for item in inventory.items() if item.id == UP_ITEM.DOLL.id] or [None])[0]
    if not altar or not doll:
        log(f"missing {('the doll of Iban' if altar else 'the well of the damned')}")
        return False
    mark = game_messages.mark()
    # Why: Iban kills you within seconds of the doors, and a use sent as the doors' forced move lands comes back "I can't reach that!". One live run then waited on a throw already refused, and died. So a refusal sends it again at once. This departs from rs2b0t.
    for attempt in range(THROW_TRIES):
        refused_at = game_messages.mark()
        if not (doll.use_on(altar)):
            log('the doll would not go on the well')
            return False
        settled = yield from drive_until(lambda: held_id(UP_ITEM.DOLL.id) == 0 or game_messages.saw_since(refused_at, CANT_REACH), [], log, THROW_MS)
        if held_id(UP_ITEM.DOLL.id) == 0:
            return True
        if not settled:
            break
    said = ' / '.join([t for t in [m.text for m in game_messages.since(mark)] if not t.startswith('get ')][-3:])
    log(f"the well kept the doll — said: {said or 'nothing'}")
    return False


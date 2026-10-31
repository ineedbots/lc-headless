"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/trollheim.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.areas import ER_ITEM, ER_LOC, ER_NPC, ER_TILE, THISTLE_SPOTS, banked, held
from rs2004.quests.defs.eadgar.journal import mark_eadgar_freed
from rs2004.quests.defs.eadgar.supplies import AEMAD, scan_bank, source_logs, source_pestle, source_tinderbox, withdraw
from rs2004.quests.defs.trollstronghold import steal_cell_key, unlock_cell
from rs2004.quests.defs.trollstronghold.areas import ITEM as TROLL_ITEM, TILE as TROLL_TILE
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['source_troll_potion', 'free_eadgar', 'hide_parrot']

FIRE_LOC = 2732
VIAL_PRICE = 10
THISTLE_STAND = THISTLE_SPOTS[2]


def inv_by_id(id):
    return ([item for item in inventory.items() if item.id == id] or [None])[0]


def withdraw_by_id(snap, id, name, qty=1):
    return withdraw(snap, [{'name': name, 'id': id, 'qty': qty}])


def source_vial(snap):
    """Bank, then Aemad's counter beside the Ardougne zoo."""
    if held(snap, ER_ITEM.VIAL_WATER) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.VIAL_WATER) > 0:
        return withdraw_by_id(snap, ER_ITEM.VIAL_WATER.id, ER_ITEM.VIAL_WATER.name)
    return Record({'kind': 'buy', 'item': ER_ITEM.VIAL_WATER.name, 'qty': 1, 'shop': AEMAD, 'est_gp': VIAL_PRICE})


def mix_ids(from_id, onto_id, product_id, log):
    if inventory.count_by_id(product_id) > 0:
        return True
    from_ = inv_by_id(from_id)
    onto = inv_by_id(onto_id)
    if not from_ or not onto:
        log(f'mix: missing item {(from_id if not from_ else onto_id)}')
        return False
    if not (from_.use_on(onto)):
        return False
    _result1 = yield from execution.delay_until(lambda: inventory.count_by_id(product_id) > 0, 10000)
    return _result1


# Why: every unfinished potion displays as "Unfinished potion", so this chain is addressed by object id; a name-keyed withdraw pulls the first unf the bank lists.
def source_ranarr_vial(snap):
    """A ranarr potion (unf): banked, or mixed from a banked ranarr weed and a vial."""
    if held(snap, ER_ITEM.RANARR_VIAL) > 0:
        return None
    if not snap.bank_known:
        return scan_bank(snap)
    if banked(snap, ER_ITEM.RANARR_VIAL) > 0:
        return withdraw_by_id(snap, ER_ITEM.RANARR_VIAL.id, ER_ITEM.RANARR_VIAL.name)
    if held(snap, ER_ITEM.RANARR) == 0:
        if banked(snap, ER_ITEM.RANARR) == 0:
            return Record({
                'kind': 'wait',
                'reason': 'no Ranarr weed and no Unfinished potion in the bank — no shop in 2004 sells either',
            })
        return withdraw_by_id(snap, ER_ITEM.RANARR.id, ER_ITEM.RANARR.name)
    _v2 = source_vial(snap)
    return (_v2 if _v2 is not None else Record({
        'kind': 'custom',
        'name': 'mix a ranarr potion (unf)',
        'run': lambda log: mix_ids(ER_ITEM.RANARR.id, ER_ITEM.VIAL_WATER.id, ER_ITEM.RANARR_VIAL.id, log),
    }))


def pick_thistle(log):
    """Pick the Thistle npc, which hops to another of its 5 tiles after every pick."""
    if inventory.count_by_id(ER_ITEM.THISTLE.id) > 0:
        return True
    for attempt in range(20):
        here = game.tile()
        if not here or THISTLE_STAND.distance_to(here) > 14 or here.level != 0:
            _w3 = yield from traversal.walk_resilient(THISTLE_STAND, radius=6, attempts=3, timeout_ms=240000, log=log)
            if not (_w3):
                return False
            yield from settle_scene()
        thistle = npcs.query().name(ER_NPC.THISTLE).action('Pick').nearest()
        if not thistle:
            log('no Troll Thistle in the scene — walking the patch')
            yield from traversal.walk_resilient(THISTLE_SPOTS[attempt % len(THISTLE_SPOTS)], radius=2, attempts=2, log=log)
            continue
        if thistle.interact('Pick'):
            _w4 = yield from execution.delay_until(lambda: inventory.count_by_id(ER_ITEM.THISTLE.id) > 0, 15000)
            if _w4:
                return True
        yield from execution.delay_ticks(2)
    log('could not pick a Troll Thistle')
    return False


# Why: the thistle dries on any `cooking_fire` and the mountain has none, so the quest brings a spare log and a tinderbox and lights one where it stands.
def dry_thistle(log):
    """Dry a picked thistle over a fire, lighting one first when there is none."""
    if inventory.count_by_id(ER_ITEM.DRIED_THISTLE.id) > 0:
        return True
    if inventory.count_by_id(ER_ITEM.THISTLE.id) == 0:
        log('no Troll thistle to dry')
        return False

    def nearby_fire():
        return locs.query().where(lambda loc: loc.id == FIRE_LOC).within(4).nearest()

    fire = nearby_fire()
    # Why: `area_allow_loc_add` refuses a tile another loc sits on and only says so in a game message, so a refusal means stand somewhere else.
    tile = 0
    while not fire and tile < 4:
        tinderbox = inv_by_id(ER_ITEM.TINDERBOX.id)
        logs = inv_by_id(ER_ITEM.LOGS.id)
        if not tinderbox or not logs:
            log('no Tinderbox or no Logs to light a drying fire')
            return False
        if tile > 0:
            here = game.tile()
            if here:
                yield from traversal.walk_resilient(Tile(here.x + 1, here.z + tile, here.level), radius=0, attempts=2, log=log)
        if tinderbox.use_on(logs):
            yield from execution.delay_until(lambda: nearby_fire() is not None, 20000)
        fire = nearby_fire()
        tile += 1
    thistle = inv_by_id(ER_ITEM.THISTLE.id)
    if not fire or not thistle:
        log('the logs never caught — nothing on this patch would take a fire')
        return False
    if not (thistle.use_on(fire)):
        return False
    _result5 = yield from execution.delay_until(lambda: inventory.count_by_id(ER_ITEM.DRIED_THISTLE.id) > 0, 15000)
    return _result5


def source_troll_potion(snap):
    """Thistle to dried to ground to Troll potion. Null once the potion is in the pack."""
    if held(snap, ER_ITEM.TROLL_POTION) > 0:
        return None
    if held(snap, ER_ITEM.GROUND_THISTLE) > 0:
        _v6 = source_ranarr_vial(snap)
        return (_v6 if _v6 is not None else Record({
            'kind': 'custom',
            'name': 'mix the troll truth potion',
            'run': lambda log: mix_ids(ER_ITEM.GROUND_THISTLE.id, ER_ITEM.RANARR_VIAL.id, ER_ITEM.TROLL_POTION.id, log),
        }))
    if held(snap, ER_ITEM.DRIED_THISTLE) > 0:
        _v7 = source_pestle(snap)
        return (_v7 if _v7 is not None else Record({
            'kind': 'custom',
            'name': 'grind the dried thistle',
            'run': lambda log: mix_ids(ER_ITEM.PESTLE.id, ER_ITEM.DRIED_THISTLE.id, ER_ITEM.GROUND_THISTLE.id, log),
        }))
    if held(snap, ER_ITEM.THISTLE) > 0:
        _v8 = source_tinderbox(snap)
        _v9 = (_v8 if _v8 is not None else source_logs(snap, 1))
        return (_v9 if _v9 is not None else Record({'kind': 'custom', 'name': 'dry the thistle over a fire', 'run': dry_thistle}))
    # Why: the thistle only grows on Trollheim and everything that processes it is bought at the bottom of the mountain, so the kit is assembled before the climb.
    _v10 = source_tinderbox(snap)
    _v11 = (_v10 if _v10 is not None else source_logs(snap, 1))
    _v12 = (_v11 if _v11 is not None else source_pestle(snap))
    _v13 = (_v12 if _v12 is not None else source_ranarr_vial(snap))
    return (_v13 if _v13 is not None else Record({'kind': 'custom', 'name': 'pick a Troll Thistle', 'run': pick_thistle}))


EADGAR_CELL_STAND = Tile(2833, 10082, 0)
EADGAR_CELL_DOOR = Tile(2832, 10082, 0)


# Why: Troll Stronghold finishes on Godric alone, so you can arrive with Mad Eadgar still in his cell and the Cave Entrance dropping you into an empty room.
# Why: Berry keeps handing out Cell key 2 for as long as the varbit is false, quest complete or not.
def free_eadgar(log):
    """Open Mad Eadgar's cell so he goes home to his cave."""
    _w14 = yield from traversal.walk_resilient(TROLL_TILE.PRISON_LANDING, radius=4, attempts=3, timeout_ms=300000, log=log)
    if not (_w14):
        return False
    _w15 = yield from steal_cell_key('Berry', TROLL_ITEM.CELL_KEY_2, EADGAR_CELL_STAND, log)
    if not (_w15):
        return False
    _w16 = yield from unlock_cell(TROLL_ITEM.CELL_KEY_2, EADGAR_CELL_DOOR, EADGAR_CELL_STAND, log)
    if not (_w16):
        return False
    mark_eadgar_freed()
    log('Mad Eadgar is free — he walks home to his cave')
    return True


def hide_parrot(log):
    """Hide the Drunk parrot under the torture rack in the troll prison."""
    return use_on_loc(ER_ITEM.DRUNK_PARROT.id, Record({'name': 'Rack', 'near': ER_TILE.RACK, 'id': ER_LOC.RACK}), [], lambda: inventory.count_by_id(ER_ITEM.DRUNK_PARROT.id) == 0, log)

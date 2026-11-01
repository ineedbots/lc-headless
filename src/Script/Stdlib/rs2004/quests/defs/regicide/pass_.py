"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/pass.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.regicide.areas import RG_LOC, RG_TILE, regicide_area
from rs2004.quests.defs.regicide.pockets import climb_out_of_pit, travel_tirannwn
from rs2004.quests.defs.regicide.supplies import usable_bows
from rs2004.quests.defs.upass.area2 import enter_main_cavern
from rs2004.quests.defs.upass.areas import UP_ITEM, UP_LOC, UP_TILE, past_grid_tile, upass_area
from rs2004.quests.defs.upass.bridge import arm_fire_arrow, cross_to_west, enter_cave, get_damp_cloth, make_fire_arrow, shoot_guiderope
from rs2004.quests.defs.upass.grid import cross_grid
from rs2004.quests.defs.upass.pass_ import travel_to
from rs2004.quests.defs.upass.railings import OUT_OF_CAGES, outstanding_crossing, take_next_crossing
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.traversal import traversal

__all__ = ['on_shelf', 'east_of_chasm', 'enter_tirannwn', 'leave_tirannwn']

# Why: Permanent `%ibanmulti` bits retain the quest gates, leaving only physical crossings for the pocket mover.
# Why: the way out at the far end is Iban's temple door: `open_iban_door` grows a branch at `%regicide_quest >= ^regicide_spoken_lathas` that teleports you `loc + (-129, +64)`, into the Well of Voyage room.
# Why: Door angle controls the tunnel landing; the z=9611 pair reaches the first cavern and the z=9665 pair reaches the loose railings.
# Why: The first-cavern shelf has no named pocket, so cross its door directly instead of calling `travelTo`.
UNICORN_TUNNEL_STAND = Tile(2376, 9610, 0)
UNICORN_TUNNEL_DOORS = [Tile(2375, 9611, 0), Tile(2376, 9611, 0)]


# Why: The shelf and orb corridor have overlapping bounds but no connected tiles, so classify the shelf first and use the remaining bands for the corridor.
def on_shelf(tile):
    return tile is not None and (tile.x <= 2379 or tile.z >= 9699)


# Why: The chasm splits disconnected tile sets only within z=9710..9726; an x-only test misclassifies the grid approach.
BRIDGE_EAST_Z = 9710
BRIDGE_EAST_X = 2446
bridge_gear = []


def restore_bridge_gear(log):
    global bridge_gear
    for name in bridge_gear:
        _c1 = not equipment.contains(name)
        if _c1:
            _w2 = yield from equipment.equip(name)
            _c1 = not (_w2)
        if _c1:
            log(f'could not restore {name} after the bridge shot')
    bridge_gear = [name for name in bridge_gear if not equipment.contains(name) and inventory.first(name) is not None]
    return len(bridge_gear) == 0


def east_of_chasm(tile):
    return tile is not None and tile.z >= BRIDGE_EAST_Z and tile.x >= BRIDGE_EAST_X


def held_id(id):
    return len([item for item in inventory.items() if item.id == id])


# Why: Reuse the explicit railing chain; targeting the mud loc has no pocket and sends the free search back north.
def cross_bridge(log):
    """Shoot down and cross the chasm bridge. Why: Its state is temporary and the west-bank lever only crosses east, so every westbound trip needs a new fire arrow."""
    global bridge_gear
    staged = held_id(UP_ITEM.LIT_ARROW.id) + held_id(UP_ITEM.UNLIT_ARROW.id) + held_id(UP_ITEM.DAMP_CLOTH.id)
    _c3 = staged == 0
    if _c3:
        _w4 = yield from get_damp_cloth(log)
        _c3 = not (_w4)
    if _c3:
        log('Koftik would not hand over a damp cloth at the bridge')
        return False
    _w5 = yield from make_fire_arrow(log)
    if not (_w5):
        return False
    bridge_gear = [name for name in [item.name for item in [item for item in equipment.items() if item.slot == 3 or item.slot == 5]] if name is not None]
    crossed = False
    try:
        _w6 = yield from arm_fire_arrow(log, usable_bows(skills.level('ranged')))
        if _w6:
            crossed = yield from shoot_guiderope(log)
    except Exception as e:
        _w7 = yield from restore_bridge_gear(log)
        if not (_w7):
            crossed = False
        raise e
    _w8 = yield from restore_bridge_gear(log)
    if not (_w8):
        crossed = False
    return crossed


def loc_by_id(id, op, within=12):
    base = locs.query().where(lambda loc: loc.id == id)
    return ((base if op is None else base.action(op))).within(within).nearest()


def climb_well(log):
    _w9 = yield from travel_to(UP_TILE.WELL, 3, log)
    if not (_w9):
        return False
    yield from settle_scene()
    well = loc_by_id(UP_LOC.WELL, None, 10)
    op = ((well.actions() if well is not None else None) or [None])[0]
    if not well or not op:
        log('no well in the orb corridor')
        return False
    if not (well.interact(op)):
        return False
    # Why: the well blasts you back out with damage unless all 4 orb bits are set, so the drop into the second cavern is the only signal the descent happened.
    _result10 = yield from drive_until(lambda: upass_area(game.tile()) == 'area2', [], log, 20000)
    return _result10


def open_voyage_door(log):
    """Iban's temple door, which at this quest stage opens onto the Well of Voyage instead."""
    _w11 = yield from travel_to(RG_TILE.IBAN_DOOR, 3, log)
    if not (_w11):
        return False
    yield from settle_scene()
    _v12 = loc_by_id(UP_LOC.IBAN_DOOR_L, None, 8)
    door = (_v12 if _v12 is not None else loc_by_id(UP_LOC.IBAN_DOOR_R, None, 8))
    op = ((door.actions() if door is not None else None) or [None])[0]
    if not door or not op or not (door.interact(op)):
        log("no doors on Iban's temple")
        return False
    _result13 = yield from drive_until(lambda: (((game.tile().x if game.tile() is not None else None) if (game.tile().x if game.tile() is not None else None) is not None else 9999)) < 2100, [], log, 15000)
    return _result13


def climb_voyage_well(log):
    """Down the Well of Voyage, which lands in the temple on the far side of the world."""
    _w14 = yield from traversal.walk_resilient(RG_TILE.WELL_OF_VOYAGE, radius=2, attempts=2, timeout_ms=60000, log=log)
    if not (_w14):
        # Why: the well sits in a sealed room whose door the pack blocks and the temple-door hop lands you on its threshold, so a walk that finds no route means the door is still shut.
        inner = locs.query().name('Door').action('Open').within(8).nearest()
        if not inner or not (inner.interact('Open')):
            log('no way into the Well of Voyage room')
            return False
        yield from settle_scene()
        _w15 = yield from traversal.walk_resilient(RG_TILE.WELL_OF_VOYAGE, radius=2, attempts=2, timeout_ms=60000, log=log)
        if not (_w15):
            return False
    yield from settle_scene()
    well = loc_by_id(RG_LOC.WELL_OF_VOYAGE, 'Climb-down', 10)
    if not well or not (well.interact('Climb-down')):
        log('no Well of Voyage to climb into')
        return False
    _result16 = yield from drive_until(lambda: regicide_area(game.tile()) == 'voyage', [], log, 20000)
    return _result16


def leave_voyage_temple(log):
    """Out of the voyage temple onto the Isafdar forest floor."""
    _w17 = yield from traversal.walk_resilient(RG_TILE.VOYAGE_EXIT, radius=3, attempts=3, timeout_ms=90000, log=log)
    if not (_w17):
        return False
    yield from settle_scene()
    exit = loc_by_id(RG_LOC.TEMPLE_EXIT, 'Exit', 12)
    if not exit or not (exit.interact('Exit')):
        log('no cave exit in the voyage temple')
        return False
    _result18 = yield from drive_until(lambda: regicide_area(game.tile()) == 'tirannwn', [], log, 20000)
    return _result18


def climb_unicorn_tunnel(log):
    """Up the unicorn tunnel from the second cavern onto the paladins' shelf. Why: by the door's own tile: 4 of these doors stand in the cavern and only the pair at z 9611 lands on the shelf, the others send the leg back to the loose railings it came from."""
    _w19 = yield from travel_to(UNICORN_TUNNEL_STAND, 1, log)
    if not (_w19):
        log(f'could not stand at ({UNICORN_TUNNEL_STAND.x},{UNICORN_TUNNEL_STAND.z}) for the unicorn tunnel')
        return False
    yield from settle_scene()
    door = locs.query().where(lambda loc: (loc.id == UP_LOC.UNICORN_DOOR_L or loc.id == UP_LOC.UNICORN_DOOR_R) and any([at.x == loc.tile().x and at.z == loc.tile().z for at in UNICORN_TUNNEL_DOORS])).nearest()
    op = ((door.actions() if door is not None else None) or [None])[0]
    if not door or not op:
        log(f'no unicorn tunnel door at z 9611 from ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)})')
        return False
    if not (door.interact(op)):
        return False
    climbed = yield from drive_until(lambda: on_shelf(game.tile()) and upass_area(game.tile()) == 'area1', [], log, 15000)
    log((f'unicorn tunnel → the shelf at ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)})' if climbed else f'the unicorn tunnel left us at ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)}), not on the shelf'))
    return climbed


def enter_tirannwn(log):
    """One leg of the walk from the mainland to Isafdar. Called until `regicideArea` reads `tirannwn`. Why: every leg is keyed on where you already are, because the pass teleports on failure (a pitfall, the well, Iban's door) and a remembered step would resume in the wrong pocket after any of them."""
    if len(bridge_gear) > 0:
        _result20 = yield from restore_bridge_gear(log)
        return _result20
    here = game.tile()
    area = regicide_area(here)
    if area == 'tirannwn':
        return True
    if area == 'pit':
        _result21 = yield from climb_out_of_pit(log)
        return _result21
    if area == 'voyage':
        _result22 = yield from leave_voyage_temple(log)
        return _result22
    _case23 = upass_area(here)
    if _case23 == 'mainland':
        _result24 = yield from cross_to_west(log)
        return _result24
    elif _case23 == 'westardougne':
        _result25 = yield from enter_cave(log)
        return _result25
    elif _case23 == 'area1':
        if east_of_chasm(here):
            _result26 = yield from cross_bridge(log)
            return _result26
        if not past_grid_tile(here):
            _result27 = yield from cross_grid(log)
            return _result27
        if on_shelf(here):
            _result_shelf = yield from enter_main_cavern(log)
            return _result_shelf
        _result_well = yield from climb_well(log)
        return _result_well
    elif _case23 == 'area2':
        # Why: the paladins' shelf is entered by one loc. Its rim carries 3 ops: the temple doors out, the blood well, and `upass_unicorn_door`, which `p_telejump`s to (2371,9666) from its south face. So the shelf is behind the second cavern, and a leg walked at `PALADINS` asks for a tile in another pocket, where the sweep picks a slave-cage door and "the cage slams shut behind you" leaves it in an 8-tile cell.
        # Why: the well's teleport leaves the old map for a tick or two, where the flood reads every stand as unreachable, no crossing as outstanding, and the fixed chain gives way to a free search through 13 seams. This departs from rs2b0t.
        yield from settle_scene()
        if outstanding_crossing(OUT_OF_CAGES) is None:
            _result_tunnel = yield from climb_unicorn_tunnel(log)
            return _result_tunnel
        _result_cages = yield from take_next_crossing(log, OUT_OF_CAGES)
        return _result_cages
    elif _case23 == 'gridpit':
        _result28 = yield from travel_to(UP_TILE.GRID_APPROACH, 3, log)
        return _result28
    elif _case23 == 'voyage':
        _result29 = yield from climb_voyage_well(log)
        return _result29
    elif _case23 in ['main', 'witch', 'temple', 'dwarves', 'kalrag']:
        _result30 = yield from open_voyage_door(log)
        return _result30
    else:
        log(f'lost on the way to Isafdar at ({(here.x if here is not None else None)},{(here.z if here is not None else None)},{(here.level if here is not None else None)})')
        return False


# Why: the palisade is one seam of the graph the forest is routed by, so `travelTirannwn` walks the crossings out to it, takes the gate, and degrades to a plain resilient walk on the Ardougne side. Walking straight at the gate reports "unreachable" from any pocket in the forest.
def leave_tirannwn(dest, stage, log):
    """Out of Tirannwn through the Arandar palisade, free northbound at any stage."""
    return travel_tirannwn(dest, 3, stage, log)


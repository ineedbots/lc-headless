"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fightarena/legs.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs._items import ITEM_DB
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game, skills
from rs2004.items import equipment, inventory
from rs2004.quests.defs.fightarena.areas import FA_LOC, FA_OBJ, FA_TILE, pocket_of
from rs2004.quests.defs.fightarena.fights import PROTECT_LEVEL, PROTECT_MELEE, run_fight
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.quests.exec.prompts import settle_scene
from rs2004.reach import reach
from rs2004.tabs import prayer
from rs2004.traversal import traversal

__all__ = ['combat_swap', 'search_chest', 'wear_khazard', 'unwearable', 'wear_kit', 'wear_combat', 'enter_building', 'leave_building', 'enter_arena_by_door2', 'enter_arena_by_guard', 'unlock_jeremy', 'talk_by_id', 'talk_and_land', 'fight_with_release', 'flee_arena']

SLOT_BY_ID = {r['id']: r['slot'] for r in ITEM_DB if r.get('slot') is not None}
DISGUISE = set([FA_OBJ.HELMET, FA_OBJ.ARMOUR])


# Why: equipping the Khazard pieces pushes whatever was worn into the pack, so the combat kit is already carried and the swap back needs no bank.
def combat_swap(pack_ids):
    """The pack's own hat and torso ids, hat first."""

    def pick(slot):
        return ([id for id in pack_ids if not (id in DISGUISE) and SLOT_BY_ID.get(id) == slot] or [None])[0]

    return [id for id in [pick('hat'), pick('torso')] if id is not None]


def pack_ids():
    return [item.id for item in inventory.items()]


def held(id):
    return inventory.count_by_id(id) > 0


def wearing(id):
    return any([item.id == id for item in equipment.items()])


def disguised():
    return wearing(FA_OBJ.HELMET) or wearing(FA_OBJ.ARMOUR)


def walk_exactly(tile, log):
    here = game.tile()
    if here and here.level == tile.level and tile.distance_to(here) == 0:
        return True
    _result1 = yield from traversal.walk_resilient(tile, radius=0, attempts=4, timeout_ms=180000, log=log)
    return _result1


def landed_in(pocket, ms):
    _result2 = yield from execution.delay_until(lambda: pocket_of(game.tile()) == pocket, ms)
    return _result2


# Why: `forceapproach=north` means the server silently drops every op from another side, which looks like a missing loc.
def search_chest(log):
    """Open and search the guards' chest for the Khazard disguise."""
    if held(FA_OBJ.HELMET) and held(FA_OBJ.ARMOUR):
        return True
    _w3 = yield from walk_exactly(FA_TILE.CHEST_STAND, log)
    if not (_w3):
        log("could not stand north of the guards' chest")
        return False
    yield from settle_scene()
    shut = locs.query().name(FA_LOC.CHEST).action('Open').within(4).nearest()
    if shut:
        shut.interact('Open')
        yield from execution.delay_ticks(2)
        return False
    open = locs.query().name(FA_LOC.CHEST).action('Search').within(4).nearest()
    if not open:
        log('no Chest to Search from the north stand')
        return False
    if not (open.interact('Search')):
        return False
    _result4 = yield from execution.delay_until(lambda: held(FA_OBJ.HELMET) and held(FA_OBJ.ARMOUR), 8000)
    return _result4


def equip_by_id(id, log):
    item = ([entry for entry in inventory.items() if entry.id == id] or [None])[0]
    if not item:
        return False
    name = (item.name if item.name is not None else str(id))
    _w5 = yield from equipment.equip(name)
    if not (_w5):
        log(f'could not wear {name}')
        return False
    _result6 = yield from execution.delay_until(lambda: wearing(id), 4000)
    return _result6


def wear_khazard(log):
    """Wear the disguise. Whatever it replaces lands in the pack."""
    ok = True
    for id in [FA_OBJ.HELMET, FA_OBJ.ARMOUR]:
        if wearing(id):
            continue
        _w7 = yield from equip_by_id(id, log)
        ok = (_w7) and ok
    return ok


unwearable = set()


# Why: a step per piece pays a task hand-off each, and the engine re-reads the journal between them.
def wear_kit(names, log):
    """Wear a melee kit, shedding whatever the account is not allowed to hold."""
    for name in names:
        if equipment.contains(name):
            continue
        _w8 = yield from equipment.equip(name)
        if not (_w8):
            log(f'cannot wear {name} — level or quest requirement; leaving it behind')
            unwearable.add(name.lower())
        yield from execution.delay_ticks(1)
    return True


def wear_combat(log):
    """Put the account's own head and body back on before a fight."""
    wanted = combat_swap(pack_ids())
    if len(wanted) == 0:
        return True
    for id in wanted:
        yield from equip_by_id(id, log)
    return True


def open_loc_by_id(loc_id, near, log):
    _w9 = yield from walk_exactly(near, log)
    if not (_w9):
        return False
    yield from settle_scene()
    door = locs.query().where(lambda l: l.id == loc_id).action('Open').within(6).nearest()
    if not door:
        log(f'no loc {loc_id} offering Open at ({near.x},{near.z})')
        return False
    return bool(door.interact('Open'))


def enter_building(log):
    """Cross `fightarena_door1` inwards. Needs the disguise and a guard within 5 tiles."""
    if not disguised():
        log('refusing to knock without the Khazard disguise on')
        return False
    _w10 = yield from open_loc_by_id(FA_LOC.DOOR1, FA_TILE.DOOR1_OUTSIDE, log)
    if not (_w10):
        return False
    yield from drive_dialog([], log)
    _result11 = yield from landed_in('building', 12000)
    return _result11


def leave_building(log):
    """Cross `fightarena_door1` outwards. `check_axis` passes from the inside, so nothing is checked."""
    _w12 = yield from open_loc_by_id(FA_LOC.DOOR1, FA_TILE.DOOR1_INSIDE, log)
    if not (_w12):
        return False
    _result13 = yield from landed_in('outside', 12000)
    return _result13


def enter_arena_by_door2(log):
    """Cross `fightarena_door2` into the arena. The guard only allows it at stages 6 and 8."""
    _w14 = yield from open_loc_by_id(FA_LOC.DOOR2, FA_TILE.DOOR2_OUTSIDE, log)
    if not (_w14):
        return False
    yield from drive_dialog([], log)
    _result15 = yield from landed_in('arena', 15000)
    return _result15


# Why: at stages 9 to 11 the guard at door1 escorts the player straight into the arena, which is the only way back in after a death.
def enter_arena_by_guard(log):
    """Knock at `fightarena_door1` from outside and let the guard walk us into the arena."""
    _w16 = yield from open_loc_by_id(FA_LOC.DOOR1, FA_TILE.DOOR1_OUTSIDE, log)
    if not (_w16):
        return False
    yield from drive_dialog([], log)
    _result17 = yield from landed_in('arena', 30000)
    return _result17


def unlock_jeremy(log):
    """Use the cell keys on Jeremy's gate. The server frees him and teleports us into the arena."""
    _w18 = yield from walk_exactly(FA_TILE.JEREMY_DOOR_STAND, log)
    if not (_w18):
        return False
    yield from settle_scene()
    door = locs.query().where(lambda l: l.id == FA_LOC.JEREMY_DOOR).within(6).nearest()
    keys = ([item for item in inventory.items() if item.id == FA_OBJ.KEYS] or [None])[0]
    if not door or not keys:
        log('no Jeremy gate in reach, or no cell keys held')
        return False
    if not (keys.use_on(door)):
        return False
    yield from drive_dialog([], log)
    _result19 = yield from landed_in('arena', 40000)
    return _result19


def npc_with_id(npc_id):
    return npcs.query().where(lambda n: n.id == npc_id)


def beast_loose(npc_id):
    return npcs.query().where(lambda n: n.id == npc_id).action('Attack').within(20).exists()


# Why: `Reach.entityOp` lets the server walk the last stretch, and its 5s window is short for a target 30 tiles across the corridor.
def talk_by_id(npc_id, prefer, log, near=None):
    """Talk to an npc found by id, then drive whatever it opens."""

    def ready():
        return chat_dialog.is_open() or chat_dialog.can_continue()

    def found():
        return npc_with_id(npc_id).within(6).exists()

    _c20 = near and not found()
    if _c20:
        _w21 = yield from traversal.walk_resilient(near, radius=4, attempts=3, timeout_ms=120000, log=log)
        _c20 = not (_w21)
    if _c20:
        log(f'could not walk to ({near.x},{near.z}) for npc {npc_id}')
        return False
    status = yield from reach.entity_op(lambda: npc_with_id(npc_id).nearest(), 'Talk-to', ready, expect_ms=15000, open_when_unreachable=True, what=f'npc {npc_id}', log=log)
    if status != 'done':
        log(f'npc {npc_id} never opened a dialogue')
        return False
    _result22 = yield from drive_dialog(prefer, log)
    return _result22


# Why: `driveDialog` returns at the `if_close` that starts a cutscene, and the next decide would open the quest log on top of 40 ticks of forced movement.
def talk_and_land(npc_id, pocket, ms, log):
    """Talk to an npc whose dialogue ends in a cutscene, and wait out the ride."""
    _w23 = yield from talk_by_id(npc_id, [], log)
    if not (_w23):
        return False
    _w24 = yield from execution.delay_until(lambda: pocket_of(game.tile()) == pocket, ms)
    if _w24:
        return True
    log(f'npc {npc_id} did not put us in the {pocket}')
    return False


# Why: each beast is caged until a script lets it out and only the entry cutscenes do that, so a bot that walked back in after a death asks a Servil.
# Why: swinging at an empty arena burns the fight budget and repeats, which wedges the quest.
def fight_with_release(fight, release_npc_id, log):
    """Make sure the beast is out, asking the Servils if it is not, then fight it."""

    beast_id = fight.npc_id

    def loose():
        return beast_loose(beast_id)

    # Why: a caged beast still renders and offers Attack, so the first pass may only learn it's caged by swinging; either way the Servil lets it out.
    if loose():
        _w26 = yield from run_fight(fight, log)
        _c25 = _w26
    else:
        _c25 = 'unengaged'
    result = _c25
    if result != 'unengaged':
        return result == 'won'
    log(f'{fight.what} is still caged — asking npc {release_npc_id} to bring it on')
    _w27 = yield from talk_by_id(release_npc_id, [], log)
    if not (_w27):
        return False
    _w28 = yield from execution.delay_until(loose, 20000)
    if not (_w28):
        log(f'{fight.what} did not come out after the dialogue')
        return False
    _w29 = yield from run_fight(fight, log)
    return (_w29) == 'won'


FLEE_EAT_AT = 25


# Why: General Khazard is attacking throughout this, and auto-retaliate walks the character back off the route to swing at him.
def flee_arena(log):
    """Leave the arena and the building while Khazard chases."""
    retaliate = game.auto_retaliate_on()
    game.set_auto_retaliate(False)
    try:
        left = yield from run_from_khazard(log)
    except Exception as e:
        yield from stop_fleeing(retaliate)
        raise e
    yield from stop_fleeing(retaliate)
    return left


def stop_fleeing(retaliate):
    game.set_auto_retaliate(retaliate)
    if prayer.active(PROTECT_MELEE):
        yield from prayer.set(PROTECT_MELEE, False)


def run_from_khazard(log):
    if skills.level('prayer') >= PROTECT_LEVEL and prayer.points() > 0 and not prayer.active(PROTECT_MELEE):
        yield from prayer.set(PROTECT_MELEE, True)
    if pocket_of(game.tile()) == 'arena':
        if skills.effective('hitpoints') <= skills.level('hitpoints') - FLEE_EAT_AT:
            yield from sustain.run()
        _w30 = yield from open_loc_by_id(FA_LOC.DOOR2, FA_TILE.DOOR2_INSIDE, log)
        if not (_w30):
            return False
        _w31 = yield from landed_in('building', 15000)
        if not (_w31):
            return False
        log('out of the arena')
    if pocket_of(game.tile()) == 'building':
        _result32 = yield from leave_building(log)
        return _result32
    return True

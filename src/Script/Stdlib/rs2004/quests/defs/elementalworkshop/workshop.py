"""Ported from rs2b0t's src/bot/api/ai/quests/defs/elementalworkshop/workshop.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.elementalworkshop.areas import BELLOWS_STAND, BOOKCASE, CRATE_HUB, EW_ITEM, FURNACE_STAND, ROCK_STAND, SMITHY, STAIRS_TOP, TROUGH_STAND, WATER_STAND, WORKBENCH_STAND, WORKSHOP_ARRIVAL, ew_area
from rs2004.quests.defs.elementalworkshop.supplies import COAL_NEED
from rs2004.quests.exec.prompts import held_id, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['search_bookcase', 'read_battered_book', 'slash_book_for_key', 'enter_workshop', 'leave_workshop', 'start_water_wheel', 'search_crates_for', 'fix_bellows', 'light_furnace', 'mine_elemental_ore', 'smelt_elemental_bar', 'smith_elemental_shield']

EARTH_ELEMENTAL = 'Earth elemental'
BOOK_MODAL_MS = 8000


def dist2(a, b):
    dx = a.x - b.x
    dz = a.z - b.z
    return dx * dx + dz * dz


def walk_near(tile, radius, log):
    here = game.tile()
    if here and tile.distance_to(here) <= radius:
        return True
    _result1 = yield from traversal.walk_resilient(tile, radius=radius, attempts=4, timeout_ms=180000, log=log)
    return _result1


def close_book_modal():
    # Reading the battered book opens a book interface as the main modal.
    deadline = _core.step_time() + BOOK_MODAL_MS
    while _core.step_time() < deadline:
        if reader.modals().main == -1:
            return
        _core.close_interfaces()
        yield from execution.delay_ticks(1)


def search_bookcase(log):
    if held_id(EW_ITEM.BATTERED_BOOK.id) > 0:
        return True
    _w2 = yield from walk_near(BOOKCASE, 2, log)
    if not (_w2):
        return False
    yield from settle_scene()
    bookcase = locs.query().name('Bookcase').action('Search').within(6).nearest()
    if not bookcase:
        log('no Bookcase to Search near Seers house')
        return False
    if not (bookcase.interact('Search')):
        return False
    _result3 = yield from execution.delay_until(lambda: held_id(EW_ITEM.BATTERED_BOOK.id) > 0, 8000)
    return _result3


def read_battered_book(log):
    book = ([i for i in inventory.items() if i.id == EW_ITEM.BATTERED_BOOK.id] or [None])[0]
    if not book:
        log('no Battered book to Read')
        return False
    log('reading the Battered book to start the quest')
    if not (book.interact('Read')):
        return False
    yield from execution.delay_ticks(2)
    yield from close_book_modal()
    return True


def is_slash_tool_name(name):
    _v4 = (name.lower() if name is not None else None)
    n = (_v4 if _v4 is not None else '')
    return n == 'knife' or ('scimitar' in n) or ('sword' in n) or ('longsword' in n) or ('dagger' in n) or ('battleaxe' in n)


def find_held_slash_tool():
    _v5 = ([i for i in inventory.items() if i.id == EW_ITEM.KNIFE.id] or [None])[0]
    return (_v5 if _v5 is not None else ([i for i in inventory.items() if is_slash_tool_name(i.name)] or [None])[0])


def slash_book_for_key(log):
    if held_id(EW_ITEM.BATTERED_KEY.id) > 0:
        return True
    book = ([i for i in inventory.items() if i.id == EW_ITEM.BATTERED_BOOK.id] or [None])[0]
    if not book:
        log('need the Battered book to cut the spine')
        return False
    knife = find_held_slash_tool()
    # useOn needs a pack item, so a worn-only blade comes off first.
    if not knife:
        worn_blade = ([i for i in equipment.items() if is_slash_tool_name(i.name)] or [None])[0]
        if (worn_blade.name if worn_blade is not None else None):
            log(f'removing {worn_blade.name} so it can cut the book spine')
            yield from equipment.unequip(worn_blade.name)
            knife = find_held_slash_tool()
    if not knife:
        log('need a Knife (or slash weapon) in the pack to cut the book spine')
        return False
    log('cutting the spine of the Battered book for the key')
    before = held_id(EW_ITEM.BATTERED_KEY.id)
    if not (knife.use_on(book)):
        return False
    _result6 = yield from execution.delay_until(lambda: held_id(EW_ITEM.BATTERED_KEY.id) > before, 8000)
    return _result6


def enter_workshop(log):
    if ew_area(game.tile()) == 'workshop':
        return True
    # Stand outside the smithy; the wall loc tile is unwalkable.
    _w7 = yield from walk_near(SMITHY, 4, log)
    if not (_w7):
        return False
    yield from settle_scene()
    # The "Odd looking wall" opens by oplocu with the Battered key; Push only works once it's unlocked for this player.
    wall = locs.query().name('Odd looking wall').within(10).nearest()
    if not wall:
        log('no Odd looking wall near the Seers smithy')
        return False
    if held_id(EW_ITEM.BATTERED_KEY.id) > 0:
        key = ([i for i in inventory.items() if i.id == EW_ITEM.BATTERED_KEY.id] or [None])[0]
        if not key:
            log('no Battered key to use on the Odd looking wall')
            return False
        log('using the Battered key on the Odd looking wall')
        if not (key.use_on(wall)):
            return False
        yield from execution.delay_ticks(3)
    else:
        pushable = locs.query().name('Odd looking wall').action('Push').within(10).nearest()
        if pushable:
            log('pushing the Odd looking wall')
            pushable.interact('Push')
            yield from execution.delay_ticks(2)
        else:
            log('need the Battered key for the Odd looking wall')
            return False
    # Stairs are inside; walk if needed, then Climb-down into the workshop pocket.
    _w8 = yield from walk_near(STAIRS_TOP, 3, log)
    if not (_w8):
        # Still try the climb from wherever we are if the stairs are visible.
        yield from settle_scene()
    else:
        yield from settle_scene()
    stairs = locs.query().name('Staircase').action('Climb-down').within(8).nearest()
    if not stairs:
        log('no Staircase to Climb-down in the Seers smithy')
        return False
    log('climbing down into the Elemental Workshop')
    if not (stairs.interact('Climb-down')):
        return False
    _result9 = yield from execution.delay_until(lambda: ew_area(game.tile()) == 'workshop', 12000)
    return _result9


def leave_workshop(log):
    if ew_area(game.tile()) != 'workshop':
        return True
    _w10 = yield from walk_near(WORKSHOP_ARRIVAL, 3, log)
    if not (_w10):
        return False
    yield from settle_scene()
    stairs = locs.query().name('Staircase').action('Climb-up').within(8).nearest()
    if not stairs:
        log('no Staircase to Climb-up out of the workshop')
        return False
    if not (stairs.interact('Climb-up')):
        return False
    _result11 = yield from execution.delay_until(lambda: ew_area(game.tile()) != 'workshop', 12000)
    return _result11


WATER_STARTED = 'water wheel starting up'
WATER_STOPPED = 'water wheel coming to a standstill'
WATER_RESET = 'flow gates resetting'
VALVE_LOCKED = 'valve seems locked off'
VALVE_TURNED = 'you turn the handle'


def distinct_water_valves():
    seen = set()
    out = []
    for v in locs.query().name('Water Valve').action('Turn').within(20).results():
        t = v.tile()
        key = f'{t.x},{t.z},{t.level}'
        if (key in seen):
            continue
        seen.add(key)
        out.append(v)
    # Higher x first (guide "east"), then reverse if the lever resets.
    return sorted(out, key=lambda v: -(v.tile().x * 100000 + v.tile().z))


def water_lever():
    return (sorted(locs.query().name('Lever').action('Pull').within(14).results(), key=lambda a: dist2(a.tile(), WATER_STAND)) or [None])[0]


def clear_nearby_water_threat(log):
    yield from ensure_melee_weapon(log)
    if not game.in_combat():
        pest = npcs.query().name('Water elemental').within(8).nearest()
        if pest and not pest.targets_another_player():
            log('clearing a Water elemental before the valves')
            pest.interact('Attack')
            yield from execution.delay_until(lambda: game.in_combat() or not pest.valid(), 4000)
    if game.in_combat():
        # Low-combat accounts can take a long time; still bound so death/respawn can resume.
        yield from execution.delay_until(lambda: not game.in_combat(), 120000)


def turn_valve(valve, label, log):
    mark = game_messages.mark()
    log(f'turning the {label} Water Valve at ({valve.tile().x},{valve.tile().z})')
    # Stand next to this valve so the op is not dropped mid-path.
    _w13 = yield from walk_near(Tile(valve.tile().x, valve.tile().z, valve.tile().level), 2, log)
    if not (_w13):
        return 'fail'
    yield from settle_scene()
    # Re-query; the scene may have resettled after the walk.
    _v14 = locs.query().name('Water Valve').action('Turn').within(6).nearest()
    live = (_v14 if _v14 is not None else valve)
    if not (live.interact('Turn')):
        return 'fail'
    yield from execution.delay_until(lambda: game_messages.saw_since(mark, VALVE_TURNED) or game_messages.saw_since(mark, VALVE_LOCKED), 4000)
    if game_messages.saw_since(mark, VALVE_LOCKED):
        return 'locked'
    if not game_messages.saw_since(mark, VALVE_TURNED):
        log(f'no turn confirmation from the {label} valve')
        return 'fail'
    yield from execution.delay_ticks(2)
    return 'ok'


# Why: right (valve_1) may only toggle while left is off, and left (valve_2) always toggles.
# Why: the lever needs both bits set, and the wrong order answers "flow gates resetting".
# Why: pulling the lever on a running wheel stops it, so success means a verified start or locked valves.
def try_valve_order(first, second, order_label, log):
    """Try one valve order and report whether the flow started."""
    log(f'valve order: {order_label}')
    a = yield from turn_valve(first, 'first', log)
    if a == 'locked':
        return 'locked'
    if a != 'ok':
        return 'fail'
    b = yield from turn_valve(second, 'second', log)
    if b == 'locked':
        return 'locked'
    if b != 'ok':
        return 'fail'
    lever = water_lever()
    if not lever:
        log('no water-chamber Lever to Pull')
        return 'fail'
    lever_mark = game_messages.mark()
    log('pulling the water-chamber Lever')
    if not (lever.interact('Pull')):
        return 'fail'
    yield from execution.delay_until(lambda: game_messages.saw_since(lever_mark, WATER_STARTED) or game_messages.saw_since(lever_mark, WATER_STOPPED) or game_messages.saw_since(lever_mark, WATER_RESET), 6000)
    if game_messages.saw_since(lever_mark, WATER_STARTED):
        return 'started'
    if game_messages.saw_since(lever_mark, WATER_STOPPED):
        return 'stopped'
    if game_messages.saw_since(lever_mark, WATER_RESET):
        return 'reset'
    return 'fail'


def start_water_wheel(log):
    _w15 = yield from walk_near(WATER_STAND, 3, log)
    if not (_w15):
        return False
    yield from settle_scene()
    yield from clear_nearby_water_threat(log)
    valves = distinct_water_valves()
    if len(valves) < 2:
        log(f'need two Water Valves in the northern chamber (found {len(valves)})')
        return False
    hi = valves[0]
    lo = valves[len(valves) - 1]
    log(f'valves at ({hi.tile().x},{hi.tile().z}) and ({lo.tile().x},{lo.tile().z})')
    # Guide says east then west. Server needs right-bit first (only toggles while left is off).
    # If the compass mapping is inverted, retry in reverse order after a reset.
    result = yield from try_valve_order(hi, lo, 'higher-x then lower-x', log)
    if result == 'reset':
        log('flow gates reset — retrying reverse valve order (valves are off again)')
        result = yield from try_valve_order(lo, hi, 'lower-x then higher-x', log)
    if result == 'started':
        log('water wheel started')
        return True
    if result == 'locked':
        log('valves are locked — water wheel already running')
        return True
    if result == 'stopped':
        log('water wheel stopped (lever toggled off) — will re-open valves next pass')
        return False
    if result == 'reset':
        log('flow gates reset on both valve orders')
        return False
    log('water controls did not confirm a start')
    return False


def search_crates_for(want, log):
    _w16 = yield from walk_near(CRATE_HUB, 4, log)
    if not (_w16):
        return False
    yield from settle_scene()

    def need_bowl():
        return want.bowl and held_id(EW_ITEM.STONE_BOWL.id) == 0 and held_id(EW_ITEM.STONE_BOWL_FULL.id) == 0

    def need_leather():
        return want.leather and held_id(EW_ITEM.LEATHER.id) == 0

    def need_needle():
        return want.needle and held_id(EW_ITEM.NEEDLE.id) == 0

    if not need_bowl() and not need_leather() and not need_needle():
        return True
    crates = list(locs.query().name('Crate').action('Search').within(18).results()) + list(locs.query().name('Boxes').action('Search').within(18).results())
    if len(crates) == 0:
        log('no Crates/Boxes to Search in the workshop')
        return False
    for crate in crates:
        if not need_bowl() and not need_leather() and not need_needle():
            return True
        before_bowl = held_id(EW_ITEM.STONE_BOWL.id)
        before_leather = held_id(EW_ITEM.LEATHER.id)
        before_needle = held_id(EW_ITEM.NEEDLE.id)
        log(f"searching {(crate.name if crate.name is not None else 'crate')} for workshop supplies")
        if not (crate.interact('Search')):
            continue
        yield from execution.delay_until(lambda: held_id(EW_ITEM.STONE_BOWL.id) > before_bowl or held_id(EW_ITEM.LEATHER.id) > before_leather or held_id(EW_ITEM.NEEDLE.id) > before_needle, 3000)
    if need_bowl() or need_leather() or need_needle():
        log(f'crate search incomplete (bowl={need_bowl()} leather={need_leather()} needle={need_needle()})')
        return False
    return True


def fix_bellows(log):
    if held_id(EW_ITEM.LEATHER.id) == 0 or held_id(EW_ITEM.NEEDLE.id) == 0 or held_id(EW_ITEM.THREAD.id) == 0:
        log('need Leather, Needle, and Thread to Fix the Bellows')
        return False
    _w17 = yield from walk_near(BELLOWS_STAND, 3, log)
    if not (_w17):
        return False
    yield from settle_scene()
    bellows = locs.query().name('Bellows').action('Fix').within(10).nearest()
    if not bellows:
        log('no Bellows to Fix')
        return False
    log('stitching leather over the hole in the Bellows')
    if not (bellows.interact('Fix')):
        return False
    yield from execution.delay_ticks(3)
    return held_id(EW_ITEM.LEATHER.id) == 0 or held_id(EW_ITEM.THREAD.id) == 0


def light_furnace(log):
    if held_id(EW_ITEM.STONE_BOWL_FULL.id) == 0:
        if held_id(EW_ITEM.STONE_BOWL.id) == 0:
            log('need a stone bowl to scoop lava')
            return False
        _w18 = yield from walk_near(TROUGH_STAND, 3, log)
        if not (_w18):
            return False
        log('filling the stone bowl from the Lava trough')
        _w19 = yield from use_on_loc(EW_ITEM.STONE_BOWL.id, Record({'name': 'Lava trough', 'near': TROUGH_STAND, 'within': 10}), [], lambda: held_id(EW_ITEM.STONE_BOWL_FULL.id) > 0, log)
        if not (_w19):
            return False
    _w20 = yield from walk_near(FURNACE_STAND, 3, log)
    if not (_w20):
        return False
    log('emptying lava into the Furnace')
    _result21 = yield from use_on_loc(EW_ITEM.STONE_BOWL_FULL.id, Record({'name': 'Furnace', 'near': FURNACE_STAND, 'within': 10}), [], lambda: held_id(EW_ITEM.STONE_BOWL_FULL.id) == 0, log)
    return _result21


FURNACE_COLD = 'furnace is cold'
FURNACE_NEEDS_HEAT = 'needs to be hotter'
FURNACE_NEED_COAL = 'need four heaps of coal'
AIR_PUMPING = 'bellows pump air'
AIR_STOPPED = 'bellows stop pumping'
AIR_NOTHING = 'nothing happens; the lever resets'


def pull_air_lever(log):
    _w22 = yield from walk_near(BELLOWS_STAND, 3, log)
    if not (_w22):
        return 'fail'
    yield from settle_scene()
    lever = (sorted(locs.query().name('Lever').action('Pull').within(12).results(), key=lambda a: dist2(a.tile(), BELLOWS_STAND)) or [None])[0]
    if not lever:
        log('no air-chamber Lever to Pull')
        return 'fail'
    mark = game_messages.mark()
    log('pulling the air-chamber Lever to pump the bellows')
    if not (lever.interact('Pull')):
        return 'fail'
    yield from execution.delay_until(lambda: game_messages.saw_since(mark, AIR_PUMPING) or game_messages.saw_since(mark, AIR_STOPPED) or game_messages.saw_since(mark, AIR_NOTHING), 5000)
    if game_messages.saw_since(mark, AIR_PUMPING):
        return 'on'
    if game_messages.saw_since(mark, AIR_STOPPED):
        return 'off'
    if game_messages.saw_since(mark, AIR_NOTHING):
        return 'nothing'
    return 'fail'


def _wait_out_combat(ms):
    yield from execution.delay_until(lambda: not game.in_combat(), ms)


def _is_melee_name(item):
    n = item.name.lower() if item.name is not None else ''
    return ('scimitar' in n) or ('sword' in n) or ('battleaxe' in n) or ('dagger' in n)


def _wieldable(item):
    return any([('wield' in a.lower() or 'wear' in a.lower() or 'equip' in a.lower()) for a in item.actions()])


def ensure_melee_weapon(log):
    """Prefer a wielded weapon; even maxed accounts stall forever unarmed on the rock elemental."""
    if any([_is_melee_name(_x) for _x in equipment.items()]):
        return
    weapon = ([_x for _x in inventory.items() if _is_melee_name(_x) and _wieldable(_x)] or [None])[0]
    if not (weapon.name if weapon is not None else None):
        log('no melee weapon in pack — fighting unarmed')
        return
    log(f'wielding {weapon.name}')
    yield from equipment.equip(weapon.name)


def near_rock_pocket(tile):
    """Only the rock-spawn Earth elemental drops quest ore; the ones in the water/air wings don't."""
    if not tile:
        return False
    # West mining wing (live runs drift to x 2690-2712, z 9880-9905).
    return tile.x >= 2688 and tile.x <= 2714 and tile.z >= 9875 and tile.z <= 9910


def _spawned_earth(before_idx):
    """The Earth elemental this Mine spawned, or the one already at the rock."""
    spawned = npcs.query().name(EARTH_ELEMENTAL).where(lambda n: not (n.index in before_idx) and not n.targets_another_player()).within(16).nearest()
    return spawned if spawned is not None else earth_at_rock()


def earth_at_rock():
    return npcs.query().name(EARTH_ELEMENTAL).where(lambda n: not n.targets_another_player() and near_rock_pocket(n.tile())).within(20).nearest()


def find_ore_on_ground():
    """Prefer the object id; a name match alone can miss depending on scene load order."""
    _v31 = ground_items.query().where(lambda g: g.id == EW_ITEM.ELEMENTAL_ORE.id).within(24).nearest()
    return (_v31 if _v31 is not None else ground_items.query().name(EW_ITEM.ELEMENTAL_ORE.name).within(24).nearest())


def take_elemental_ore(log):
    """Loot Elemental ore after the rock-spawn death. The drop can land a few tiles off and shows up a tick or two after the NPC is gone, so wait, walk and retry Take."""
    if held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0:
        return True
    # Wait for the server loot add after death (stack with swamprocks on same tile).
    yield from execution.delay_until(lambda: find_ore_on_ground() is not None or held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0, 10000)
    if held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0:
        return True
    for attempt in range(5):
        ground = find_ore_on_ground()
        if not ground:
            yield from execution.delay_ticks(2)
            continue
        t = ground.tile()
        log(f'taking Elemental ore at ({t.x},{t.z}) attempt {attempt + 1}')
        # Stand next to the pile so Take is not dropped mid-path.
        if game.tile() and ground.distance() > 2:
            yield from walk_near(Tile(t.x, t.z, t.level), 1, log)
            yield from settle_scene()
        live = find_ore_on_ground()
        if not live:
            continue
        before = held_id(EW_ITEM.ELEMENTAL_ORE.id)
        if not (live.interact('Take')):
            yield from execution.delay_ticks(1)
            continue
        _w32 = yield from execution.delay_until(lambda: held_id(EW_ITEM.ELEMENTAL_ORE.id) > before, 6000)
        if _w32:
            return True
        # Another pile (e.g. swamprocks) may have been clicked first, try again.
        yield from execution.delay_ticks(1)
    return held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0


def _is_droppable_food(item):
    n = item.name.lower() if item.name is not None else ''
    return (('lobster' in n) or ('swordfish' in n) or ('salmon' in n) or ('trout' in n)) and any([a.lower() == 'drop' for a in item.actions()])


def free_slot_for_ore(log):
    """Free one pack slot so Take is not silently refused on a full inventory."""
    if not inventory.is_full():
        return
    # Prefer dropping a spare food; never drop quest tools/ore/key/book.
    keep = set([
        EW_ITEM.BATTERED_BOOK.id,
        EW_ITEM.BATTERED_KEY.id,
        EW_ITEM.ELEMENTAL_ORE.id,
        EW_ITEM.ELEMENTAL_METAL.id,
        EW_ITEM.STONE_BOWL.id,
        EW_ITEM.STONE_BOWL_FULL.id,
        EW_ITEM.KNIFE.id,
        EW_ITEM.HAMMER.id,
        EW_ITEM.NEEDLE.id,
        EW_ITEM.THREAD.id,
        EW_ITEM.LEATHER.id,
        EW_ITEM.COAL.id,
        EW_ITEM.COINS.id,
        1265,
        1267,
        1269,
        1271,
        1273,
        1275,
    ])

    food = ([_x for _x in inventory.items() if _is_droppable_food(_x)] or [None])[0]
    junk = (food if food is not None else ([i for i in inventory.items() if i.id is not None and not (i.id in keep) and any([a.lower() == 'drop' for a in i.actions()])] or [None])[0])
    if not junk:
        log('inventory full and nothing safe to drop for Elemental ore')
        return
    log(f'dropping {(junk.name if junk.name is not None else junk.id)} to free a slot for ore')
    junk.interact('Drop')
    yield from execution.delay_until(lambda: not inventory.is_full(), 3000)


# Why: standing "Earth elemental" NPCs drop no quest ore; only `earth_elemental_rock_version` after Mine does, and only for the hero.
# Why: mine first, never attack a pre-existing earth elemental.
def mine_elemental_ore(log):
    """Mine the west-chamber rock, which spawns the rock Earth elemental, and take the ore."""
    if held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0:
        return True
    yield from ensure_melee_weapon(log)
    yield from free_slot_for_ore(log)
    _w37 = yield from walk_near(ROCK_STAND, 5, log)
    if not (_w37):
        return False
    yield from settle_scene()
    if find_ore_on_ground():
        _w38 = yield from take_elemental_ore(log)
        if _w38:
            return True
    # Snapshot scene NPCs so we only attack the one that spawns from this Mine.
    before_idx = set([n.index for n in npcs.query().name(EARTH_ELEMENTAL).within(20).results()])
    rock = locs.query().name('Pile of Rock').action('Mine').within(12).nearest()
    if not rock:
        log('no Pile of Rock to Mine in the west chamber')
        return False
    log('mining the elemental rock (Earth elemental will spawn)')
    if not (rock.interact('Mine')):
        return False
    yield from execution.delay_until(lambda: held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0 or find_ore_on_ground() is not None or _spawned_earth(before_idx) is not None, 12000)
    elemental = _spawned_earth(before_idx)
    if held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0:
        return True
    _w41 = yield from take_elemental_ore(log)
    if _w41:
        return True
    if not elemental:
        # Rock may have already been "mined" into an aggressive NPC mid-click.
        elemental = earth_at_rock()
    if not elemental:
        log('Earth elemental did not appear at the rock')
        return False
    log('killing the rock Earth elemental for Elemental ore')
    if not (elemental.interact('Attack')):
        return False
    yield from execution.delay_until(lambda: game.in_combat() or not elemental.valid() or find_ore_on_ground() is not None, 6000)
    # Stay until the NPC is gone or ore is visible, hero loot only drops on our kill.
    death_tile = elemental.tile()
    finished = yield from execution.delay_until(lambda: held_id(EW_ITEM.ELEMENTAL_ORE.id) > 0 or find_ore_on_ground() is not None or not elemental.valid(), 60000)
    if not finished and game.in_combat():
        log('Earth elemental combat did not finish in time')
        return False
    # Loot often lands on the death tile a tick after the NPC disappears.
    if death_tile:
        yield from walk_near(Tile(death_tile.x, death_tile.z, death_tile.level), 1, log)
        yield from settle_scene()
    _w42 = yield from take_elemental_ore(log)
    if _w42:
        return True
    log('Earth elemental died but Elemental ore was not on the ground')
    return False


def smelt_elemental_bar(log):
    """Smelt ore + 4 coal. Air isn't journal-visible and the air lever toggles, so try the furnace first and only pull air when the server asks for more heat."""
    if held_id(EW_ITEM.ELEMENTAL_METAL.id) > 0:
        return True
    if held_id(EW_ITEM.ELEMENTAL_ORE.id) == 0:
        log('no Elemental ore to smelt')
        return False
    if inventory.count_by_id(EW_ITEM.COAL.id) < COAL_NEED and inventory.count(EW_ITEM.COAL.name) < COAL_NEED:
        log(f'need {COAL_NEED} Coal to smelt Elemental ore')
        return False

    def try_smelt():
        _w43 = yield from walk_near(FURNACE_STAND, 3, log)
        if not (_w43):
            return 'fail'
        yield from settle_scene()
        before = held_id(EW_ITEM.ELEMENTAL_METAL.id)
        mark = game_messages.mark()
        log('placing Elemental ore and Coal into the Furnace')
        ore = ([i for i in inventory.items() if i.id == EW_ITEM.ELEMENTAL_ORE.id] or [None])[0]
        furnace = locs.query().name('Furnace').within(10).nearest()
        if not ore or not furnace:
            return 'fail'
        if not (ore.use_on(furnace)):
            return 'fail'
        yield from execution.delay_until(lambda: held_id(EW_ITEM.ELEMENTAL_METAL.id) > before or game_messages.saw_since(mark, FURNACE_COLD) or game_messages.saw_since(mark, FURNACE_NEEDS_HEAT) or game_messages.saw_since(mark, FURNACE_NEED_COAL), 10000)
        if held_id(EW_ITEM.ELEMENTAL_METAL.id) > before:
            return 'ok'
        if game_messages.saw_since(mark, FURNACE_NEED_COAL):
            return 'coal'
        if game_messages.saw_since(mark, FURNACE_COLD):
            return 'cold'
        if game_messages.saw_since(mark, FURNACE_NEEDS_HEAT):
            return 'hotter'
        return 'fail'

    result = yield from try_smelt()
    if result == 'ok':
        return True
    if result == 'coal':
        log('furnace refused — need 4 Coal in the pack')
        return False
    if result == 'cold':
        log('furnace is cold — light it with lava first')
        return False
    if result == 'hotter' or result == 'fail':
        # Heat off or unknown: try air once (toggle risk handled by message).
        air = yield from pull_air_lever(log)
        if air == 'off':
            # Toggled off a running blast, pull again to restore.
            log('air was on; re-pulling to restore blast')
            yield from pull_air_lever(log)
        elif air == 'nothing':
            log('air lever did nothing — water wheel / bellows may not be ready')
            return False
        result = yield from try_smelt()
        return result == 'ok'
    return False


def smith_elemental_shield(log):
    if held_id(EW_ITEM.ELEMENTAL_SHIELD.id) > 0:
        return True
    if held_id(EW_ITEM.ELEMENTAL_METAL.id) == 0:
        log('no Elemental metal to smith')
        return False
    if held_id(EW_ITEM.BATTERED_BOOK.id) == 0:
        log('need the Battered book as instructions on the workbench')
        return False
    if held_id(EW_ITEM.HAMMER.id) == 0:
        log('need a Hammer to work the metal')
        return False
    _w44 = yield from walk_near(WORKBENCH_STAND, 3, log)
    if not (_w44):
        return False
    yield from settle_scene()
    before = held_id(EW_ITEM.ELEMENTAL_SHIELD.id)
    log('smithing an Elemental shield on the Workbench')
    _result45 = yield from use_on_loc(EW_ITEM.ELEMENTAL_METAL.id, Record({'name': 'Workbench', 'near': WORKBENCH_STAND, 'within': 10}), [], lambda: held_id(EW_ITEM.ELEMENTAL_SHIELD.id) > before, log)
    return _result45

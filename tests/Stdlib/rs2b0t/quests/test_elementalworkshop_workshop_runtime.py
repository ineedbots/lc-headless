"""Elemental Workshop's legs against spied facades: the book and its key, the way in and out, the water wheel's valve
orders, the crates, the bellows, the furnace, the rock elemental's ore, and the smelt and smith, each through its
success and its failures."""

import _core
from rs2004.geometry import Tile
from rs2004.quests.defs.elementalworkshop import workshop
from rs2004.quests.defs.elementalworkshop.areas import BELLOWS_STAND, CRATE_HUB, EW_ITEM, FURNACE_STAND, ROCK_STAND, SMITHY, STAIRS_TOP, TROUGH_STAND, WATER_STAND, WORKBENCH_STAND, WORKSHOP_ARRIVAL
from rs2004.quests.defs.elementalworkshop.supplies import COAL_NEED

SEERS = Tile(2720, 3490, 0)
WANT_ALL = Fake(bowl=True, leather=True, needle=True)


def give(scene, item):
    return scene.item(item.id, item.name)


# The bookcase and the book.

def bookcase_gives_the_book():
    scene = Scene(SEERS)
    scene.loc('Bookcase', ['Search'], effect=lambda op: give(scene, EW_ITEM.BATTERED_BOOK) and True)
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.BATTERED_BOOK.id)).to_be(True)


test('searching the bookcase ends when the book lands in the pack', bookcase_gives_the_book)


def bookcase_book_already_held():
    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_BOOK)
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('a held book needs no search', bookcase_book_already_held)


def bookcase_failures():
    scene = Scene(SEERS)
    scene.walk_ok = False
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(False)

    scene = Scene(SEERS)
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(False)
    expect(scene.logged('no Bookcase to Search')).to_be(True)

    scene = Scene(SEERS)
    scene.loc('Bookcase', ['Search'], effect=lambda op: False)
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(False)

    scene = Scene(SEERS)
    scene.loc('Bookcase', ['Search'])
    expect(run_wait(workshop.search_bookcase(scene.log))).to_be(False)


test('the bookcase fails on a failed walk, no bookcase, a refused click, or no book', bookcase_failures)


def reading_the_book():
    scene = Scene(SEERS)
    expect(run_wait(workshop.read_battered_book(scene.log))).to_be(False)
    expect(scene.logged('no Battered book')).to_be(True)

    scene = Scene(SEERS)
    scene.item(EW_ITEM.BATTERED_BOOK.id, 'Battered book', effect=lambda op: False)
    expect(run_wait(workshop.read_battered_book(scene.log))).to_be(False)

    scene = Scene(SEERS)
    scene.main_modal = 77
    scene.item(EW_ITEM.BATTERED_BOOK.id, 'Battered book')
    expect(run_wait(workshop.read_battered_book(scene.log))).to_be(True)
    expect(scene.main_modal).to_be(-1)


test('reading needs the book, and shuts the book interface it opens', reading_the_book)


def book_modal_that_will_not_shut():
    scene = Scene(SEERS)
    scene.main_modal = 77
    spy_on(_core, 'close_interfaces', returns=None)
    run_wait(workshop.close_book_modal())
    expect(scene.clock).to_be_greater_than_or_equal(workshop.BOOK_MODAL_MS)


test('a book that will not shut gives up at its deadline', book_modal_that_will_not_shut)


def slash_names():
    for name in ['Knife', 'Bronze scimitar', 'Steel longsword', 'Iron dagger', 'Rune battleaxe']:
        expect(workshop.is_slash_tool_name(name)).to_be(True)
    expect(workshop.is_slash_tool_name('Pickaxe')).to_be(False)
    expect(workshop.is_slash_tool_name(None)).to_be(False)


test('knives and bladed weapons can cut the spine', slash_names)


def cuts_with_a_knife():
    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_BOOK)

    def cut(target):
        give(scene, EW_ITEM.BATTERED_KEY)

    scene.item(EW_ITEM.KNIFE.id, 'Knife', on_use=cut)
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.BATTERED_KEY.id)).to_be(True)


test('the knife cuts the key out of the book', cuts_with_a_knife)


def cuts_with_a_worn_blade():
    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_BOOK)
    scene.wear('Steel scimitar')
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(False)
    expect(scene.logged('removing Steel scimitar')).to_be(True)
    expect(scene.worn).to_have_length(0)
    expect(scene.pack).to_have_length(2)


test('a worn-only blade comes off to do the cutting', cuts_with_a_worn_blade)


def slash_failures():
    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_KEY)
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(True)

    scene = Scene(SEERS)
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(False)
    expect(scene.logged('need the Battered book')).to_be(True)

    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_BOOK)
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(False)
    expect(scene.logged('need a Knife')).to_be(True)

    scene = Scene(SEERS)
    give(scene, EW_ITEM.BATTERED_BOOK)
    scene.item(EW_ITEM.KNIFE.id, 'Knife', on_use=lambda target: False)
    expect(run_wait(workshop.slash_book_for_key(scene.log))).to_be(False)


test('cutting is skipped with a key, and fails with no book, no blade, or a refused use', slash_failures)


# The way in and out.

def entering_scene():
    scene = Scene(SMITHY)
    scene.loc('Odd looking wall', ['Push'])

    def down(op):
        scene.at = WORKSHOP_ARRIVAL

    scene.loc('Staircase', ['Climb-down'], effect=down)
    return scene


def enters_with_the_key():
    scene = entering_scene()
    give(scene, EW_ITEM.BATTERED_KEY)
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(True)
    expect(scene.logged('using the Battered key')).to_be(True)


test('the key opens the odd wall and the stairs lead down', enters_with_the_key)


def enters_by_push():
    scene = entering_scene()
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(True)
    expect(scene.logged('pushing the Odd looking wall')).to_be(True)


test('an unlocked wall is pushed without the key', enters_by_push)


def already_inside():
    scene = Scene(WORKSHOP_ARRIVAL)
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('inside the workshop there is nothing to enter', already_inside)


def stairs_visible_after_a_failed_walk():
    scene = entering_scene()
    # Close enough to the smithy to stay put, too far from the stairs.
    scene.at = Tile(SMITHY.x + 4, SMITHY.z, 0)
    scene.no_walk = [STAIRS_TOP]
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(True)
    expect(scene.walks).to_equal([STAIRS_TOP])


test('a failed walk to the stairs still tries a climb when they are in view', stairs_visible_after_a_failed_walk)


def enter_failures():
    scene = Scene(SEERS)
    scene.walk_ok = False
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)

    scene = Scene(SMITHY)
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)
    expect(scene.logged('no Odd looking wall')).to_be(True)

    # The wall offers no Push and there is no key.
    scene = Scene(SMITHY)
    scene.loc('Odd looking wall')
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)
    expect(scene.logged('need the Battered key')).to_be(True)

    scene = Scene(SMITHY)
    scene.loc('Odd looking wall')
    scene.item(EW_ITEM.BATTERED_KEY.id, 'Battered key', on_use=lambda target: False)
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)

    scene = Scene(SMITHY)
    scene.loc('Odd looking wall', ['Push'])
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)
    expect(scene.logged('no Staircase to Climb-down')).to_be(True)

    scene = Scene(SMITHY)
    scene.loc('Odd looking wall', ['Push'])
    scene.loc('Staircase', ['Climb-down'], effect=lambda op: False)
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)

    # The climb is sent and nothing moves the player.
    scene = Scene(SMITHY)
    scene.loc('Odd looking wall', ['Push'])
    scene.loc('Staircase', ['Climb-down'])
    expect(run_wait(workshop.enter_workshop(scene.log))).to_be(False)


test('entering fails at each of its steps', enter_failures)


def leaving():
    scene = Scene(SEERS)
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)

    scene = Scene(WORKSHOP_ARRIVAL)

    def up(op):
        scene.at = STAIRS_TOP

    scene.loc('Staircase', ['Climb-up'], effect=up)
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(True)
    expect(scene.at).to_equal(STAIRS_TOP)


test('leaving climbs back up, and is nothing from outside', leaving)


def leaving_failures():
    scene = Scene(ROCK_STAND)
    scene.walk_ok = False
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(False)

    scene = Scene(WORKSHOP_ARRIVAL)
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(False)
    expect(scene.logged('no Staircase to Climb-up')).to_be(True)

    scene = Scene(WORKSHOP_ARRIVAL)
    scene.loc('Staircase', ['Climb-up'], effect=lambda op: False)
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(False)

    scene = Scene(WORKSHOP_ARRIVAL)
    scene.loc('Staircase', ['Climb-up'])
    expect(run_wait(workshop.leave_workshop(scene.log))).to_be(False)


test('leaving fails on a failed walk, no stairs, a refused click, or staying put', leaving_failures)


# The water wheel.

VALVE_EAST = Tile(2725, 9905, 0)
VALVE_WEST = Tile(2712, 9905, 0)


def water_scene(lever_says=None, valve_says=None):
    scene = Scene(WATER_STAND)
    scene.turned = []
    says = valve_says if valve_says is not None else workshop.VALVE_TURNED

    def turn_east(op):
        scene.turned.append('east')
        scene.say(says)

    def turn_west(op):
        scene.turned.append('west')
        scene.say(says)

    scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, effect=turn_east, id=1, dist=None)
    scene.loc('Water Valve', ['Turn'], tile=VALVE_WEST, effect=turn_west, id=2, dist=None)
    if lever_says is not None:
        scene.lever_says = list(lever_says)
        scene.loc('Lever', ['Pull'], tile=WATER_STAND, effect=lambda op: scene.say(scene.lever_says.pop(0)))
    return scene


def valves_are_deduplicated_and_sorted():
    scene = water_scene()
    scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, id=1, dist=None)
    tiles = [v.tile().x for v in workshop.distinct_water_valves()]
    expect(tiles).to_equal([VALVE_EAST.x, VALVE_WEST.x])


test('a valve seen twice counts once, and the higher x comes first', valves_are_deduplicated_and_sorted)


def lever_is_the_nearest_to_the_chamber():
    scene = Scene(WATER_STAND)
    scene.loc('Lever', ['Pull'], tile=Tile(WATER_STAND.x + 9, WATER_STAND.z, 0), id=1)
    near = scene.loc('Lever', ['Pull'], tile=Tile(WATER_STAND.x + 1, WATER_STAND.z, 0), id=2)
    expect(workshop.water_lever().id).to_be(near.id)


test('the water lever is the one closest to the valves', lever_is_the_nearest_to_the_chamber)


def wheel_starts():
    scene = water_scene([workshop.WATER_STARTED])
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(True)
    expect(scene.turned).to_equal(['east', 'west'])
    expect(scene.logged('water wheel started')).to_be(True)


test('the valves east then west and the lever start the wheel', wheel_starts)


def wheel_reversed_after_a_reset():
    scene = water_scene([workshop.WATER_RESET, workshop.WATER_STARTED])
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(True)
    expect(scene.turned).to_equal(['east', 'west', 'west', 'east'])


test('a flow-gate reset retries the valves in the other order', wheel_reversed_after_a_reset)


def wheel_reset_twice():
    scene = water_scene([workshop.WATER_RESET, workshop.WATER_RESET])
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)
    expect(scene.logged('flow gates reset on both valve orders')).to_be(True)


test('a reset on both orders fails', wheel_reset_twice)


def wheel_toggled_off():
    scene = water_scene([workshop.WATER_STOPPED])
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)
    expect(scene.logged('lever toggled off')).to_be(True)


test('a lever that stops a running wheel is reported as a failure, for the next pass', wheel_toggled_off)


def wheel_already_running():
    scene = water_scene(valve_says=workshop.VALVE_LOCKED)
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(True)
    expect(scene.logged('valves are locked')).to_be(True)
    expect(scene.turned).to_equal(['east'])


test('locked valves mean the wheel already runs', wheel_already_running)


def second_valve_locked():
    scene = Scene(WATER_STAND)
    states = [workshop.VALVE_TURNED, workshop.VALVE_LOCKED]

    def speak(op):
        scene.say(states.pop(0))

    east = scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, effect=speak, id=3, dist=None)
    west = scene.loc('Water Valve', ['Turn'], tile=VALVE_WEST, effect=speak, id=4, dist=None)
    expect(run_wait(workshop.try_valve_order(east, west, 'test', scene.log))).to_be('locked')


test('a lock on the second valve reports locked too', second_valve_locked)


def wheel_failures():
    scene = Scene(ROCK_STAND)
    scene.walk_ok = False
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)

    scene = Scene(WATER_STAND)
    scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, dist=None)
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)
    expect(scene.logged('need two Water Valves in the northern chamber (found 1)')).to_be(True)

    scene = water_scene()
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)
    expect(scene.logged('no water-chamber Lever')).to_be(True)

    # The lever says nothing.
    scene = water_scene()
    scene.loc('Lever', ['Pull'], tile=WATER_STAND)
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)
    expect(scene.logged('did not confirm a start')).to_be(True)

    scene = water_scene()
    scene.loc('Lever', ['Pull'], tile=WATER_STAND, effect=lambda op: False)
    expect(run_wait(workshop.start_water_wheel(scene.log))).to_be(False)


test('the wheel fails on a failed walk, one valve, no lever, a silent or refused lever', wheel_failures)


def valve_turn_failures():
    scene = Scene(WATER_STAND)
    valve = scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, dist=None)
    expect(run_wait(workshop.turn_valve(valve, 'first', scene.log))).to_be('fail')
    expect(scene.logged('no turn confirmation from the first valve')).to_be(True)

    scene = Scene(WATER_STAND)
    valve = scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, effect=lambda op: False, dist=None)
    expect(run_wait(workshop.turn_valve(valve, 'first', scene.log))).to_be('fail')

    scene = Scene(WATER_STAND)
    valve = scene.loc('Water Valve', ['Turn'], tile=VALVE_EAST, dist=None)
    scene.walk_ok = False
    expect(run_wait(workshop.turn_valve(valve, 'first', scene.log))).to_be('fail')

    scene = water_scene()
    bad = scene.loc('Water Valve', ['Turn'], tile=Tile(2700, 9905, 0), effect=lambda op: False, dist=None)
    good = scene.locs[0]
    expect(run_wait(workshop.try_valve_order(bad, good, 'test', scene.log))).to_be('fail')
    expect(run_wait(workshop.try_valve_order(good, bad, 'test', scene.log))).to_be('fail')


test('a valve that says nothing, refuses the click or cannot be reached fails its order', valve_turn_failures)


def water_threat_is_cleared():
    scene = Scene(WATER_STAND)
    scene.wear('Bronze scimitar')

    def end_fight():
        scene.fighting = False

    def attack(op):
        scene.fighting = True
        scene.later(lambda: None)
        scene.later(end_fight)

    pest = scene.npc('Water elemental', ['Attack'], effect=attack)
    run_wait(workshop.clear_nearby_water_threat(scene.log))
    expect(scene.logged('clearing a Water elemental')).to_be(True)
    expect(scene.fighting).to_be(False)
    expect(pest.valid()).to_be(True)


test('a Water elemental near the valves is fought first and waited out', water_threat_is_cleared)


def contested_threat_is_left():
    scene = Scene(WATER_STAND)
    scene.wear('Bronze scimitar')
    scene.npc('Water elemental', ['Attack'], others=True)
    run_wait(workshop.clear_nearby_water_threat(scene.log))
    expect(scene.logged('clearing a Water elemental')).to_be(False)


test('an elemental fighting someone else is left to them', contested_threat_is_left)


# The crates.

def crate_scene():
    scene = Scene(CRATE_HUB)
    scene.loc('Crate', ['Search'], effect=lambda op: give(scene, EW_ITEM.STONE_BOWL) and True, id=1)
    scene.loc('Crate', ['Search'], effect=lambda op: give(scene, EW_ITEM.LEATHER) and True, id=2)
    scene.loc('Boxes', ['Search'], effect=lambda op: give(scene, EW_ITEM.NEEDLE) and True, id=3)
    return scene


def crates_supply_everything():
    scene = crate_scene()
    expect(run_wait(workshop.search_crates_for(WANT_ALL, scene.log))).to_be(True)
    for item in [EW_ITEM.STONE_BOWL, EW_ITEM.LEATHER, EW_ITEM.NEEDLE]:
        expect(scene.has(item.id)).to_be(True)


test('the crates and boxes are searched until every supply is held', crates_supply_everything)


def crates_stop_when_supplied():
    scene = crate_scene()
    expect(run_wait(workshop.search_crates_for(Fake(bowl=True, leather=False, needle=False), scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.LEATHER.id)).to_be(False)
    expect(scene.lines).to_have_length(1)


test('searching stops at the first crate that gives what is wanted', crates_stop_when_supplied)


def crates_not_needed():
    scene = crate_scene()
    give(scene, EW_ITEM.STONE_BOWL_FULL)
    give(scene, EW_ITEM.LEATHER)
    give(scene, EW_ITEM.NEEDLE)
    expect(run_wait(workshop.search_crates_for(WANT_ALL, scene.log))).to_be(True)
    expect(scene.lines).to_have_length(0)


test('a full bowl counts as the bowl, so nothing is searched', crates_not_needed)


def crates_failures():
    scene = crate_scene()
    scene.at = ROCK_STAND
    scene.walk_ok = False
    expect(run_wait(workshop.search_crates_for(WANT_ALL, scene.log))).to_be(False)

    scene = Scene(CRATE_HUB)
    expect(run_wait(workshop.search_crates_for(WANT_ALL, scene.log))).to_be(False)
    expect(scene.logged('no Crates/Boxes')).to_be(True)

    scene = Scene(CRATE_HUB)
    scene.loc('Crate', ['Search'], effect=lambda op: False)
    scene.loc('Boxes', ['Search'])
    expect(run_wait(workshop.search_crates_for(WANT_ALL, scene.log))).to_be(False)
    expect(scene.logged('crate search incomplete (bowl=True leather=True needle=True)')).to_be(True)


test('the crates fail on a failed walk, no crates, or a search that leaves something missing', crates_failures)


# The bellows and furnace.

def stitch_kit(scene):
    give(scene, EW_ITEM.LEATHER)
    give(scene, EW_ITEM.NEEDLE)
    give(scene, EW_ITEM.THREAD)


def bellows_fixed():
    scene = Scene(BELLOWS_STAND)
    stitch_kit(scene)
    scene.loc('Bellows', ['Fix'], effect=lambda op: scene.take(EW_ITEM.LEATHER.id))
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(True)


test('the bellows are fixed once the leather is used up', bellows_fixed)


def bellows_failures():
    scene = Scene(BELLOWS_STAND)
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(False)
    expect(scene.logged('need Leather, Needle, and Thread')).to_be(True)

    scene = Scene(ROCK_STAND)
    stitch_kit(scene)
    scene.walk_ok = False
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(False)

    scene = Scene(BELLOWS_STAND)
    stitch_kit(scene)
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(False)
    expect(scene.logged('no Bellows to Fix')).to_be(True)

    scene = Scene(BELLOWS_STAND)
    stitch_kit(scene)
    scene.loc('Bellows', ['Fix'], effect=lambda op: False)
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(False)

    # Stitched, but the kit is all still held.
    scene = Scene(BELLOWS_STAND)
    stitch_kit(scene)
    scene.loc('Bellows', ['Fix'])
    expect(run_wait(workshop.fix_bellows(scene.log))).to_be(False)


test('the bellows fail with no kit, a failed walk, no bellows, a refused click, or an unused kit', bellows_failures)


def furnace_scene():
    scene = Scene(TROUGH_STAND)

    def fill(target):
        scene.take(EW_ITEM.STONE_BOWL.id)
        give(scene, EW_ITEM.STONE_BOWL_FULL)

    def empty(target):
        scene.take(EW_ITEM.STONE_BOWL_FULL.id)
        give(scene, EW_ITEM.STONE_BOWL)

    scene.fill = fill
    scene.empty = empty
    scene.loc('Lava trough', ['Use'])
    scene.loc('Furnace', ['Use'])
    return scene


def bowl_item(scene, full, on_use):
    item = EW_ITEM.STONE_BOWL_FULL if full else EW_ITEM.STONE_BOWL
    return scene.item(item.id, item.name, on_use=on_use)


def furnace_lit():
    scene = furnace_scene()

    def fill_then_arm(target):
        scene.take(EW_ITEM.STONE_BOWL.id)
        bowl_item(scene, True, scene.empty)

    bowl_item(scene, False, fill_then_arm)
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(True)
    expect(scene.logged('filling the stone bowl')).to_be(True)
    expect(scene.logged('emptying lava into the Furnace')).to_be(True)
    expect(scene.has(EW_ITEM.STONE_BOWL.id)).to_be(True)


test('an empty bowl is filled at the trough and emptied into the furnace', furnace_lit)


def furnace_lit_from_a_full_bowl():
    scene = furnace_scene()
    bowl_item(scene, True, scene.empty)
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(True)
    expect(scene.logged('filling the stone bowl')).to_be(False)


test('a bowl already full skips the trough', furnace_lit_from_a_full_bowl)


def furnace_failures():
    scene = furnace_scene()
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(False)
    expect(scene.logged('need a stone bowl')).to_be(True)

    scene = furnace_scene()
    bowl_item(scene, False, scene.fill)
    scene.no_walk = [TROUGH_STAND]
    scene.at = BELLOWS_STAND
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(False)

    # The trough never fills the bowl.
    scene = furnace_scene()
    bowl_item(scene, False, lambda target: False)
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(False)

    scene = furnace_scene()
    bowl_item(scene, True, scene.empty)
    scene.no_walk = [FURNACE_STAND]
    expect(run_wait(workshop.light_furnace(scene.log))).to_be(False)


test('the furnace fails with no bowl, failed walks, or a trough that gives no lava', furnace_failures)


def air_lever_answers():
    for says, want in [(workshop.AIR_PUMPING, 'on'), (workshop.AIR_STOPPED, 'off'), (workshop.AIR_NOTHING, 'nothing')]:
        scene = Scene(BELLOWS_STAND)
        scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(says))
        expect(run_wait(workshop.pull_air_lever(scene.log))).to_be(want)

    scene = Scene(BELLOWS_STAND)
    scene.loc('Lever', ['Pull'])
    expect(run_wait(workshop.pull_air_lever(scene.log))).to_be('fail')

    scene = Scene(BELLOWS_STAND)
    scene.loc('Lever', ['Pull'], effect=lambda op: False)
    expect(run_wait(workshop.pull_air_lever(scene.log))).to_be('fail')

    scene = Scene(BELLOWS_STAND)
    expect(run_wait(workshop.pull_air_lever(scene.log))).to_be('fail')
    expect(scene.logged('no air-chamber Lever')).to_be(True)

    scene = Scene(ROCK_STAND)
    scene.walk_ok = False
    expect(run_wait(workshop.pull_air_lever(scene.log))).to_be('fail')


test('the air lever reads back on, off, nothing or fail', air_lever_answers)


def waits_out_combat():
    scene = Scene(ROCK_STAND)
    scene.fighting = True
    run_wait(workshop._wait_out_combat(5000))
    expect(scene.clock).to_be(5000)


test('combat is waited on up to its timeout', waits_out_combat)


# The weapon.

def weapon_choice():
    scene = Scene(ROCK_STAND)
    scene.wear('Rune scimitar')
    run_wait(workshop.ensure_melee_weapon(scene.log))
    expect(scene.lines).to_have_length(0)

    scene = Scene(ROCK_STAND)
    run_wait(workshop.ensure_melee_weapon(scene.log))
    expect(scene.logged('fighting unarmed')).to_be(True)

    scene = Scene(ROCK_STAND)
    scene.item(1, 'Bronze sword', actions=['Wield', 'Drop'])
    run_wait(workshop.ensure_melee_weapon(scene.log))
    expect(scene.logged('wielding Bronze sword')).to_be(True)
    expect(scene.worn).to_have_length(1)

    # A name that reads as a weapon, but can't be wielded.
    scene = Scene(ROCK_STAND)
    scene.item(2, 'Swordfish', actions=['Eat', 'Drop'])
    run_wait(workshop.ensure_melee_weapon(scene.log))
    expect(scene.logged('fighting unarmed')).to_be(True)


test('a weapon is wielded from the pack, or the fight goes on unarmed', weapon_choice)


def rock_pocket_bounds():
    expect(workshop.near_rock_pocket(None)).to_be(False)
    expect(workshop.near_rock_pocket(ROCK_STAND)).to_be(True)
    expect(workshop.near_rock_pocket(WATER_STAND)).to_be(False)


test('only the west wing counts as the rock pocket', rock_pocket_bounds)


# The ore.

def ore_scene():
    scene = Scene(ROCK_STAND)
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND)
    return scene


def takes_ore():
    scene = ore_scene()
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.ELEMENTAL_ORE.id)).to_be(True)


test('ore on the ground is taken', takes_ore)


def takes_ore_by_name():
    scene = Scene(ROCK_STAND)
    scene.on_ground(999, 'Elemental ore', tile=ROCK_STAND)
    expect(workshop.find_ore_on_ground().id).to_be(999)


test('a pile whose id does not match is still found by name', takes_ore_by_name)


def ore_walked_to():
    scene = Scene(ROCK_STAND)
    far = Tile(ROCK_STAND.x + 5, ROCK_STAND.z, 0)
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=far, dist=5)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(True)
    expect(scene.walks).to_contain(far)


test('a pile a few tiles off is walked to first', ore_walked_to)


def ore_held_or_arriving():
    scene = Scene(ROCK_STAND)
    give(scene, EW_ITEM.ELEMENTAL_ORE)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(True)

    scene = Scene(ROCK_STAND)
    scene.later(lambda: give(scene, EW_ITEM.ELEMENTAL_ORE))
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(True)
    expect(scene.lines).to_have_length(0)


test('ore already held, or landing during the wait, needs no click', ore_held_or_arriving)


def ore_never_lands():
    scene = Scene(ROCK_STAND)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(False)
    expect(scene.ticks).to_be(10)


test('with no pile the take retries five times, then fails', ore_never_lands)


def ore_take_refused():
    scene = Scene(ROCK_STAND)
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND, effect=lambda op: False)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('attempt 5')).to_be(True)

    # A click that lands on another pile: Take goes through and nothing arrives.
    scene = Scene(ROCK_STAND)
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND, effect=lambda op: True)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('attempt 5')).to_be(True)


test('refused or fruitless Takes retry up to their cap', ore_take_refused)


def ore_pile_vanishes_on_the_way():
    scene = Scene(ROCK_STAND)
    far = Tile(ROCK_STAND.x + 5, ROCK_STAND.z, 0)
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=far, dist=5)

    def gone(dest, radius=0, attempts=0, timeout_ms=0, log=None):
        scene.ground = []
        return True
        yield

    spy_on(traversal, 'walk_resilient', impl=gone)
    expect(run_wait(workshop.take_elemental_ore(scene.log))).to_be(False)


test('a pile gone by the time the walk ends is looked for again', ore_pile_vanishes_on_the_way)


def full_pack(scene, last=None):
    for n in range(27):
        scene.item(EW_ITEM.COAL.id, 'Coal', actions=['Use', 'Drop'])
    if last is not None:
        scene.pack.append(last)


def frees_a_slot():
    scene = Scene(ROCK_STAND)
    run_wait(workshop.free_slot_for_ore(scene.log))
    expect(scene.lines).to_have_length(0)

    scene = Scene(ROCK_STAND)
    full_pack(scene)
    scene.item(379, 'Lobster', actions=['Eat', 'Drop'], effect=lambda op: scene.take(379))
    run_wait(workshop.free_slot_for_ore(scene.log))
    expect(scene.logged('dropping Lobster')).to_be(True)
    expect(scene.pack).to_have_length(27)


test('a full pack drops a spare food to make room for the ore', frees_a_slot)


def frees_a_slot_of_junk():
    scene = Scene(ROCK_STAND)
    full_pack(scene)
    scene.item(555, 'Bones', actions=['Bury', 'Drop'], effect=lambda op: scene.take(555))
    run_wait(workshop.free_slot_for_ore(scene.log))
    expect(scene.logged('dropping Bones')).to_be(True)


test('with no food, junk goes instead', frees_a_slot_of_junk)


def keeps_every_quest_tool():
    scene = Scene(ROCK_STAND)
    full_pack(scene)
    scene.item(EW_ITEM.BATTERED_KEY.id, 'Battered key', actions=['Use', 'Drop'])
    run_wait(workshop.free_slot_for_ore(scene.log))
    expect(scene.logged('nothing safe to drop')).to_be(True)
    expect(scene.pack).to_have_length(28)


test('quest tools are never dropped for the ore', keeps_every_quest_tool)


def mine_scene():
    scene = Scene(ROCK_STAND)
    scene.wear('Rune scimitar')
    return scene


def spawn_elemental(scene):
    def finish():
        scene.fighting = False
        scene.npcs = []
        scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND)

    def dies(op):
        scene.fighting = True
        scene.later(lambda: None)
        scene.later(finish)

    return scene.npc(workshop.EARTH_ELEMENTAL, ['Attack'], tile=ROCK_STAND, effect=dies, id=5)


def mines_kills_and_loots():
    scene = mine_scene()
    scene.loc('Pile of Rock', ['Mine'], effect=lambda op: spawn_elemental(scene) and True)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(True)
    expect(scene.logged('killing the rock Earth elemental')).to_be(True)
    expect(scene.has(EW_ITEM.ELEMENTAL_ORE.id)).to_be(True)


test("the rock is mined, its elemental killed, and the drop taken", mines_kills_and_loots)


def ore_held_needs_no_mining():
    scene = mine_scene()
    give(scene, EW_ITEM.ELEMENTAL_ORE)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(True)
    expect(scene.walks).to_have_length(0)


test('held ore needs no mining', ore_held_needs_no_mining)


def ore_on_the_ground_before_mining():
    scene = mine_scene()
    scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(True)
    expect(scene.logged('mining the elemental rock')).to_be(False)


test('ore left on the ground from an earlier kill is taken without mining', ore_on_the_ground_before_mining)


def mining_lands_ore_directly():
    scene = mine_scene()
    scene.loc('Pile of Rock', ['Mine'], effect=lambda op: give(scene, EW_ITEM.ELEMENTAL_ORE) and True)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(True)
    expect(scene.logged('killing the rock')).to_be(False)


test('ore that lands straight from the mine needs no kill', mining_lands_ore_directly)


def mining_drops_ore_nearby():
    scene = mine_scene()

    def lands(op):
        scene.on_ground(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', tile=ROCK_STAND)

    scene.loc('Pile of Rock', ['Mine'], effect=lands)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(True)
    expect(scene.logged('killing the rock')).to_be(False)


test('ore that lands on the ground from the mine is taken with no kill', mining_drops_ore_nearby)


def existing_elementals_are_not_attacked():
    scene = mine_scene()
    far = Tile(2730, 9890, 0)
    scene.npc(workshop.EARTH_ELEMENTAL, ['Attack'], tile=far, effect=lambda op: expect(op).to_be('never'), id=6)
    scene.loc('Pile of Rock', ['Mine'])
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('Earth elemental did not appear')).to_be(True)


test("a standing Earth elemental in another wing is no reason to fight: only the Mine's spawn drops ore", existing_elementals_are_not_attacked)


def mining_failures():
    scene = mine_scene()
    scene.at = WATER_STAND
    scene.walk_ok = False
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)

    scene = mine_scene()
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('no Pile of Rock')).to_be(True)

    scene = mine_scene()
    scene.loc('Pile of Rock', ['Mine'], effect=lambda op: False)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)


test('mining fails on a failed walk, no rock, or a refused click', mining_failures)


def elemental_refuses_the_attack():
    scene = mine_scene()

    def spawn(op):
        scene.npc(workshop.EARTH_ELEMENTAL, ['Attack'], tile=ROCK_STAND, effect=lambda op2: False, id=7)

    scene.loc('Pile of Rock', ['Mine'], effect=spawn)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('killing the rock Earth elemental')).to_be(True)


test('an attack the elemental refuses fails the leg', elemental_refuses_the_attack)


def elemental_outlasts_the_wait():
    scene = mine_scene()

    def start_fight(op):
        scene.fighting = True

    def spawn(op):
        scene.npc(workshop.EARTH_ELEMENTAL, ['Attack'], tile=ROCK_STAND, effect=start_fight, id=8)

    scene.loc('Pile of Rock', ['Mine'], effect=spawn)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('combat did not finish in time')).to_be(True)


test('a fight that outlasts the wait fails, for a later attempt', elemental_outlasts_the_wait)


def elemental_dies_without_a_drop():
    scene = mine_scene()

    def die(op):
        scene.npcs = []

    def spawn(op):
        scene.npc(workshop.EARTH_ELEMENTAL, ['Attack'], tile=ROCK_STAND, effect=die, id=9)

    scene.loc('Pile of Rock', ['Mine'], effect=spawn)
    expect(run_wait(workshop.mine_elemental_ore(scene.log))).to_be(False)
    expect(scene.logged('died but Elemental ore was not on the ground')).to_be(True)


test('a kill with no ore on the ground is reported', elemental_dies_without_a_drop)


# The smelt and the smith.

def smelting_scene(furnace_says=None, ore_ok=True):
    scene = Scene(FURNACE_STAND)
    scene.furnace_says = list(furnace_says) if furnace_says is not None else []

    def smelt(target):
        if not ore_ok:
            return False
        if len(scene.furnace_says) > 0:
            scene.say(scene.furnace_says.pop(0))
            return True
        give(scene, EW_ITEM.ELEMENTAL_METAL)
        return True

    scene.item(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore', on_use=smelt)
    scene.item(EW_ITEM.COAL.id, 'Coal', count=COAL_NEED)
    scene.loc('Furnace', ['Use'], tile=FURNACE_STAND)
    return scene


def smelts():
    scene = smelting_scene()
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.ELEMENTAL_METAL.id)).to_be(True)
    expect(scene.logged('pulling the air-chamber Lever')).to_be(False)


test('ore and coal smelt without touching the air, when the furnace is already hot', smelts)


def smelt_gates():
    scene = Scene(FURNACE_STAND)
    give(scene, EW_ITEM.ELEMENTAL_METAL)
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(True)

    scene = Scene(FURNACE_STAND)
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('no Elemental ore')).to_be(True)

    scene = Scene(FURNACE_STAND)
    give(scene, EW_ITEM.ELEMENTAL_ORE)
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged(f'need {COAL_NEED} Coal')).to_be(True)


test('smelting needs ore and coal, and skips with a bar held', smelt_gates)


def furnace_refusals():
    scene = smelting_scene([workshop.FURNACE_NEED_COAL])
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('need 4 Coal in the pack')).to_be(True)

    scene = smelting_scene([workshop.FURNACE_COLD])
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('light it with lava first')).to_be(True)


test('a furnace asking for coal or lava fails with its reason', furnace_refusals)


def needs_heat():
    scene = smelting_scene([workshop.FURNACE_NEEDS_HEAT])
    scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(workshop.AIR_PUMPING))
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(True)
    expect(scene.logged('pulling the air-chamber Lever')).to_be(True)


test('a furnace wanting more heat gets the air, then smelts', needs_heat)


def air_was_already_on():
    scene = smelting_scene([workshop.FURNACE_NEEDS_HEAT])
    answers = [workshop.AIR_STOPPED, workshop.AIR_PUMPING]
    scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(answers.pop(0)))
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(True)
    expect(scene.logged('re-pulling to restore blast')).to_be(True)
    expect(answers).to_have_length(0)


test('a pull that stopped a running blast is pulled again', air_was_already_on)


def air_does_nothing():
    scene = smelting_scene([workshop.FURNACE_NEEDS_HEAT])
    scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(workshop.AIR_NOTHING))
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('water wheel / bellows may not be ready')).to_be(True)


test('an air lever that does nothing means the wheel or bellows are not ready', air_does_nothing)


def smelt_step_failures():
    scene = smelting_scene(ore_ok=False)
    scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(workshop.AIR_PUMPING))
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('pulling the air-chamber Lever')).to_be(True)

    # No furnace in range.
    scene = smelting_scene()
    scene.locs = []
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)

    # The walk fails both times.
    scene = smelting_scene()
    scene.no_walk = [BELLOWS_STAND]
    scene.at = ROCK_STAND
    scene.walk_ok = False
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)


test('a refused use, no furnace, or failed walks fail after trying the air once', smelt_step_failures)


def furnace_says_nothing():
    scene = Scene(FURNACE_STAND)
    scene.item(EW_ITEM.ELEMENTAL_ORE.id, 'Elemental ore')
    scene.item(EW_ITEM.COAL.id, 'Coal', count=COAL_NEED)
    scene.loc('Furnace', ['Use'], tile=FURNACE_STAND)
    scene.loc('Lever', ['Pull'], effect=lambda op: scene.say(workshop.AIR_PUMPING))
    expect(run_wait(workshop.smelt_elemental_bar(scene.log))).to_be(False)
    expect(scene.logged('pulling the air-chamber Lever')).to_be(True)


test('a silent furnace is treated like one wanting heat, and fails if that does not help', furnace_says_nothing)


def smith_kit(scene):
    scene.item(EW_ITEM.ELEMENTAL_METAL.id, 'Elemental metal', on_use=lambda target: give(scene, EW_ITEM.ELEMENTAL_SHIELD) and True)
    give(scene, EW_ITEM.BATTERED_BOOK)
    give(scene, EW_ITEM.HAMMER)
    scene.loc('Workbench', ['Use'], tile=WORKBENCH_STAND)


def smiths():
    scene = Scene(WORKBENCH_STAND)
    smith_kit(scene)
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(True)
    expect(scene.has(EW_ITEM.ELEMENTAL_SHIELD.id)).to_be(True)


test('the metal, book and hammer make the shield at the workbench', smiths)


def smith_gates():
    scene = Scene(WORKBENCH_STAND)
    give(scene, EW_ITEM.ELEMENTAL_SHIELD)
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(True)

    scene = Scene(WORKBENCH_STAND)
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(False)
    expect(scene.logged('no Elemental metal')).to_be(True)

    scene = Scene(WORKBENCH_STAND)
    give(scene, EW_ITEM.ELEMENTAL_METAL)
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(False)
    expect(scene.logged('need the Battered book')).to_be(True)

    scene = Scene(WORKBENCH_STAND)
    give(scene, EW_ITEM.ELEMENTAL_METAL)
    give(scene, EW_ITEM.BATTERED_BOOK)
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(False)
    expect(scene.logged('need a Hammer')).to_be(True)

    scene = Scene(ROCK_STAND)
    smith_kit(scene)
    scene.walk_ok = False
    expect(run_wait(workshop.smith_elemental_shield(scene.log))).to_be(False)


test('smithing checks for the shield, the metal, the book and the hammer, and the walk', smith_gates)

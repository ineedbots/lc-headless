"""Plague City's legs against spied facades: the crossings between Ardougne's pockets, the east side's errands and
the west side's doors, each through its success and its failures."""

import rs2004.quests.defs.plaguecity.east as east
import rs2004.quests.defs.plaguecity.travel as travel
import rs2004.quests.defs.plaguecity.west as west
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.quests.defs.plaguecity.areas import PC_ITEM, PC_LOC, PC_NPC, PC_TILE
from rs2004.reach import reach
from rs2004.traversal import traversal

EAST = Tile(2616, 3332, 0)
WEST = Tile(2540, 3305, 0)
SEWER = Tile(2530, 9703, 0)
UPSTAIRS = Tile(2529, 3331, 1)
CELLAR = Tile(2541, 9672, 0)
BRAVEK_ROOM = Tile(2535, 3314, 0)
PLAGUE_HOUSE = Tile(2534, 3270, 0)


def result(value):
    return value
    yield


class City:
    """The player among Ardougne's pockets, with what the pack, the scene and the dialogue hold."""

    def __init__(self, at):
        self.at = at
        self.pack = []
        self.locs = []
        self.ground = []
        self.npcs = []
        self.walk_ok = True
        self.walks = []
        self.equip_ok = True
        self.dialog = 'done'
        self.talk_ok = True
        self.talks = []
        self.chat_open = False
        self.lines = []
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(equipment, 'equip', impl=lambda name: result(self.equip_ok))
        spy_on(reach, 'npc_dialog', impl=lambda npc, near, log=None: result(self.dialog))
        spy_on(direct_navigator, 'walk_to', impl=self.direct)
        spy_on(chat_dialog, 'is_open', impl=lambda: self.chat_open)
        spy_on(chat_dialog, 'can_continue', returns=False)
        for module in [travel, east, west]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
        spy_on(travel, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        spy_on(east, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        spy_on(east, 'talk_strict', impl=self.talk)
        spy_on(west, 'drive_choice', impl=lambda prefer, log: result(True))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, tile, radius=2, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def direct(self, tile, radius=2, timeout_ms=45000, run=False):
        self.at = tile
        return True
        yield

    def talk(self, npc, prefer, log):
        self.talks.append(npc)
        return self.talk_ok
        yield

    def hold(self, item, use_on=None, interact=None):
        held = Fake(id=item.id, name=item.name, count=1, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(held)
        return held

    def drop(self, item):
        self.pack = [held for held in self.pack if held.id != item.id]

    def loc(self, id, ops=None, interact=None):
        made = Fake(id=id, name='Loc', actions=lambda: ops if ops is not None else ['Open', 'Search', 'Climb', 'Climb-down', 'Walk-up', 'Walk-Up', 'Walk-down', 'Walk-Down'],
                    distance=lambda: 1, interact=interact if interact is not None else (lambda op: True))
        self.locs.append(made)
        return made

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go

    def swaps(self, have, gives):
        def swap(*args):
            self.drop(have)
            self.hold(gives)
            return True
        return swap


def classifies_and_finds():
    city = City(EAST)
    expect(travel.area()).to_be('east')
    city.loc(PC_LOC.MUD_PILE)
    expect(travel.loc_by_id(PC_LOC.MUD_PILE, 'Climb', 8)).to_be_truthy()
    expect(travel.loc_by_id(PC_LOC.MUD_PATCH, None, 8)).to_be_falsy()
    city.loc(PC_LOC.MUD_PATCH[1])
    expect(travel.loc_by_id(PC_LOC.MUD_PATCH, None, 8)).to_be_truthy()
    city.at = PC_TILE.GARDEN
    expect(run_wait(travel.walk_to(PC_TILE.GARDEN, 1, city.log))).to_be(True)
    expect(len(city.walks)).to_be(0)
    expect(run_wait(travel.walk_to(PC_TILE.FOUNTAIN, 1, city.log))).to_be(True)
    expect(city.walks).to_equal([PC_TILE.FOUNTAIN])


test('the areas, loc lookups by one id or several, and walks that are already there', classifies_and_finds)


def digs_into_the_sewer():
    city = City(SEWER)
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(True)
    city.at = EAST
    city.walk_ok = False
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(False)
    expect(city.logged('no Spade')).to_be(True)
    city.hold(PC_ITEM.SPADE)
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(False)
    expect(city.logged('no Mud patch')).to_be(True)
    city.pack = []
    city.hold(PC_ITEM.SPADE, use_on=lambda other: False)
    city.loc(PC_LOC.MUD_PATCH[0])
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(False)
    city.pack = []
    city.hold(PC_ITEM.SPADE, use_on=city.moves(PC_TILE.SEWER_LANDING))
    expect(run_wait(travel.dig_into_sewer(city.log))).to_be(True)
    expect(travel.area()).to_be('sewer')


test('the garden dig needs the spade and the mud patch, and lands in the sewer', digs_into_the_sewer)


def climbs_and_squeezes():
    city = City(EAST)
    expect(run_wait(travel.climb_mud_pile(city.log))).to_be(True)
    city.at = SEWER
    city.walk_ok = False
    expect(run_wait(travel.climb_mud_pile(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(travel.climb_mud_pile(city.log))).to_be(False)
    expect(city.logged('no Mud pile')).to_be(True)
    city.loc(PC_LOC.MUD_PILE, interact=city.moves(EAST))
    expect(run_wait(travel.climb_mud_pile(city.log))).to_be(True)

    city = City(WEST)
    expect(run_wait(travel.squeeze_pipe(city.log))).to_be(True)
    city.at = SEWER
    city.equip_ok = False
    expect(run_wait(travel.squeeze_pipe(city.log))).to_be(False)
    expect(city.logged('has to be worn')).to_be(True)
    city.equip_ok = True
    city.walk_ok = False
    expect(run_wait(travel.squeeze_pipe(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(travel.squeeze_pipe(city.log))).to_be(False)
    expect(city.logged('no Sewer pipe')).to_be(True)
    city.loc(PC_LOC.SEWER_PIPE, interact=city.moves(WEST))
    expect(run_wait(travel.squeeze_pipe(city.log))).to_be(True)


test('the mud pile climbs out east, and the pipe needs the mask worn to squeeze west', climbs_and_squeezes)


def drops_through_the_manhole():
    city = City(SEWER)
    expect(run_wait(travel.drop_manhole(city.log))).to_be(True)
    city.at = WEST
    city.walk_ok = False
    expect(run_wait(travel.drop_manhole(city.log))).to_be(False)
    city.walk_ok = True
    city.loc(PC_LOC.MANHOLE_SHUT, interact=lambda op: False)
    expect(run_wait(travel.drop_manhole(city.log))).to_be(False)
    city.locs = []

    def opens(op):
        city.locs = []
        city.loc(PC_LOC.MANHOLE_OPEN, interact=city.moves(SEWER))
        return True
    city.loc(PC_LOC.MANHOLE_SHUT, interact=opens)
    expect(run_wait(travel.drop_manhole(city.log))).to_be(True)
    city.at = WEST
    city.locs = []
    expect(run_wait(travel.drop_manhole(city.log))).to_be(False)
    expect(city.logged('no open Manhole')).to_be(True)


test('the manhole is opened when its cover is back, then climbed down', drops_through_the_manhole)


def takes_the_stairs():
    city = City(UPSTAIRS)
    city.walk_ok = False
    expect(run_wait(travel.leave_upstairs(city.log))).to_be(False)
    city.walk_ok = True
    city.at = UPSTAIRS
    expect(run_wait(travel.leave_upstairs(city.log))).to_be(False)
    expect(city.logged('no Rehnison stairs down')).to_be(True)
    city.loc(PC_LOC.REHNISON_STAIRS_DOWN, interact=city.moves(WEST))
    city.at = UPSTAIRS
    expect(run_wait(travel.leave_upstairs(city.log))).to_be(True)

    city = City(CELLAR)
    city.walk_ok = False
    expect(run_wait(travel.leave_cellar(city.log))).to_be(False)
    city.walk_ok = True
    city.at = CELLAR
    expect(run_wait(travel.leave_cellar(city.log))).to_be(False)
    expect(city.logged('no plague house stairs up')).to_be(True)
    city.loc(PC_LOC.HOUSE_STAIRS_UP, interact=city.moves(WEST))
    city.at = CELLAR
    expect(run_wait(travel.leave_cellar(city.log))).to_be(True)

    city = City(UPSTAIRS)
    expect(run_wait(travel.go_upstairs(city.log))).to_be(True)
    city.at = WEST
    city.walk_ok = False
    expect(run_wait(travel.go_upstairs(city.log))).to_be(False)
    city.walk_ok = True
    city.at = WEST
    expect(run_wait(travel.go_upstairs(city.log))).to_be(False)
    city.loc(PC_LOC.REHNISON_STAIRS_UP, interact=city.moves(UPSTAIRS))
    city.at = WEST
    expect(run_wait(travel.go_upstairs(city.log))).to_be(True)

    city = City(CELLAR)
    expect(run_wait(travel.go_cellar(city.log))).to_be(True)
    city.at = WEST
    city.walk_ok = False
    expect(run_wait(travel.go_cellar(city.log))).to_be(False)
    city.walk_ok = True
    city.at = WEST
    expect(run_wait(travel.go_cellar(city.log))).to_be(False)
    city.loc(PC_LOC.HOUSE_STAIRS_DOWN, interact=city.moves(CELLAR))
    city.at = WEST
    expect(run_wait(travel.go_cellar(city.log))).to_be(True)


test("the Rehnisons' stairs and the plague house's both ways", takes_the_stairs)


def leg(calls, name, ok=True):
    def run(log):
        calls.append(name)
        return ok
        yield
    return run


def routes_between_pockets():
    city = City(EAST)
    expect(run_wait(travel.go_east(city.log))).to_be(True)
    calls = []
    for name in ['leave_upstairs', 'leave_cellar', 'drop_manhole', 'climb_mud_pile', 'dig_into_sewer', 'squeeze_pipe']:
        spy_on(travel, name, impl=leg(calls, name))
    for at, want in [[UPSTAIRS, 'leave_upstairs'], [CELLAR, 'leave_cellar'], [SEWER, 'climb_mud_pile']]:
        city.at = at
        expect(run_wait(travel.go_east(city.log))).to_be(True)
        expect(calls[-1]).to_be(want)
    city.at = WEST
    expect(run_wait(travel.go_east(city.log))).to_be(True)
    expect(calls[-2:]).to_equal(['drop_manhole', 'climb_mud_pile'])
    spy_on(travel, 'drop_manhole', impl=leg(calls, 'drop_manhole', False))
    expect(run_wait(travel.go_east(city.log))).to_be(False)
    city.at = Tile(2540, 3305, 2)
    expect(run_wait(travel.go_east(city.log))).to_be(False)
    expect(run_wait(travel.go_sewer(city.log))).to_be(False)
    expect(run_wait(travel.go_west(city.log))).to_be(False)

    calls = []
    for name in ['leave_upstairs', 'leave_cellar', 'drop_manhole', 'climb_mud_pile', 'dig_into_sewer', 'squeeze_pipe']:
        spy_on(travel, name, impl=leg(calls, name))
    for at, want in [[EAST, 'dig_into_sewer'], [WEST, 'drop_manhole'], [UPSTAIRS, 'leave_upstairs'], [CELLAR, 'leave_cellar']]:
        city.at = at
        expect(run_wait(travel.go_sewer(city.log))).to_be(True)
        expect(calls[-1]).to_be(want)
    city.at = SEWER
    expect(run_wait(travel.go_sewer(city.log))).to_be(True)
    for at, want in [[UPSTAIRS, 'leave_upstairs'], [CELLAR, 'leave_cellar'], [SEWER, 'squeeze_pipe']]:
        city.at = at
        expect(run_wait(travel.go_west(city.log))).to_be(True)
        expect(calls[-1]).to_be(want)
    city.at = WEST
    expect(run_wait(travel.go_west(city.log))).to_be(True)
    city.at = EAST
    expect(run_wait(travel.go_west(city.log))).to_be(True)
    expect(calls[-2:]).to_equal(['dig_into_sewer', 'squeeze_pipe'])
    spy_on(travel, 'dig_into_sewer', impl=leg(calls, 'dig_into_sewer', False))
    expect(run_wait(travel.go_west(city.log))).to_be(False)


test('each pocket has its way east, down into the sewer and west, and a two-hop leg stops when its first fails', routes_between_pockets)


def talks_on_the_east_side():
    city = City(EAST)
    city.walk_ok = False
    expect(run_wait(east.talk_at(PC_NPC.EDMOND, PC_TILE.EDMOND, [], city.log))).to_be(False)
    city.walk_ok = True
    city.dialog = 'failed'
    expect(run_wait(east.talk_at(PC_NPC.EDMOND, PC_TILE.EDMOND, [], city.log))).to_be(False)
    expect(city.logged('no dialogue with Edmond')).to_be(True)
    city.dialog = 'done'
    for leg in [east.start_quest, east.give_dwellberries, east.ask_about_digging, east.pull_the_grill, east.thank_edmond]:
        expect(run_wait(leg(city.log))).to_be(True)
    expect(city.talks).to_equal([PC_NPC.EDMOND, PC_NPC.ALRENA, PC_NPC.EDMOND, PC_NPC.EDMOND, PC_NPC.EDMOND])


test("Edmond's and Alrena's talks walk to them first and need the dialogue to open", talks_on_the_east_side)


def fills_and_pours():
    city = City(EAST)
    city.walk_ok = False
    expect(run_wait(east.fill_buckets(city.log))).to_be(False)
    city.walk_ok = True
    city.hold(PC_ITEM.BUCKET)
    expect(run_wait(east.fill_buckets(city.log))).to_be(False)
    city.locs = [Fake(id=0, name='Fountain', actions=lambda: [], distance=lambda: 1, interact=lambda op: True)]
    city.pack = []
    city.hold(PC_ITEM.BUCKET, use_on=lambda other: False)
    expect(run_wait(east.fill_buckets(city.log))).to_be(False)
    city.pack = []
    city.hold(PC_ITEM.BUCKET, use_on=lambda other: True)
    expect(run_wait(east.fill_buckets(city.log))).to_be(False)
    city.pack = []
    for i in range(2):
        city.hold(PC_ITEM.BUCKET, use_on=city.swaps(PC_ITEM.BUCKET, PC_ITEM.BUCKET_WATER))
    expect(run_wait(east.fill_buckets(city.log))).to_be(True)
    expect(city.logged('filled')).to_be(True)

    city = City(EAST)
    city.walk_ok = False
    expect(run_wait(east.pour_water(city.log))).to_be(False)
    city.walk_ok = True
    city.hold(PC_ITEM.BUCKET_WATER)
    expect(run_wait(east.pour_water(city.log))).to_be(False)
    expect(city.logged('no Mud patch or no Bucket of water')).to_be(True)
    city.loc(PC_LOC.MUD_PATCH[0])
    city.pack = []
    city.hold(PC_ITEM.BUCKET_WATER, use_on=lambda other: False)
    expect(run_wait(east.pour_water(city.log))).to_be(False)
    city.pack = []
    city.hold(PC_ITEM.BUCKET_WATER, use_on=lambda other: True)
    expect(run_wait(east.pour_water(city.log))).to_be(False)
    expect(city.logged('took no more water')).to_be(True)
    city.pack = []
    city.hold(PC_ITEM.BUCKET_WATER, use_on=city.swaps(PC_ITEM.BUCKET_WATER, PC_ITEM.BUCKET))
    expect(run_wait(east.pour_water(city.log))).to_be(True)


test('the buckets fill at the fountain and pour on the soil until it takes no more', fills_and_pours)


def takes_from_the_house():
    city = City(EAST)
    city.hold(PC_ITEM.SPADE)
    expect(run_wait(east.take_from_house(PC_ITEM.SPADE, city.log))).to_be(True)
    city.pack = []
    city.walk_ok = False
    expect(run_wait(east.take_from_house(PC_ITEM.SPADE, city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(east.take_from_house(PC_ITEM.SPADE, city.log))).to_be(False)
    expect(city.logged("no Spade on the floor")).to_be(True)
    city.ground = [Fake(name='Spade', distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(east.take_from_house(PC_ITEM.SPADE, city.log))).to_be(False)

    def picks(op):
        city.hold(PC_ITEM.SPADE)
        return True
    city.ground = [Fake(name='Spade', distance=lambda: 1, interact=picks)]
    expect(run_wait(east.take_from_house(PC_ITEM.SPADE, city.log))).to_be(True)


test("the spade and the picture come off Edmond's floor from inside the house", takes_from_the_house)


def searches_the_cupboard():
    city = City(EAST)
    city.walk_ok = False
    expect(run_wait(east.search_cupboard(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(east.search_cupboard(city.log))).to_be(False)
    expect(city.logged("no cupboard")).to_be(True)

    def opens(op):
        city.locs = []
        city.loc(PC_LOC.CUPBOARD_OPEN)
        return True
    city.loc(PC_LOC.CUPBOARD_SHUT, interact=opens)
    expect(run_wait(east.search_cupboard(city.log))).to_be(True)
    city.locs = []
    city.loc(PC_LOC.CUPBOARD_OPEN, interact=lambda op: False)
    expect(run_wait(east.search_cupboard(city.log))).to_be(False)
    city.locs = []

    def gives(op):
        city.hold(PC_ITEM.GAS_MASK)
        return True
    city.loc(PC_LOC.CUPBOARD_OPEN, interact=gives)
    expect(run_wait(east.search_cupboard(city.log))).to_be(True)


test("Alrena's cupboard is opened, then searched for the spare mask", searches_the_cupboard)


def reads_the_scroll_and_ties_the_rope():
    city = City(EAST)
    expect(run_wait(east.read_scroll(city.log))).to_be(True)
    city.hold(PC_ITEM.ARDOUGNE_SCROLL, interact=lambda op: False)
    expect(run_wait(east.read_scroll(city.log))).to_be(False)
    city.pack = []
    city.hold(PC_ITEM.ARDOUGNE_SCROLL, interact=lambda op: True)
    expect(run_wait(east.read_scroll(city.log))).to_be(False)
    expect(city.logged('would not read')).to_be(True)
    city.pack = []

    def learns(op):
        city.pack = []
        return True
    city.hold(PC_ITEM.ARDOUGNE_SCROLL, interact=learns)
    expect(run_wait(east.read_scroll(city.log))).to_be(True)

    city = City(SEWER)
    city.walk_ok = False
    expect(run_wait(east.tie_rope(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(east.tie_rope(city.log))).to_be(False)
    expect(city.logged('no Sewer pipe')).to_be(True)
    city.loc(PC_LOC.SEWER_PIPE)
    expect(run_wait(east.tie_rope(city.log))).to_be(False)
    expect(city.logged('no Rope')).to_be(True)
    city.hold(PC_ITEM.ROPE, use_on=lambda other: False)
    expect(run_wait(east.tie_rope(city.log))).to_be(False)
    city.pack = []

    def ties(other):
        city.pack = []
        return True
    city.hold(PC_ITEM.ROPE, use_on=ties)
    expect(run_wait(east.tie_rope(city.log))).to_be(True)


test('the reward scroll is read, and the rope is tied to the grill from the pipe', reads_the_scroll_and_ties_the_rope)


def answers_and_opens_doors():
    city = City(WEST)
    expect(run_wait(west.answer_prompt([], city.log))).to_be(True)
    city.chat_open = True
    expect(run_wait(west.answer_prompt([], city.log))).to_be(True)
    city.walk_ok = False
    expect(run_wait(west.open_door(PC_LOC.REHNISON_DOOR, PC_TILE.REHNISON_DOOR, [], city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(west.open_door(PC_LOC.REHNISON_DOOR, PC_TILE.REHNISON_DOOR, [], city.log))).to_be(True)
    expect(city.logged('already open')).to_be(True)
    city.loc(PC_LOC.REHNISON_DOOR, interact=lambda op: False)
    expect(run_wait(west.open_door(PC_LOC.REHNISON_DOOR, PC_TILE.REHNISON_DOOR, [], city.log))).to_be(False)
    city.locs = []
    city.loc(PC_LOC.REHNISON_DOOR)
    expect(run_wait(west.open_door(PC_LOC.REHNISON_DOOR, PC_TILE.REHNISON_DOOR, [], city.log))).to_be(True)


test('a door the quest answers is opened and its prompt driven, and an open one is left', answers_and_opens_doors)


def follows_the_rehnisons():
    city = City(WEST)
    expect(run_wait(west.show_picture(city.log))).to_be(True)
    expect(run_wait(west.ask_parents(city.log))).to_be(True)
    city.hold(PC_ITEM.TURNIP_BOOK)
    spy_on(west, 'open_door', impl=lambda id, near, prefer, log: result(False))
    expect(run_wait(west.return_book(city.log))).to_be(False)
    expect(run_wait(west.enter_rehnisons(city.log))).to_be(False)

    def hands_over(id, near, prefer, log):
        city.pack = []
        return True
        yield
    spy_on(west, 'open_door', impl=hands_over)
    city.hold(PC_ITEM.TURNIP_BOOK)
    expect(run_wait(west.enter_rehnisons(city.log))).to_be(True)
    city.talk_ok = False
    expect(run_wait(west.enter_rehnisons(city.log))).to_be(False)
    expect(city.logged('asking Jethick for another book')).to_be(True)
    spy_on(west, 'go_upstairs', impl=lambda log: result(False))
    expect(run_wait(west.ask_milli(city.log))).to_be(False)
    spy_on(west, 'go_upstairs', impl=lambda log: result(True))
    city.talk_ok = True
    expect(run_wait(west.ask_milli(city.log))).to_be(True)


test('the book goes back to the Rehnisons, who are then asked, or Jethick asked again for another', follows_the_rehnisons)


def knocks_at_the_plague_house():
    city = City(WEST)
    city.walk_ok = False
    expect(run_wait(west.knock_plague_door([], city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(west.knock_plague_door([], city.log))).to_be(False)
    expect(city.logged('the op does nothing without one')).to_be(True)
    city.npcs = [Fake(name=PC_NPC.MOURNER, distance=lambda: 20)]
    expect(run_wait(west.knock_plague_door([], city.log))).to_be(False)
    city.npcs = [Fake(name=PC_NPC.MOURNER, distance=lambda: 5)]
    expect(run_wait(west.ask_about_clearance(city.log))).to_be(True)
    city.loc(PC_LOC.PLAGUE_DOOR, interact=lambda op: False)
    expect(run_wait(west.knock_plague_door([], city.log))).to_be(False)
    city.locs = []
    city.loc(PC_LOC.PLAGUE_DOOR)
    expect(run_wait(west.knock_plague_door([], city.log))).to_be(True)


test('the plague house door is only knocked with a mourner in earshot', knocks_at_the_plague_house)


def reaches_bravek():
    city = City(WEST)
    city.walk_ok = False
    expect(run_wait(west.ask_clerk(city.log))).to_be(False)
    city.walk_ok = True
    expect(run_wait(west.ask_clerk(city.log))).to_be(False)
    expect(city.logged('too far for the clerk')).to_be(True)
    city.npcs = [Fake(name=PC_NPC.BRAVEK, distance=lambda: 3)]
    expect(run_wait(west.ask_clerk(city.log))).to_be(True)

    city.at = BRAVEK_ROOM
    expect(west.in_bravek_room()).to_be(True)
    expect(run_wait(west.reach_bravek(city.log))).to_be(True)
    city.at = WEST
    spy_on(west, 'open_door', impl=lambda id, near, prefer, log: result(False))
    expect(run_wait(west.reach_bravek(city.log))).to_be(False)
    spy_on(west, 'open_door', impl=lambda id, near, prefer, log: result(True))
    expect(run_wait(west.reach_bravek(city.log))).to_be(False)
    expect(city.logged('still busy')).to_be(True)
    expect(run_wait(west.ask_bravek_for_recipe(city.log))).to_be(False)
    expect(run_wait(west.give_hangover_cure(city.log))).to_be(False)

    def lets_in(id, near, prefer, log):
        city.at = BRAVEK_ROOM
        return True
        yield
    spy_on(west, 'open_door', impl=lets_in)
    expect(run_wait(west.ask_bravek_for_recipe(city.log))).to_be(True)
    city.at = WEST
    expect(run_wait(west.give_hangover_cure(city.log))).to_be(True)
    spy_on(west, 'ask_clerk', impl=lambda log: result(False))
    expect(run_wait(west.get_audience(city.log))).to_be(False)
    spy_on(west, 'ask_clerk', impl=lambda log: result(True))
    city.at = WEST
    expect(run_wait(west.get_audience(city.log))).to_be(True)


test("the clerk calls Bravek in, and his door lets the bot through only then", reaches_bravek)


def rescues_elena():
    city = City(WEST)
    expect(west.inside_plague_house()).to_be(False)
    city.at = PLAGUE_HOUSE
    expect(west.inside_plague_house()).to_be(True)
    city.at = Tile(2536, 3272, 0)
    expect(west.inside_plague_house()).to_be(True)
    city.at = WEST
    spy_on(west, 'knock_plague_door', impl=lambda prefer, log: result(False))
    expect(run_wait(west.enter_plague_house(city.log))).to_be(False)
    expect(run_wait(west.rescue_elena(city.log))).to_be(False)
    spy_on(west, 'knock_plague_door', impl=lambda prefer, log: result(True))
    spy_on(direct_navigator, 'walk_to', impl=lambda tile, radius=2, timeout_ms=45000, run=False: result(True))
    expect(run_wait(west.enter_plague_house(city.log))).to_be(False)
    expect(city.logged('did not turn their back')).to_be(True)
    spy_on(direct_navigator, 'walk_to', impl=city.direct)
    expect(run_wait(west.enter_plague_house(city.log))).to_be(True)

    city = City(PLAGUE_HOUSE)
    city.walk_ok = False
    expect(run_wait(west.search_barrel(city.log))).to_be(False)
    expect(run_wait(west.rescue_elena(city.log))).to_be(False)
    city.walk_ok = True
    city.at = PLAGUE_HOUSE
    expect(run_wait(west.search_barrel(city.log))).to_be(False)
    expect(city.logged('no Barrel')).to_be(True)

    def finds_key(op):
        city.hold(PC_ITEM.ELENA_KEY)
        return True
    city.loc(PC_LOC.BARREL, interact=finds_key)
    expect(run_wait(west.search_barrel(city.log))).to_be(True)

    spy_on(west, 'go_cellar', impl=lambda log: result(False))
    expect(run_wait(west.free_elena(city.log))).to_be(False)
    spy_on(west, 'go_cellar', impl=lambda log: result(True))
    city.walk_ok = False
    expect(run_wait(west.free_elena(city.log))).to_be(False)
    city.walk_ok = True
    city.pack = []
    city.locs = []
    city.loc(PC_LOC.ELENA_GATE)
    expect(run_wait(west.free_elena(city.log))).to_be(False)
    expect(city.logged("no key for Elena's cell")).to_be(True)
    city.hold(PC_ITEM.ELENA_KEY, use_on=lambda other: False)
    expect(run_wait(west.free_elena(city.log))).to_be(False)
    city.pack = []
    city.hold(PC_ITEM.ELENA_KEY)
    expect(run_wait(west.free_elena(city.log))).to_be(True)
    expect(city.talks[-1]).to_be(PC_NPC.ELENA)
    city.at = CELLAR
    expect(run_wait(west.rescue_elena(city.log))).to_be(True)


test('the plague house is entered with the warrant, the barrel gives the key, and the key opens her cell', rescues_elena)


def leaves_with_the_scroll():
    import rs2004.quests.defs.plaguecity as plaguecity
    city = City(WEST)
    spy_on(plaguecity, 'go_east', impl=lambda log: result(False))
    expect(run_wait(plaguecity.exit_plague_city(city.log))).to_be(False)
    spy_on(plaguecity, 'go_east', impl=lambda log: result(True))
    spy_on(plaguecity, 'read_scroll', impl=lambda log: result(True))
    expect(run_wait(plaguecity.exit_plague_city(city.log))).to_be(True)


test("the quest's exit walks back east and reads the reward scroll", leaves_with_the_scroll)

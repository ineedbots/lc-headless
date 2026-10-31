"""Sheep Herder's scene grid, which a live run found outrunning the script's step budget when every route search asked
the client for each tile again, and the herd, gate, poison and furnace legs."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.messages import game_messages
from rs2004.navigation import reachability
from rs2004.quests.defs.sheepherder import herd, pen
from rs2004.quests.defs.sheepherder.areas import (BONES_OBJ, FEED_OBJ, GATE_INSIDE, GATE_LOC, GATE_OUTSIDE, PEN, PROD_OBJ,
                                                  SHEEP_SPAWN, in_box, sheep_name)
from rs2004.quests.defs.sheepherder.herd import SceneGrid
from rs2004.traversal import traversal


def asks_each_tile_once():
    walks = spy_on(reachability, 'walkable', returns=True)
    steps = spy_on(reachability, 'can_step', returns=False)
    grid = SceneGrid()
    for i in range(3):
        expect(grid.walkable(2600, 3350)).to_be(True)
        expect(grid.can_step(2600, 3350, 0, -1)).to_be(False)
    expect(grid.can_step(2600, 3350, 1, 0)).to_be(False)
    expect(len(walks.calls)).to_be(1)
    expect(len(steps.calls)).to_be(2)
    grid.reset()
    grid.walkable(2600, 3350)
    expect(len(walks.calls)).to_be(2)


test('the scene grid asks the client once per tile and direction until reset', asks_each_tile_once)


# The herd, the gate, the prod, the poison and the furnace.

EAST = Record({'dx': 1, 'dz': 0})
FIELD = Tile(2585, 3361, 0)
OUTSIDE_PEN = Tile(2590, 3370, 0)
INSIDE_PEN = Tile(2600, 3358, 0)


def result(value):
    return value
    yield


class Sheep:
    """A diseased sheep that a Prod moves one tile directly away from the prodder, who steps into its old tile;
    on_prod(op) replaces that."""

    def __init__(self, farm, n, at, moves=True):
        self.farm = farm
        self.name = sheep_name(n)
        self.at = at
        self.moves = moves
        self.prods = 0
        self.on_prod = None

    def tile(self):
        return self.at

    def actions(self):
        return ['Prod']

    def distance(self):
        return max(abs(self.at.x - self.farm.at.x), abs(self.at.z - self.farm.at.z))

    def interact(self, op):
        self.prods += 1
        if self.on_prod is not None:
            return self.on_prod(op)
        if self.moves:
            me = self.farm.at
            step_x = self.at.x - me.x
            step_z = self.at.z - me.z
            self.farm.at = self.at
            self.at = Tile(self.at.x + step_x, self.at.z + step_z, 0)
        return True


class Farm:
    """The player, the sheep, the pen gate and the ground around the enclosure."""

    def __init__(self, at=None):
        self.at = at if at is not None else FIELD
        self.pack = []
        self.sheep = []
        self.locs = []
        self.ground = []
        self.walks = []
        self.walk_ok = True
        self.lands = None
        self.modal = False
        self.messages = []
        self.directions = [EAST]
        self.lines = []
        self.chat = FakeChat().install(chat_dialog)
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(npcs, 'query', impl=querying(lambda: self.sheep))
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(equipment, 'equip', impl=lambda name: result(True))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(direct_navigator, 'walk_to', impl=self.step_to)
        spy_on(reachability, 'walkable', returns=True)
        spy_on(reachability, 'can_step', returns=True)
        spy_on(modals, 'is_open', impl=lambda: self.modal)
        spy_on(modals, 'close', impl=self.close)
        spy_on(game_messages, 'mark', impl=lambda: len(self.messages))
        spy_on(game_messages, 'saw_since', impl=lambda mark, text: any([text in m for m in self.messages[mark:]]))
        spy_on(herd, 'route_cost', impl=lambda npc: 10)
        spy_on(herd, 'herd_directions', impl=lambda grid, tile, zone: list(self.directions))
        spy_on(pen, 'settle_scene', impl=instant_ticks)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def close(self):
        self.modal = False
        return True
        yield

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = self.lands if self.lands is not None else tile
        return self.walk_ok
        yield

    def step_to(self, tile, radius=2, timeout_ms=45000, run=False):
        if self.walk_ok:
            self.at = tile
        return True
        yield

    def hold(self, id, use_on=None):
        item = Fake(id=id, count=1, use_on=use_on if use_on is not None else (lambda other: True))
        self.pack.append(item)
        return item

    def drop(self, id):
        self.pack = [item for item in self.pack if item.id != id]

    def gate(self, interact=None):
        return Fake(id=GATE_LOC[0], name='Gate', actions=lambda: ['Open'], distance=lambda: 1,
                    interact=interact if interact is not None else self.cross)

    def cross(self, op):
        self.at = GATE_INSIDE if self.at == GATE_OUTSIDE else GATE_OUTSIDE
        return True

    def bones(self, n, at=None, take=True):
        tile = at if at is not None else self.at
        id = BONES_OBJ[n]

        def pick(op):
            if take:
                self.ground = [item for item in self.ground if item.id != id]
                self.hold(id)
            return take
        return Fake(id=id, name='Bones', distance=lambda: 2, tile=lambda: tile, interact=pick)


def herds():
    farm = Farm()
    sheep = Sheep(farm, 1, Tile(2589, 3361, 0))
    farm.sheep = [sheep]
    expect(run_wait(herd.herd_to_pen(1, farm.log))).to_be(True)
    expect(in_box(PEN, sheep.at)).to_be(True)
    expect(sheep.prods).to_be(6)
    expect(farm.logged('is in the enclosure after 6 push(es)')).to_be(True)


test('a sheep is pushed east into the gate zone and over into the enclosure', herds)


def finds_field():
    farm = Farm(OUTSIDE_PEN)
    expect(run_wait(herd.herd_to_pen(2, farm.log))).to_be(False)
    expect(farm.logged('not at its field')).to_be(True)
    expect(farm.walks).to_equal([SHEEP_SPAWN[2]])
    farm.walk_ok = False
    expect(run_wait(herd.herd_to_pen(2, farm.log))).to_be(False)
    farm.walk_ok = True
    spy_on(herd, 'route_cost', impl=lambda npc: None)
    farm.sheep = [Sheep(farm, 2, SHEEP_SPAWN[2])]
    expect(run_wait(herd.herd_to_pen(2, farm.log))).to_be(False)
    expect(farm.logged('no movable Diseased sheep 2 in range')).to_be(True)


test("a sheep out of range or trapped is looked for at its field, where an empty one waits out the respawn", finds_field)


def picks_nearest():
    farm = Farm()
    near = Sheep(farm, 1, Tile(2589, 3361, 0))
    far = Sheep(farm, 1, Tile(2570, 3361, 0))
    farm.sheep = [far, near]
    spy_on(herd, 'route_cost', impl=lambda npc: npc.at.distance_to(GATE_OUTSIDE))
    expect(run_wait(herd.pick_sheep(1))).to_be(near)


test('the copy with the shortest push route is the one herded', picks_nearest)


def pinned():
    farm = Farm()
    farm.sheep = [Sheep(farm, 3, Tile(2589, 3361, 0))]
    farm.directions = []
    expect(run_wait(herd.herd_to_pen(3, farm.log))).to_be(False)
    expect(farm.logged('stayed pinned at (2589,3361)')).to_be(True)


test('a sheep with no side to push from is waited on, then given up', pinned)


def refused():
    farm = Farm()
    farm.sheep = [Sheep(farm, 1, Tile(2589, 3361, 0), False)]
    expect(run_wait(herd.herd_to_pen(1, farm.log))).to_be(False)
    expect(farm.logged('refused 8 pushes near (2589,3361)')).to_be(True)
    farm = Farm()
    farm.sheep = [Sheep(farm, 1, Tile(2589, 3361, 0))]
    spy_on(direct_navigator, 'walk_to', impl=lambda tile, radius, ms: result(False))
    expect(run_wait(herd.herd_to_pen(1, farm.log))).to_be(False)
    expect(farm.logged('could not stand at (2588,3361)')).to_be(True)


test('a sheep that will not move, or a stand that cannot be reached, ends the herd', refused)


def strays():
    farm = Farm()
    sheep = Sheep(farm, 4, Tile(2589, 3361, 0), False)

    def drift(op):
        sheep.at = Tile(sheep.at.x, sheep.at.z + (1 if sheep.prods % 2 else -1), 0)
        return True
    sheep.on_prod = drift
    farm.sheep = [sheep]
    expect(run_wait(herd.herd_to_pen(4, farm.log))).to_be(False)
    expect(farm.logged('kept landing off the push axis')).to_be(True)
    expect(farm.logged('not penned within 260 pushes')).to_be(True)


test('a sheep that keeps drifting off the push axis is chased stand by stand until the budget runs out', strays)


def lost():
    farm = Farm()
    sheep = Sheep(farm, 1, Tile(2589, 3361, 0))

    def vanish(op):
        farm.sheep = []
        return True
    sheep.on_prod = vanish
    farm.sheep = [sheep]
    expect(run_wait(herd.herd_to_pen(1, farm.log))).to_be(False)
    expect(farm.logged('lost Diseased sheep 1 mid-herd')).to_be(True)
    farm.sheep = [Sheep(farm, 1, Tile(2589, 3361, 0))]
    farm.sheep[0].on_prod = lambda op: False
    expect(run_wait(herd.push_once(1, farm.sheep[0], EAST, farm.log))).to_be('refused')
    expect(farm.logged('no Prod op')).to_be(True)


test('a sheep that disappears mid-herd ends it', lost)


def clears():
    farm = Farm()
    expect(run_wait(herd.clear_refusal())).to_be(False)
    farm.modal = True
    farm.chat.pages = ['continue']
    expect(run_wait(herd.clear_refusal())).to_be(True)
    expect(farm.modal).to_be(False)
    expect(farm.chat.pages).to_equal([])
    farm.chat.pages = [['Yes', 'No']]
    expect(run_wait(herd.clear_refusal())).to_be(True)


test("a refusal's chat and message box are both cleared before the next push", clears)


def gate():
    farm = Farm(GATE_OUTSIDE)
    expect(run_wait(pen.enter_pen(farm.log))).to_be(False)
    expect(farm.logged('no enclosure gate')).to_be(True)
    farm.locs = [farm.gate(lambda op: False)]
    expect(run_wait(pen.enter_pen(farm.log))).to_be(False)
    farm.locs = [farm.gate()]
    expect(run_wait(pen.enter_pen(farm.log))).to_be(True)
    expect(run_wait(pen.enter_pen(farm.log))).to_be(True)
    expect(run_wait(pen.leave_pen(farm.log))).to_be(True)
    expect(farm.at).to_equal(GATE_OUTSIDE)
    farm.at = INSIDE_PEN
    farm.walk_ok = False
    expect(run_wait(pen.leave_pen(farm.log))).to_be(False)
    farm.walk_ok = True
    farm.locs = [farm.gate(lambda op: True)]
    expect(run_wait(pen.leave_pen(farm.log))).to_be(False)
    farm.at = OUTSIDE_PEN
    farm.lands = INSIDE_PEN
    expect(run_wait(pen.enter_pen(farm.log))).to_be(True)


test('the gate is crossed from its stand and judged by which side we land on', gate)


def prod():
    farm = Farm(GATE_OUTSIDE)
    farm.locs = [farm.gate()]
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(False)
    expect(farm.logged('no Prod on the barn floor')).to_be(True)
    farm.ground = [Fake(id=PROD_OBJ, distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(False)
    farm.ground = [Fake(id=PROD_OBJ, distance=lambda: 1, interact=lambda op: True)]
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(False)
    farm.ground = [Fake(id=PROD_OBJ, distance=lambda: 1, interact=lambda op: farm.hold(PROD_OBJ) is not None)]
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(True)
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(True)
    farm.pack = []
    farm.walk_ok = False
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(False)
    farm.at = GATE_OUTSIDE
    expect(run_wait(pen.fetch_prod(farm.log))).to_be(False)


test('the prod is taken off the barn floor inside the enclosure and wielded', prod)


def bones():
    farm = Farm(INSIDE_PEN)
    expect(run_wait(pen.take_bones(1, farm.log))).to_be(False)
    expect(farm.logged('no remains from Diseased sheep 1')).to_be(True)
    farm.ground = [farm.bones(1, Tile(2603, 3358, 0))]
    expect(run_wait(pen.take_bones(1, farm.log))).to_be(True)
    expect(farm.walks).to_equal([Tile(2603, 3358, 0)])
    expect(run_wait(pen.take_bones(1, farm.log))).to_be(True)
    farm.pack = []
    farm.ground = [farm.bones(1, take=False)]
    farm.walk_ok = False
    expect(run_wait(pen.take_bones(1, farm.log))).to_be(False)


test("a sheep's remains are walked to and picked up by their id", bones)


def poisons():
    farm = Farm(INSIDE_PEN)
    sheep = Sheep(farm, 2, Tile(2602, 3356, 0))
    farm.sheep = [sheep]

    def feed(target):
        farm.sheep = []
        farm.ground = [farm.bones(2)]
        return True
    farm.hold(FEED_OBJ, use_on=feed)
    expect(run_wait(pen.pen_and_kill(2, farm.log))).to_be(True)
    expect(farm.logged('feeding the poison to Diseased sheep 2')).to_be(True)
    expect(run_wait(pen.pen_and_kill(2, farm.log))).to_be(True)
    farm.pack = []
    farm.ground = [farm.bones(2)]
    expect(run_wait(pen.pen_and_kill(2, farm.log))).to_be(True)


test('a penned sheep is fed the poison and its remains taken in the same leg', poisons)


def poison_fails():
    farm = Farm(INSIDE_PEN)
    farm.sheep = [Sheep(farm, 2, Tile(2602, 3356, 0))]
    expect(run_wait(pen.poison(2, farm.log))).to_be(False)
    expect(farm.logged('no feed in the pack')).to_be(True)
    farm.hold(FEED_OBJ, use_on=lambda target: False)
    expect(run_wait(pen.poison(2, farm.log))).to_be(False)
    farm.walk_ok = False
    expect(run_wait(pen.poison(2, farm.log))).to_be(False)
    farm.walk_ok = True
    farm.sheep = []
    expect(run_wait(pen.poison(2, farm.log))).to_be(False)
    farm.at = OUTSIDE_PEN
    farm.walk_ok = False
    expect(run_wait(pen.poison(2, farm.log))).to_be(False)


test('the poisoning stops without feed, a refused use, a failed walk or a sheep gone', poison_fails)


def pens():
    farm = Farm(INSIDE_PEN)
    left = spy_on(pen, 'leave_pen', impl=lambda log: result(False))
    expect(run_wait(pen.pen_and_kill(3, farm.log))).to_be(False)
    left.mock_implementation(lambda log: result(True))
    herded = spy_on(pen, 'herd_to_pen', impl=lambda n, log: result(False))
    expect(run_wait(pen.pen_and_kill(3, farm.log))).to_be(False)
    herded.mock_implementation(lambda n, log: result(True))
    poisoned = spy_on(pen, 'poison', impl=lambda n, log: result(True))
    expect(run_wait(pen.pen_and_kill(3, farm.log))).to_be(True)
    expect(len(poisoned.calls)).to_be(1)
    farm.sheep = [Sheep(farm, 3, INSIDE_PEN)]
    expect(run_wait(pen.pen_and_kill(3, farm.log))).to_be(True)
    expect(len(herded.calls)).to_be(2)
    expect(len(poisoned.calls)).to_be(2)


test('a sheep not yet penned is herded from outside the enclosure first', pens)


def burns():
    farm = Farm(INSIDE_PEN)
    used = spy_on(pen, 'use_on_loc', impl=lambda id, loc, prefer, expect, log: result(False))
    expect(run_wait(pen.incinerate(4, farm.log))).to_be(False)
    expect(farm.logged('burning the remains of Diseased sheep 4')).to_be(True)

    def burn(id, loc, prefer, expect, log):
        farm.messages.append('the ' + 'remains burn to dust')
        return True
        yield
    used.mock_implementation(burn)
    expect(run_wait(pen.incinerate(4, farm.log))).to_be(True)
    expect(used.calls[-1][0]).to_be(BONES_OBJ[4])
    farm.at = OUTSIDE_PEN
    farm.walk_ok = False
    expect(run_wait(pen.incinerate(4, farm.log))).to_be(False)


test('the remains are burnt in the furnace until the server says they are dust', burns)

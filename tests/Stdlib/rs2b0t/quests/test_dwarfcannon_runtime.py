"""Dwarf Cannon's legs: the six railings, the watchtower remains, Gilob's son in the goblin cave and the cannon repair,
each told apart by the server's messages."""

import rs2004.quests.defs.dwarfcannon.repair as repair
from rs2004 import execution
from rs2004.geometry import Tile
from rs2004.quests.defs.dwarfcannon.areas import CANNON_PARTS, MC_LOC, MC_OBJ, MC_TILE, RAILINGS


def result(value):
    return value
    yield


class Workshop:
    """The player, their pack by name, the scene and the game messages a click sends."""

    def __init__(self, at=None):
        self.at = at if at is not None else MC_TILE.COMMANDER
        self.pack = []
        self.locs = []
        self.ground = []
        self.walks = []
        self.walk_ok = True
        self.messages = []
        self.lines = []
        spy_on(repair.game, 'tile', impl=lambda: self.at)
        spy_on(repair.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(repair.ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(repair.inventory, 'contains', impl=lambda name: name in self.pack)
        spy_on(repair.traversal, 'walk_resilient', impl=self.walk)
        spy_on(repair.game_messages, 'mark', impl=lambda: len(self.messages))
        spy_on(repair.game_messages, 'saw_since', impl=self.saw_since)
        spy_on(repair, 'settle_scene', impl=instant_ticks)
        spy_on(repair, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def saw_since(self, mark, pattern):
        for text in self.messages[mark:]:
            if pattern(text) if callable(pattern) else pattern in text.lower():
                return True
        return False

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def loc(self, id, ops=None, interact=None, name='Loc'):
        return Fake(id=id, name=name, actions=lambda: ops if ops is not None else [], distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))

    def says(self, replies):
        """A click that sends the next of replies each time, the last one again once they run out."""
        queue = list(replies)

        def click(op):
            self.messages.append(queue.pop(0) if len(queue) > 1 else queue[0])
            return True
        return click


def railings():
    world = Workshop()
    world.locs = [world.loc(entry.id, interact=world.says(['You fail and cut yourself trying.',
                                                           'You replace the railing with no problems.']))
                  for entry in RAILINGS]
    expect(run_wait(repair.fix_railings(world.log))).to_be(True)
    expect(world.lines).to_equal([])
    expect(len([text for text in world.messages if 'with no problems' in text])).to_be(len(RAILINGS))
    expect(world.walks[0]).to_equal(RAILINGS[0].at)


test('each railing is retried after a cut until the server says it is replaced', railings)


def railing_fails():
    world = Workshop()
    world.walk_ok = False
    expect(run_wait(repair.fix_one(RAILINGS[0], world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(repair.fix_one(RAILINGS[0], world.log))).to_be(False)
    expect(world.logged('no railing loc 15')).to_be(True)
    world.locs = [world.loc(RAILINGS[0].id, interact=lambda op: False)]
    expect(run_wait(repair.fix_one(RAILINGS[0], world.log))).to_be(False)
    world.locs = [world.loc(RAILINGS[0].id, interact=world.says(['You fail and cut yourself trying.']))]
    expect(run_wait(repair.fix_one(RAILINGS[0], world.log))).to_be(False)
    world.locs = []
    run_wait(repair.fix_railings(world.log))
    expect(world.logged('railing 20 did not take')).to_be(True)


test('a railing that never takes is left for the journal to decide', railing_fails)


class Tower(Workshop):
    def __init__(self, level=0):
        Workshop.__init__(self, Tile(MC_TILE.TOWER_LADDER.x, MC_TILE.TOWER_LADDER.z, level))
        self.locs = [self.loc(1, ['Climb-up', 'Climb-down'], self.climb, 'Ladder')]

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def climb(self, op):
        self.at = Tile(self.at.x, self.at.z, self.at.level + (1 if op == 'Climb-up' else -1))
        return True


def remains():
    world = Tower()
    world.ground = [Fake(name=MC_OBJ.REMAINS.name, distance=lambda: 2,
                         interact=lambda op: world.pack.append(MC_OBJ.REMAINS.name) is None)]
    expect(run_wait(repair.fetch_remains(world.log))).to_be(True)
    expect(world.at.level).to_be(0)
    expect(world.pack).to_equal([MC_OBJ.REMAINS.name])
    world.at = Tile(2570, 3443, 2)
    expect(run_wait(repair.fetch_remains(world.log))).to_be(True)
    expect(world.at.level).to_be(0)


test('the remains are taken from the top of the watchtower and the tower climbed back down', remains)


def remains_fail():
    world = Tower()
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    expect(world.logged('no Dwarf remains')).to_be(True)
    world.ground = [Fake(name=MC_OBJ.REMAINS.name, distance=lambda: 2, interact=lambda op: False)]
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    world.ground = [Fake(name=MC_OBJ.REMAINS.name, distance=lambda: 2, interact=lambda op: True)]
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    world = Tower()
    world.locs = []
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    expect(world.logged("no Ladder offering 'Climb-up'")).to_be(True)
    world.at = Tile(2570, 3443, 1)
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    world.locs = [world.loc(1, ['Climb-up'], lambda op: False, 'Ladder')]
    expect(run_wait(repair.fetch_remains(world.log))).to_be(False)
    world.locs = [world.loc(1, ['Climb-down'], lambda op: True, 'Ladder')]
    world.pack = [MC_OBJ.REMAINS.name]
    world.at = Tile(2570, 3443, 2)
    expect(run_wait(repair.leave_tower(world.log))).to_be(False)
    world.at = Tile(2570, 3443, 1)
    expect(run_wait(repair.leave_tower(world.log))).to_be(False)


test('the tower trip stops at a missing ladder, a refused climb or remains that will not come', remains_fail)


def child():
    world = Workshop()
    hops = []

    def hop(dest, radius, cave_hops, log):
        hops.append(dest)
        world.at = dest
        return True
        yield
    spy_on(repair, 'walk_with_hops', impl=hop)
    talked = spy_on(repair, 'talk_through', impl=lambda name, prefer, log: result(True))
    expect(run_wait(repair.rescue_child(False, world.log))).to_be(False)
    expect(world.logged('no crate loc 1')).to_be(True)
    world.locs = [world.loc(MC_LOC.CRATE, interact=lambda op: False)]
    expect(run_wait(repair.rescue_child(False, world.log))).to_be(False)
    world.locs = [world.loc(MC_LOC.CRATE)]
    expect(run_wait(repair.rescue_child(False, world.log))).to_be(True)
    expect(hops).to_equal([MC_TILE.CAVE_ARRIVE])
    expect(len(talked.calls)).to_be(1)
    expect(run_wait(repair.rescue_child(True, world.log))).to_be(True)
    expect(hops[-1]).to_equal(MC_TILE.COMMANDER)
    world.walk_ok = False
    world.at = MC_TILE.CAVE_ARRIVE
    expect(run_wait(repair.rescue_child(False, world.log))).to_be(False)
    world.at = MC_TILE.COMMANDER
    spy_on(repair, 'walk_with_hops', impl=lambda dest, radius, cave_hops, log: result(False))
    expect(run_wait(repair.rescue_child(False, world.log))).to_be(False)


test("Gilob's son is freed from the cave crate and his dialogue drained", child)


def cannon():
    world = Workshop()
    world.locs = [world.loc(MC_LOC.BROKEN_CANNON, interact=world.says([
        "You can't quite find the problem.",
        'You manage to fix it.',
        "You've already fixed this part of the cannon.",
        'You manage to fix it.',
        'You manage to fix it.',
        'It looks like a strange dwarf contraption.',
    ]))]
    expect(run_wait(repair.repair_cannon(world.log))).to_be(True)
    expect(world.logged(CANNON_PARTS[0].lower() + ': fixed')).to_be(True)
    expect(world.logged(CANNON_PARTS[1].lower() + ': already')).to_be(True)
    expect(world.logged('the cannon is repaired')).to_be(False)
    world.messages = []
    world.locs = [world.loc(MC_LOC.BROKEN_CANNON, interact=world.says(['It looks like a strange dwarf contraption.']))]
    expect(run_wait(repair.repair_cannon(world.log))).to_be(True)
    expect(world.logged('the cannon is repaired')).to_be(True)


test('each cannon part is repaired by name, and the contraption line ends the repair', cannon)


def cannon_fails():
    world = Workshop()
    world.walk_ok = False
    expect(run_wait(repair.repair_cannon(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(repair.inspect_for('Pipe', world.log))).to_be('retry')
    expect(world.logged('no broken cannon loc')).to_be(True)
    world.locs = [world.loc(MC_LOC.BROKEN_CANNON, interact=lambda op: False)]
    expect(run_wait(repair.inspect_for('Pipe', world.log))).to_be('retry')
    world.locs = [world.loc(MC_LOC.BROKEN_CANNON)]
    expect(run_wait(repair.repair_cannon(world.log))).to_be(True)


test('a cannon that never answers is inspected five times a part and handed back to the journal', cannon_fails)

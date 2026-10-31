"""Observatory Quest's cavern legs: the ladder down, the keep key, the keep gate, the lens mould and the telescope."""

import rs2004.quests.defs.observatory.dungeon as obs
from rs2004 import execution
from rs2004.geometry import Tile
from rs2004.quests.defs.observatory.areas import OBS_ID, OBS_LOC, OBS_TILE

SURFACE = OBS_TILE.PROFESSOR
CAVERN = OBS_TILE.DUNGEON_LANDING
KEEP = OBS_TILE.SACK_STAND
DOME = OBS_TILE.DOME_ARRIVE


def result(value):
    return value
    yield


class Cavern:
    """The player between the reception, the cavern and the dome, with the locs about them."""

    def __init__(self, at=None):
        self.at = at if at is not None else SURFACE
        self.pack = []
        self.locs = []
        self.walks = []
        self.walk_ok = True
        self.guard = None
        self.fights = []
        self.modal = False
        self.status = 'in_progress'
        self.lines = []
        spy_on(obs.game, 'tile', impl=lambda: self.at)
        spy_on(obs.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(obs.inventory, 'items', impl=lambda: self.pack)
        spy_on(obs.traversal, 'walk_resilient', impl=self.walk)
        spy_on(obs.modals, 'is_open', impl=lambda: self.modal)
        spy_on(obs.modals, 'close', impl=self.close)
        spy_on(obs.quests, 'status', impl=lambda name: self.status)
        spy_on(obs, 'settle_scene', impl=instant_ticks)
        spy_on(obs, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        spy_on(obs, 'attackable', impl=lambda name, within: self.guard)
        spy_on(obs, 'fight', impl=self.fight)
        patch(execution, 'delay_until', instant_until)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def close(self):
        self.modal = False
        return True
        yield

    def fight(self, plan, log):
        self.fights.append(plan.what)
        self.guard = None
        return True
        yield

    def hold(self, id, use_on=None):
        item = Fake(id=id, count=1, use_on=use_on if use_on is not None else (lambda other: True))
        self.pack.append(item)
        return item

    def loc(self, id, ops=None, interact=None, name='Loc'):
        return Fake(id=id, name=name, actions=lambda: ops if ops is not None else [], distance=lambda: 1,
                    interact=interact if interact is not None else (lambda op: True))

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go

    def gives(self, id):
        def give(*args):
            self.hold(id)
            return True
        return give


def descends():
    world = Cavern(CAVERN)
    expect(run_wait(obs.descend(world.log))).to_be(True)
    world.at = SURFACE
    world.walk_ok = False
    expect(run_wait(obs.descend(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(obs.descend(world.log))).to_be(False)
    expect(world.logged('no cavern ladder')).to_be(True)
    world.locs = [world.loc(OBS_LOC.RECEPTION_LADDER, interact=lambda op: False)]
    expect(run_wait(obs.descend(world.log))).to_be(False)
    world.locs = [world.loc(OBS_LOC.RECEPTION_LADDER)]
    expect(run_wait(obs.descend(world.log))).to_be(False)
    world.locs = [world.loc(OBS_LOC.RECEPTION_LADDER, interact=world.moves(CAVERN))]
    expect(run_wait(obs.descend(world.log))).to_be(True)
    expect(world.at).to_equal(CAVERN)


test("the cavern is reached by the reception ladder, through the assistant's warning", descends)


def keep_key():
    world = Cavern(CAVERN)
    world.hold(OBS_ID.KEEP_KEY)
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(True)
    world.pack = []
    spy_on(obs, 'descend', impl=lambda log: result(False))
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(False)
    spy_on(obs, 'descend', impl=lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(False)
    expect(world.logged('no keep-key chest')).to_be(True)
    world.locs = [world.loc(OBS_LOC.KEY_CHEST_SHUT, interact=lambda op: False)]
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(False)

    def opened(op):
        world.locs = [world.loc(OBS_LOC.KEY_CHEST_OPEN, interact=world.gives(OBS_ID.KEEP_KEY))]
        return True
    world.locs = [world.loc(OBS_LOC.KEY_CHEST_SHUT, interact=opened)]
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(True)
    expect(world.logged('opening the keep-key chest')).to_be(True)
    world.pack = []
    world.locs = [world.loc(OBS_LOC.KEY_CHEST_OPEN, interact=lambda op: False)]
    expect(run_wait(obs.fetch_keep_key(world.log))).to_be(False)


test('the keep key is searched for in its own chest, opened first, by id', keep_key)


def keep_gate():
    world = Cavern(KEEP)
    expect(run_wait(obs.enter_keep(world.log))).to_be(True)
    world.at = CAVERN
    world.walk_ok = False
    expect(run_wait(obs.enter_keep(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(obs.enter_keep(world.log))).to_be(False)
    expect(world.logged('no keep gate')).to_be(True)
    world.guard = Fake(name='Goblin guard')
    world.locs = [world.loc(OBS_LOC.GATE_LEFT, ['Open'], interact=world.moves(OBS_TILE.GATE_SOUTH))]
    expect(run_wait(obs.enter_keep(world.log))).to_be(True)
    expect(world.fights).to_equal(['Goblin guard'])
    expect(world.logged('without a key')).to_be(True)
    world.at = CAVERN
    fetched = spy_on(obs, 'fetch_keep_key', impl=lambda log: result(True))
    world.locs = [world.loc(OBS_LOC.GATE_RIGHT, ['Open'])]
    expect(run_wait(obs.enter_keep(world.log))).to_be(False)
    expect(len(fetched.calls)).to_be(1)
    world.locs = [world.loc(OBS_LOC.GATE_RIGHT, ['Open'], interact=lambda op: False)]
    expect(run_wait(obs.enter_keep(world.log))).to_be(False)
    world.hold(OBS_ID.KEEP_KEY, use_on=lambda gate: False)
    expect(run_wait(obs.enter_keep(world.log))).to_be(False)
    world.pack = []
    world.hold(OBS_ID.KEEP_KEY, use_on=world.moves(OBS_TILE.GATE_SOUTH))
    expect(run_wait(obs.enter_keep(world.log))).to_be(True)
    expect(world.logged('unlocking the keep gate')).to_be(True)


test('the keep gate is crossed by key, or tried without one and the key fetched when locked', keep_gate)


def lens_mould():
    world = Cavern(CAVERN)
    spy_on(obs, 'descend', impl=lambda log: result(True))
    world.locs = [world.loc(OBS_LOC.GATE_LEFT, ['Open'], interact=world.moves(OBS_TILE.GATE_SOUTH))]
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    expect(world.logged('no sack')).to_be(True)
    world.locs.append(world.loc(OBS_LOC.SACK, interact=lambda op: False))
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    world.locs[1] = world.loc(OBS_LOC.SACK)
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)

    def gate(op):
        world.at = OBS_TILE.GATE_SOUTH if world.at.z == OBS_TILE.GATE_NORTH.z else OBS_TILE.GATE_NORTH
        return True
    world.locs = [world.loc(OBS_LOC.GATE_LEFT, ['Open'], interact=gate),
                  world.loc(OBS_LOC.SACK, interact=world.gives(OBS_ID.LENS_MOULD))]
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(True)
    expect(world.at).to_equal(OBS_TILE.PROFESSOR)
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(True)


test('the lens mould is searched out of the keep sack and carried back to the reception', lens_mould)


def lens_mould_fails():
    world = Cavern(CAVERN)
    descended = spy_on(obs, 'descend', impl=lambda log: result(False))
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    descended.mock_implementation(lambda log: result(True))
    entered = spy_on(obs, 'enter_keep', impl=lambda log: result(False))
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    entered.mock_implementation(lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    world.hold(OBS_ID.LENS_MOULD)
    world.at = KEEP
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)
    expect(world.logged('cannot leave the keep')).to_be(True)
    world.locs = [world.loc(OBS_LOC.GATE_LEFT, ['Open'])]
    expect(run_wait(obs.fetch_lens_mould(world.log))).to_be(False)


test('the lens mould trip stops at the ladder, the gate or a gate that will not let us out', lens_mould_fails)


def telescope():
    world = Cavern(CAVERN)
    spy_on(obs, 'descend', impl=lambda log: result(True))
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    expect(world.logged('no dome ladder')).to_be(True)
    world.locs = [world.loc(1, ['Climb-up'], interact=lambda op: False, name='Ladder')]
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    world.locs = [world.loc(1, ['Climb-up'], name='Ladder')]
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    world.locs = [world.loc(1, ['Climb-up'], interact=world.moves(DOME), name='Ladder')]
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    expect(world.logged('no telescope')).to_be(True)
    world.locs = [world.loc(OBS_LOC.TELESCOPE, interact=lambda op: False)]
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)

    def look(op):
        world.modal = True
        world.status = 'complete'
        return True
    world.locs = [world.loc(OBS_LOC.TELESCOPE, interact=look)]
    expect(run_wait(obs.use_telescope(world.log))).to_be(True)
    expect(world.modal).to_be(False)
    expect(world.logged('closing the star chart')).to_be(True)
    world.walk_ok = False
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    world.at = CAVERN
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)
    spy_on(obs, 'descend', impl=lambda log: result(False))
    expect(run_wait(obs.use_telescope(world.log))).to_be(False)


test('the telescope is used from the dome, the star chart closed for the constellation', telescope)

"""Tree Gnome Village's stronghold and fights: the ballista's coordinates, the wall, the inner door, the orb chest,
the way out, and the melee loop against the commander and the warlord."""

import rs2004.quests.defs.treegnome.combat as combat
import rs2004.quests.defs.treegnome.stronghold as sh
from rs2004 import execution
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.treegnome.areas import TG_ITEM, TG_LOC, TG_TILE

OUTSIDE = TG_TILE.WALL_STAND
HALL = TG_TILE.HALL_LANDING
LADDER_ROOM = TG_TILE.LADDER_STAND
CHEST_FLOOR = TG_TILE.CHEST_STAND


def result(value):
    return value
    yield


class Stronghold:
    """The player in and around the Khazard stronghold, with a tick clock for the fights."""

    def __init__(self, at=None):
        self.at = at if at is not None else OUTSIDE
        self.pack = []
        self.locs = []
        self.npcs = []
        self.walks = []
        self.walk_ok = True
        self.texts = []
        self.now = 0
        self.hp = 40
        self.prayer_level = 43
        self.points = 30
        self.praying = []
        self.fighting = False
        self.ate = 0
        self.pending = False
        self.retaliate = False
        self.on_tick = None
        self.foe = None
        self.lines = []
        self.chat = FakeChat().install(sh.chat_dialog)
        spy_on(sh.chat_dialog, 'texts', impl=lambda: self.texts)
        spy_on(sh.game, 'tile', impl=lambda: self.at)
        spy_on(sh.game, 'tick', impl=lambda: self.now)
        spy_on(sh.game, 'in_combat', impl=lambda: self.fighting)
        spy_on(sh.game, 'set_auto_retaliate', impl=lambda on: setattr(self, 'retaliate', on))
        spy_on(sh.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(combat.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(sh.traversal, 'walk_resilient', impl=self.walk)
        spy_on(sh.direct_navigator, 'walk_to', impl=self.step_to)
        spy_on(combat.skills, 'level', impl=lambda name: self.prayer_level if name == 'prayer' else 40)
        spy_on(combat.skills, 'effective', impl=lambda name: self.hp)
        spy_on(combat.prayer, 'points', impl=lambda: self.points)
        spy_on(combat.prayer, 'active', impl=lambda name: name in self.praying)
        spy_on(combat.prayer, 'set', impl=self.pray)
        spy_on(combat.sustain, 'run', impl=self.eat)
        spy_on(combat.event_signal, 'pending', impl=lambda: self.pending)
        for module in [sh, combat]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
        spy_on(sh, 'drive_until', impl=lambda expect, prefer, log, ms=30000: result(expect()))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', self.ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def ticks(self, n=1):
        self.now += n
        if self.foe is not None and self.fighting:
            self.foe.life -= n
            if self.foe.life <= 0:
                self.npcs.remove(self.foe)
                self.foe = None
                self.fighting = False
        if self.on_tick is not None:
            self.on_tick()
        return None
        yield

    def pray(self, name, on):
        if on:
            self.praying.append(name)
        else:
            self.praying.remove(name)
        return True
        yield

    def eat(self):
        self.ate += 1
        self.hp = 40
        return True
        yield

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def step_to(self, tile, radius=2, timeout_ms=45000, run=False):
        self.at = tile
        return True
        yield

    def hold(self, id):
        self.pack.append(Fake(id=id, count=1))

    def loc(self, id, interact=None):
        return Fake(id=id, name='Loc', actions=lambda: [], distance=lambda: 1,
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


# The ballista.

def ballista():
    world = Stronghold(TG_TILE.BALLISTA_STAND)
    world.walk_ok = False
    expect(run_wait(sh.fire_ballista(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(sh.fire_ballista(world.log))).to_be(False)
    expect(world.logged('no Ballista')).to_be(True)
    world.locs = [world.loc(TG_LOC.BALLISTA, lambda op: False)]
    expect(run_wait(sh.fire_ballista(world.log))).to_be(False)
    headers = ['Height-coordinate:', 'X-coordinate:', 'Y-coordinate:']
    world.chat.pages = ['continue', ['0001', '0004'], ['0003', '0007'], 'continue', ['0002', '0005']]

    def chose(text):
        world.texts = [headers[len(world.chat.chosen)]] if len(world.chat.chosen) < 3 else []
    world.texts = [headers[0]]
    world.chat.on_choose = chose
    world.locs = [world.loc(TG_LOC.BALLISTA)]
    expect(run_wait(sh.fire_ballista(world.log))).to_be(True)
    expect(world.chat.chosen).to_equal(['0004', '0003', '0005'])


test('the ballista is fired with the coordinates each header asks for', ballista)


def ballista_fails():
    world = Stronghold()
    world.chat.pages = [['0001', '0004']]
    world.texts = ['Fire the ballista?']
    expect(run_wait(sh.answer_coordinates(world.log))).to_be(False)
    expect(world.logged('no coordinate header above [0001 | 0004]')).to_be(True)
    world.chat.pages = []
    expect(run_wait(sh.answer_coordinates(world.log))).to_be(False)


test('an unrecognised header or a silent ballista fails the shot', ballista_fails)


# The stronghold.

def wall_and_door():
    world = Stronghold()
    cleared = spy_on(sh, 'clear_commander', impl=lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(sh.climb_crumbled_wall(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(sh.climb_crumbled_wall(world.log))).to_be(False)
    expect(world.logged('no Crumbled wall')).to_be(True)
    world.locs = [world.loc(TG_LOC.CRUMBLED_WALL, lambda op: False)]
    expect(run_wait(sh.climb_crumbled_wall(world.log))).to_be(False)
    world.locs = [world.loc(TG_LOC.CRUMBLED_WALL)]
    expect(run_wait(sh.climb_crumbled_wall(world.log))).to_be(False)
    expect(world.logged('is the ballista shot in?')).to_be(True)
    world.locs = [world.loc(TG_LOC.CRUMBLED_WALL, world.moves(HALL))]
    expect(run_wait(sh.climb_crumbled_wall(world.log))).to_be(True)
    expect(len(cleared.calls)).to_be(1)
    world.locs = [world.loc(TG_LOC.INNER_DOOR)]
    expect(run_wait(sh.cross_inner_door(world.log))).to_be(True)
    expect(world.at).to_equal(LADDER_ROOM)
    world.locs = [world.loc(TG_LOC.INNER_DOOR, lambda op: False)]
    expect(run_wait(sh.cross_inner_door(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(sh.cross_inner_door(world.log))).to_be(False)
    world.walk_ok = True
    spy_on(sh.direct_navigator, 'walk_to', impl=lambda tile, radius, ms: result(False))
    world.locs = []
    expect(run_wait(sh.cross_inner_door(world.log))).to_be(False)
    expect(world.logged('inner door did not let us through')).to_be(True)


test('the stronghold is entered over the crumbled wall and through the inner door', wall_and_door)


def chest_floor():
    world = Stronghold(CHEST_FLOOR)
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(True)
    world.at = LADDER_ROOM
    world.locs = [world.loc(TG_LOC.LADDER_UP, world.moves(Tile(2503, 3253, 1)))]
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(True)
    world.at = HALL
    spy_on(sh, 'cross_inner_door', impl=lambda log: result(False))
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)
    world.at = OUTSIDE
    spy_on(sh, 'climb_crumbled_wall', impl=lambda log: result(False))
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)
    world.at = LADDER_ROOM
    world.locs = []
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)
    expect(world.logged('no Ladder offering Climb-up')).to_be(True)
    world.locs = [world.loc(TG_LOC.LADDER_UP, lambda op: False)]
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)
    world.locs = [world.loc(TG_LOC.LADDER_UP)]
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(sh.reach_chest_floor(world.log))).to_be(False)


test('the chest floor is reached up the ladder from wherever in the stronghold we are', chest_floor)


def orb():
    world = Stronghold(CHEST_FLOOR)
    world.hold(TG_ITEM.ORB.id)
    expect(run_wait(sh.take_the_orb(world.log))).to_be(True)
    world.pack = []
    cleared = spy_on(sh, 'clear_commander', impl=lambda log: result(False))
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)
    cleared.mock_implementation(lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)
    expect(world.logged('no chest at')).to_be(True)
    world.locs = [world.loc(TG_LOC.CHEST_SHUT, lambda op: False)]
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)
    world.locs = [world.loc(TG_LOC.CHEST_SHUT)]
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)
    expect(world.logged('never opened')).to_be(True)

    def opened(op):
        world.locs = [world.loc(TG_LOC.CHEST_OPEN, world.gives(TG_ITEM.ORB.id))]
        return True
    world.locs = [world.loc(TG_LOC.CHEST_SHUT, opened)]
    expect(run_wait(sh.take_the_orb(world.log))).to_be(True)
    world.pack = []
    world.locs = [world.loc(TG_LOC.CHEST_OPEN, lambda op: False)]
    expect(run_wait(sh.take_the_orb(world.log))).to_be(False)


test('the orb is searched out of the Khazard chest on the first floor', orb)


def leaves():
    world = Stronghold(OUTSIDE)
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(True)
    world.at = CHEST_FLOOR

    def down(op):
        world.at = LADDER_ROOM
        return True
    world.locs = [world.loc(TG_LOC.LADDER_DOWN, down), world.loc(TG_LOC.FRONT_DOOR, world.moves(TG_TILE.OUTSIDE_FRONT_DOOR))]
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(True)
    expect(world.at).to_equal(TG_TILE.OUTSIDE_FRONT_DOOR)
    world.at = HALL
    world.locs = [world.loc(TG_LOC.FRONT_DOOR, world.moves(TG_TILE.OUTSIDE_FRONT_DOOR))]
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(True)


test('the stronghold is left down the ladder and out of the front door', leaves)


def leave_fails():
    world = Stronghold(CHEST_FLOOR)
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(False)
    world.at = HALL
    spy_on(sh, 'cross_inner_door', impl=lambda log: result(False))
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(False)
    world.at = LADDER_ROOM
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(False)
    expect(world.logged('no stronghold door')).to_be(True)
    world.locs = [world.loc(TG_LOC.FRONT_DOOR, lambda op: False)]
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(sh.leave_stronghold(world.log))).to_be(False)


test('the way out stops at a missing ladder, door or a refused click', leave_fails)


# The fights.

class Foe:
    """An npc that falls after life ticks in combat with us."""

    def __init__(self, world, id, life, index=1):
        self.world = world
        self.id = id
        self.index = index
        self.life = life
        self.attacks = 0

    def actions(self):
        return ['Attack']

    def targets_another_player(self):
        return False

    def distance(self):
        return 3

    def interact(self, op):
        self.attacks += 1
        self.world.fighting = True
        self.world.foe = self
        return True


def commander():
    world = Stronghold(HALL)
    expect(run_wait(combat.clear_commander(world.log))).to_be(True)
    foe = Foe(world, combat.COMMANDER_ID, 5)
    world.npcs = [foe]
    world.hp = 20
    world.chat.pages = ['continue']
    expect(run_wait(combat.clear_commander(world.log))).to_be(True)
    expect(foe.attacks).to_be(1)
    expect(world.ate).to_be(1)
    expect(world.praying).to_equal([])
    expect(world.retaliate).to_be(True)
    expect(world.logged('Khazard commander: down after 1 attacks')).to_be(True)


test('the commander is cleared under the prayer, eating when low, and the prayer dropped after', commander)


def holds_target():
    world = Stronghold(HALL)
    world.prayer_level = 1
    foe = Foe(world, combat.COMMANDER_ID, 9999)
    world.npcs = [foe]
    expect(run_wait(combat.clear_commander(world.log))).to_be(False)
    expect(foe.attacks).to_be(1)
    expect(world.logged('prayer below 43')).to_be(True)
    expect(world.logged('gave up after 200 ticks (1 attacks)')).to_be(True)


test('a commander already being hit is not re-clicked, and the fight gives up at its guard', holds_target)


def warlord():
    world = Stronghold(TG_TILE.WARLORD)
    world.hold(TG_ITEM.ORBS.id)
    expect(run_wait(combat.kill_the_warlord(world.log))).to_be(True)
    world.pack = []
    world.walk_ok = False
    expect(run_wait(combat.kill_the_warlord(world.log))).to_be(False)
    world.walk_ok = True
    world.pending = True
    expect(run_wait(combat.kill_the_warlord(world.log))).to_be(False)
    expect(world.logged('yielding to a random event')).to_be(True)
    world.pending = False
    foe = Foe(world, combat.WARLORD_ID, 6)
    world.npcs = [foe]

    def drops():
        if foe not in world.npcs and len(world.pack) == 0:
            world.hold(TG_ITEM.ORBS.id)
    world.on_tick = drops
    expect(run_wait(combat.kill_the_warlord(world.log))).to_be(True)
    expect(foe.attacks).to_be(1)


test('the warlord is fought until his orbs land in the pack, yielding to random events', warlord)


def broken_fight():
    world = Stronghold(HALL)
    world.praying = [combat.PROTECT_MELEE]

    def boom(fight, log):
        raise ValueError('lost the client')
        yield
    spy_on(combat, 'fight_until_won', impl=boom)
    expect(lambda: run_wait(combat.melee_fight(Fake(what='x'), world.log))).to_throw('lost the client')
    expect(world.praying).to_equal([])


test('a broken fight still drops the prayer', broken_fight)

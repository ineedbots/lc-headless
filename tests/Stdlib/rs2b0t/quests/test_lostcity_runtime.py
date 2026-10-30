"""Lost City's legs: Shamus's tree, the Entrana ship and cave, the zombie's axe, the Dramen branch, the portal and the
shed, and the early ways out of the Tree Spirit fight."""

import rs2004.quests.defs.lostcity as lc
import rs2004.quests.defs.lostcity_combat as lcc
from rs2004 import execution
from rs2004.geometry import Tile

MAINLAND = lc.DRAYNOR_BANK
SHIP = Tile(2834, 3335, 1)
DUNGEON = lc.DUNGEON_ARRIVAL
ZANARIS = Tile(3200, 9500, 0)


def result(value):
    return value
    yield


class Entrana:
    """The player around Lost City: pack by name, worn items, the scene, health and a step clock."""

    def __init__(self, at=None):
        self.at = at if at is not None else MAINLAND
        self.pack = []
        self.worn = []
        self.locs = []
        self.npcs = []
        self.ground = []
        self.walks = []
        self.walk_ok = True
        self.fighting = False
        self.hp = 10
        self.base = 10
        self.ate = 0
        self.now = 0
        self.status = 'in_progress'
        self.modal = -1
        self.closed = 0
        self.on_tick = None
        self.lines = []
        for module in [lc, lcc]:
            spy_on(module.game, 'tile', impl=lambda: self.at)
        spy_on(lc.game, 'in_combat', impl=lambda: self.fighting)
        spy_on(lc.skills, 'effective', impl=lambda name: self.hp)
        spy_on(lc.skills, 'hp_fraction', impl=lambda: self.hp / self.base)
        spy_on(lc.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(lc.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(lc.npcs, 'all', impl=lambda: self.npcs)
        spy_on(lc.ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(lc.inventory, 'items', impl=lambda: self.pack)
        spy_on(lc.inventory, 'contains', impl=lambda name: any([item.name == name for item in self.pack]))
        spy_on(lc.inventory, 'count', impl=lambda name: len([item for item in self.pack if item.name == name]))
        spy_on(lc.inventory, 'is_full', impl=lambda: len(self.pack) >= 28)
        spy_on(lc.equipment, 'items', impl=lambda: self.worn)
        spy_on(lc.equipment, 'contains', impl=lambda name: any([item.name == name for item in self.worn]))
        spy_on(lc.equipment, 'unequip', impl=self.unequip)
        spy_on(lc.traversal, 'walk_resilient', impl=self.walk)
        spy_on(lc.sustain, 'run', impl=self.eat)
        spy_on(lc.quests, 'status', impl=lambda name: self.status)
        spy_on(lc.reader, 'modals', impl=lambda: Fake(main=self.modal))
        patch(lc._core, 'close_interfaces', self.close)
        patch(lc._core, 'step_time', lambda: self.now)
        patch(execution, 'delay_until', self.until)
        patch(execution, 'delay_until_ticks', self.until_ticks)
        patch(execution, 'delay_ticks', self.ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def advance(self):
        self.now += 600
        if self.on_tick is not None:
            self.on_tick()

    def until(self, cond, timeout_ms=6000):
        self.advance()
        return cond()
        yield

    def until_ticks(self, cond, ticks=1):
        self.advance()
        return cond()
        yield

    def ticks(self, n=1):
        self.advance()
        return None
        yield

    def close(self):
        self.closed += 1
        self.modal = -1

    def eat(self):
        if any([item.name == 'Lobster' for item in self.pack]):
            self.drop('Lobster')
            self.ate += 1
            self.hp = min(self.base, self.hp + 3)
        return True
        yield

    def unequip(self, name):
        if name == 'Cursed amulet':
            return False
        self.worn = [item for item in self.worn if item.name != name]
        return True
        yield

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def hold(self, name, ops=None, interact=None):
        item = Fake(name=name, actions=lambda: ops if ops is not None else ['Drop'],
                    interact=interact if interact is not None else (lambda op: self.drop(name) is None))
        self.pack.append(item)
        return item

    def drop(self, name):
        for item in self.pack:
            if item.name == name:
                self.pack.remove(item)
                return

    def loc(self, id, ops, interact=None, name='Loc'):
        return Fake(id=id, name=name, actions=lambda: ops, distance=lambda: 2,
                    interact=interact if interact is not None else (lambda op: True))

    def moves(self, tile):
        def go(*args):
            self.at = tile
            return True
        return go


def stage():
    world = Entrana()
    world.status = 'complete'
    expect(run_wait(lc.read_lost_city_stage())).to_be(lc.LOST_CITY_STAGE.COMPLETE)
    world.status = 'not_started'
    expect(run_wait(lc.read_lost_city_stage())).to_be(lc.LOST_CITY_STAGE.NOT_STARTED)
    world.status = 'unknown'
    expect(run_wait(lc.read_lost_city_stage())).to_be(None)
    world.status = 'in_progress'

    def journal(name):
        world.modal = 275
        return ['Quest complete!']
        yield
    spy_on(lc.quests, 'journal', impl=journal)
    run_wait(lc.read_lost_city_stage())
    expect(world.closed).to_be(1)


test('the stage comes from the quest list or the journal, whose page is closed after', stage)


def strips():
    world = Entrana()
    world.worn = [Fake(name='Bronze sword'), Fake(name=None)]
    expect(run_wait(lc.unequip_all(world.log))).to_be(False)
    world.worn = [Fake(name='Bronze sword')]
    expect(run_wait(lc.unequip_all(world.log))).to_be(True)
    world.worn = [Fake(name='Cursed amulet')]
    expect(run_wait(lc.unequip_all(world.log))).to_be(False)


test("everything worn comes off before Entrana's monks search the player", strips)


def eats():
    world = Entrana()
    world.hp = 4
    world.hold('Lobster')
    run_wait(lc.restore_with_selected_food(0.9))
    expect(world.ate).to_be(1)
    expect(world.hp).to_be(7)
    world.fighting = True

    def calm():
        if world.now > 1800:
            world.fighting = False
    world.on_tick = calm
    expect(run_wait(lc.wait_out_combat(10000))).to_be(True)
    world.fighting = True
    world.on_tick = None
    expect(run_wait(lc.wait_out_combat(3000))).to_be(False)


test('food tops health up before a fight until it stops healing, and combat is waited out to a deadline', eats)


def shamus():
    world = Entrana()
    world.npcs = [Fake(id=lc.SHAMUS_ID, distance=lambda: 5)]
    talked = spy_on(lc, 'talk_through', impl=lambda name, prefer, log: result(True))
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(True)
    world.npcs = []
    world.walk_ok = False
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(False)
    expect(world.logged('no Lost City tree to Chop')).to_be(True)
    world.locs = [world.loc(lc.SHAMUS_TREE_ID, ['Chop'], lambda op: False)]
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(False)
    world.locs = [world.loc(lc.SHAMUS_TREE_ID, ['Chop'])]
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(False)

    def appears(op):
        world.npcs = [Fake(id=lc.SHAMUS_ID, distance=lambda: 2)]
        return True
    world.locs = [world.loc(lc.SHAMUS_TREE_ID, ['Chop'], appears)]
    expect(run_wait(lc.reveal_and_talk_shamus(world.log))).to_be(True)
    expect(len(talked.calls)).to_be(2)


test('Shamus is chopped out of his tree and talked to', shamus)


def ship():
    world = Entrana(SHIP)
    expect(run_wait(lc.disembark_entrana(world.log))).to_be(False)
    expect(world.logged('no Entrana Gangplank')).to_be(True)
    world.locs = [world.loc(1, ['Cross'], lambda op: False, 'Gangplank')]
    expect(run_wait(lc.disembark_entrana(world.log))).to_be(False)
    world.locs = [world.loc(1, ['Cross'], world.moves(lc.ENTRANA_LANDING), 'Gangplank')]
    expect(run_wait(lc.disembark_entrana(world.log))).to_be(True)
    world.at = MAINLAND
    talked = spy_on(lc, 'talk_through', impl=lambda name, prefer, log: result(False))
    expect(run_wait(lc.sail_to_entrana(world.log))).to_be(False)

    def sail(name, prefer, log):
        world.at = SHIP
        return True
        yield
    talked.mock_implementation(sail)
    expect(run_wait(lc.sail_to_entrana(world.log))).to_be(True)
    world.walk_ok = False
    expect(run_wait(lc.sail_to_entrana(world.log))).to_be(False)


test('the monk ships the player to Entrana and the gangplank takes them ashore', ship)


def cave():
    world = Entrana(lc.ENTRANA_LANDING)
    talked = spy_on(lc, 'talk_through', impl=lambda name, prefer, log: result(False))
    expect(run_wait(lc.descend_entrana(world.log))).to_be(False)

    def warn(name, prefer, log):
        world.at = DUNGEON
        return True
        yield
    talked.mock_implementation(warn)
    expect(run_wait(lc.descend_entrana(world.log))).to_be(True)
    expect(talked.calls[-1][0]).to_be('Cave monk')
    world.walk_ok = False
    expect(run_wait(lc.descend_entrana(world.log))).to_be(False)


test("the cave monk's warning is accepted to reach the dungeon", cave)


def axe_drop(world, name='Bronze axe', take=True):
    def pick(op):
        if take:
            world.ground = []
            world.hold(name)
        return take
    return Fake(name=name, distance=lambda: 4, interact=pick)


def takes_axe():
    world = Entrana(DUNGEON)
    expect(run_wait(lc.take_dungeon_axe())).to_be(False)
    world.ground = [axe_drop(world, take=False)]
    expect(run_wait(lc.take_dungeon_axe())).to_be(False)
    for i in range(28):
        world.hold('Air rune' if i == 0 else 'Bones')
    world.ground = [axe_drop(world)]
    expect(run_wait(lc.take_dungeon_axe())).to_be(True)
    expect(len([item for item in world.pack if item.name == 'Bones'])).to_be(26)


test("the zombie's axe is taken off the floor, dropping junk for room", takes_axe)


class Zombie:
    def __init__(self, world, dies=True):
        self.world = world
        self.id = lc.ENTRANA_ZOMBIE_ID
        self.in_combat = False
        self.dies = dies
        self.attacks = 0

    def targets_another_player(self):
        return False

    def actions(self):
        return ['Attack']

    def distance(self):
        return 5

    def valid(self):
        return True

    def interact(self, op):
        self.attacks += 1
        if self.dies:
            self.world.ground = [axe_drop(self.world)]
        return self.dies


def axe():
    world = Entrana(DUNGEON)
    world.hold('Iron axe')
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(True)
    world.pack = []
    world.ground = [axe_drop(world)]
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(True)
    world.pack = []
    world.fighting = True
    world.on_tick = lambda: setattr(world, 'fighting', False)
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(False)
    world.on_tick = None
    world.walk_ok = False
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(False)
    expect(world.logged('waiting for an available Entrana Zombie')).to_be(True)
    world.npcs = [Zombie(world, False)]
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(False)
    zombie = Zombie(world)
    world.npcs = [zombie]
    expect(run_wait(lc.acquire_dungeon_axe(world.log))).to_be(True)
    expect(zombie.attacks).to_be(1)


test('an axe is taken from a zombie it is killed for, after any fight already on', axe)


def branch():
    world = Entrana(lc.DRAMEN_TREE)
    expect(run_wait(lc.chop_branch(world.log))).to_be(False)
    expect(world.logged('no Dramen tree')).to_be(True)
    world.locs = [world.loc(lc.DRAMEN_TREE_ID, ['Chop down'], lambda op: False)]
    expect(run_wait(lc.chop_branch(world.log))).to_be(False)
    world.locs = [world.loc(lc.DRAMEN_TREE_ID, ['Chop down'], lambda op: world.hold(lc.BRANCH) is not None)]
    expect(run_wait(lc.chop_branch(world.log))).to_be(True)
    world.pack = []
    for i in range(28):
        world.hold('Knife', ['Use'])
    expect(run_wait(lc.chop_branch(world.log))).to_be(False)
    expect(world.logged('no disposable item or food')).to_be(True)
    world.pack[0] = Fake(name='Bones', actions=lambda: ['Drop'], interact=lambda op: True)
    expect(run_wait(lc.chop_branch(world.log))).to_be(False)
    world.pack = world.pack[1:]
    world.hold('Bones')
    expect(run_wait(lc.chop_branch(world.log))).to_be(True)
    world.walk_ok = False
    expect(run_wait(lc.chop_branch(world.log))).to_be(False)


test('a Dramen branch is cut, dropping junk first when the pack is full', branch)


def portal():
    world = Entrana(DUNGEON)
    world.fighting = True
    expect(run_wait(lc.leave_dungeon(world.log))).to_be(False)
    world.fighting = False
    world.walk_ok = False
    expect(run_wait(lc.leave_dungeon(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(lc.leave_dungeon(world.log))).to_be(False)
    expect(world.logged('no Magic door')).to_be(True)
    world.locs = [world.loc(lc.MAGIC_DOOR_ID, ['Open'], lambda op: False)]
    expect(run_wait(lc.leave_dungeon(world.log))).to_be(False)
    world.locs = [world.loc(lc.MAGIC_DOOR_ID, ['Open'], world.moves(Tile(3100, 3900, 0)))]
    expect(run_wait(lc.leave_dungeon(world.log))).to_be(True)


test('the dungeon is left through the magic door, never mid-fight', portal)


def shed():
    world = Entrana()
    world.walk_ok = False
    expect(run_wait(lc.enter_zanaris(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(lc.enter_zanaris(world.log))).to_be(False)
    expect(world.logged('no Lost City shed Door')).to_be(True)
    world.locs = [world.loc(2406, ['Open'], lambda op: False)]
    expect(run_wait(lc.enter_zanaris(world.log))).to_be(False)
    world.locs = [world.loc(2406, ['Open'], world.moves(ZANARIS))]
    expect(run_wait(lc.enter_zanaris(world.log))).to_be(True)


test('Zanaris is entered through the swamp shed door with the staff worn', shed)


# The Tree Spirit's early ways out.

class Spirit:
    def __init__(self, tile=None):
        self.id = 655
        self.health = 10
        self.max_health = 10
        self.at = tile if tile is not None else lcc.TREE_SPIRIT_TRAP

    def targets_another_player(self):
        return False

    def network_tile(self):
        return self.at


class Grove(Entrana):
    def __init__(self, at=None):
        Entrana.__init__(self, at if at is not None else lcc.TREE_STAND)
        self.retaliate = False
        self.retaliate_sticks = False
        self.pending = False
        self.steps = []
        self.step_ok = True
        spy_on(lcc.game, 'auto_retaliate_on', impl=lambda: self.retaliate)
        spy_on(lcc.game, 'set_auto_retaliate', impl=self.set_retaliate)
        spy_on(lcc.event_signal, 'pending', impl=lambda: self.pending)
        spy_on(lcc.direct_navigator, 'walk', impl=self.step)
        spy_on(lcc, 'strike', returns='Wind Strike')

    def set_retaliate(self, on):
        if not self.retaliate_sticks:
            self.retaliate = on

    def step(self, tile, run=False):
        self.steps.append(tile)
        if self.step_ok:
            self.at = tile
        return True


def spirit_exits():
    world = Grove()
    world.pending = True
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    world.pending = False
    world.retaliate = True
    world.retaliate_sticks = True
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    world.retaliate_sticks = False
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(True)))).to_be(True)
    expect(world.retaliate).to_be(True)
    world.retaliate = False
    spy_on(lcc, 'strike', returns=None)
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    expect(world.logged('no castable Strike spell; supply runes')).to_be(True)
    spy_on(lcc, 'strike', returns='Wind Strike')
    world.npcs =[Fake(id=655, targets_another_player=lambda: True)]
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    expect(world.logged('waiting for the other player')).to_be(True)
    world.npcs = []
    world.walk_ok = False
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    world.walk_ok = True
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    world.locs = [world.loc(1292, ['Chop down'])]
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)


test('the Tree Spirit fight does not start on an event, stuck retaliation, no runes, a rival or no tree', spirit_exits)


def cover():
    world = Grove(lcc.TREE_SPIRIT_SAFESPOT)
    world.npcs = [Spirit()]
    expect(run_wait(lcc.take_cover(world.log))).to_be(True)
    world.at = lcc.TREE_STAND
    expect(run_wait(lcc.take_cover(world.log))).to_be(True)
    expect(world.steps).to_equal(lcc.LURE)
    expect(world.logged('Tree Spirit trapped behind the fungus')).to_be(True)
    world.npcs = [Spirit(lcc.TREE_STAND)]
    world.at = lcc.TREE_STAND
    expect(run_wait(lcc.take_cover(world.log))).to_be(False)
    expect(world.logged('did not reach the trapped tile')).to_be(True)
    world.at = lcc.TREE_STAND
    world.step_ok = False
    expect(run_wait(lcc.take_cover(world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(lcc.take_cover(world.log))).to_be(False)
    world.walk_ok = True
    world.pending = True
    expect(run_wait(lcc.take_cover(world.log))).to_be(False)


test('cover is taken by the lure path, and the safespot only counts with the Spirit trapped', cover)


def credit():
    world = Grove(lcc.TREE_SPIRIT_SAFESPOT)
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    world.npcs = [Spirit()]
    world.retaliate = False

    def vanish(spell, target):
        world.npcs = []
        return False
    spy_on(lcc.game, 'cast_on_npc', impl=vanish)
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    expect(world.logged('could not cast Wind Strike')).to_be(True)
    world.npcs = [Spirit()]
    spy_on(lcc, 'strike', returns=None)
    expect(run_wait(lcc.defeat_tree_spirit(world.log, lambda: result(False)))).to_be(False)
    expect(world.logged('holding the Tree Spirit safespot')).to_be(True)


test('the fight stops on a cast the client refuses or when the Strike runes run out', credit)

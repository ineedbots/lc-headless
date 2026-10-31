"""Scorpion Catcher's way out of Velrak's cell, which a live run found 6 tiles from the door after following him, and
the legs through the jail, the deep dungeon and the three catches."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.scorpcatcher import antipoison, dungeon, legs
from rs2004.quests.defs.scorpcatcher.areas import CAGE_ID, JAILER_NPC, SC_ID, SC_TILE, SCORPION_NPC, SEER, VELRAK
from rs2004.quests.defs.scorpcatcher.dungeon import leave_cell
from rs2004.tabs import PROTECT_FROM_MAGIC, prayer
from rs2004.traversal import traversal


class Cell:
    def __init__(self):
        self.here = Tile(2932, 9684, 0)
        self.walks = []
        self.door = Fake(id=SC_ID.JAIL_DOOR, name='Door', actions=lambda: ['Open'], distance=self.door_distance, interact=self.open)

    def tile(self):
        return self.here

    def door_distance(self):
        return max(abs(self.here.x - SC_TILE.JAIL_DOOR.x), abs(self.here.z - SC_TILE.JAIL_DOOR.z))

    def walk_to(self, dest, radius=2, timeout_ms=45000, run=False):
        self.walks.append(dest)
        self.here = dest
        return True
        yield

    def open(self, op):
        self.here = SC_TILE.JAIL_DOOR
        return True


def steps_to_the_door_first():
    cell = Cell()
    spy_on(game, 'tile', cell.tile)
    spy_on(direct_navigator, 'walk_to', cell.walk_to)
    spy_on(locs, 'query', querying(lambda: [cell.door]))
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until', instant_until)
    expect(cell.door_distance()).to_be(6)
    left = yield from leave_cell(lambda message: None)
    expect(left).to_be(True)
    expect(cell.walks).to_equal([SC_TILE.JAIL_CELL])
    expect(cell.here).to_equal(SC_TILE.JAIL_DOOR)


test('leaves the cell from beside Velrak by stepping to the door before opening it', steps_to_the_door_first)


def pockets():
    from rs2004.quests.defs.scorpcatcher import scorpcatcher
    from rs2004.quests.defs.scorpcatcher.dungeon import locked_in
    expect(scorpcatcher.resume_at).to_be(locked_in)
    expect(locked_in(Tile(2932, 9684, 0))).to_be(True)
    expect(locked_in(SC_TILE.SECRET_ROOM)).to_be(True)
    expect(locked_in(SC_TILE.JAIL_DOOR)).to_be(False)
    expect(locked_in(SC_TILE.BANK)).to_be(False)


test("a restart in Velrak's cell or past the dusty-key gate resumes there before any banking", pockets)


# The jail, the deep dungeon, the secret room, the antipoison and the three catches.

CORRIDOR = Tile(2931, 9692, 0)
CELL = Tile(2931, 9686, 0)
DEEP = Tile(2870, 9800, 0)
SECRET = Tile(2877, 9796, 0)
OUTSIDE_GATE = Tile(2930, 9803, 0)
DUSTY = SC_ID.DUSTY_KEY
JAIL = SC_ID.JAIL_KEY


def result(value):
    return value
    yield


class Taverley:
    """The player in and around Taverley Dungeon: pack, scene, prayer and a step clock that each tick moves on."""

    def __init__(self, at=None):
        self.at = at if at is not None else CORRIDOR
        self.pack = []
        self.locs = []
        self.npcs = []
        self.ground = []
        self.walks = []
        self.walk_ok = True
        self.praying = []
        self.now = 0
        self.on_tick = None
        self.texts = []
        self.lines = []
        self.chat = FakeChat().install(chat_dialog)
        spy_on(chat_dialog, 'texts', impl=lambda: self.texts)
        spy_on(game, 'tile', impl=lambda: self.at)
        spy_on(inventory, 'items', impl=lambda: self.pack)
        spy_on(inventory, 'count', impl=lambda name: sum([item.count for item in self.pack if item.name == name]))
        spy_on(locs, 'query', impl=querying(lambda: self.locs))
        spy_on(npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(npcs, 'all', impl=lambda: self.npcs)
        spy_on(ground_items, 'query', impl=querying(lambda: self.ground))
        spy_on(traversal, 'walk_resilient', impl=self.walk)
        spy_on(direct_navigator, 'walk_to', impl=self.step_to)
        spy_on(prayer, 'active', impl=lambda name: name in self.praying)
        spy_on(prayer, 'set', impl=self.pray)
        spy_on(sustain, 'run', impl=self.tick)
        patch(dungeon._core, 'step_time', lambda: self.now)
        patch(execution, 'delay_until', self.until)
        patch(execution, 'delay_ticks', self.ticks)
        for module in [dungeon, legs]:
            spy_on(module, 'settle_scene', impl=instant_ticks)
            spy_on(module, 'drive_until', impl=self.drive_until)
        spy_on(dungeon, 'drive_dialog', impl=lambda prefer, log: result(True))

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def advance(self):
        self.now += 600
        if self.on_tick is not None:
            self.on_tick()

    def tick(self):
        self.advance()
        return True
        yield

    def ticks(self, n=1):
        self.advance()
        return None
        yield

    def until(self, cond, timeout_ms=6000):
        self.advance()
        return cond()
        yield

    def drive_until(self, expect, prefer, log, ms=30000):
        self.advance()
        return expect()
        yield

    def pray(self, name, on):
        if on:
            self.praying.append(name)
        else:
            self.praying.remove(name)
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

    def hold(self, id, name=None, count=1, use_on=None, interact=None):
        item = Fake(id=id, name=name, count=count, use_on=use_on if use_on is not None else (lambda other: True),
                    interact=interact if interact is not None else (lambda op: True))
        self.pack.append(item)
        return item

    def drop(self, id):
        self.pack = [item for item in self.pack if item.id != id]

    def held(self, id):
        return any([item.id == id for item in self.pack])

    def loc(self, id, ops=None, interact=None, distance=1):
        return Fake(id=id, name='Loc', actions=lambda: ops if ops is not None else [], distance=lambda: distance,
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


def jail_key():
    world = Taverley()
    expect(run_wait(dungeon.take_jail_key(world.log))).to_be(False)
    far = Tile(2935, 9692, 0)
    world.ground = [Fake(id=JAIL, distance=lambda: 4, tile=lambda: far, interact=world.gives(JAIL))]
    world.walk_ok = False
    expect(run_wait(dungeon.take_jail_key(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(dungeon.take_jail_key(world.log))).to_be(True)
    expect(world.walks[-1]).to_equal(far)
    world.drop(JAIL)
    world.ground = [Fake(id=JAIL, distance=lambda: 1, interact=lambda op: False)]
    expect(run_wait(dungeon.take_jail_key(world.log))).to_be(False)


test('the jail key is walked to and taken off the floor', jail_key)


def jailer(world, dies_after=None):
    state = {'hits': 0}

    def attack(op):
        return True
    npc = Fake(index=7, name=JAILER_NPC, actions=lambda: ['Attack'], distance=lambda: 3, interact=attack)
    if dies_after is not None:
        def hit():
            state['hits'] += 1
            if state['hits'] == dies_after:
                world.npcs = []
                world.ground = [Fake(id=JAIL, distance=lambda: 1, interact=world.gives(JAIL))]
        world.on_tick = hit
    return npc


def kills_jailer():
    world = Taverley()
    expect(run_wait(dungeon.kill_jailer(world.log))).to_be(False)
    expect(world.logged('no Jailer in the prison corridor')).to_be(True)
    world.npcs = [Fake(index=7, name=JAILER_NPC, actions=lambda: ['Attack'], distance=lambda: 3, interact=lambda op: False)]
    expect(run_wait(dungeon.kill_jailer(world.log))).to_be(False)
    world.npcs = [jailer(world, 3)]
    expect(run_wait(dungeon.kill_jailer(world.log))).to_be(True)
    expect(world.held(JAIL)).to_be(True)
    world.npcs = [jailer(world)]
    expect(run_wait(dungeon.kill_jailer(world.log))).to_be(True)
    world.drop(JAIL)
    world.on_tick = None
    expect(run_wait(dungeon.kill_jailer(world.log))).to_be(False)
    expect(world.logged('outlived 90s of combat')).to_be(True)


test('the Jailer is fought until he drops the jail key, within the kill budget', kills_jailer)


def doors():
    world = Taverley()
    inside = lambda: world.at == CELL
    expect(run_wait(dungeon.unlock_with_key(JAIL, SC_ID.JAIL_DOOR, lambda: True, 'cell door', world.log))).to_be(True)
    expect(run_wait(dungeon.unlock_with_key(JAIL, SC_ID.JAIL_DOOR, inside, 'cell door', world.log))).to_be(False)
    expect(world.logged('no cell door in reach or no key 1591')).to_be(True)
    world.locs = [world.loc(SC_ID.JAIL_DOOR, ['Open'])]
    world.hold(JAIL, use_on=lambda door: False)
    expect(run_wait(dungeon.unlock_with_key(JAIL, SC_ID.JAIL_DOOR, inside, 'cell door', world.log))).to_be(False)
    world.drop(JAIL)
    world.hold(JAIL, use_on=world.moves(CELL))
    expect(run_wait(dungeon.unlock_with_key(JAIL, SC_ID.JAIL_DOOR, inside, 'cell door', world.log))).to_be(True)
    outside = lambda: world.at != CELL
    world.locs = []
    expect(run_wait(dungeon.open_loc(SC_ID.JAIL_DOOR, 'Open', outside, 'cell door', world.log))).to_be(False)
    expect(world.logged('no cell door to open here')).to_be(True)


test('a keyed door is unlocked with its key and a plain one opened, each until the far side holds', doors)


def velrak(world, distance=1, interact=None, at=None):
    tile = at if at is not None else CELL
    return Fake(name=VELRAK.npc, actions=lambda: ['Talk-to'], distance=lambda: distance, tile=lambda: tile,
                interact=interact if interact is not None else (lambda op: True))


def talks_in_cell():
    world = Taverley(CELL)
    expect(run_wait(dungeon.talk_in_cell(world.log))).to_be(False)
    expect(world.logged('no Velrak the explorer in the cell')).to_be(True)
    world.npcs = [velrak(world, interact=lambda op: False)]
    expect(run_wait(dungeon.talk_in_cell(world.log))).to_be(False)
    expect(world.logged('refused the talk')).to_be(True)
    world.npcs = [velrak(world)]
    expect(run_wait(dungeon.talk_in_cell(world.log))).to_be(False)
    expect(world.logged('never opened a dialogue')).to_be(True)

    def talk(op):
        world.chat.pages = ['continue']
        return True
    corner = Tile(2929, 9684, 0)
    world.npcs = [velrak(world, 4, talk, corner)]
    expect(run_wait(dungeon.talk_in_cell(world.log))).to_be(True)
    expect(world.at).to_equal(corner)


test('Velrak is talked to by scene steps inside his cell', talks_in_cell)


def dusty_key():
    world = Taverley()
    world.hold(DUSTY)
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(True)
    world.pack = []
    world.walk_ok = False
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)

    def talk(op):
        world.chat.pages = ['continue']
        world.hold(DUSTY)
        return True
    world.npcs = [velrak(world, interact=talk)]
    world.hold(JAIL, use_on=world.moves(CELL))
    world.locs = [world.loc(SC_ID.JAIL_DOOR, ['Open'], interact=world.moves(SC_TILE.JAIL_DOOR))]
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(True)
    expect(world.at).to_equal(SC_TILE.JAIL_DOOR)
    expect(world.logged("unlocking Velrak's cell")).to_be(True)
    world.drop(DUSTY)
    world.at = CELL
    world.npcs = [velrak(world, interact=lambda op: True)]
    world.chat.pages = []
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)
    world.npcs = [velrak(world, interact=lambda op: setattr(world.chat, 'pages', ['continue']) is None)]
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)
    expect(world.logged('Velrak handed over no dusty key')).to_be(True)


test("the dusty key comes from Velrak, through the Jailer's key and his cell door", dusty_key)


def dusty_key_fails():
    world = Taverley()
    world.walk_ok = True
    world.hold(JAIL, use_on=lambda door: False)
    world.locs = [world.loc(SC_ID.JAIL_DOOR, ['Open'])]
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)

    def short(tile, radius=None, attempts=None, timeout_ms=None, log=None):
        world.walks.append(tile)
        if len(world.walks) > 1:
            return False
        world.at = Tile(2931, 9691, 0)
        return True
        yield
    spy_on(traversal, 'walk_resilient', impl=short)
    world.walks = []
    world.at = Tile(2931, 9700, 0)
    expect(run_wait(dungeon.fetch_dusty_key(world.log))).to_be(False)


test('the dusty key stops at a refused cell door or a failed walk to it', dusty_key_fails)


def deep_dungeon():
    world = Taverley(DEEP)
    expect(run_wait(dungeon.enter_deep_dungeon(world.log))).to_be(True)
    expect(world.praying).to_equal([PROTECT_FROM_MAGIC])
    world.at = SECRET
    expect(run_wait(dungeon.enter_deep_dungeon(world.log))).to_be(True)
    expect(world.praying).to_equal([])
    world.at = OUTSIDE_GATE
    fetched = spy_on(dungeon, 'fetch_dusty_key', impl=lambda log: result(False))
    expect(run_wait(dungeon.enter_deep_dungeon(world.log))).to_be(False)
    fetched.mock_implementation(lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(dungeon.enter_deep_dungeon(world.log))).to_be(False)
    world.walk_ok = True
    world.locs = [world.loc(SC_ID.DEEP_GATE, ['Open'], interact=world.moves(SC_TILE.DEEP_GATE))]
    world.hold(DUSTY, use_on=world.moves(SC_TILE.DEEP_DUNGEON))
    expect(run_wait(dungeon.enter_deep_dungeon(world.log))).to_be(True)
    expect(world.praying).to_equal([PROTECT_FROM_MAGIC])
    world.at = DEEP
    expect(run_wait(dungeon.leave_deep_dungeon(world.log))).to_be(True)
    expect(world.at).to_equal(SC_TILE.DEEP_GATE)
    expect(world.praying).to_equal([])
    expect(run_wait(dungeon.leave_deep_dungeon(world.log))).to_be(True)
    world.at = DEEP
    world.walk_ok = False
    expect(run_wait(dungeon.leave_deep_dungeon(world.log))).to_be(False)
    world.walk_ok = True
    world.locs = []
    expect(run_wait(dungeon.leave_deep_dungeon(world.log))).to_be(False)


test('the deep dungeon is entered with the dusty key under Protect from Magic, and left by the gate', deep_dungeon)


def secret_wall():
    world = Taverley(DEEP)
    world.praying = [PROTECT_FROM_MAGIC]
    world.locs = [world.loc(SC_ID.SECRET_WALL, ['Search'], interact=world.moves(SC_TILE.SECRET_ROOM))]
    expect(run_wait(dungeon.cross_secret_wall(True, world.log))).to_be(True)
    expect(world.praying).to_equal([])
    expect(run_wait(dungeon.cross_secret_wall(True, world.log))).to_be(True)
    world.locs = [world.loc(SC_ID.SECRET_WALL, ['Search'], interact=world.moves(SC_TILE.SECRET_WALL))]
    expect(run_wait(dungeon.cross_secret_wall(False, world.log))).to_be(True)
    expect(world.praying).to_equal([PROTECT_FROM_MAGIC])
    expect(run_wait(dungeon.cross_secret_wall(False, world.log))).to_be(True)
    world.at = DEEP
    world.walk_ok = False
    expect(run_wait(dungeon.cross_secret_wall(True, world.log))).to_be(False)
    world.walk_ok = True
    world.locs = []
    expect(run_wait(dungeon.cross_secret_wall(True, world.log))).to_be(False)


test('the old wall is searched both ways, with the prayer down only inside the secret room', secret_wall)


class Store:
    def __init__(self, world, opens=True, stocked=True):
        self.world = world
        self.opens = opens
        self.stocked = stocked
        self.closed = False

    def open(self, npc):
        return self.opens
        yield

    def buy(self, name, n):
        if self.stocked:
            self.world.hold(1, name, n)
        return self.stocked
        yield

    def close(self):
        self.closed = True
        return True
        yield


def stocks(opens, stocked, coins, walks, said):
    def run():
        world = Taverley()
        world.hold(995, 'Coins', coins)
        world.walk_ok = walks
        store = Store(world, opens, stocked)
        spy_on(antipoison.shop, 'open', impl=store.open)
        spy_on(antipoison.shop, 'buy', impl=store.buy)
        spy_on(antipoison.shop, 'close', impl=store.close)
        run_wait(antipoison.stock_antipoison(world.log))
        expect(world.logged(said), str(world.lines)).to_be(True)
        run_wait(antipoison.stock_antipoison(world.log))
    return run


test('the antipoison is bought at Musa Point', stocks(True, True, 1000, True, 'bought an Antipoison(3)'))
test('a short purse runs the spiders uncured', stocks(True, True, 100, True, 'will not cover the 600'))
test('an unreachable store runs the spiders uncured', stocks(True, True, 1000, False, 'could not reach the Karamja'))
test('a store that will not open runs the spiders uncured', stocks(False, True, 1000, True, 'would not open'))
test('an empty store runs the spiders uncured', stocks(True, False, 1000, True, 'is out of antipoison'))


def cures():
    world = Taverley()
    messages = []
    spy_on(game_messages, 'mark', impl=lambda: len(messages))
    spy_on(game_messages, 'saw_since', impl=lambda mark, text: any([text in m for m in messages[mark:]]))
    mark = antipoison.poison_mark()
    run_wait(antipoison.cure_poison(mark, world.log))
    expect(world.lines).to_equal([])
    messages.append('you have been poisoned!')
    run_wait(antipoison.cure_poison(mark, world.log))
    expect(world.logged('no antipoison to drink')).to_be(True)
    world.hold(1, 'Antipoison(2)', interact=lambda op: False)
    run_wait(antipoison.cure_poison(mark, world.log))
    expect(world.logged('the Antipoison(2) refused the drink')).to_be(True)
    world.pack = []
    world.hold(1, 'Antipoison(2)', interact=lambda op: world.drop(1) is None)
    run_wait(antipoison.cure_poison(mark, world.log))
    expect(world.logged('drank the Antipoison(2) clear of the spiders')).to_be(True)


test('the dose is drunk outside the gate only if the dungeon poisoned us', cures)


def seer(hint, options=None):
    def run():
        world = Taverley(SC_TILE.SEER)
        reached = spy_on(legs, 'goto_npc', impl=lambda stop, hops, log: result(False))
        expect(run_wait(legs.ask_the_seer(world.log))).to_be(False)
        reached.mock_implementation(lambda stop, hops, log: result(True))
        opened = spy_on(legs, 'open_dialogue', impl=lambda name, log: result(False))
        expect(run_wait(legs.ask_the_seer(world.log))).to_be(False)
        opened.mock_implementation(lambda name, log: result(True))
        world.chat.pages = ['continue', options if options is not None else list(SEER.prefer[:1]), 'continue']
        if hint:
            world.chat.on_choose = lambda text: world.texts.append('Go and see if you can find that scorpion.')
        expect(run_wait(legs.ask_the_seer(world.log))).to_be(hint)
        if options is not None:
            expect(world.logged('none of it asks about the scorpions')).to_be(True)
        elif hint:
            expect(world.logged('the Seer has placed the first scorpion')).to_be(True)
        else:
            expect(world.logged('never got as far as the hint')).to_be(True)
    return run


test("the Seer's hint is waited for through the looking-glass pauses", seer(True))
test('a Seer who never gives the hint fails after the wait', seer(False))
test('a Seer offering nothing about the scorpions fails at once', seer(False, ['Tell me my future']))


def scorpion(world, key, at=None, distance=3):
    tile = at if at is not None else Tile(2552, 3572, 0)
    return Fake(id=SCORPION_NPC[key], name='Kharid Scorpion', distance=lambda: distance, tile=lambda: tile)


def cages():
    world = Taverley(SC_TILE.OUTPOST_HUT)
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(False)
    expect(world.logged('no scorpion cage in the pack')).to_be(True)
    world.hold(CAGE_ID.B)
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(True)
    world.pack = []
    world.hold(CAGE_ID.EMPTY)
    expect(run_wait(legs.cage_scorpion('a', world.log))).to_be(False)
    expect(world.logged('no Kharid Scorpion 385 within 10 tiles')).to_be(True)
    world.npcs = [scorpion(world, 'b')]
    world.walk_ok = False
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(False)
    expect(world.logged('could not reach the B scorpion at (2552,3572)')).to_be(True)
    world.walk_ok = True
    world.pack[0]._fields['use_on'] = lambda target: False
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(False)
    expect(world.logged('the B scorpion refused the cage')).to_be(True)
    world.pack[0]._fields['use_on'] = lambda target: True
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(False)
    expect(world.logged('it has wandered off')).to_be(True)

    def catch(target):
        world.pack = [Fake(id=CAGE_ID.B)]
        return True
    world.pack[0]._fields['use_on'] = catch
    expect(run_wait(legs.cage_scorpion('b', world.log))).to_be(True)
    expect(world.logged('caught the B scorpion')).to_be(True)


test('a scorpion is caged by id, and the cage id changing proves the catch', cages)


def outpost():
    world = Taverley()
    left = spy_on(legs, 'leave_deep_dungeon', impl=lambda log: result(False))
    expect(run_wait(legs.catch_outpost_scorpion(world.log))).to_be(False)
    left.mock_implementation(lambda log: result(True))
    crawled = spy_on(legs, 'ensure_barcrawl', impl=lambda log: result(False))
    expect(run_wait(legs.catch_outpost_scorpion(world.log))).to_be(False)
    crawled.mock_implementation(lambda log: result(True))
    world.walk_ok = False
    expect(run_wait(legs.catch_outpost_scorpion(world.log))).to_be(False)
    expect(world.logged("could not get into Ivor's hut")).to_be(True)
    world.walk_ok = True
    caged = spy_on(legs, 'cage_scorpion', impl=lambda key, log: result(True))
    expect(run_wait(legs.catch_outpost_scorpion(world.log))).to_be(True)
    expect(caged.calls[0][0]).to_be('b')


test("the outpost scorpion is caught in Ivor's hut after the barcrawl", outpost)


def step(order, name):
    return lambda *args: result(order.append(name) is None)


def taverley():
    world = Taverley()
    order = []
    for name in ['leave_cell', 'stock_antipoison', 'enter_deep_dungeon', 'leave_deep_dungeon', 'cure_poison']:
        spy_on(legs, name, impl=step(order, name))
    spy_on(legs, 'poison_mark', returns=0)
    spy_on(legs, 'cross_secret_wall', impl=lambda inward, log: result(order.append('in' if inward else 'out') is None))
    spy_on(legs, 'cage_scorpion', impl=lambda key, log: result(order.append(key) is None))
    expect(run_wait(legs.catch_taverley_scorpion(world.log))).to_be(True)
    expect(order).to_equal(['leave_cell', 'stock_antipoison', 'enter_deep_dungeon', 'in', 'a', 'out',
                            'leave_deep_dungeon', 'cure_poison'])
    for name in ['leave_cell', 'enter_deep_dungeon', 'cage_scorpion', 'leave_deep_dungeon']:
        spy_on(legs, name, impl=lambda *args: result(False))
        expect(run_wait(legs.catch_taverley_scorpion(world.log)), name).to_be(False)
        spy_on(legs, name, impl=lambda *args: result(True))
    for inward in [True, False]:
        spy_on(legs, 'cross_secret_wall', impl=wall_fails(inward))
        expect(run_wait(legs.catch_taverley_scorpion(world.log))).to_be(False)


def wall_fails(failing):
    return lambda inward, log: result(inward != failing)


test('the Taverley scorpion is caught behind the wall, with the cell left and the poison cured outside', taverley)


def monastery():
    world = Taverley(SC_TILE.ABBOT)
    left = spy_on(legs, 'leave_deep_dungeon', impl=lambda log: result(False))
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    left.mock_implementation(lambda log: result(True))
    talked = spy_on(legs, 'talk_through', impl=lambda name, prefer, log: result(False))
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    expect(world.logged('asking Abbot Langley')).to_be(True)
    talked.mock_implementation(lambda name, prefer, log: result(True))
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    expect(world.logged('no monastery ladder to climb')).to_be(True)
    world.locs = [world.loc(SC_ID.MONASTERY_LADDER, ['Climb-up'])]
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    expect(world.logged('the monastery ladder did not let us up')).to_be(True)
    world.locs = [world.loc(SC_ID.MONASTERY_LADDER, ['Climb-up'], interact=world.moves(Tile(3057, 3484, 1)))]
    caged = spy_on(legs, 'cage_scorpion', impl=lambda key, log: result(True))
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(True)
    expect(caged.calls[0][0]).to_be('c')
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(True)
    world.walk_ok = False
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    world.at = SC_TILE.ABBOT
    expect(run_wait(legs.catch_monastery_scorpion(world.log))).to_be(False)
    expect(run_wait(legs.climb_to_the_robes(world.log))).to_be(False)


test('the monastery scorpion is caught upstairs after joining the order', monastery)

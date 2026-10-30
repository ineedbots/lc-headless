"""Waterfall Quest's legs: self-funding, the raft and book, Golrie's pebble, the tomb, the falls, the pillars and the
dungeon's doors out."""

import rs2004.quests.defs.waterfall as wf
from rs2004 import execution
from rs2004.geometry import Tile

ITEM = wf.ITEM
LOC = wf.LOC
MOUND = Tile(2510, 3480, 0)
TREE_BANK = Tile(2512, 3470, 0)
LEDGE = Tile(2511, 3463, 0)
DUNGEON = Tile(2580, 9870, 0)
BETWEEN_DOORS = Tile(2568, 9896, 0)
PUZZLE = Tile(2565, 9912, 0)
RAISED = Tile(2603, 9906, 0)
TOMB = Tile(2530, 9845, 0)
TGV = Tile(2548, 9565, 0)
MAINLAND = wf.ARDOUGNE_BANK


def result(value):
    return value
    yield


class Falls:
    """The player, their pack and the locs around them. Each tick of a wait runs on_tick first."""

    def __init__(self, at=None):
        self.at = at if at is not None else MAINLAND
        self.pack = []
        self.worn = []
        self.locs = []
        self.npcs = []
        self.walks = []
        self.walk_ok = True
        self.hp = 10
        self.base = 10
        self.xp = 0
        self.energy = 100
        self.run = True
        self.run_ok = True
        self.messages = []
        self.modal = -1
        self.closed = 0
        self.status = 'in_progress'
        self.now = 0
        self.on_tick = None
        self.on_sustain = None
        self.lines = []
        self.chat = FakeChat().install(wf.chat_dialog)
        spy_on(wf.game, 'tile', impl=lambda: self.at)
        spy_on(wf.game, 'energy', impl=lambda: self.energy)
        spy_on(wf.game, 'run_enabled', impl=lambda: self.run)
        spy_on(wf.game, 'set_run', impl=self.set_run)
        spy_on(wf.skills, 'effective', impl=lambda name: self.hp)
        spy_on(wf.skills, 'level', impl=lambda name: self.base)
        spy_on(wf.skills, 'xp', impl=lambda name: self.xp)
        spy_on(wf.locs, 'query', impl=querying(lambda: self.locs))
        spy_on(wf.npcs, 'query', impl=querying(lambda: self.npcs))
        spy_on(wf.traversal, 'walk_resilient', impl=self.walk)
        spy_on(wf.inventory, 'items', impl=lambda: self.pack)
        spy_on(wf.inventory, 'free', impl=lambda: 28 - len(self.pack))
        spy_on(wf.equipment, 'items', impl=lambda: self.worn)
        spy_on(wf.game_messages, 'mark', impl=lambda: len(self.messages))
        spy_on(wf.game_messages, 'saw_since', impl=lambda mark, text: any([text in m for m in self.messages[mark:]]))
        spy_on(wf.reader, 'modals', impl=lambda: Fake(main=self.modal))
        spy_on(wf.quests, 'status', impl=lambda name: self.status)
        spy_on(wf.sustain, 'run', impl=self.sustain)
        patch(wf._core, 'close_interfaces', self.close)
        patch(wf._core, 'step_time', lambda: self.now)
        patch(execution, 'delay_until', self.until)
        patch(execution, 'delay_ticks', instant_ticks)

    def log(self, text):
        self.lines.append(text)

    def logged(self, part):
        return any([part in line for line in self.lines])

    def until(self, cond, timeout_ms=6000):
        if self.on_tick is not None:
            self.on_tick()
        return cond()
        yield

    def sustain(self):
        if self.on_sustain is not None:
            self.on_sustain()
        return True
        yield

    def close(self):
        self.closed += 1
        self.modal = -1

    def set_run(self, on):
        if self.run_ok:
            self.run = on
        return self.run_ok

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok:
            self.at = tile
        return self.walk_ok
        yield

    def hold(self, item, count=1, use_on=None, interact=None):
        thing = Fake(id=item.id, name=item.name, count=count,
                     use_on=use_on if use_on is not None else (lambda other: True),
                     interact=interact if interact is not None else (lambda op: True))
        self.pack.append(thing)
        return thing

    def count(self, item):
        return sum([thing.count for thing in self.pack if thing.id == item.id])

    def drop(self, item):
        self.pack = [thing for thing in self.pack if thing.id != item.id]

    def loc(self, id, ops=None, at=None, interact=None, distance=1, name='Scenery'):
        tile = at if at is not None else self.at
        return Fake(id=id, name=name, actions=lambda: ops if ops is not None else [], distance=lambda: distance,
                    tile=lambda: tile, interact=interact if interact is not None else (lambda op: True))

    def moves(self, tile):
        """An interaction that takes the player to tile."""
        def go(*args):
            self.at = tile
            return True
        return go

    def gives(self, item):
        """An interaction that puts item in the pack."""
        def give(*args):
            self.hold(item)
            return True
        return give


# Self-funding at the Varrock and Al Kharid Men.

def man(world, anchor, interact=None):
    return Fake(name='Man', actions=lambda: ['Pickpocket'], tile=lambda: anchor, distance=lambda: 2,
                interact=interact if interact is not None else (lambda op: True))


def reaches_man():
    world = Falls()
    world.walk_ok = False
    expect(run_wait(wf.reach_funding_man(wf.VARROCK_MAN, world.log))).to_be(False)
    world.walk_ok = True
    world.npcs = [man(world, wf.VARROCK_MAN)]
    expect(run_wait(wf.reach_funding_man(wf.VARROCK_MAN, world.log))).to_be(True)
    world.npcs = [man(world, Tile(3300, 3405, 0))]
    expect(run_wait(wf.reach_funding_man(wf.VARROCK_MAN, world.log))).to_be(False)
    expect(world.logged('no pickpocketable Man')).to_be(True)
    world.on_tick = lambda: world.npcs.append(man(world, wf.VARROCK_MAN))
    expect(run_wait(wf.reach_funding_man(wf.VARROCK_MAN, world.log))).to_be(True)


test('a funding Man counts only inside his leash, and may wander back in', reaches_man)


def pickpockets():
    world = Falls()
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(False)
    world.walk_ok = False
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(False)
    world.walk_ok = True
    world.npcs = [man(world, wf.AL_KHARID_MAN, lambda op: False)]
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(False)

    def paid(op):
        world.hold(ITEM.COINS, 3)
        world.chat.pages = ['continue', 'continue']
        return True
    world.npcs = [man(world, wf.AL_KHARID_MAN, paid)]
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(True)
    expect(world.count(ITEM.COINS)).to_be(3)
    expect(world.chat.pages).to_equal([])

    def stunned(op):
        world.hp -= 1
        return True
    world.npcs = [man(world, wf.AL_KHARID_MAN, stunned)]
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(True)
    world.npcs = [man(world, wf.AL_KHARID_MAN)]
    expect(run_wait(wf.pickpocket_funding_man(wf.AL_KHARID_MAN, world.log))).to_be(True)
    expect(world.logged('produced no coin')).to_be(True)


test('a pickpocket is judged by coins, XP, health or a dialogue, and a silent one is retried', pickpockets)


def seller(world, interact=None):
    return Fake(name='Kebab seller', actions=lambda: ['Talk-to'], distance=lambda: 2,
                interact=interact if interact is not None else (lambda op: True))


def buys_kebab():
    world = Falls()
    world.walk_ok = False
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(False)
    expect(world.logged('no talkable Kebab seller')).to_be(True)
    world.npcs = [seller(world, lambda op: False)]
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(False)
    world.npcs = [seller(world)]
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(False)
    expect(world.logged('accepted no exact purchase')).to_be(True)

    def talk(op):
        world.chat.pages = ['continue', ['Yes please.', 'No thanks.']]
        return True
    world.npcs = [seller(world, talk)]
    world.chat.on_choose = lambda text: world.hold(ITEM.KEBAB)
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(True)
    expect(world.chat.chosen).to_equal(['Yes please.'])

    def odd(op):
        world.chat.pages = [['Buy a kebab', 'No thanks.']]
        return True
    world.npcs = [seller(world, odd)]
    expect(run_wait(wf.buy_funding_kebab(world.log))).to_be(False)
    expect(world.logged('unexpected options')).to_be(True)


test("a kebab is bought only through the seller's exact Yes please", buys_kebab)


def eats_kebab():
    world = Falls()
    expect(run_wait(wf.eat_funding_kebab())).to_be(False)
    world.hold(ITEM.KEBAB, interact=lambda op: False)
    expect(run_wait(wf.eat_funding_kebab())).to_be(False)
    world.drop(ITEM.KEBAB)
    world.hold(ITEM.KEBAB, interact=lambda op: world.drop(ITEM.KEBAB) is None)
    expect(run_wait(wf.eat_funding_kebab())).to_be(True)


test('a kebab is eaten when it leaves the pack', eats_kebab)


def restores_health():
    world = Falls()
    world.hp = 1
    world.hold(ITEM.COINS, 5)
    bought = spy_on(wf, 'buy_funding_kebab', impl=lambda log: result(True))

    def eat():
        world.hp += 1
        return True
        yield
    spy_on(wf, 'eat_funding_kebab', impl=eat)
    expect(run_wait(wf.restore_funding_health(True, world.log))).to_be(True)
    expect(len(bought.calls)).to_be(2)
    world.hp = 1
    bought.mock_implementation(lambda log: result(False))
    expect(run_wait(wf.restore_funding_health(True, world.log))).to_be(False)

    def heal():
        world.hp += 1
    world.on_tick = heal
    expect(run_wait(wf.restore_funding_health(False, world.log))).to_be(True)
    expect(world.logged('waiting for 3 Hitpoints')).to_be(True)


test('health below the safe mark is bought back with kebabs, or waited for without them', restores_health)


def farms():
    world = Falls()
    reached = spy_on(wf, 'reach_funding_man', impl=lambda anchor, log: result(False))
    expect(run_wait(wf.farm_waterfall_coins(wf.VARROCK_MAN, 300, False, world.log))).to_be(False)
    reached.mock_implementation(lambda anchor, log: result(True))
    restored = spy_on(wf, 'restore_funding_health', impl=lambda kebabs, log: result(True))

    def steal(anchor, log):
        world.hold(ITEM.COINS, 60)
        return True
        yield
    stolen = spy_on(wf, 'pickpocket_funding_man', impl=steal)
    expect(run_wait(wf.farm_waterfall_coins(wf.VARROCK_MAN, 300, False, world.log))).to_be(True)
    expect(len(stolen.calls)).to_be(5)
    expect(world.logged('Waterfall funding: 300/300 gp')).to_be(True)
    stolen.mock_implementation(lambda anchor, log: result(False))
    expect(run_wait(wf.farm_waterfall_coins(wf.VARROCK_MAN, 400, False, world.log))).to_be(False)
    restored.mock_implementation(lambda kebabs, log: result(False))
    expect(run_wait(wf.farm_waterfall_coins(wf.VARROCK_MAN, 400, False, world.log))).to_be(False)


test('coins are farmed to the target, reporting each hundred', farms)


def stalls():
    world = Falls()
    spy_on(wf, 'reach_funding_man', impl=lambda anchor, log: result(True))
    spy_on(wf, 'restore_funding_health', impl=lambda kebabs, log: result(True))

    def nothing(anchor, log):
        world.now += 30000
        return True
        yield
    spy_on(wf, 'pickpocket_funding_man', impl=nothing)
    expect(run_wait(wf.farm_waterfall_coins(wf.VARROCK_MAN, 100, False, world.log))).to_be(False)
    expect(world.logged('for 120s at the verified Man')).to_be(True)


test('two minutes without coins, XP or health change stops the farm', stalls)


class Funding(Falls):
    def __init__(self, coins=0):
        Falls.__init__(self)
        if coins > 0:
            self.hold(ITEM.COINS, coins)
        self.farmed = []
        self.farm_ok = True
        self.into_al_kharid = True
        spy_on(wf, 'farm_waterfall_coins', impl=self.farm)

    def farm(self, anchor, target, kebabs, log):
        self.farmed.append((anchor, target, kebabs))
        if self.farm_ok:
            self.drop(ITEM.COINS)
            self.hold(ITEM.COINS, target)
        return self.farm_ok
        yield

    def walk(self, tile, radius=None, attempts=None, timeout_ms=None, log=None):
        self.walks.append(tile)
        if self.walk_ok and (tile != wf.AL_KHARID_MAN or self.into_al_kharid):
            self.at = tile
        return self.walk_ok
        yield


def funds():
    world = Funding(600)
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(True)
    expect(world.farmed).to_equal([])
    world = Funding()
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(True)
    target = wf.waterfall_funding_target(500, MAINLAND)
    expect(world.farmed).to_equal([(wf.VARROCK_MAN, wf.AL_KHARID_ENTRY_CASH, False), (wf.AL_KHARID_MAN, target, True)])
    expect(world.at).to_equal(MAINLAND)
    world = Funding()
    expect(run_wait(wf.fund_waterfall_coins(10, MAINLAND, world.log))).to_be(True)
    expect(len(world.farmed)).to_be(1)


test('self-funding earns the toll in Varrock, then the target and fares in Al Kharid', funds)


def funding_fails():
    world = Funding()
    world.farm_ok = False
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)
    world = Funding(20)
    world.walk_ok = False
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)
    world = Funding(20)
    world.into_al_kharid = False
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)
    expect(world.logged('did not cross the Al Kharid toll gate')).to_be(True)
    world = Funding(20)
    world.at = wf.AL_KHARID_MAN
    world.farm_ok = False
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)
    world = Funding(20)
    world.at = wf.AL_KHARID_MAN
    world.walk_ok = False
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)

    def short(anchor, target, kebabs, log):
        world.drop(ITEM.COINS)
        world.hold(ITEM.COINS, 100)
        return True
        yield
    world = Funding(20)
    world.at = wf.AL_KHARID_MAN
    spy_on(wf, 'farm_waterfall_coins', impl=short)
    expect(run_wait(wf.fund_waterfall_coins(500, MAINLAND, world.log))).to_be(False)
    expect(world.logged('below the required 500')).to_be(True)


test('self-funding stops on a failed farm, walk, toll gate or a short return', funding_fails)


# The raft, Hudon and the book.

def raft(world, interact=None):
    return world.loc(LOC.RAFT, ['Board'], interact=interact if interact is not None else world.moves(MOUND))


def boards_raft():
    world = Falls()
    world.walk_ok = False
    expect(run_wait(wf.board_raft(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.board_raft(world.log))).to_be(False)
    world.locs = [raft(world, lambda op: False)]
    expect(run_wait(wf.board_raft(world.log))).to_be(False)

    def ride(op):
        world.at = MOUND
        world.chat.pages = ['continue', 'continue', 'continue']
        return True
    world.locs = [raft(world, ride)]
    expect(run_wait(wf.stage_one_leg(world.log))).to_be(True)
    expect(world.chat.pages).to_equal([])
    talked = spy_on(wf, 'talk_through', impl=lambda name, prefer, log: result(True))
    expect(run_wait(wf.stage_one_leg(world.log))).to_be(True)
    expect(talked.calls[0][0]).to_be('Hudon')
    world.walk_ok = False
    expect(run_wait(wf.stage_one_leg(world.log))).to_be(False)


test("the raft lands on Hudon's mound and his forced dialogue is finished there", boards_raft)


def swims_back():
    world = Falls(MOUND)
    world.walk_ok = False
    expect(run_wait(wf.leave_hudon_mound(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.leave_hudon_mound(world.log))).to_be(False)
    world.locs = [world.loc(LOC.CROSSING_ROCK, ['Swim to'], interact=world.moves(MAINLAND))]
    expect(run_wait(wf.leave_hudon_mound(world.log))).to_be(True)


test("the mound is left by swimming to the crossing rock", swims_back)


def reads_book():
    world = Falls()
    expect(run_wait(wf.read_book())).to_be(False)

    def read(op):
        world.modal = 392
        return True
    world.hold(ITEM.BOOK, interact=read)
    expect(run_wait(wf.read_book())).to_be(True)
    expect(world.closed).to_be(1)
    expect(run_wait(wf.book_leg(world.log))).to_be(True)


test('the book is read and its page closed', reads_book)


def finds_book():
    world = Falls(MOUND)
    left = spy_on(wf, 'leave_hudon_mound', impl=lambda log: result(True))
    expect(run_wait(wf.book_leg(world.log))).to_be(True)
    expect(len(left.calls)).to_be(1)
    world.at = MAINLAND
    world.walk_ok = False
    expect(run_wait(wf.book_leg(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.book_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.BOOKCASE, ['Search'])]
    expect(run_wait(wf.book_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.BOOKCASE, ['Search'], interact=world.gives(ITEM.BOOK))]
    expect(run_wait(wf.book_leg(world.log))).to_be(True)


test("the book is searched for in the tourist office's bookcase", finds_book)


# Golrie's pebble, in the Tree Gnome Village dungeon.

def pebble():
    world = Falls(MAINLAND)
    hopped = spy_on(wf, 'walk_with_hops', impl=lambda dest, radius, hops, log: result(False))
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)
    hopped.mock_implementation(lambda dest, radius, hops, log: result(True))
    world.at = TGV
    world.walk_ok = False
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.GOLRIE_CRATE, ['Search'], interact=world.gives(ITEM.GOLRIE_KEY))]
    expect(run_wait(wf.pebble_leg(world.log))).to_be(True)
    world.locs = []
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.GOLRIE_GATE)]
    world.drop(ITEM.GOLRIE_KEY)
    world.hold(ITEM.GOLRIE_KEY, use_on=world.moves(wf.GOLRIE_STAND))
    expect(run_wait(wf.pebble_leg(world.log))).to_be(True)
    talked = spy_on(wf, 'talk_through', impl=lambda name, prefer, log: result(False))
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)

    def golrie(name, prefer, log):
        world.hold(ITEM.PEBBLE)
        return True
        yield
    talked.mock_implementation(golrie)
    expect(run_wait(wf.pebble_leg(world.log))).to_be(True)
    expect(run_wait(wf.pebble_leg(world.log))).to_be(True)
    expect(hopped.calls[-1][0]).to_equal(Tile(2533, 3156, 0))
    world.drop(ITEM.PEBBLE)
    world.walk_ok = False
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)
    world.at = TGV
    expect(run_wait(wf.pebble_leg(world.log))).to_be(False)


test("Golrie's pebble needs the crate's key, his gate and a talk", pebble)


# Glarial's tomb.

def enters_tomb():
    world = Falls()
    world.walk_ok = False
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.walk_ok = True
    world.locs = [world.loc(LOC.TOMBSTONE)]
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.hold(ITEM.PEBBLE, use_on=world.moves(TOMB))
    expect(run_wait(wf.tomb_leg(world.log))).to_be(True)


test("the tomb is entered with Glarial's pebble on her tombstone", enters_tomb)


def loots_tomb():
    world = Falls(TOMB)
    world.walk_ok = False
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.walk_ok = True
    world.locs = [world.loc(LOC.CHEST_CLOSED, ['Open'], interact=lambda op: False)]
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.CHEST_CLOSED, ['Open'])]
    expect(run_wait(wf.tomb_leg(world.log))).to_be(True)
    world.locs = []
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.CHEST_OPEN, ['Search'], interact=world.gives(ITEM.AMULET))]
    expect(run_wait(wf.tomb_leg(world.log))).to_be(True)
    world.walk_ok = False
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.COFFIN, ['Search'], interact=world.gives(ITEM.FULL_URN))]
    expect(run_wait(wf.tomb_leg(world.log))).to_be(True)
    world.walk_ok = False
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.tomb_leg(world.log))).to_be(False)
    world.locs = [world.loc(1757, ['Climb-up'], interact=world.moves(MAINLAND))]
    world.hp = 4
    expect(run_wait(wf.tomb_leg(world.log))).to_be(True)
    expect(world.logged('Glarial tomb exit: cannot reach full health')).to_be(True)


test("the tomb gives the amulet from the chest and the urn from the coffin, then is left by its ladder", loots_tomb)


# The falls, the ledge and the barrel.

def heals():
    world = Falls()
    world.hp = 6

    def eat():
        world.hp += 2
    world.on_sustain = eat
    expect(run_wait(wf.heal_to_full(world.log, 'test'))).to_be(True)
    expect(world.hp).to_be(10)
    world.hp = 6
    world.on_sustain = None
    expect(run_wait(wf.heal_to_full(world.log, 'test'))).to_be(False)
    expect(world.logged('test: cannot reach full health')).to_be(True)


test('healing to full stops when the food stops healing', heals)


def sprints():
    world = Falls(LEDGE)
    world.energy = 10
    world.hp = 8
    world.run = False

    def rest():
        world.energy += 20
        world.hp = world.base
    world.on_sustain = rest
    expect(run_wait(wf.prepare_dungeon_sprint(world.log))).to_be(True)
    expect(world.run).to_be(True)
    expect(world.logged('waiting on the safe Waterfall ledge')).to_be(True)
    world.run = False
    world.run_ok = False
    expect(run_wait(wf.prepare_dungeon_sprint(world.log))).to_be(False)
    expect(world.logged('could not enable run')).to_be(True)
    world.on_sustain = None
    world.hp = 5
    escaped = spy_on(wf, 'barrel_escape', impl=lambda log: result(True))
    expect(run_wait(wf.prepare_dungeon_sprint(world.log))).to_be(False)
    expect(len(escaped.calls)).to_be(1)


test('the dungeon is entered with run energy, full health and run on, or left by barrel', sprints)


def barrel():
    world = Falls()
    expect(run_wait(wf.barrel_escape(world.log))).to_be(True)
    world.at = LEDGE
    expect(run_wait(wf.barrel_escape(world.log))).to_be(False)
    expect(world.logged('no Waterfall escape barrel')).to_be(True)
    world.locs = [world.loc(LOC.BARREL, ['Get in'], interact=lambda op: False)]
    expect(run_wait(wf.barrel_escape(world.log))).to_be(False)
    world.locs = [world.loc(LOC.BARREL, ['Get in'], interact=world.moves(MAINLAND))]
    expect(run_wait(wf.barrel_escape(world.log))).to_be(True)


test('the ledge is left in the barrel', barrel)


def falls():
    world = Falls(MOUND)
    world.walk_ok = False
    expect(run_wait(wf.falls_leg(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.falls_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.CROSSING_ROCK, distance=3)]
    world.hold(ITEM.ROPE, use_on=lambda target: world.moves(TREE_BANK if target.id == LOC.CROSSING_ROCK else LEDGE)())
    expect(run_wait(wf.falls_leg(world.log))).to_be(True)
    expect(world.at).to_equal(TREE_BANK)
    expect(run_wait(wf.falls_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.DEAD_TREE)]
    expect(run_wait(wf.falls_leg(world.log))).to_be(True)
    expect(world.at).to_equal(LEDGE)
    sprint = spy_on(wf, 'prepare_dungeon_sprint', impl=lambda log: result(False))
    expect(run_wait(wf.falls_leg(world.log))).to_be(False)
    sprint.mock_implementation(lambda log: result(True))
    expect(run_wait(wf.falls_leg(world.log))).to_be(False)
    world.locs = [world.loc(LOC.LEDGE_DOOR, ['Open'], interact=world.moves(Tile(2575, 9862, 0)))]
    expect(run_wait(wf.falls_leg(world.log))).to_be(True)
    world.at = MAINLAND
    world.locs = [raft(world)]
    expect(run_wait(wf.falls_leg(world.log))).to_be(True)


test('the falls are crossed by rope to the rock and the tree, then through the ledge door', falls)


# The pillars, the key and the chalice.

def pillar_room(world, count=6, placed=True):
    """Six pillars, each taking one of every rune; placed False leaves the runes unspent and the server silent."""
    world.at = wf.PILLAR_STAND
    world.locs = [world.loc(LOC.PILLAR, at=Tile(2562 + i % 2 * 6, 9910 + i // 2 * 3, 0)) for i in range(count)]
    for rune in wf.RUNES:
        world.hold(rune, 6, use_on=lambda target: True)
    if placed:
        for thing in world.pack:
            thing._fields['use_on'] = spend(world, thing)


def spend(world, thing):
    def use(target):
        thing._fields['count'] = thing.count - 1
        world.messages.append('You place the rune on the stand.'.lower())
        return True
    return use


def pillars():
    world = Falls(PUZZLE)
    world.walk_ok = False
    expect(run_wait(wf.solve_pillars(world.log))).to_be(False)
    world.walk_ok = True
    pillar_room(world, 5)
    expect(run_wait(wf.solve_pillars(world.log))).to_be(False)
    expect(world.logged('5/6 pillars')).to_be(True)
    world.pack = []
    pillar_room(world)
    expect(run_wait(wf.solve_pillars(world.log))).to_be(False)
    expect([thing.count for thing in world.pack]).to_equal([0, 0, 0])
    world.locs.append(world.loc(LOC.GLARIAL_STATUE))
    world.hold(ITEM.AMULET, use_on=world.moves(RAISED))
    expect(run_wait(wf.solve_pillars(world.log))).to_be(True)
    world.at = PUZZLE
    world.walk_ok = False
    world.pack = []
    pillar_room(world)
    world.walk_ok = False
    expect(run_wait(wf.solve_pillars(world.log))).to_be(False)


test('every rune goes on every pillar, then the amulet on the statue raises the floor', pillars)


def unplaced():
    world = Falls(PUZZLE)
    pillar_room(world, 6, False)
    expect(run_wait(wf.solve_pillars(world.log))).to_be(False)
    expect(world.logged('placement on (2562,9910) was not acknowledged')).to_be(True)
    world.pack[0]._fields['use_on'] = lambda target: False
    expect(run_wait(wf.place_rune(wf.RUNES[0], world.locs[0], world.log))).to_be(False)
    world.drop(wf.RUNES[0])
    expect(run_wait(wf.place_rune(wf.RUNES[0], world.locs[0], world.log))).to_be(True)


test('a rune the server does not take stops the pillars', unplaced)


def key():
    world = Falls(DUNGEON)
    world.hold(ITEM.BAXTORIAN_KEY)
    expect(run_wait(wf.find_baxtorian_key(world.log))).to_be(True)
    world.pack = []
    world.walk_ok = False
    expect(run_wait(wf.find_baxtorian_key(world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.find_baxtorian_key(world.log))).to_be(False)
    world.locs = [world.loc(LOC.BAXTORIAN_CRATE, ['Search'], interact=world.gives(ITEM.BAXTORIAN_KEY))]
    expect(run_wait(wf.find_baxtorian_key(world.log))).to_be(True)
    world.pack = []
    world.hp = 3
    left = spy_on(wf, 'exit_waterfall_dungeon', impl=lambda log: result(True))
    expect(run_wait(wf.find_baxtorian_key(world.log))).to_be(False)
    expect(len(left.calls)).to_be(1)


test("Baxtorian's key is searched for at full health, or the dungeon is left", key)


def chalice():
    world = Falls(DUNGEON)
    expect(run_wait(wf.complete_quest(world.log))).to_be(False)
    world.at = RAISED
    for i in range(24):
        world.hold(ITEM.KEBAB)
    left = spy_on(wf, 'exit_waterfall_dungeon', impl=lambda log: result(True))
    expect(run_wait(wf.complete_quest(world.log))).to_be(True)
    expect(world.logged('fewer than five reward slots')).to_be(True)
    world.pack = []
    world.locs = [world.loc(LOC.CHALICE, distance=4)]
    expect(run_wait(wf.complete_quest(world.log))).to_be(False)

    def pour(target):
        world.status = 'complete'
        return True
    world.hold(ITEM.FULL_URN, use_on=pour)
    expect(run_wait(wf.complete_quest(world.log))).to_be(True)
    expect(len(left.calls)).to_be(1)


test("the urn is poured on the chalice with five free slots, or the treasure washes the player out", chalice)


class Doors(Falls):
    """The keyed doors move the player across them; the entry door to the ledge."""

    def __init__(self, at):
        Falls.__init__(self, at)
        self.hold(ITEM.BAXTORIAN_KEY, use_on=self.unlock)
        self.locs = [self.loc(LOC.KEYED_DOOR), self.loc(LOC.ENTRY_DOOR, ['Open'], interact=self.moves(LEDGE)),
                     self.loc(LOC.BARREL, ['Get in'], interact=self.moves(MAINLAND)),
                     self.loc(LOC.CHALICE, ['Take treasure'], interact=self.moves(MAINLAND))]

    def unlock(self, door):
        if self.at == wf.PUZZLE_DOOR_NORTH_STAND:
            self.at = BETWEEN_DOORS
        elif self.at == wf.SOUTH_DOOR_NORTH_STAND:
            self.at = DUNGEON
        elif self.at == wf.SOUTH_DOOR_STAND:
            self.at = BETWEEN_DOORS
        elif self.at == wf.PUZZLE_DOOR_STAND:
            self.at = PUZZLE
        return True


def exits():
    for start in [RAISED, PUZZLE, BETWEEN_DOORS, DUNGEON, LEDGE]:
        world = Doors(start)
        expect(run_wait(wf.exit_waterfall_dungeon(world.log)), str(start)).to_be(True)
        expect(world.at).to_equal(MAINLAND)


test('the dungeon is left from any room, back through each keyed door and out by the barrel', exits)


def exits_fail():
    world = Doors(RAISED)
    world.locs = []
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)
    world = Doors(PUZZLE)
    world.walk_ok = False
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)
    world = Doors(BETWEEN_DOORS)
    world.locs = world.locs[1:]
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)
    world = Doors(DUNGEON)
    world.walk_ok = False
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)
    world = Doors(DUNGEON)
    world.locs = [world.loc(LOC.ENTRY_DOOR, ['Open'])]
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)
    world.locs = []
    expect(run_wait(wf.exit_waterfall_dungeon(world.log))).to_be(False)


test('the dungeon exit stops at a missing chalice, door or key, or a failed walk', exits_fail)


def dungeon_leg():
    world = Falls(RAISED)
    finished = spy_on(wf, 'complete_quest', impl=lambda log: result(True))
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.ENTERED_PUZZLE, world.log))).to_be(False)
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.RAISED_FLOOR, world.log))).to_be(True)
    expect(len(finished.calls)).to_be(1)
    keyed = spy_on(wf, 'find_baxtorian_key', impl=lambda log: result(False))
    world.at = DUNGEON
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.ENTERED_WATERFALL, world.log))).to_be(False)
    keyed.mock_implementation(lambda log: result(True))
    crossed = spy_on(wf, 'cross_keyed_door', impl=lambda stand, arrived, log: result(True))
    solved = spy_on(wf, 'solve_pillars', impl=lambda log: result(True))
    rows = [(DUNGEON, wf.WATERFALL_STAGE.ENTERED_WATERFALL, wf.SOUTH_DOOR_STAND),
            (BETWEEN_DOORS, wf.WATERFALL_STAGE.ENTERED_WATERFALL, wf.PUZZLE_DOOR_STAND),
            (BETWEEN_DOORS, wf.WATERFALL_STAGE.RAISED_FLOOR, wf.PUZZLE_DOOR_STAND),
            (PUZZLE, wf.WATERFALL_STAGE.RAISED_FLOOR, wf.PUZZLE_DOOR_NORTH_STAND)]
    for at, stage, stand in rows:
        world.at = at
        expect(run_wait(wf.dungeon_leg(stage, world.log))).to_be(True)
        expect(crossed.calls[-1][0], str(at)).to_equal(stand)
        expect(crossed.calls[-1][1]()).to_be(False)
    world.at = PUZZLE
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.ENTERED_PUZZLE, world.log))).to_be(True)
    expect(len(solved.calls)).to_be(1)
    world.at = Tile(2600, 9900, 0)
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.RAISED_FLOOR, world.log))).to_be(True)
    expect(world.at).to_equal(wf.RAISED_ROOM_STAND)
    world.at = Tile(2600, 9900, 0)
    world.walk_ok = False
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.RAISED_FLOOR, world.log))).to_be(False)
    world.at = None
    expect(run_wait(wf.dungeon_leg(wf.WATERFALL_STAGE.RAISED_FLOOR, world.log))).to_be(False)


test('the dungeon leg crosses to the next room for its stage, then solves or finishes', dungeon_leg)


def crosses_door():
    world = Falls(DUNGEON)
    world.walk_ok = False
    expect(run_wait(wf.cross_keyed_door(wf.SOUTH_DOOR_STAND, lambda: True, world.log))).to_be(False)
    world.walk_ok = True
    expect(run_wait(wf.cross_keyed_door(wf.SOUTH_DOOR_STAND, lambda: True, world.log))).to_be(False)
    world.locs = [world.loc(LOC.KEYED_DOOR)]
    world.hold(ITEM.BAXTORIAN_KEY)
    expect(run_wait(wf.cross_keyed_door(wf.SOUTH_DOOR_STAND, lambda: True, world.log))).to_be(True)


test("a keyed door is crossed with Baxtorian's key", crosses_door)


# Banking and the journal.

def strips():
    world = Falls()
    steps = []

    def deposit(step, hops, log):
        steps.append(step.leave_open)
        return True
        yield
    spy_on(wf, 'execute_step', impl=deposit)
    removed = []

    def unequip(name):
        removed.append(name)
        return name != 'Cape'
        yield
    spy_on(wf.equipment, 'unequip', impl=unequip)
    world.worn = [Fake(name='Amulet of power'), Fake(name=None)]
    expect(run_wait(wf.strip_and_deposit([ITEM.COINS.id], world.log))).to_be(True)
    expect(steps).to_equal([False, True])
    expect(removed).to_equal(['Amulet of power'])
    world.worn = [Fake(name='Cape')]
    expect(run_wait(wf.strip_and_deposit([ITEM.COINS.id], world.log))).to_be(False)
    spy_on(wf, 'execute_step', impl=lambda step, hops, log: result(False))
    expect(run_wait(wf.strip_and_deposit([ITEM.COINS.id], world.log))).to_be(False)


test('stripping banks the pack, takes off every worn item, then banks again with the bank left open', strips)


def journal_stage():
    world = Falls()
    world.status = 'complete'
    expect(run_wait(wf.read_waterfall_stage())).to_be(wf.WATERFALL_STAGE.COMPLETE)
    world.status = 'not_started'
    expect(run_wait(wf.read_waterfall_stage())).to_be(wf.WATERFALL_STAGE.NOT_STARTED)
    world.status = 'unknown'
    expect(run_wait(wf.read_waterfall_stage())).to_be(None)
    world.status = 'in_progress'

    def journal(name):
        world.modal = 275
        return ['I found Hudon a short raft ride down the river.']
        yield
    spy_on(wf.quests, 'journal', impl=journal)
    expect(run_wait(wf.read_waterfall_stage())).to_be(wf.WATERFALL_STAGE.SPOKEN_TO_HUDON)
    expect(world.closed).to_be(1)


test('the stage comes from the quest list, or the journal, whose page is closed after', journal_stage)

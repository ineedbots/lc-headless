"""rs2b0t's test/api/ai/clues: AcquireTools.test.ts and shantayPass.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect, with the facades patched as rs2b0t stubs them."""

from rs2004 import execution
from rs2004.clues import guardian
from rs2004.clues.acquire import ensure_coord_tools, ensure_spade
from rs2004.clues.executor import ClueExecutor

COORD_CLUE_ID = 2801


class Tools:
    def __init__(self):
        self.held = []
        self.coord_clue = COORD_CLUE_ID
        self.here = Tile(2660, 3300, 0)
        self.walks = []
        self.spades = []
        self.takes = 0
        self.npc_at = {'Observatory professor': Tile(2438, 3186, 0), 'Murphy': Tile(2668, 3162, 0), 'Brother Kojo': Tile(2569, 3249, 0)}

    def install(self):
        w = self
        spy_on(game, 'tile', lambda: w.here)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(event_signal, 'pending', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk(dest))
        spy_on(traversal, 'walk_to', lambda dest, **opts: w.walk(dest))
        spy_on(ground_items, 'query', querying(lambda: sorted([w.spade(t) for t in w.spades], key=lambda g: g.distance())))
        spy_on(npcs, 'query', querying(lambda: [w.npc(name, tile) for name, tile in w.npc_at.items()]))
        spy_on(inventory, 'items', lambda: w.items())
        spy_on(inventory, 'first', lambda name: Fake(name=name) if name in w.held else None)
        spy_on(inventory, 'count', lambda name: len([n for n in w.held if n == name]))
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'options', lambda: [])
        return self

    def items(self):
        clue = [Fake(id=self.coord_clue, name='coord clue', count=1, slot=0)] if self.coord_clue is not None else []
        return clue + [Fake(id=5000 + i, name=n, count=1, slot=i + 1) for i, n in enumerate(self.held)]

    def walk(self, dest):
        self.walks.append(f'{dest.x},{dest.z}')
        self.here = Tile(dest.x, dest.z, 0)
        return True
        yield

    def spade(self, t):
        w = self

        def take(op):
            w.takes += 1
            w.spades = [s for s in w.spades if s is not t]
            w.held.append('Spade')
            return True

        return Fake(id=952, name='Spade', tile=lambda: t, distance=lambda: t.distance_to(w.here), interact=take)

    def npc(self, name, tile):
        w = self
        return Fake(name=name, tile=lambda: tile, distance=lambda: tile.distance_to(w.here), actions=lambda: ['Talk-to'], interact=lambda op: True)


def spade_held():
    w = Tools().install()
    w.held = ['Spade']
    expect(run_wait(ensure_spade(lambda m: None))).to_be(True)
    expect(w.walks).to_equal([])


def nearer_spawn():
    w = Tools().install()
    w.here = Tile(2600, 3320, 0)
    w.spades = [Tile(2574, 3331, 0)]
    expect(run_wait(ensure_spade(lambda m: None))).to_be(True)
    expect(w.walks[0]).to_be('2574,3331')
    expect(w.takes).to_be(1)
    expect(w.held).to_contain('Spade')


def falador():
    w = Tools().install()
    w.here = Tile(2950, 3360, 0)
    w.spades = [Tile(2981, 3369, 0)]
    expect(run_wait(ensure_spade(lambda m: None))).to_be(True)
    expect(w.walks[0]).to_be('2981,3369')


def no_spade():
    w = Tools().install()
    w.here = Tile(2600, 3320, 0)
    expect(run_wait(ensure_spade(lambda m: None))).to_be(False)


describe('ensure_spade', lambda: [
    test('already held: True, no walk', spade_held),
    test('walks to the nearer spawn and takes the spade', nearer_spawn),
    test('picks Falador when closer', falador),
    test('no spade at either spawn: False', no_spade),
])


def trio_held():
    w = Tools().install()
    w.held = ['Sextant', 'Watch', 'Chart']
    expect(run_wait(ensure_coord_tools(lambda m: None))).to_be(True)
    expect(w.walks).to_equal([])


def needs_coord_clue():
    w = Tools().install()
    w.coord_clue = None
    expect(run_wait(ensure_coord_tools(lambda m: None))).to_be(False)
    expect(w.walks).to_equal([])


def professor_first():
    w = Tools().install()
    expect(run_wait(ensure_coord_tools(lambda m: None))).to_be(False)
    expect(w.walks[0]).to_be('2438,3186')
    expect(w.walks).to_contain('2668,3162')


def chart_last():
    w = Tools().install()
    w.held = ['Sextant', 'Watch']
    run_wait(ensure_coord_tools(lambda m: None))
    expect(w.walks[0]).to_be('2438,3186')
    expect(w.walks).not_.to_contain('2668,3162')
    expect(w.walks).not_.to_contain('2569,3249')


describe('ensure_coord_tools', lambda: [
    test('all three held: True at once, no walk', trio_held),
    test('needs a coordinate clue held: False and no walk when none', needs_coord_clue),
    test('none held: visits the professor first (learn), then Murphy for the sextant', professor_first),
    test('sextant and watch held: straight to the professor for the chart, no Murphy or Kojo', chart_last),
])


# The Shantay pass (shantayPass.test.ts)

ORIGIN = Tile(3222, 3218, 0)
TARGET = Tile(3168, 3041, 0)
COUNTER = Tile(3304, 3122, 0)


def pack_item(id, name, count=1):
    return Fake(id=id, name=name, count=count, noted=False, slot=0, actions=lambda: [], interact=lambda op: True)


class Desert:
    def __init__(self):
        self.here = ORIGIN
        self.pending = False
        self.interrupt_shop = False
        self.visited = []
        self.opened = []
        self.bought = []
        self.pack = [pack_item(3552, 'Clue scroll (hard)'), pack_item(952, 'Spade'), pack_item(2574, 'Sextant'), pack_item(2575, 'Watch'), pack_item(2576, 'Chart'),
                     pack_item(385, 'Shark', 12), pack_item(2448, 'Superantipoison(4)'), pack_item(995, 'Coins', 1000)]

    def install(self):
        w = self
        spy_on(inventory, 'items', lambda: list(w.pack))
        spy_on(inventory, 'first', lambda name: w.first(name))
        spy_on(inventory, 'count', lambda name: sum([i.count for i in w.pack if i.name == name]))
        spy_on(inventory, 'count_by_id', lambda id: sum([i.count for i in w.pack if i.id == id]))
        spy_on(inventory, 'is_full', lambda: False)
        spy_on(equipment, 'items', lambda: [Fake(id=1231, name='Dragon dagger(p)', count=1, slot=3, noted=False)])
        spy_on(game, 'tile', lambda: w.here)
        spy_on(game, 'in_combat', lambda: False)
        spy_on(skills, 'level', lambda name: 60)
        spy_on(skills, 'effective', lambda name: 60)
        spy_on(quests, 'status', lambda name: 'complete')
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(chat_dialog, 'can_continue', lambda: False)
        spy_on(chat_dialog, 'is_open', lambda: False)
        spy_on(reader, 'count_dialog_open', lambda: False)
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_ticks', instant_ticks)
        spy_on(guardian.GuardianProtection, 'prepare', lambda *a: instant_until(lambda: True))
        stub(traversal, last_missing_gate_items=[])
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk(dest))
        spy_on(shop, 'open', lambda name: w.open_shop(name))
        spy_on(shop, 'close', lambda: instant_until(lambda: True))
        spy_on(shop, 'buy', lambda name, count: w.buy(name, count))
        return self

    def first(self, name):
        for i in self.pack:
            if i.name == name:
                return i
        return None

    def walk(self, dest):
        self.visited.append(dest)
        traversal.last_missing_gate_items = []
        if dest.equals(COUNTER):
            if self.interrupt_shop:
                self.pending = True
                return False
            self.here = dest
            return True
        if sum([i.count for i in self.pack if i.name == 'Shantay pass']) == 0:
            traversal.last_missing_gate_items = [Fake(name='Shantay pass', count=1)]
            return False
        self.pack = [i for i in self.pack if i.name != 'Shantay pass']
        self.here = dest
        self.pending = True
        return True
        yield

    def open_shop(self, name):
        self.opened.append(name)
        return True
        yield

    def buy(self, name, count):
        self.bought.append((name, count))
        self.pack.append(pack_item(1854, name, count))
        return count
        yield


def solve(executor):
    return run_wait(executor.solve_held_clue(lambda m: None))


def buys_pass():
    w = Desert().install()
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.opened).to_equal(['Shantay'])
    expect(w.bought).to_equal([('Shantay pass', 1)])
    expect([[t.x, t.z] for t in w.visited]).to_equal([[TARGET.x, TARGET.z], [COUNTER.x, COUNTER.z], [TARGET.x, TARGET.z]])
    expect(w.here.equals(TARGET)).to_be(True)


def buys_again():
    w = Desert().install()
    executor = ClueExecutor()
    solve(executor)
    w.here = ORIGIN
    w.pending = False
    expect(solve(executor)).to_be('yield')
    expect(len(w.bought)).to_be(2)
    expect(w.here.equals(TARGET)).to_be(True)


def interrupted():
    w = Desert().install()
    w.interrupt_shop = True
    executor = ClueExecutor()
    expect(solve(executor)).to_be('yield')
    expect(w.opened).to_equal([])
    w.interrupt_shop = False
    w.pending = False
    expect(solve(executor)).to_be('yield')
    expect(len(w.bought)).to_be(1)
    expect(w.here.equals(TARGET)).to_be(True)


describe('the Shantay pass', lambda: [
    test('buys a pass from Shantay and resumes the reported desert dig', buys_pass),
    test('can buy another consumed pass when the same trail returns to the desert', buys_again),
    test('resumes a shopping trip interrupted before reaching Shantay', interrupted),
])

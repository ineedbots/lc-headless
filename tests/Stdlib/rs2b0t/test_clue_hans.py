"""rs2b0t's test/api/ai/clues/hans.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect,
with the facades patched for a fake Lumbridge as rs2b0t spies on them. game.set_run gives nothing back here, so the
test of a run that won't turn on leaves run off and the bot reads run_enabled()."""

from rs2004 import execution
from rs2004.clues.executor import ClueExecutor
from rs2004.clues.steps import HANS_WAIT_SPOT

SPOT = HANS_WAIT_SPOT


class Lumbridge:
    def __init__(self):
        self.tick = 0
        self.energy = 10
        self.running = False
        self.pending = False
        self.clue = 2681
        self.here = Tile(3240, 3218, 0)
        self.hans = Tile(3202, 3205, 0)
        self.dialogue = False
        self.clicked_at = None
        self.advance = None
        self.walks = []
        self.direct_walks = []
        self.clicks = []
        self.reachable = True
        self.run_turns_on = True
        self.set_runs = 0

    def install(self):
        w = self
        spy_on(game, 'tile', lambda: w.here)
        spy_on(game, 'energy', lambda: w.energy)
        spy_on(game, 'tick', lambda: w.tick)
        spy_on(game, 'run_enabled', lambda: w.running)
        spy_on(game, 'set_run', lambda on: w.set_run(on))
        spy_on(event_signal, 'pending', lambda: w.pending)
        spy_on(inventory, 'items', lambda: [Fake(id=w.clue, name='Clue scroll', count=1, noted=False, actions=lambda: ['Read'])] if w.clue else [])
        spy_on(inventory, 'count_by_id', lambda id: 1 if w.clue and id == w.clue else 0)
        spy_on(inventory, 'first', lambda name: None)
        spy_on(npcs, 'query', querying(lambda: [w.hans_npc()] if w.hans is not None else []))
        spy_on(chat_dialog, 'is_open', lambda: w.dialogue)
        spy_on(chat_dialog, 'can_continue', lambda: w.dialogue)
        spy_on(chat_dialog, 'options', lambda: [])
        spy_on(chat_dialog, 'continue_', lambda: w.talked())
        patch(execution, 'delay_ticks', lambda n=1: w.ticks(n))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', lambda cond, ticks=1: w.until_ticks(cond, ticks))
        spy_on(reachability, 'can_reach', lambda tile, **kw: w.reachable)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: w.walk(dest))
        spy_on(direct_navigator, 'walk', lambda dest, run=False: w.direct(dest))
        spy_on(reach, 'npc_dialog', lambda name, near, **kw: instant_until(lambda: 'retry'))
        spy_on(modals, 'close', lambda: instant_until(lambda: True))
        return self

    def set_run(self, on):
        self.set_runs += 1
        if self.run_turns_on:
            self.running = on

    def hans_npc(self):
        w = self
        tile = self.hans

        def interact(op):
            w.clicks.append({'tick': w.tick, 'energy': w.energy, 'running': w.running, 'distance': w.here.distance_to(tile)})
            w.clicked_at = w.tick
            return True

        return Fake(id=0, index=1, name='Hans', tile=lambda: tile, distance=lambda: w.here.distance_to(tile), actions=lambda: ['Talk-to'], interact=interact)

    def talked(self):
        self.clue = 0
        self.dialogue = False
        self.pending = True
        return True
        yield

    def ticks(self, n=1):
        for _ in range(n):
            self.tick += 1
            if self.advance is not None:
                self.advance()
        return None
        yield

    def until_ticks(self, cond, ticks):
        for _ in range(ticks):
            if cond():
                break
            yield from self.ticks(1)
        return cond()

    def walk(self, dest):
        if self.pending:
            return False
        self.here = Tile(dest.x, dest.z, dest.level)
        self.walks.append(self.here)
        return True
        yield

    def direct(self, dest):
        self.here = Tile(dest.x, dest.z, dest.level)
        self.direct_walks.append(self.here)
        self.walks.append(self.here)
        return True


def solve(executor):
    return run_wait(executor.solve_held_clue(lambda m: None))


def late_patrol(id, delay):
    w = Lumbridge().install()
    w.clue = id

    def advance():
        if w.tick >= 150:
            w.hans = Tile(3221, 3219, 0)
        if w.clicked_at is not None and w.tick - w.clicked_at >= delay:
            w.dialogue = True

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clue).to_be(0)
    expect(w.clicks).to_have_length(1)
    expect(w.clicks[0]['tick']).to_be_greater_than_or_equal(150)
    expect(w.clicks[0]['energy']).to_be(10)
    expect(w.here.equals(SPOT)).to_be(True)
    expect(all([t.equals(SPOT) for t in w.walks])).to_be(True)


def low_energy():
    w = Lumbridge().install()
    executor = ClueExecutor()
    expect(solve(executor)).to_be('yield')
    expect(w.tick).to_be_greater_than_or_equal(200)
    expect(w.clue).to_be(2681)
    expect(w.clicks).to_equal([])
    expect(w.here.equals(SPOT)).to_be(True)
    expect(solve(executor)).to_be('yield')
    expect(w.clue).to_be(2681)
    expect(executor.current.target.equals(SPOT)).to_be(True)


def shared_budget():
    w = Lumbridge().install()
    w.hans = Tile(3221, 3219, 0)
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.tick).to_be_greater_than_or_equal(200)
    expect(w.tick).to_be_less_than_or_equal(201)
    expect(w.clue).to_be(2681)
    expect(w.here.equals(SPOT)).to_be(True)


def bounded_chase():
    w = Lumbridge().install()
    w.energy = 60

    def advance():
        if w.clicked_at is not None and w.tick - w.clicked_at >= 25:
            w.dialogue = True

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clue).to_be(0)
    expect(w.clicks).to_have_length(1)
    expect(w.clicks[0]).to_match_object({'energy': 60, 'running': True})
    expect(w.clicks[0]['tick']).to_be_greater_than_or_equal(200)


def failed_chase(reason):
    w = Lumbridge().install()
    w.energy = 60

    def advance():
        if w.clicked_at is None:
            return
        w.here = Tile(3210, 3205, 0)
        if reason == 'energy':
            w.energy = 19
        if reason == 'lost':
            w.hans = None

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clue).to_be(2681)
    expect(w.clicks).to_have_length(1)
    expect(w.here.equals(SPOT)).to_be(True)
    expect(w.tick - w.clicks[0]['tick']).to_be_less_than_or_equal(41)


def behind_obstacle():
    w = Lumbridge().install()
    w.hans = Tile(3221, 3219, 0)
    w.reachable = False
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clicks).to_equal([])
    expect(w.here.equals(SPOT)).to_be(True)


def event_interrupts(event_tick):
    w = Lumbridge().install()
    w.energy = 60

    def advance():
        if w.tick == event_tick:
            w.pending = True

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.tick).to_be(event_tick)
    expect(w.set_runs).to_be(0)
    expect(w.clicks).to_equal([])
    expect(w.clue).to_be(2681)


def run_refused():
    w = Lumbridge().install()
    w.energy = 60
    w.run_turns_on = False
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clicks).to_equal([])
    expect(w.clue).to_be(2681)


def walks_away():
    w = Lumbridge().install()
    w.hans = Tile(3221, 3219, 0)

    def advance():
        if w.tick == 1:
            w.here = Tile(3221, 3219, 0)
            w.hans = Tile(3219, 3225, 0)

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clicks).to_have_length(1)
    expect(any([t.equals(SPOT) for t in w.direct_walks])).to_be(True)
    expect(w.here.equals(SPOT)).to_be(True)
    expect(w.clue).to_be(2681)


def event_in_chase():
    w = Lumbridge().install()
    w.energy = 60

    def advance():
        if w.clicked_at is not None:
            w.pending = True

    w.advance = advance
    expect(solve(ClueExecutor())).to_be('yield')
    expect(w.clicks).to_have_length(1)
    expect(w.direct_walks).to_equal([])
    expect(w.clue).to_be(2681)


describe('Hans', lambda: [
    test('Hans clue 2681 waits for a late patrol and dialogue after 25 ticks', lambda: late_patrol(2681, 25)),
    test('Hans clue 2681 waits for a late patrol and dialogue after 30 ticks', lambda: late_patrol(2681, 30)),
    test('Hans clue 2792 waits for a late patrol and dialogue after 25 ticks', lambda: late_patrol(2792, 25)),
    test('Hans clue 2792 waits for a late patrol and dialogue after 30 ticks', lambda: late_patrol(2792, 30)),
    test('low energy waits without chasing or spending the clue reset', low_energy),
    test('repeated adjacent dialogue failures share one patrol wait budget', shared_budget),
    test('high energy allows a bounded chase after waiting and enables run first', bounded_chase),
    test('an unsuccessful chase returns to the wait spot after energy runs low', lambda: failed_chase('energy')),
    test('an unsuccessful chase returns to the wait spot after a timeout', lambda: failed_chase('timeout')),
    test('an unsuccessful chase returns to the wait spot after losing him', lambda: failed_chase('lost')),
    test('a nearby Hans behind an obstacle is not clicked from the waiting spot', behind_obstacle),
    test('a runtime event at tick 30 interrupts the wait without chasing or abandoning', lambda: event_interrupts(30)),
    test('a runtime event at tick 200 interrupts the wait without chasing or abandoning', lambda: event_interrupts(200)),
    test('failing to enable run does not start a chase', run_refused),
    test('a nearby Hans walking away cancels the approach and resumes waiting at low energy', walks_away),
    test('a runtime event during a chase prevents return movement from competing with it', event_in_chase),
])

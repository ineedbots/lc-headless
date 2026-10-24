"""rs2b0t's test/api/ai/clues: ClueExecutor.test.ts and riddleKey.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's
describe, test and expect, with the client's facades patched for a fake world as rs2b0t stubs them.

rs2b0t's ClueExecutor is one module-wide object; here each test makes its own, as each SolveClue does, so the test
of a fresh solver after a stopped one makes a new executor."""

from rs2004 import execution
from rs2004.clues.data import CLUE_DB, KILL_ANCHORS
from rs2004.clues.executor import ClueExecutor

CHALLENGE_CLUE = 2853
ANSWER = 5096
RIDDLE_CLUE = 2831
KEY_ID = CLUE_DB[RIDDLE_CLUE]['key_from']['key_id']
NPC_NAME = CLUE_DB[RIDDLE_CLUE]['key_from']['npc']
ANCHOR = KILL_ANCHORS[RIDDLE_CLUE]
FOOD_ID = 379
SHARK = 385
RUNE = 561
NEXT_SCROLL = 2722
HERE = Tile(2394, 3488, 0)
REFUSAL = "I'm already under attack!"


def name_of(id):
    names = {1893: '2/3 cake', 379: 'Lobster', 380: 'Lobster', SHARK: 'Shark', RUNE: 'Nature rune', NEXT_SCROLL: 'Clue scroll', 3549: 'Casket', 2714: 'Casket'}
    return names.get(id, 'Loot')


class World:
    """The fake client a test drives the executor through."""

    def __init__(self, here=None):
        self.inv = []
        self.names = []
        self.count_dialog = False
        self.pages = []
        self.answered = []
        self.continues = 0
        self.walks = []
        self.npcs = []
        self.ground = []
        self.locs = []
        self.messages = []
        self.in_combat = False
        self.pending = False
        self.ticks = 0
        self.on_tick = None
        self.on_walk = None
        self.here = here if here is not None else HERE
        self.stackable = {}
        self.full_at = 28
        self.used_fn = None

    def install(self):
        world = self
        spy_on(reader, 'count_dialog_open', lambda: world.count_dialog)
        spy_on(reader, 'main_modal', lambda: -1)
        spy_on(reader, 'item_type', lambda id: Fake(stackable=world.stackable[id]) if id in world.stackable else None)
        spy_on(chat_dialog, 'is_open', lambda: len(world.pages) > 0)
        spy_on(chat_dialog, 'can_continue', lambda: len(world.pages) > 0)
        spy_on(chat_dialog, 'continue_', lambda: world.on_page() if world.on_page is not None else world.next_page())
        spy_on(chat_dialog, 'options', lambda: [])
        spy_on(chat_dialog, 'answer_count', lambda n: world.answer(n))
        spy_on(modals, 'close', lambda: instant_until(lambda: True))
        patch(execution, 'delay_until', instant_until)
        patch(execution, 'delay_until_ticks', instant_until_ticks)
        patch(execution, 'delay_ticks', lambda n=1: world.tick(n))
        spy_on(game, 'in_combat', lambda: world.in_combat)
        spy_on(game, 'tile', lambda: world.here)
        spy_on(event_signal, 'pending', lambda: world.pending)
        spy_on(traversal, 'walk_resilient', lambda dest, **opts: world.walk(dest))
        stub(traversal, last_missing_gate_items=[])
        spy_on(npcs, 'query', querying(lambda: world.npcs))
        spy_on(locs, 'query', querying(lambda: world.locs))
        spy_on(ground_items, 'query', querying(lambda: [g for g in world.ground if not g.taken]))
        spy_on(game_messages, 'mark', lambda: len(world.messages))
        spy_on(game_messages, 'saw_since', lambda mark, pattern: any([pattern.lower() in m.lower() for m in world.messages[mark:]]))
        spy_on(game_messages, 'since', lambda mark: [Fake(text=m) for m in world.messages[mark:]])
        spy_on(inventory, 'items', lambda: [world.item(id) for id in world.inv])
        spy_on(inventory, 'first', lambda name: Fake(id=0, count=1, interact=lambda op: True) if name.lower() in [n.lower() for n in world.names] else None)
        spy_on(inventory, 'is_full', lambda: world.used() >= world.full_at)
        spy_on(inventory, 'used', lambda: world.used())
        spy_on(inventory, 'free', lambda: 28 - world.used())
        spy_on(inventory, 'count', lambda name: len([id for id in world.inv if name_of(id) == name]))
        spy_on(inventory, 'count_by_id', lambda id: len([i for i in world.inv if i == id]))
        return self

    def used(self):
        return self.used_fn() if self.used_fn is not None else len(self.inv)

    def tick(self, n=1):
        self.ticks += n
        if self.on_tick is not None:
            self.on_tick()
        return None
        yield

    def walk(self, dest):
        self.walks.append(f'walk {dest.x},{dest.z}')
        if self.on_walk is not None:
            self.on_walk()
        return True
        yield

    def next_page(self):
        self.continues += 1
        page = self.pages.pop(0) if self.pages else None
        if page == 'well-done':
            self.inv = [id for id in self.inv if id != CHALLENGE_CLUE]
            self.pages.append('found-clue')
        return True
        yield

    def answer(self, n):
        self.answered.append(n)
        self.count_dialog = False
        self.pages.append('well-done')
        return True

    def item(self, id):
        world = self

        def interact(op):
            if op == 'Open':
                world.inv.remove(id)
                if world.on_open is not None:
                    world.on_open()
            if op == 'Drop':
                world.inv.remove(id)
                world.dropped += 1
                world.ground.append(world.ground_item(id, name_of(id)))
            return True

        food = id in [FOOD_ID, 380, SHARK, 1893]
        return Fake(id=id, count=1, name=name_of(id), noted=id == 380, actions=lambda: ['Eat'] if food else [], interact=interact)

    def ground_item(self, id, name, tile=None, interact=None):
        world = self
        g = Fake(id=id, name=name, count=1, taken=False, tile=lambda: tile or world.reward_tile, distance=lambda: 0, actions=lambda: ['Take'])

        def take(op):
            if not world.take_allowed:
                return False
            g._fields['taken'] = True
            world.inv.append(id)
            return True

        g._fields['interact'] = interact or take
        return g

    reward_tile = HERE
    take_allowed = True
    dropped = 0
    on_open = None
    on_page = None


def solve(executor, log=None):
    return run_wait(executor.solve_held_clue(log or (lambda m: None)))


# Challenge replies


def challenge():
    world = World().install()
    world.inv = [CHALLENGE_CLUE]
    world.count_dialog = True
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.answered).to_equal([ANSWER])
    expect(world.continues).to_be_greater_than_or_equal(2)
    expect(world.walks).to_equal([])


describe('challenge reply handling', lambda: [
    test('answers the count dialog, continues the reply, and never pathfinds', challenge),
])


# Tools before abandoning


def spade_first():
    world = World().install()
    dig = [id for id, r in CLUE_DB.items() if r['type'] == 'dig' and r.get('needs_sextant') != True][0]
    world.inv = [dig]
    expect(solve(ClueExecutor())).to_be('abandon')
    expect(world.walks).to_contain('walk 2574,3331')


def rope_missing():
    world = World().install()
    world.inv = [2811]
    world.names = ['Spade', 'Sextant', 'Watch', 'Chart']
    lines = []
    expect(solve(ClueExecutor(), lambda m: lines.append(m))).to_be('abandon')
    expect(any(['Rope' in l for l in lines])).to_be(True)
    expect(world.walks).not_.to_contain('walk 2512,3467')


def rope_held():
    world = World().install()
    world.inv = [2811]
    world.names = ['Spade', 'Sextant', 'Watch', 'Chart', 'Rope']
    solve(ClueExecutor())
    expect(world.walks).to_contain('walk 2512,3467')


describe('tool acquisition before abandon', lambda: [
    test('a spade-less dig walks to a spade spawn before abandoning', spade_first),
])

describe('per-clue required items (2811 Baxtorian Falls rope)', lambda: [
    test('rope missing: the dig is blocked and abandoned, never walked', rope_missing),
    test('rope held: the dig proceeds to the falls ledge', rope_held),
])


# Caskets


def casket_world(casket=3549, inv=None):
    world = World().install()
    world.inv = [casket] + (inv or [])
    world.dropped = 0
    world.take_allowed = True
    world.reward_tile = HERE
    return world


def spill(world, *drops):
    for id, name in drops:
        world.ground.append(world.ground_item(id, name))


def next_scroll():
    world = casket_world(3549, [SHARK, SHARK])

    def opened():
        world.inv.append(NEXT_SCROLL)
        world.pending = True

    world.on_open = opened
    expect(solve(ClueExecutor())).to_be('yield')
    expect(world.inv).to_contain(NEXT_SCROLL)
    expect(world.dropped).to_be(0)
    expect(world.walks).to_equal([])


def last_casket():
    world = casket_world(3549, [SHARK] * 27)

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'), (1615, 'Uncut dragonstone'))

    world.on_open = opened
    log = []
    expect(solve(ClueExecutor(), lambda m: log.append(m))).to_be('done')
    expect(all([g.taken for g in world.ground if g.id != SHARK])).to_be(True)
    expect(any([g.taken for g in world.ground if g.id == SHARK])).to_be(False)
    expect(world.dropped).to_be(2)
    expect(world.inv).to_contain(995)
    expect(world.inv).to_contain(1615)
    expect(world.walks).to_equal([])
    expect(any(["took 'Coins'" in m for m in log])).to_be(True)


def full_without_food():
    world = casket_world(3549, [RUNE] * 27)

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'))

    world.on_open = opened
    executor = ClueExecutor()
    log = []
    expect(solve(executor, lambda m: log.append(m))).to_be('yield')
    expect(world.ground[0].taken).to_be(False)
    expect(any(["WARNING: 'Coins' is left on the ground" in m for m in log])).to_be(True)
    world.inv.pop()
    expect(solve(executor)).to_be('done')
    expect(world.ground[0].taken).to_be(True)


def drops_food(food):
    world = casket_world(3549, [food] * 27)

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'), (1615, 'Uncut dragonstone'))

    world.on_open = opened
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.inv).to_contain(1615)
    expect(world.dropped).to_be(2)
    expect(all([not g.taken for g in world.ground if g.id == food])).to_be(True)


def queued_rewards():
    world = casket_world(3549, [FOOD_ID] * 27)
    world.on_open = lambda: world.inv.append(RUNE)

    def on_tick():
        if world.ticks >= 2 and len(world.ground) == 0:
            spill(world, (995, 'Coins'))

    world.on_tick = on_tick
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.dropped).to_be(1)


def easy_spill():
    world = casket_world(2714, [FOOD_ID] * 27)

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'))

    world.on_open = opened
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.dropped).to_be(1)
    expect([g.taken for g in world.ground if g.id == FOOD_ID]).to_equal([False])


def failed_pickup():
    world = casket_world(3549, [FOOD_ID] * 27)
    world.take_allowed = False

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'))

    world.on_open = opened
    executor = ClueExecutor()
    expect(solve(executor)).to_be('yield')
    expect(world.inv).not_.to_contain(995)
    expect(world.dropped).to_be(1)
    world.take_allowed = True
    expect(solve(executor)).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.dropped).to_be(1)
    expect([g.taken for g in world.ground if g.id == FOOD_ID]).to_equal([False])


def noted_food():
    world = casket_world(3549, [380] + [FOOD_ID] * 26)

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'))

    world.on_open = opened
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.inv).to_contain(380)
    expect(any([g.id == 380 for g in world.ground])).to_be(False)
    expect([g.taken for g in world.ground if g.id == FOOD_ID]).to_equal([False])


def fresh_solver():
    world = casket_world(3549, [FOOD_ID] * 27)
    world.take_allowed = False

    def opened():
        world.inv.append(RUNE)
        spill(world, (995, 'Coins'))

    world.on_open = opened
    expect(solve(ClueExecutor())).to_be('yield')
    world.reward_tile = Tile(3000, 3200, 0)
    world.here = world.reward_tile
    world.inv = [3549]
    world.ground = []
    world.take_allowed = True
    world.on_open = lambda: spill(world, (995, 'Coins'))
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.ground[0].taken).to_be(True)


def existing_stack():
    world = casket_world(3549, [RUNE])
    world.on_open = lambda: spill(world, (RUNE, 'Nature rune'))
    world.used_fn = lambda: len(set(world.inv))
    expect(solve(ClueExecutor())).to_be('done')
    expect([i for i in world.inv if i == RUNE]).to_have_length(2)
    expect(world.ground[0].taken).to_be(True)
    expect(world.dropped).to_be(0)


def stackable_full(stackable):
    world = casket_world(3549, [RUNE] + [6000 + i for i in range(26)])

    def opened():
        world.inv.append(6500)
        spill(world, (RUNE, 'Nature rune'))

    world.on_open = opened
    world.stackable = {RUNE: stackable}
    world.used_fn = lambda: len(set(world.inv))
    expect(solve(ClueExecutor())).to_be('done' if stackable else 'yield')
    expect(world.ground[0].taken).to_be(stackable)
    expect([i for i in world.inv if i == RUNE]).to_have_length(2 if stackable else 1)
    expect(world.dropped).to_be(0)


def talk_reward():
    world = casket_world(CHALLENGE_CLUE, [FOOD_ID] * 27)
    world.count_dialog = True

    def page_on():
        if world.pages and world.pages.pop(0) == 'well-done':
            world.inv = [id for id in world.inv if id != CHALLENGE_CLUE]
            world.inv.append(RUNE)
            spill(world, (995, 'Coins'))
        return True
        yield

    world.on_page = page_on
    expect(solve(ClueExecutor())).to_be('done')
    expect(world.inv).to_contain(995)
    expect(world.dropped).to_be(1)


describe('opening a casket', lambda: [
    test('a casket that hands back a scroll is the next leg, not a reward', next_scroll),
    test('the last casket is opened in place, Sharks make room and the spill comes off our tile', last_casket),
    test('a full pack without food keeps the reward pending until room is available', full_without_food),
    test('hard rewards drop ordinary food and never pick it back up', lambda: drops_food(FOOD_ID)),
    test('hard rewards drop partial food and never pick it back up', lambda: drops_food(1893)),
    test('waits for queued rewards to reach the ground after the casket disappears', queued_rewards),
    test('easy reward spill makes room from ordinary food without picking it back up', easy_spill),
    test('retries a failed pickup without collecting food dropped during the first attempt', failed_pickup),
    test('preserves noted food rewards when dropping edible food to make room', noted_food),
    test('a fresh solver collects its rewards instead of reusing a stopped solver pickup tile', fresh_solver),
    test('confirms a reward added to an existing stack without requiring another used slot', existing_stack),
    test('a full pack accepts an existing reward id when it stacks', lambda: stackable_full(True)),
    test('a full pack refuses an existing reward id that does not stack', lambda: stackable_full(False)),
    test('collects rewards granted directly by a final talk challenge', talk_reward),
])


# The riddle key hunt (riddleKey.test.ts)


def heather(world, busy=False):
    e = Fake(id=202, name=NPC_NAME, tile=lambda: ANCHOR, distance=lambda: 1, actions=lambda: ['Talk-to', 'Attack'], targets_me=lambda: False,
             busy=busy)
    e._fields['targets_another_player'] = lambda: e._fields['busy']

    def interact(op):
        if op != 'Attack':
            return True
        world.attacks += 1
        if world.refusals_left > 0:
            world.refusals_left -= 1
            world.messages.append(REFUSAL)
            return True
        world.npcs = [n for n in world.npcs if n is not e]
        world.in_combat = False
        world.ground.append(world.ground_item(KEY_ID, 'Key', ANCHOR))
        return True

    e._fields['interact'] = interact
    return e


def riddle_world():
    world = World(ANCHOR).install()
    world.inv = [RIDDLE_CLUE]
    world.names = ['Spade', 'Sextant', 'Watch', 'Chart', 'Rope']
    world.attacks = 0
    world.refusals_left = 0
    world.npcs = [heather(world)]
    return world


def held_key(world):
    return KEY_ID in world.inv


def refused_resent():
    world = riddle_world()
    world.refusals_left = 6
    solve(ClueExecutor())
    expect(world.attacks).to_be_greater_than_or_equal(7)
    expect(held_key(world)).to_be(True)


def landed_once():
    world = riddle_world()
    solve(ClueExecutor())
    expect(world.attacks).to_be(1)
    expect(held_key(world)).to_be(True)


def respawn_wait():
    world = riddle_world()
    world.npcs = []

    def on_tick():
        if world.ticks >= 3 and len(world.npcs) == 0 and KEY_ID not in world.inv:
            world.npcs = [heather(world)]

    world.on_tick = on_tick
    lines = []
    solve(ClueExecutor(), lambda m: lines.append(m))
    expect(any(['respawn' in l for l in lines])).to_be(True)
    expect(held_key(world)).to_be(True)


def busy_target():
    world = riddle_world()
    busy = heather(world, True)
    world.npcs = [busy]
    attacks_while_busy = []

    def on_tick():
        attacks_while_busy.append(world.attacks)
        if world.ticks >= 3:
            busy._fields['busy'] = False

    world.on_tick = on_tick
    solve(ClueExecutor())
    expect(attacks_while_busy[0:3]).to_equal([0, 0, 0])
    expect(held_key(world)).to_be(True)


def eating_is_not_progress():
    world = riddle_world()
    # 2811 digs at Baxtorian Falls, which nothing here can solve, so the only movement in the pack is a bite.
    world.inv = [2811, FOOD_ID]
    world.npcs = []

    def ate():
        world.inv = [id for id in world.inv if id != FOOD_ID]

    world.on_walk = ate
    lines = []
    executor = ClueExecutor()
    expect(solve(executor, lambda m: lines.append(m))).to_be('reset-needed')
    expect(solve(executor, lambda m: lines.append(m))).to_be('abandon')
    expect(any(['no progress after' in l for l in lines])).to_be(True)
    expect(any([l == 'step done' for l in lines])).to_be(False)


describe('riddle key hunt', lambda: [
    # Why: more refusals than the executor has step attempts, so the retry has to live inside the hunt.
    test('a refused attack is sent again within the same attempt', refused_resent),
    test('an attack that lands is not sent again', landed_once),
    test('an absent target is waited out rather than abandoning the riddle', respawn_wait),
    test('a target another player is fighting is left alone until it is free', busy_target),
])

describe('step progress', lambda: [
    test('eating mid-leg is not mistaken for solving the step', eating_is_not_progress),
])

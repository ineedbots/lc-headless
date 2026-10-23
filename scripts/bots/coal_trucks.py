# Mines coal at the Coal Trucks west of Seers' Village, fills the trucks with 120 of it, then empties them into
# the Seers bank: rs2b0t's CoalTrucks (MIT, see thirdparty/rs2b0t). It needs Mining 30 and a pickaxe, and has no
# combat handling: the level-27 giant bats here attack below combat 55.

from rs2004.catalogs import GAS_ROCK_IDS, best_pickaxe

COAL = 'Coal'
TRUCK_LOC = 'Coal Truck'
REMOVE_OP = 'Remove-coal'
ROCK_LOC = 'Rocks'
MINE_OP = 'Mine'
TRUCK_MAX = 120
COAL_MINING_LEVEL = 30
COAL_ROCK_IDS = [2096, 2097]
# The truck line runs east across the river; the trucks on the far bank are a long detour.
TRUCK_LEASH = 4
# How far from the anchor counts as the working area: the rocks, the truck stand and some walking slop.
MINE_AREA = 20
# Why: four pulls bank 135 coal over 720 tiles; a fifth adds only 12 coal and 102 tiles.
MAX_PULLS_PER_HAUL = 4
MINE_ANCHOR = Tile(2582, 3481, 0)
MINE_TRUCK = Tile(2574, 3487, 0)
MINE_TRUCK_STAND = Tile(2575, 3486, 0)
SEERS_TRUCK = Tile(2696, 3504, 0)
SEERS_TRUCK_STAND = Tile(2695, 3503, 0)
SEERS_BANK = Tile(2725, 3491, 0)
# A click to a swing; the server starts the animation within a tick or two.
MINE_START_MS = 3000
# A backstop for a swing that neither yields nor ends.
MINE_STALL_MS = 20000
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
MESSAGE_WAIT_MS = 5000
RESPAWN_WAIT_TICKS = 5
ROCK_LEASH = 12
MAX_BANK_FAILS = 6

DEPOSIT_PATTERNS = [
    ('you put some of the coal in the truck', 'partial', True),
    ('you put the coal in the truck', 'all', True),
    ('the coal truck is full', 'full', True),
    ("isn't meant to transport", 'wrong-item', False),
]
REMOVE_PATTERNS = [
    ('you remove some of the coal from the truck', 'partial', True),
    ('you remove the coal from the truck', 'all', True),
    ('there is no coal left in the truck', 'empty', True),
    ('enough inventory space', 'no-space', False),
]


class MineView:
    """interrupted is a random event pending or a dialogue open: either way, mining stops and gives way."""

    def __init__(self, gained, pack_full, animating, interrupted):
        self.gained = gained
        self.pack_full = pack_full
        self.animating = animating
        self.interrupted = interrupted


def mine_wait_done(stage, view):
    """Two stages, 'start' and 'sustain', since the swing hasn't begun on the tick the wait starts."""
    if view.gained or view.pack_full or view.interrupted:
        return True
    return view.animating if stage == 'start' else not view.animating


def _classify(lines, patterns):
    for line in lines:
        text = line.strip().lower()
        for pattern, result, at_start in patterns:
            if (at_start and text.startswith(pattern)) or (not at_start and pattern in text):
                return result
    return 'none'


def classify_deposit(lines):
    """'all', 'partial', 'full', 'wrong-item' or 'none'."""
    return _classify(lines, DEPOSIT_PATTERNS)


def classify_remove(lines):
    """'all', 'partial', 'empty', 'no-space' or 'none'."""
    return _classify(lines, REMOVE_PATTERNS)


def truck_full_after_deposit(result):
    return result == 'partial' or result == 'full'


def truck_empty_after_remove(result):
    return result == 'all' or result == 'empty'


class WorldView:
    def __init__(self, phase, pack_full, coal_held, rock_available, truck_empty, truck_full, pulls_this_haul, has_pickaxe, at_mine):
        self.phase = phase
        self.pack_full = pack_full
        self.coal_held = coal_held
        self.rock_available = rock_available
        self.truck_empty = truck_empty
        self.truck_full = truck_full
        self.pulls_this_haul = pulls_this_haul
        self.has_pickaxe = has_pickaxe
        self.at_mine = at_mine


def decide(view):
    """The next action: 'mine', 'await-rocks', 'deposit', 'travel-to-seers', 'remove', 'bank' or
    'travel-to-mine'."""
    # A missing pickaxe fails silently, so it banks for one before anything else.
    if not view.has_pickaxe:
        return 'bank'
    # Why: when the truck starts capped, carried coal is banked directly rather than doubling back.
    if view.phase == 'run':
        return 'bank' if view.coal_held > 0 else 'travel-to-seers'
    if view.phase == 'drain':
        if view.coal_held > 0:
            return 'bank'
        spent = view.truck_empty or view.pulls_this_haul >= MAX_PULLS_PER_HAUL
        return 'travel-to-mine' if spent else 'remove'
    # Tops the pack up before a capped truck's haul; the bank's hops cost the same either way.
    if view.truck_full:
        if view.at_mine and not view.pack_full and view.rock_available:
            return 'mine'
        # Carried coal can't go in a capped truck, so it goes straight to the bank.
        return 'bank' if view.coal_held > 0 else 'travel-to-seers'
    if not view.at_mine:
        return 'travel-to-mine'
    if view.pack_full:
        return 'deposit'
    return 'mine' if view.rock_available else 'await-rocks'


class CoalTrucks(LoopingBot):
    loop_delay = 0

    def on_start(self):
        self.phase = 'fill'
        self.truck_empty = False
        self.truck_full = False
        self.pulls_this_haul = 0
        self.deposited_estimate = 0
        self.banked = 0
        self.trips = 0
        self.bank_fails = 0
        self.status = 'starting'
        self.xp_start = skills.xp('mining')
        level = skills.level('mining')
        if level < COAL_MINING_LEVEL:
            self.log(f'CoalTrucks: Mining {COAL_MINING_LEVEL} required to mine coal (have {level}). Stopping.')
            raise ValueError('CoalTrucks: Mining level too low')
        self.log(f'CoalTrucks; mine {MINE_ANCHOR}, truck {MINE_TRUCK}, Seers truck {SEERS_TRUCK}, bank {SEERS_BANK}')
        self.log('no combat handling: the level-27 giant bats here are aggressive below 55 combat')
        if not self.has_pickaxe():
            self.log('no pickaxe held; banking at Seers for one before mining')

    def grind_targets(self):
        return [ROCK_LOC]

    def recovery_anchor(self):
        return MINE_ANCHOR

    def loop(self):
        was_draining = self.phase == 'drain'
        action = decide(WorldView(self.phase, inventory.is_full(), inventory.count(COAL), self.find_rock() is not None, self.truck_empty,
                                  self.truck_full, self.pulls_this_haul, self.has_pickaxe(), self.at_mine()))
        if action == 'mine':
            yield from self.mine()
        elif action == 'await-rocks':
            self.status = 'waiting for a coal respawn'
            yield from execution.delay_ticks(RESPAWN_WAIT_TICKS)
        elif action == 'deposit':
            yield from self.deposit()
        elif action == 'travel-to-seers':
            self.status = 'heading to the Seers truck'
            self.phase = 'run'
            if not self.at(SEERS_TRUCK_STAND, 1):
                self.log('walking to the Seers truck to unload')
            arrived = yield from self.walk_to(SEERS_TRUCK_STAND, 1)
            if arrived:
                self.phase = 'drain'
                self.truck_empty = False
                self.pulls_this_haul = 0
        elif action == 'remove':
            yield from self.remove()
        elif action == 'bank':
            yield from self.bank()
        elif action == 'travel-to-mine':
            self.status = 'walking back to the mine'
            arrived = yield from self.walk_to(MINE_ANCHOR, 4)
            if arrived:
                self.phase = 'fill'
                self.truck_empty = False
                self.truck_full = False
                # Only a finished drain closes a cycle: a pickaxe detour mid-fill mustn't zero a truck that's
                # partly loaded.
                if was_draining:
                    self.deposited_estimate = 0
                    self.trips += 1
        yield from execution.delay_ticks(1)

    def held_pickaxe(self):
        """The one pickaxe worth keeping; a spare, or a tier you can't use, is banked."""
        held = [(i.name or '').lower() for i in equipment.items() + inventory.items()]
        return best_pickaxe(skills.level('mining'), lambda name: name.lower() in held)

    def has_pickaxe(self):
        return self.held_pickaxe() is not None

    def at_mine(self):
        here = game.tile()
        return here is not None and MINE_ANCHOR.distance_to(here) <= MINE_AREA

    def find_rock(self):
        return locs.query().name(ROCK_LOC).action(MINE_OP).where(lambda l: l.id in COAL_ROCK_IDS and l.id not in GAS_ROCK_IDS).where(lambda l: l.tile().distance_to(MINE_ANCHOR) <= ROCK_LEASH).nearest()

    def truck_at(self, expected):
        return locs.query().name(TRUCK_LOC).where(lambda l: l.tile().distance_to(expected) <= TRUCK_LEASH).nearest()

    def mine(self):
        rock = self.find_rock()
        if rock is None:
            yield from execution.delay_ticks(2)
            return
        self.status = 'mining coal'
        before = inventory.count(COAL)
        if not rock.interact(MINE_OP):
            yield from execution.delay_ticks(2)
            return

        # Why: a rock gives one coal and depletes, so this returns on the gain and lets the next loop pick a live
        # rock; waiting a spent rock out costs the 20 s. A swing that stops is the other way out, as when the rock
        # is taken first.
        def view():
            return MineView(inventory.count(COAL) > before, inventory.is_full(), game.animating(), event_signal.pending() or chat_dialog.can_continue())

        yield from execution.delay_until(lambda: mine_wait_done('start', view()), MINE_START_MS)
        yield from execution.delay_until(lambda: mine_wait_done('sustain', view()), MINE_STALL_MS)

    def await_message(self, mark, classify):
        found = {'result': 'none'}

        def seen():
            found['result'] = classify([m.text for m in game_messages.since(mark)])
            return found['result'] != 'none'

        yield from execution.delay_until(seen, MESSAGE_WAIT_MS)
        return found['result']

    def deposit(self):
        self.status = 'loading the truck'
        arrived = yield from self.walk_to(MINE_TRUCK_STAND, 1)
        if not arrived:
            return
        truck = self.truck_at(MINE_TRUCK)
        coal = inventory.first(COAL)
        if truck is None or coal is None:
            yield from execution.delay_ticks(2)
            return
        held = inventory.count(COAL)
        mark = game_messages.mark()
        if not coal.use_on(truck):
            yield from execution.delay_ticks(2)
            return
        result = yield from self.await_message(mark, classify_deposit)
        if result == 'none':
            self.log('deposit produced no message; retrying')
            return
        if result == 'wrong-item':
            self.status = 'wrong item used; stopped'
            self.request_finish('CoalTrucks: the truck refused the item we used on it')
            return
        # The message can beat the pack by a tick, so it waits for the coal to go; 'full' moves none.
        if result == 'all' or result == 'partial':
            yield from execution.delay_until(lambda: inventory.count(COAL) < held, 2000)
        moved = held - inventory.count(COAL)
        self.deposited_estimate = min(TRUCK_MAX, self.deposited_estimate + moved)
        self.truck_full = truck_full_after_deposit(result)
        capped = '; capped, topping the pack up before the run' if self.truck_full else ''
        self.log(f'put {moved} coal in the truck ({result}){capped}')

    def remove(self):
        self.status = 'unloading the truck'
        arrived = yield from self.walk_to(SEERS_TRUCK_STAND, 1)
        if not arrived:
            return
        truck = self.truck_at(SEERS_TRUCK)
        if truck is None:
            yield from execution.delay_ticks(2)
            return
        before = inventory.count(COAL)
        mark = game_messages.mark()
        if not truck.interact(REMOVE_OP):
            yield from execution.delay_ticks(2)
            return
        result = yield from self.await_message(mark, classify_remove)
        if result == 'none':
            self.log('Remove-coal produced no message; retrying')
            return
        if result == 'no-space':
            return
        # The message can beat the pack by a tick, so it settles before counting.
        yield from execution.delay_until(lambda: inventory.count(COAL) > before, 2000)
        self.pulls_this_haul += 1
        self.truck_empty = truck_empty_after_remove(result)
        spent = not self.truck_empty and self.pulls_this_haul >= MAX_PULLS_PER_HAUL
        note = '; pull budget spent, the remainder rides to the next cycle' if spent else ''
        self.log(f'took {inventory.count(COAL) - before} coal from the truck ({result}){note}')

    def bank(self):
        self.status = 'banking the coal'
        arrived = yield from self.walk_to(SEERS_BANK, 4)
        if not arrived:
            return
        opened = yield from bank.open_booth(SEERS_BANK, BOOTH_NAME, BOOTH_OP)
        if not opened:
            self.bank_fails += 1
            if self.bank_fails >= MAX_BANK_FAILS:
                self.status = 'cannot reach the bank; stopped'
                self.request_finish('CoalTrucks: could not open the Seers bank')
                return
            self.log('could not open the bank; will retry')
            return
        self.bank_fails = 0
        held = inventory.count(COAL)
        # Why: random events leave coins and junk the truck won't take, and anything kept takes a coal slot
        # every load, so only the pickaxe in use stays.
        keep = self.held_pickaxe()
        yield from bank.deposit_all_matching(deposit_all_except([keep] if keep else []))
        yield from execution.delay_ticks(1)
        moved = held - inventory.count(COAL)
        self.banked += moved
        if moved > 0:
            self.log(f'banked {moved} coal ({self.banked} this run)')
        yield from self.ensure_pickaxe()
        yield from bank.close()

    def ensure_pickaxe(self):
        if self.has_pickaxe():
            return
        from_bank = best_pickaxe(skills.level('mining'), lambda name: bank.count(name) > 0)
        if from_bank is None:
            self.status = 'no pickaxe; stopped'
            self.request_finish('CoalTrucks: no usable pickaxe held or banked')
            return
        if bank.withdraw(from_bank):
            self.log(f'withdrew a {from_bank}')
        yield from execution.delay_until(lambda: self.has_pickaxe(), 3000)

    def at(self, dest, radius):
        here = game.tile()
        return here is not None and dest.distance_to(here) <= radius

    def walk_to(self, dest, radius):
        if self.at(dest, radius):
            return True
        arrived = yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=300000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def on_progress_report(self):
        return {'Status': self.status, 'Mining': skills.level('mining'), 'Mining xp': skills.xp('mining') - self.xp_start, 'Phase': self.phase,
                'Banked': self.banked, 'Trips': self.trips, 'Pack': inventory.count(COAL), 'Truck (est)': f'{self.deposited_estimate}/{TRUCK_MAX}'}


BOT = define_bot(
    name='CoalTrucks',
    create=CoalTrucks,
    description='Mines coal at the Coal Trucks, buffers 120 in the trucks, then drains them into the Seers bank — needs Mining 30 and a pickaxe. No combat handling: the level-27 giant bats are aggressive below 55 combat.',
    category='Mining',
    tags=['mining', 'coal', 'seers', 'banking'],
)

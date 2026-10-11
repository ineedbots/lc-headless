# Trains Thieving from level 1, by level: men and women in Lumbridge to 5, then East Ardougne's Baker's stall to
# 40, banking each full backpack of cakes, then the market guards to 55 and its knights after that, eating the
# banked cakes. Built from rs2b0t's ThievingBot, ArdyCakes and ArdyThiever (MIT, see thirdparty/rs2b0t).
# Thieving needs a members' world.

from rs2004.catalogs import ContinueDialog, MIN_EAT_HP, food_heal_amount, should_eat_to_use_food

SETTINGS = {
    'food_target': SettingDef('number', 20, 'Cakes to carry', 1, 27, help='for guards and knights: how many to take from the bank'),
    'restock_at_food': SettingDef('number', 3, 'Restock cakes at', 0, 26, help='bank for more at this many, or steal them from the stall when the bank has none'),
    'rest_until_hp': SettingDef('number', 70, 'Rest to HP% without food', 10, 100),
    'stop_at_level': SettingDef('number', 99, 'Stop at Thieving level', 2, 99),
}

LUMBRIDGE = Tile(3221, 3219, 0)
MARKET = Tile(2661, 3306, 0)
ARDOUGNE_BANK_STAND = Tile(2655, 3286, 0)
# The stall is 2x2 from STALL_TILE, and these are rs2b0t's two stands beside it. A steal the baker sees gives
# nothing, and three of those in a row move to the other stand.
STALL_NAME = "Baker's stall"
STALL_OP = 'Steal from'
STALL_TILE = Tile(2667, 3310, 0)
STALL_STAND = Tile(2668, 3312, 0)
STALL_STAND_ALT = Tile(2669, 3310, 0)
NEAR_STALL = 2
# A market guard this close, in Chebyshev tiles to its south-west corner, who can see you attacks the thief.
STALL_GUARD = 'Guard'
GUARD_SIGHT = 5
GUARD_WAIT_MS = 6000
FLEE_TILE = Tile(2655, 3298, 0)
# Port Sarim to Karamja, and Brimhaven to Ardougne.
SHIP_FARES = 60
# East of here is Asgarnia and Misthalin, across White Wolf Mountain or the sea from Ardougne.
ARDOUGNE_EAST_X = 2880

# The server's lockout after combat: no stealing from a market stall for 10 ticks.
LOCKOUT_TICKS = 10
# A failed pickpocket stuns for 8 ticks; waiting 9 lets the next click path.
STUN_TICKS = 9
UNREACHABLE_SKIP_TICKS = 15
REFUSALS_BEFORE_SWAP = 3
STEAL_RESOLVE_MS = 2400
STALL_RESTOCK_WAIT_MS = 8000
STEAL_PASS_TICKS = 150
LEASH_SLACK = 6
LONG_WALK_TILES = 30

# Every food the stall gives. Eaten partial forms first, so slots free up; withdrawn whole cakes first.
FOOD_NAMES = ['cake', '2/3 cake', 'slice of cake', 'bread', 'chocolate slice']
EAT_ORDER = ['Slice of cake', '2/3 cake', 'Chocolate slice', 'Bread', 'Cake']
WITHDRAW_ORDER = ['Cake', '2/3 cake', 'Chocolate slice', 'Bread', 'Slice of cake']

COINS = 'Coins'
MEMBERS_ONLY = "members' world to gain experience in thieving"
STALL_LOCKOUT = "can't steal from the market stall during combat"
GRIND_TARGETS = ['man', 'woman', 'guard', 'knight of ardougne']


class Phase:
    """A way to train: from min_level, at anchor, within leash tiles of it. targets are the NPCs to pickpocket,
    or None for the stall."""

    def __init__(self, name, min_level, targets, anchor, leash, where):
        self.name = name
        self.min_level = min_level
        self.targets = targets
        self.anchor = anchor
        self.leash = leash
        self.where = where


PHASES = [
    Phase('men', 1, ['Man', 'Woman'], LUMBRIDGE, 18, 'Lumbridge'),
    Phase('cakes', 5, None, STALL_STAND, 40, "East Ardougne's Baker's stall"),
    Phase('guards', 40, ['Guard'], MARKET, 19, 'the East Ardougne market'),
    Phase('knights', 55, ['Knight of Ardougne'], MARKET, 29, 'the East Ardougne market'),
]


def phase_for(level):
    chosen = PHASES[0]
    for phase in PHASES:
        if level >= phase.min_level:
            chosen = phase
    return chosen


def is_food(name):
    return (name or '').lower() in FOOD_NAMES


class AioThiever(TaskBot):
    def on_start(self):
        self.steals = 0
        self.stuns = 0
        self.eats = 0
        self.banked = 0
        self.trips = 0
        self.flees = 0
        self.deaths = 0
        self.stunned_until = 0
        self.lockout_until = 0
        self.lockout_seen = False
        self.resting = False
        self.bank_out_of_food = False
        self.unreachable = {}
        self.xp_start = skills.xp('thieving')
        self.level_start = skills.level('thieving')
        self.last_phase = None
        log('thieving', self.level_start, '; starting with', self.phase().name, 'in', self.phase().where)
        self.add(
            ContinueDialog(),
            Task(self.done, self.finish, 'finish'),
            Task(lambda: self.in_ardougne_phase() and self.in_real_combat(), self.flee, 'flee'),
            Task(self.need_eat, self.eat, 'eat'),
            Task(self.far_from_post, self.travel, 'travel'),
            Task(lambda: self.phase().name == 'cakes' and inventory.is_full(), self.bank_haul, 'bank cakes'),
            Task(self.needs_bank, self.restock_from_bank, 'bank'),
            Task(self.must_rest, self.rest, 'rest'),
            Task(self.needs_stall_food, self.restock_from_stall, 'steal food'),
            Task(lambda: self.phase().name == 'cakes', self.steal_cakes_task, 'steal cakes'),
            Task(lambda: self.phase().targets is not None and self.find_target() is not None, self.pickpocket, 'pickpocket'),
            Task(lambda: self.phase().targets is not None, self.wait_for_target, 'wait'),
        )

    # Where and how to train.

    def phase(self):
        phase = phase_for(skills.level('thieving'))
        if self.last_phase is not None and phase.name != self.last_phase:
            log('thieving', skills.level('thieving'), ': moving on to', phase.name, 'in', phase.where)
        self.last_phase = phase.name
        return phase

    def in_ardougne_phase(self):
        return self.phase().name != 'men'

    def recovery_anchor(self):
        return self.phase().anchor

    def grind_targets(self):
        return GRIND_TARGETS

    def done(self):
        return skills.level('thieving') >= self.settings.stop_at_level

    def finish(self):
        self.request_finish(f'reached Thieving {skills.level("thieving")}')

    # Hooks.

    def on_server_message(self, msg):
        text = msg.lower()
        if 'fail to pick' in text or 'been stunned' in text:
            if game.tick() > self.stunned_until:
                self.stuns += 1
            self.stunned_until = game.tick() + STUN_TICKS
        elif STALL_LOCKOUT in text:
            self.lockout_seen = True
        elif MEMBERS_ONLY in text:
            self.request_finish('Thieving needs a members\' world')

    def on_death(self):
        self.deaths += 1
        self.bank_out_of_food = False
        log('died; walking back to', self.phase().where)

    # Health.

    def stunned(self):
        return game.tick() <= self.stunned_until

    def in_real_combat(self):
        """Fighting, not just hurt by a stun."""
        return game.in_combat() and not self.stunned()

    def food_count(self):
        return len([i for i in inventory.items() if is_food(i.name)])

    def next_food(self):
        for name in EAT_ORDER:
            item = inventory.first(name)
            if item is not None:
                return item
        return None

    def need_eat(self):
        food = self.next_food()
        if food is None:
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(food.name), self.food_count())

    def eat(self):
        food = self.next_food()
        if food is None:
            return
        before = skills.effective('hitpoints')
        if not food.interact('Eat'):
            yield from execution.delay_ticks(1)
            return
        ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
        if ate:
            self.eats += 1

    def must_rest(self):
        """Out of food and low: wait for hitpoints to come back to rest_until_hp."""
        if self.food_count() > 0:
            self.resting = False
            return False
        if skills.effective('hitpoints') <= MIN_EAT_HP:
            if not self.resting:
                log('resting at', skills.effective('hitpoints'), 'hp with no food')
            self.resting = True
        elif skills.hp_fraction() * 100 >= self.settings.rest_until_hp:
            self.resting = False
        return self.resting

    def rest(self):
        until = self.settings.rest_until_hp
        yield from execution.delay_until(lambda: skills.hp_fraction() * 100 >= until or game.in_combat() or chat_dialog.can_continue(), 60000)

    def hunted(self):
        """Something is still after you, though it may not be hitting you."""
        return npcs.query().action('Attack').where(lambda n: n.targets_me()).exists()

    def flee(self):
        log('a guard is on us; running to', FLEE_TILE)
        self.flees += 1
        yield from traversal.walk_to(FLEE_TILE, radius=0, timeout_ms=20000)
        # Going back while the guard is still after you only starts the fight again.
        yield from execution.delay_until(lambda: not game.in_combat() and not self.hunted(), 30000)
        self.lockout_until = game.tick() + LOCKOUT_TICKS

    # Getting there.

    def far_from_post(self):
        here = game.tile()
        phase = self.phase()
        return here is not None and phase.anchor.distance_to(here) > phase.leash + LEASH_SLACK

    def travel(self):
        phase = self.phase()
        here = game.tile()
        say = lambda m: log(' ', m)
        if phase.anchor.distance_to(here) <= LONG_WALK_TILES:
            yield from traversal.walk_to(phase.anchor, radius=3, timeout_ms=90000, log=say)
            return
        # From Lumbridge the walker takes the ships by Karamja, which beats the pass over White Wolf Mountain and
        # its wolves, when you have their fares.
        if phase.name != 'men' and here.x > ARDOUGNE_EAST_X and inventory.count(COINS) < SHIP_FARES:
            log('only', inventory.count(COINS), 'coins, short of the', SHIP_FARES, 'for the ships to Ardougne; walking over White Wolf Mountain')
        log('walking to', phase.where, 'at', phase.anchor)
        yield from traversal.walk_resilient(phase.anchor, radius=3, attempts=4, timeout_ms=600000, log=say)

    # Banking.

    def bank_haul(self):
        """The stall's phase: banks the whole backpack and goes back to the stall."""
        opened = yield from banking.open(ARDOUGNE_BANK_STAND)
        if not opened:
            log('could not open the bank; trying again')
            yield from execution.delay_ticks(3)
            return
        cakes = self.food_count()
        yield from bank.deposit_inventory()
        self.banked += max(0, cakes - self.food_count())
        self.trips += 1
        log('banked', cakes, 'stall food;', self.banked, 'in all')
        yield from bank.close()
        yield from traversal.walk_resilient(STALL_STAND, radius=1, attempts=4, timeout_ms=120000, log=lambda m: log(' ', m))

    def needs_bank(self):
        """Guards and knights: banks for cakes when low, and the loot when the backpack fills."""
        phase = self.phase()
        if phase.targets is None or not self.in_ardougne_phase() or self.in_real_combat():
            return False
        low = self.food_count() <= self.settings.restock_at_food and not self.bank_out_of_food
        # The coins go on their stack, so a full backpack only gets in the way when it has no coins yet, or holds
        # something else, such as a random event's gift.
        junk = [i for i in inventory.items() if not is_food(i.name) and i.name != COINS]
        clutter = inventory.is_full() and (len(junk) > 0 or inventory.count(COINS) == 0)
        return low or clutter

    def restock_from_bank(self):
        opened = yield from banking.open(ARDOUGNE_BANK_STAND)
        if not opened:
            log('could not open the bank; trying again')
            yield from execution.delay_ticks(3)
            return
        # Everything goes in and food_target cakes come out, leaving a slot for the coins.
        yield from bank.deposit_inventory()
        yield from bank.wait_ready()
        target = self.settings.food_target
        for name in WITHDRAW_ORDER:
            need = target - self.food_count()
            if need <= 0 or inventory.is_full():
                break
            if bank.count(name) > 0:
                yield from bank.withdraw_x(name, need)
        self.trips += 1
        self.bank_out_of_food = self.food_count() <= self.settings.restock_at_food
        if self.bank_out_of_food:
            log('the bank is out of cakes; stealing more from the stall')
        else:
            log('carrying', self.food_count(), 'cakes')
        yield from bank.close()
        if not self.bank_out_of_food:
            yield from traversal.walk_resilient(self.phase().anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: log(' ', m))

    # The Baker's stall.

    def needs_stall_food(self):
        phase = self.phase()
        if phase.targets is None or not self.in_ardougne_phase() or self.in_real_combat() or inventory.is_full():
            return False
        return self.bank_out_of_food and self.food_count() <= self.settings.restock_at_food

    def restock_from_stall(self):
        result = yield from self.steal_cakes(self.settings.food_target)
        if result == 'stocked':
            log('stole', self.food_count(), 'cakes to eat')

    def steal_cakes_task(self):
        result = yield from self.steal_cakes(None)
        if result == 'combat':
            log('a guard caught the steal')
        elif result == 'no-progress':
            log('a pass at the stall made no progress; starting over')

    def stocked_stall(self):
        return locs.query().name(STALL_NAME).action(STALL_OP).where(lambda l: l.tile().distance_to(STALL_TILE) <= 3).nearest()

    def lockout_over(self):
        return game.tick() >= self.lockout_until

    def guard_near(self, tile):
        return npcs.query().name(STALL_GUARD).where(lambda n: n.tile().distance_to(tile) <= GUARD_SIGHT).exists()

    def steal_cakes(self, fill_to):
        """rs2b0t's stealCakes: steals from a stand beside the stall until the backpack is full, or holds fill_to
        food. Gives 'stocked', 'combat', 'aborted' or 'no-progress'."""
        stand = STALL_STAND
        refusals = 0
        deadline = game.tick() + STEAL_PASS_TICKS
        while game.tick() < deadline:
            if self.need_eat() or chat_dialog.can_continue():
                return 'aborted'
            if game.in_combat():
                return 'combat'
            if inventory.is_full() or (fill_to is not None and self.food_count() >= fill_to):
                return 'stocked'
            if not self.lockout_over():
                yield from execution.delay_until(lambda: self.lockout_over(), 12000)
                continue

            if game.tile().distance_to(stand) > 0:
                yield from traversal.walk_to(stand, radius=0, timeout_ms=30000)
                if STALL_TILE.distance_to(game.tile()) > NEAR_STALL:
                    log('could not get beside the stall from', game.tile())
                    yield from execution.delay_ticks(1)
                    continue

            stall = self.stocked_stall()
            if stall is None:
                yield from execution.delay_until(lambda: self.stocked_stall() is not None, STALL_RESTOCK_WAIT_MS)
                continue

            if self.guard_near(stand):
                other = STALL_STAND_ALT if stand == STALL_STAND else STALL_STAND
                if not self.guard_near(other):
                    stand = other
                else:
                    yield from execution.delay_until(lambda: not self.guard_near(game.tile()), GUARD_WAIT_MS)
                continue

            self.lockout_seen = False
            before = self.food_count()
            if stall.interact(STALL_OP):
                yield from execution.delay_until(lambda: self.food_count() > before or game.in_combat() or self.lockout_seen, STEAL_RESOLVE_MS)
                if self.food_count() > before:
                    self.steals += 1
                    refusals = 0
                    continue
                if game.in_combat():
                    return 'combat'
                if self.lockout_seen:
                    self.lockout_until = game.tick() + LOCKOUT_TICKS
                    continue
            else:
                yield from execution.delay_ticks(1)
            refusals += 1
            if refusals >= REFUSALS_BEFORE_SWAP:
                stand = STALL_STAND_ALT if stand == STALL_STAND else STALL_STAND
                log(refusals, 'steals got nothing; moving to the stand at', stand)
                refusals = 0
        return 'no-progress'

    # Pickpocketing.

    def find_target(self):
        """The nearest target in the leash, those beside you first, as rs2b0t picks them."""
        phase = self.phase()
        anchor = phase.anchor
        leash = phase.leash
        now = game.tick()
        skip = self.unreachable
        found = npcs.query().name(phase.targets).action('Pickpocket').where(lambda n: n.tile().distance_to(anchor) <= leash and skip.get(n.index, -1) < now).reachable().results()
        if not found:
            return None
        found.sort(key=lambda n: (0 if n.distance() <= 1 else 1, n.distance()))
        return found[0]

    def pickpocket(self):
        if self.stunned():
            yield from execution.delay_until(lambda: not self.stunned() or self.need_eat(), 9000)
            return
        target = self.find_target()
        if target is None:
            return
        xp = skills.xp('thieving')
        mark = game_messages.mark()
        if not target.interact('Pickpocket'):
            yield from execution.delay_ticks(2)
            return
        wait_ms = 2400 + 600 * target.distance()
        yield from execution.delay_until(lambda: skills.xp('thieving') > xp or self.stunned() or chat_dialog.can_continue() or self.need_eat() or game_messages.saw_since(mark, CANT_REACH), wait_ms)
        if skills.xp('thieving') > xp:
            self.steals += 1
            return
        if game_messages.saw_since(mark, CANT_REACH):
            # Behind a stall or a wall the walk check missed; try another while it wanders.
            self.unreachable[target.index] = game.tick() + UNREACHABLE_SKIP_TICKS
            return
        if self.stunned():
            yield from execution.delay_until(lambda: not self.stunned() or self.need_eat(), 9000)

    def wait_for_target(self):
        yield from execution.delay_ticks(2)

    def on_progress_report(self):
        return {
            'Thieving': f'{skills.level("thieving")} (from {self.level_start})',
            'Thieving xp': skills.xp('thieving') - self.xp_start,
            'Doing': self.phase().name,
            'Steals': self.steals,
            'Stuns': self.stuns,
            'Food banked': self.banked,
            'Bank trips': self.trips,
            'Eaten': self.eats,
            'Fled': self.flees,
            'Deaths': self.deaths,
        }


BOT = define_bot(
    name='AIO thiever',
    create=AioThiever,
    description="Thieving 1 to 99: Lumbridge men to 5, Ardougne cakes to 40, guards to 55, then knights",
    category='Thieving',
    settings_schema=SETTINGS,
)

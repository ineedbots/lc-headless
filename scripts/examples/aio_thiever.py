# Trains Thieving from level 1, by level: men and women in Lumbridge to 5, then East Ardougne's Baker's stall to
# 40, banking each full backpack of cakes, then the market guards to 55 and its knights after that, eating cakes
# stolen from the stall, or taken from the bank with bank_food. Built from rs2b0t's ThievingBot, ArdyCakes and ArdyThiever (MIT, see thirdparty/rs2b0t).
# Thieving needs a members' world.

from rs2004.catalogs import ContinueDialog, MIN_EAT_HP, food_heal_amount, should_eat_to_use_food
from rs2004.catalogs import FLEE_TILE, LOCKOUT_TICKS, STAND, steal_cakes

SETTINGS = {
    'food_target': SettingDef('number', 20, 'Cakes to carry', 1, 27, help='for guards and knights: how many to steal from the stall, or take from the bank'),
    'restock_at_food': SettingDef('number', 3, 'Restock cakes at', 0, 26, help='steal more from the stall at this many, or bank for them'),
    'bank_food': SettingDef('boolean', False, 'Take cakes from the bank', help='instead of the stall, while the bank has them'),
    'rest_until_hp': SettingDef('number', 10, 'Rest to HP% without food', 10, 100),
    'bank_every_minutes': SettingDef('number', 60, 'Bank run every N minutes', 0, 120, help='also whenever the backpack fills; 0 for only then. Keeps food, and coins in Lumbridge'),
    'stop_at_level': SettingDef('number', 100, 'Stop at Thieving level', 2, 100),
}

LUMBRIDGE = Tile(3221, 3219, 0)
MARKET = Tile(2661, 3306, 0)
ARDOUGNE_BANK_STAND = Tile(2655, 3286, 0)
# Port Sarim to Karamja, and Brimhaven to Ardougne.
SHIP_FARES = 60
# East of here is Asgarnia and Misthalin, across White Wolf Mountain or the sea from Ardougne. Its wolves kill a
# thief, so from there the bot sails, pickpocketing in Lumbridge first when it is short of the fares.
ARDOUGNE_EAST_X = 2880
WOLF_PASS = 'white-wolf-mountain'

# A failed pickpocket stuns for 8 ticks; waiting 9 lets the next click path.
STUN_TICKS = 9
UNREACHABLE_SKIP_TICKS = 15
LEASH_SLACK = 6
LONG_WALK_TILES = 30
TICKS_PER_MINUTE = 100
# A bank run keeps food, but at most this much, so the backpack keeps room for loot.
MAX_KEPT_FOOD = 22

# Every food the stall gives. Eaten partial forms first, so slots free up; withdrawn whole cakes first.
FOOD_NAMES = ['cake', '2/3 cake', 'slice of cake', 'bread', 'chocolate slice']
EAT_ORDER = ['Slice of cake', '2/3 cake', 'Chocolate slice', 'Bread', 'Cake']
WITHDRAW_ORDER = ['Cake', '2/3 cake', 'Chocolate slice', 'Bread', 'Slice of cake']
DEPOSIT_FOOD_ORDER = ['Slice of cake', 'Bread', 'Chocolate slice', '2/3 cake', 'Cake']

COINS = 'Coins'
MEMBERS_ONLY = "members' world to gain experience in thieving"
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
    Phase('cakes', 5, None, STAND, 40, "East Ardougne's Baker's stall"),
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
        self.resting = False
        self.bank_out_of_food = False
        self.unreachable = {}
        self.xp_start = skills.xp('thieving')
        self.level_start = skills.level('thieving')
        self.last_phase = None
        self.last_wanted = None
        self.fare_check = False
        self.earning_fare = False
        self.last_bank_tick = game.tick()
        log('thieving', self.level_start, '; starting with', self.phase().name, 'in', self.phase().where)
        self.add(
            ContinueDialog(),
            Task(self.done, self.finish, 'finish'),
            Task(lambda: self.in_ardougne_phase() and self.in_real_combat(), self.flee, 'flee'),
            Task(self.need_eat, self.eat, 'eat'),
            Task(self.far_from_post, self.travel, 'travel'),
            Task(lambda: self.phase().name == 'cakes' and inventory.is_full(), self.bank_haul, 'bank cakes'),
            Task(self.needs_bank, self.restock_from_bank, 'bank'),
            Task(self.bank_run_due, self.bank_run, 'bank run'),
            Task(self.must_rest, self.rest, 'rest'),
            Task(self.needs_stall_food, self.restock_from_stall, 'steal food'),
            Task(lambda: self.phase().name == 'cakes', self.steal_cakes_task, 'steal cakes'),
            Task(lambda: self.phase().targets is not None and self.find_target() is not None, self.pickpocket, 'pickpocket'),
            Task(lambda: self.phase().targets is not None, self.wait_for_target, 'wait'),
        )

    # Where and how to train.

    def phase(self):
        wanted = phase_for(skills.level('thieving'))
        if wanted.name != self.last_wanted:
            self.last_wanted = wanted.name
            self.fare_check = wanted.name != 'men'
        # Decided once on the way to Ardougne, and again after a death once respawned, not on each call: the
        # first ship takes half the fares, and that half must not send the bot back to Lumbridge.
        if self.fare_check and skills.effective('hitpoints') > 0 and game.tile() is not None:
            self.fare_check = False
            self.earning_fare = self.short_of_fares()
            if self.earning_fare:
                log('only', inventory.count(COINS), 'coins, short of the', SHIP_FARES, 'for the ships to Ardougne; pickpocketing in Lumbridge first')
        phase = wanted
        if self.earning_fare and wanted.name != 'men':
            if inventory.count(COINS) < SHIP_FARES:
                phase = PHASES[0]
            else:
                self.earning_fare = False
                log(inventory.count(COINS), 'coins, enough for the ships to Ardougne')
        if self.last_phase is not None and phase.name != self.last_phase:
            log('thieving', skills.level('thieving'), ': moving on to', phase.name, 'in', phase.where)
        self.last_phase = phase.name
        return phase

    def east_of_ardougne(self):
        here = game.tile()
        return here is not None and here.x > ARDOUGNE_EAST_X

    def short_of_fares(self):
        return self.east_of_ardougne() and inventory.count(COINS) < SHIP_FARES

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
        elif MEMBERS_ONLY in text:
            self.request_finish('Thieving needs a members\' world')

    def on_death(self):
        self.deaths += 1
        self.bank_out_of_food = False
        # The coins may be gone; phase() looks again once respawned.
        self.fare_check = True
        log('died')

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
        # From the east the walker takes the ships by Karamja, never the pass: phase() has made sure of the fares.
        avoid = [WOLF_PASS] if self.east_of_ardougne() else None
        log('walking to', phase.where, 'at', phase.anchor)
        yield from traversal.walk_resilient(phase.anchor, radius=3, attempts=4, timeout_ms=600000, avoid_zones=avoid, log=say)

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
        self.last_bank_tick = game.tick()
        log('banked', cakes, 'stall food;', self.banked, 'in all')
        yield from bank.close()
        yield from traversal.walk_resilient(STAND, radius=1, attempts=4, timeout_ms=120000, log=lambda m: log(' ', m))

    def needs_bank(self):
        """Guards and knights: banks the loot when the backpack fills, and for cakes when low with bank_food."""
        phase = self.phase()
        if phase.targets is None or not self.in_ardougne_phase() or self.in_real_combat():
            return False
        low = self.settings.bank_food and self.food_count() <= self.settings.restock_at_food and not self.bank_out_of_food
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
        # Everything goes in, and with bank_food, food_target cakes come out, leaving a slot for the coins.
        yield from bank.deposit_inventory()
        yield from bank.wait_ready()
        self.trips += 1
        self.last_bank_tick = game.tick()
        if not self.settings.bank_food:
            yield from bank.close()
            return
        target = self.settings.food_target
        for name in WITHDRAW_ORDER:
            need = target - self.food_count()
            if need <= 0 or inventory.is_full():
                break
            if bank.count(name) > 0:
                yield from bank.withdraw_x(name, need)
        self.bank_out_of_food = self.food_count() <= self.settings.restock_at_food
        if self.bank_out_of_food:
            log('the bank is out of cakes; stealing more from the stall')
        else:
            log('carrying', self.food_count(), 'cakes')
        yield from bank.close()
        if not self.bank_out_of_food:
            yield from traversal.walk_resilient(self.phase().anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: log(' ', m))

    def bank_run_due(self):
        """A full backpack the run would make room in, or bank_every_minutes since the last bank, between
        steals."""
        if self.in_real_combat() or self.stunned():
            return False
        if inventory.is_full() and self.bank_run_frees_space():
            return True
        minutes = self.settings.bank_every_minutes
        return minutes > 0 and game.tick() - self.last_bank_tick >= minutes * TICKS_PER_MINUTE

    def keeps_coins(self):
        return self.phase().name == 'men'

    def banks_on_run(self, name):
        return len(name) > 0 and not is_food(name) and not (self.keeps_coins() and name == COINS)

    def bank_run_frees_space(self):
        return self.food_count() > self.kept_food() or len([i for i in inventory.items() if self.banks_on_run(i.name or '')]) > 0

    def kept_food(self):
        return min(self.settings.food_target, MAX_KEPT_FOOD)

    def bank_run(self):
        """Banks everything except food, and except coins in Lumbridge, where they are the fares to Ardougne. Food beyond
        kept_food() goes in too, the partial forms first."""
        phase = self.phase()
        stand = None if phase.name == 'men' else ARDOUGNE_BANK_STAND
        if inventory.is_full():
            log('bank run: the backpack is full')
        else:
            log('bank run after', self.settings.bank_every_minutes, 'minutes')
        opened = yield from banking.open(stand)
        if not opened:
            log('could not open the bank; trying again')
            yield from execution.delay_ticks(3)
            return
        yield from bank.deposit_all_matching(lambda name, id: self.banks_on_run(name))
        food_before = self.food_count()
        for name in DEPOSIT_FOOD_ORDER:
            while self.food_count() > self.kept_food() and inventory.count(name) > 0:
                before = self.food_count()
                if not bank.deposit(name, 'Deposit 1'):
                    break
                yield from execution.delay_until(lambda: self.food_count() < before, 2000)
        self.banked += max(0, food_before - self.food_count())
        self.trips += 1
        self.last_bank_tick = game.tick()
        log('bank run done; carrying', self.food_count(), 'food')
        yield from bank.close()
        yield from traversal.walk_resilient(phase.anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: log(' ', m))

    # The Baker's stall.

    def needs_stall_food(self):
        phase = self.phase()
        if phase.targets is None or not self.in_ardougne_phase() or self.in_real_combat() or inventory.is_full():
            return False
        from_stall = not self.settings.bank_food or self.bank_out_of_food
        return from_stall and self.food_count() <= self.settings.restock_at_food

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

    def steal_cakes(self, fill_to):
        """The catalogs' steal_cakes, with this bot's eating and its lockout after a flee. Gives 'stocked', 'combat',
        'aborted' or 'no-progress'. Use with yield from."""
        result = yield from steal_cakes(lambda: chat_dialog.can_continue(), lambda _status: None, lambda m: log(m), fill_to, self.need_eat,
                                        lambda: self.lockout_until, self.count_steal)
        return result

    def count_steal(self):
        self.steals += 1

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

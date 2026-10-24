"""WanderLooter's tasks: rs2b0t's scripts/WanderLooter/WanderLooterTasks.ts (MIT, see thirdparty/rs2b0t)."""

import random

from bots.wanderlooter.logic import now_ms, pick_wander_tile, should_bank_loot, should_deposit_on_bank, should_idle_bank
from rs2004.catalogs import is_edible_food, should_panic


def eat_one(bot):
    """Eats one bite when the bot needs it: True when hitpoints went up. Use with yield from."""
    if bank.is_open() or not bot.need_eat():
        return False
    foods = [item for item in inventory.items() if is_edible_food(item, bot.food_name)]
    if len(foods) == 0:
        return False
    food = foods[0]
    bot.status = f"eating {food.name} ({skills.effective('hitpoints')}/{skills.level('hitpoints')} hp)"
    before = skills.effective('hitpoints')
    if not food.interact('Eat'):
        return False
    healed = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
    if healed:
        bot.eats += 1
    return healed


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Eat food')
        self.bot = bot

    def validate(self):
        return not bank.is_open() and self.bot.need_eat()

    def execute(self):
        for _ in range(28):
            if event_signal.pending() or not self.bot.need_eat():
                return
            ate = yield from eat_one(self.bot)
            if not ate:
                return


class FleeLowHealth(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Flee low health')
        self.bot = bot

    def validate(self):
        return should_panic(skills.hp_fraction(), self.bot.panic_at, self.bot.food_count())

    def execute(self):
        bot = self.bot
        here = game.tile()
        bot.status = 'low health — fleeing'
        bot.log(f"fleeing at {skills.effective('hitpoints')}/{skills.level('hitpoints')} hp with no food")
        found = nearest_bank_reachable(here, navigator) if here is not None else None
        if found is None:
            bot.request_finish('fled low health: no reachable bank')
            return
        stand = found['tile']
        arrived = yield from traversal.walk_resilient(Tile(stand['x'], stand['z'], stand['level']), radius=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        bot.request_finish(f"fled to the {found['name']} bank at low health" if arrived else f"fled low health: could not reach the {found['name']} bank")


def withdraw_food(bot):
    """Use with yield from."""
    target = bot.food_withdraw
    if target <= 0:
        return
    for _ in range(40):
        if bot.food_count() >= target or inventory.is_full():
            break
        before = bot.food_count()
        need = target - before
        op = 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')
        if not bank.withdraw(bot.food_name, op):
            break
        landed = yield from execution.delay_until(lambda: bot.food_count() > before, 2500)
        if not landed:
            break
    if bot.food_count() == 0:
        bot.log(f"no '{bot.food_name}' in the bank — continuing foodless")


def bank_trip(bot, reason):
    """Banks the loot at the nearest bank and tops the food up: True when it banked. Use with yield from."""
    bot.status = 'banking loot'
    bot.log(f'banking ({reason})')
    ok = yield from banking.bank_nearest(lambda name: should_deposit_on_bank(name, bot.food_name, bot.food_count(), bot.food_withdraw), common_junk=False,
                                         after_deposit=lambda: withdraw_food(bot), log=lambda m: bot.log(f'  {m}'))
    if bank.is_open():
        yield from bank.close()
    if not ok:
        return False
    bot.bank_trips += 1
    bot.log(f'banked loot (trip {bot.bank_trips})')
    return True


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Bank run')
        self.bot = bot
        self.next_try_at = 0

    def validate(self):
        return now_ms() >= self.next_try_at and should_bank_loot(self.bot.loot_slots(), self.bot.bank_at, inventory.is_full())

    def execute(self):
        bot = self.bot
        reason = 'inventory full' if inventory.is_full() else f'{bot.loot_slots()}/{bot.bank_at} loot slots'
        banked = yield from bank_trip(bot, reason)
        if banked:
            self.next_try_at = 0
            return
        self.next_try_at = now_ms() + 60000
        bot.log('bank run failed — retrying in 60s')


def count_item(id):
    return inventory.count_by_id(id)


class LootDrops(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Loot drops')
        self.bot = bot

    def validate(self):
        self.bot.observe_health()
        return not inventory.is_full() and self.bot.find_loot() is not None

    def execute(self):
        bot = self.bot
        hp_before = bot.observe_health()
        drop = bot.find_loot()
        if drop is None:
            return
        id = drop.id
        name = drop.name or 'loot'
        tile = drop.tile()
        if bot.damage_near(tile):
            bot.blacklist.mark_unsafe(id, tile)
            bot.log(f'blacklisting {name} at {tile} for 30m — damage nearby before looting')
            return
        bot.status = f'looting {name} at {tile}'
        before = count_item(id)
        status = yield from reach.entity_op(lambda: bot.find_loot_at(id, tile), 'Take', lambda: count_item(id) > before, expect_ms=5000, what=name, log=lambda m: bot.log(m))
        hurt = bot.observe_health() < hp_before
        if status == 'done' and count_item(id) > before:
            now = now_ms()
            bot.blacklist.success(id, tile)
            bot.note_loot(now)
            bot.log(f'looted {name} at {tile}')
            if hurt:
                bot.blacklist.mark_unsafe(id, tile)
                bot.log(f'blacklisting {name} at {tile} for 30m — took damage while looting')
            else:
                bot.note_pickup(id, tile, now)
            return
        if hurt:
            bot.blacklist.mark_unsafe(id, tile)
            bot.log(f'blacklisting {name} at {tile} for 30m — took damage while trying to loot')
            return
        self.handle_failure(id, name, tile, status)

    def handle_failure(self, id, name, tile, status):
        result = self.bot.blacklist.failure(id, tile, status)
        if result == 'blacklisted':
            until = 'unreachable' if status == 'unreachable' else 'stuck'
            self.bot.log(f"blacklisting {until} loot '{name}' id={id} at {tile} for 30m")
            return
        self.bot.log(f"loot '{name}' id={id} at {tile} did not complete ({status}); still trying")


class Wander(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Wander')
        self.bot = bot

    def validate(self):
        return True

    def execute(self):
        bot = self.bot
        here = game.tile()
        if here is None:
            return
        target = None
        for attempt in range(6):
            if target is not None:
                break
            candidate = pick_wander_tile(here, bot.wander_distance, lambda tile: self.wanderable(here, tile, attempt), random.random, bot.last_wander_dir)
            if candidate is not None and bot.can_walk_to(candidate):
                target = candidate
        if target is None:
            bot.note_wander()
            bot.log('no reachable wander target — trying again')
            return
        steps = max(abs(target.x - here.x), abs(target.z - here.z))
        bot.status = f'wandering {steps} steps to {target}'
        bot.log(f'wandering {steps} steps to {target}')
        arrived = yield from traversal.walk_resilient(target, radius=3, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))
        bot.note_wander(here, target)
        bot.log(f'wandered to {target}' if arrived else f'wander to {target} did not complete')

    def wanderable(self, here, tile, attempt):
        # Only the first attempt may take the floor below; later ones stay on this level.
        return (attempt == 0 or tile.level == here.level) and self.bot.can_wander_to(tile)


class IdleBank(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Bank when idle')
        self.bot = bot
        self.next_try_at = 0

    def validate(self):
        now = now_ms()
        return now >= self.next_try_at and should_idle_bank(now, self.bot.last_loot_at, self.bot.bank_after_ms)

    def execute(self):
        bot = self.bot
        minutes = round(bot.bank_after_ms / 60000)
        banked = yield from bank_trip(bot, f'no loot for {minutes} minutes')
        if banked:
            self.next_try_at = 0
            bot.restart_idle_timer()
            return
        self.next_try_at = now_ms() + 60000
        bot.log('bank run failed — retrying in 60s')

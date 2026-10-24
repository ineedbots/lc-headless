# Pickpockets East Ardougne market's guards, knights, paladins or heroes, stealing cakes from the Baker's stall
# for food, kiting or fighting a guard that catches it, and banking the loot: rs2b0t's ArdyThiever (MIT, see
# thirdparty/rs2b0t). It solves the clues it picks up.

from rs2004.catalogs import ARDOUGNE_PICKPOCKET_TARGETS, CAKE_ITEMS, STUN_COMBAT_TICKS, ContinueDialog, DeathRecovery
from rs2004.catalogs import choose_target, count_matching, food_heal_amount, is_hostile_attacker, matches_any, required_thieving
from rs2004.catalogs import should_bank, should_eat, should_panic, slots_matching, steal_cakes, sustain, target_spot, withdraw_to
from rs2004.clues import SolveClue, SolveClueHost

BANK_STAND = Tile(2655, 3286, 0)
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
PICKPOCKET_OP = 'Pickpocket'
FLEE_TILE = Tile(2655, 3298, 0)
ENGAGE_RADIUS = 5
OBSTACLE = ['door', 'gate']
FOOD = CAKE_ITEMS
LOOT = ['coins', 'chaos rune', 'death rune', 'blood rune', 'nature rune', 'jug of wine', 'fire orb', 'gold ore', 'clue scroll', 'body talisman', 'steel arrow', 'iron ore']
# 90 seconds, and 5 minutes.
FIGHT_TICKS = 150
REGEN_MS = 300000
STUNNED = ['been stunned', 'fail to pick']

SETTINGS = {
    'thieve_target': SettingDef('string', 'Guard', 'Pickpocket target', options=ARDOUGNE_PICKPOCKET_TARGETS, help="the bot knows each target's market spot — no anchor to place"),
    'guard_response': SettingDef('string', 'Flee', 'Guard response', options=['Flee', 'Fight'], help='caught at the stall: Flee kites the guard off the market; Fight kills it (bring combat stats)'),
    'panic_hp': SettingDef('number', 25, 'Panic below HP% (no food)', 0, 100),
    'rest_until_hp': SettingDef('number', 60, 'Regen to HP% when bank empty', 0, 100),
    'food_target': SettingDef('number', 22, 'Fill food to (count)', 1, 27),
    'restock_at_food': SettingDef('number', 3, 'Restock when food drops to', 0, 26),
    'bank_at_loot_slots': SettingDef('number', 12, 'Bank at loot slots', 1, 27),
    'solve_clues': SettingDef('boolean', True, 'Solve clue drops', group='Clues'),
}
SETTINGS.update(PERIODIC_BANK_SETTINGS)


def food_count():
    return count_matching(inventory.items(), FOOD)


def first_food():
    for item in inventory.items():
        if matches_any(item.name, FOOD):
            return item
    return None


def need_eat():
    item = first_food()
    if item is None or food_count() <= 0:
        return False
    return should_eat(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(item.name or 'Cake'), food_count())


def loot_slots():
    return slots_matching(inventory.items(), LOOT)


def eat_if_needed():
    if not need_eat():
        return
    food = first_food()
    if food is None:
        return
    before = skills.effective('hitpoints')
    if food.interact('Eat'):
        yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)


class Flee(Task):
    def __init__(self, bot):
        Task.__init__(self, label='flee')
        self.bot = bot

    def validate(self):
        return self.bot.in_real_combat()

    def execute(self):
        bot = self.bot
        bot.status = f'kiting the guard to {FLEE_TILE.x},{FLEE_TILE.z}'
        bot.log(f'combat; kiting the guard to {FLEE_TILE.x},{FLEE_TILE.z}')
        bot.flees += 1
        yield from walk_opening(FLEE_TILE, 0, OBSTACLE, lambda m: bot.log(f'  {m}'))
        yield from execution.delay_until(lambda: not game.in_combat(), 15000)


class FightBack(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight back')
        self.bot = bot

    def validate(self):
        return self.bot.in_real_combat()

    def track(self, engaged):
        index = engaged.index
        name = engaged.name
        return npcs.query().where(lambda n: n.index == index and n.name == name).first()

    def execute(self):
        bot = self.bot
        attacker = npcs.query().where(lambda n: is_hostile_attacker(n, ENGAGE_RADIUS)).nearest()
        if attacker is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = f'fighting back: {attacker.name} at {attacker.tile()}'
        bot.log(f'combat; fighting back against {attacker.name}')
        if not attacker.interact('Attack'):
            yield from execution.delay_ticks(2)
            return
        deadline = game.tick() + FIGHT_TICKS
        while game.tick() < deadline:
            if event_signal.pending() or chat_dialog.can_continue() or bot.died:
                return
            if need_eat() or should_panic(skills.hp_fraction(), bot.panic_at, food_count()):
                return
            target = self.track(attacker)
            if target is None:
                bot.kills += 1
                bot.log(f'killed the {attacker.name}')
                return
            if target.health == 0 and target.max_health > 0:
                yield from execution.delay_until(lambda: self.track(attacker) is None, 10000)
                bot.kills += 1
                bot.log(f'killed the {attacker.name}')
                return
            if not game.in_combat() and not target.in_combat:
                return
            yield from execution.delay_ticks(2)


class LootDrops(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot drops')
        self.bot = bot

    def find(self):
        bot = self.bot
        # Adjacent only: walking for coins in or after a stun wrecks the pickpocket rate.
        return ground_items.query().where(lambda g: matches_any(g.name, LOOT)).where(lambda g: g.distance() <= 1 and g.tile().distance_to(bot.anchor) <= bot.leash + 4 and reachability.can_reach(g.tile())).nearest()

    def validate(self):
        return not self.bot.in_real_combat() and not self.bot.stunned() and not inventory.is_full() and self.find() is not None

    def execute(self):
        drop = self.find()
        if drop is None:
            return
        name = drop.name or ''
        self.bot.status = f'picking up {name}'
        before = inventory.count(name)
        if not drop.interact('Take'):
            yield from execution.delay_ticks(2)
            return
        taken = yield from execution.delay_until(lambda: inventory.count(name) > before, 3000)
        if taken:
            self.bot.count_loot(name)


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat food')
        self.bot = bot

    # Above Pickpocket, so low-HP bites use a stun, when it can't steal anyway.
    def validate(self):
        return need_eat()

    def execute(self):
        bot = self.bot
        for _ in range(28):
            if bot.died or chat_dialog.can_continue() or event_signal.pending() or not need_eat():
                return
            food = first_food()
            if food is None:
                return
            hp = round(skills.hp_fraction() * 100)
            bot.status = f'eating {food.name} while stunned ({hp}% hp)' if bot.stunned() else f'eating {food.name} ({hp}% hp)'
            before = skills.effective('hitpoints')
            if not food.interact('Eat'):
                return
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or food_count() == 0, 3000)
            if skills.effective('hitpoints') > before:
                bot.eats += 1


class PanicRetreat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='panic retreat')
        self.bot = bot

    def validate(self):
        return self.bot.near_market() and should_panic(skills.hp_fraction(), self.bot.panic_at, food_count())

    def execute(self):
        bot = self.bot
        bot.status = 'panic: no food; retreating to the bank'
        yield from traversal.walk_to(BANK_STAND, radius=2, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
        opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if opened:
            banked = [i for i in bank.items() if matches_any(i.name, FOOD)]
            if len(banked) > 0 and banked[0].name:
                yield from withdraw_to(banked[0].name, bot.food_target, food_count)
        if food_count() == 0:
            bot.status = 'panic: bank empty; waiting for regen'
            yield from execution.delay_until(lambda: skills.hp_fraction() >= bot.rest_until or game.in_combat() or chat_dialog.can_continue() or event_signal.pending(), REGEN_MS)
        yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        return self.bot.near_market() and should_bank(loot_slots(), self.bot.bank_at, inventory.is_full())

    def execute(self):
        bot = self.bot
        bot.status = 'banking the loot'
        yield from traversal.walk_to(BANK_STAND, radius=2, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
        opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        before = loot_slots()
        yield from bank.deposit_all_matching(deposit_matcher(lambda name: matches_any(name, LOOT), bot.bank_common))
        yield from execution.delay_ticks(1)
        after = loot_slots()
        note = ' (nothing deposited!)' if after >= before else ''
        bot.log(f'banked: loot slots {before}->{after}{note}')
        bot.trips += 1
        bot.status = 'heading back'
        yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class RestockCakes(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock cakes')
        self.bot = bot

    def validate(self):
        return self.bot.near_market() and not self.bot.in_real_combat() and not inventory.is_full() and food_count() <= self.bot.restock_at

    def set_status(self, status):
        self.bot.status = status

    def on_steal(self):
        self.bot.steals += 1

    def execute(self):
        bot = self.bot
        bot.status = "restocking at the Baker's stall"
        bot.log(f'restocking cake (have {food_count()})')
        yield from steal_cakes(
            lambda: event_signal.pending() or bot.died or chat_dialog.can_continue() or bot.in_real_combat(),
            self.set_status,
            bot.log,
            fill_to=bot.food_target,
            should_eat=need_eat,
            on_steal=self.on_steal,
        )


class Pickpocket(Task):
    def __init__(self, bot):
        Task.__init__(self, label='pickpocket')
        self.bot = bot
        self.unreachable_streak = 0

    def candidates(self):
        bot = self.bot
        found = npcs.query().name(bot.target).action(PICKPOCKET_OP).where(lambda n: n.tile().distance_to(bot.anchor) <= bot.leash).results()
        # Adjacent first: less walking between attempts once a stun lifts.
        found.sort(key=lambda n: (1 if n.distance() > 1 else 0, n.distance()))
        return found

    # Gives way while stunned with low HP, so EatFood can bite during the lock.
    def validate(self):
        bot = self.bot
        if bot.stunned() and need_eat():
            return False
        return not bot.in_real_combat() and food_count() > bot.restock_at and not inventory.is_full() and len(self.candidates()) > 0

    def execute(self):
        bot = self.bot
        if bot.stunned():
            bot.status = 'stunned; waiting'
            yield from execution.delay_until(lambda: not bot.stunned() or need_eat(), 9000)
            return
        choice = choose_target(self.candidates(), lambda n: reachability.can_reach(n.tile(), adjacent_ok=True))
        target = choice.target
        if target is None:
            if choice.blocked is not None and self.unreachable_streak < 2:
                self.unreachable_streak += 1
                bot.status = f'clearing path to {bot.target}'
                yield from walk_opening(choice.blocked.tile(), 1, OBSTACLE, bot.log)
            else:
                self.unreachable_streak += 1
                bot.status = f'{bot.target} out of reach; waiting for it to wander back'
                yield from execution.delay_ticks(2)
            return
        self.unreachable_streak = 0

        bot.status = f'pickpocketing {bot.target} at {target.tile()}'
        xp_before = skills.xp('thieving')
        used_before = inventory.used()
        if not target.interact(PICKPOCKET_OP):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: skills.xp('thieving') > xp_before or inventory.used() > used_before or chat_dialog.can_continue() or bot.stunned() or need_eat(), 2500)
        if skills.xp('thieving') > xp_before:
            bot.steals += 1
            return
        if bot.stunned():
            yield from execution.delay_until(lambda: not bot.stunned() or need_eat(), 9000)


class ReturnToAnchor(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to anchor')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and self.bot.anchor.distance_to(here) > self.bot.leash + 6

    def execute(self):
        bot = self.bot
        bot.status = 'heading to the market'
        here = game.tile()
        if here is not None and bot.anchor.distance_to(here) > 30:
            yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=6, timeout_ms=240000, log=lambda m: bot.log(f'  {m}'))
        yield from walk_opening(bot.anchor, 2, OBSTACLE, bot.log)


class ArdyThiever(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.target = s.str('thieve_target', 'Guard')
        self.response = s.str('guard_response', 'Flee')
        spot = target_spot(self.target)
        self.anchor = spot.anchor
        self.leash = spot.leash
        self.food_target = s.num('food_target', 22)
        self.restock_at = s.num('restock_at_food', 3)
        self.bank_at = s.num('bank_at_loot_slots', 12)
        self.panic_at = s.num('panic_hp', 25) / 100
        self.rest_until = s.num('rest_until_hp', 60) / 100
        self.bank_common = s.bool('bank_common_junk', True)
        self.steals = 0
        self.eats = 0
        self.looted = 0
        self.trips = 0
        self.flees = 0
        self.kills = 0
        self.died = False
        self.status = 'starting'
        self.stunned_until_tick = 0
        self.loot_counts = {}
        self.clues_solved = 0
        self.xp_at_start = skills.xp('thieving')
        self.solve_clues = s.bool('solve_clues', True)
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda name: matches_any(name, FOOD),
                                                  food_name=lambda: 'Cake', food_withdraw=lambda: self.food_target, enabled=lambda: self.solve_clues))
        sustain.set(eat_if_needed)

        need = required_thieving(self.target)
        if skills.level('thieving') < need:
            self.log(f"ArdyThiever needs Thieving {need} to pickpocket {self.target} (have {skills.level('thieving')}); stopping.")
            raise ValueError(f'ArdyThiever: Thieving {need} required')
        self.log(f"ArdyThiever starting; target '{self.target}' at {self.anchor} r{self.leash} (Thieving {need}+), {self.response.lower()} mode, bank {BANK_STAND}")
        self.on('chat_message', self.heard)

        # EatFood before Pickpocket, to use a stun; Pickpocket before Loot, so coins beside you don't pull you off
        # the target.
        tasks = [ContinueDialog(), DeathRecovery(self, self.anchor, 6, on_death=self.died_now, on_recovered=self.recovered)]
        if self.response != 'Fight':
            tasks.append(Flee(self))
        tasks.append(EatFood(self))
        tasks.append(PanicRetreat(self))
        if self.response == 'Fight':
            tasks.append(FightBack(self))
        tasks.append(self.solve_clue)
        tasks.append(PeriodicBank(
            strategy=lambda: parse_bank_strategy(self.settings.str('bank_strategy', 'Off')),
            items_threshold=lambda: self.settings.num('bank_every_items', 15),
            minutes_threshold=lambda: self.settings.num('bank_every_minutes', 10),
            count_loot=loot_slots,
            deposit=lambda name: matches_any(name, LOOT),
            common_junk=lambda: self.bank_common,
            return_to=lambda: self.anchor,
            set_status=self.set_status,
            log=self.log,
        ))
        tasks.append(BankRun(self))
        tasks.append(RestockCakes(self))
        tasks.append(Pickpocket(self))
        tasks.append(LootDrops(self))
        tasks.append(ReturnToAnchor(self))
        for task in tasks:
            self.add(task)

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
        self.set_status(text)

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True
        if len([s for s in STUNNED if s in text]) > 0:
            self.stunned_until_tick = game.tick() + STUN_COMBAT_TICKS

    def died_now(self):
        self.status = 'died; recovering'
        self.solve_clue.note_death()
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def set_status(self, status):
        self.status = status

    def grind_targets(self):
        return [self.target.lower()]

    def recovery_anchor(self):
        return self.anchor

    def near_market(self):
        here = game.tile()
        return here is not None and self.anchor.distance_to(here) <= self.leash + 6

    def stunned(self):
        return game.tick() <= self.stunned_until_tick

    def in_real_combat(self):
        return game.in_combat() and not self.stunned()

    def count_loot(self, name):
        self.looted += 1
        if name:
            self.loot_counts[name] = self.loot_counts.get(name, 0) + 1

    def on_progress_report(self):
        report = {'Status': self.status, 'Steals': self.steals, 'Thieving xp': skills.xp('thieving') - self.xp_at_start, 'Food': food_count(),
                  'Loot slots': loot_slots(), 'Looted': self.looted, 'Bank trips': self.trips, 'Fled': self.flees, 'Fought': self.kills, 'Ate': self.eats}
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report


BOT = define_bot(
    name='ArdyThiever',
    create=ArdyThiever,
    description='Low-level East Ardougne pickpocket bot — steals cake for food, pickpockets Guard/Knight/Paladin/Hero, flees (kites) or fights the guard per the guardResponse setting, banks loot + junk, grabs ground coins',
    category='Thieving',
    tags=['ardougne', 'thieving', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

# Steals cakes from East Ardougne's Baker's stall, swapping stands when the baker watches, banks each full pack,
# and kites or fights a guard that catches it: rs2b0t's ArdyCakes (MIT, see thirdparty/rs2b0t). In Fight mode it
# solves the medium clues the guards drop on the spot. Thieving 5 and a members' world.

from rs2004.catalogs import CAKE_ITEMS, FLEE_TILE, HOSTILE_NAMES, LOCKOUT_TICKS, STAND, ContinueDialog, DeathRecovery
from rs2004.catalogs import carried_cakes, food_heal_amount, is_hostile_attacker, matches_any, should_eat, steal_cakes, sustain
from rs2004.clues import SolveClue, SolveClueHost

BANK_STAND = Tile(2655, 3286, 0)
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
MARKET_RADIUS = 40
OBSTACLE = ['door', 'gate']
ENGAGE_RADIUS = 5
# 90 seconds.
FIGHT_TICKS = 150

SETTINGS = {
    'guard_response': SettingDef('string', 'Flee', 'Guard response', options=['Flee', 'Fight'], help='caught at the stall: Flee kites the guard off the market; Fight kills it (bring combat stats)'),
    'solve_clues': SettingDef('boolean', True, 'Solve clue drops', group='Clues', help='Fight mode kills guards, which drop medium clues: solve them on the spot'),
}


def near_market():
    here = game.tile()
    return here is not None and STAND.distance_to(here) <= MARKET_RADIUS


def need_eat():
    n = carried_cakes()
    if n <= 0:
        return False
    return should_eat(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount('Cake'), n)


def cake_in_pack():
    for item in inventory.items():
        if matches_any(item.name, CAKE_ITEMS):
            return item
    return None


def eat_if_needed():
    if not need_eat():
        return
    food = cake_in_pack()
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
        return game.in_combat()

    def execute(self):
        bot = self.bot
        bot.status = f'kiting the guard to {FLEE_TILE.x},{FLEE_TILE.z}'
        bot.log(f'combat; kiting the guard to {FLEE_TILE.x},{FLEE_TILE.z}')
        bot.flees += 1
        yield from walk_opening(FLEE_TILE, 0, OBSTACLE, lambda m: bot.log(f'  {m}'))
        yield from execution.delay_until(lambda: not game.in_combat(), 15000)
        if not game.in_combat():
            bot.mark_combat_end()


class FightBack(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight back')
        self.bot = bot

    def validate(self):
        return game.in_combat()

    def track(self, engaged):
        index = engaged.index
        name = engaged.name
        return npcs.query().where(lambda n: n.index == index and n.name == name).first()

    def execute(self):
        bot = self.bot
        attacker = npcs.query().where(lambda n: is_hostile_attacker(n, ENGAGE_RADIUS)).nearest()
        if attacker is None:
            yield from execution.delay_ticks(2)
            if not game.in_combat():
                bot.mark_combat_end()
            return
        bot.status = f'fighting back: {attacker.name} at {attacker.tile()}'
        bot.log(f'combat; fighting back against {attacker.name}')
        if not attacker.interact('Attack'):
            yield from execution.delay_ticks(2)
            return
        deadline = game.tick() + FIGHT_TICKS
        while game.tick() < deadline:
            if event_signal.pending() or chat_dialog.can_continue() or bot.died or need_eat():
                return
            target = self.track(attacker)
            if target is None or (target.health == 0 and target.max_health > 0):
                if target is not None:
                    yield from execution.delay_until(lambda: self.track(attacker) is None, 10000)
                bot.kills += 1
                bot.log(f'killed the {attacker.name}')
                bot.mark_combat_end()
                return
            if not game.in_combat() and not target.in_combat:
                bot.mark_combat_end()
                return
            yield from execution.delay_ticks(2)


class EatCake(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat cake')
        self.bot = bot

    def validate(self):
        return need_eat()

    def execute(self):
        bot = self.bot
        for _ in range(28):
            if bot.died or chat_dialog.can_continue() or event_signal.pending() or not need_eat():
                return
            food = cake_in_pack()
            if food is None:
                return
            bot.status = f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
            before = skills.effective('hitpoints')
            if not food.interact('Eat'):
                return
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or carried_cakes() == 0, 3000)
            if skills.effective('hitpoints') > before:
                bot.eats += 1


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        return near_market() and not game.in_combat() and inventory.is_full()

    def execute(self):
        bot = self.bot
        bot.status = 'banking the cakes'
        yield from traversal.walk_to(BANK_STAND, radius=2, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
        opened = yield from bank.open_booth(BANK_STAND, BOOTH_NAME, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank; will retry')
            return
        before = carried_cakes()
        held_before = inventory.used()
        # The whole pack goes in: cakes are the haul, and the rest is random event loot (death runes, arrows,
        # coins) that would ride along forever.
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(1)
        shed = before - carried_cakes()
        bot.banked += max(0, shed)
        stuck = f' ({inventory.used()} slot(s) would not deposit)' if inventory.used() > 0 else ''
        bot.log(f'banked {shed} cakes + {max(0, held_before - inventory.used() - shed)} other item stack(s){stuck}')
        bot.trips += 1
        bot.status = 'heading back to the stall'
        yield from traversal.walk_resilient(STAND, radius=1, attempts=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class StealCakes(Task):
    def __init__(self, bot):
        Task.__init__(self, label='steal cakes')
        self.bot = bot

    def validate(self):
        return near_market() and not game.in_combat() and not inventory.is_full() and not self.bot.died

    def on_steal(self):
        self.bot.steals += 1

    def on_reset(self):
        self.bot.resets += 1

    def set_status(self, status):
        self.bot.status = status

    def execute(self):
        bot = self.bot
        result = yield from steal_cakes(
            lambda: bot.died or event_signal.pending() or chat_dialog.can_continue(),
            self.set_status,
            bot.log,
            fill_to=28,
            should_eat=need_eat,
            locked_out_until=bot.locked_out_until,
            on_steal=self.on_steal,
            on_reset=self.on_reset,
        )
        if result == 'combat':
            bot.log('guard caught the steal; handling per guard_response')
        elif result == 'no-progress':
            bot.log('steal pass made no progress; re-entering')


class ReturnToStall(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to stall')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and STAND.distance_to(here) > MARKET_RADIUS

    def execute(self):
        bot = self.bot
        bot.status = "heading to the Baker's stall"
        here = game.tile()
        if here is not None and STAND.distance_to(here) > 30:
            yield from traversal.walk_resilient(STAND, radius=3, attempts=6, timeout_ms=240000, log=lambda m: bot.log(f'  {m}'))
        yield from walk_opening(STAND, 2, OBSTACLE, bot.log)


class ArdyCakes(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.response = self.settings.str('guard_response', 'Flee')
        self.steals = 0
        self.resets = 0
        self.eats = 0
        self.banked = 0
        self.trips = 0
        self.flees = 0
        self.kills = 0
        self.died = False
        self.combat_end_tick = 0
        self.clues_solved = 0
        self.status = 'starting'
        self.xp_at_start = skills.xp('thieving')
        self.solve_clues = self.settings.bool('solve_clues', True)
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda name: matches_any(name, CAKE_ITEMS),
                                                  food_name=lambda: 'Cake', food_withdraw=lambda: 10, enabled=lambda: self.solve_clues))
        sustain.set(eat_if_needed)
        if skills.level('thieving') < 5:
            self.log(f"ArdyCakes needs Thieving 5 for the Baker's stall (have {skills.level('thieving')}); stopping.")
            raise ValueError('ArdyCakes: Thieving 5 required')
        self.log(f'ArdyCakes starting; stand {STAND}, bank {BANK_STAND}, {self.response.lower()} mode')
        self.on('chat_message', self.heard)
        self.add(
            ContinueDialog(),
            DeathRecovery(self, STAND, 6, on_death=self.died_now, on_recovered=self.recovered),
            FightBack(self) if self.response == 'Fight' else Flee(self),
            EatCake(self),
            self.solve_clue,
            BankRun(self),
            StealCakes(self),
            ReturnToStall(self),
        )

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True

    def died_now(self):
        self.status = 'died; recovering'
        self.solve_clue.note_death()
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def grind_targets(self):
        return [n.lower() for n in HOSTILE_NAMES]

    def recovery_anchor(self):
        return STAND

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
        self.set_status(text)

    def mark_combat_end(self):
        self.combat_end_tick = game.tick()

    def locked_out_until(self):
        return self.combat_end_tick + LOCKOUT_TICKS

    def on_progress_report(self):
        fought = {'Fought': self.kills} if self.response == 'Fight' else {'Fled': self.flees}
        report = {'Status': self.status, 'Steals': self.steals, 'Thieving xp': skills.xp('thieving') - self.xp_at_start,
                  'Carried': carried_cakes(), 'Banked': self.banked, 'Resets': self.resets, 'Trips': self.trips}
        report.update(fought)
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report


BOT = define_bot(
    name='ArdyCakes',
    create=ArdyCakes,
    description="Baker's-stall cake thiever — steals on the golden stand, resets nearby when watched, banks full packs, flees (kites) or fights a catching guard per guardResponse",
    category='Thieving',
    tags=['ardougne', 'thieving', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

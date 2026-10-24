# Fights East Ardougne market's guards, feeding itself from the Baker's stall, and banks the rares they drop at
# the south bank: rs2b0t's ArdyFighter (MIT, see thirdparty/rs2b0t). It needs melee stats that beat the guards'
# 60-second respawn, about Strength 80 unarmed. It solves the clues they drop.

from rs2004.catalogs import CAKE_ITEMS, ContinueDialog, DeathRecovery, count_matching, food_heal_amount
from rs2004.catalogs import matches_any, needs_cake_restock, should_bank, should_eat, should_panic, slots_matching, steal_cakes
from rs2004.catalogs import selected_loadout, sustain, weapon_of
from rs2004.clues import SolveClue, SolveClueHost
from rs2004.tabs import WEAPON_SLOT

DEFAULT_ANCHOR = Tile(2661, 3306, 0)
DEFAULT_BANK_STAND = Tile(2655, 3286, 0)
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
DEFAULT_LOOT = ['clue scroll', 'blood rune', 'nature rune', 'chaos rune', 'body talisman', 'steel arrow', 'iron ore']
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints']
# Why: the Baker's stall is the only restock, so the bot eats what it hands over; a loadout's food would never
# arrive, and the restock would never settle.
FOOD = CAKE_ITEMS
# 90 seconds, and 5 minutes.
FIGHT_TICKS = 150
REGEN_MS = 300000

SETTINGS = {
    'anchor': SettingDef('tile', DEFAULT_ANCHOR, 'Market anchor (x,z)'),
    'leash_radius': SettingDef('number', 12, 'Leash radius (tiles)', 5, 25),
    'target': SettingDef('string', 'Guard', 'NPC to fight (name)'),
    'combat_style': SettingDef('string', 'strength', 'Combat style', options=COMBAT_STYLE_OPTIONS, help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'bank_stand': SettingDef('tile', DEFAULT_BANK_STAND, 'Bank stand tile (x,z)'),
    'loadout': SettingDef('string', '', 'Loadout', options=[], options_from='loadouts', help="gear to wear, defined in the Loadouts panel; its food is ignored, this bot eats what it steals from the Baker's stall"),
    'panic_hp': SettingDef('number', 25, 'Panic below HP% (no food)', 0, 100),
    'rest_until_hp': SettingDef('number', 60, 'Regen to HP% when bank empty', 0, 100),
    'food_target': SettingDef('number', 8, 'Keep food stocked to (count)', 1, 27, help="after eating to full, restock the Baker's stall back up to this many"),
    'bank_at_loot_slots': SettingDef('number', 12, 'Bank at loot slots', 1, 27),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot item names (contains)'),
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


def eat_if_needed():
    if not need_eat():
        return
    food = first_food()
    if food is None:
        return
    before = skills.effective('hitpoints')
    if food.interact('Eat'):
        yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)


class ReturnToAnchor(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to anchor')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and self.bot.anchor.distance_to(here) > self.bot.leash + 6

    def execute(self):
        self.bot.status = 'walking to the market'
        yield from traversal.walk_resilient(self.bot.anchor, radius=3, attempts=6, timeout_ms=240000, log=lambda m: self.bot.log(f'  {m}'))


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat food')
        self.bot = bot

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
            bot.status = f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
            before = skills.effective('hitpoints')
            if not food.interact('Eat'):
                return
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or food_count() == 0, 3000)
            if skills.effective('hitpoints') > before:
                bot.eats += 1


class RestockCakes(Task):
    def __init__(self, bot):
        Task.__init__(self, label='restock cakes')
        self.bot = bot

    def validate(self):
        return not game.in_combat() and needs_cake_restock(self.bot.food_target)

    def set_status(self, status):
        self.bot.status = status

    def on_steal(self):
        self.bot.steals += 1

    def execute(self):
        bot = self.bot
        bot.status = "restocking at the Baker's stall"
        yield from steal_cakes(
            lambda: event_signal.pending() or bot.died or chat_dialog.can_continue(),
            self.set_status,
            bot.log,
            fill_to=bot.food_target,
            should_eat=need_eat,
            on_steal=self.on_steal,
        )


class LootDrops(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot drops')
        self.bot = bot

    def find(self):
        loot = self.bot.loot
        return ground_items.query().where(lambda g: matches_any(g.name, loot)).within(self.bot.leash + 4).nearest()

    def validate(self):
        return not game.in_combat() and not inventory.is_full() and self.find() is not None

    def execute(self):
        bot = self.bot
        drop = self.find()
        if drop is None:
            return
        bot.status = f'looting {drop.name} at {drop.tile()}'
        before = count_matching(inventory.items(), bot.loot)
        if not drop.interact('Take'):
            yield from execution.delay_ticks(2)
            return
        taken = yield from execution.delay_until(lambda: count_matching(inventory.items(), bot.loot) > before, 5000)
        if taken:
            bot.looted += 1


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        return should_bank(self.bot.loot_slots(), self.bot.bank_at, inventory.is_full())

    def execute(self):
        bot = self.bot
        bot.status = 'banking the loot'
        yield from traversal.walk_to(bot.bank_stand, radius=2, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
        opened = yield from bank.open_booth(bot.bank_stand, BOOTH_NAME, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank, will retry')
            return
        loot = bot.loot
        yield from bank.deposit_all_matching(deposit_matcher(lambda name: matches_any(name, loot), bot.bank_common))
        yield from execution.delay_ticks(1)
        bot.trips += 1
        bot.log(f'deposited the loot (trip {bot.trips})')
        bot.status = 'heading back to the market'
        yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class PanicRetreat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='panic retreat')
        self.bot = bot

    def validate(self):
        return should_panic(skills.hp_fraction(), self.bot.panic_at, food_count())

    def execute(self):
        bot = self.bot
        bot.status = 'panic: no food, retreating to the bank'
        bot.log(f"panic retreat at {skills.effective('hitpoints')}/{skills.level('hitpoints')} hp")
        yield from traversal.walk_to(bot.bank_stand, radius=2, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
        opened = yield from bank.open_booth(bot.bank_stand, BOOTH_NAME, BOOTH_OP)
        if opened:
            banked = [i for i in bank.items() if matches_any(i.name, FOOD)]
            if len(banked) > 0 and banked[0].name:
                name = banked[0].name
                for _ in range(bot.food_target):
                    if inventory.is_full():
                        break
                    before = food_count()
                    if not bank.withdraw(name, 'Withdraw-1'):
                        break
                    taken = yield from execution.delay_until(lambda: food_count() > before, 2000)
                    if not taken:
                        break
                bot.log(f'withdrew {food_count()} food from the bank')
        if food_count() == 0:
            bot.status = 'panic: bank empty, waiting for regen'
            yield from execution.delay_until(lambda: skills.hp_fraction() >= bot.rest_until or game.in_combat() or chat_dialog.can_continue() or event_signal.pending(), REGEN_MS)
        yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=4, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class SetStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set style')
        self.bot = bot
        self.announced = False

    def validate(self):
        return not game.in_combat() and not game.has_combat_style(self.bot.combat_style)

    def execute(self):
        style = self.bot.combat_style
        self.bot.status = 'setting combat style'
        game.set_combat_style(style)
        ok = yield from execution.delay_until(lambda: game.has_combat_style(style), 3000)
        resolution = game.combat_style_resolution(style)
        if ok and resolution is not None and not self.announced:
            self.announced = True
            self.bot.log(f'combat style: {describe_combat_style(resolution)}')


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot

    def find_target(self):
        bot = self.bot
        return npcs.query().name(bot.target).action('Attack').where(lambda n: not n.in_combat and n.tile().distance_to(bot.anchor) <= bot.leash).nearest()

    def track(self, engaged):
        index = engaged.index
        target = self.bot.target
        return npcs.query().where(lambda n: n.index == index and matches_entity_name(n.name, target)).first()

    def validate(self):
        return not game.in_combat() and not need_eat() and self.find_target() is not None

    def execute(self):
        bot = self.bot
        guard = self.find_target()
        if guard is None:
            return
        bot.status = f'attacking {bot.target} at {guard.tile()}'
        if not guard.interact('Attack'):
            yield from execution.delay_ticks(2)
            return
        engaged = yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
        if not engaged or chat_dialog.can_continue():
            return

        bot.status = 'fighting'
        deadline = game.tick() + FIGHT_TICKS
        reattacks = 0
        while game.tick() < deadline:
            if event_signal.pending() or chat_dialog.can_continue() or bot.died or inventory.is_full():
                return
            if need_eat() or skills.hp_fraction() < bot.panic_at:
                return
            me = game.tile()
            if me is None or guard.tile().distance_to(me) > bot.leash + 10:
                bot.log('displaced mid-fight, abandoning target')
                return
            target = self.track(guard)
            if target is None:
                bot.kills += 1
                return
            if target.health == 0 and target.max_health > 0:
                yield from execution.delay_until(lambda: self.track(guard) is None, 10000)
                bot.kills += 1
                return
            if not game.in_combat() and not target.in_combat:
                if reattacks >= 2:
                    return
                reattacks += 1
                target.interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
                continue
            yield from execution.delay_ticks(2)


class ArdyFighter(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.anchor = s.tile('anchor', DEFAULT_ANCHOR)
        self.leash = s.num('leash_radius', 12)
        self.target = s.str('target', 'Guard')
        self.bank_stand = s.tile('bank_stand', DEFAULT_BANK_STAND)
        self.loot = [l.lower() for l in s.list('loot', DEFAULT_LOOT)]
        self.panic_at = s.num('panic_hp', 25) / 100
        self.rest_until = s.num('rest_until_hp', 60) / 100
        self.food_target = s.num('food_target', 8)
        self.bank_at = s.num('bank_at_loot_slots', 12)
        self.bank_common = s.bool('bank_common_junk', True)
        self.combat_style = parse_combat_style(s.str('combat_style', 'strength'))
        self.kills = 0
        self.steals = 0
        self.eats = 0
        self.looted = 0
        self.trips = 0
        self.deaths = 0
        self.died = False
        self.clues_solved = 0
        self.status = 'starting'
        self.solve_clues = s.bool('solve_clues', True)
        worn = [i.name for i in equipment.items() if i.slot == WEAPON_SLOT]
        weapon = weapon_of(selected_loadout(s), worn[0] if worn else None) or ''
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda name: matches_any(name, FOOD),
                                                  food_name=lambda: 'Cake', food_withdraw=lambda: self.food_target, weapon_name=lambda: weapon,
                                                  enabled=lambda: self.solve_clues))
        sustain.set(eat_if_needed)
        if skills.level('thieving') < 5:
            self.log(f"ArdyFighter needs Thieving 5 for the Baker's stall (have {skills.level('thieving')}), stopping.")
            raise ValueError('ArdyFighter: Thieving 5 required')
        self.xp_at_start = sum([skills.xp(sk) for sk in COMBAT_SKILLS])
        self.log(f"ArdyFighter starting, anchor {self.anchor} r{self.leash}, target '{self.target}', bank {self.bank_stand}")
        self.on('chat_message', self.heard)
        self.add(
            ContinueDialog(),
            DeathRecovery(self, self.anchor, 6, on_death=self.died_now, on_recovered=self.recovered),
            LootDrops(self),
            EatFood(self),
            PanicRetreat(self),
            self.solve_clue,
            PeriodicBank(
                strategy=lambda: parse_bank_strategy(self.settings.str('bank_strategy', 'Off')),
                items_threshold=lambda: self.settings.num('bank_every_items', 15),
                minutes_threshold=lambda: self.settings.num('bank_every_minutes', 10),
                count_loot=self.loot_slots,
                deposit=lambda name: matches_any(name, self.loot),
                common_junk=lambda: self.bank_common,
                return_to=lambda: self.anchor,
                set_status=self.set_status,
                log=self.log,
            ),
            BankRun(self),
            RestockCakes(self),
            SetStyle(self),
            Fight(self),
            ReturnToAnchor(self),
        )

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True

    def died_now(self):
        self.status = 'died, recovering'
        self.deaths += 1
        self.solve_clue.note_death()
        self.log('died! waiting for respawn, then walking back to the market')

    def recovered(self):
        self.died = False

    def set_status(self, status):
        self.status = status

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
        self.set_status(text)

    def loot_slots(self):
        return slots_matching(inventory.items(), self.loot)

    def grind_targets(self):
        return [self.target.lower()]

    def recovery_anchor(self):
        return self.anchor

    def on_progress_report(self):
        xp = sum([skills.xp(sk) for sk in COMBAT_SKILLS]) - self.xp_at_start
        report = {'Status': self.status, 'Kills': self.kills, 'Combat xp': xp, 'Food': food_count(), 'Steals': self.steals,
                  'Looted': self.looted, 'Loot slots': self.loot_slots(), 'Bank trips': self.trips, 'Deaths': self.deaths}
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report


BOT = define_bot(
    name='ArdyFighter',
    create=ArdyFighter,
    description="Fights East Ardougne market guards, feeds itself from the Baker's stall, loots rares, banks them at the south bank (needs melee stats that beat the 60s guard respawn — ~str 80 unarmed)",
    category='Combat',
    tags=['ardougne', 'thieving', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

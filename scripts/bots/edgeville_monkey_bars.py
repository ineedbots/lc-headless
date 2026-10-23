# Swings across the monkey bars in Edgeville's dungeon, restocking food by the dungeon's ladder when it runs out,
# or only after a death: rs2b0t's EdgevilleMonkeyBars (MIT, see thirdparty/rs2b0t). Agility 15. Not for a
# 10-hitpoint account.

from rs2004.catalogs import LOADOUT_SETTING, food_heal_amount, script_food, should_eat_to_use_food

MONKEYBARS_APPROACH = Tile(3121, 9964, 0)
# To swing across the bars.
MIN_AGILITY = 15
FALLBACK_FOOD = 'Lobster'
RESTOCK_DUNGEON = 'Dungeon ladder (out of food)'
RESTOCK_DEATH = 'After death only'
# Dungeon tiles are north of this; the surface south of it.
UNDERGROUND_Z = 6400
# Beside the trapdoor, as ChaosDruidKiller stands; shut it offers Open, open Climb-down.
TRAPDOOR_NAME = 'Trapdoor'
TRAPDOOR_STAND = Tile(3096, 3468, 0)
LADDER_NAME = 'Ladder'
LADDER_OP = 'Climb-up'
LADDER_STAND = Tile(3096, 9868, 0)
INTERMEDIATE_GATE = Tile(3103, 9909, 0)
WILDERNESS_GATE = Tile(3130, 9914, 0)
EDGEVILLE_BANK = Tile(3094, 3493, 0)
BARS_NAME = 'Monkeybars'
BARS_OP = 'Swing across'
BARS_RADIUS = 15
SWINGS = ['swing', 'cross', 'climb-across', 'balance']
# How long a swing back across the bars takes to settle.
SWING_SETTLE_MS = 12000

SETTINGS = {
    'loadout': LOADOUT_SETTING,
    'food': SettingDef('string', FALLBACK_FOOD, 'Food', help='Food to eat and restock when the loadout does not specify food.'),
    'food_amount': SettingDef('number', 20, 'Food to withdraw', 5, 28),
    'min_food': SettingDef('number', 1, 'Bank below food count', 0, 28,
                           help='minimum food to have before heading into the dungeon; 0 = never bank for food (used at startup and during dungeon restocks)'),
    'restock_mode': SettingDef('string', RESTOCK_DEATH, 'Restock mode', options=[RESTOCK_DUNGEON, RESTOCK_DEATH],
                               help='Dungeon ladder: climb out near 3096,9868 when food runs out. After death only: stay until death, then bank from surface.'),
    'bank_junk': SettingDef('boolean', True, 'Bank junk items', help="deposit anything that isn't the selected food (e.g. random event loot) when banking"),
}


def underground():
    here = game.tile()
    return here is not None and here.z >= UNDERGROUND_Z


def food_count(food):
    wanted = food.lower()
    return len([i for i in inventory.items() if i.name is not None and wanted in i.name.lower()])


def swing_op(actions, preferred=None):
    if preferred:
        for a in actions:
            if a.lower() == preferred.lower():
                return a
    for a in actions:
        lower = a.lower()
        if len([s for s in SWINGS if s in lower]) > 0:
            return a
    return None


def looks_like_bars(loc):
    name = (loc.name or '').lower()
    return name == BARS_NAME.lower() or 'monkey' in name or 'bar' in name or swing_op(loc.actions()) is not None


def find_monkey_bars():
    """The bars by name and a swing option, by name, by any swing option, or by a name like monkey bars."""
    by_name = locs.query().name(BARS_NAME).within(BARS_RADIUS).where(lambda l: swing_op(l.actions(), BARS_OP) is not None).nearest()
    if by_name is not None:
        return by_name
    named = locs.query().name(BARS_NAME).within(BARS_RADIUS).where(lambda l: len(l.actions()) > 0).nearest()
    if named is not None:
        return named
    by_op = locs.query().within(BARS_RADIUS).where(lambda l: swing_op(l.actions(), BARS_OP) is not None).nearest()
    if by_op is not None:
        return by_op
    return locs.query().within(BARS_RADIUS).where(lambda l: looks_like_bars(l) and len(l.actions()) > 0).nearest()


def ensure_retaliate_off(log):
    """Auto retaliate off, so it doesn't fight back while it trains."""
    if game.auto_retaliate_on():
        log(f'Auto Retaliate turned off ({game.set_auto_retaliate(False)})')


def open_nearest_gate(log):
    gate = locs.query().name('Gate').within(6).nearest()
    if gate is None:
        log('No gate found nearby; may already be open or out of range')
        return
    ops = [a for a in gate.actions() if 'open' in a.lower()]
    if len(ops) == 0:
        log(f"Gate found but no \"Open\" action (actions: [{', '.join(gate.actions())}]); likely already open")
        return
    log(f'Opening gate: {ops[0]} @ {gate.tile().x},{gate.tile().z}')
    gate.interact(ops[0])
    # The gate swings before the walk goes through it.
    yield from execution.delay_ticks(4)


def climb_dungeon_ladder(log):
    """Climbs Edgeville dungeon's ladder back to the surface. Use with yield from."""
    if not underground():
        return True
    yield from traversal.walk_resilient(LADDER_STAND, radius=2)
    for _ in range(5):
        if not underground():
            return True
        ladder = locs.query().name(LADDER_NAME).within(8).where(lambda l: len([a for a in l.actions() if 'climb-up' in a.lower()]) > 0).nearest()
        if ladder is None:
            ladder = locs.query().name(LADDER_NAME).within(8).nearest()
        if ladder is None:
            log('Ladder not found near exit; retrying walk')
            yield from traversal.walk_resilient(LADDER_STAND, radius=1)
            continue
        ups = [a for a in ladder.actions() if 'climb-up' in a.lower()]
        op = ups[0] if len(ups) > 0 else LADDER_OP
        log(f"Climbing ladder: {op} on '{ladder.name}' @ {ladder.tile().x},{ladder.tile().z}")
        ladder.interact(op)
        climbed = yield from execution.delay_until(lambda: not underground(), 8000)
        if climbed:
            log('Climbed to surface')
            return True
    return not underground()


# Why: the reverse of the way in, trying each gate's walk first since they may still be open.
def exit_dungeon_to_surface(log):
    """Walks from the bars back through the dungeon's gates to the ladder, and climbs out. Use with yield from."""
    if not underground():
        return True
    # Why: a swing can land on the bars' far side, around 3121,9969, and the way out starts on the near side.
    here = game.tile()
    if here is not None and here.z > 9967:
        log('On far side of monkey bars; swinging back toward exit before leaving dungeon')
        bars = locs.query().within(10).where(lambda l: swing_op(l.actions()) is not None).nearest()
        if bars is not None:
            op = swing_op(bars.actions()) or (bars.actions()[0] if len(bars.actions()) > 0 else None)
            if op:
                log(f"Swinging back: {op} on '{bars.name}' @ {bars.tile().x},{bars.tile().z}")
                bars.interact(op)
                yield from execution.delay(SWING_SETTLE_MS)
    log('Exiting dungeon; approaching wilderness gate')
    yield from traversal.walk_resilient(WILDERNESS_GATE, radius=3)
    yield from open_nearest_gate(log)
    log('Exiting dungeon; approaching intermediate gate')
    yield from traversal.walk_resilient(INTERMEDIATE_GATE, radius=3)
    yield from open_nearest_gate(log)
    log('Exiting dungeon; approaching ladder')
    climbed = yield from climb_dungeon_ladder(log)
    return climbed


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat food')
        self.bot = bot

    def need_eat(self):
        food = self.bot.food_name()
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(food), food_count(food))

    def validate(self):
        return not self.bot.died and not bank.is_open() and self.need_eat()

    def execute(self):
        self.bot.status = 'eating'
        key = self.bot.food_name().lower()
        while self.need_eat():
            food = None
            for item in inventory.items():
                if item.name is not None and key in item.name.lower():
                    food = item
                    break
            if food is None:
                break
            before = skills.effective('hitpoints')
            food.interact('Eat')
            ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
            if ate:
                self.bot.eats += 1
        # Eating has a 3-tick delay, so the next swing waits it out.
        yield from execution.delay_ticks(3)


class BankAndRestock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank and restock')
        self.bot = bot

    # Banks after a death, when food runs low in dungeon mode, or below min_food on the surface, at the start.
    def validate(self):
        bot = self.bot
        if bot.died:
            return True
        if food_count(bot.food_name()) < bot.settings.num('min_food', 1) and not underground():
            return True
        return bot.needs_food_restock()

    def execute(self):
        bot = self.bot
        food_name = bot.food_name()
        has_any_food = food_count(food_name) > 0
        # Out of food underground in dungeon mode: back out through the gates and up the ladder.
        if not bot.died and not has_any_food and bot.restock_mode() != RESTOCK_DEATH and underground():
            bot.status = 'exiting dungeon to bank'
            bot.log('Out of food; exiting dungeon via ladder')
            out = yield from exit_dungeon_to_surface(bot.log)
            if not out:
                bot.log('Failed to climb dungeon ladder; will retry')
                return
        was_dead = bot.died
        bot.status = 'banking after death' if bot.died else 'banking'
        yield from traversal.walk_resilient(EDGEVILLE_BANK, radius=5)
        opened = yield from bank.open_booth(EDGEVILLE_BANK, 'Bank booth', 'Use-quickly')
        if not opened:
            opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            bot.log('Could not open bank; will retry')
            return
        if bot.settings.bool('bank_junk', True):
            yield from bank.deposit_all_matching(deposit_all_except([food_name]))
        else:
            yield from bank.deposit_inventory()
        yield from bank.withdraw_x(food_name, bot.settings.num('food_amount', 20))
        after = food_count(food_name)
        min_food = bot.settings.num('min_food', 1)
        if after < min_food:
            bot.status = f'out of {food_name} in bank; stopped'
            bot.request_finish(f'only {after} {food_name} in bank (minimum {min_food}); sending the bot to its own death is not useful')
            return
        bot.log(f'Withdrew food (have {after})')
        # After a death, auto retaliate off again.
        if was_dead:
            ensure_retaliate_off(bot.log)
        bot.died = False


class NavigateToMonkeyBars(Task):
    def __init__(self, bot):
        Task.__init__(self, label='navigate to monkey bars')
        self.bot = bot

    # Only while away from the bars: on the surface, or underground and out of reach of them.
    def validate(self):
        bot = self.bot
        if bot.died or bot.needs_food_restock():
            return False
        here = game.tile()
        if here is None:
            return False
        if here.z < UNDERGROUND_Z:
            return True
        if find_monkey_bars() is not None:
            return False
        return here.distance_to(MONKEYBARS_APPROACH) > 12

    def execute(self):
        bot = self.bot
        bot.status = 'navigating to monkey bars'
        bot.log('Starting dungeon navigation sequence')
        # The surface's trapdoor, opened then climbed down.
        if not underground():
            yield from traversal.walk_resilient(TRAPDOOR_STAND, radius=1)
            descended = False
            for _ in range(6):
                if descended:
                    break
                trap = locs.query().name(TRAPDOOR_NAME).where(lambda l: l.distance() <= 3).nearest()
                if trap is None:
                    yield from traversal.walk_resilient(TRAPDOOR_STAND, radius=1)
                    continue
                downs = [a for a in trap.actions() if 'climb-down' in a.lower()]
                opens = [a for a in trap.actions() if 'open' in a.lower()]
                op = downs[0] if len(downs) > 0 else (opens[0] if len(opens) > 0 else None)
                if op is None:
                    bot.log(f"Trapdoor actions: [{', '.join(trap.actions())}]")
                    yield from execution.delay_ticks(2)
                    continue
                bot.log(f'Interacting trapdoor: {op}')
                trap.interact(op)
                descended = yield from execution.delay_until(underground, 2500 if 'open' in op.lower() else 6000)
            if not descended:
                bot.log('Failed to climb down trapdoor; will retry')
                return
            bot.log('Descended into dungeon')
        yield from traversal.walk_resilient(INTERMEDIATE_GATE, radius=4)
        yield from open_nearest_gate(bot.log)
        yield from traversal.walk_resilient(WILDERNESS_GATE, radius=4)
        yield from open_nearest_gate(bot.log)
        yield from traversal.walk_resilient(MONKEYBARS_APPROACH, radius=3)
        bot.log('Reached monkey bars area')


class RepeatMonkeyBars(Task):
    def __init__(self, bot):
        Task.__init__(self, label='repeat monkey bars')
        self.bot = bot
        self.last_scan_tick = -100
        self.last_xp = -1

    def validate(self):
        return not self.bot.died and not self.bot.needs_food_restock() and underground()

    def execute(self):
        bot = self.bot
        bot.status = 'swinging on monkey bars'
        # Why: it clicks again without waiting for a swing to end, so a click's xp lands a loop or two later, and
        # a swing counts whenever the xp rose since the last loop.
        xp_now = skills.xp('agility')
        if self.last_xp >= 0 and xp_now > self.last_xp:
            bot.completions += 1
        self.last_xp = xp_now

        bars = find_monkey_bars()
        if bars is None:
            if game.tick() - self.last_scan_tick > 13:
                self.last_scan_tick = game.tick()
                nearby = [f"{l.name or '?'}@{l.tile().x},{l.tile().z}[{'|'.join(l.actions())}]" for l in locs.query().within(15).where(lambda l: len(l.actions()) > 0).results()[0:8]]
                found = f"; nearby: {'; '.join(nearby)}" if len(nearby) > 0 else ''
                bot.log(f'No monkey bars found nearby{found}')
            bot.status = 'waiting: no monkey bars in range'
            here = game.tile()
            if here is not None and here.distance_to(MONKEYBARS_APPROACH) > 4:
                yield from traversal.walk_resilient(MONKEYBARS_APPROACH, radius=2)
            else:
                yield from execution.delay_ticks(2)
            return
        actions = bars.actions()
        op = swing_op(actions, BARS_OP) or (actions[0] if len(actions) > 0 else None)
        if not op:
            bot.log(f"Bars '{bars.name}' has no actions")
            yield from execution.delay_ticks(2)
            return
        bot.status = f"{op} {bars.name or 'bars'} @ {bars.tile().x},{bars.tile().z}"
        if not bars.interact(op):
            bot.log(f"interact('{op}') returned false")
            bot.failed_swings += 1


class EdgevilleMonkeyBars(TaskBot):
    def on_start(self):
        self.status = 'starting'
        self.deaths = 0
        self.completions = 0
        self.eats = 0
        self.failed_swings = 0
        self.died = False
        self.xp_at_start = skills.xp('agility')
        agility = skills.level('agility')
        if agility < MIN_AGILITY:
            self.log(f'EdgevilleMonkeyBars needs Agility {MIN_AGILITY} (have {agility}); stopping.')
            raise ValueError(f'EdgevilleMonkeyBars: Agility {MIN_AGILITY} required')
        self.on('chat_message', self.heard)
        # With no food in the pack, BankAndRestock runs first.
        has_food = food_count(self.food_name()) > 0
        if not has_food:
            self.log(f'No {self.food_name()} in inventory; banking first')
        ensure_retaliate_off(self.log)
        self.log(f'EdgevilleMonkeyBars started (restock: {self.restock_mode()}, hasFood: {has_food})')
        self.add(EatFood(self), BankAndRestock(self), NavigateToMonkeyBars(self), RepeatMonkeyBars(self))

    def heard(self, e):
        text = (e.text or '').lower()
        if 'oh dear' in text and 'you are dead' in text:
            self.died = True
            self.deaths += 1
            self.log('Death detected')

    def food_name(self):
        return script_food(self.settings, self.settings.str('food', FALLBACK_FOOD))

    def restock_mode(self):
        return self.settings.str('restock_mode', RESTOCK_DEATH)

    def needs_food_restock(self):
        if self.restock_mode() == RESTOCK_DEATH:
            return False
        minimum = self.settings.num('min_food', 1)
        return minimum > 0 and food_count(self.food_name()) < minimum

    def on_progress_report(self):
        return {'Status': self.status, 'Swings': self.completions, 'Agility xp': skills.xp('agility') - self.xp_at_start,
                'Food': food_count(self.food_name()), 'Ate': self.eats, 'Deaths': self.deaths, 'Misses': self.failed_swings,
                'Restock': 'death' if self.restock_mode() == RESTOCK_DEATH else 'dungeon'}


BOT = define_bot(
    name='EdgevilleMonkeyBars',
    create=EdgevilleMonkeyBars,
    description='Edgeville dungeon monkey bars — restock via dungeon ladder or after death. NOT RECOMMENDED FOR 10HP ACCOUNTS.',
    category='Agility',
    tags=['edgeville', 'dungeon', 'monkey-bars', 'wilderness', 'banking'],
    settings_schema=SETTINGS,
)

# Pickpockets an NPC, Man by default, eating after failed steals, and can bank to restock food before walking
# back to where it started: rs2b0t's ThievingBot, registered as Thiever (MIT, see thirdparty/rs2b0t).

from rs2004.catalogs import LOADOUT_SETTING, MIN_EAT_HP, PICKPOCKET_TARGET_NAMES, STUN_COMBAT_TICKS, THIEVER_BANKING_OPTIONS
from rs2004.catalogs import ContinueDialog, auto_food_banking, can_steal_now, choose_target, close_bank_and_confirm_count
from rs2004.catalogs import count_food, create_return_to_anchor_task, food_heal_amount, food_matches, resolve_run_anchor
from rs2004.catalogs import script_food, should_eat_to_use_food, should_restock_food, tile_within_leash, withdraw_to

STUNNED = ['been stunned', 'fail to pick']
BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}

SETTINGS = {
    'target': SettingDef('string', 'Man', 'Pickpocket target', options=PICKPOCKET_TARGET_NAMES,
                         help='pick by exact in-game name (level in parens): Man/Woman 1, Farmer 10, Rogue 32, Guard 40, Knight of Ardougne 55, Paladin 70, Hero 80'),
    'action': SettingDef('string', 'Pickpocket', 'Action', help='right-click op, e.g. Pickpocket / Steal-from'),
    'loadout': LOADOUT_SETTING,
    'food': SettingDef('string', '', 'Food', help='Food to eat and withdraw; blank uses the selected loadout.'),
    'banking': SettingDef('string', 'None', 'Food banking', options=THIEVER_BANKING_OPTIONS, help='Auto = bank non-food items, withdraw food, and return to the starting spot'),
    'food_withdraw': SettingDef('number', 22, 'Food to carry', 1, 27, show_if={'key': 'banking', 'any_of': ['Auto']}),
    'bank_at_food': SettingDef('number', 0, 'Bank at food remaining', 0, 26, show_if={'key': 'banking', 'any_of': ['Auto']}),
    'suicide': SettingDef('boolean', False, 'Suicide thieving', help='keep pickpocketing when out of food instead of waiting to regen'),
    'drop_match': SettingDef('string', '', 'Drop when full (name contains)', help='drop these when the pack fills; blank = just idle when full (coins stack, so rarely fills)'),
    'loot': SettingDef('string', 'coins', 'Pick up from ground (name contains)', help='grab matching ground drops within the leash, e.g. coins; comma-separate for several; blank = pick up nothing'),
    'obstacle': SettingDef('string', 'door, gate', 'Openable obstacles (name contains)', help='when a target or the anchor is walled off, open the nearest of these that still has an Open action; comma-separate'),
    'leash_radius': SettingDef('number', 19, 'Leash radius (tiles)', 2, 40),
}


def split_keywords(raw):
    return [s.strip().lower() for s in raw.split(',') if s.strip()]


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Eat food')
        self.bot = bot

    def food(self):
        for item in inventory.items():
            if self.bot.is_food(item.name):
                return item
        return None

    # Above Steal, so it eats while a stun locks movement.
    def validate(self):
        return self.bot.need_eat() and self.food() is not None

    def execute(self):
        food = self.food()
        if food is None:
            return
        self.bot.status = 'eating (stunned)' if self.bot.stunned() else 'eating'
        before = skills.effective('hitpoints')
        food.interact('Eat')
        ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
        if ate:
            self.bot.eats += 1


class FoodBank(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Food bank')
        self.bot = bot

    def validate(self):
        return not game.in_combat() and self.bot.should_bank()

    def bank_food(self):
        for item in bank.items():
            if self.bot.is_food(item.name):
                return item
        return None

    def execute(self):
        bot = self.bot
        here = game.tile()
        known = nearest_bank(here) if here is not None else None
        if known is None:
            bot.stop_safely('no usable bank from this location')
            return
        stand = Tile(known['tile']['x'], known['tile']['z'], known['tile']['level'])
        bot.status = f"banking for food at {known['name']}"
        bot.log(f"food restock: {bot.food_count()}/{bot.food_withdraw}; walking to {known['name']} {stand}")
        walked = yield from traversal.walk_resilient(stand, radius=3, attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        if not walked:
            bot.stop_safely(f"could not reach {known['name']} bank")
            return
        opened = yield from open_bank_access(known, known.get('access') or BOOTH, lambda m: bot.log(f'  {m}'))
        if not opened:
            bot.stop_safely(f"could not open {known['name']} bank")
            return

        yield from bank.deposit_all_matching(lambda name, id: not bot.is_food(name))
        yield from execution.delay_until(lambda: self.bank_food() is not None, 3000)
        food = self.bank_food()
        if food is None or not food.name:
            bot.stop_safely(f"no '{bot.food}' food in the bank")
            return
        yield from withdraw_to(food.name, bot.food_withdraw, bot.food_count)
        expected = bot.food_count()
        if expected <= bot.bank_at_food:
            bot.stop_safely(f"only {expected} '{bot.food}' food available")
            return

        bot.status = 'closing the bank'
        kept = yield from close_bank_and_confirm_count(expected, bot.food_count)
        if not kept:
            bot.stop_safely(f"backpack did not retain {expected} '{bot.food}' food after closing the bank")
            return
        bot.bank_trips += 1
        bot.log(f"food restock complete: carrying {bot.food_count()} '{bot.food}' food")
        bot.status = 'returning from the bank'
        walked = yield from traversal.walk_resilient(bot.anchor, radius=2, attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        if not walked:
            bot.stop_safely('could not return to the pickpocket spot')


class WaitForHealth(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Wait for health')
        self.bot = bot
        self.announced = False

    def validate(self):
        waiting = not self.bot.can_steal()
        if not waiting:
            self.announced = False
        return waiting

    def execute(self):
        self.bot.status = 'waiting for HP; no food'
        if not self.announced:
            self.announced = True
            self.bot.log('HP is below the eat threshold with no food; waiting instead of risking death')
        yield from execution.delay_ticks(5)


class DropJunk(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Drop junk')
        self.bot = bot

    def junk(self):
        keyword = self.bot.drop_match
        if not keyword:
            return []
        return [i for i in inventory.items() if i.name is not None and keyword in i.name.lower()]

    def validate(self):
        return inventory.is_full() and len(self.junk()) > 0

    def execute(self):
        self.bot.status = 'dropping junk'
        for _ in range(28):
            junk = self.junk()
            if len(junk) == 0:
                break
            before = inventory.used()
            junk[0].interact('Drop')
            yield from execution.delay_until(lambda: inventory.used() < before, 3000)


class Loot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Loot')
        self.bot = bot

    def find(self):
        bot = self.bot
        want = bot.loot
        if len(want) == 0:
            return None

        def wanted(g):
            name = (g.name or '').lower()
            return len([k for k in want if k in name]) > 0

        # Adjacent only: walking the leash for coins wrecks the pickpocket rate.
        return ground_items.query().where(wanted).where(lambda g: g.distance() <= 1 and tile_within_leash(bot, g.tile()) and reachability.can_reach(g.tile())).nearest()

    # Never while stunned: Take would only turn you, or walk once the stun lifts.
    def validate(self):
        return not self.bot.stunned() and not inventory.is_full() and self.find() is not None

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
            self.bot.picked += 1


class Steal(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Steal')
        self.bot = bot
        self.unreachable_streak = 0

    def candidates(self):
        bot = self.bot
        found = npcs.query().name(bot.target).action(bot.action).where(lambda n: tile_within_leash(bot, n.tile())).results()
        # Adjacent first: less walking between attempts once a stun lifts.
        found.sort(key=lambda n: (1 if n.distance() > 1 else 0, n.distance()))
        return found

    # Holds the stun's wait so Loot can't walk you off a guard, but gives way when HP is low so EatFood can use
    # the locked ticks.
    def validate(self):
        bot = self.bot
        if bot.stunned() and bot.need_eat():
            return False
        return bot.can_steal() and not inventory.is_full() and len(self.candidates()) > 0

    def execute(self):
        bot = self.bot
        if bot.stunned():
            bot.status = 'stunned; waiting'
            yield from execution.delay_until(lambda: not bot.stunned() or bot.need_eat(), 9000)
            return

        choice = choose_target(self.candidates(), lambda n: reachability.can_reach(n.tile(), adjacent_ok=True))
        target = choice.target
        if target is None:
            if choice.blocked is not None and self.unreachable_streak < 2:
                self.unreachable_streak += 1
                bot.status = f'clearing path to {bot.target}'
                yield from walk_opening(choice.blocked.tile(), 1, bot.obstacles, bot.log)
            else:
                self.unreachable_streak += 1
                bot.status = f'{bot.target} out of reach; waiting'
                yield from execution.delay_ticks(2)
            return
        self.unreachable_streak = 0

        bot.status = f'{bot.action} {bot.target} at {target.tile()}'
        xp_before = skills.xp('thieving')
        used_before = inventory.used()
        if not target.interact(bot.action):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: skills.xp('thieving') > xp_before or inventory.used() > used_before or chat_dialog.can_continue() or bot.stunned() or bot.need_eat(), 2500)
        if skills.xp('thieving') > xp_before:
            bot.steals += 1
            return
        if bot.stunned():
            yield from execution.delay_until(lambda: not bot.stunned() or bot.need_eat(), 9000)


class ThievingBot(TaskBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.target = s.str('target', 'Man')
        self.action = s.str('action', 'Pickpocket')
        self.food = script_food(s, '').lower()
        self.auto_bank = auto_food_banking(s.str('banking', 'None'))
        self.food_withdraw = s.num('food_withdraw', 22)
        self.bank_at_food = min(s.num('bank_at_food', 0), self.food_withdraw - 1)
        self.suicide = s.bool('suicide', False)
        self.drop_match = s.str('drop_match', '').lower()
        self.loot = split_keywords(s.str('loot', 'coins'))
        self.obstacles = split_keywords(s.str('obstacle', 'door, gate'))
        self.leash_radius = s.num('leash_radius', 19)
        self.steals = 0
        self.eats = 0
        self.picked = 0
        self.bank_trips = 0
        self.status = 'starting'
        self.stunned_until_tick = 0
        self.xp_at_start = skills.xp('thieving')
        self.anchor = resolve_run_anchor(game.tile(), None)
        if self.auto_bank and not self.food:
            self.status = 'Auto banking needs a food name; stopped'
            self.request_finish('Auto food banking needs a non-blank food setting')
            return
        eat = f', smart-eat *{self.food}*' if self.food else ''
        banking = f'at {self.bank_at_food} food (target {self.food_withdraw})' if self.auto_bank else 'off'
        suicide = ', suicide on' if self.suicide else ''
        self.log(f"thieving '{self.target}' ({self.action}) within {self.leash_radius} of {self.anchor}{eat}, banking {banking}{suicide}")
        self.on('chat_message', self.heard)
        # Why: EatFood comes before Steal, so low-HP bites happen in a stun, when pickpocketing can't anyway;
        # Steal comes before Loot so coins don't pull the bot off a guard.
        self.add(
            ContinueDialog(),
            EatFood(self),
            FoodBank(self),
            WaitForHealth(self),
            DropJunk(self),
            Steal(self),
            Loot(self),
            create_return_to_anchor_task(self, slack=4, arrive_radius=2, long_range_tiles=30),
        )

    def heard(self, e):
        text = (e.text or '').lower()
        if len([s for s in STUNNED if s in text]) > 0:
            self.stunned_until_tick = game.tick() + STUN_COMBAT_TICKS

    def recovery_anchor(self):
        return self.anchor

    def food_count(self):
        return count_food(inventory.items(), self.food)

    def need_eat(self):
        if not self.food or self.food_count() <= 0:
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food), self.food_count())

    def is_food(self, name):
        return food_matches(name, self.food)

    def should_bank(self):
        bankable_pack_full = inventory.is_full() and len([i for i in inventory.items() if not self.is_food(i.name)]) > 0
        return should_restock_food(self.auto_bank, self.food_count(), self.bank_at_food, bankable_pack_full)

    def can_steal(self):
        return can_steal_now(self.food_count(), skills.effective('hitpoints'), MIN_EAT_HP, self.suicide)

    def stunned(self):
        return game.tick() <= self.stunned_until_tick

    def stop_safely(self, reason):
        self.status = f'{reason}; stopped'
        self.request_finish(reason)

    def on_progress_report(self):
        return {'Status': self.status, 'Target': self.target, 'Steals': self.steals, 'Ate': self.eats, 'Picked': self.picked,
                'Food': self.food_count(), 'Bank trips': self.bank_trips, 'Thieving xp': skills.xp('thieving') - self.xp_at_start}


BOT = define_bot(
    name='Thiever',
    create=ThievingBot,
    description='Pickpockets an NPC (Man by default), eats after failed steals, and optionally banks to restock food before returning to the start tile',
    category='Thieving',
    tags=['pickpocket', 'coins', 'banking', 'food'],
    settings_schema=SETTINGS,
)

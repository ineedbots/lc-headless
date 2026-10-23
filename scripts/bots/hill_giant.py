# Fights the hill giants in Edgeville dungeon's pit, banking limpwurt roots and big bones at Varrock West:
# rs2b0t's HillGiant (MIT, see thirdparty/rs2b0t). It fetches the Brass key for the hut's shortcut first.

import math
import random
import time

from rs2004.catalogs import LOADOUT_SETTING, ContinueDialog, DeathRecovery, drop_db, food_count, food_forms, food_heal_amount, script_food, should_eat_to_use_food

TARGET = 'Giant'
# Why: the nav graph takes the Brass-key hut's ladder and keyed door when the key is held, and the public trapdoor
# otherwise, so there's no hard-coded route.
WEST_BANK = Tile(3185, 3440, 0)
PIT_RADIUS = 14
BIG_BONES = 'Big bones'
LIMPWURT = 'Limpwurt root'
BRASS_KEY = 'Brass key'
# Why: the dungeon tile of Edgeville dungeon's Brass key spawn, for the hut's shortcut.
KEY_SPAWN = Tile(3131, 9862, 0)
# Why: several bots on one world otherwise pile onto the same corner and starve each other of spawns, so a trip
# picks one at random.
PIT_SPOTS = [Tile(3110, 9832, 0), Tile(3117, 9835, 0), Tile(3103, 9836, 0), Tile(3113, 9841, 0), Tile(3120, 9843, 0)]
DEFAULT_LOOT = [LIMPWURT, BIG_BONES]
STYLE_RETRY_MS = 60000
FIGHT_MS = 90000

SETTINGS = {
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'weapon': SettingDef('string', '', 'Weapon to wield',
                         help='kept wielded, withdrawn from the bank when missing and re-worn after a death. Leave blank to fight with whatever you are already wearing.'),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 12, 'Food per trip', 1, 27, group='Food & healing'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up', options=drop_db().get(TARGET) or [], group='Banking & loot',
                       help='limpwurt roots and big bones by default; everything picked up is banked'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'bury_bones': SettingDef('boolean', False, 'Bury big bones', group='Banking & loot', help='bury Big bones for Prayer xp instead of banking them'),
    'loot_slots': SettingDef('number', 14, 'Bank after this many loot slots', 1, 27, group='Banking & loot'),
}


# The pure decisions, kept apart from the game so they can be tested without a client.

def pick_spot(rand, spots=None):
    """A pit spot from rand in [0, 1); rand is passed in so tests are exact."""
    if spots is None:
        spots = PIT_SPOTS
    if len(spots) == 0:
        raise RuntimeError('no pit spots configured')
    clamped = min(max(rand, 0), 0.999999)
    return spots[math.floor(clamped * len(spots))]


def trip_food_needed(food_in_pack, food_per_trip):
    """The food a trip must leave the bank with."""
    return max(0, food_per_trip - food_in_pack)


# Why: reaching the loot target ends the trip, and so does a full pack with no food left to free a slot. Out of
# food with HP where a full heal would fit, or below the safety floor, ends it too, since fighting on with an empty
# pack is how the bot dies: a lobster (12) at 40/53 HP with no food banks, because 40+12 is still under the max.
def should_bank_trip(free_slots, food_in_pack, loot_slots_target, used_loot_slots, hp, max_hp, heal):
    """Whether the trip should leave for the bank."""
    if used_loot_slots >= loot_slots_target:
        return True
    if free_slots == 0 and food_in_pack == 0:
        return True
    # Out of food, and it would eat if it had any: restock before dying.
    if food_in_pack == 0:
        return should_eat_to_use_food(hp, max_hp, heal, 1)
    return False


# Why: eating for space is worth it only while there's loot to pick up and the pack is full, and eating at full
# health purely to free a slot is the intent, so HP isn't part of it.
def should_eat_for_space(free_slots, food_in_pack):
    return free_slots == 0 and food_in_pack > 0


def bones_action(bury_bones):
    """Big bones are buried for prayer xp or banked, never both."""
    return 'bury' if bury_bones else 'bank'


def keep_on_deposit(food):
    """What a trip keeps in the pack when depositing."""
    return [food, BRASS_KEY]


# Why: counting on Attack counts a kill many times, since a dying giant stays attackable for several ticks and
# each loop clicks it again; health bars often read 0/0 until hit, so the giant leaving the scene is the signal.
def is_hill_giant_kill(still_present):
    """A kill counts only once the engaged giant has left the scene."""
    return not still_present


def hp_frac():
    top = skills.level('hitpoints')
    return skills.effective('hitpoints') / top if top > 0 else 1


def now_ms():
    return time.time() * 1000


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return (bot.need_eat() or should_eat_for_space(inventory.free(), bot.food_in_pack())) and bot.food_in_pack() > 0

    def execute(self):
        bot = self.bot
        forms = food_forms(bot.food_name)
        items = [i for i in inventory.items() if (i.name or '').lower() in forms]
        if len(items) == 0:
            return
        item = items[0]
        for_space = inventory.free() == 0 and not bot.need_eat()
        bot.status = f'eating {item.name} for a free slot' if for_space else f'eating {item.name} ({round(hp_frac() * 100)}% hp)'
        before = inventory.used()
        item.interact('Eat')
        yield from execution.delay_until(lambda: inventory.used() < before, 3000)


class GearEquip(Task):
    """Keeps the chosen weapon wielded, on the first trip and after a death."""

    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0

    def validate(self):
        weapon = self.bot.weapon
        return weapon != '' and self.fails < 5 and not equipment.contains(weapon) and inventory.contains(weapon)

    def execute(self):
        bot = self.bot
        weapon = bot.weapon
        bot.status = f'wielding {weapon}'
        wielded = yield from equipment.equip(weapon)
        if wielded:
            bot.log(f'wielded {weapon}')
            self.fails = 0
        else:
            self.fails += 1
            bot.log(f'could not wield {weapon} (attempt {self.fails}/5)')


class SetAttackStyle(Task):
    """The combat style isn't saved, so it's set again whenever the varp disagrees; style clicks are fine mid-fight."""

    def __init__(self, bot):
        Task.__init__(self, label='set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0
        self.announced = False

    def validate(self):
        return not game.has_combat_style(self.bot.melee_style) and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        style = bot.melee_style
        bot.status = 'setting combat style'
        game.set_combat_style(style)
        ok = yield from execution.delay_until(lambda: game.has_combat_style(style), 3000)
        if ok:
            self.fails = 0
            if not self.announced:
                self.announced = True
                resolution = game.combat_style_resolution(style)
                bot.log(f'combat style: {describe_combat_style(resolution) if resolution else style}')
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + STYLE_RETRY_MS
            bot.log(f"could not set melee style '{style}' (combat tab not ready?) — retrying in 60s")


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot

    def validate(self):
        return self.bot.bury_bones and inventory.contains(BIG_BONES)

    def execute(self):
        bones = inventory.first(BIG_BONES)
        if bones is None:
            return
        self.bot.status = 'burying big bones'
        before = inventory.count(BIG_BONES)
        bones.interact('Bury')
        buried = yield from execution.delay_until(lambda: inventory.count(BIG_BONES) < before, 4000)
        if buried:
            self.bot.buried += 1


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return should_bank_trip(inventory.free(), bot.food_in_pack(), bot.loot_slots, bot.loot_used(),
                                skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(bot.food_name))

    def execute(self):
        bot = self.bot
        food = bot.food_name
        bot.status = 'banking for food/loot'
        if not bot.has_brass_key():
            bot.log(f'need a {BRASS_KEY} before banking')
            return
        arrived = yield from bot.walk_to(WEST_BANK, 'the Varrock West bank')
        if not arrived:
            return
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            return
        keep = [n.lower() for n in keep_on_deposit(food)]
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() not in keep)
        needed = trip_food_needed(bot.food_in_pack(), bot.food_per_trip)
        weapon = bot.weapon
        if weapon != '' and not equipment.contains(weapon) and not inventory.contains(weapon):
            if bank.count(weapon) > 0:
                yield from bank.withdraw_x(weapon, 1)
            else:
                bot.log(f'no {weapon} banked to replace the lost one — fighting unarmed until one is banked')
        if needed > 0:
            if bank.count(food) == 0:
                yield from bank.close()
                bot.request_finish(f'out of {food} in the bank')
                return
            yield from bank.withdraw_x(food, needed)
        yield from bank.close()
        bot.trips += 1
        # A new spot each trip spreads bots around the pit.
        bot.reroll_spot()
        bot.log(f'trip {bot.loot_slots} slots banked; next spot {bot.spot}')


class GetKey(Task):
    def __init__(self, bot):
        Task.__init__(self, label='get key')
        self.bot = bot

    def validate(self):
        return not self.bot.has_brass_key()

    def execute(self):
        yield from self.bot.go_get_key()


class EnterPit(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter pit')
        self.bot = bot

    def validate(self):
        return not self.bot.in_pit()

    def execute(self):
        yield from self.bot.travel_to_pit()


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def find(self):
        wanted = self.bot.loot_set
        return ground_items.query().where(lambda g: (g.name or '').lower() in wanted).within(PIT_RADIUS).nearest()

    def validate(self):
        return self.bot.in_pit() and inventory.free() > 0 and self.find() is not None

    def execute(self):
        bot = self.bot
        drop = self.find()
        if drop is None:
            return
        bot.status = f'looting {drop.name}'
        before = inventory.used()
        drop.interact('Take')
        took = yield from execution.delay_until(lambda: inventory.used() > before, 4000)
        if took:
            bot.looted += 1
            bot.log(f'looted {drop.name}')


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.target_idx = None

    def living_target(self):
        spot = self.bot.spot
        return npcs.query().name(TARGET).action('Attack').where(
            lambda n: spot.distance_to(Tile(n.tile().x, n.tile().z, 0)) <= PIT_RADIUS and not n.targets_another_player() and not n.in_combat).nearest()

    def by_index(self, idx):
        for n in npcs.all():
            if n.index == idx and matches_entity_name(n.name, TARGET):
                return n
        return None

    def gone(self):
        return self.target_idx is not None and is_hill_giant_kill(self.by_index(self.target_idx) is not None)

    def validate(self):
        bot = self.bot
        if not bot.in_pit() or not bot.has_brass_key():
            self.target_idx = None
            return False
        # It keeps running once engaged, so the despawn is seen even if eating or looting came first.
        if self.target_idx is not None:
            return True
        return not game.in_combat() and self.living_target() is not None

    def execute(self):
        bot = self.bot
        if self.target_idx is None:
            giant = self.living_target()
            if giant is None:
                return
            bot.status = f'attacking {TARGET}'
            if not giant.interact('Attack'):
                return
            # Tracking starts only once the click lands, and never counts a kill here.
            self.target_idx = giant.index
            yield from execution.delay_until(lambda: game.in_combat() or self.by_index(self.target_idx) is None or chat_dialog.can_continue() or event_signal.pending(), 5000)
        if chat_dialog.can_continue() or event_signal.pending() or bot.died:
            self.target_idx = None
            return
        bot.status = 'fighting'
        deadline = now_ms() + FIGHT_MS
        while now_ms() < deadline:
            if event_signal.pending() or chat_dialog.can_continue() or bot.died:
                self.target_idx = None
                return
            if self.gone():
                bot.count_kill()
                self.target_idx = None
                yield from execution.delay_ticks(2)
                return
            # It gives way to eating, keeping target_idx so the next pass still counts the despawn.
            if bot.need_eat():
                return
            cur = self.by_index(self.target_idx) if self.target_idx is not None else None
            if cur is not None and not game.in_combat() and not cur.in_combat:
                yield from execution.delay_ticks(3)
                if self.gone():
                    bot.count_kill()
                self.target_idx = None
                return
            yield from execution.delay_ticks(2)
        self.target_idx = None


class HillGiant(TaskBot):
    def on_start(self):
        self.died = False
        self.kills = 0
        self.looted = 0
        self.buried = 0
        self.trips = 0
        self.status = 'starting'
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.weapon = s.str('weapon', '').strip()
        self.food_name = script_food(s, 'Trout')
        self.food_per_trip = s.num('food_withdraw', 12)
        self.bank_common = s.bool('bank_common_junk', True)
        self.bury_bones = s.bool('bury_bones', False)
        self.loot_slots = s.num('loot_slots', 14)
        self.loot_set = [n.lower() for n in s.list('loot', DEFAULT_LOOT)]
        if self.bury_bones and BIG_BONES.lower() not in self.loot_set:
            self.loot_set.append(BIG_BONES.lower())
        self.reroll_spot()
        self.started_at = time.time()
        self.log(f"HillGiant — {self.melee_style}, food '{self.food_name}' x{self.food_per_trip} (smart-eat), {bones_action(self.bury_bones)}ing big bones, spot {self.spot}")
        self.add(ContinueDialog(), DeathRecovery(self, self.spot, PIT_RADIUS, on_death=self.died_now, on_recovered=self.recovered, walk_back=self.travel_to_pit),
                 Eat(self), GearEquip(self), SetAttackStyle(self), BuryBones(self), GetKey(self), BankRun(self), EnterPit(self), LootCorpse(self), Fight(self))

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.log('died! walking back and re-wielding whatever gear survived')

    def recovered(self):
        self.died = False

    def recovery_anchor(self):
        return self.spot

    def grind_targets(self):
        return [TARGET.lower()]

    def count_kill(self):
        self.kills += 1
        self.log(f"giant down — {self.kills} kill{'' if self.kills == 1 else 's'}")

    # A fresh spot each trip keeps several bots off one corner.
    def reroll_spot(self):
        self.spot = pick_spot(random.random())

    def food_in_pack(self):
        return food_count(inventory.items(), self.food_name)

    def need_eat(self):
        n = self.food_in_pack()
        if n <= 0:
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food_name), n)

    def in_pit(self):
        here = game.tile()
        return here is not None and here.z > 9000 and self.spot.distance_to(here) <= PIT_RADIUS + 12

    def has_brass_key(self):
        return inventory.contains(BRASS_KEY)

    def loot_used(self):
        return inventory.used() - self.food_in_pack() - (1 if self.has_brass_key() else 0)

    def walk_to(self, dest, what):
        """Use with yield from."""
        here = game.tile()
        if here is not None and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= 3 and here.level == dest.level:
            return True
        self.status = f'walking to {what}'
        walked = yield from traversal.walk_resilient(dest, radius=3, attempts=6, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
        return walked

    def travel_to_pit(self):
        """The nav graph's route to the pit: the hut's ladder and keyed door with the key, else the trapdoor. Use with yield from."""
        if self.in_pit():
            walked = yield from self.walk_to(self.spot, 'the pit spot')
            return walked
        if not self.has_brass_key():
            got = yield from self.go_get_key()
            if not got:
                return False
        walked = yield from self.walk_to(self.spot, 'the giant pit')
        return walked

    def go_get_key(self):
        """Use with yield from."""
        self.log(f'no {BRASS_KEY} — going to fetch it')
        arrived = yield from self.walk_to(KEY_SPAWN, f'the {BRASS_KEY} spawn')
        if not arrived:
            self.log(f'could not reach the {BRASS_KEY} spawn')
            return False
        for _ in range(12):
            if self.has_brass_key():
                self.log(f'got the {BRASS_KEY}')
                return True
            drop = ground_items.query().name(BRASS_KEY).within(8).nearest()
            if drop is not None and drop.interact('Take'):
                took = yield from execution.delay_until(self.has_brass_key, 3000)
                if took:
                    return True
            else:
                self.log(f'no {BRASS_KEY} on the floor yet — waiting for the respawn')
            yield from execution.delay_ticks(5)
        self.log(f'could not obtain the {BRASS_KEY}')
        return False

    def on_progress_report(self):
        return {'Status': self.status, 'Kills': self.kills, 'Looted': self.looted, 'Buried': self.buried, 'Trips': self.trips,
                'Food': self.food_in_pack(), 'Loot slots': self.loot_used(), 'Spot': str(self.spot)}


BOT = define_bot(
    name='HillGiant',
    create=HillGiant,
    description='Edgeville dungeon hill giants — enters through the public trapdoor and banks limpwurt roots and big bones at Edgeville',
    category='Combat',
    tags=['combat', 'giants', 'edgeville', 'banking', 'looting'],
    settings_schema=SETTINGS,
)

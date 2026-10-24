# Fights the King Black Dragon with magic from the alcove beside the lair's exit lever, wearing the Dragonfire shield
# against the far fire: rs2b0t's JiveKBD (MIT, see thirdparty/rs2b0t), on the hunting framework. It walks the
# wilderness from Edgeville to the Lava Maze ladder, drinks a Superantipoison before the lever spiders, and teleports
# to Varrock to bank at Edgeville.

import time

from bots.jivekbd.entry import enter_kbd_lair, leave_kbd_lair
from bots.jivekbd.logic import ANTIPOISON_DOSES, POISONED, antipoison_plan, dose_to_drink
from bots.jivekbd.sites import KBD_LAIR, KBD_ROUTE, SITE_OPTIONS, site_for
from rs2004.catalogs import LOADOUT_SETTING, SPELL_DB, STAFFS, ContinueDialog, DeathRecovery, Record, casts_available, drop_db, food_count
from rs2004.catalogs import food_forms, food_heal_amount, is_food_item, script_food, should_eat_to_use_food, sustain
from rs2004.hunting import LOOT_GUARD, SHIELD, BankOpts, Fight, HoldSafespot, Retreat, WalkToSpot, bank_routine, escape_runes_for, guarded
from rs2004.hunting import loot_halts, site_tile_of, wants_drop

# The body is five wide and the drop lands on its south-west corner, so the pile can sit a few tiles past the range.
LOOT_RADIUS = 12
LOOT_BURST_MAX = 8
LOOT_SKIP_MS = 30000
LOOT_WAIT_MS = 4000
DRINK_MS = 4000
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
PARK_TICKS = 10
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic']
STYLE = 'mage'

DROPS = drop_db().get(KBD_LAIR.target) or []

SETTINGS = {
    'staff': SettingDef('string', 'Staff of fire', 'Staff', options=STAFFS, group='Combat',
                        help='one-handed, so the Dragonfire shield goes in the other hand. The shield caps the far fire at 15 and the run wears it every trip'),
    'spell': SettingDef('string', 'Fire Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat'),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 2000, group='Combat', help='the dragon has 240 hitpoints, so a kill is thirty to sixty casts'),
    'rune_buffer': SettingDef('number', 300, 'Spare runes per type', 0, 2000, group='Combat',
                              help='withdrawn on top of the cast budget. The dragon drops air, fire, blood, law and death runes'),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing',
                                help='the far fire lands about once every fourteen ticks under sustained casting, for up to 15 through the shield'),
    'doses_withdraw': SettingDef('number', 1, 'Superantipoison flasks per trip', 1, 4, group='Food & healing',
                                 help='one dose goes down on the surface before the ladder, since the poison spiders spawn on the lever tiles, and another whenever the poison line prints. A four-dose flask covers four trips'),
    'panic_hp': SettingDef('number', 30, 'Panic-to-bank below HP%', 1, 98, group='Food & healing', help='out of food and this low, the run teleports out for the bank'),
    'retreat_hp': SettingDef('number', 50, 'Retreat to a safespot below HP%', 0, 99, group='Food & healing',
                             help='off the safespot and this hurt, the run walks back to the alcove and heals there. An empty pack sends it back whatever the HP. 0 turns off both'),
    'food_reserve': SettingDef('number', 4, 'Food kept back from slot-freeing', 0, 27, group='Food & healing',
                               help='a full pack spends food to make room for loot instead of banking, never below this many'),
    'heal_to': SettingDef('number', 90, 'Heal to HP% before heading back', 10, 100, group='Food & healing',
                          help='the wilderness walk is long, so the trip eats up at the booth and tops the food back up after'),
    'loot': SettingDef('string[]', DROPS, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot', help='the King Black Dragon table. Everything picked up is banked'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'site': SettingDef('string', 'kbd-lair', 'Lair', options=SITE_OPTIONS, group='Location',
                       help='the lever in the Lava Maze dungeon, reached by the ladder at level 42 wilderness. The lair itself is not wilderness, so the Varrock teleport fires from inside it'),
    'safespot1': SettingDef('tile', KBD_LAIR.safespots[0], 'Safespot 1', group='Location',
                            help='the alcove south of the arrival tile: walled on the south, open north, and too narrow a row for the five-wide body to stand beside. The dragon still breathes at it from range'),
    'safespot2': SettingDef('tile', KBD_LAIR.safespots[1], 'Safespot 2', group='Location', help='the other alcove tile, taken when nothing is in range for 20s'),
    'bank_tile': SettingDef('tile', KBD_LAIR.bank, 'Bank stand tile', group='Location'),
    'tele_stock': SettingDef('number', 2, 'Spare escape casts', 0, 10, group='Location',
                             help='Varrock casts carried on top of the one needed to leave. When none will fire the run pulls the exit lever and walks out through the wilderness'),
    'log_detail': SettingDef('string', 'Normal', 'Log detail', options=['Normal', 'Verbose'], group='Diagnostics', help='Verbose adds the loot and slot-freeing traces'),
}

SPOT_KEYS = ['safespot1', 'safespot2']


def site_tile(bag, key, site):
    """The site's own tile, unless the setting has been moved off its schema default."""
    return site_tile_of(SETTINGS, bag, key, site)


def now_ms():
    return time.time() * 1000


def loot_key(g):
    return f'{g.name or ""}@{g.tile().x},{g.tile().z}'


def loot_stacks_into_pack(name):
    if not name:
        return False
    held = inventory.first(name)
    return held is not None and held.count > 1


def doses_held():
    return sum([inventory.count(name) for name in ANTIPOISON_DOSES])


class Parked(Task):
    def __init__(self, bot):
        Task.__init__(self, label='parked')
        self.bot = bot

    def validate(self):
        return self.bot.parked

    def execute(self):
        yield from execution.delay_ticks(PARK_TICKS)


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.need_eat()

    def execute(self):
        yield from self.bot.eat_once()


# Why: the poison varp never reaches the client, and the poisoning prints its line once per fresh poisoning, so the
# line is the only signal, and the mark moves past it whether or not a dose was there to answer it.
class CurePoison(Task):
    def __init__(self, bot):
        Task.__init__(self, label='cure poison')
        self.bot = bot
        self.mark = game_messages.mark()
        self.warned = False

    def validate(self):
        return game_messages.saw_since(self.mark, POISONED)

    def execute(self):
        bot = self.bot
        self.mark = game_messages.mark()
        bot.set_status('poisoned, drinking an antipoison')
        drank = yield from bot.drink_antipoison()
        if drank:
            bot.log('poisoned. Drank a Superantipoison')
            self.warned = False
            return
        if not self.warned:
            bot.log('WARNING: poisoned with no Superantipoison in the pack. The food covers it until the bank run.')
            self.warned = True


class GearEquip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def _missing(self):
        for name in [self.bot.weapon, SHIELD]:
            if name != '' and not equipment.contains(name) and inventory.first(name) is not None:
                return name
        return None

    def validate(self):
        return now_ms() >= self.retry_at and self._missing() is not None

    def execute(self):
        bot = self.bot
        item = self._missing()
        if item is None:
            return
        bot.set_status(f'equipping {item}')
        equipped = yield from equipment.equip(item)
        if equipped:
            bot.log(f'equipped {item}')
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not equip {item}. Retrying in {ASSERT_RETRY_MS // 1000}s.')


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if autocast.armed() or now_ms() < self.retry_at or bot.casts_left() < 1:
            return False
        return autocast.staff_tab_attached() or (bot.weapon != '' and equipment.contains(bot.weapon))

    def execute(self):
        bot = self.bot
        bot.set_status(f'arming autocast: {bot.spell}')
        yield from execution.delay_ticks(3)
        armed = yield from autocast.arm(bot.spell, lambda m: bot.log(m))
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}'. Retrying in {ASSERT_RETRY_MS // 1000}s.")


class PanicBank(Task):
    def __init__(self, bot):
        Task.__init__(self, label='panic bank')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not bot.parked and not bot.bank_empty and skills.hp_fraction() < bot.panic_at and not bot.has_food()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.set_status('panicking, retreating to the bank')
        bot.log(f'panic at {round(skills.hp_fraction() * 100)}% hp with no food. Banking.')
        yield from bot.bank_trip()


class FreeSlot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='free slot')
        self.bot = bot

    def validate(self):
        return self.bot.slot_action(self.bot.find_loot()) != 'none'

    def execute(self):
        yield from self.bot.free_slot()


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.parked:
            return False
        if not bot.shield_ready() and inventory.count(SHIELD) == 0:
            return True
        if not bot.has_food() and not bot.bank_empty:
            return True
        if bot.casts_left() < 1 and not bot.supply_empty:
            return True
        return inventory.is_full() and bot.food_count() <= bot.food_reserve

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.set_status('banking, restocking')
        bot.log(f'banking (food {bot.food_count()}, casts {bot.casts_left()}, doses {doses_held()})')
        yield from bot.bank_trip()


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not bot.too_hurt_to_loot() and not inventory.is_full() and bot.find_loot() is not None

    def execute(self):
        yield from self.bot.loot_burst()


class EnterLair(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter lair')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not bot.parked and bot.shield_ready() and not bot.site.in_area(game.tile()) and skills.hp_fraction() >= bot.panic_at

    def execute(self):
        yield from enter_kbd_lair(self.bot, self.bot.site, KBD_ROUTE)


class JiveKBD(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.bank_trips = 0
        self.looted = 0
        self.doses_drunk = 0
        self.last_dose_tick = None
        self.loot_counts = {}
        self.loot_skip = {}
        self.safespot_idx = 0
        self.parked = False
        self.park_reason = ''
        self.died = False
        self.target_idx = None
        self.bank_empty = False
        self.supply_empty = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        base = site_for(s.str('site', 'kbd-lair'))
        spots = []
        for i in range(len(base.safespots)):
            spots.append(site_tile(s, SPOT_KEYS[i] if i < len(SPOT_KEYS) else None, base.safespots[i]))
        self.site = base.with_changes(safespots=spots, bank=site_tile(s, 'bank_tile', base.bank))
        self.weapon = s.str('staff', 'Staff of fire')
        self.spell = s.str('spell', 'Fire Strike')
        self.food = script_food(s, 'Lobster')
        escape = escape_runes_for(self.site.escape_teleport_id).label
        self.panic_at = s.num('panic_hp', 30) / 100
        self.retreat_at = s.num('retreat_hp', 50) / 100
        self.rune_casts = s.num('runes_withdraw', 150)
        self.rune_buffer = s.num('rune_buffer', 300)
        self.food_withdraw_count = s.num('food_withdraw', 20)
        self.food_reserve = s.num('food_reserve', 4)
        self.doses = s.num('doses_withdraw', 1)
        self.escape_stock = s.num('tele_stock', 2)
        self.heal_to = s.num('heal_to', 90) / 100
        self.loot_set = set([n.lower() for n in s.list('loot', DROPS)])
        self.bank_common = s.bool('bank_common_junk', True)
        self.verbose = s.str('log_detail', 'Normal') == 'Verbose'
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in COMBAT_SKILLS])
        self.log(f"JiveKBD: {self.site.label}, {self.weapon} ({self.spell}) with the {SHIELD}, food '{self.food}' "
                 + f'(retreat<{round(self.retreat_at * 100)}%, panic<{round(self.panic_at * 100)}%), {self.doses} Superantipoison flask(s) a trip, '
                 + f'escape {escape}, bank {self.site.bank}')
        self.vlog(f"safespots [{' '.join([str(t) for t in self.site.safespots])}], loot [{', '.join(sorted(self.loot_set))}]")

        # Why: the hunting framework's waits, idle ticks and walks pump sustain, and with no hook none of them take a
        # bite while standing in the fire.
        def eat_if_needed():
            if self.need_eat():
                yield from self.eat_once()

        sustain.set(eat_if_needed)
        self.fight = Fight(self, self.site)
        self.add(
            Parked(self), ContinueDialog(),
            DeathRecovery(self, self.site.bank, 6, on_death=self.died_now, on_recovered=self.recovered),
            Retreat(self, self.site), Eat(self), CurePoison(self), GearEquip(self), ArmAutocast(self), PanicBank(self), FreeSlot(self),
            BankRun(self), LootCorpse(self), EnterLair(self), WalkToSpot(self, self.site), HoldSafespot(self, self.site), self.fight,
        )

    def died_now(self):
        self.died = True
        self.set_status('died, recovering')
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def recovery_anchor(self):
        return self.site.bank

    def grind_targets(self):
        return [self.site.target.lower()]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in COMBAT_SKILLS]) - self.xp_at_start
        report = {
            'Status': self.status,
            'Kills': self.kills,
            'Kills/hr': round(self.kills * 60 / minutes) if minutes > 0.5 else '-',
            'Looted': self.looted,
            'Bank trips': self.bank_trips,
            'Casts': self.casts_left(),
            'Food': self.food_count(),
            'Doses': f'{doses_held()} ({self.doses_drunk} drunk)',
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.parked:
            report['Parked'] = self.park_reason
        return report

    # The host the hunting framework drives

    def shield_ready(self):
        return equipment.contains(SHIELD)

    def set_status(self, text):
        self.status = text

    def vlog(self, message):
        if self.verbose:
            self.log(message)

    def park_for(self, reason):
        if self.parked:
            return
        self.parked = True
        self.park_reason = reason
        self.set_status('parked')
        self.log(f'PARKED: {reason}')

    def style(self):
        return STYLE

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return self.food_withdraw_count

    def weapon_name(self):
        return self.weapon

    def ammo_name(self):
        return ''

    def spell_name(self):
        return self.spell

    def keep_extra(self):
        return [SHIELD] + ANTIPOISON_DOSES

    def leave_by_walk(self):
        return False

    def hp_fraction(self):
        return skills.hp_fraction()

    def panic_hp(self):
        return self.panic_at

    def retreat_hp(self):
        return self.retreat_at

    def food_count(self):
        return food_count(inventory.items(), self.food)

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food), self.food_count())

    def eat_once(self):
        forms = food_forms(self.food)
        food = None
        for item in inventory.items():
            if (item.name or '').lower() in forms:
                food = item
                break
        if food is None:
            return False
        self.set_status(f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)')
        before = skills.effective('hitpoints')
        id = food.id
        count = inventory.count_by_id(id)
        if not food.interact('Eat'):
            return False
        ate = yield from execution.delay_until_ticks(lambda: inventory.count_by_id(id) < count or skills.effective('hitpoints') > before, 2)
        return ate

    def bury_bones(self):
        """The bones are banked with the rest of the pile, never buried in the fight."""
        return False

    def bone_name(self):
        return ''

    def safespot_index(self):
        return self.safespot_idx

    def set_safespot_index(self, n):
        self.safespot_idx = n

    def count_kill(self):
        self.kills += 1

    def count_burial(self):
        pass

    def count_bank_trip(self):
        self.bank_trips += 1

    def drink_antipoison(self):
        """Drinks the smallest antipoison flask held. False with none in the pack."""
        name = dose_to_drink(lambda n: inventory.count(n))
        dose = inventory.first(name) if name is not None else None
        if name is None or dose is None:
            return False
        before = doses_held() * 10 + inventory.count(name)
        if not dose.interact('Drink'):
            return False
        drank = yield from execution.delay_until(lambda: doses_held() * 10 + inventory.count(name) != before, DRINK_MS)
        if not drank:
            return False
        self.last_dose_tick = game.tick()
        self.doses_drunk += 1
        return True

    # Supplies and the bank

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def bank_opts(self):
        """Every setting bank_routine reads."""
        return BankOpts(withdraw_food=True, rune_casts=self.rune_casts, rune_buffer=self.rune_buffer, escape_stock=self.escape_stock, heal_to=self.heal_to,
                        potions=[], flasks=[antipoison_plan(self.doses)], wear=[SHIELD], leave=lambda h, site: leave_kbd_lair(self, site, KBD_ROUTE))

    def bank_trip(self):
        """Takes the trip, and notes what it came back with when it finished."""
        before = self.bank_trips
        yield from bank_routine(self, self.site, self.bank_opts())
        if self.bank_trips > before:
            self.note_trip(self.has_food(), self.casts_left() > 0)

    def note_trip(self, food, supplies):
        self.bank_empty = not food
        self.supply_empty = not supplies
        if not food:
            self.park_for(f"no '{self.food}' left in the bank after a full trip. The run stopped at the booth rather than walk the wilderness "
                          + 'with no way to heal. Deposit food, or point the loadout at food the bank has, and restart.')

    # Loot

    def loot_filter(self):
        return Record({'loot': self.loot_set, 'bank_common': self.bank_common, 'solve_clues': False, 'bury_bones': False, 'bone_name': ''})

    # Why: the pile lands where the dragon died and it respawns ninety seconds later on the same floor, so a drop
    # beside a live body is a walk into its melee.
    def find_loot(self):
        now = now_ms()
        bodies = [Record({'tile': n.tile(), 'size': n.size}) for n in npcs.query().name(self.site.target).within(LOOT_RADIUS + LOOT_GUARD).results()]
        f = self.loot_filter()
        return ground_items.query().where(lambda g: self.site.in_area(g.tile()) and self.loot_skip.get(loot_key(g), 0) < now
                                          and not guarded(g.tile(), bodies) and wants_drop(g, f)).within(LOOT_RADIUS).nearest()

    def slot_action(self, drop):
        """Trades a food slot for a loot slot: 'eat', 'drop' or 'none'."""
        if drop is None or not inventory.is_full() or loot_stacks_into_pack(drop.name):
            return 'none'
        if self.food_count() <= self.food_reserve:
            return 'none'
        return 'eat' if skills.hp_fraction() < 1 else 'drop'

    def free_slot(self):
        drop = self.find_loot()
        action = self.slot_action(drop)
        want = drop.name if drop is not None and drop.name else 'loot'
        self.vlog(f"slot check: {inventory.used()} used, {self.food} x{self.food_count()} (reserve {self.food_reserve}), "
                  + f"hp {round(skills.hp_fraction() * 100)}%, ground '{want}' -> {action}")
        if action == 'eat':
            self.log(f'pack full. Eating {self.food} to make room for {want}')
            yield from self.eat_once()
            return
        if action != 'drop':
            return
        food = None
        for item in inventory.items():
            if is_food_item(item.name, self.food):
                food = item
                break
        if food is None:
            return
        self.set_status(f'dropping {food.name} for pack space')
        self.log(f'pack full at full hp. Dropping {food.name} to make room for {want}')
        before = inventory.used()
        if food.interact('Drop'):
            yield from execution.delay_until(lambda: inventory.used() < before, 3000)

    def loot_once(self):
        drop = self.find_loot()
        if drop is None:
            return False
        name = drop.name or ''
        self.set_status(f'looting {name}')
        used_before = inventory.used()
        count_before = inventory.count(name)
        if not drop.interact('Take'):
            return False
        took = yield from execution.delay_until(lambda: inventory.used() > used_before or inventory.count(name) > count_before, LOOT_WAIT_MS)
        if took:
            self.looted += 1
            self.loot_counts[name] = self.loot_counts.get(name, 0) + 1
            self.log(f'looted {name}')
            return True
        self.loot_skip[loot_key(drop)] = now_ms() + LOOT_SKIP_MS
        self.log(f'could not pick up {name} at {drop.tile()}. Ignoring it for {LOOT_SKIP_MS // 1000}s.')
        return False

    def too_hurt_to_loot(self):
        return loot_halts(skills.hp_fraction(), self.panic_at, self.retreat_at)

    def loot_burst(self):
        """Clears the drop pile in one pass rather than one item per task hop."""
        for _ in range(LOOT_BURST_MAX):
            if event_signal.pending() or self.died or inventory.is_full() or self.need_eat() or self.too_hurt_to_loot() or self.find_loot() is None:
                return
            yield from self.loot_once()


BOT = define_bot(
    name='JiveKBD',
    create=JiveKBD,
    description='King Black Dragon with magic from the alcove beside the lair exit lever, wearing the Dragonfire shield against the far fire. Walks the wilderness from Edgeville to the Lava Maze ladder, drinks a Superantipoison before the lever spiders, and teleports to Varrock to bank.',
    category='Combat',
    tags=['kbd', 'dragon', 'safespot', 'wilderness', 'members', 'banking'],
    settings_schema=SETTINGS,
)

# Fights the black demons in Taverley Dungeon's pocket past the blue dragons, with range or magic from a safespot
# no demon can reach: rs2b0t's JiveDemons (MIT, see thirdparty/rs2b0t), on the hunting framework. It opens the
# dusty-key gate, fetching the key from Velrak when the bank has none, and banks at Falador West.

import time

from bots.jivedemons.sites import SITE_OPTIONS, TAVERLEY_BLACK_DEMON, site_for
from rs2004.catalogs import ARROWS, BOWS, LOADOUT_SETTING, SPELL_DB, STAFFS, ContinueDialog, DeathRecovery, Record, casts_available, drop_db
from rs2004.catalogs import food_count, food_forms, food_heal_amount, is_food_item, script_food, should_eat_to_use_food, sustain
from rs2004.hunting import LOOT_GUARD, BankOpts, Fight, HoldSafespot, Retreat, WalkToSpot, acquire_key, bank_routine, enter_lair
from rs2004.hunting import escape_runes_for, guarded, in_cell, key_status, leave_cell, loot_halts, site_tile_of, wants_drop

LOOT_RADIUS = 10
LOOT_BURST_MAX = 8
LOOT_SKIP_MS = 30000
LOOT_WAIT_MS = 4000
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
PARK_TICKS = 10
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic']

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}

DROPS = drop_db().get(TAVERLEY_BLACK_DEMON.target) or []
# Why: the coin pile is the most common drop and the demons die within a few tiles of the safespot, so coins stay
# ticked here where the blue dragon run leaves them.
DEFAULT_LOOT = [n for n in DROPS if n.lower() != 'ashes']

SETTINGS = {
    'combat_style': SettingDef('string', 'range', 'Combat style', options=['range', 'mage'],
                               help='both fight from a tile no demon can path to. A black demon only hunts within three tiles, so the run clicks each one and waits for it to close'),
    'staff': SettingDef('string', 'Staff of fire', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE),
    'spell': SettingDef('string', 'Fire Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 2000, group='Combat', show_if=SHOW_MAGE),
    'rune_buffer': SettingDef('number', 300, 'Spare runes per type', 0, 2000, group='Combat', show_if=SHOW_MAGE,
                              help='withdrawn on top of the cast budget. Black demons drop air, chaos, blood, fire and law runes, so looted runes let a trip cast past its budget and drain whichever rune is scarcest. When that is the law rune the escape teleport needs, the way home is the long walk out'),
    'bow': SettingDef('string', 'Maple shortbow', 'Bow', options=BOWS, group='Combat', show_if=SHOW_RANGE),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Iron arrow', 'Ammo', options=ARROWS, group='Combat', show_if=SHOW_RANGE),
    'ammo_withdraw': SettingDef('number', 500, 'Ammo per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 30, 'Panic-to-bank below HP%', 1, 98, group='Food & healing',
                           help='out of food and this low, the run leaves the dungeon for the bank'),
    'retreat_hp': SettingDef('number', 50, 'Retreat to a safespot below HP%', 0, 99, group='Food & healing',
                             help='off the safespot and this hurt, the run walks back to the nearest one and heals there. An empty pack sends it back whatever the HP, since nothing in the dungeon heals. 0 turns off both'),
    'food_reserve': SettingDef('number', 4, 'Food kept back from slot-freeing', 0, 27, group='Food & healing',
                               help='a full pack spends food to make room for loot instead of banking, never below this many'),
    'heal_to': SettingDef('number', 90, 'Heal to HP% before heading back', 10, 100, group='Food & healing',
                          help='the walk in is long, so the trip eats up at the booth and tops the food back up after'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot',
                       help='the black demon table. Everything picked up is banked. Ashes start unticked, since nothing pays for the slot'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'site': SettingDef('string', 'taverley-black-demon', 'Demon site', options=SITE_OPTIONS, group='Location',
                       help='the pocket past the blue dragons, behind the dusty-key gate. The walk in crosses the blue lair, where a baby blue aggresses below combat 97 and an adult within four tiles'),
    'safespot1': SettingDef('tile', TAVERLEY_BLACK_DEMON.safespots[0], 'Safespot 1', group='Location', help='derived off the collision pack as melee-proof with line of sight on a demon'),
    'safespot2': SettingDef('tile', TAVERLEY_BLACK_DEMON.safespots[1], 'Safespot 2', group='Location', help='the ladder rotates here when a hit lands, or when nothing is in range for 20s'),
    'safespot3': SettingDef('tile', TAVERLEY_BLACK_DEMON.safespots[2], 'Safespot 3', group='Location'),
    'bank_tile': SettingDef('tile', TAVERLEY_BLACK_DEMON.bank, 'Bank stand tile', group='Location'),
    'leave_via': SettingDef('string', 'teleport', 'Leave the dungeon by', options=['teleport', 'walk'],
                            option_labels={'teleport': 'Falador teleport', 'walk': 'Walk out through the gate'}, group='Location',
                            help='the teleport falls back to the gate walk when the runes or the magic level are short. Every other spell teleport lands further from the Falador West bank, so none is offered'),
    'tele_stock': SettingDef('number', 2, 'Spare escape casts', 0, 10, group='Location', help='casts carried on top of the one needed to leave'),
    'log_detail': SettingDef('string', 'Normal', 'Log detail', options=['Normal', 'Verbose'], group='Diagnostics',
                             help='Verbose adds the loot, slot-freeing and key-state traces'),
}

# The settings the safespot ladder is offered through. A site with more tiles keeps the rest of its own.
SPOT_KEYS = ['safespot1', 'safespot2', 'safespot3']


def site_tile(bag, key, site):
    """The site's own tile, unless the setting has been moved off its schema default."""
    return site_tile_of(SETTINGS, bag, key, site)


def now_ms():
    return time.time() * 1000


def loot_key(g):
    return f'{g.name or ""}@{g.tile().x},{g.tile().z}'


def loot_stacks_into_pack(name):
    """Loot that merges into a stack already held needs no slot."""
    if not name:
        return False
    held = inventory.first(name)
    return held is not None and held.count > 1


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


class GearEquip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def _missing(self):
        bot = self.bot
        for name in [bot.weapon, bot.ammo if bot.combat_style == 'range' else '']:
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


class SetAttackStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        return bot.combat_style == 'range' and game.combat_mode() != bot.range_mode and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        bot.set_status('setting the combat style')
        game.set_combat_mode(bot.range_mode)
        ok = yield from execution.delay_until(lambda: game.combat_mode() == bot.range_mode, 3000)
        if ok:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not set the {bot.combat_style} attack style. Retrying in {ASSERT_RETRY_MS // 1000}s.')


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.combat_style != 'mage' or autocast.armed() or now_ms() < self.retry_at or bot.casts_left() < 1:
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
        if not bot.has_food() and not bot.bank_empty:
            return True
        if bot.need_style_supplies() and not bot.supply_empty:
            return True
        # Why: food is a resource the run spends and FreeSlot turns it into room, so a pack full of food is no reason
        # to walk to Falador.
        return inventory.is_full() and bot.food_count() <= bot.food_reserve

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.set_status('banking, restocking')
        supplies = f', casts {bot.casts_left()}' if bot.combat_style == 'mage' else f', ammo {bot.ammo_left()}'
        bot.log(f'banking (food {bot.food_count()}{supplies})')
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


# Why: fetching from Velrak can leave the key in hand behind a cell door that won't open, a dead end nothing else
# walks out of.
class AcquireKey(Task):
    def __init__(self, bot):
        Task.__init__(self, label='acquire key')
        self.bot = bot

    def validate(self):
        bot = self.bot
        item = bot.site.key_item
        if item is None or bot.parked:
            return False
        return in_cell() or key_status(inventory.count_by_id(item.id), bank.count_by_id(item.id)) != 'held'

    def execute(self):
        bot = self.bot
        if in_cell():
            bot.set_status('leaving the jail cell')
            out = yield from leave_cell(bot)
            if not out:
                bot.log('the cell door would not open from the inside. Retrying.')
                return
            bot.log('out of the cell')
        bot.key_state = yield from acquire_key(bot, bot.site)
        bot.vlog(f'key state: {bot.key_state}')


class EnterLair(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter lair')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.parked or bot.site.in_area(game.tile()) or skills.hp_fraction() < bot.panic_at:
            return False
        return bot.site.key_item is None or inventory.count_by_id(bot.site.key_item.id) > 0

    def execute(self):
        yield from enter_lair(self.bot, self.bot.site)


class JiveDemons(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.bank_trips = 0
        self.looted = 0
        self.loot_counts = {}
        self.loot_skip = {}
        self.safespot_idx = 0
        self.key_state = 'fetch'
        self.parked = False
        self.park_reason = ''
        self.died = False
        self.target_idx = None
        self.bank_empty = False
        self.supply_empty = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        base = site_for(s.str('site', 'taverley-black-demon'))
        spots = []
        for i in range(len(base.safespots)):
            spots.append(site_tile(s, SPOT_KEYS[i] if i < len(SPOT_KEYS) else None, base.safespots[i]))
        self.site = base.with_changes(safespots=spots, bank=site_tile(s, 'bank_tile', base.bank))
        self.combat_style = s.str('combat_style', 'range')
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        self.spell = s.str('spell', 'Fire Strike')
        self.ammo = s.str('ammo', 'Iron arrow')
        self.weapon = s.str('staff', 'Staff of fire') if self.combat_style == 'mage' else s.str('bow', 'Maple shortbow')
        self.food = script_food(s, 'Lobster')
        self.leave_walk = s.str('leave_via', 'teleport') == 'walk'
        escape = 'walk out' if self.leave_walk else escape_runes_for(self.site.escape_teleport_id).label
        self.panic_at = s.num('panic_hp', 30) / 100
        self.retreat_at = s.num('retreat_hp', 50) / 100
        self.rune_casts = s.num('runes_withdraw', 150)
        self.rune_buffer = s.num('rune_buffer', 300)
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        self.food_withdraw_count = s.num('food_withdraw', 20)
        self.food_reserve = s.num('food_reserve', 4)
        self.escape_stock = s.num('tele_stock', 2)
        self.heal_to = s.num('heal_to', 90) / 100
        self.loot_set = set([n.lower() for n in s.list('loot', DEFAULT_LOOT)])
        # Why: fired arrows land where the demon dies and are on no drop table, so the 500 a trip withdraws come home
        # only if the loot set names them.
        if self.combat_style == 'range':
            self.loot_set.add(self.ammo.lower())
        self.bank_common = s.bool('bank_common_junk', True)
        self.verbose = s.str('log_detail', 'Normal') == 'Verbose'
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in COMBAT_SKILLS])
        item = self.site.key_item
        self.key_state = 'held' if item is None else key_status(inventory.count_by_id(item.id), bank.count_by_id(item.id))
        spell = f' ({self.spell})' if self.combat_style == 'mage' else ''
        self.log(f"JiveDemons: {self.site.label}, style {self.combat_style} w/ {self.weapon}{spell}, food '{self.food}' "
                 + f'(retreat<{round(self.retreat_at * 100)}%, panic<{round(self.panic_at * 100)}%), escape {escape}, bank {self.site.bank}')
        self.vlog(f"safespots [{' '.join([str(t) for t in self.site.safespots])}], loot [{', '.join(sorted(self.loot_set))}]")

        # Why: the hunting framework's waits, idle ticks and walks all pump sustain, and with no hook set none of
        # them take a bite while standing in the fight.
        def eat_if_needed():
            if self.need_eat():
                yield from self.eat_once()

        sustain.set(eat_if_needed)
        self.fight = Fight(self, self.site)
        self.add(
            Parked(self), ContinueDialog(),
            DeathRecovery(self, self.site.bank, 6, on_death=self.died_now, on_recovered=self.recovered),
            Retreat(self, self.site), Eat(self), GearEquip(self), SetAttackStyle(self), ArmAutocast(self), PanicBank(self), FreeSlot(self),
            BankRun(self), LootCorpse(self), AcquireKey(self), EnterLair(self), WalkToSpot(self, self.site), HoldSafespot(self, self.site), self.fight,
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
            'Looted': self.looted,
            'Bank trips': self.bank_trips,
            'Food': self.food_count(),
            'Key': self.key_state,
            'Safespot': self.safespot_idx,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.parked:
            report['Parked'] = self.park_reason
        return report

    # The host the hunting framework drives

    def set_status(self, text):
        self.status = text

    def vlog(self, message):
        """Silent unless log_detail is Verbose, so the log keeps what matters."""
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
        return self.combat_style

    def food_name(self):
        return self.food

    def food_withdraw(self):
        return self.food_withdraw_count

    def weapon_name(self):
        return self.weapon

    def ammo_name(self):
        return self.ammo

    def spell_name(self):
        return self.spell

    def keep_extra(self):
        return []

    def leave_by_walk(self):
        return self.leave_walk

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
        """Below the eat line with food in the pack. The fight reads a refused eat as an empty pack, so the food
        half of this matters."""
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
        """Demons drop ashes, so the fight never has a bone to bury."""
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

    # Supplies and the bank

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def quiver_count(self):
        wanted = self.ammo.lower()
        for item in equipment.items():
            if (item.name or '').lower() == wanted:
                return item.count
        return 0

    def ammo_left(self):
        return self.quiver_count() + inventory.count(self.ammo)

    def need_style_supplies(self):
        if self.combat_style == 'mage':
            return self.casts_left() < 1
        return self.combat_style == 'range' and self.ammo_left() == 0

    def bank_opts(self):
        """Every setting bank_routine reads."""
        return BankOpts(withdraw_food=True, rune_casts=self.rune_casts, rune_buffer=self.rune_buffer, ammo=self.ammo_withdraw, escape_stock=self.escape_stock,
                        heal_to=self.heal_to, potions=[])

    # Why: bank_routine counts a trip only where it runs to the end, so the counter moving is what tells an empty bank
    # from a walk that never got there.
    def bank_trip(self):
        """Takes the trip, and notes what it came back with when it finished."""
        before = self.bank_trips
        yield from bank_routine(self, self.site, self.bank_opts())
        if self.bank_trips > before:
            self.note_trip(self.has_food(), not self.need_style_supplies())

    # Why: a finished trip with no food is the one state the run can't fix from inside, so it stops at the booth
    # rather than walking back unable to heal; a supply shortfall clears on the next trip, which a full pack forces.
    def note_trip(self, food, supplies):
        self.bank_empty = not food
        self.supply_empty = not supplies
        if not food:
            self.park_for(f"no '{self.food}' left in the bank after a full trip. The run stopped at the booth rather than walk back to the demons "
                          + 'with no way to heal. Deposit food, or point the loadout at food the bank has, and restart.')

    # Loot

    def loot_filter(self):
        return Record({'loot': self.loot_set, 'bank_common': self.bank_common, 'solve_clues': False, 'bury_bones': False, 'bone_name': ''})

    def find_loot(self):
        now = now_ms()
        demons = [Record({'tile': n.tile(), 'size': n.size}) for n in npcs.query().name(self.site.target).within(LOOT_RADIUS + LOOT_GUARD).results()]
        f = self.loot_filter()
        return ground_items.query().where(lambda g: self.site.in_area(g.tile()) and self.loot_skip.get(loot_key(g), 0) < now
                                          and not guarded(g.tile(), demons) and wants_drop(g, f)).within(LOOT_RADIUS).nearest()

    # Why: eating wins while the heal isn't wasted and at full hp the food is dropped instead, so a full pack buys a
    # loot slot rather than the walk to Falador; the reserve is never dug into.
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
        # Why: a stackable drop merges into a slot already held, so used() alone never moves for the coins, runes and
        # arrows that are most of this table.
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
    name='JiveDemons',
    create=JiveDemons,
    description='Taverley Dungeon black demons: mage or range from a derived safespot in the pocket past the blue dragons. Opens the dusty-key gate, fetching the key off Velrak when the bank has none.',
    category='Combat',
    tags=['taverley', 'demons', 'safespot', 'members', 'banking'],
    settings_schema=SETTINGS,
)

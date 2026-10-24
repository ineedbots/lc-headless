# Fights the moss giants north of Ardougne, from a safespot with range or magic or toe to toe with melee, and banks
# all the loot at Ardougne North: rs2b0t's MossGiant (MIT, see thirdparty/rs2b0t).

import time

from rs2004.catalogs import CUSTOM_RANGED_SETTINGS, LOADOUT_SETTING, RANGED_WEAPONS, SPELL_DB, STAFFS, ContinueDialog, DeathRecovery
from rs2004.catalogs import bury_one_in_fight, casts_available, combat_keep_names, drop_db, food_count, food_forms, food_heal_amount
from rs2004.catalogs import range_loadout_of, range_supply_empty, ranged_item, rune_withdraw_list, script_food, should_eat_to_use_food

TARGET = 'Moss giant'
DEFAULT_SAFESPOT = Tile(2553, 3406, 0)
DEFAULT_BANK = Tile(2615, 3332, 0)
FIELD_RADIUS = 10
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
XP_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}


def _default_loot(name):
    words = name.lower().split(' ')
    return 'arrow' not in words and name.lower() != 'coal' and 'spinach roll' not in name.lower()


DROPS = drop_db().get(TARGET) or []
DEFAULT_LOOT = [n for n in DROPS if _default_loot(n)]

SETTINGS = {
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range']),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'staff': SettingDef('string', 'Staff of air', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE, help='wielded staff, withdrawn from bank when missing'),
    'spell': SettingDef('string', 'Wind Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE),
    'bow': SettingDef('string', 'Maple shortbow', 'Ranged weapon', options=RANGED_WEAPONS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                      help='bows use the selected ammo; darts are both the weapon and the projectile stack'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Iron arrow', 'Bow ammo', options=['Bronze arrow', 'Iron arrow', 'Steel arrow', 'Mithril arrow', 'Adamant arrow', 'Rune arrow', 'Other'],
                       group='Combat', show_if=SHOW_RANGE, help='used by bows; ignored when the ranged weapon is a dart'),
}
SETTINGS.update(CUSTOM_RANGED_SETTINGS)
SETTINGS.update({
    'ammo_withdraw': SettingDef('number', 500, 'Projectiles per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 25, 'Panic-to-bank below HP%', 1, 98, group='Food & healing',
                           help='retreat to the bank when HP drops this low (out of food, or damage outpacing eating)'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot',
                       help='the moss giant drop table; ticked drops get grabbed. Everything picked up is banked — the bank keeps only food/runes/ammo/weapon.'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'bury_bones': SettingDef('boolean', False, 'Bury big bones', group='Banking & loot',
                             help='bury Big bones for Prayer xp instead of banking them (always looted when on)'),
    'safespot_tile': SettingDef('tile', DEFAULT_SAFESPOT, 'Safespot / field tile', group='Location'),
    'bank_tile': SettingDef('tile', DEFAULT_BANK, 'Bank stand tile (Ardougne N)', group='Location'),
})


def now_ms():
    return time.time() * 1000


def withdraw_op(need):
    return 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')


def withdraw_to(name, target):
    """Tops the pack up to target of name; how many arrived. Use with yield from."""
    start = inventory.count(name)
    for _ in range(40):
        if inventory.count(name) >= target or inventory.is_full():
            break
        before = inventory.count(name)
        need = target - before
        if need > 10:
            taken = yield from bank.withdraw_x(name, need)
            if taken:
                if inventory.count(name) > before:
                    continue
                break
        bank.withdraw(name, withdraw_op(need))
        landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
        if not landed:
            break
    return inventory.count(name) - start


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.should_eat_now()

    def execute(self):
        bot = self.bot
        yield from bot.eat_once(bot.need_eat_for_loot() and not bot.need_eat())


class GearEquip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0

    def _need_weapon(self):
        bot = self.bot
        # Darts are the projectile stack, which _need_quiver handles.
        if bot.style == 'range' and bot.range_loadout().thrown:
            return False
        return bot.weapon != '' and not equipment.contains(bot.weapon) and inventory.first(bot.weapon) is not None

    def _need_quiver(self):
        bot = self.bot
        if bot.style != 'range':
            return False
        return inventory.count(bot.range_projectile()) > 0 and bot.equipped_projectile_count() == 0

    def validate(self):
        return self.bot.style != 'melee' and self.fails < 5 and (self._need_weapon() or self._need_quiver())

    def execute(self):
        bot = self.bot
        if self._need_weapon():
            bot.status = f'wielding {bot.weapon}'
            wielded = yield from equipment.equip(bot.weapon)
            if wielded:
                bot.log(f'wielded {bot.weapon}')
                self.fails = 0
            else:
                self.fails += 1
            return
        projectile = bot.range_projectile()
        bot.status = f'equipping {projectile}'
        equipped = yield from bot.equip_pack_projectiles()
        if equipped:
            bot.log(f'equipped {projectile}')
            self.fails = 0
        else:
            self.fails += 1


class SetAttackStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def _selected(self):
        bot = self.bot
        return game.combat_mode() == bot.range_mode if bot.style == 'range' else game.has_combat_style(bot.melee_style)

    def validate(self):
        return self.bot.style != 'mage' and not self._selected() and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        bot.status = 'setting combat style'
        if bot.style == 'range':
            game.set_combat_mode(bot.range_mode)
        else:
            game.set_combat_style(bot.melee_style)
        ok = yield from execution.delay_until(lambda: self._selected(), 3000)
        if ok:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not set the {bot.style} attack style (combat tab not ready?) — retrying in {ASSERT_RETRY_MS // 1000}s')


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.style != 'mage' or autocast.armed() or now_ms() < self.retry_at:
            return False
        if bot.casts_left() < 1:
            return False
        return autocast.staff_tab_attached() or (bot.weapon != '' and equipment.contains(bot.weapon))

    def execute(self):
        bot = self.bot
        bot.status = f'arming autocast: {bot.spell}'
        yield from execution.delay_ticks(3)
        armed = yield from autocast.arm(bot.spell, lambda m: bot.log(m))
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}' — retrying in {ASSERT_RETRY_MS // 1000}s (check spell/level/staff).")


class PanicBank(Task):
    def __init__(self, bot):
        Task.__init__(self, label='panic bank')
        self.bot = bot

    def validate(self):
        return skills.hp_fraction() < self.bot.panic_hp and not self.bot.has_food()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.status = 'panic — retreating to the bank'
        bot.log(f'panic at {round(skills.hp_fraction() * 100)}% hp — banking for food')
        yield from bot.bank_routine(True)


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot

    def validate(self):
        return self.bot.bury_bones and inventory.contains('Big bones')

    def execute(self):
        bot = self.bot
        bones = inventory.first('Big bones')
        if bones is None:
            return
        bot.status = 'burying big bones'
        before = inventory.used()
        if not bones.interact('Bury'):
            bot.log(f"no Bury op on big bones? ops=[{', '.join(bones.actions())}]")
            yield from execution.delay_ticks(2)
            return
        buried = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
        if buried:
            bot.buried += 1


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.need_style_supplies() and not bot.supply_empty:
            return True
        if not bot.has_food() and not bot.bank_empty:
            return True
        # Eating a food for loot space beats an early bank run when drops wait.
        if inventory.is_full() and bot.has_food() and bot.find_loot() is not None:
            return False
        return inventory.is_full()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.status = 'banking — restocking'
        casts = f', casts {bot.casts_left()}' if bot.style == 'mage' else ''
        ammo = f', projectiles {bot.equipped_projectile_count() + inventory.count(bot.range_projectile())}' if bot.style == 'range' else ''
        bot.log(f'banking (food {bot.food_count()}{casts}{ammo})')
        yield from bot.bank_routine(True)


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        return not inventory.is_full() and self.bot.find_loot() is not None

    def execute(self):
        yield from self.bot.loot_once()


class ReturnToSafespot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to safespot')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.uses_safespot() and not bot.at_safespot() and skills.hp_fraction() >= bot.panic_hp

    def execute(self):
        bot = self.bot
        bot.status = 'returning to the safespot'
        yield from traversal.walk_resilient(bot.safespot, radius=0, attempts=4, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.target_idx = None
        self.skip = {}

    def validate(self):
        bot = self.bot
        if skills.hp_fraction() < bot.panic_hp:
            return False
        if bot.uses_safespot() and not bot.at_safespot():
            return False
        return len(bot.field_giants()) > 0

    def execute(self):
        bot = self.bot
        bot.status = 'fighting moss giants'
        deadline = now_ms() + 120000
        while now_ms() < deadline:
            if event_signal.pending() or bot.died or chat_dialog.can_continue():
                return
            if bot.should_eat_now():
                yield from bot.eat_once(bot.need_eat_for_loot() and not bot.need_eat())
                continue
            if skills.hp_fraction() < bot.panic_hp:
                return
            giants = bot.field_giants()
            if self.target_idx is not None and len([g for g in giants if g.index == self.target_idx]) == 0:
                bot.kills += 1
                bot.log(f'moss giant down — {bot.kills} kills')
                self.target_idx = None
            if not inventory.is_full() and bot.find_loot() is not None:
                yield from bot.loot_once()
                continue
            if bot.uses_safespot() and not bot.at_safespot():
                back = yield from bot.quick_return_to_safespot()
                if not back:
                    return
                continue
            # Why: this loop owns the bot for the fight, so a sibling BuryBones task only runs in the gaps it leaves.
            # Why: the burial skips the swing tick, so it costs no attack.
            if bot.bury_bones:
                buried = yield from bury_one_in_fight('Big bones')
                if buried:
                    bot.buried += 1
            if game.in_combat():
                yield from execution.delay_ticks(2)
                continue
            now = now_ms()
            choices = [g for g in giants if not bot.uses_safespot() or self.skip.get(g.index, 0) < now]
            choices.sort(key=lambda g: g.distance())
            if not choices:
                yield from execution.delay_ticks(2)
                return
            target = choices[0]
            target.interact('Attack')
            self.target_idx = target.index
            yield from execution.delay_until(lambda: game.in_combat() or (bot.uses_safespot() and not bot.at_safespot()) or len(bot.field_giants()) == 0, 3000)
            if bot.uses_safespot() and not bot.at_safespot():
                self.skip[target.index] = now + 8000
                self.target_idx = None


class MossGiant(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.looted = 0
        self.buried = 0
        self.bank_trips = 0
        self.loot_counts = {}
        self.supply_empty = False
        self.bank_empty = False
        self.died = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.style = s.str('combat_style', 'melee')
        self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        self.spell = s.str('spell', 'Wind Strike')
        self.ammo = ranged_item(s, 'ammo', 'Iron arrow') if self.style == 'range' else ''
        if self.style == 'mage':
            self.weapon = s.str('staff', 'Staff of air')
        elif self.style == 'range':
            self.weapon = ranged_item(s, 'bow', 'Maple shortbow')
        else:
            self.weapon = ''
        self.food_name = script_food(s, 'Lobster')
        self.panic_hp = s.num('panic_hp', 25) / 100
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        self.food_withdraw = s.num('food_withdraw', 20)
        self.loot_set = set([n.lower() for n in s.list('loot', DEFAULT_LOOT)])
        self.bank_common = s.bool('bank_common_junk', True)
        self.bury_bones = s.bool('bury_bones', False)
        if self.bury_bones:
            self.loot_set.add('big bones')
        self.safespot = s.tile('safespot_tile', DEFAULT_SAFESPOT)
        self.bank_tile = s.tile('bank_tile', DEFAULT_BANK)
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in XP_SKILLS])
        loadout = self.range_loadout()
        if self.style == 'range':
            note = f" darts '{loadout.projectile}'" if loadout.thrown else f" bow '{loadout.weapon}' + '{loadout.projectile}'"
        elif self.style == 'mage':
            note = f' w/ {self.weapon} ({self.spell})'
        else:
            note = f' ({self.melee_style})'
        burying = ', burying big bones' if self.bury_bones else ''
        self.log(f"MossGiant — style {self.style}{note}, food '{self.food_name}' (smart-eat, panic<{round(self.panic_hp * 100)}%), "
                 + f'safespot {self.safespot}, bank {self.bank_tile}{burying}')
        self.add(
            ContinueDialog(),
            DeathRecovery(self, self.safespot, 6, on_death=self.died_now, on_recovered=self.recovered),
            Eat(self), GearEquip(self), SetAttackStyle(self), ArmAutocast(self), PanicBank(self), BuryBones(self), BankRun(self),
            LootCorpse(self), ReturnToSafespot(self), Fight(self),
        )

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def recovery_anchor(self):
        return self.safespot

    def grind_targets(self):
        return [TARGET.lower()]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in XP_SKILLS]) - self.xp_at_start
        return {
            'Status': self.status,
            'Style': self.style,
            'Kills': self.kills,
            'Looted': self.looted,
            'Buried': self.buried,
            'Bank trips': self.bank_trips,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }

    # Food

    def food_count(self):
        return food_count(inventory.items(), self.food_name)

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food_name), 1)

    def need_eat_for_loot(self):
        """A full pack with food in it and loot on the ground eats to free a slot rather than banking early."""
        return inventory.is_full() and self.has_food() and self.find_loot() is not None

    def should_eat_now(self):
        return self.need_eat() or self.need_eat_for_loot()

    def eat_once(self, for_loot=False):
        forms = food_forms(self.food_name)
        food = None
        for item in inventory.items():
            if (item.name or '').lower() in forms:
                food = item
                break
        if food is None:
            return False
        self.status = f'eating {food.name} for a free slot' if for_loot else f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
        before_hp = skills.effective('hitpoints')
        before_used = inventory.used()
        food.interact('Eat')
        # HP may not rise when already full; a free slot is the space eat's signal.
        ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before_hp or inventory.used() < before_used, 3000)
        return ate

    # Style supplies

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def range_loadout(self):
        return range_loadout_of(self.weapon, self.ammo)

    def range_projectile(self):
        return self.range_loadout().projectile

    def equipped_projectile_count(self):
        projectile = self.range_projectile().lower()
        for item in equipment.items():
            if (item.name or '').lower() == projectile:
                return item.count
        return 0

    def need_style_supplies(self):
        if self.style == 'mage':
            return self.casts_left() < 1
        if self.style == 'range':
            return range_supply_empty(self.equipped_projectile_count(), inventory.count(self.range_projectile()), 0)
        return False

    def equip_pack_projectiles(self):
        projectile = self.range_projectile()
        item = inventory.first(projectile)
        if item is None:
            return True
        op = None
        for option in item.actions():
            lower = option.lower()
            if 'wield' in lower or 'wear' in lower or 'equip' in lower:
                op = option
                break
        if op is None:
            return False
        before = inventory.count(projectile)
        item.interact(op)
        equipped = yield from execution.delay_until(lambda: inventory.count(projectile) < before, 3000)
        return equipped

    # The field

    def in_field(self, tile):
        return self.safespot.distance_to(tile) <= FIELD_RADIUS

    def at_safespot(self):
        here = game.tile()
        return here is not None and here.equals(self.safespot)

    def uses_safespot(self):
        return self.style == 'mage' or self.style == 'range'

    def field_giants(self):
        return npcs.query().name(TARGET).where(lambda n: self.in_field(n.tile()) and not n.targets_another_player()).results()

    def find_loot(self):
        def wanted(g):
            name = (g.name or '').lower()
            return name in self.loot_set or (self.bank_common and matches_common_bank_loot(g.name or '', g.id))

        return ground_items.query().where(wanted).within(FIELD_RADIUS).nearest()

    def keep_names(self):
        projectile = self.range_projectile() if self.style == 'range' else self.ammo
        weapon = projectile if self.style == 'range' and self.range_loadout().thrown else self.weapon
        return combat_keep_names(self.food_name, self.style, spell=self.spell, ammo=projectile, weapon=weapon, extra=['Coins'])

    def quick_return_to_safespot(self):
        self.status = 'returning to the safespot'
        for _ in range(3):
            if self.at_safespot() or event_signal.pending():
                break
            direct_navigator.walk(self.safespot)
            back = yield from execution.delay_until(lambda: self.at_safespot(), 4000)
            if back:
                break
        return self.at_safespot()

    def loot_once(self):
        drop = self.find_loot()
        if drop is None:
            return False
        self.status = f'looting {drop.name}'
        before = inventory.used()
        drop.interact('Take')
        took = yield from execution.delay_until(lambda: inventory.used() > before, 4000)
        if took:
            self.looted += 1
            if drop.name:
                self.loot_counts[drop.name] = self.loot_counts.get(drop.name, 0) + 1
            self.log(f'looted {drop.name}')
            return True
        return False

    # The bank

    def bank_routine(self, withdraw_food):
        say = lambda m: self.log(f'  {m}')
        arrived = yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=6, timeout_ms=240000, log=say)
        if not arrived:
            self.log('walk to the bank failed — will retry')
            return
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank — will retry')
            return
        yield from bank.deposit_all_matching(deposit_all_except(self.keep_names()))
        if withdraw_food:
            self.status = f'withdrawing {self.food_name}'
            for _ in range(12):
                if self.food_count() >= self.food_withdraw or inventory.is_full():
                    break
                need = self.food_withdraw - self.food_count()
                before = self.food_count()
                bank.withdraw(self.food_name, withdraw_op(need))
                landed = yield from execution.delay_until(lambda: self.food_count() > before, 2500)
                if not landed:
                    break
            if self.food_count() == 0:
                self.bank_empty = True
                self.log(f"WARNING: no '{self.food_name}' in the bank — carrying on without food. Deposit food (or fix the name) to resume eating.")
            else:
                self.bank_empty = False
        yield from self.withdraw_style_supplies()
        self.bank_trips += 1
        self.status = 'restocked — walking back to the safespot'
        yield from traversal.walk_resilient(self.safespot, radius=0 if self.uses_safespot() else 3, attempts=6, timeout_ms=240000, log=say)

    def withdraw_style_supplies(self):
        # Darts are the projectile stack, not a weapon kept, so they're restocked below.
        need_weapon = self.style != 'melee' and self.weapon != '' and not (self.style == 'range' and self.range_loadout().thrown) \
            and not equipment.contains(self.weapon) and inventory.first(self.weapon) is None
        if need_weapon:
            self.status = f'withdrawing {self.weapon}'
            got = yield from withdraw_to(self.weapon, 1)
            if got > 0:
                yield from equipment.equip(self.weapon)
                self.log(f'withdrew and wielded {self.weapon}')
            else:
                self.log(f"WARNING: no '{self.weapon}' in the bank — carrying on with current gear.")
        if self.style == 'mage':
            self.status = 'withdrawing runes'
            for row in rune_withdraw_list(self.spell, self.wielded_names(), self.runes_withdraw):
                rune = row['rune']
                count = row['count']
                if inventory.count(rune) < count:
                    got = yield from withdraw_to(rune, count)
                    self.log(f'withdrew {got} {rune} ({inventory.count(rune)}/{count})')
            if self.casts_left() < 1:
                self.supply_empty = True
                self.log(f"WARNING: bank can't supply a single '{self.spell}' cast — deposit runes to resume.")
            else:
                self.supply_empty = False
        elif self.style == 'range':
            projectile = self.range_projectile()
            self.status = f'withdrawing {projectile}'
            got = yield from withdraw_to(projectile, self.ammo_withdraw)
            if got > 0:
                # The bank modal blocks the equip.
                closed = yield from bank.close()
                equipped = False
                if closed:
                    equipped = yield from self.equip_pack_projectiles()
                if not equipped:
                    self.log(f'WARNING: withdrew {projectile}, but could not equip the stack — will retry from the pack')
                self.log(f'withdrew {got} {projectile} — {self.equipped_projectile_count()} equipped')
                self.supply_empty = False
            elif self.equipped_projectile_count() == 0 and inventory.count(projectile) == 0:
                self.supply_empty = True
                self.log(f"WARNING: no '{projectile}' in the bank — deposit projectiles to resume.")


BOT = define_bot(
    name='MossGiant',
    create=MossGiant,
    description='Moss giants N of Ardougne: range/mage safespot or melee, banks all loot',
    category='Combat',
    tags=['ardougne', 'safespot', 'afk'],
    settings_schema=SETTINGS,
)

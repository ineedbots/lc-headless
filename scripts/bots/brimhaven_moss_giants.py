# Fights the moss giants on Brimhaven's island, walking to them in the multicombat field, and banks all the loot at
# Ardougne South, sailing both ways with Captain Barnaby: rs2b0t's BrimhavenMossGiants (MIT, see thirdparty/rs2b0t),
# its twelve files in one. A phase (travel, fight, loot, bury or bank) decides which tasks run.

import time

from rs2004.catalogs import ARROWS, BOLTS, CROSSBOWS, CUSTOM_RANGED_SETTINGS, FOOD_OPTIONS, RANGED_WEAPONS, SPELL_DB, STAFFS, ContinueDialog
from rs2004.catalogs import DeathRecovery, casts_available, combat_keep_names, drop_db, food_count, food_forms, food_heal_amount
from rs2004.catalogs import range_loadout_of, range_supply_empty, ranged_item, rune_withdraw_list, should_eat_to_use_food

TARGET = 'Moss giant'
# Brimhaven's moss giant island, fought walk-and-fight in multicombat.
FIELD_TILE = Tile(2698, 3206, 0)
# Ardougne's south-east bank by Captain Barnaby's pier, where the boat leaves.
BANK_TILE = Tile(2655, 3283, 0)
# Beside Captain Barnaby, so the way out can't plan through the wrong port.
PIER_TILE = Tile(2683, 3272, 0)
# Ardougne to Brimhaven, each way.
BOAT_FARE = 30
FIELD_RADIUS = 10
# How far from the field tile the bot roams to find and engage moss giants.
HUNT_RADIUS = 25
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
XP_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']

# The phases.
TRAVEL = 'travel'
FIGHT = 'fight'
LOOT = 'loot'
BURY = 'bury'
BANK = 'bank'

# The strip west of Captain Barnaby, x >= 2780, that a route to the field must avoid so it never takes the Port
# Sarim, Musa Point or Thresnor boat.
WRONG_BOAT_ZONE = {'min_x': 2780, 'max_x': 3040, 'min_z': 3130, 'max_z': 3330}


def _default_loot(name):
    lower = name.lower()
    return 'arrow' not in lower.split(' ') and lower != 'coal' and 'spinach roll' not in lower


DROPS = drop_db().get(TARGET) or []
DEFAULT_LOOT = [n for n in DROPS if _default_loot(n)]

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}

SETTINGS = {
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range']),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'staff': SettingDef('string', 'Staff of air', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE, help='wielded staff, withdrawn from bank when missing'),
    'spell': SettingDef('string', 'Wind Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE),
    'bow': SettingDef('string', 'Maple shortbow', 'Ranged weapon', options=RANGED_WEAPONS + CROSSBOWS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                      help='bows use an arrow, crossbows use a bolt (see ammo); darts are both the weapon and the projectile stack'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Iron arrow', 'Ammo (arrows / bolts)', options=ARROWS + BOLTS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                       help='arrows for bows, bolts for crossbows; ignored when the ranged weapon is a dart'),
}
SETTINGS.update(CUSTOM_RANGED_SETTINGS)
SETTINGS.update({
    'ammo_withdraw': SettingDef('number', 500, 'Projectiles per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'loot_ammo': SettingDef('boolean', True, 'Loot & re-equip ammo', group='Combat', show_if=SHOW_RANGE,
                            help='pick up dropped arrows/bolts in the loot phase and re-equip them before fighting'),
    'food': SettingDef('string', 'Lobster', 'Food', options=FOOD_OPTIONS, group='Food & healing'),
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'loot_cake': SettingDef('boolean', False, 'Loot & eat slice of cake', group='Food & healing',
                            help='also grab and eat Slice of cake in addition to the selected food (looted when on)'),
    'panic_hp': SettingDef('number', 25, 'Panic-to-bank below HP%', 1, 98, group='Food & healing',
                           help='retreat to the bank when HP drops this low (out of food, or damage outpacing eating)'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot',
                       help='the moss giant drop table; ticked drops get grabbed. Everything picked up is banked — the bank keeps only food/runes/ammo/weapon.'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'bury_bones': SettingDef('boolean', False, 'Bury big bones', group='Banking & loot',
                             help='bury Big bones for Prayer xp instead of banking them (always looted when on)'),
    'field_tile': SettingDef('tile', FIELD_TILE, 'Field / fight tile (Brimhaven island)', group='Location'),
    'bank_tile': SettingDef('tile', BANK_TILE, 'Bank stand tile (Ardougne S, by the pier)', group='Location'),
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


def edible_at_bank(name, food_name):
    """Food to eat at the bank: the food's forms, or a part-eaten cake, pizza or pie, so healing never stalls."""
    n = (name or '').lower()
    if n in food_forms(food_name):
        return True
    words = n.split(' ')
    for i in range(len(words) - 1):
        part = words[i]
        if len(part) == 3 and part[1] == '/' and part[0] in '0123456789' and part[2] in '0123456789' and words[i + 1] in ['cake', 'pizza', 'pie']:
            return True
    return n == 'slice of cake' or n == 'chocolate slice'


def route_uses_wrong_boat(names):
    for name in names:
        n = name.lower()
        if 'thresnor' in n or 'musa' in n or 'port sarim' in n:
            return True
    return False


def route_uses_barnaby(names):
    return len([n for n in names if 'barnaby' in n.lower()]) > 0


def route_loc_names(route):
    names = []
    for waypoint in route.raw.get('waypoints') or []:
        transport = waypoint.get('transport') if isinstance(waypoint, dict) else None
        if transport is not None and transport.get('loc_name'):
            names.append(transport['loc_name'])
    return names


class PhaseDirector(Task):
    """The first task: flips the phase when the state says it should change."""

    def __init__(self, bot):
        Task.__init__(self, label='phase director')
        self.bot = bot

    def validate(self):
        return self.bot.decide_phase() != self.bot.phase

    def execute(self):
        bot = self.bot
        before = bot.phase
        after = bot.decide_phase()
        if before != after:
            bot.log(f'phase end: {before}')
            bot.log(f'phase start: {after}')
            bot.status = after
            bot.phase = after


class Eat(Task):
    """Eats to survive in the fight, or to free a slot for loot."""

    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.phase in [FIGHT, LOOT] and self.bot.should_eat_now()

    def execute(self):
        bot = self.bot
        yield from bot.eat_once(bot.need_eat_for_loot() and not bot.has_food())


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
    """Selects the melee style or ranged mode each login, since neither is saved."""

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


class BuryBones(Task):
    """Buries big bones in the bury phase, after the loot."""

    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.phase == BURY and bot.bury_bones and inventory.contains('Big bones')

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


class Banking(Task):
    """The bank phase: walk to the bank, restock, then sail back to the field."""

    def __init__(self, bot):
        Task.__init__(self, label='banking')
        self.bot = bot

    def validate(self):
        return self.bot.phase == BANK and not event_signal.pending()

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
    """Clears the ground drops in the loot phase."""

    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.phase == LOOT and not inventory.is_full() and bot.find_loot() is not None

    def execute(self):
        yield from self.bot.loot_once()


class TravelToField(Task):
    """Reaches the Brimhaven field by boat; the bank run supplies the fare."""

    def __init__(self, bot):
        Task.__init__(self, label='travel to field')
        self.bot = bot

    def validate(self):
        return self.bot.phase == TRAVEL and not event_signal.pending() and not self.bot.at_field()

    def execute(self):
        if event_signal.pending():
            return
        yield from self.bot.walk_to_field()


class Fight(Task):
    """The kill loop: attack giants and survive. Looting belongs to the loot phase."""

    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.target_idx = None

    def validate(self):
        bot = self.bot
        here = game.tile()
        return bot.phase == FIGHT and skills.hp_fraction() >= bot.panic_hp and here is not None and bot.in_hunt(here) \
            and (len(bot.hunt_giants()) > 0 or not bot.at_field())

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
            giants = bot.hunt_giants()
            if self.target_idx is not None and len([g for g in giants if g.index == self.target_idx]) == 0:
                bot.kills += 1
                bot.log(f'moss giant down — {bot.kills} kills')
                self.target_idx = None
                # The loot phase clears the drops before the next kill.
                return
            if len(giants) == 0:
                # None in the hunt area, so go back to the field and wait there.
                if not bot.at_field():
                    back = yield from bot.quick_return_to_field()
                    if not back:
                        return
                    continue
                bot.status = 'waiting for moss giants'
                yield from execution.delay_ticks(4)
                return
            giants.sort(key=lambda g: g.distance())
            target = giants[0]
            if target.distance() > 8:
                # Out of attack range, so walk into range and look again.
                yield from traversal.walk_resilient(target.tile(), radius=1, attempts=4, timeout_ms=30000, log=lambda m: bot.log(f'  {m}'))
                continue
            if game.in_combat():
                yield from execution.delay_ticks(2)
                continue
            target.interact('Attack')
            self.target_idx = target.index

            def engaged():
                here = game.tile()
                return game.in_combat() or len(giants) == 0 or here is None or not bot.in_hunt(here)

            yield from execution.delay_until(engaged, 3000)


class BrimhavenMossGiants(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.phase = TRAVEL
        self.kills = 0
        self.looted = 0
        self.buried = 0
        self.bank_trips = 0
        self.loot_counts = {}
        self.supply_empty = False
        self.bank_empty = False
        self.died = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        # Why: this bot fights through auto retaliate.
        game.set_auto_retaliate(True)
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
        self.food_name = s.str('food', 'Lobster')
        self.panic_hp = s.num('panic_hp', 25) / 100
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        self.food_withdraw = s.num('food_withdraw', 20)
        self.loot_set = set([n.lower() for n in s.list('loot', DEFAULT_LOOT)])
        self.bank_common = s.bool('bank_common_junk', True)
        self.bury_bones = s.bool('bury_bones', False)
        if self.bury_bones:
            self.loot_set.add('big bones')
        self.cake = s.bool('loot_cake', False)
        self.loot_ammo = s.bool('loot_ammo', True)
        self.field_tile = s.tile('field_tile', FIELD_TILE)
        self.bank_tile = s.tile('bank_tile', BANK_TILE)
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in XP_SKILLS])
        loadout = range_loadout_of(self.weapon, self.ammo)
        if self.style == 'range':
            note = f" darts '{loadout.projectile}'" if loadout.thrown else f" bow '{loadout.weapon}' + '{loadout.projectile}'"
        elif self.style == 'mage':
            note = f' w/ {self.weapon} ({self.spell})'
        else:
            note = f' ({self.melee_style})'
        burying = ', burying big bones' if self.bury_bones else ''
        self.log(f"BrimhavenMossGiants — style {self.style}{note}, food '{self.food_name}' (smart-eat, panic<{round(self.panic_hp * 100)}%), "
                 + f'field {self.field_tile}, bank {self.bank_tile} (Ardougne↔Brimhaven boat){burying}')
        self.add(
            PhaseDirector(self), ContinueDialog(),
            DeathRecovery(self, self.field_tile, 6, on_death=self.died_now, on_recovered=self.recovered),
            Eat(self), GearEquip(self), SetAttackStyle(self), ArmAutocast(self), BuryBones(self), Banking(self), LootCorpse(self),
            TravelToField(self), Fight(self),
        )

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.log('died! recovering')

    def recovered(self):
        self.died = False

    def recovery_anchor(self):
        return self.field_tile

    def grind_targets(self):
        return [TARGET.lower()]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in XP_SKILLS]) - self.xp_at_start
        return {
            'Status': self.status,
            'Phase': self.phase,
            'Kills': self.kills,
            'Looted': self.looted,
            'Buried': self.buried,
            'Bank trips': self.bank_trips,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }

    # The phase (phase.ts)

    def should_bank(self):
        """The one bank trigger: panic, no food and low hp, or a full haul, a full pack and no food."""
        panic = not self.has_food() and skills.hp_fraction() < self.panic_hp and not self.bank_empty
        full_haul = inventory.is_full() and not self.has_food()
        return panic or full_haul

    def decide_phase(self):
        """The phase for the next tick, from what can be seen."""
        if self.should_bank():
            return BANK
        phase = self.phase
        if phase == TRAVEL:
            if self.at_field():
                if len(self.field_giants()) > 0:
                    return FIGHT
                return LOOT if self.find_loot() is not None else FIGHT
            # Bank before sailing unless the bot can fight on arrival.
            if not self.has_food() or inventory.count('Coins') < BOAT_FARE or inventory.is_full() or self.need_style_supplies():
                return BANK
            return TRAVEL
        if phase == FIGHT:
            # Clear the last kill's drops.
            return LOOT if self.find_loot() is not None else FIGHT
        if phase == LOOT:
            # Bury the bones once the ground is clear.
            if self.find_loot() is not None:
                return LOOT
            return BURY if self.bury_bones and inventory.contains('Big bones') else FIGHT
        if phase == BURY:
            if not self.bury_bones or not inventory.contains('Big bones'):
                return FIGHT
            return BURY
        # The bank phase fights once restocked and back on the island.
        if self.at_field() and not self.should_bank():
            return FIGHT
        return BANK

    # Health and food (shared.ts)

    def primary_food_count(self):
        return food_count(inventory.items(), self.food_name)

    def cake_count(self):
        if not self.cake:
            return 0
        return len([i for i in inventory.items() if (i.name or '').lower() == 'slice of cake'])

    def food_count(self):
        # Cake counts as food for "is there anything to eat" and the loot space checks.
        return self.primary_food_count() + self.cake_count()

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        hp = skills.effective('hitpoints')
        max_hp = skills.level('hitpoints')
        if self.primary_food_count() > 0 and should_eat_to_use_food(hp, max_hp, food_heal_amount(self.food_name), self.primary_food_count()):
            return True
        return self.cake_count() > 0 and should_eat_to_use_food(hp, max_hp, food_heal_amount('slice of cake'), self.cake_count())

    def need_eat_for_loot(self):
        """A full pack with food and loot on the ground frees a slot rather than banking early."""
        return inventory.is_full() and self.has_food() and self.find_loot() is not None

    def should_eat_now(self):
        return self.need_eat() or self.need_eat_for_loot()

    def eat_once(self, for_loot=False):
        hp = skills.effective('hitpoints')
        max_hp = skills.level('hitpoints')
        forms = food_forms(self.food_name)
        primary = None
        cake = None
        for item in inventory.items():
            name = (item.name or '').lower()
            if primary is None and name in forms:
                primary = item
            if cake is None and self.cake and name == 'slice of cake':
                cake = item
        # The chosen food when a full heal fits; otherwise cake, or any food, to free a slot.
        if primary is not None and should_eat_to_use_food(hp, max_hp, food_heal_amount(self.food_name), self.primary_food_count()):
            food = primary
        elif cake is not None:
            food = cake
        else:
            food = primary
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
        return self.field_tile.distance_to(tile) <= FIELD_RADIUS

    def in_hunt(self, tile):
        """Within the larger roaming area, so the bot walks to distant giants."""
        return self.field_tile.distance_to(tile) <= HUNT_RADIUS

    def at_field(self):
        here = game.tile()
        return here is not None and self.in_field(here)

    def field_giants(self):
        return npcs.query().name(TARGET).where(lambda n: self.in_field(n.tile()) and not n.targets_another_player()).results()

    def hunt_giants(self):
        """Every moss giant in the hunt area, the ones the bot walks to and engages."""
        return npcs.query().name(TARGET).where(lambda n: self.in_hunt(n.tile()) and not n.targets_another_player()).results()

    def find_loot(self):
        projectile = self.range_projectile().lower()

        def wanted(g):
            name = (g.name or '').lower()
            # Arrows and bolts the giants drop, only with loot_ammo on.
            ammo = self.loot_ammo and self.style == 'range' and name == projectile
            # Why: common bank junk such as beer, kebabs and gems is a banking concern, not a loot one.
            return name in self.loot_set or (self.cake and name == 'slice of cake' and self.cake_count() < 2) or ammo

        return ground_items.query().where(wanted).within(HUNT_RADIUS).nearest()

    def keep_names(self):
        projectile = self.range_projectile() if self.style == 'range' else self.ammo
        weapon = projectile if self.style == 'range' and self.range_loadout().thrown else self.weapon
        extra = ['Coins', 'slice of cake'] if self.cake else ['Coins']
        return combat_keep_names(self.food_name, self.style, spell=self.spell, ammo=projectile if self.loot_ammo else '', weapon=weapon, extra=extra)

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

    # Travel

    def walk_to_field(self):
        """Walks to the field, crossing the Ardougne to Brimhaven boat as needed."""
        self.status = 'walking to the Brimhaven moss giants'
        here = game.tile()
        where = f'{here.x},{here.z}' if here is not None else '?,?'
        self.log(f'not at the field ({where}) — walking to {self.field_tile}')
        arrived = yield from traversal.walk_resilient(self.field_tile, radius=3, attempts=6, timeout_ms=300000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def quick_return_to_field(self):
        """Back into the field mid-fight after drifting past its radius."""
        self.status = 'returning to the field'
        for _ in range(3):
            if self.at_field() or event_signal.pending():
                break
            yield from self.walk_to_field()
            back = yield from execution.delay_until(lambda: self.at_field(), 4000)
            if back:
                break
        return self.at_field()

    def sail_to_field(self):
        """Sails back to the field with Captain Barnaby, turning down any route that takes the wrong boat."""
        say = lambda m: self.log(f'  {m}')
        for attempt in range(4):
            me = game.tile()
            if me is None:
                yield from execution.delay_ticks(2)
                continue
            route = navigator.find_path(me, self.field_tile, avoid_zones=[WRONG_BOAT_ZONE] if attempt > 0 else None)
            names = route_loc_names(route) if route.ok else []
            wrong = route_uses_wrong_boat(names)
            barnaby = route_uses_barnaby(names)
            if not route.ok or wrong or not barnaby:
                self.log(f'planned route rejected (ok={route.ok}, barnaby={barnaby}, wrongBoat={wrong}) — replanning (attempt {attempt + 1})')
                continue
            self.log('planned route uses Captain Barnaby — sailing to Brimhaven')
            # Stand at the pier, so the boat hop goes from a still spot in range.
            at_pier = yield from traversal.walk_resilient(PIER_TILE, radius=2, attempts=4, timeout_ms=120000, log=say)
            if not at_pier:
                self.log('walk to the pier failed — sailing straight to the field')
            arrived = yield from traversal.walk_resilient(self.field_tile, radius=3, attempts=6, timeout_ms=300000, log=say)
            if arrived:
                return
            self.log('sail to field failed — retrying')
        # The last resort walks without the check, so the bot never stalls; it may still take the wrong boat.
        self.log('route validation exhausted — walking to the field without validation')
        at_pier = yield from traversal.walk_resilient(PIER_TILE, radius=2, attempts=4, timeout_ms=120000, log=say)
        if not at_pier:
            self.log('walk to the pier failed — sailing straight to the field')
        yield from self.walk_to_field()

    # The bank (bank.ts)

    def top_up_food(self):
        self.status = f'withdrawing {self.food_name}'
        for _ in range(12):
            if self.primary_food_count() >= self.food_withdraw or inventory.is_full():
                break
            need = self.food_withdraw - self.primary_food_count()
            before = self.primary_food_count()
            bank.withdraw(self.food_name, withdraw_op(need))
            landed = yield from execution.delay_until(lambda: self.primary_food_count() > before, 2500)
            if not landed:
                break

    def heal_at_bank(self):
        """Eats at the bank, where it's safe, so the bot goes back to the field healthy."""
        max_hp = skills.level('hitpoints')
        # Eat until full, out of food, or a minute is up; the wait covers the eating cooldown.
        deadline = now_ms() + 60000
        while now_ms() < deadline:
            hp = skills.effective('hitpoints')
            if hp >= max_hp or inventory.is_full():
                break
            forms = food_forms(self.food_name)
            food = None
            for item in inventory.items():
                if (item.name or '').lower() in forms:
                    food = item
                    break
            if food is None:
                for item in inventory.items():
                    if edible_at_bank(item.name, self.food_name):
                        food = item
                        break
            if food is None:
                break
            self.status = f'healing at bank ({round(skills.hp_fraction() * 100)}% hp)'
            food.interact('Eat')
            # The eating cooldown is about 3 ticks, so the next bite isn't dropped.
            yield from execution.delay_ticks(3)
        self.log(f"healed at the bank to {skills.effective('hitpoints')}/{max_hp}")

    def bank_routine(self, withdraw_food):
        """Walks to the bank, deposits the loot, restocks, takes the boat's coins, and sails back."""
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
        # The bank's items fill in a beat after it opens, and a withdrawal before that reads 0.
        loaded = yield from execution.delay_until(lambda: bank.loaded(), 5000)
        if not loaded:
            self.log('bank item list never loaded — will retry next bank trip')
            return
        if withdraw_food:
            # A stack to eat from and carry; then, with the bank closed, heal up so the bot doesn't arrive low and
            # burn the stack at once; then top back up for the trip.
            yield from self.top_up_food()
            if skills.effective('hitpoints') < skills.level('hitpoints'):
                closed = yield from bank.close()
                if closed:
                    yield from self.heal_at_bank()
                    reopened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
                    if not reopened:
                        self.log('could not reopen the bank to top off food — carrying what we have')
            yield from self.top_up_food()
            if self.primary_food_count() == 0:
                self.bank_empty = True
                self.log(f"WARNING: no '{self.food_name}' in the bank — carrying on without food. Deposit food (or fix the name) to resume eating.")
            else:
                self.bank_empty = False
        yield from self.withdraw_style_supplies()
        # Brimhaven always needs coins for the boat, out and back.
        fare_target = BOAT_FARE * 2
        if inventory.count('Coins') < fare_target:
            self.status = 'withdrawing coins for the boat'
            got = yield from withdraw_to('Coins', fare_target)
            self.log(f"withdrew {got} coins ({inventory.count('Coins')}) for the Ardougne↔Brimhaven boat")
            if inventory.count('Coins') < BOAT_FARE:
                self.log('WARNING: not enough coins for the boat — deposit more coins to reach Brimhaven.')
        self.bank_trips += 1
        self.status = 'restocked — sailing back to Brimhaven'
        yield from self.sail_to_field()

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
    name='BrimhavenMossGiants',
    create=BrimhavenMossGiants,
    description='Brimhaven moss giant island: range/mage/melee walk-and-fight (multicombat, safespot disabled), banks all loot at Ardougne S and sails back via the boat',
    category='Combat',
    tags=['brimhaven', 'moss giant', 'boat', 'members', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

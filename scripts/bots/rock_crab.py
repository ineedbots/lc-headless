# Wakes and stacks the rock crabs north of Rellekka and clears them, melee, mage or range, banking for food at
# Seers' Village: rs2b0t's RockCrab, with its AmmoLogic.ts and RockCrabSpots.ts (MIT, see thirdparty/rs2b0t). Ranged
# sweeps its own arrows, bolts or darts off the field after each kill. It solves the easy clues the crabs drop.

import time

from rs2004.catalogs import CUSTOM_RANGED_SETTINGS, LOADOUT_SETTING, ROCK_CRAB_RANGED_WEAPONS, SPELL_DB, STAFFS, DeathRecovery
from rs2004.catalogs import casts_available, food_forms, food_heal_amount, range_supply_empty, ranged_item, rock_crab_range_loadout
from rs2004.catalogs import rune_withdraw_list, script_food, should_eat_to_use_food, spell_button_com, sustain
from rs2004.clues import SolveClue, SolveClueHost

# The Rocks spawns of the field (RockCrabSpots.ts).
ROCKS_SPAWNS = [
    Tile(2694, 3724, 0), Tile(2700, 3718, 0), Tile(2701, 3728, 0), Tile(2702, 3720, 0), Tile(2703, 3716, 0), Tile(2704, 3727, 0),
    Tile(2705, 3725, 0), Tile(2708, 3719, 0), Tile(2711, 3715, 0), Tile(2712, 3719, 0), Tile(2712, 3725, 0), Tile(2715, 3729, 0),
    Tile(2716, 3721, 0), Tile(2719, 3719, 0),
]
# Stand tiles whose 3x3 square touches two or three Rocks spawns.
DEFAULT_SPOTS = [Tile(2704, 3726, 0), Tile(2701, 3719, 0), Tile(2717, 3720, 0), Tile(2710, 3717, 0), Tile(2713, 3727, 0)]

DEFAULT_RESET = Tile(2712, 3688, 0)
DEFAULT_BANK = Tile(2725, 3491, 0)
BANK_NAME = 'Bank booth'
BANK_OP = 'Use-quickly'
MAX_FAILED_WAKES = 3
CENTRE_RADIUS = 2
DEFAULT_LOOT = ['half of a key', 'casket', 'clue scroll', 'small oyster pearls', 'oyster pearls', 'uncut sapphire', 'uncut emerald', 'uncut ruby',
                'uncut diamond']
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic']
AMMO_OPTIONS = ['Bronze arrow', 'Iron arrow', 'Steel arrow', 'Mithril arrow', 'Adamant arrow', 'Rune arrow', 'Ogre arrow', 'Bolts', 'Barbed bolts']
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000

SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}
SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}

SETTINGS = {
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range']),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE,
                              help='rapid trains Ranged fastest; longrange splits xp with Defence'),
    'staff': SettingDef('string', 'Staff of air', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE, help='wielded staff, withdrawn from bank when missing'),
    'bow': SettingDef('string', 'Maple shortbow', 'Ranged weapon', options=ROCK_CRAB_RANGED_WEAPONS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                      help='bows use the selected ammo; darts are the weapon and projectile stack'),
    'spell': SettingDef('string', 'Wind Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE),
    'ammo': SettingDef('string', 'Bronze arrow', 'Bow ammo', options=AMMO_OPTIONS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                       help='used by bows; ignored when the ranged weapon is a dart'),
}
SETTINGS.update(CUSTOM_RANGED_SETTINGS)
SETTINGS.update({
    'ammo_withdraw': SettingDef('number', 200, 'Projectiles per bank trip', 1, 1000, group='Combat', show_if=SHOW_RANGE),
    'min_stack': SettingDef('number', 1, 'Ignore projectile stacks smaller than', 1, 50, group='Combat', show_if=SHOW_RANGE,
                            help='every kill sweeps your arrows, bolts or darts off the ground; stacks below this size are not worth the walk'),
    'collect_range': SettingDef('number', 12, 'Projectile sweep range (tiles)', 2, 30, group='Combat', show_if=SHOW_RANGE),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'fight_hp_gate': SettingDef('number', 40, 'Retreat below HP%', 0, 100, group='Food & healing'),
    'rest_until_hp': SettingDef('number', 75, 'Rest until HP% (no-food fallback)', 0, 100, group='Food & healing'),
    'loc1': SettingDef('tile', DEFAULT_SPOTS[0], 'Spot 1 (x,z)', group='Field',
                       help='stand tiles whose 3x3 square touches 2-3 Rocks spawns. Set a slot to 0,0 to disable it.'),
    'loc2': SettingDef('tile', DEFAULT_SPOTS[1], 'Spot 2 (x,z)', group='Field'),
    'loc3': SettingDef('tile', DEFAULT_SPOTS[2], 'Spot 3 (x,z)', group='Field'),
    'loc4': SettingDef('tile', DEFAULT_SPOTS[3], 'Spot 4 (x,z)', group='Field'),
    'loc5': SettingDef('tile', DEFAULT_SPOTS[4], 'Spot 5 (x,z)', group='Field'),
    'reset_tile': SettingDef('tile', DEFAULT_RESET, 'Run-out reset tile (x,z)', group='Field'),
    'field_radius': SettingDef('number', 15, 'Field radius (tiles)', 5, 30, group='Field'),
    'stack': SettingDef('number', 3, 'Crabs to stack before clearing', 1, 8, group='Field'),
    'bank_tile': SettingDef('tile', DEFAULT_BANK, 'Bank stand tile (Seers)', group='Banking & loot'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot item names', group='Banking & loot'),
})
SETTINGS.update(PERIODIC_BANK_SETTINGS)
SETTINGS['solve_clues'] = SettingDef('boolean', True, 'Solve easy clues', group='Clues')


# The pure pieces, kept apart from the game so they can be tested without a client.

def spawns_within(spot, ring, spawns=None):
    """How many Rocks spawns lie within ring tiles of spot."""
    return len([s for s in (spawns if spawns is not None else ROCKS_SPAWNS) if s.distance_to(spot) <= ring])


def sweep_plan(stacks, min_stack, range_, force):
    """The keys of the projectile stacks worth walking to, nearest first: those within range_, and of at least
    min_stack unless force. Each stack has key, count and distance."""
    chosen = [s for s in stacks if s.distance <= range_ and (force or s.count >= min_stack)]
    chosen.sort(key=lambda s: s.distance)
    return [s.key for s in chosen]


def distinct_spots(slots):
    """The spot settings that are set, without repeats, or the defaults when none is."""
    seen = set()
    spots = []
    for t in slots:
        key = f'{t.x},{t.z}'
        if t.x <= 0 or t.z <= 0 or key in seen:
            continue
        seen.add(key)
        spots.append(t)
    return spots if spots else list(DEFAULT_SPOTS)


def nearest_spot_index(spots, here):
    if here is None:
        return 0
    best = 0
    for i, t in enumerate(spots):
        if t.distance_to(here) < spots[best].distance_to(here):
            best = i
    return best


def now_ms():
    return time.time() * 1000


class Stack:
    """A projectile pile on the ground, as sweep_plan reads it."""

    def __init__(self, key, count, distance):
        self.key = key
        self.count = count
        self.distance = distance


def stack_key(g):
    t = g.tile()
    return f'{t.x}|{t.z}|{t.level}'


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.need_eat()

    def execute(self):
        yield from self.bot.eat_once()


class GearEquip(Task):
    """Keeps the staff or bow wielded, and the projectiles in the pack equipped."""

    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0

    def _wants_weapon(self):
        weapon = self.bot.weapon
        return weapon != '' and not equipment.contains(weapon) and inventory.first(weapon) is not None

    def validate(self):
        bot = self.bot
        if bot.style == 'melee' or self.fails >= 5:
            return False
        if self._wants_weapon():
            return True
        return bot.style == 'range' and inventory.count(bot.range_projectile()) > 0

    def execute(self):
        bot = self.bot
        if self._wants_weapon():
            bot.status = f'wielding {bot.weapon}'
            wielded = yield from equipment.equip(bot.weapon)
            if wielded:
                bot.log(f'wielded {bot.weapon}')
                self.fails = 0
            else:
                self.fails += 1
            return
        projectile = bot.range_projectile()
        equipped = yield from bot.equip_pack_projectiles()
        if equipped:
            bot.log(f'equipped {projectile} — {bot.equipped_projectile_count()} ready')
            self.fails = 0
        else:
            self.fails += 1
            if self.fails >= 5:
                bot.log(f"WARNING: could not equip '{projectile}' from the pack after 5 tries")


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
            if bot.style == 'range':
                label = ['accurate', 'rapid', 'longrange'][bot.range_mode]
            else:
                resolution = game.combat_style_resolution(bot.melee_style)
                label = describe_combat_style(resolution) if resolution else None
            bot.log(f'combat style: {label or "?"}')
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
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}' — retrying in {ASSERT_RETRY_MS // 1000}s. Check the spell name, magic level and staff.")


class CollectProjectiles(Task):
    def __init__(self, bot):
        Task.__init__(self, label='collect projectiles')
        self.bot = bot
        self.warned_mismatch = False

    def _force(self):
        bot = self.bot
        projectile = bot.range_projectile()
        dry = bot.equipped_projectile_count() == 0 and inventory.count(projectile) == 0
        return dry or (not bot.has_food() and not bot.bank_known_empty) or bot.need_style_supplies() or bot.clue_pending()

    def validate(self):
        bot = self.bot
        if bot.style != 'range':
            return False
        projectile = bot.range_projectile().lower()
        if not self.warned_mismatch:
            def other_ammo(g):
                name = (g.name or '').lower()
                return ('arrow' in name or 'bolt' in name or 'dart' in name) and name != projectile and bot.in_field(g.tile())

            if ground_items.query().where(other_ammo).nearest() is not None:
                self.warned_mismatch = True
                bot.log(f"WARNING: ground projectiles in the field do not match '{bot.range_projectile()}' — those will not be collected. "
                        + "Check the Ranged weapon and Bow ammo settings if they're yours.")
        stacks = [Stack(stack_key(g), g.count, g.distance()) for g in bot.projectile_stacks_on_ground()]
        return len(sweep_plan(stacks, bot.min_stack, bot.collect_range, self._force())) > 0

    def execute(self):
        self.bot.status = f'sweeping {self.bot.range_projectile()}'
        yield from self.bot.sweep_projectiles_once(self._force())


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def _need_weapon(self):
        bot = self.bot
        if bot.style == 'range' and bot.range_loadout().thrown:
            return False
        return bot.style != 'melee' and bot.weapon != '' and not equipment.contains(bot.weapon) and inventory.first(bot.weapon) is None \
            and not bot.weapon_missing

    def validate(self):
        bot = self.bot
        if self._need_weapon():
            return True
        if bot.need_style_supplies() and not bot.style_supply_empty:
            return True
        return not bot.has_food() and not bot.bank_known_empty

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.status = 'restocking — walking to the bank'
        casts = f', casts {bot.casts_left()}' if bot.style == 'mage' else ''
        darts = f', projectiles {bot.equipped_projectile_count()}' if bot.style == 'range' else ''
        weapon = f', need {bot.weapon}' if self._need_weapon() else ''
        bot.log(f'banking at {bot.bank_tile} (food {bot.food_count()}{casts}{darts}{weapon})')
        say = lambda m: bot.log(f'  {m}')
        arrived = yield from traversal.walk_resilient(bot.bank_tile, radius=3, attempts=6, timeout_ms=300000, log=say)
        if not arrived:
            bot.log('walk to the bank failed — will retry')
            return
        opened = yield from bank.open_nearest(BANK_NAME, BANK_OP)
        if not opened:
            bot.log('could not open the bank — will retry')
            return
        bot.status = f'withdrawing {bot.food_name}'
        for _ in range(12):
            if inventory.count(bot.food_name) >= bot.food_withdraw or inventory.is_full():
                break
            need = bot.food_withdraw - inventory.count(bot.food_name)
            op = 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')
            before = inventory.count(bot.food_name)
            bank.withdraw(bot.food_name, op)
            landed = yield from execution.delay_until(lambda: inventory.count(bot.food_name) > before, 2500)
            if not landed:
                break
        got = inventory.count(bot.food_name)
        if got == 0:
            bot.bank_known_empty = True
            bot.log(f"WARNING: no '{bot.food_name}' in the bank — falling back to no-food combat. Deposit food (or fix the food name) and it'll resume eating.")
        else:
            bot.bank_trips += 1
            bot.log(f'withdrew {got} {bot.food_name}')
        yield from self._withdraw_style_supplies()
        bot.status = 'restocked — walking back to the field'
        yield from traversal.walk_resilient(bot.current_spot(), radius=4, attempts=6, timeout_ms=300000, log=say)
        bot.failed_wakes = 0

    def _withdraw_to(self, name, target):
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
            op = 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1')
            bank.withdraw(name, op)
            landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
            if not landed:
                break
        return inventory.count(name) - start

    def _withdraw_style_supplies(self):
        bot = self.bot
        if self._need_weapon():
            bot.status = f'withdrawing {bot.weapon}'
            got = yield from self._withdraw_to(bot.weapon, 1)
            if got > 0:
                yield from equipment.equip(bot.weapon)
                bot.log(f'withdrew and wielded {bot.weapon}')
            else:
                bot.weapon_missing = True
                bot.log(f"WARNING: no '{bot.weapon}' in the bank — carrying on with current gear. Deposit it (or fix the weapon name) and restart to retry.")
        if bot.style == 'mage':
            bot.status = 'withdrawing runes'
            short = False
            for row in rune_withdraw_list(bot.spell, bot.wielded_names(), bot.runes_withdraw):
                rune = row['rune']
                count = row['count']
                if inventory.count(rune) < count:
                    gained = yield from self._withdraw_to(rune, count)
                    bot.log(f'withdrew {gained} {rune} ({inventory.count(rune)}/{count})')
                short = short or inventory.count(rune) == 0
            if bot.casts_left() < 1:
                bot.style_supply_empty = True
                missing = ' (a rune is missing entirely)' if short else ''
                bot.log(f"WARNING: bank can't supply a single '{bot.spell}' cast{missing} — deposit runes to resume casting.")
            else:
                bot.style_supply_empty = False
        elif bot.style == 'range':
            projectile = bot.range_projectile()
            bot.status = f'withdrawing {projectile}'
            gained = yield from self._withdraw_to(projectile, bot.ammo_withdraw)
            if gained > 0:
                closed = yield from bank.close()
                equipped = False
                if closed:
                    equipped = yield from bot.equip_pack_projectiles()
                if not equipped:
                    bot.log(f'WARNING: withdrew {projectile}, but could not equip the stack — will retry from the pack')
                bot.log(f'withdrew {gained} {projectile} — {bot.equipped_projectile_count()} equipped')
                bot.style_supply_empty = False
            elif bot.equipped_projectile_count() == 0 and inventory.count(projectile) == 0:
                bot.style_supply_empty = True
                bot.log(f"WARNING: no '{projectile}' in the bank and none carried — deposit projectiles to resume. Recovered projectiles will re-enable ranged combat.")


class GoToField(Task):
    def __init__(self, bot):
        Task.__init__(self, label='go to field')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and not self.bot.in_field(here)

    def execute(self):
        bot = self.bot
        bot.status = 'walking to the field'
        ok = yield from traversal.walk_resilient(bot.current_spot(), radius=4, attempts=6, timeout_ms=240000, log=lambda m: bot.log(f'  {m}'))
        if ok:
            bot.failed_wakes = 0


class LootValuables(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot valuables')
        self.bot = bot

    def validate(self):
        return not inventory.is_full() and self.bot.find_loot() is not None

    def execute(self):
        yield from self.bot.loot_once()


class RegroupAtField(Task):
    def __init__(self, bot):
        Task.__init__(self, label='regroup')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return skills.hp_fraction() >= bot.fight_hp_gate and bot.stack_ready() and not bot.at_centre()

    def execute(self):
        if event_signal.pending():
            return
        self.bot.status = 'regrouping — running back to the stand spot'
        yield from direct_navigator.walk_to(self.bot.current_spot(), CENTRE_RADIUS, 30000)


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.last_count = 0

    def validate(self):
        bot = self.bot
        if skills.hp_fraction() < bot.fight_hp_gate:
            return False
        if bot.style == 'range' and bot.equipped_projectile_count() == 0:
            return False
        return bot.stack_ready()

    def execute(self):
        bot = self.bot
        bot.status = 'fighting the stack'
        deadline = now_ms() + 120000
        while now_ms() < deadline:
            if event_signal.pending() or bot.died or chat_dialog.can_continue():
                return
            if bot.need_eat():
                yield from bot.eat_once()
                continue
            if skills.hp_fraction() < bot.fight_hp_gate:
                return
            if bot.style == 'range' and bot.equipped_projectile_count() == 0:
                return
            if not inventory.is_full() and bot.find_loot() is not None:
                yield from bot.loot_once()
                continue
            crabs = bot.active_crabs()
            crabs.sort(key=lambda n: n.distance())
            if not crabs:
                return
            if not game.in_combat():
                crabs[0].interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or len(bot.active_crabs()) == 0, 4000)
            else:
                yield from execution.delay_ticks(2)
            remaining = len(bot.active_crabs())
            if remaining < self.last_count:
                bot.kills += self.last_count - remaining
                bot.log(f'rock crab down — {bot.kills} kills total')
                if bot.style == 'range':
                    yield from bot.sweep_projectiles_once(False)
            self.last_count = remaining


class Aggro(Task):
    def __init__(self, bot):
        Task.__init__(self, label='aggro')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if skills.hp_fraction() < bot.fight_hp_gate or bot.de_aggroed() or (bot.style == 'range' and bot.equipped_projectile_count() == 0):
            return False
        return len(bot.active_crabs()) < bot.desired_stack and len(bot.dormant_rocks()) > 0

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        rocks = bot.dormant_rocks()
        rocks.sort(key=lambda n: n.distance())
        if not rocks:
            return
        rock_tile = rocks[0].tile()
        bot.status = f'waking rocks at {rock_tile}'
        before = len(bot.active_crabs())
        yield from direct_navigator.walk_to(rock_tile, 1, 15000)
        woke = yield from execution.delay_until(lambda: len(bot.active_crabs()) > before or len([r for r in bot.dormant_rocks() if r.tile().equals(rock_tile)]) == 0, 4000)
        bot.failed_wakes = 0 if woke else bot.failed_wakes + 1
        if woke:
            bot.log(f'woke a rock crab — stack now {len(bot.active_crabs())}')
        else:
            bot.log(f"rocks at {rock_tile} did not wake ({'area de-aggroed — will reset' if bot.de_aggroed() else 'retrying'})")


class ResetAggro(Task):
    def __init__(self, bot):
        Task.__init__(self, label='reset aggro')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.de_aggroed() or (skills.hp_fraction() < bot.fight_hp_gate and not bot.has_food() and not game.in_combat())

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        low = skills.hp_fraction() < bot.fight_hp_gate
        bot.status = 'low HP, no food — retreating to regen' if low else 'running out to reset aggression'
        bot.resets += 1
        say = lambda m: bot.log(f'  {m}')
        yield from traversal.walk_resilient(bot.reset_tile, radius=1, attempts=5, timeout_ms=90000, log=say)
        if low:
            bot.log(f"resting at the reset tile ({skills.effective('hitpoints')}/{skills.level('hitpoints')} hp)")
            yield from execution.delay_until(lambda: skills.hp_fraction() >= bot.rest_hp, 120000)
        else:
            yield from execution.delay_ticks(5)
        yield from traversal.walk_resilient(bot.current_spot(), radius=3, attempts=5, timeout_ms=90000, log=say)
        bot.failed_wakes = 0
        bot.log('back in the field')


class RockCrab(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.kills = 0
        self.looted = 0
        self.deaths = 0
        self.resets = 0
        self.bank_trips = 0
        self.failed_wakes = 0
        self.bank_known_empty = False
        self.weapon_missing = False
        self.style_supply_empty = False
        self.died = False
        self.status = 'starting'
        self.loot_counts = {}
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.locs = distinct_spots([s.tile(f'loc{i}', DEFAULT_SPOTS[i - 1]) for i in [1, 2, 3, 4, 5]])
        self.loc_idx = nearest_spot_index(self.locs, game.tile())
        self.reset_tile = s.tile('reset_tile', DEFAULT_RESET)
        self.bank_tile = s.tile('bank_tile', DEFAULT_BANK)
        self.field_radius = s.num('field_radius', 15)
        self.desired_stack = s.num('stack', 3)
        self.fight_hp_gate = s.num('fight_hp_gate', 40) / 100
        self.rest_hp = s.num('rest_until_hp', 75) / 100
        self.food_name = script_food(s, 'Lobster')
        self.food_withdraw = s.num('food_withdraw', 20)
        self.loot_names = [n.lower() for n in s.list('loot', DEFAULT_LOOT)]
        self.bank_common = s.bool('bank_common_junk', True)
        self.style = s.str('combat_style', 'melee').lower()
        self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        if self.style == 'mage':
            self.weapon = s.str('staff', 'Staff of air')
        elif self.style == 'range':
            self.weapon = ranged_item(s, 'bow', 'Maple shortbow')
        else:
            self.weapon = ''
        self.spell = s.str('spell', 'Wind Strike')
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.ammo = ranged_item(s, 'ammo', 'Bronze arrow') if self.style == 'range' else ''
        self.ammo_withdraw = s.num('ammo_withdraw', 200)
        self.min_stack = s.num('min_stack', 1)
        self.collect_range = s.num('collect_range', 12)
        self.solve_clues = s.bool('solve_clues', True)
        self.clues_solved = 0
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=self.is_food_item, food_name=lambda: self.food_name,
                                                  food_withdraw=lambda: self.food_withdraw, weapon_name=lambda: self.weapon, enabled=lambda: self.solve_clues))
        loadout = self.range_loadout()
        if self.style == 'mage':
            note = f", mage '{self.spell}' w/ '{self.weapon or '(no weapon set)'}'"
        elif self.style == 'range':
            held = ' (thrown)' if loadout.thrown else f" w/ '{loadout.weapon or '(no weapon set)'}'"
            note = f", range '{loadout.projectile}'{held} ({s.str('range_style', 'rapid')}, sweep>={self.min_stack})"
        else:
            note = f" ({s.str('melee_style', 'strength')})"
        spots = ' | '.join([f'{t.x},{t.z}' for t in self.locs])
        self.log(f"RockCrab starting — spots [{spots}] starting at {self.current_spot()} r{self.field_radius}, stack {self.desired_stack}, "
                 + f"food '{self.food_name}' (smart-eat), bank {self.bank_tile}, style {self.style}{note}")
        if self.style == 'mage' and spell_button_com(self.spell) == -1:
            self.log(f"WARNING: '{self.spell}' is not an autocastable spell (Wind/Water/Earth/Fire Strike, Bolt, Blast or Wave) — autocast will not arm")
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in COMBAT_SKILLS])

        def eat_if_needed():
            if self.need_eat():
                yield from self.eat_once()

        sustain.set(eat_if_needed)
        self.add(
            DeathRecovery(self, self.locs[0], 4, on_death=self.died_now, on_recovered=self.recovered),
            Eat(self), GearEquip(self), SetAttackStyle(self), ArmAutocast(self), CollectProjectiles(self), self.solve_clue,
            BankRun(self),
            PeriodicBank(
                strategy=lambda: parse_bank_strategy(self.settings.str('bank_strategy', 'Off')),
                items_threshold=lambda: self.settings.num('bank_every_items', 15),
                minutes_threshold=lambda: self.settings.num('bank_every_minutes', 10),
                count_loot=lambda: len([i for i in inventory.items() if (i.name or '').lower() in self.loot_names]),
                deposit=lambda name: name.lower() in self.loot_names,
                common_junk=lambda: self.bank_common,
                return_to=lambda: self.current_spot(),
                set_status=lambda text: self.set_status(text),
                log=lambda m: self.log(m),
            ),
            GoToField(self), LootValuables(self), RegroupAtField(self), Fight(self), Aggro(self), ResetAggro(self),
        )

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.deaths += 1
        self.solve_clue.note_death()
        self.log('died! waiting for respawn, then web-walking back to the field')

    def recovered(self):
        self.died = False

    def set_status(self, text):
        self.status = text

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
        self.set_status(text)

    def clue_pending(self):
        return self.solve_clues and any([(i.name or '').lower() == 'clue scroll' for i in inventory.items()])

    def grind_targets(self):
        return ['rock crab', 'rocks']

    def recovery_anchor(self):
        return self.current_spot()

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in COMBAT_SKILLS]) - self.xp_at_start
        report = {
            'Status': self.status,
            'Kills': self.kills,
            'Looted': self.looted,
            'Bank trips': self.bank_trips,
            'Deaths': self.deaths,
            'Resets': self.resets,
            'Combat xp': gained,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report

    # The field

    def current_spot(self):
        return self.locs[self.loc_idx % len(self.locs)]

    def in_field(self, tile):
        return self.current_spot().distance_to(tile) <= self.field_radius

    def stack_ready(self):
        crabs = len(self.active_crabs())
        return crabs >= self.desired_stack or (crabs >= 1 and len(self.dormant_rocks()) == 0)

    def at_centre(self):
        here = game.tile()
        return here is not None and self.current_spot().distance_to(here) <= CENTRE_RADIUS

    def active_crabs(self):
        return npcs.query().name('Rock Crab').where(lambda n: self.in_field(n.tile()) and not n.targets_another_player()).results()

    def dormant_rocks(self):
        me = players.local()
        others = [p for p in players.all() if p.index != me.index and self.in_field(p.tile())]
        return npcs.query().name('Rocks').where(lambda n: self.in_field(n.tile()) and len([p for p in others if n.tile().distance_to(p.tile()) <= 2]) == 0).results()

    def de_aggroed(self):
        return self.failed_wakes >= MAX_FAILED_WAKES

    # Food

    def is_food_item(self, name):
        return (name or '').lower() in food_forms(self.food_name)

    def food_count(self):
        return len([i for i in inventory.items() if self.is_food_item(i.name)])

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food_name), 1)

    def eat_once(self):
        food = None
        for item in inventory.items():
            if self.is_food_item(item.name):
                food = item
                break
        if food is None:
            return False
        self.status = f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
        before = skills.effective('hitpoints')
        food.interact('Eat')
        ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
        return ate

    # Style supplies

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def range_loadout(self):
        return rock_crab_range_loadout(self.weapon, self.ammo)

    def range_projectile(self):
        return self.range_loadout().projectile

    def equipped_projectile_count(self):
        projectile = self.range_projectile().lower()
        for item in equipment.items():
            if (item.name or '').lower() == projectile:
                return item.count
        return 0

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def projectile_stacks_on_ground(self):
        projectile = self.range_projectile().lower()
        return ground_items.query().where(lambda g: (g.name or '').lower() == projectile and self.in_field(g.tile())).results()

    def need_style_supplies(self):
        if self.style == 'mage':
            return self.casts_left() < 1
        if self.style == 'range':
            projectile = self.range_projectile()
            return range_supply_empty(self.equipped_projectile_count(), inventory.count(projectile), len(self.projectile_stacks_on_ground()))
        return False

    def sweep_projectiles_once(self, force):
        projectile = self.range_projectile()
        stacks = self.projectile_stacks_on_ground()
        plan = set(sweep_plan([Stack(stack_key(g), g.count, g.distance()) for g in stacks], self.min_stack, self.collect_range, force))
        collected = 0
        for stack in stacks:
            if event_signal.pending() or self.died or stack_key(stack) not in plan:
                continue
            before = inventory.count(projectile)
            stack.interact('Take')
            took = yield from execution.delay_until(lambda: inventory.count(projectile) > before, 5000)
            if took:
                collected += 1
                self.log(f'swept {inventory.count(projectile) - before} {projectile} off the ground')
        if inventory.count(projectile) > 0:
            yield from self.equip_pack_projectiles()
        return collected

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

    # Loot

    def find_loot(self):
        return ground_items.query().where(lambda g: (g.name or '').lower() in self.loot_names).within(self.field_radius).nearest()

    def loot_once(self):
        drop = self.find_loot()
        if drop is None:
            return False
        self.status = f'looting {drop.name} at {drop.tile()}'
        before = inventory.used()
        drop.interact('Take')
        took = yield from execution.delay_until(lambda: inventory.used() > before, 5000)
        if took:
            self.looted += 1
            if drop.name:
                self.loot_counts[drop.name] = self.loot_counts.get(drop.name, 0) + 1
            self.log(f'looted {drop.name}')
            return True
        return False


BOT = define_bot(
    name='RockCrab',
    create=RockCrab,
    description='Rellekka rock crabs: aggro-stack-kill-reset, loots key halves',
    category='Combat',
    tags=['rellekka', 'keys', 'afk'],
    settings_schema=SETTINGS,
)

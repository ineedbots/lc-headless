# Fights any named NPC within a leash of where it starts, or of chosen coordinates: loots the chosen drops, banks
# them at the nearest bank or a named one, and comes back. rs2b0t's AutoFighter (MIT, see thirdparty/rs2b0t). Melee,
# magic or range, with special attacks. It solves the clues it picks up, and banks the reward after.

import time

from bots.autofighter.data import BANK_LOCATION_OPTIONS, BANKING_OPTIONS, BURIAL_BONE_NAME, CUSTOM_COORDINATES, DEFAULT_CUSTOM_SPOT
from bots.autofighter.data import DEFAULT_LOOT, SPOT_OPTIONS, START_POSITION, assert_auto_retaliate_on, auto_bank_enabled
from bots.autofighter.data import auto_retaliate_should_enable, is_burial_bone, resolve_killing_spot, should_arm_special
from bots.autofighter.data import should_bank_after_minutes, should_bury_regular_bones, special_available, wants_auto_fighter_loot
from rs2004.catalogs import HERB_OPTIONS, HERBS, LOADOUT_SETTING, SPELL_DB, ContinueDialog, DeathRecovery, casts_available
from rs2004.catalogs import count_matching, food_heal_amount, matches_any, rune_withdraw_list, script_food, should_bank, should_eat
from rs2004.catalogs import should_panic, sustain
from rs2004.clues import SolveClue, SolveClueHost
from rs2004.hunting.logic import attack_range_for, body_origin, gap_to

BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
KIT = ['spade', 'sextant', 'watch', 'chart']
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic']
# Why: auto retaliate only fires on a landed hit, so a zero-damage enemy leaves us stuck in combat; the attack goes
# out again after this long with flat combat xp.
STALL_REATTACK_MS = 2 * 60000
# Why: a drop the server never lets us take would pin the loot task forever; it's given up only after the same item
# and tile have failed this long.
LOOT_STUCK_MS = 30000
# Why: a cooldown lets the drop come back later, since another bot may have moved it, without spinning on it now.
LOOT_SKIP_MS = 30 * 60000

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}
SHOW_MAGE_RANGE = {'key': 'combat_style', 'any_of': ['mage', 'range']}
SHOW_MELEE_RANGE = {'key': 'combat_style', 'any_of': ['melee', 'range']}

SETTINGS = {
    'target': SettingDef('string', 'Guard', 'Target NPC name(s)', help='comma-separated exact in-game names to fight, e.g. Guard, Knight, Moss giant'),
    'spot': SettingDef('string', START_POSITION, 'Killing spot', options=SPOT_OPTIONS, help='use the tile where the script starts, or walk to custom coordinates'),
    'coordinates': SettingDef('tile', DEFAULT_CUSTOM_SPOT, 'Killing coordinates (x,z)', show_if={'key': 'spot', 'any_of': [CUSTOM_COORDINATES]}),
    'leash_radius': SettingDef('number', 8, 'Leash radius (tiles)', 2, 30),
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range'],
                               help='melee / mage / range. Older saves that stored attack/strength/controlled/defence under this key are migrated to Melee style.'),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'use_special': SettingDef('boolean', True, 'Use special attacks', group='Combat', show_if=SHOW_MELEE_RANGE,
                              help="arms the spec bar whenever energy covers the wielded weapon's special (dragon dagger, dragon longsword, magic shortbow, …); does nothing with a weapon that has no special"),
    'spell': SettingDef('string', 'Fire Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE,
                        help='kept armed via autocast — a staff must be wielded'),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE,
                                 help='the bot tops runes up to this many casts of the selected spell; runes the wielded staff provides free are skipped'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Bronze arrow', 'Ammo (withdrawn from bank)', group='Combat', show_if=SHOW_RANGE),
    'ammo_withdraw': SettingDef('number', 500, 'Ammo per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'ammo_restock_below': SettingDef('number', 25, 'Bank for ammo below %', 0, 100, group='Combat', show_if=SHOW_MAGE_RANGE,
                                     help='when not banking for food, go bank once magic casts / ranged ammo drop below this percentage of a full trip'),
    'loadout': LOADOUT_SETTING,
    'food': SettingDef('string', '', 'Food to eat', help="exact item name to eat (e.g. Shark, Monkfish, Trout). Leave blank to use the loadout's food, falling back to Trout"),
    'food_withdraw': SettingDef('number', 10, 'Food to carry', 0, 27),
    'panic_hp': SettingDef('number', 25, 'Panic below HP% (no food)', 0, 100),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot item names (exact)', csv_toggle='loot_mode',
                       help='exact item names, case-insensitive; defaults to gem-table items + clue scrolls, nothing else'),
    'loot_mode': SettingDef('string', 'list', 'Loot entry mode', options=['list', 'csv'], option_labels={'list': 'List (chips)', 'csv': 'CSV (text + copy/paste)'},
                            help='List = add items one at a time (current). CSV = paste a comma-separated list with copy/paste buttons.'),
    'avoid_herbs': SettingDef('string[]', [], 'Herbs to avoid', options=HERB_OPTIONS, group='Banking & loot',
                              help='pick herbs to never pick up; matched by item id for grimy and cleaned forms, since every grimy herb reads as "Herb"'),
    'bury_bones': SettingDef('boolean', False, 'Bury regular bones', group='Banking & loot', help='pick up and bury regular Bones for Prayer XP (always looted when on)'),
    'bury_big_bones': SettingDef('boolean', False, 'Bury big bones', group='Banking & loot',
                                 help='pick up and bury Big bones for Prayer XP, independently of regular bones (always looted when on)'),
    'solve_clues': SettingDef('boolean', True, 'Solve clue drops', group='Clues'),
    'banking': SettingDef('string', 'Auto', 'Banking', options=BANKING_OPTIONS, help='Auto = bank loot at the nearest bank and return; None = no loot-only bank trips'),
    'bank_location': SettingDef('string', 'Nearest', 'Bank location', options=BANK_LOCATION_OPTIONS, group='Banking & loot',
                                help='Nearest = closest reachable unlocked bank; a named bank forces that stand (locked banks fall back to nearest). Used for loot, food, supplies, and panic retreats.'),
    'bank_at_loot_slots': SettingDef('number', 12, 'Bank at loot slots', 1, 27, show_if={'key': 'banking', 'any_of': ['Auto']}),
    'bank_every_minutes': SettingDef('number', 0, 'Bank every N minutes', 0, 120, group='Banking & loot', show_if={'key': 'banking', 'any_of': ['Auto']},
                                     help='0 = never. Same idea as CowKiller: walk loot to the bank after this many minutes so a death does not wipe a long session.'),
    'bank_common_junk': SettingDef('boolean', True, 'Bank common junk too'),
}


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


def should_keep_bank_item(name, id, food, bank_common, ammo=None, gear=None, bury_bones=False, bury_big_bones=False):
    """Whether a backpack item stays out of the deposit: the food, coins, clue kit and clues, a casket (the random
    event's only with bank_common off), the ammo, the gear, and unnoted bones to bury."""
    n = name.lower()
    generic_casket = id == RANDOM_EVENT_CASKET_ID
    ammo_match = len([a for a in (ammo or []) if a.lower() == n]) > 0
    gear_match = len([g for g in (gear or []) if g.lower() == n]) > 0
    return matches_any(name, [food]) or n == 'coins' or n in KIT or 'clue' in n \
        or ('casket' in n and not generic_casket) or (generic_casket and not bank_common) \
        or ammo_match or gear_match or is_burial_bone(name, bury_bones and id == 526, bury_big_bones and id == 532)


class EnableAutoRetaliate(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Enable auto retaliate')
        self.bot = bot

    def validate(self):
        return auto_retaliate_should_enable(game.auto_retaliate_on())

    def execute(self):
        self.bot.status = 'enabling auto retaliate'
        yield from game.open_side_tab(0)
        for _ in range(5):
            if game.auto_retaliate_on():
                break
            game.set_auto_retaliate(True)
            on = yield from execution.delay_until(lambda: game.auto_retaliate_on(), 1500)
            if on:
                break
        assert_auto_retaliate_on(game.auto_retaliate_on())
        self.bot.log('Auto Retaliate on')


class LootDrops(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Loot drops')
        self.bot = bot
        self.skipped = {}
        self.stuck = {}

    def _key(self, drop):
        return f'{drop.id}:{drop.tile()}'

    def _find(self):
        bot = self.bot
        now = now_ms()
        for key in list(self.skipped.keys()):
            if self.skipped[key] <= now:
                self.skipped.pop(key)
        reach = bot.leash + 4
        return ground_items.query().action('Take').where(
            lambda g: bot.is_loot(g.name) and not bot.is_avoided_herb(g.id) and g.tile().distance_to(bot.anchor) <= reach
            and self._key(g) not in self.skipped and reachability.walkable(g.tile())).within(reach).nearest()

    def validate(self):
        return not game.in_combat() and not inventory.is_full() and self._find() is not None

    def execute(self):
        bot = self.bot
        drop = self._find()
        if drop is None:
            return
        bot.status = f'looting {drop.name} at {drop.tile()}'
        id = drop.id
        tile = drop.tile()
        key = self._key(drop)

        def find():
            # pocketpy's lambda can't read execute's id and tile from here, so it gets copies.
            wanted_id = id
            wanted_tile = tile
            return ground_items.query().where(lambda g: g.id == wanted_id and g.tile().equals(wanted_tile)).nearest()

        def count():
            return sum([i.count for i in inventory.items() if i.id == id])

        before = count()
        status = yield from reach.entity_op(find, 'Take', lambda: count() > before, expect_ms=5000, what=drop.name or 'loot', log=lambda m: bot.log(m))
        if status == 'done' and count() > before:
            self.skipped.pop(key, None)
            self.stuck.pop(key, None)
            bot.looted += 1
            return
        now = now_ms()
        if status == 'unreachable':
            self.stuck.pop(key, None)
            self.skipped[key] = now + LOOT_SKIP_MS
            bot.log(f"blacklisting unreachable loot '{drop.name}' id={id} at {tile} for {LOOT_SKIP_MS // 1000}s")
            return
        prev = self.stuck.get(key)
        started = prev[0] if prev is not None and now - prev[1] <= LOOT_STUCK_MS else now
        self.stuck[key] = (started, now)
        if now - started < LOOT_STUCK_MS:
            bot.log(f"loot '{drop.name}' id={id} at {tile} did not complete ({status}); still trying")
            return
        self.stuck.pop(key, None)
        self.skipped[key] = now + LOOT_SKIP_MS
        bot.log(f"blacklisting loot '{drop.name}' id={id} at {tile} for {LOOT_SKIP_MS // 1000}s after {LOOT_STUCK_MS // 1000}s stuck ({status})")


class EatFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Eat food')
        self.bot = bot

    def validate(self):
        # Why: the bank side shows Deposit ops, not Eat, so eating with the bank open spins and blocks BankRun.
        return self.bot.need_eat() and not bank.is_open()

    def execute(self):
        bot = self.bot
        for _ in range(28):
            if bot.died or chat_dialog.can_continue() or event_signal.pending() or not bot.need_eat():
                return
            food = bot.first_food()
            if food is None:
                return
            bot.status = f"eating {food.name} ({skills.effective('hitpoints')}/{skills.level('hitpoints')} hp)"
            before = skills.effective('hitpoints')
            if not food.interact('Eat'):
                return
            bot.resume_attack = True
            yield from execution.delay_until(lambda: skills.effective('hitpoints') > before or bot.food_count() == 0, 3000)
            if skills.effective('hitpoints') > before:
                bot.eats += 1


class PanicRetreat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Panic retreat')
        self.bot = bot

    def validate(self):
        return should_panic(skills.hp_fraction(), self.bot.panic_at, self.bot.food_count())

    def execute(self):
        bot = self.bot
        destination = bot.pick_bank(game.tile())
        if destination is None:
            return
        bot.status = 'panic: no food — retreating to the bank'
        bot.log(f"panic retreat at {skills.effective('hitpoints')}/{skills.level('hitpoints')} hp")
        bot.note_forced_fallback(destination)
        say = lambda m: bot.log(f'  {m}')
        yield from traversal.walk_resilient(bot.bank_tile_of(destination), radius=3, attempts=4, timeout_ms=180000, log=say)
        opened = yield from open_bank_access(destination, BOOTH, log=say)
        if opened:
            for _ in range(bot.food_withdraw):
                if inventory.is_full():
                    break
                before = bot.food_count()
                if not bank.withdraw(bot.food, 'Withdraw-1'):
                    break
                landed = yield from execution.delay_until(lambda: bot.food_count() > before, 2000)
                if not landed:
                    break
        if bot.food_count() == 0:
            bot.status = 'panic: bank empty — waiting for regen'
            yield from execution.delay_until(lambda: skills.hp_fraction() >= 0.9 or game.in_combat() or chat_dialog.can_continue() or event_signal.pending(), 300000)
        yield from bank.close()


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Bury bones')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not event_signal.pending() and should_bury_regular_bones(bot.bury_bones or bot.bury_big_bones, game.in_combat(), bank.is_open(),
                                                                        len(bot.burial_bones()), inventory.is_full())

    def execute(self):
        bot = self.bot
        bones = bot.burial_bones()
        if not bones:
            return
        bone = bones[0]
        bot.status = f'burying {(bone.name or "").lower()}'
        before = inventory.count_by_id(bone.id)
        if not bone.interact('Bury'):
            bot.log(f'could not bury {bone.name}')
            yield from execution.delay_ticks(2)
            return
        buried = yield from execution.delay_until(lambda: inventory.count_by_id(bone.id) < before, 3000)
        if buried:
            bot.buried += 1
            bot.log(f'buried {bone.name}')


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Bank run')
        self.bot = bot

    def _loot_full(self):
        bot = self.bot
        return bot.auto_bank and should_bank(bot.loot_slots(), bot.bank_at, inventory.is_full())

    def _out_of_food(self):
        bot = self.bot
        return bot.food_count() == 0 and bot.food_withdraw > 0 and not bot.bank_food_empty

    def validate(self):
        bot = self.bot
        out_of_supplies = bot.fully_out_of_supplies()
        if game.in_combat() and not out_of_supplies:
            return False
        if bot.food_count() > 0:
            bot.bank_food_empty = False
        if bot.style != 'melee' and bot.supply_metric() >= bot.restock_threshold():
            bot.supply_empty = False
        return bot.bank_after_solve or self._loot_full() or bot.due_for_timed_bank() or self._out_of_food() \
            or (bot.style != 'melee' and bot.need_style_supplies() and not bot.supply_empty)

    def execute(self):
        bot = self.bot
        destination = bot.pick_bank(game.tile())
        if destination is None:
            bot.bank_after_solve = False
            return
        if bot.bank_after_solve:
            reason = 'clue solved'
        elif self._loot_full():
            reason = f'loot {bot.loot_slots()}/{bot.bank_at} slots or inventory full'
        elif bot.due_for_timed_bank():
            reason = f'time {bot.minutes_since_bank():.1f}m/{bot.bank_every_minutes}m with loot'
        elif self._out_of_food():
            reason = 'out of food'
        elif bot.style != 'melee' and bot.need_style_supplies():
            reason = f'supplies below threshold ({bot.supply_metric()} < {bot.restock_threshold()})'
        else:
            reason = 'unknown'
        bot.log(f'BankRun triggered: {reason}')
        bot.status = 'clue done — banking the loot' if bot.bank_after_solve else 'banking'
        bot.log(f"banking at the {destination['name']} bank ({bot.bank_tile_of(destination)})")
        bot.note_forced_fallback(destination)
        say = lambda m: bot.log(f'  {m}')
        arrived = yield from traversal.walk_resilient(bot.bank_tile_of(destination), radius=3, attempts=4, timeout_ms=300000, log=say)
        if not arrived:
            return
        opened = yield from open_bank_access(destination, BOOTH, log=say)
        if not opened:
            return
        ammo = [bot.ammo] if bot.style == 'range' else []
        yield from bank.deposit_all_matching(lambda name, id: not should_keep_bank_item(name, id, bot.food, bot.bank_common, ammo, bot.tracked_gear,
                                                                                        bot.bury_bones, bot.bury_big_bones))
        for _ in range(bot.food_withdraw):
            if bot.food_count() >= bot.food_withdraw or inventory.is_full():
                break
            before = bot.food_count()
            if not bank.withdraw(bot.food, 'Withdraw-1'):
                break
            landed = yield from execution.delay_until(lambda: bot.food_count() > before, 2000)
            if not landed:
                break
        if bot.food_count() == 0 and bot.food_withdraw > 0:
            bot.bank_food_empty = True
            bot.log(f"no '{bot.food}' in the bank — fighting on without food (foodless safety disarmed)")
        yield from self._restock_style_supplies()
        bot.bank_after_solve = False
        bot.trips += 1
        bot.last_bank_at = now_ms()
        bot.status = 'heading back to the spot'
        # Why: an open bank left behind blocks eating and fighting at the anchor.
        yield from bank.close()
        yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=4, timeout_ms=300000, log=say)

    def _restock_style_supplies(self):
        bot = self.bot
        if bot.style == 'melee':
            bot.supply_empty = False
            return
        if bot.style == 'mage':
            bot.status = 'withdrawing runes'
            for row in rune_withdraw_list(bot.spell, bot.wielded_names(), bot.runes_withdraw):
                if inventory.count(row['rune']) < row['count']:
                    got = yield from withdraw_to(row['rune'], row['count'])
                    bot.log(f"withdrew {got} {row['rune']} ({inventory.count(row['rune'])}/{row['count']})")
            after = bot.casts_left()
            bot.log(f'runes restocked: {after} casts left (re-bank threshold {bot.restock_threshold()})')
            if after < bot.restock_threshold():
                bot.supply_empty = True
                bot.log(f"WARNING: bank can't top runes up to {bot.restock_threshold()} casts — pausing ammo bank runs (have {after})")
            else:
                bot.supply_empty = False
            return
        bot.status = f'restocking {bot.ammo}'
        got = yield from withdraw_to(bot.ammo, bot.ammo_withdraw)
        if got > 0:
            bot.log(f'withdrew {got} {bot.ammo} ({bot.total_ammo()} total in quiver + inventory)')
        if inventory.count(bot.ammo) > 0 and bot.wielded_ammo() == 0:
            equipped = yield from equipment.equip(bot.ammo)
            if equipped:
                bot.log(f'equipped {bot.ammo} ({bot.wielded_ammo()} in quiver)')
            else:
                bot.log(f'WARNING: could not equip {bot.ammo} — will retry from inventory')
        after = bot.total_ammo()
        if after < bot.restock_threshold():
            bot.supply_empty = True
            bot.log(f"WARNING: bank can't supply {bot.ammo} up to {bot.restock_threshold()} — pausing ammo bank runs (have {after})")
        else:
            bot.supply_empty = False
            bot.log(f'ammo ready: {after} total ({bot.wielded_ammo()} quiver, {inventory.count(bot.ammo)} inventory)')


class SetAttackStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0
        self.announced = False

    def _selected(self):
        bot = self.bot
        return game.combat_mode() == bot.range_mode if bot.style == 'range' else game.has_combat_style(bot.melee_style)

    def validate(self):
        # Why: com_mode isn't saved, so it's set again whenever it disagrees; style clicks are fine mid-fight, and
        # continuous combat starves a set gated on being out of combat.
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
            if not self.announced:
                self.announced = True
                if bot.style == 'range':
                    bot.log(f"ranged style set to {['accurate', 'rapid', 'longrange'][bot.range_mode]}")
                else:
                    resolution = game.combat_style_resolution(bot.melee_style)
                    bot.log(f'combat style: {describe_combat_style(resolution) if resolution else bot.melee_style}')
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + 60000
            bot.log(f'could not set the {bot.style} attack style (combat tab not ready?) — retrying in 60s')


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.style != 'mage' or autocast.armed() or now_ms() < self.retry_at:
            return False
        if bot.casts_left() < 1:
            return False
        return autocast.staff_tab_attached()

    def execute(self):
        bot = self.bot
        bot.status = f'arming autocast: {bot.spell}'
        yield from execution.delay_ticks(3)
        armed = yield from autocast.arm(bot.spell, lambda m: bot.log(m))
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + 60000
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}' — retrying in 60s (check spell/level, and that a staff is wielded).")


# Why: Fight's validate is false while already in combat, so a fight from retaliation would never reach the inline
# arm.
class ArmSpecial(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Arm special')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        return now_ms() >= self.retry_at and self.bot.special_due()

    def execute(self):
        bot = self.bot
        bot.status = 'arming the special attack'
        armed = yield from bot.arm_special()
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + 60000
            bot.log(f'WARNING: could not arm the {special.wielded()} special (combat tab not ready?) — retrying in 60s')


class ReequipGear(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Reequip gear')
        self.bot = bot
        self.last_fail_log_at = 0

    def _candidates(self):
        bot = self.bot
        gear = list(bot.tracked_gear)
        if bot.style == 'range' and len([g for g in gear if g.lower() == bot.ammo.lower()]) == 0:
            gear.append(bot.ammo)
        return gear

    def validate(self):
        return len([g for g in self._candidates() if not equipment.contains(g) and inventory.first(g) is not None]) > 0

    def execute(self):
        bot = self.bot
        for item in self._candidates():
            if equipment.contains(item) or inventory.first(item) is None:
                continue
            bot.status = f're-equipping {item}'
            equipped = yield from equipment.equip(item)
            if equipped:
                bot.log(f'equipped {item}')
            elif now_ms() > self.last_fail_log_at:
                self.last_fail_log_at = now_ms() + 30000
                bot.log(f'WARNING: could not equip {item} (not wieldable / no weapon slot?) — retrying')


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Fight')
        self.bot = bot
        self.skipped = {}

    def _key(self, npc):
        return f'{npc.index}:{npc.id}'

    def _eligible(self, npc):
        return (npc.targets_me() or not npc.in_combat) and not npc.targets_another_player() and npc.tile().distance_to(self.bot.anchor) <= self.bot.leash

    def _reachable(self, npc):
        tile = npc.tile()
        here = game.tile()
        if not reachability.probeable(tile):
            return True
        style = self.bot.style
        if style != 'melee' and here is not None and gap_to(here, npc.network_tile(), npc.size) <= attack_range_for(style):
            origin = body_origin(npc.network_tile(), npc.size)
            if reachability.line_of_sight(here, Tile(origin.x, origin.z, tile.level), npc.size):
                return True
        return reachability.can_reach(tile, adjacent_ok=True, max_steps=2048)

    def _skip(self, npc, reason):
        self.skipped[self._key(npc)] = now_ms() + 30000
        self.bot.log(f'skipping {npc.name} at {npc.tile()} for 30s ({reason})')

    def _find_target(self):
        now = now_ms()
        for key in list(self.skipped.keys()):
            if self.skipped[key] <= now:
                self.skipped.pop(key)
        q = npcs.query().action('Attack').where(lambda n: self._eligible(n) and (n.targets_me() or self._key(n) not in self.skipped))
        names = self.bot.target_names()
        if len(names) > 0:
            q.name(names)
        targets = q.results()
        targets.sort(key=lambda n: n.distance())
        for n in targets:
            if n.targets_me():
                return n
        for n in targets:
            if self._reachable(n):
                return n
        return targets[0] if targets else None

    def _track(self, engaged):
        names = self.bot.target_names()
        for n in npcs.all():
            if n.index == engaged.index and n.id == engaged.id and len([name for name in names if matches_entity_name(n.name, name)]) > 0:
                return n
        return None

    def validate(self):
        bot = self.bot
        if bot.need_eat() or skills.hp_fraction() < bot.panic_at:
            return False
        target = self._find_target()
        # Why: a stalled fight stays in combat, so neither the idle branch nor resume_attack ever fires; strike instead
        # when xp has been flat long enough.
        if bot.combat_stalled(STALL_REATTACK_MS):
            return target is not None
        return target is not None and (not game.in_combat() or (bot.resume_attack and target.targets_me()))

    def execute(self):
        bot = self.bot
        target = self._find_target()
        if target is None:
            return
        if not game.in_combat() and not self._reachable(target):
            bot.status = f'approaching {target.name} through obstacles'
            arrived = yield from traversal.walk_to(target.tile(), radius=1, timeout_ms=20000, log=lambda m: bot.log(m))
            if event_signal.pending() or bot.died or bot.need_eat() or skills.hp_fraction() < bot.panic_at or chat_dialog.can_continue():
                return
            current = self._track(target)
            if current is None or not self._eligible(current):
                return
            if not arrived or not self._reachable(current):
                self._skip(current, 'approach blocked')
                return
        bot.status = f'attacking {target.name} at {target.tile()}'
        if bot.resume_attack and target.targets_me():
            if not target.interact('Attack'):
                return
            bot.resume_attack = False

        def find():
            current = self._track(target)
            return current if current is not None and self._eligible(current) else None

        # A wandering target puts off the server's can't-reach verdict forever, so the scene is probed and the door
        # in the way opened here.
        status = yield from reach.entity_op(find, 'Attack', lambda: game.in_combat() or chat_dialog.can_continue(), open_when_unreachable=True,
                                            expect_ms=5000, what=target.name, log=lambda m: bot.log(m))
        if status != 'done' or chat_dialog.can_continue():
            if status != 'done' and not event_signal.pending() and not chat_dialog.can_continue() and not bot.died:
                self._skip(target, status)
            return
        bot.resume_attack = False
        bot.status = 'fighting'
        deadline = now_ms() + 90000
        while now_ms() < deadline:
            if event_signal.pending() or chat_dialog.can_continue() or bot.died:
                return
            if bot.need_eat() or skills.hp_fraction() < bot.panic_at:
                return
            if bot.style == 'range' and bot.wielded_ammo() < bot.restock_threshold() and inventory.count(bot.ammo) > 0:
                bot.log(f'ammo in quiver below {bot.restock_threshold()} — reloading from inventory')
                return
            if bot.fully_out_of_supplies():
                bot.log(f"out of {'runes' if bot.style == 'mage' else 'ammo'} — breaking off to restock")
                return
            current = self._track(target)
            if current is None or (current.health == 0 and current.max_health > 0):
                if current is not None:
                    yield from execution.delay_until(lambda: self._track(target) is None, 10000)
                bot.kills += 1
                yield from execution.delay_ticks(2)
                return
            # Why: auto retaliate only fires on a landed hit, so the loop never sets it off again on a zero-damage enemy;
            # the xp clock stays fresh here while validate attacks again when xp goes flat.
            bot.mark_combat_xp()
            if not game.in_combat() and not current.in_combat:
                return
            # Why: inline, not left to the sibling task; this loop owns the bot until the target dies.
            yield from bot.arm_special()
            yield from execution.delay_ticks(2)


class ReturnToAnchor(Task):
    def __init__(self, bot):
        Task.__init__(self, label='Return to anchor')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and self.bot.anchor.distance_to(here) > self.bot.leash + 6 and not game.in_combat()

    def execute(self):
        bot = self.bot
        bot.status = 'heading to the spot'
        say = lambda m: bot.log(f'  {m}')
        if bot.delegated:
            arrived = yield from traversal.walk_to(bot.anchor, radius=3, timeout_ms=90000, log=say)
            here = game.tile()
            if (not arrived or here is None or bot.anchor.distance_to(here) > 3) and not event_signal.pending():
                bot.request_finish(f'Could not return to combat camp at {bot.anchor}')
        else:
            yield from traversal.walk_resilient(bot.anchor, radius=3, attempts=6, timeout_ms=300000, log=say)


class AutoFighter(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.kills = 0
        self.looted = 0
        self.buried = 0
        self.specials = 0
        self.eats = 0
        self.trips = 0
        self.deaths = 0
        self.bank_food_empty = False
        self.supply_empty = False
        self.status = 'starting'
        self.died = False
        self.resume_attack = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.target = s.str('target', 'Guard').strip() or 'Guard'
        spot_mode = s.str('spot', START_POSITION)
        self.anchor = resolve_killing_spot(spot_mode, game.tile(), s.tile('coordinates', DEFAULT_CUSTOM_SPOT))
        self.leash = s.num('leash_radius', 8)
        self.food = s.str('food', '').strip() or script_food(s, 'Trout')
        self.food_withdraw = s.num('food_withdraw', 10)
        self.panic_at = s.num('panic_hp', 25) / 100
        self.loot = [n.strip().lower() for n in s.list('loot', DEFAULT_LOOT)]
        avoided = s.list('avoid_herbs', [])
        self.avoid_herb_ids = set()
        for herb in HERBS:
            if herb.name in avoided:
                self.avoid_herb_ids.add(herb.id)
                self.avoid_herb_ids.add(herb.unid_id)
        self.bury_bones = s.bool('bury_bones', False)
        self.bury_big_bones = s.bool('bury_big_bones', False)
        self.solve_clues = s.bool('solve_clues', True)
        self.bank_at = s.num('bank_at_loot_slots', 12)
        self.bank_every_minutes = s.num('bank_every_minutes', 0)
        self.auto_bank = auto_bank_enabled(s.str('banking', 'Auto'))
        self.bank_common = s.bool('bank_common_junk', True)
        self.bank_location = s.str('bank_location', 'Nearest')
        forced = self.forced_bank()
        if forced is not None:
            if bank_unlocked(forced):
                self.log(f"bank location: {forced['name']} (forced)")
            else:
                self.log(f"bank location: {forced['name']} is locked — falling back to the nearest bank")
        else:
            self.log('bank location: nearest unlocked bank')
        # Why: older saves stored attack/strength/controlled/defence in combat_style, and option validation turns
        # those into the default 'melee', ignoring the style they chose.
        if self.delegated:
            raw_combat_style = s.str('combat_style', 'melee')
            raw_melee_style = s.str('melee_style', 'strength')
        else:
            raw_combat_style = settings_store.display_string('AutoFighter', 'combat_style', SETTINGS['combat_style'])
            raw_melee_style = settings_store.saved('AutoFighter', 'melee_style')
        split = resolve_split_combat_settings(raw_combat_style, raw_melee_style)
        self.style = split.kind
        self.melee_style = split.melee_style
        if not self.delegated and split.legacy_migrated is not None:
            settings_store.save('AutoFighter', 'combat_style', 'melee')
            settings_store.save('AutoFighter', 'melee_style', split.legacy_migrated)
            self.log(f"migrated legacy combat_style='{raw_combat_style.strip()}' → melee_style='{split.legacy_migrated}'")
        elif not self.delegated and try_parse_combat_style(raw_combat_style) is not None:
            # The setting still holds a training style while melee_style is already set, so only combat_style is
            # rewritten.
            settings_store.save('AutoFighter', 'combat_style', 'melee')
        self.use_special = s.bool('use_special', True)
        self.spell = s.str('spell', 'Fire Strike')
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        self.ammo = s.str('ammo', 'Bronze arrow')
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        self.ammo_restock_below = s.num('ammo_restock_below', 25) / 100
        self.tracked_gear = [i.name for i in equipment.items() if i.name]
        self.clues_solved = 0
        self.bank_after_solve = False
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda name: matches_any(name, [self.food]),
                                                  food_name=lambda: self.food, food_withdraw=lambda: self.food_withdraw, enabled=lambda: self.solve_clues))

        def sustain_eat():
            # Why: with the bank open the backpack shows the bank's Deposit ops, so Eat fails and the loop spins.
            if bank.is_open() or not self.need_eat():
                return
            food = self.first_food()
            if food is not None:
                before = skills.effective('hitpoints')
                if food.interact('Eat'):
                    self.resume_attack = True
                    yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)

        sustain.set(sustain_eat)
        self.started_at = time.time()
        self.last_bank_at = now_ms()
        self.xp_at_start = self.combat_xp_total()
        self.combat_xp_last = self.combat_xp_total()
        self.combat_xp_gain_at = now_ms()
        if self.style == 'mage':
            style_note = f' ({self.spell}, {self.runes_withdraw} casts)'
        elif self.style == 'range':
            style_note = f" ({['accurate', 'rapid', 'longrange'][self.range_mode]}, {self.ammo}x{self.ammo_withdraw})"
        else:
            style_note = f' ({self.melee_style})'
        every = f' every {self.bank_every_minutes}m' if self.bank_every_minutes > 0 else ''
        bones = f', burying {BURIAL_BONE_NAME}' if self.bury_bones else ''
        big = ', burying Big bones' if self.bury_big_bones else ''
        self.log(f"AutoFighter starting — '{', '.join(self.target_names())}' at {spot_mode} {self.anchor} r{self.leash}, style {self.style}{style_note}, "
                 + f"banking {'auto' if self.auto_bank else 'none'}{every} at {self.bank_location}, food '{self.food}'x{self.food_withdraw}, "
                 + f"loot [{', '.join(self.loot)}]{bones}{big}")
        self.add(
            ContinueDialog(),
            DeathRecovery(self, self.anchor, 6, on_death=self.died_now, on_recovered=self.recovered),
            EnableAutoRetaliate(self), EatFood(self), PanicRetreat(self), BuryBones(self), LootDrops(self), ReequipGear(self), self.solve_clue,
            BankRun(self),
            SetAttackStyle(self), ArmAutocast(self), ArmSpecial(self), Fight(self), ReturnToAnchor(self),
        )

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.deaths += 1
        self.solve_clue.note_death()
        self.log('died! waiting for respawn, then walking back to the spot')

    def recovered(self):
        self.died = False

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
            self.bank_after_solve = True
        self.status = text

    def grind_targets(self):
        return [n.lower() for n in self.target_names()]

    def recovery_anchor(self):
        return self.anchor

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        xp = self.combat_xp_total() - self.xp_at_start
        if self.style == 'mage':
            supplies = ('Casts', self.casts_left())
        elif self.style == 'range':
            supplies = ('Ammo', self.total_ammo())
        else:
            supplies = ('Style', self.melee_style)
        report = {
            'Status': self.status,
            'Kills': self.kills,
            'Looted': self.looted,
            supplies[0]: supplies[1],
            'Food': self.food_count(),
            'Trips': self.trips,
            'Deaths': self.deaths,
            'Bones': self.buried,
            'Specials': self.specials,
            'XP/hr': f'{(xp / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report

    def target_names(self):
        return [n.strip() for n in self.target.split(',') if n.strip()]

    # Banks

    def forced_bank(self):
        """The bank bank_location names, or None for Nearest."""
        if self.bank_location == 'Nearest':
            return None
        for b in BANK_LOCATIONS:
            if b['name'] == self.bank_location:
                return b
        return None

    def pick_bank(self, here):
        """The bank a trip uses: the forced one when it's unlocked, else the nearest."""
        forced = self.forced_bank()
        if here is not None and forced is not None and bank_unlocked(forced):
            return forced
        return nearest_bank_reachable(here, navigator) if here is not None else None

    def note_forced_fallback(self, chosen):
        forced = self.forced_bank()
        if forced is not None and chosen['name'] != forced['name']:
            self.log(f"bank: {forced['name']} is locked — using {chosen['name']} instead")

    def bank_tile_of(self, b):
        tile = b['tile']
        return Tile(tile['x'], tile['z'], tile['level'])

    def minutes_since_bank(self):
        return (now_ms() - self.last_bank_at) / 60000

    def due_for_timed_bank(self):
        return should_bank_after_minutes(self.auto_bank, self.bank_every_minutes, self.minutes_since_bank(), self.loot_count())

    # Food and loot

    def is_avoided_herb(self, id):
        return id in self.avoid_herb_ids

    def food_count(self):
        return count_matching(inventory.items(), [self.food])

    def first_food(self):
        for item in inventory.items():
            if matches_any(item.name, [self.food]):
                return item
        return None

    def need_eat(self):
        return should_eat(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food), self.food_count())

    def is_loot(self, name):
        return wants_auto_fighter_loot(name, self.loot, self.bury_bones, self.bury_big_bones)

    def burial_bones(self):
        return [i for i in inventory.items() if not i.noted and is_burial_bone(i.name, self.bury_bones, self.bury_big_bones)
                and len([a for a in i.actions() if a.lower() == 'bury']) > 0]

    def loot_count(self):
        return sum([i.count for i in inventory.items() if self.is_loot(i.name)])

    def loot_slots(self):
        return len([i for i in inventory.items() if self.is_loot(i.name)])

    # Specials and supplies

    def spec_weapon(self):
        """The wielded weapon when it carries a special this bot may arm, else ''."""
        weapon = special.wielded()
        return weapon if special_available(self.use_special, self.style, special.cost(weapon)) else ''

    def special_due(self):
        return should_arm_special(self.use_special, self.style, special.cost(special.wielded()), special.energy(), special.armed())

    # Why: arming is one-shot; the next attack spends it and the engine clears the flag, so it's armed again for each.
    def arm_special(self):
        weapon = special.wielded()
        if not self.special_due():
            return False
        armed = yield from special.arm()
        if not armed:
            return False
        self.specials += 1
        self.log(f'special armed with {weapon} (bar at {round(special.energy() / 10)}%, spent on the next hit)')
        return True

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def wielded_ammo(self):
        wanted = self.ammo.lower()
        for item in equipment.items():
            if (item.name or '').lower() == wanted:
                return item.count
        return 0

    def total_ammo(self):
        return inventory.count(self.ammo) + self.wielded_ammo()

    def restock_threshold(self):
        return max(1, int(self.ammo_restock_below * (self.runes_withdraw if self.style == 'mage' else self.ammo_withdraw)))

    def supply_metric(self):
        return self.casts_left() if self.style == 'mage' else self.total_ammo()

    def need_style_supplies(self):
        return self.style != 'melee' and self.supply_metric() < self.restock_threshold()

    def fully_out_of_supplies(self):
        return self.style != 'melee' and self.supply_metric() == 0

    def combat_xp_total(self):
        return sum([skills.xp(skill) for skill in COMBAT_SKILLS])

    def mark_combat_xp(self):
        xp = self.combat_xp_total()
        if xp > self.combat_xp_last:
            self.combat_xp_last = xp
            self.combat_xp_gain_at = now_ms()

    def combat_stalled(self, ms):
        return now_ms() - self.combat_xp_gain_at > ms


BOT = define_bot(
    name='AutoFighter',
    create=AutoFighter,
    description='Start-or-coordinate fighter — kills any named NPC in its leash, loots selected drops, auto-banks, solves clues, and returns to the killing spot',
    category='Combat',
    tags=['combat', 'clues', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

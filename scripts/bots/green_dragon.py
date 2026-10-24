# Fights the green dragons in the wilderness north of Edgeville with melee or magic behind a Dragonfire shield, and
# banks the bones and hides at Edgeville, sipping super attack and strength mid-fight: rs2b0t's GreenDragon (MIT,
# see thirdparty/rs2b0t). It flees to the bank, or teleports to Varrock, when a player attacks or it's out of food
# and low. It solves the hard clues the dragons drop, the trail running out of the wilderness and back.

import time

from bots.greendragon.logic import AT_BANK_RADIUS, RETURN_HOLD_MS, LootFilter, escape_needed, gear_candidates, gear_to_keep
from bots.greendragon.logic import is_grind_foreign, pack_forces_bank, slot_freeing_action, under_player_attack, wants_ground_item
from rs2004.bot import is_generator
from rs2004.catalogs import EMPTY_VIAL, LOADOUT_SETTING, MELEE_WEAPONS, SPELL_DB, STAFFS, URGENT_HP_FRACTION, AttackClock, ContinueDialog
from rs2004.catalogs import DeathRecovery, bury_one_in_fight, casts_available, combat_keep_names, drop_db, food_count, food_forms
from rs2004.catalogs import food_heal_amount, is_food_item, planned_potions, potion_to_sip, rune_withdraw_list, script_food
from rs2004.catalogs import selected_loadout, should_eat_to_use_food, should_hold_eat, supplies_of, swing_started_this_tick
from rs2004.clues import SolveClue, SolveClueHost

TARGET = 'Green dragon'
DEFAULT_ANCHOR = Tile(3096, 3814, 0)
DEFAULT_BANK = Tile(3094, 3493, 0)
FIELD_RADIUS = 22
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
# Teleports work at wilderness level 20 and below, which is south of this row.
TELE_SAFE_Z = 3665
VARROCK_TELE_RUNES = [('Law rune', 1), ('Air rune', 3), ('Fire rune', 1)]
TELE_STOCK = 2
BONE_NAME = 'Dragon bones'
# The drop table names it plainly, and it's the headline drop.
HIDE_NAME = 'Dragonhide'
GRIND_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}

DROPS = drop_db().get(TARGET) or []
DEFAULT_LOOT = [n for n in DROPS if n.lower() != 'bass']

SETTINGS = {
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage'], help='range is unavailable — a bow blocks the anti-dragon shield slot'),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE),
    'use_special': SettingDef('boolean', True, 'Use special attacks', group='Combat', show_if=SHOW_MELEE,
                              help='arms the spec bar whenever energy allows and the wielded weapon has one (dragon dagger, dragon longsword, …); does nothing with a weapon that has no special'),
    'weapon': SettingDef('string', 'Rune scimitar', 'Weapon', options=MELEE_WEAPONS, group='Combat', show_if=SHOW_MELEE,
                         help='1-handed (keeps the shield slot free), withdrawn from bank when missing'),
    'staff': SettingDef('string', 'Staff of fire', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE),
    'spell': SettingDef('string', 'Fire Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE),
    'shield': SettingDef('string', 'Dragonfire shield', 'Anti-dragon shield', options=['Dragonfire shield'], group='Combat', help='worn to absorb the dragonfire — required'),
    'use_potions': SettingDef('boolean', True, 'Drink super attack / strength', group='Combat', show_if=SHOW_MELEE,
                              help="sips a dose mid-fight once the boost decays to within a tenth of the base level; the loadout's carry list sets the dose form and how many flasks per trip, otherwise one Super attack(3) and one Super strength(3)"),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 30, 'Escape below HP%', 1, 98, group='Food & healing', help='when out of food and this low, escape to the bank'),
    'food_reserve': SettingDef('number', 4, 'Food kept back from slot-freeing', 0, 27, group='Food & healing',
                               help='a full pack spends food to make room for loot instead of banking — never below this many'),
    'solve_clues': SettingDef('boolean', True, 'Solve clue drops', group='Clues', help='green dragons drop hard clues — the trail runs out of the wilderness and back'),
    'escape': SettingDef('string', 'Flee to bank', 'Escape mode', options=['Flee to bank', 'Teleport to Varrock'], group='Wilderness',
                         help='Teleport brings Varrock runes and runs south to level 20 to cast (teleports are blocked above level 20 wilderness)'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot',
                       help='Dragon bones + Dragonhide + the rest of the green dragon table; everything picked up is banked.'),
    'bury_bones': SettingDef('boolean', False, 'Bury dragon bones', group='Banking & loot',
                             help=f'bury {BONE_NAME} for Prayer xp instead of banking them (always looted when on) — they are the most valuable drop, so this trades gold for xp'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'anchor_tile': SettingDef('tile', DEFAULT_ANCHOR, 'Dragon field tile', group='Location'),
    'bank_tile': SettingDef('tile', DEFAULT_BANK, 'Bank stand tile (Edgeville)', group='Location'),
    'log_detail': SettingDef('string', 'Normal', 'Log detail', options=['Normal', 'Verbose'], group='Diagnostics',
                             help='Verbose adds task-switch and decision traces (pack census, loot skips, slot freeing, escape reasons)'),
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


def potions_held(plan):
    """The flasks of one potion held, counting every dose form."""
    return sum([inventory.count(dose) for dose in plan.potion.doses])


def has_varrock_runes():
    for rune, count in VARROCK_TELE_RUNES:
        if inventory.count(rune) < count:
            return False
    return True


def loot_stacks_into_pack(name):
    """Loot that merges into a stack already held needs no slot."""
    if not name:
        return False
    held = inventory.first(name)
    return held is not None and held.count > 1


# Shared by the Eat task and slot freeing, so both respect the swing.
attack_clock = AttackClock()


class Traced(Task):
    """Names the winning task, so Verbose can trace control flow, hand-overs included."""

    def __init__(self, bot, name, inner):
        Task.__init__(self, label=getattr(inner, 'label', name))
        self.bot = bot
        self.name = name
        self.inner = inner

    def validate(self):
        ok = self.inner.validate()
        if is_generator(ok):
            ok = yield from ok
        if ok:
            self.bot.note_task(self.name)
        return ok

    def execute(self):
        result = self.inner.execute()
        if is_generator(result):
            yield from result


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return self.bot.need_eat()

    # Why: eating spends the tick it lands on, so a meal on the swing costs an attack; low enough health makes
    # waiting the greater risk.
    def execute(self):
        """Holds one tick and takes the meal in the swing cooldown."""
        tick = game.tick()
        attack_clock.observe(players.local().animation, tick)
        hold = game.in_combat() and should_hold_eat(attack_clock.attacked_this_tick(tick), skills.hp_fraction(), URGENT_HP_FRACTION)
        if hold:
            yield from execution.delay_ticks(1)
        yield from self.bot.eat_once()


class GearEquip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='gear equip')
        self.bot = bot
        self.fails = 0

    def _missing(self):
        bot = self.bot
        for name in gear_candidates(bot.weapon, bot.shield, bot.tracked_gear):
            if name != '' and not equipment.contains(name) and inventory.first(name) is not None:
                return name
        return None

    def validate(self):
        return self.fails < 5 and self._missing() is not None

    def execute(self):
        bot = self.bot
        item = self._missing()
        if item is None:
            return
        bot.status = f'equipping {item}'
        equipped = yield from equipment.equip(item)
        if equipped:
            bot.log(f'equipped {item}')
            self.fails = 0
        else:
            self.fails += 1


class SetAttackStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set attack style')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        return bot.style == 'melee' and not game.has_combat_style(bot.melee_style) and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        bot.status = 'setting combat style'
        game.set_combat_style(bot.melee_style)
        ok = yield from execution.delay_until(lambda: game.has_combat_style(bot.melee_style), 3000)
        if ok:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            bot.log(f'could not set the melee attack style — retrying in {ASSERT_RETRY_MS // 1000}s')


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
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}' — retrying in {ASSERT_RETRY_MS // 1000}s.")


class Escape(Task):
    def __init__(self, bot):
        Task.__init__(self, label='escape')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return escape_needed(bot.under_attack(), skills.hp_fraction(), bot.panic_hp, bot.has_food(), bot.at_bank())

    def execute(self):
        bot = self.bot
        attacked = bot.under_attack()
        if attacked:
            bot.hold_return(RETURN_HOLD_MS)
        why = 'under attack' if attacked else 'low hp'
        say = lambda m: bot.log(f'  {m}')
        if bot.tele_escape and has_varrock_runes():
            me = game.tile()
            if me is not None and me.z > TELE_SAFE_Z:
                bot.status = 'escaping — running south to teleport range'
                bot.log(f'escaping ({why}) — running to <=lvl20')
                yield from traversal.walk_resilient(Tile(bot.anchor.x, TELE_SAFE_Z - 5, 0), radius=4, attempts=3, timeout_ms=60000, log=say)
                return
            bot.status = 'escaping — Varrock teleport'
            teleported = yield from bot.cast_varrock_tele()
            if teleported:
                bot.log('teleported to Varrock')
                return
            bot.log('Varrock teleport did not fire — fleeing on foot')
        bot.status = 'escaping — fleeing to the bank'
        bot.log(f'escaping ({why}) — fleeing to {bot.bank_tile}')
        yield from traversal.walk_resilient(bot.bank_tile, radius=3, attempts=6, timeout_ms=240000, log=say)


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.under_attack():
            return False
        if bot.needs_resupply():
            return True
        foreign = bot.foreign_kit()
        if len(foreign) > 0:
            bot.vlog(f"holding trail leftovers [{', '.join(foreign)}] — banking to restock the grind kit")
            return True
        return pack_forces_bank(inventory.is_full(), bot.food_count(), bot.food_reserve)

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.status = 'banking — restocking'
        casts = f', casts {bot.casts_left()}' if bot.style == 'mage' else ''
        bot.log(f'banking (food {bot.food_count()}{casts})')
        yield from bot.bank_routine()


# Why: a vial is neither grind kit nor loot, so left in the pack is_grind_foreign reads it as clue-trail junk and
# sends the bot to Edgeville every time a flask empties.
class DropVial(Task):
    """Catches a vial the fight loop didn't, before it can force a bank trip."""

    def __init__(self, bot):
        Task.__init__(self, label='drop vial')
        self.bot = bot

    def validate(self):
        return len(self.bot.potions) > 0 and not self.bot.under_attack() and inventory.contains(EMPTY_VIAL)

    def execute(self):
        yield from self.bot.drop_vial()


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        return self.bot.bury_bones and now_ms() >= self.retry_at and inventory.contains(BONE_NAME)

    def execute(self):
        bot = self.bot
        bones = inventory.first(BONE_NAME)
        if bones is None:
            return
        bot.status = f'burying {BONE_NAME}'
        before = inventory.used()
        if not bones.interact('Bury'):
            bot.log(f"no Bury op on {BONE_NAME}? ops=[{', '.join(bones.actions())}]")
            self._note_fail()
            yield from execution.delay_ticks(2)
            return
        buried = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
        if buried:
            bot.buried += 1
            bot.vlog(f'buried {BONE_NAME} ({bot.buried} total)')
            self.fails = 0
            return
        self._note_fail()

    def _note_fail(self):
        """A stuck burial mustn't starve the tasks below it."""
        self.fails += 1
        if self.fails >= ASSERT_BATCH:
            self.fails = 0
            self.retry_at = now_ms() + ASSERT_RETRY_MS
            self.bot.log(f'could not bury {BONE_NAME} — pausing burial for {ASSERT_RETRY_MS // 1000}s')


class FreeSlot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='free slot')
        self.bot = bot

    def validate(self):
        return not self.bot.under_attack() and self.bot.slot_decision()[0] != 'none'

    def execute(self):
        yield from self.bot.free_slot_for_loot()


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.under_attack() or bot.find_loot() is None:
            return False
        if inventory.is_full():
            bot.vlog_change('lootskip', 'loot on the ground but the pack is full and no slot could be freed — banking')
            return False
        return True

    def execute(self):
        yield from self.bot.loot_once()


# Why: held off briefly after an escape from a threat, so it doesn't walk straight back into the player that caused
# it.
class ReturnToField(Task):
    """Takes back control wherever the bot ended up away from the field."""

    def __init__(self, bot):
        Task.__init__(self, label='return to field')
        self.bot = bot

    def validate(self):
        bot = self.bot
        here = game.tile()
        if here is None or game.in_combat() or bot.anchor.distance_to(here) <= FIELD_RADIUS + 6:
            return False
        hold = bot.return_hold_remaining()
        if hold > 0:
            bot.vlog(f'away from the field but holding {int(hold // 1000) + 1}s after an escape')
            return False
        return True

    def execute(self):
        bot = self.bot
        bot.status = 'returning to the dragon field'
        bot.log(f'returning to the field at {bot.anchor}')
        yield from traversal.walk_resilient(bot.anchor, radius=4, attempts=6, timeout_ms=300000, log=lambda m: bot.log(f'  {m}'))


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.target_idx = None

    def validate(self):
        bot = self.bot
        return not bot.under_attack() and skills.hp_fraction() >= bot.panic_hp and len(bot.field_dragons()) > 0

    def execute(self):
        bot = self.bot
        bot.status = 'fighting green dragons'
        deadline = now_ms() + 120000
        while now_ms() < deadline:
            if event_signal.pending() or bot.died or chat_dialog.can_continue() or bot.under_attack():
                return
            # This loop owns the bot for up to two minutes, long enough to die without food, so it hands back for
            # the bank run.
            if bot.needs_resupply():
                bot.vlog('out of supplies mid-fight — yielding to the bank run')
                return
            if bot.need_eat():
                yield from bot.eat_once()
                continue
            if skills.hp_fraction() < bot.panic_hp:
                return
            dragons = bot.field_dragons()
            if self.target_idx is not None and len([d for d in dragons if d.index == self.target_idx]) == 0:
                bot.kills += 1
                bot.log(f'green dragon down — {bot.kills} kills')
                self.target_idx = None
            if bot.find_loot() is not None:
                # Inline, not a sibling task: a task hop per item loses drops.
                if inventory.is_full():
                    freed = yield from bot.free_slot_for_loot()
                    if freed:
                        continue
                if not inventory.is_full():
                    yield from bot.loot_once()
                    continue
            # Why: this loop owns the bot for the kill, so a special attack task above Fight never runs in combat.
            if bot.use_special and not special.armed() and special.ready(bot.weapon) and equipment.contains(bot.weapon):
                armed = yield from special.arm()
                if armed:
                    bot.specials += 1
                    bot.vlog(f'special armed ({special.energy()}/{SA_MAX_ENERGY} energy left)')
            if game.in_combat():
                # Why: the dose is due once every few minutes while a bone waits at no cost, and reaching here is itself
                # the "only sip while fighting a dragon" gate.
                sipped = yield from bot.sip_upkeep()
                if sipped:
                    yield from execution.delay_ticks(1)
                    continue
                # Why: burying costs a tick like eating, so spend it in the swing cooldown; inline, since a sibling task
                # only runs when Fight yields.
                if bot.bury_bones:
                    buried = yield from bury_one_in_fight(BONE_NAME)
                    if buried:
                        bot.buried += 1
                        bot.vlog(f'buried {BONE_NAME} ({bot.buried} total)')
                yield from execution.delay_ticks(2)
                continue
            dragons.sort(key=lambda d: d.distance())
            if not dragons:
                return
            dragon = dragons[0]
            bot.vlog(f'attacking green dragon #{dragon.index} at {dragon.distance()} tiles')
            dragon.interact('Attack')
            self.target_idx = dragon.index
            yield from execution.delay_until(lambda: game.in_combat() or len(bot.field_dragons()) == 0, 4000)


class GreenDragon(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.looted = 0
        self.bank_trips = 0
        self.supply_empty = False
        self.bank_empty = False
        self.slots_freed = 0
        self.specials = 0
        self.buried = 0
        self.sips = 0
        self.potion_warned = set()
        self.loot_counts = {}
        self.last_task = ''
        self.last_vlog = {}
        self.hold_return_until = 0
        self.died = False
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.style = s.str('combat_style', 'melee')
        self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.spell = s.str('spell', 'Fire Strike')
        self.weapon = s.str('staff', 'Staff of fire') if self.style == 'mage' else s.str('weapon', 'Rune scimitar')
        self.shield = s.str('shield', 'Dragonfire shield')
        self.use_special = s.bool('use_special', True)
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in GRIND_SKILLS])
        self.food_name = script_food(s, 'Lobster')
        self.panic_hp = s.num('panic_hp', 30) / 100
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.food_withdraw = s.num('food_withdraw', 20)
        self.loot_set = set([n.lower() for n in s.list('loot', DEFAULT_LOOT)])
        self.bank_common = s.bool('bank_common_junk', True)
        self.tele_escape = s.str('escape', 'Flee to bank') == 'Teleport to Varrock'
        self.anchor = s.tile('anchor_tile', DEFAULT_ANCHOR)
        self.bank_tile = s.tile('bank_tile', DEFAULT_BANK)
        self.food_reserve = s.num('food_reserve', 4)
        self.bury_bones = s.bool('bury_bones', False)
        self.solve_clues = s.bool('solve_clues', True)
        self.verbose = s.str('log_detail', 'Normal') == 'Verbose'
        # Why: attack and strength boosts do nothing for a spell's damage, so magic runs carry no flasks.
        if self.style == 'melee' and s.bool('use_potions', True):
            self.potions = planned_potions(supplies_of(selected_loadout(s)))
        else:
            self.potions = []
        self.tracked_gear = [i.name for i in equipment.items() if i.name]
        self.clues_solved = 0
        self.solve_clue = SolveClue(SolveClueHost(log=self.log, set_status=self.clue_status, is_food=lambda name: is_food_item(name, self.food_name),
                                                  food_name=lambda: self.food_name, food_withdraw=lambda: self.food_withdraw,
                                                  weapon_name=lambda: self.weapon, enabled=lambda: self.solve_clues))
        yield from self.assert_auto_retaliate()
        mage = f' ({self.spell})' if self.style == 'mage' else ''
        escape = 'Varrock tele' if self.tele_escape else 'flee to bank'
        burying = f', burying {BONE_NAME}' if self.bury_bones else ''
        potions = ' + '.join([f'{p.want}x {p.flask}' for p in self.potions]) if self.potions else 'off'
        self.log(f"GreenDragon — style {self.style} w/ {self.weapon} + {self.shield}{mage}, food '{self.food_name}' (reserve {self.food_reserve}), "
                 + f"escape '{escape}', clues {'on' if self.solve_clues else 'off'}{burying}, potions {potions}, field {self.anchor}, bank {self.bank_tile}")
        self.vlog(f"verbose logging on — loot set [{', '.join(sorted(self.loot_set))}], common junk {'on' if self.bank_common else 'off'}")
        traced = lambda name, task: Traced(self, name, task)
        self.add(
            traced('ContinueDialog', ContinueDialog()),
            traced('DeathRecovery', DeathRecovery(self, self.bank_tile, 6, on_death=self.died_now, on_recovered=self.recovered)),
            traced('Escape', Escape(self)),
            traced('Eat', Eat(self)),
            traced('GearEquip', GearEquip(self)),
            traced('SetAttackStyle', SetAttackStyle(self)),
            traced('ArmAutocast', ArmAutocast(self)),
            traced('DropVial', DropVial(self)),
            # Above SolveClue: a trail's bank stop would otherwise deposit the bones it was told to bury.
            traced('BuryBones', BuryBones(self)),
            traced('SolveClue', self.solve_clue),
            traced('FreeSlot', FreeSlot(self)),
            traced('BankRun', BankRun(self)),
            traced('LootCorpse', LootCorpse(self)),
            traced('Fight', Fight(self)),
            traced('ReturnToField', ReturnToField(self)),
        )

    def died_now(self):
        self.died = True
        self.status = 'died — recovering'
        self.solve_clue.note_death()
        self.log('died! recovering')

    def recovered(self):
        self.died = False
        # A death can leave auto retaliate off, and without it there's no warning of a player killer.
        if not game.auto_retaliate_on():
            game.set_auto_retaliate(True)

    def recovery_anchor(self):
        return self.bank_tile

    # SolveClue's host

    def clue_status(self, text):
        if text == 'clue solved':
            self.clues_solved += 1
        self.status = text

    def grind_targets(self):
        return [TARGET.lower()]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in GRIND_SKILLS]) - self.xp_at_start
        report = {
            'Status': self.status,
            'Kills': self.kills,
            'Looted': self.looted,
            'Hides': self.loot_counts.get(HIDE_NAME, 0),
            'Bones': self.loot_counts.get(BONE_NAME, 0),
            'Bank trips': self.bank_trips,
            'Specials': self.specials,
            'Sips': self.sips,
            'Buried': self.buried,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.solve_clues:
            report['Clues'] = self.clues_solved
            report['Clue'] = self.solve_clue.clue_status()
        return report

    # Logging

    def vlog(self, message):
        """Silent unless log_detail is Verbose, so the log keeps what matters."""
        if self.verbose:
            self.log(message)

    def vlog_change(self, key, message):
        """Verbose, but only when the message changes; hot loops repeat."""
        if self.last_vlog.get(key) == message:
            return
        self.last_vlog[key] = message
        self.vlog(message)

    def note_task(self, name):
        if name != self.last_task:
            self.last_task = name
            self.vlog(f'-> {name}')

    def hold_return(self, ms):
        self.hold_return_until = now_ms() + ms

    def return_hold_remaining(self):
        return max(0, self.hold_return_until - now_ms())

    def warn_potion_empty(self, flask):
        """Once a flask: the grind carries on unboosted rather than stopping."""
        if flask in self.potion_warned:
            return
        self.potion_warned.add(flask)
        self.log(f"WARNING: no '{flask}' in the bank — fighting unboosted. Deposit some, or turn the potion setting off.")

    # The wilderness

    def under_attack(self):
        """True when a player is attacking us. Players near are almost all bots, so being near is no signal;
        auto retaliate points our face target at an attacker."""
        here = game.tile()
        return under_player_attack(here.z if here is not None else None, game.attacked_by_player())

    def assert_auto_retaliate(self):
        """With retaliate off there's no signal, and the bot would never notice a player killer."""
        for _ in range(3):
            if game.auto_retaliate_on():
                return
            game.set_auto_retaliate(True)
            on = yield from execution.delay_until(lambda: game.auto_retaliate_on(), 2000)
            if on:
                self.log('auto-retaliate enabled')
                return
        self.log('WARNING: auto-retaliate is OFF and would not enable — the bot cannot detect a player attacking it.')

    def at_bank(self):
        here = game.tile()
        return here is not None and self.bank_tile.distance_to(here) <= AT_BANK_RADIUS

    def cast_varrock_tele(self):
        before = game.tile()
        if not game.teleport('Varrock'):
            return False

        def moved():
            t = game.tile()
            return t is not None and before is not None and t.distance_to(before) > 40

        landed = yield from execution.delay_until(moved, 4000)
        return landed

    # Food, supplies and gear

    def food_count(self):
        return food_count(inventory.items(), self.food_name)

    def has_food(self):
        return self.food_count() > 0

    def need_eat(self):
        if not self.has_food():
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food_name), 1)

    def eat_once(self):
        forms = food_forms(self.food_name)
        food = None
        for item in inventory.items():
            if (item.name or '').lower() in forms:
                food = item
                break
        if food is None:
            return False
        self.status = f'eating {food.name} ({round(skills.hp_fraction() * 100)}% hp)'
        before = skills.effective('hitpoints')
        food.interact('Eat')
        ate = yield from execution.delay_until(lambda: skills.effective('hitpoints') > before, 3000)
        return ate

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), lambda rune: inventory.count(rune))

    def need_style_supplies(self):
        return self.style == 'mage' and self.casts_left() < 1

    def needs_resupply(self):
        """Out of the consumables the grind runs on; only the bank fixes this."""
        return (not self.has_food() and not self.bank_empty) or (self.need_style_supplies() and not self.supply_empty)

    def potion_dose_names(self):
        """Every dose form the run carries, so the deposit keeps part-used flasks."""
        names = []
        for plan in self.potions:
            names.extend(plan.potion.doses)
        return names

    def keep_names(self):
        extra = gear_to_keep(gear_candidates(self.weapon, self.shield, self.tracked_gear), lambda n: equipment.contains(n))
        if self.tele_escape:
            extra.extend([rune for rune, count in VARROCK_TELE_RUNES])
        extra.extend(self.potion_dose_names())
        return combat_keep_names(self.food_name, self.style, spell=self.spell, extra=extra)

    def loot_filter(self):
        return LootFilter(self.loot_set, self.bank_common, self.solve_clues, self.bury_bones, BONE_NAME)

    def foreign_kit(self):
        """Trail leftovers (a spade, sextant, watch, chart, god page or stray runes) a finished clue leaves behind."""
        keep = set([n.lower() for n in self.keep_names()])
        loot = self.loot_filter()
        return [i.name or '?' for i in inventory.items() if is_grind_foreign(i, keep, loot)]

    # The field

    def in_field(self, tile):
        return self.anchor.distance_to(tile) <= FIELD_RADIUS

    def field_dragons(self):
        return npcs.query().name(TARGET).where(lambda n: self.in_field(n.tile()) and not n.targets_another_player()).results()

    def find_loot(self):
        loot = self.loot_filter()
        return ground_items.query().where(lambda g: wants_ground_item(g, loot)).within(FIELD_RADIUS).nearest()

    def slot_decision(self):
        """(action, drop): 'eat', 'drop' or 'none', and the loot it's for."""
        drop = self.find_loot()
        action = slot_freeing_action(inventory.is_full(), drop is not None, self.food_count(), self.food_reserve, skills.hp_fraction(),
                                     loot_stacks_into_pack(drop.name if drop is not None else None))
        return (action, drop)

    def free_slot_for_loot(self):
        """Trades a food slot for a loot slot rather than walking to Edgeville: eats while the heal still counts,
        drops at full hp. True when a slot came free."""
        action, drop = self.slot_decision()
        want = drop.name if drop is not None and drop.name else 'loot'
        self.vlog_change('slot', f'slot check: pack {inventory.used()} used / {inventory.free()} free, {self.food_name} x{self.food_count()} '
                         + f"(reserve {self.food_reserve}), hp {round(skills.hp_fraction() * 100)}%, ground '{want}' -> {action}")
        if action == 'none':
            return False
        if action == 'eat':
            self.log(f'pack full — eating {self.food_name} to make room for {want}')
            ate = yield from self.eat_once()
            if not ate:
                return False
            self.slots_freed += 1
            return True
        food = None
        for item in inventory.items():
            if is_food_item(item.name, self.food_name):
                food = item
                break
        if food is None:
            return False
        self.status = f'dropping {food.name} for pack space'
        self.log(f'pack full at full hp — dropping {food.name} to make room for {want}')
        before = inventory.used()
        food.interact('Drop')
        dropped = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
        if dropped:
            self.slots_freed += 1
            return True
        self.log(f'dropping {food.name} did not free a slot')
        return False

    def drop_vial(self):
        vial = inventory.first(EMPTY_VIAL)
        if vial is None:
            return False
        self.status = f'dropping an empty {EMPTY_VIAL}'
        before = inventory.used()
        if not vial.interact('Drop'):
            return False
        dropped = yield from execution.delay_until_ticks(lambda: inventory.used() < before, 3)
        return dropped

    # Why: the sip is gated on the fight loop, not on standing in the field, because a dose drunk on the walk from
    # Edgeville has half decayed before the first dragon. One op lands a tick, so the vial and the dose take turns,
    # and True means the tick was spent.
    def sip_upkeep(self):
        """Drops a drained vial, or drinks the one dose that's due, from inside a fight."""
        if len(self.potions) == 0 or swing_started_this_tick():
            return False
        dropped = yield from self.drop_vial()
        if dropped:
            return True
        plan = potion_to_sip(self.potions, potions_held, lambda skill: (skills.level(skill), skills.effective(skill)))
        if plan is None:
            return False
        dose = None
        for name in plan.potion.doses:
            item = inventory.first(name)
            if item is not None:
                dose = item
                break
        if dose is None:
            return False
        skill = plan.potion.skill
        name = dose.name or plan.flask
        before = skills.effective(skill)
        self.status = f'drinking {name}'
        if not dose.interact('Drink'):
            return False
        took = yield from execution.delay_until_ticks(lambda: skills.effective(skill) > before, 3)
        if not took:
            self.vlog(f'{name} did not take — {skill} stayed at {before}')
            return False
        self.sips += 1
        self.log(f'drank {name} — {skill} {before} -> {skills.effective(skill)}')
        return True

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

    def bank_routine(self):
        say = lambda m: self.log(f'  {m}')
        arrived = yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=6, timeout_ms=300000, log=say)
        if not arrived:
            self.log('walk to the bank failed — will retry')
            return
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank — will retry')
            return
        yield from bank.deposit_all_matching(deposit_all_except(self.keep_names()))
        self.status = f'withdrawing {self.food_name}'
        yield from self.withdraw_food()
        self.bank_empty = self.food_count() == 0
        if self.food_count() == 0:
            self.log(f"WARNING: no '{self.food_name}' in the bank — deposit food to resume eating.")
        yield from self.withdraw_style_supplies()
        # Why: eating spends the load withdrawn, so heal first and top the food back up after; walking back on panic
        # hp forces another trip, or a death on the way in.
        ate = yield from self.eat_to_full()
        if ate:
            reopened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
            if reopened:
                yield from self.withdraw_food()
        self.bank_trips += 1
        self.status = 'restocked — walking back to the dragons'
        yield from traversal.walk_resilient(self.anchor, radius=4, attempts=6, timeout_ms=300000, log=say)

    def eat_to_full(self):
        """Heals up before walking back."""
        if skills.hp_fraction() >= 1 or not self.has_food():
            return False
        # The open bank swaps the backpack for its deposit view, with no Eat to click until it's shut.
        if bank.is_open():
            yield from bank.close()
            yield from execution.delay_until(lambda: not bank.is_open(), 3000)
        self.status = 'eating back to full before returning'
        self.log(f'healing up before the walk back ({round(skills.hp_fraction() * 100)}% hp, {self.food_count()} {self.food_name})')
        ate = False
        # Eating has a cooldown, so a single failed bite is normal; only several in a row give up.
        misses = 0
        for _ in range(40):
            if skills.hp_fraction() >= 1 or self.food_count() == 0 or misses >= 3:
                break
            bit = yield from self.eat_once()
            if bit:
                ate = True
                misses = 0
            else:
                misses += 1
                yield from execution.delay_ticks(2)
        self.log(f'healed to {round(skills.hp_fraction() * 100)}% hp ({self.food_count()} {self.food_name} left)')
        return ate

    def withdraw_food(self):
        for _ in range(12):
            if self.food_count() >= self.food_withdraw or inventory.is_full():
                break
            before = self.food_count()
            bank.withdraw(self.food_name, withdraw_op(self.food_withdraw - before))
            landed = yield from execution.delay_until(lambda: self.food_count() > before, 2500)
            if not landed:
                break
        self.vlog(f'food after withdrawal: {self.food_count()}/{self.food_withdraw}')

    def withdraw_style_supplies(self):
        if self.shield != '' and not equipment.contains(self.shield) and inventory.first(self.shield) is None:
            got = yield from withdraw_to(self.shield, 1)
            if got > 0:
                yield from equipment.equip(self.shield)
                self.log(f'withdrew and equipped {self.shield}')
            else:
                self.log(f"WARNING: no '{self.shield}' in the bank — WITHOUT it the dragonfire will kill you. Deposit one.")
        if self.weapon != '' and not equipment.contains(self.weapon) and inventory.first(self.weapon) is None:
            got = yield from withdraw_to(self.weapon, 1)
            if got > 0:
                yield from equipment.equip(self.weapon)
                self.log(f'withdrew and wielded {self.weapon}')
        if self.style == 'mage':
            self.status = 'withdrawing runes'
            for row in rune_withdraw_list(self.spell, self.wielded_names(), self.runes_withdraw):
                if inventory.count(row['rune']) < row['count']:
                    got = yield from withdraw_to(row['rune'], row['count'])
                    self.log(f"withdrew {got} {row['rune']}")
            self.supply_empty = self.casts_left() < 1
        yield from self.withdraw_potions()
        if self.tele_escape:
            for rune, count in VARROCK_TELE_RUNES:
                target = count * TELE_STOCK
                if inventory.count(rune) < target:
                    yield from withdraw_to(rune, target)
            if not has_varrock_runes():
                self.log('WARNING: bank is short of Varrock-teleport runes — escape falls back to fleeing on foot.')

    # Why: flasks are counted across every dose form, so a half-used potion carried back isn't stocked on top of.
    def withdraw_potions(self):
        """Tops each planned potion up to its flask count."""
        for plan in self.potions:
            start = potions_held(plan)
            for _ in range(12):
                if potions_held(plan) >= plan.want or inventory.is_full():
                    break
                before = potions_held(plan)
                bank.withdraw(plan.flask, 'Withdraw-1')
                landed = yield from execution.delay_until(lambda: potions_held(plan) > before, 2500)
                if not landed:
                    break
            got = potions_held(plan) - start
            if got > 0:
                self.log(f'withdrew {got} {plan.flask}')
            elif potions_held(plan) == 0 and bank.count(plan.flask) == 0:
                self.warn_potion_empty(plan.flask)
            elif potions_held(plan) < plan.want:
                self.vlog(f'short of {plan.flask}: {potions_held(plan)}/{plan.want} held, pack {inventory.used()}/28, bank has {bank.count(plan.flask)}')


BOT = define_bot(
    name='GreenDragon',
    create=GreenDragon,
    description='Wilderness green dragons N of Edgeville: melee/mage w/ anti-dragon shield, banks bones + hides, sips super attack/strength mid-fight',
    category='Combat',
    tags=['wilderness', 'dragons', 'hides', 'potions'],
    settings_schema=SETTINGS,
)

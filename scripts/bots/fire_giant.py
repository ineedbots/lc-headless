# Fights the fire giants in the Waterfall Dungeon, from a safespot with range or magic or in the east chamber with
# melee: rs2b0t's FireGiant (MIT, see thirdparty/rs2b0t). It enters by the log raft, a rope to the rock and the dead
# tree, and Glarial's amulet at the ledge door, and leaves by the barrel off the ledge or a teleport. A death parks
# it, since the amulet may be on the death pile and there's no way back in without it.

import time

from bots.firegiant.logic import AMULET, BARREL_BANK, BARREL_EXIT, BARREL_LOC, BARREL_OP, DEFAULT_MELEE_TILE, DEFAULT_SAFESPOT, DEFAULT_SAFESPOT_FALLBACK
from bots.firegiant.logic import DUNGEON_MIN_Z, ESCAPE_TELES, EXIT_DOOR, EXIT_DOOR_LOC, EXIT_OPTIONS, LEDGE_DOOR, LEDGE_LOC, LEDGE_OP, RAFT_LOC, RAFT_OP
from bots.firegiant.logic import RAFT_STAND, ROCK_LOC, ROPE, ROPE_THROW_STAND, TREE_LOC, TREE_STAND, attack_range_for, east_first_key, leg_for, loot_wait_ms
from bots.firegiant.logic import same_room, taken_by_another
from rs2004.catalogs import CUSTOM_RANGED_SETTINGS, LOADOUT_SETTING, RANGED_WEAPONS, SPELL_DB, STAFFS, ContinueDialog, bury_one_in_fight
from rs2004.catalogs import casts_available, combat_keep_names, drop_db, food_count, food_forms, food_heal_amount, range_loadout_of, ranged_item
from rs2004.catalogs import rune_withdraw_list, script_food, should_eat_to_use_food

TARGET = 'Fire giant'
FIELD_RADIUS = 10
BANK_HEAL_TO = 0.9
RE_ENGAGE_MS = 4000
TAKEN_SKIP_MS = 15000
LOOT_BURST_MAX = 8
LOOT_SKIP_MS = 30000
LEASH_WAIT_MS = 15000
LEASH_SKIP_MS = 20000
ASSERT_BATCH = 5
ASSERT_RETRY_MS = 60000
XP_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic', 'prayer']

SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}
SHOW_SAFESPOT = {'key': 'combat_style', 'any_of': ['mage', 'range']}

DROPS = drop_db().get(TARGET) or []
# Fire giants drop only rune and steel arrows, so every arrow stack is kept.
DEFAULT_LOOT = DROPS

SETTINGS = {
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range']),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'staff': SettingDef('string', 'Staff of air', 'Staff', options=STAFFS, group='Combat', show_if=SHOW_MAGE, help='wielded staff, withdrawn from bank when missing'),
    'spell': SettingDef('string', 'Wind Strike', 'Autocast spell', options=list(SPELL_DB.keys()), group='Combat', show_if=SHOW_MAGE),
    'runes_withdraw': SettingDef('number', 150, 'Casts of runes per bank trip', 1, 2000, group='Combat', show_if=SHOW_MAGE),
    'rune_buffer': SettingDef('number', 500, 'Spare runes per type', 0, 2000, group='Combat', show_if=SHOW_MAGE,
                              help="withdrawn on top of the cast budget. Looted runes (fire giants drop chaos) let the trip cast past its planned count and drain whichever rune is scarcest — if that rune is also the escape teleport's, the bot cannot leave. Runes stack, so this costs no extra slots"),
    'bow': SettingDef('string', 'Maple shortbow', 'Ranged weapon', options=RANGED_WEAPONS + ['Other'], group='Combat', show_if=SHOW_RANGE,
                      help='bows use the selected ammo; darts are both the weapon and the projectile stack'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Iron arrow', 'Ammo', options=['Bronze arrow', 'Iron arrow', 'Steel arrow', 'Mithril arrow', 'Adamant arrow', 'Rune arrow', 'Other'],
                       group='Combat', show_if=SHOW_RANGE),
}
SETTINGS.update(CUSTOM_RANGED_SETTINGS)
SETTINGS.update({
    'ammo_withdraw': SettingDef('number', 500, 'Ammo per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE),
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', 20, 'Food to withdraw per bank run', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 25, 'Panic-to-bank below HP%', 1, 98, group='Food & healing',
                           help='retreat to the bank when HP drops this low (out of food, or damage outpacing eating)'),
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot to pick up (drop table)', options=DROPS, group='Banking & loot',
                       help='the fire giant drop table; ticked drops get grabbed. Everything picked up is banked — the bank keeps only food/runes/ammo/weapon plus the amulet, rope, and escape runes.'),
    'bank_common_junk': SettingDef('boolean', True, 'Also grab shared gems/junk', group='Banking & loot'),
    'bury_bones': SettingDef('boolean', False, 'Bury big bones', group='Banking & loot',
                             help='bury Big bones for Prayer xp instead of banking them (always looted when on)'),
    'safespot_tile': SettingDef('tile', DEFAULT_SAFESPOT, 'Safespot tile (west room)', group='Location', show_if=SHOW_SAFESPOT,
                                help='preferred spot in the west room — sees two giants. If one reaches it the bot drops to the fallback tile for a minute'),
    'safespot_fallback_tile': SettingDef('tile', DEFAULT_SAFESPOT_FALLBACK, 'Safespot fallback tile', group='Location', show_if=SHOW_SAFESPOT,
                                         help='retreat tile used for a minute whenever a giant reaches the main safespot; must be somewhere no giant can path to'),
    'melee_tile': SettingDef('tile', DEFAULT_MELEE_TILE, 'Melee anchor tile (centre room)', group='Location', show_if=SHOW_MELEE,
                             help='centre of the east chamber — 7 giants within 6 tiles'),
    'escape_tele': SettingDef('string', BARREL_EXIT, 'Way out', options=EXIT_OPTIONS, group='Location',
                              help='Barrel walks out through the dungeon door and rides the barrel off the ledge to 2527,3413 — free, no runes or magic level, 118 tiles from Ardougne West. A teleport only saves the walk back to the exit door'),
    'tele_stock': SettingDef('number', 2, 'Spare escape casts', 1, 10, group='Location', help='casts carried on top of the one needed to leave'),
    'bank_tile': SettingDef('tile', ESCAPE_TELES['Camelot'].bank, 'Bank stand tile', group='Location', help='left at the Seers default, this follows the escape teleport'),
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


def in_dungeon():
    here = game.tile()
    return here is not None and here.z > DUNGEON_MIN_Z


def has_amulet():
    return inventory.count(AMULET) > 0 or equipment.contains(AMULET)


def has_rope():
    return inventory.count(ROPE) > 0


def ledge_door():
    return locs.query().name(LEDGE_LOC).action(LEDGE_OP).where(lambda l: l.tile().x == LEDGE_DOOR.x and l.tile().z == LEDGE_DOOR.z).first()


def use_rope_on(loc_name):
    rope = inventory.first(ROPE)
    if rope is None:
        return False
    target = locs.query().name(loc_name).nearest()
    if target is None:
        return False
    return bool(rope.use_on(target))


def loot_key(g):
    return f'{g.name or ""}@{g.tile().x},{g.tile().z}'


class Parked(Task):
    def __init__(self, bot):
        Task.__init__(self, label='parked')
        self.bot = bot

    def validate(self):
        return self.bot.parked

    def execute(self):
        yield from execution.delay_ticks(10)


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

    def _need_weapon(self):
        bot = self.bot
        return not (bot.style == 'range' and range_loadout_of(bot.weapon, bot.ammo).thrown) \
            and bot.weapon != '' and not equipment.contains(bot.weapon) and inventory.first(bot.weapon) is not None

    def _need_quiver(self):
        return self.bot.style == 'range' and inventory.count(self.bot.ammo) > 0

    def validate(self):
        return self.bot.style != 'melee' and self.fails < 5 and (self._need_weapon() or self._need_quiver())

    def execute(self):
        bot = self.bot
        if self._need_weapon():
            bot.status = f'wielding {bot.weapon}'
            wielded = yield from equipment.equip(bot.weapon)
            if wielded:
                bot.log(f'wielded {bot.weapon}')
                if not bot.need_style_supplies():
                    bot.supply_empty = False
                self.fails = 0
            else:
                self.fails += 1
            return
        bot.status = f'equipping {bot.ammo}'
        equipped = yield from bot.equip_projectiles()
        if equipped:
            bot.log(f'equipped {bot.ammo}')
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
        return inventory.is_full()

    def execute(self):
        bot = self.bot
        if event_signal.pending():
            return
        bot.status = 'banking — restocking'
        casts = f', casts {bot.casts_left()}' if bot.style == 'mage' else ''
        ammo = f', ammo {inventory.count(bot.ammo)}' if bot.style == 'range' else ''
        bot.log(f'banking (food {bot.food_count()}{casts}{ammo})')
        yield from bot.bank_routine(True)


class LootCorpse(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot corpse')
        self.bot = bot

    def validate(self):
        return in_dungeon() and not inventory.is_full() and self.bot.find_loot() is not None

    def execute(self):
        bot = self.bot
        yield from bot.loot_burst()
        # Why: leaving the walk back to ReturnToSafespot lets it cancel a pickup still in flight, so the loot stays on
        # the floor and the two tasks trade places.
        if bot.uses_safespot() and not bot.at_safespot() and skills.hp_fraction() >= bot.panic_hp:
            yield from bot.quick_return_to_safespot()


class ReturnToSafespot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to safespot')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return in_dungeon() and bot.uses_safespot() and not bot.at_safespot() and skills.hp_fraction() >= bot.panic_hp

    def execute(self):
        bot = self.bot
        bot.status = 'returning to the safespot'
        yield from traversal.walk_resilient(bot.active_safespot(), radius=0, attempts=4, timeout_ms=60000, log=lambda m: bot.log(f'  {m}'))


class EnterDungeon(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter dungeon')
        self.bot = bot

    def validate(self):
        return not in_dungeon() and has_amulet() and has_rope() and not self.bot.parked

    def execute(self):
        leg = leg_for(game.tile())
        if leg == 'AtLedge':
            yield from self._open_ledge()
        elif leg == 'PastRock':
            yield from self._rope_tree()
        elif leg == 'AtLanding':
            yield from self._rope_rock()
        elif leg == 'AtRaft':
            yield from self._board_raft()
        else:
            if leg == 'WashedOut':
                self.bot.log('washed downstream — walking back to the raft')
            yield from self._walk_to_raft()

    def _walk(self, tile, radius, attempts, timeout_ms):
        bot = self.bot
        yield from traversal.walk_resilient(tile, radius=radius, attempts=attempts, timeout_ms=timeout_ms, log=lambda m: bot.log(f'  {m}'))

    def _walk_to_raft(self):
        self.bot.status = 'walking to the log raft'
        yield from self._walk(RAFT_STAND, 2, 6, 300000)

    def _board_raft(self):
        bot = self.bot
        raft = locs.query().name(RAFT_LOC).action(RAFT_OP).nearest()
        if raft is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = 'boarding the log raft'
        if not raft.interact(RAFT_OP):
            yield from execution.delay_ticks(2)
            return
        landed = yield from execution.delay_until(lambda: leg_for(game.tile()) == 'AtLanding', 12000)
        if landed:
            bot.log('rafted down to the landing')

    def _rope_rock(self):
        bot = self.bot
        here = game.tile()
        if here is None or here.x != ROPE_THROW_STAND.x or here.z != ROPE_THROW_STAND.z:
            bot.status = 'walking to the rope-throw stand'
            yield from self._walk(ROPE_THROW_STAND, 0, 4, 60000)
            return
        bot.status = 'roping across to the rock'
        if not use_rope_on(ROCK_LOC):
            bot.log(f'could not use the rope on the {ROCK_LOC} — retrying')
            yield from execution.delay_ticks(2)
            return
        crossed = yield from execution.delay_until(lambda: leg_for(game.tile()) == 'PastRock', 12000)
        bot.log('crossed to the rock' if crossed else 'rope throw did not cross — retrying')

    def _rope_tree(self):
        bot = self.bot
        here = game.tile()
        if here is None or here.x != TREE_STAND.x or here.z != TREE_STAND.z:
            bot.status = 'walking to the dead tree'
            yield from self._walk(TREE_STAND, 0, 4, 60000)
            return
        bot.status = 'roping down the dead tree'
        if not use_rope_on(TREE_LOC):
            bot.log(f'could not use the rope on the {TREE_LOC} — retrying')
            yield from execution.delay_ticks(2)
            return
        down = yield from execution.delay_until(lambda: leg_for(game.tile()) == 'AtLedge', 12000)
        bot.log('down on the ledge' if down else 'rope-down did not land on the ledge — retrying')

    def _open_ledge(self):
        bot = self.bot
        if not has_amulet():
            return
        # The locs read empty for a tick after the teleport onto the ledge.
        door = ledge_door()
        for _ in range(5):
            if door is not None:
                break
            yield from execution.delay_ticks(1)
            door = ledge_door()
        if door is None:
            bot.log('the ledge door is not in the scene yet — retrying')
            return
        bot.status = 'opening the ledge door'
        if not door.interact(LEDGE_OP):
            yield from execution.delay_ticks(2)
            return
        inside = yield from execution.delay_until(lambda: in_dungeon(), 12000)
        bot.log('inside the Waterfall Dungeon' if inside else 'the ledge door did not let us through — retrying')


class WalkToSpot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='walk to spot')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return in_dungeon() and here is not None and self.bot.anchor().distance_to(here) > FIELD_RADIUS

    def execute(self):
        bot = self.bot
        bot.status = 'walking to the fight spot'
        yield from traversal.walk_resilient(bot.anchor(), radius=0 if bot.uses_safespot() else 3, attempts=6, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.target_idx = None
        self.engaged_at = 0
        self.engaged_health = -1
        self.skip = {}

    def validate(self):
        bot = self.bot
        if not in_dungeon() or skills.hp_fraction() < bot.panic_hp:
            return False
        if bot.uses_safespot() and not bot.at_safespot():
            return False
        return len(bot.field_giants()) > 0

    def _drop_target(self):
        self.target_idx = None
        self.bot.target_idx = None
        self.bot.engaged_idx = None

    def execute(self):
        bot = self.bot
        bot.status = 'fighting fire giants'
        deadline = now_ms() + 120000
        while now_ms() < deadline:
            if event_signal.pending() or bot.died or chat_dialog.can_continue():
                return
            if bot.need_eat():
                yield from bot.eat_once()
                continue
            if skills.hp_fraction() < bot.panic_hp:
                return
            if bot.check_retreat():
                # Reposition at once: falling through would loot or attack first, and handing it to ReturnToSafespot
                # costs another task hop.
                yield from bot.quick_return_to_safespot()
                continue
            giants = bot.field_giants()
            if self.target_idx is not None and len([g for g in giants if g.index == self.target_idx]) == 0:
                bot.kills += 1
                bot.log(f'fire giant down — {bot.kills} kills')
                self._drop_target()
                bot.clear_retreat()
            if bot.uses_safespot() and not bot.at_safespot():
                back = yield from bot.quick_return_to_safespot()
                if not back:
                    return
                continue
            if not inventory.is_full() and bot.find_loot() is not None:
                yield from bot.loot_burst()
                continue
            # Why: you stay in combat with a giant until one of you dies, so clicking a live target again is noise.
            # Why: our own combat bar never lights up while safespotting, so the target is held instead.
            # Why: the hold breaks early on a random event, a hit on us, or the giant's health changing, which proves
            # we're connecting and resets the clock.
            live = None
            if self.target_idx is not None:
                for g in giants:
                    if g.index == self.target_idx:
                        live = g
            if live is not None and live.targets_another_player():
                bot.log(f'giant {live.index} was taken by another player — finding another')
                self.skip[live.index] = now_ms() + TAKEN_SKIP_MS
                self._drop_target()
                continue
            if live is not None:
                if live.health != self.engaged_health:
                    self.engaged_health = live.health
                    self.engaged_at = now_ms()
                if now_ms() - self.engaged_at < RE_ENGAGE_MS:
                    # Why: this hold is the idle stretch while the giant is worn down, so the tick is free for a bone.
                    if bot.bury_bones:
                        buried = yield from bury_one_in_fight('Big bones')
                        if buried:
                            bot.buried += 1
                            continue
                    yield from execution.delay_ticks(1)
                    continue
            now = now_ms()
            candidates = [g for g in giants if not bot.uses_safespot() or self.skip.get(g.index, 0) < now]
            if bot.uses_safespot():
                candidates.sort(key=lambda g: east_first_key(g.tile().x, g.distance()))
            else:
                candidates.sort(key=lambda g: g.distance())
            if not candidates:
                yield from execution.delay_ticks(2)
                return
            target = candidates[0]
            if bot.uses_safespot() and target.distance() > attack_range_for(bot.style, bot.weapon):
                closed = yield from self._leash(target.index)
                if not closed:
                    self.skip[target.index] = now_ms() + LEASH_SKIP_MS
                continue
            tier_before = bot.retreated
            if target.index != self.target_idx:
                bot.log(f'engaging fire giant {target.index} at {target.tile().x},{target.tile().z} (d={target.distance()})')
            else:
                bot.log(f'giant {target.index} stalled — re-issuing the attack')
            target.interact('Attack')
            self.target_idx = target.index
            bot.target_idx = target.index
            bot.engaged_idx = target.index
            self.engaged_at = now_ms()
            self.engaged_health = -1
            yield from execution.delay_until(lambda: (bot.uses_safespot() and not bot.at_safespot()) or len(bot.field_giants()) == 0, 1200)
            if bot.uses_safespot() and not bot.at_safespot():
                # Why: a tier switch moves us one tile on purpose, so it isn't the giant dragging us and the target is
                # kept.
                if bot.retreated != tier_before:
                    bot.log(f'safespot tier changed mid-fight — keeping giant {target.index}')
                    continue
                self.skip[target.index] = now + 8000
                bot.log(f'giant {target.index} pulled us off the safespot — skipping it for 8s')
                self._drop_target()

    # Why: clicking the giant from here makes the server walk us into range, and ReturnToSafespot drags us back
    # before the shot leaves.
    def _leash(self, idx):
        """Holds the tile while the giant closes. False means it never did."""
        bot = self.bot
        bot.status = 'leashing fire giant'
        bot.target_idx = idx
        deadline = now_ms() + LEASH_WAIT_MS
        while now_ms() < deadline:
            if event_signal.pending() or bot.died or chat_dialog.can_continue():
                return True
            if bot.need_eat():
                yield from bot.eat_once()
                continue
            if bot.check_retreat():
                return True
            if not bot.at_safespot():
                back = yield from bot.quick_return_to_safespot()
                if not back:
                    return True
                continue
            giant = None
            for g in bot.field_giants():
                if g.index == idx:
                    giant = g
            if giant is None or giant.distance() <= attack_range_for(bot.style, bot.weapon):
                return True
            yield from execution.delay_ticks(1)
        return False


class FireGiant(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.status = 'starting'
        self.kills = 0
        self.looted = 0
        self.buried = 0
        self.bank_trips = 0
        self.loot_counts = {}
        self.loot_skip = {}
        self.supply_empty = False
        self.bank_empty = False
        self.died = False
        self.parked = False
        self.park_reason = ''
        self.target_idx = None
        self.engaged_idx = None
        self.retreated = False
        self.last_hp = -1
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
        if self.style == 'range':
            self.ammo = range_loadout_of(self.weapon, self.ammo).projectile
        self.food_name = script_food(s, 'Lobster')
        self.panic_hp = s.num('panic_hp', 25) / 100
        self.runes_withdraw = s.num('runes_withdraw', 150)
        self.rune_buffer = s.num('rune_buffer', 500)
        self.ammo_withdraw = s.num('ammo_withdraw', 500)
        self.food_withdraw = s.num('food_withdraw', 20)
        self.loot_set = set([n.lower() for n in s.list('loot', DEFAULT_LOOT)])
        self.bank_common = s.bool('bank_common_junk', True)
        self.bury_bones = s.bool('bury_bones', False)
        if self.bury_bones:
            self.loot_set.add('big bones')
        self.safespot = s.tile('safespot_tile', DEFAULT_SAFESPOT)
        self.safespot_fallback = s.tile('safespot_fallback_tile', DEFAULT_SAFESPOT_FALLBACK)
        self.melee_tile = s.tile('melee_tile', DEFAULT_MELEE_TILE)
        exit = s.str('escape_tele', BARREL_EXIT)
        self.use_barrel = exit == BARREL_EXIT
        self.tele = ESCAPE_TELES.get(exit, ESCAPE_TELES['Camelot'])
        self.tele_stock = s.num('tele_stock', 2)
        chosen_bank = s.tile('bank_tile', ESCAPE_TELES['Camelot'].bank)
        seers = ESCAPE_TELES['Camelot'].bank
        bank_is_default = chosen_bank.x == seers.x and chosen_bank.z == seers.z
        if bank_is_default:
            self.bank_tile = BARREL_BANK if self.use_barrel else self.tele.bank
        else:
            self.bank_tile = chosen_bank
        self.on('death', self.died_now)
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(skill) for skill in XP_SKILLS])
        weapon = f' w/ {self.weapon}' if self.style != 'melee' else ''
        spell = f' ({self.spell})' if self.style == 'mage' else ''
        burying = ', burying big bones' if self.bury_bones else ''
        self.log(f"FireGiant — style {self.style}{weapon}{spell}, food '{self.food_name}' (smart-eat, panic<{round(self.panic_hp * 100)}%), "
                 + f'spot {self.anchor()}, escape {self.tele.name} tele, bank {self.bank_tile}{burying}')
        self.add(
            Parked(self), ContinueDialog(), Eat(self), GearEquip(self), SetAttackStyle(self), ArmAutocast(self), PanicBank(self),
            BuryBones(self), BankRun(self), LootCorpse(self), EnterDungeon(self), WalkToSpot(self), ReturnToSafespot(self), Fight(self),
        )
        self.check_prereqs()

    def died_now(self):
        self.died = True
        where = game.tile()
        at = f' at {where.x},{where.z}' if where is not None else ''
        self.park_for(f'died{at}. Gear is on the death pile in the Waterfall Dungeon and {AMULET} may be with it — re-entry is impossible '
                      + 'without it, so the bot stopped rather than burn bank stock.')

    def park_for(self, reason):
        if self.parked:
            return
        self.parked = True
        self.park_reason = reason
        self.status = 'parked'
        self.log(f'PARKED: {reason}')

    def check_prereqs(self):
        if quests.status('Waterfall Quest') == 'not_started':
            self.park_for('the Waterfall Quest is not started — the log raft refuses to launch. Talk to Almera at 2515,3495, then restart.')
            return False
        if not has_amulet() and inventory.is_full():
            self.park_for(f'no {AMULET} and the pack is full — free a slot so it can be withdrawn.')
            return False
        return True

    def recovery_anchor(self):
        return self.anchor()

    def grind_targets(self):
        return [TARGET.lower()]

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(skill) for skill in XP_SKILLS]) - self.xp_at_start
        report = {
            'Status': self.status,
            'Style': self.style,
            'Kills': self.kills,
            'Looted': self.looted,
            'Buried': self.buried,
            'Bank trips': self.bank_trips,
            'XP/hr': f'{(gained / minutes * 60 / 1000):.1f}k' if minutes > 0.5 else '-',
        }
        if self.parked:
            report['Parked'] = self.park_reason
        return report

    # Food

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

    # Style supplies

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

    def equip_projectiles(self):
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                return False
        item = inventory.first(self.ammo)
        op = None
        if item is not None:
            for action in item.actions():
                lower = action.lower()
                if 'wield' in lower or 'wear' in lower or 'equip' in lower:
                    op = action
                    break
        if item is None or op is None:
            return False
        before = self.quiver_count()
        if not item.interact(op):
            return False
        equipped = yield from execution.delay_until(lambda: self.quiver_count() > before, 3000)
        return equipped

    def ammo_left(self):
        return self.quiver_count() + inventory.count(self.ammo)

    def need_style_supplies(self):
        if self.style == 'mage':
            return self.casts_left() < 1
        if self.style == 'range':
            return self.ammo_left() == 0
        return False

    # The field

    def uses_safespot(self):
        return self.style == 'mage' or self.style == 'range'

    def active_safespot(self):
        return self.safespot_fallback if self.retreated else self.safespot

    def anchor(self):
        return self.active_safespot() if self.uses_safespot() else self.melee_tile

    # Why: the forward spot trades safety for a second giant in view, so a hit there is expected, not a fault.
    # Why: damage is the trigger; a giant walking past is harmless, and only a connecting hit means the tile failed.
    def check_retreat(self):
        """True when the forward safespot has to be given up."""
        hp = skills.effective('hitpoints')
        hurt = self.last_hp >= 0 and hp < self.last_hp
        self.last_hp = hp
        if not self.uses_safespot() or self.retreated or not hurt:
            return False
        self.retreated = True
        self.log(f'took a hit at {self.safespot} — falling back to {self.safespot_fallback} until the next kill')
        return True

    # A kill means whatever reached us is gone, so the forward spot is worth trying again.
    def clear_retreat(self):
        if self.retreated:
            self.retreated = False
            self.log(f'giant down — back to {self.safespot}')

    def in_field(self, tile):
        return self.anchor().distance_to(tile) <= FIELD_RADIUS

    def at_safespot(self):
        here = game.tile()
        return here is not None and here.equals(self.active_safespot())

    # Why: the rooms overlap inside the field radius, and the nearest east giant is closer to the west safespot than
    # two of the west ones, so safespotting only engages giants sharing the anchor's chamber.
    def same_room_as_anchor(self, tile):
        return same_room(self.anchor(), tile)

    def field_giants(self):
        def huntable(n):
            return self.in_field(n.tile()) and not taken_by_another(n.index == self.engaged_idx, n.in_combat, n.targets_me(), n.targets_another_player()) \
                and (not self.uses_safespot() or self.same_room_as_anchor(n.tile()))

        return npcs.query().name(TARGET).where(huntable).results()

    # Loot

    def find_loot(self):
        now = now_ms()

        def wanted(g):
            name = (g.name or '').lower()
            keep = name in self.loot_set or (self.bank_common and matches_common_bank_loot(g.name or ''))
            # Someone else's kills in the next chamber aren't ours to collect, and the rooms overlap inside the field
            # radius, so distance won't keep us out of them.
            return keep and self.same_room_as_anchor(g.tile()) and self.loot_skip.get(loot_key(g), 0) < now

        return ground_items.query().where(wanted).within(FIELD_RADIUS).nearest()

    def quick_return_to_safespot(self):
        self.status = 'returning to the safespot'
        # A tier switch is a one-tile hop, so a long wait each try adds latency while something hits us; try sooner.
        for _ in range(4):
            if self.at_safespot() or event_signal.pending():
                break
            direct_navigator.walk(self.active_safespot())
            back = yield from execution.delay_until(lambda: self.at_safespot(), 2000)
            if back:
                break
        return self.at_safespot()

    def loot_once(self):
        drop = self.find_loot()
        if drop is None:
            return False
        name = drop.name or ''
        key = loot_key(drop)
        self.status = f'looting {name}'
        used_before = inventory.used()
        count_before = inventory.count(name)
        if not drop.interact('Take'):
            return False
        # Why: a stackable drop merges into its slot, so used() alone never moves for coins, runes or arrows, the bulk
        # of this table.
        took = yield from execution.delay_until(lambda: inventory.used() > used_before or inventory.count(name) > count_before, loot_wait_ms(drop.distance()))
        if took:
            self.looted += 1
            self.loot_counts[name] = self.loot_counts.get(name, 0) + 1
            return True
        self.loot_skip[key] = now_ms() + LOOT_SKIP_MS
        self.log(f'could not pick up {name} at {drop.tile().x},{drop.tile().z} — ignoring it for {LOOT_SKIP_MS // 1000}s')
        return False

    # Why: loot lands on the corpse tile, so collecting it means leaving the safespot and tanking.
    # Why: the pile drains in one pass, not one item per task hop, breaking off to eat rather than finishing at low hp.
    def loot_burst(self):
        """Clears the drop pile in a single pass."""
        for _ in range(LOOT_BURST_MAX):
            if event_signal.pending() or self.died or inventory.is_full() or self.need_eat() or self.find_loot() is None:
                return
            # A failure skips that drop, so carry on and clear the rest of the pile.
            yield from self.loot_once()

    # Leaving and banking

    def keep_names(self):
        """What the deposit holds back. The spell and escape runes aren't kept, since the withdrawals put back the
        set amount and a trip leaves with a known quantity."""
        return combat_keep_names(self.food_name, self.style, ammo=self.ammo, weapon=self.weapon, extra=[AMULET, ROPE])

    def has_escape_runes(self):
        if self.use_barrel:
            return True
        for rune, count in self.tele.runes:
            if inventory.count(rune) < count:
                return False
        return True

    def cast_escape(self):
        tele = self.tele
        if not self.has_escape_runes():
            self.log(f'no {tele.name}-teleport runes — cannot leave the dungeon')
            return False
        if skills.level('magic') < tele.level:
            self.log(f"magic {skills.level('magic')} is below the {tele.level} needed for the {tele.name} teleport")
            return False
        self.status = f'teleporting to {tele.name}'
        if not game.teleport(tele.name):
            return False
        out = yield from execution.delay_until(lambda: not in_dungeon(), 8000)
        return out

    # Why: the exit door sits on the dungeon entry tile and drops us on the ledge, where the barrel washes us to
    # 2527,3413; the route is free and the only one that works with no runes at all.
    def exit_via_barrel(self):
        """Walks out of the dungeon and rides the barrel to the mainland."""
        if in_dungeon():
            self.status = 'walking to the dungeon door'
            yield from traversal.walk_resilient(EXIT_DOOR, radius=1, attempts=5, timeout_ms=180000, log=lambda m: self.log(f'  {m}'))
            door = locs.query().name(EXIT_DOOR_LOC).where(lambda l: l.tile().x == EXIT_DOOR.x and l.tile().z == EXIT_DOOR.z).first()
            if door is None:
                self.log('the dungeon door is not in the scene yet — retrying')
                return False
            self.status = 'leaving through the dungeon door'
            door.interact('Open')
            out = yield from execution.delay_until(lambda: leg_for(game.tile()) == 'AtLedge', 12000)
            if not out:
                self.log('the dungeon door did not put us on the ledge — retrying')
                return False
            self.log('out on the ledge')
        if leg_for(game.tile()) != 'AtLedge':
            return True
        # The locs read empty for a tick after the teleport onto the ledge.
        barrel = locs.query().name(BARREL_LOC).action(BARREL_OP).nearest()
        for _ in range(5):
            if barrel is not None:
                break
            yield from execution.delay_ticks(1)
            barrel = locs.query().name(BARREL_LOC).action(BARREL_OP).nearest()
        if barrel is None:
            self.log('the barrel is not in the scene yet — retrying')
            return False
        self.status = 'riding the barrel off the ledge'
        barrel.interact(BARREL_OP)
        washed = yield from execution.delay_until(lambda: leg_for(game.tile()) == 'WashedOut', 12000)
        if not washed:
            self.log('the barrel did not wash us downstream — retrying')
            return False
        self.log('washed up downstream — walking to the bank')
        return True

    def leave_dungeon(self):
        if not in_dungeon() and leg_for(game.tile()) != 'AtLedge':
            return True
        if self.use_barrel:
            out = yield from self.exit_via_barrel()
            return out
        for _ in range(3):
            if not in_dungeon():
                break
            cast = yield from self.cast_escape()
            if cast:
                self.log(f'teleported out to {self.tele.name}')
                return True
            yield from execution.delay_ticks(3)
        if not in_dungeon():
            return True
        # The barrel always works, so a dud teleport is a detour, not a dead end.
        self.log(f'the {self.tele.name} teleport will not fire — walking out through the barrel instead')
        out = yield from self.exit_via_barrel()
        return out

    def bank_routine(self, withdraw_food):
        out = yield from self.leave_dungeon()
        if not out:
            return
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
            yield from self.withdraw_food_to()
        yield from self.withdraw_style_supplies()
        yield from self.withdraw_escape_runes()
        yield from self.withdraw_entry_kit()
        yield from self.ensure_escape_runes()
        # Why: the trip back is long, so healing happens at the booth, and the bank comes down first or the Eat click
        # lands on the bank panel; the food is topped back up afterwards.
        if withdraw_food and skills.hp_fraction() < BANK_HEAL_TO and self.has_food():
            closed = yield from bank.close()
            if closed:
                yield from self.heal_up()
                reopened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
                if not reopened:
                    self.log('could not reopen the bank to top off food — carrying what we have')
                else:
                    yield from self.withdraw_food_to()
        # Why: the next task may be Eat, and with the bank panel over the pack that bite would land on the bank.
        yield from bank.close()
        self.bank_trips += 1
        self.status = 'restocked — heading back to the waterfall'

    def withdraw_food_to(self):
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

    def heal_up(self):
        if skills.hp_fraction() >= BANK_HEAL_TO or not self.has_food():
            return False
        self.status = 'eating up before the trip back'
        start = round(skills.hp_fraction() * 100)
        for _ in range(24):
            if skills.hp_fraction() >= BANK_HEAL_TO or not self.has_food():
                break
            ate = yield from self.eat_once()
            if not ate:
                break
        self.log(f'healed {start}% -> {round(skills.hp_fraction() * 100)}% before heading back')
        return True

    def withdraw_escape_runes(self):
        for rune, count in self.tele.runes:
            target = count * (self.tele_stock + 1)
            if inventory.count(rune) < target:
                yield from withdraw_to(rune, target)
        if not self.has_escape_runes():
            self.log(f'WARNING: bank is short of {self.tele.name}-teleport runes — the next trip cannot leave the dungeon.')

    # Never fatal: the barrel walks out for free, so missing teleport runes cost a detour to the dungeon door.
    def ensure_escape_runes(self):
        if self.use_barrel:
            return
        for _ in range(3):
            if self.has_escape_runes():
                break
            yield from self.withdraw_escape_runes()
        if self.has_escape_runes():
            return
        short = [rune for rune, count in self.tele.runes if inventory.count(rune) + bank.count(rune) < count]
        why = f"the bank is out of {' and '.join(short)}" if short else 'the withdrawal would not stick'
        self.log(f'WARNING: no {self.tele.name}-teleport runes — {why}. Walking out through the barrel instead.')

    def withdraw_entry_kit(self):
        if not has_amulet():
            yield from withdraw_to(AMULET, 1)
        if not has_rope():
            yield from withdraw_to(ROPE, 1)
        if not has_amulet():
            self.park_for(f'no {AMULET} in the bank or on the player — it is required to open the ledge door and cannot be re-obtained without redoing the Waterfall Quest chain.')
            return
        if not has_rope():
            self.park_for('no Rope in the bank or on the player — it is required for both the rock and the dead tree. Bank a rope and restart.')

    def withdraw_style_supplies(self):
        if self.style != 'melee' and not (self.style == 'range' and range_loadout_of(self.weapon, self.ammo).thrown) \
                and self.weapon != '' and not equipment.contains(self.weapon) and inventory.first(self.weapon) is None:
            self.status = f'withdrawing {self.weapon}'
            got = yield from withdraw_to(self.weapon, 1)
            if got > 0:
                self.log(f'withdrew {self.weapon}')
            else:
                self.log(f"WARNING: no '{self.weapon}' in the bank — carrying on with current gear.")
        if self.style == 'mage':
            self.status = 'withdrawing runes'
            # Why: fire giants drop chaos runes, so looted runes let the trip outrun its cast budget until the scarcest
            # rune runs dry; when that's also the escape teleport's, the bot can't leave. Runes stack, so a spare few
            # hundred costs one slot.
            for row in rune_withdraw_list(self.spell, self.wielded_names(), self.runes_withdraw):
                rune = row['rune']
                target = row['count'] + self.rune_buffer
                if inventory.count(rune) < target:
                    got = yield from withdraw_to(rune, target)
                    self.log(f'withdrew {got} {rune} ({inventory.count(rune)}/{target})')
            if self.casts_left() < 1:
                self.supply_empty = True
                self.log(f"WARNING: bank can't supply a single '{self.spell}' cast — deposit runes to resume.")
            else:
                self.supply_empty = False
        elif self.style == 'range':
            self.status = f'withdrawing {self.ammo}'
            got = yield from withdraw_to(self.ammo, self.ammo_withdraw)
            if got > 0:
                self.log(f'withdrew {got} {self.ammo}')
                self.supply_empty = False
            elif self.ammo_left() == 0:
                # An empty bank is only a problem when the quiver is empty too.
                self.supply_empty = True
                self.log(f"WARNING: no '{self.ammo}' in the bank — deposit ammo to resume.")


BOT = define_bot(
    name='FireGiant',
    create=FireGiant,
    description="Waterfall Dungeon fire giants: range/mage safespot or melee, enters by raft + rope + Glarial's amulet, rides the barrel out to bank",
    category='Combat',
    tags=['waterfall', 'safespot', 'members', 'banking'],
    settings_schema=SETTINGS,
)

# Fights an NPC around where it starts, chickens by default, in melee, magic (autocast) or ranged, burying the
# bones and banking the loot every so often: rs2b0t's ChickenKiller (MIT, see thirdparty/rs2b0t). CowKiller
# (cow_killer.py) is it with a cow field preset.

import time

from rs2004.catalogs import SPELL_DB, ContinueDialog, DeathRecovery, casts_available, rune_withdraw_list

COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints', 'ranged', 'magic']
SHOW_MAGE = {'key': 'combat_style', 'any_of': ['mage']}
SHOW_RANGE = {'key': 'combat_style', 'any_of': ['range']}
SHOW_MELEE = {'key': 'combat_style', 'any_of': ['melee']}
# Older saves kept combat_style as a melee training style.
LEGACY_MELEE = ['attack', 'strength', 'controlled', 'defence', 'accurate', 'aggressive', 'defensive', 'shared']
RANGE_MODE_NAMES = ['accurate', 'rapid', 'longrange']
# Why: a ground stack can stay in view after its Take fails, taken by another player or a desync, so a failed
# pickup's tile and id are left alone this long rather than chased forever.
LOOT_SKIP_MS = 30000
STYLE_RETRY_MS = 60000
FIGHT_MS = 90000

SETTINGS = {
    'leash_radius': SettingDef('number', 12, 'Leash radius (tiles)', 3, 30),
    'fight_hp_gate': SettingDef('number', 45, 'Stop fighting below HP%', 0, 100),
    'rest_until_hp': SettingDef('number', 70, 'Rest until HP%', 0, 100),
    'target_name': SettingDef('string', 'Chicken', 'Target NPC name'),
    'loot_match': SettingDef('string', 'bones', 'Loot name match (| = OR)', help='e.g. "cow hide|bones"'),
    'bury_bones': SettingDef('boolean', True, 'Bury bones?'),
    'combat_style': SettingDef('string', 'melee', 'Combat style', options=['melee', 'mage', 'range'],
                               help='melee / mage / range — same shape as AutoFighter. Older saves that stored attack/strength/controlled/defence still work as melee.'),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS, group='Combat', show_if=SHOW_MELEE,
                              help='which melee stat to train; re-applied each login since com_mode is not saved'),
    'spell': SettingDef('string', 'Wind Strike', 'Autocast spell', options=list(SPELL_DB), group='Combat', show_if=SHOW_MAGE,
                        help='kept armed via autocast — a staff must be wielded'),
    'runes_withdraw': SettingDef('number', 100, 'Casts of runes per bank trip', 1, 1000, group='Combat', show_if=SHOW_MAGE,
                                 help='when periodic banking is on, top runes up to this many casts (staff free runes skipped)'),
    'range_style': SettingDef('string', 'rapid', 'Ranged style', options=RANGE_STYLE_OPTIONS, group='Combat', show_if=SHOW_RANGE),
    'ammo': SettingDef('string', 'Bronze arrow', 'Ammo (kept + bank withdraw)', group='Combat', show_if=SHOW_RANGE),
    'ammo_withdraw': SettingDef('number', 200, 'Ammo per bank trip', 1, 5000, group='Combat', show_if=SHOW_RANGE,
                                help='when periodic banking is on, withdraw ammo up to this count after deposit'),
}
SETTINGS.update(PERIODIC_BANK_SETTINGS)


def now_ms():
    return time.time() * 1000


def withdraw_to(name, target):
    """Withdraws the item up to target held, and gives how many came. Use with yield from."""
    start = inventory.count(name)
    for _ in range(40):
        if inventory.count(name) >= target or inventory.is_full():
            break
        before = inventory.count(name)
        need = target - before
        if need > 10:
            took = yield from bank.withdraw_x(name, need)
            if took:
                if inventory.count(name) > before:
                    continue
                break
        bank.withdraw(name, 'Withdraw-10' if need >= 10 else ('Withdraw-5' if need >= 5 else 'Withdraw-1'))
        landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 2500)
        if not landed:
            break
    return inventory.count(name) - start


class SetCombatStyle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='set combat style')
        self.bot = bot
        self.announced = False
        self.fails = 0
        self.retry_at = 0

    def selected(self):
        bot = self.bot
        if bot.fight_kind == 'mage':
            return True
        if bot.fight_kind == 'range':
            return game.combat_mode() == bot.range_mode
        return game.has_combat_style(bot.melee_style)

    def validate(self):
        return self.bot.fight_kind != 'mage' and not game.in_combat() and not self.selected() and now_ms() >= self.retry_at

    def execute(self):
        bot = self.bot
        bot.status = 'setting combat style'
        if bot.fight_kind == 'range':
            game.set_combat_mode(bot.range_mode)
        else:
            game.set_combat_style(bot.melee_style)
        ok = yield from execution.delay_until(self.selected, 3000)
        if ok:
            self.fails = 0
            if not self.announced:
                self.announced = True
                if bot.fight_kind == 'range':
                    bot.log(f'ranged style set to {RANGE_MODE_NAMES[bot.range_mode]}')
                else:
                    resolution = game.combat_style_resolution(bot.melee_style)
                    if resolution:
                        bot.log(f'combat style set to {describe_combat_style(resolution)}')
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + STYLE_RETRY_MS
            bot.log(f'could not set the {bot.fight_kind} attack style — retrying in 60s')


class ArmAutocast(Task):
    def __init__(self, bot):
        Task.__init__(self, label='arm autocast')
        self.bot = bot
        self.fails = 0
        self.retry_at = 0

    def validate(self):
        bot = self.bot
        if bot.fight_kind != 'mage' or autocast.armed() or now_ms() < self.retry_at:
            return False
        return bot.casts_left() >= 1 and autocast.staff_tab_attached()

    def execute(self):
        bot = self.bot
        bot.status = f'arming autocast: {bot.spell}'
        yield from execution.delay_ticks(3)
        armed = yield from autocast.arm(bot.spell, bot.log)
        if armed:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= 5:
            self.fails = 0
            self.retry_at = now_ms() + STYLE_RETRY_MS
            bot.log(f"WARNING: could not arm autocast for '{bot.spell}' — retrying in 60s")


class ReequipGear(Task):
    def __init__(self, bot):
        Task.__init__(self, label='reequip gear')
        self.bot = bot
        self.fail_log_after = 0

    def candidates(self):
        bot = self.bot
        gear = list(bot.tracked_gear)
        if bot.fight_kind == 'range' and bot.ammo.lower() not in [g.lower() for g in gear]:
            gear.append(bot.ammo)
        return gear

    def validate(self):
        return len([g for g in self.candidates() if not equipment.contains(g) and inventory.first(g) is not None]) > 0

    def execute(self):
        bot = self.bot
        for item in self.candidates():
            if equipment.contains(item) or inventory.first(item) is None:
                continue
            bot.status = f're-equipping {item}'
            worn = yield from equipment.equip(item)
            if worn:
                bot.log(f'equipped {item}')
            elif now_ms() > self.fail_log_after:
                self.fail_log_after = now_ms() + 30000
                bot.log(f'WARNING: could not equip {item} — retrying')


class BuryBones(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bury bones')
        self.bot = bot

    def validate(self):
        return self.bot.bury_enabled and inventory.contains('Bones')

    def execute(self):
        bot = self.bot
        bot.status = 'burying bones'
        bones = inventory.first('Bones')
        if bones is None:
            return
        before = inventory.used()
        if not bones.interact('Bury'):
            bot.log(f"no Bury op on bones? ops=[{', '.join(bones.actions())}]")
            yield from execution.delay_ticks(2)
            return
        buried = yield from execution.delay_until(lambda: inventory.used() < before, 3000)
        if buried:
            bot.buried += 1
            bot.log('buried bones')


def drop_at(id, tile):
    return ground_items.query().where(lambda g: g.id == id and g.tile() == tile).nearest()


def loot_key(id, tile):
    return f'{id}|{tile.x}|{tile.z}|{tile.level}'


class LootDrops(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot drops')
        self.bot = bot

    def validate(self):
        return not game.in_combat() and self.find() is not None and not inventory.is_full()

    def find(self):
        bot = self.bot
        now = now_ms()
        skip = bot.loot_skip
        return (ground_items.query().where(lambda g: bot.wants_loot(g.name)).where(lambda g: bot.accepts_loot_at(g.tile()))
                .where(lambda g: skip.get(loot_key(g.id, g.tile()), 0) < now).within(bot.leash + 4).nearest())

    def execute(self):
        bot = self.bot
        drop = self.find()
        if drop is None:
            return
        name = drop.name or 'loot'
        id = drop.id
        tile = drop.tile()
        key = loot_key(id, tile)
        bot.status = f'looting {name} at {tile}'
        before = inventory.used()
        count_before = inventory.count(name)
        # Stackables may not take a new slot, so the count is watched too.
        status = yield from reach.entity_op(lambda: drop_at(id, tile), 'Take',
                                            lambda: inventory.used() > before or inventory.count(name) > count_before, False, 6000, name, bot.log)
        if status == 'done' and (inventory.used() > before or inventory.count(name) > count_before):
            bot.loot_skip.pop(key, None)
            bot.log(f'looted {name}')
        elif status == 'retry' or status == 'unreachable':
            bot.loot_skip[key] = now_ms() + LOOT_SKIP_MS
            bot.log(f'loot attempt did not complete — ignoring {name} at {tile.x},{tile.z} for {LOOT_SKIP_MS // 1000}s')


class Rest(Task):
    def __init__(self, bot):
        Task.__init__(self, label='rest')
        self.bot = bot

    def validate(self):
        return not game.in_combat() and skills.hp_fraction() < self.bot.hp_gate

    def execute(self):
        bot = self.bot
        bot.status = f"resting ({skills.effective('hitpoints')}/{skills.level('hitpoints')} hp)"
        rest_hp = bot.rest_hp
        yield from execution.delay_until(lambda: skills.hp_fraction() >= rest_hp or game.in_combat() or chat_dialog.can_continue(), 120000)


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot
        self.misses = 0

    def find_target(self):
        bot = self.bot
        anchor = bot.anchor
        leash = bot.leash
        return npcs.query().name(bot.target).action('Attack').where(lambda n: not n.in_combat and n.tile().distance_to(anchor) <= leash).nearest()

    def resnapshot(self, index):
        name = self.bot.target.lower()
        for n in npcs.all():
            if n.index == index and (n.name or '').lower() == name:
                return n
        return None

    def validate(self):
        bot = self.bot
        if game.in_combat() or skills.hp_fraction() < bot.hp_gate:
            return False
        if bot.fight_kind == 'mage' and bot.casts_left() < 1:
            return False
        if bot.fight_kind == 'range' and bot.total_ammo() < 1:
            return False
        return self.find_target() is not None

    def killed(self, name):
        self.bot.kills += 1
        self.bot.log(f'{name} killed')

    def execute(self):
        bot = self.bot
        mob = self.find_target()
        if mob is None:
            return
        name = bot.target
        index = mob.index
        bot.status = f'attacking {name} at {mob.tile()}'
        mark = game_messages.mark()
        if not mob.interact('Attack'):
            bot.log(f"no Attack op on {name}? ops=[{', '.join(mob.actions())}]")
            yield from execution.delay_ticks(2)
            return
        engaged = yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
        if not engaged or chat_dialog.can_continue():
            if not engaged:
                self.misses += 1
                if game_messages.saw_since(mark, CANT_REACH) or self.misses >= 2:
                    bot.log(f"can't engage {name} — a shut gate/fence in the way; walking through it")
                    bot.status = 'crossing the pen gate'
                    yield from traversal.walk_resilient(mob.tile(), radius=1, attempts=3, timeout_ms=45000, log=lambda m: bot.log(f'  {m}'))
                    self.misses = 0
            return
        self.misses = 0
        bot.status = 'fighting'
        deadline = now_ms() + FIGHT_MS
        reattacks = 0
        while now_ms() < deadline:
            if chat_dialog.can_continue() or bot.died:
                return
            if bot.fight_kind == 'range' and bot.wielded_ammo() == 0 and inventory.count(bot.ammo) > 0:
                bot.log('ammo left inventory — reloading quiver')
                return
            if bot.fight_kind == 'range' and bot.total_ammo() < 1:
                bot.log('out of ammo — breaking off')
                return
            if bot.fight_kind == 'mage' and bot.casts_left() < 1:
                bot.log('out of runes — breaking off')
                return
            me = game.tile()
            if me is None or mob.tile().distance_to(me) > bot.leash + 8:
                bot.log('displaced mid-fight — abandoning target')
                return
            current = self.resnapshot(index)
            if current is None:
                self.killed(name)
                return
            if current.health == 0 and current.max_health > 0:
                yield from execution.delay_until(lambda: self.resnapshot(index) is None, 10000)
                self.killed(name)
                return
            if not game.in_combat() and not current.in_combat:
                if reattacks >= 2:
                    bot.log(f'target disengaged twice — abandoning this {name.lower()}')
                    return
                reattacks += 1
                current.interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
                continue
            yield from execution.delay_ticks(2)


class ReturnToAnchor(Task):
    def __init__(self, bot):
        Task.__init__(self, label='return to anchor')
        self.bot = bot

    def validate(self):
        here = game.tile()
        return here is not None and self.bot.anchor.distance_to(here) > self.bot.leash

    def execute(self):
        bot = self.bot
        bot.status = 'returning to anchor'
        bot.log(f'web-walking to the hunting anchor {bot.anchor}')
        yield from traversal.walk_resilient(bot.anchor, radius=3, timeout_ms=120000, log=lambda m: bot.log(f'  {m}'))


class ChickenKiller(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.buried = 0
        self.kills = 0
        self.deaths = 0
        self.status = 'starting'
        self.died = False
        self.loot_skip = {}
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.leash = s.num('leash_radius', 12)
        self.hp_gate = s.num('fight_hp_gate', 45) / 100
        self.rest_hp = s.num('rest_until_hp', 70) / 100
        self.target = s.str('target_name', 'Chicken')
        self.loot = [t.strip() for t in s.str('loot_match', 'bones').lower().split('|') if t.strip()]
        self.bury_enabled = s.bool('bury_bones', True)
        self.parse_combat_settings()
        self.tracked_gear = [i.name for i in equipment.items() if i.name]
        hinted = recovery_hints.take_anchor()
        here = game.tile()
        self.anchor = self.select_anchor(here, hinted)
        recovery_hints.anchor = self.anchor
        if hinted is not None:
            self.log(f'recovery restart — keeping original anchor {self.anchor}')
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(k) for k in COMBAT_SKILLS])
        self.log(f'anchored at {self.anchor}, hunting {self.target}, leash {self.leash}, style {self.fight_kind} ({self.style_note()})')
        yield from self.prepare_for_travel(here)
        self.on('chat_message', self.heard)
        self.add(
            ContinueDialog(lambda: self.set_status('continuing dialog')),
            DeathRecovery(self, self.anchor, 3, on_death=self.died_now, on_recovered=self.recovered),
            PeriodicBank(
                strategy=lambda: parse_bank_strategy(self.settings.str('bank_strategy', 'Off')),
                items_threshold=lambda: self.settings.num('bank_every_items', 15),
                minutes_threshold=lambda: self.settings.num('bank_every_minutes', 10),
                count_loot=self.depositables,
                deposit=deposit_all_except(self.keep_list()),
                after_deposit=self.after_bank_deposit,
                destination=self.bank_destination,
                return_to=lambda: self.anchor,
                set_status=self.set_status,
                log=self.log,
            ),
            BuryBones(self), LootDrops(self), Rest(self), ReequipGear(self), SetCombatStyle(self), ArmAutocast(self), Fight(self), ReturnToAnchor(self),
        )

    def parse_combat_settings(self):
        s = self.settings
        raw = s.str('combat_style', 'melee').strip().lower()
        if raw in LEGACY_MELEE:
            self.fight_kind = 'melee'
            self.melee_style = parse_combat_style(raw)
        else:
            self.fight_kind = raw if raw in ['mage', 'range', 'melee'] else 'melee'
            self.melee_style = parse_combat_style(s.str('melee_style', 'strength'))
        self.spell = s.str('spell', 'Wind Strike')
        self.runes_withdraw = s.num('runes_withdraw', 100)
        self.range_mode = parse_range_style(s.str('range_style', 'rapid'))
        self.ammo = s.str('ammo', 'Bronze arrow')
        self.ammo_withdraw = s.num('ammo_withdraw', 200)

    def style_note(self):
        if self.fight_kind == 'mage':
            return self.spell
        if self.fight_kind == 'range':
            return f'{RANGE_MODE_NAMES[self.range_mode]}, {self.ammo}'
        return self.melee_style

    def heard(self, e):
        t = (e.text or '').lower()
        if 'oh dear' in t and 'you are dead' in t:
            self.died = True

    def died_now(self):
        self.status = 'died — recovering'
        self.deaths += 1
        self.log('died! waiting for respawn, then walking back to the anchor')

    def recovered(self):
        self.died = False
        self.log('back at the anchor')

    def set_status(self, status):
        self.status = status

    def grind_targets(self):
        return [self.target.lower()]

    def recovery_anchor(self):
        return self.anchor

    # Hooks a preset such as CowKiller overrides.

    def select_anchor(self, here, hinted):
        return hinted if hinted is not None else here

    def prepare_for_travel(self, start):
        """Use with yield from."""
        if False:
            yield

    def after_bank_deposit(self):
        """After the periodic bank's deposit: restocks the style's ammo or runes. Use with yield from."""
        yield from self.restock_style_supplies()

    def bank_destination(self):
        return None

    def accepts_loot_at(self, tile):
        return True

    def keep_list(self):
        keep = []
        if self.bury_enabled:
            keep.append('Bones')
        if self.fight_kind == 'range':
            keep.append(self.ammo)
        if self.fight_kind == 'mage':
            for row in rune_withdraw_list(self.spell, self.wielded_names(), 1):
                keep.append(row['rune'])
        for g in self.tracked_gear:
            if g.lower() not in [k.lower() for k in keep]:
                keep.append(g)
        return keep

    def wants_loot(self, name):
        n = (name or '').lower()
        return len([t for t in self.loot if t in n]) > 0

    def depositables(self):
        keep = [k.lower() for k in self.keep_list()]
        return len([i for i in inventory.items() if i.name and i.name.lower() not in keep])

    def wielded_names(self):
        return [i.name or '' for i in equipment.items()]

    def casts_left(self):
        return casts_available(self.spell, self.wielded_names(), inventory.count)

    def wielded_ammo(self):
        for i in equipment.items():
            if (i.name or '').lower() == self.ammo.lower():
                return i.count
        return 0

    def total_ammo(self):
        return inventory.count(self.ammo) + self.wielded_ammo()

    def restock_style_supplies(self):
        """Use with yield from."""
        if not bank.is_open() or self.fight_kind == 'melee':
            return
        if self.fight_kind == 'mage':
            self.status = 'withdrawing runes'
            for row in rune_withdraw_list(self.spell, self.wielded_names(), self.runes_withdraw):
                rune = row['rune']
                if inventory.count(rune) < row['count']:
                    got = yield from withdraw_to(rune, row['count'])
                    self.log(f"withdrew {got} {rune} ({inventory.count(rune)}/{row['count']})")
            self.log(f'runes restocked: {self.casts_left()} casts left')
            return
        self.status = f'restocking {self.ammo}'
        got = yield from withdraw_to(self.ammo, self.ammo_withdraw)
        if got > 0:
            self.log(f'withdrew {got} {self.ammo} ({self.total_ammo()} total in quiver + inventory)')
        if inventory.count(self.ammo) > 0 and self.wielded_ammo() == 0:
            worn = yield from equipment.equip(self.ammo)
            if worn:
                self.log(f'equipped {self.ammo} ({self.wielded_ammo()} in quiver)')
            else:
                self.log(f'WARNING: could not equip {self.ammo} — will retry from inventory')

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(k) for k in COMBAT_SKILLS]) - self.xp_at_start
        if self.fight_kind == 'mage':
            supply = ('Casts', int(self.casts_left()))
        elif self.fight_kind == 'range':
            supply = ('Ammo', self.total_ammo())
        else:
            supply = ('Style', self.melee_style)
        return {'Status': self.status, 'Kills': self.kills, 'Combat xp': gained, 'XP/hr': f'{gained / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—',
                supply[0]: supply[1], 'Buried': self.buried, 'Deaths': self.deaths}


BOT = define_bot(
    name='ChickenKiller',
    create=ChickenKiller,
    description='Kills chickens, loots and buries bones (anchor = start tile)',
    category='Combat',
    tags=['lumbridge', 'bones', 'feathers', 'afk'],
    settings_schema=SETTINGS,
)

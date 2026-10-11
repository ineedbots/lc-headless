# Kills cows, picks up their hides, and banks them every so often: rs2b0t's ChickenKiller with its CowKiller
# preset (MIT, see thirdparty/rs2b0t), in melee. The Lumbridge field banks at Al Kharid through the toll gate,
# so it keeps 20 coins for the toll; the other fields bank at Draynor or Falador.

from rs2004.catalogs import COW_LOCATION_OPTIONS, TOLL_COIN_TARGET, AL_KHARID_BANK, ContinueDialog, DeathRecovery
from rs2004.catalogs import resolve_cow_location, cow_bank_destination, is_cow_field_loot_tile, needs_toll_coins
from rs2004.catalogs import should_bootstrap_toll_coins

SETTINGS = {
    'location': SettingDef('string', 'Auto', 'Cow field', options=COW_LOCATION_OPTIONS, help='Auto picks the nearer field; Start tile fights where you stand'),
    'al_kharid_toll_coins': SettingDef('boolean', True, 'Keep 20 coins for the Al Kharid gate'),
    'leash_radius': SettingDef('number', 18, 'Leash radius (tiles)', 3, 30),
    'fight_hp_gate': SettingDef('number', 45, 'Stop fighting below HP%', 0, 100),
    'rest_until_hp': SettingDef('number', 70, 'Rest until HP%', 0, 100),
    'target_name': SettingDef('string', 'Cow', 'Target NPC name'),
    'loot_match': SettingDef('string', 'Cowhide', 'Loot name match (| = OR)'),
    'bury_bones': SettingDef('boolean', False, 'Bury bones'),
    'melee_style': SettingDef('string', 'strength', 'Melee style', options=COMBAT_STYLE_OPTIONS),
}
SETTINGS.update(PERIODIC_BANK_SETTINGS)
SETTINGS['bank_strategy'] = SettingDef('string', 'Loot count', 'Periodic bank', options=['Off', 'Loot count', 'Time', 'Either'])
SETTINGS['bank_every_items'] = SettingDef('number', 20, 'Bank at N loot items', 1, 27)

# A ground stack whose pickup failed is left alone this long, so a pile another player took isn't chased.
LOOT_SKIP_MS = 30000
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints']


class CowKiller(TaskBot):
    def on_start(self):
        s = self.settings
        self.leash = int(s.leash_radius)
        self.hp_gate = s.fight_hp_gate / 100
        self.rest_hp = s.rest_until_hp / 100
        self.target = s.target_name
        self.loot = [t.strip().lower() for t in s.loot_match.lower().split('|') if t.strip()]
        self.kills = 0
        self.deaths = 0
        self.buried = 0
        self.loot_skip = {}
        self.xp_start = sum([skills.xp(skill) for skill in COMBAT_SKILLS])
        self.gear = [i.name for i in equipment.items() if i.name]

        here = game.tile()
        self.field = resolve_cow_location(s.location, here)
        self.anchor = self.field.anchor if self.field is not None else here
        log('cow field:', self.field.name if self.field is not None else 'start tile', 'at', self.anchor)

        if should_bootstrap_toll_coins(self.field, here, inventory.count('Coins'), s.al_kharid_toll_coins):
            yield from self.fetch_toll_coins()

        self.add(
            ContinueDialog(),
            DeathRecovery(self, self.anchor, 3, on_death=lambda: self.died()),
            PeriodicBank(
                strategy=lambda: parse_bank_strategy(self.settings.bank_strategy),
                items_threshold=lambda: self.settings.bank_every_items,
                minutes_threshold=lambda: self.settings.bank_every_minutes,
                count_loot=lambda: self.depositables(),
                deposit=deposit_all_except(self.keep_list()),
                after_deposit=lambda: self.top_up_toll_coins(),
                common_junk=lambda: self.settings.bank_common_junk,
                return_to=lambda: self.anchor,
                destination=lambda: self.bank_destination(),
                log=lambda m: log(m),
            ),
            Task(lambda: self.settings.bury_bones and inventory.contains('Bones'), self.bury, 'bury'),
            Task(lambda: not game.in_combat() and not inventory.is_full() and self.find_loot() is not None, self.take_loot, 'loot'),
            Task(lambda: not game.in_combat() and skills.hp_fraction() < self.hp_gate, self.rest, 'rest'),
            Task(lambda: len(self.gear_to_wear()) > 0, self.reequip, 'reequip'),
            Task(lambda: not game.in_combat() and not game.has_combat_style(self.settings.melee_style), self.set_style, 'style'),
            Task(lambda: not game.in_combat() and skills.hp_fraction() >= self.hp_gate and self.find_target() is not None, self.fight, 'fight'),
            Task(lambda: game.tile().distance_to(self.anchor) > self.leash, self.walk_back, 'return'),
        )

    def grind_targets(self):
        return [self.settings.target_name.lower()]

    def recovery_anchor(self):
        return self.anchor

    def died(self):
        self.deaths += 1
        log('died; walking back once respawned')

    # What the bank keeps and where it is.

    def uses_toll_coins(self):
        return needs_toll_coins(self.field, self.settings.al_kharid_toll_coins)

    def keep_list(self):
        keep = list(self.gear)
        if self.settings.bury_bones:
            keep.append('Bones')
        if self.uses_toll_coins():
            keep.append('Coins')
        return keep

    def depositables(self):
        kept = [k.lower() for k in self.keep_list()]
        return len([i for i in inventory.items() if i.name and i.name.lower() not in kept])

    def bank_destination(self):
        where = cow_bank_destination(self.field, self.settings.al_kharid_toll_coins)
        if where is None:
            return None
        for known in bank_locations():
            tile = known['tile']
            if tile['x'] == where[1].x and tile['z'] == where[1].z and tile['level'] == where[1].level:
                return known
        return None

    def fetch_toll_coins(self):
        log('fetching', TOLL_COIN_TARGET, 'toll coins from Al Kharid bank first')
        arrived = yield from traversal.walk_resilient(AL_KHARID_BANK, radius=4, timeout_ms=90000, log=lambda m: log(' ', m))
        opened = False
        if arrived:
            opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            log('could not open Al Kharid bank for toll coins; going without them')
            return
        yield from self.top_up_toll_coins()

    def top_up_toll_coins(self):
        if not self.uses_toll_coins():
            return
        need = TOLL_COIN_TARGET - inventory.count('Coins')
        if need <= 0:
            return
        if bank.count('Coins') < need:
            log('the toll float needs', need, 'coins, but the bank has', bank.count('Coins'))
            return
        yield from bank.withdraw_x('Coins', need)
        log('toll float:', inventory.count('Coins'), 'coins')

    # Fighting.

    def find_target(self):
        anchor = self.anchor
        leash = self.leash
        return npcs.query().name(self.target).action('Attack').where(lambda n: not n.in_combat and n.tile().distance_to(anchor) <= leash).nearest()

    def fight(self):
        cow = self.find_target()
        if cow is None:
            return
        mark = game_messages.mark()
        if not cow.interact('Attack'):
            yield from execution.delay_ticks(2)
            return
        engaged = yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
        if not engaged:
            if game_messages.saw_since(mark, CANT_REACH):
                log("can't reach the cow; walking through the gate")
                yield from traversal.walk_resilient(cow.tile(), radius=1, attempts=3, timeout_ms=45000, log=lambda m: log(' ', m))
            return
        index = cow.index
        name = self.target.lower()
        deadline = game.tick() + 150
        reattacks = 0
        while game.tick() < deadline:
            if chat_dialog.can_continue():
                return
            current = npcs.get(index)
            if current is None or (current.name or '').lower() != name:
                self.kills += 1
                return
            if not game.in_combat() and not current.in_combat:
                if reattacks >= 2:
                    return
                reattacks += 1
                current.interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
                continue
            yield from execution.delay_ticks(2)

    def set_style(self):
        game.set_combat_style(self.settings.melee_style)
        yield from execution.delay_until(lambda: game.has_combat_style(self.settings.melee_style), 3000)

    def rest(self):
        log('resting at', skills.effective('hitpoints'), '/', skills.level('hitpoints'), 'hp')
        rest_hp = self.rest_hp
        yield from execution.delay_until(lambda: skills.hp_fraction() >= rest_hp or game.in_combat() or chat_dialog.can_continue(), 120000)

    def gear_to_wear(self):
        return [g for g in self.gear if not equipment.contains(g) and inventory.first(g) is not None]

    def reequip(self):
        for name in self.gear_to_wear():
            worn = yield from equipment.equip(name)
            log('equipped' if worn else 'could not equip', name)

    def walk_back(self):
        log('walking back to the field at', self.anchor)
        yield from traversal.walk_resilient(self.anchor, radius=3, timeout_ms=120000, log=lambda m: log(' ', m))

    # Loot.

    def wants(self, name):
        lower = (name or '').lower()
        return len([t for t in self.loot if t in lower]) > 0

    def find_loot(self):
        now = game.tick()
        anchor = self.anchor
        leash = self.leash
        skip = self.loot_skip
        query = ground_items.query().where(lambda g: self.wants(g.name))
        query = query.where(lambda g: is_cow_field_loot_tile(anchor, leash, g.tile()))
        query = query.where(lambda g: skip.get((g.id, g.tile().x, g.tile().z), -1) < now)
        return query.within(leash + 4).nearest()

    def take_loot(self):
        drop = self.find_loot()
        if drop is None:
            return
        name = drop.name
        id = drop.id
        tile = drop.tile()
        used = inventory.used()
        held = inventory.count(name)
        status = yield from reach.entity_op(
            lambda: self.drop_at(id, tile),
            'Take', lambda: inventory.used() > used or inventory.count(name) > held, False, 6000, name)
        if status != 'done':
            self.loot_skip[(id, tile.x, tile.z)] = game.tick() + LOOT_SKIP_MS // 600
            log('could not take the', name, 'at', tile, '; leaving it for a while')

    def drop_at(self, id, tile):
        return ground_items.query().where(lambda g: g.id == id and g.tile() == tile).nearest()

    def bury(self):
        bones = inventory.first('Bones')
        if bones is None:
            return
        used = inventory.used()
        bones.interact('Bury')
        buried = yield from execution.delay_until(lambda: inventory.used() < used, 3000)
        if buried:
            self.buried += 1

    def on_progress_report(self):
        xp = sum([skills.xp(skill) for skill in COMBAT_SKILLS]) - self.xp_start
        return {'Kills': self.kills, 'Combat xp': xp, 'Hides held': inventory.count('Cowhide'), 'Deaths': self.deaths}


BOT = define_bot(
    name='Cow killer',
    create=CowKiller,
    description="Kills cows, takes their hides, and banks them every so often; rs2b0t's CowKiller",
    category='Combat',
    settings_schema=SETTINGS,
)

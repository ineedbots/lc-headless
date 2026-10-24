# Wanders the overworld picking up drops by exact name, without fighting: rs2b0t's WanderLooter (MIT, see
# thirdparty/rs2b0t). It eats the chosen food, flees to the nearest bank when low with none, banks the loot and the
# spare food, and leaves alone drops where it took damage.

from bots.wanderlooter.logic import DANGER_RADIUS, DANGER_WINDOW_MS, DEFAULT_LOOT, LootBlacklist, matches_loot, now_ms
from bots.wanderlooter.tasks import BankRun, EatFood, FleeLowHealth, IdleBank, LootDrops, Wander, eat_one
from rs2004.catalogs import ContinueDialog, food_count, script_food, should_eat_food, sustain

SETTINGS = {
    'loot': SettingDef('string[]', DEFAULT_LOOT, 'Loot item names (exact)', csv_toggle='loot_mode',
                       help='exact item names, case-insensitive; defaults to the current event drop'),
    'loot_mode': SettingDef('string', 'list', 'Loot entry mode', options=['list', 'csv'], option_labels={'list': 'List (chips)', 'csv': 'CSV (text + copy/paste)'},
                            help='List = add items one at a time. CSV = paste a comma-separated list.'),
    'food': SettingDef('string', '', 'Food to eat', help='exact item name (e.g. Shark, Monkfish, Trout). Leave blank to use the loadout food, falling back to Trout'),
    'food_withdraw': SettingDef('number', 0, 'Food to carry', 0, 27, group='Food & safety'),
    'panic_hp': SettingDef('number', 25, 'Flee below HP% (no food)', 0, 100, group='Food & safety'),
    'bank_at_loot_slots': SettingDef('number', 28, 'Bank at loot slots', 1, 28, group='Banking'),
    'wander_distance': SettingDef('number', 30, 'Wander distance (tiles)', 5, 60, group='Wandering'),
    'bank_after_minutes': SettingDef('number', 10, 'Bank after no loot (minutes)', 1, 240, group='Wandering'),
}

# Why: a route search for a wander target that has none mustn't hold the loop for long.
WANDER_PATH_EXPANSIONS = 300000


class WanderLooter(TaskBot):
    loop_delay = 600

    def on_start(self):
        self.blacklist = LootBlacklist()
        self.status = 'starting'
        self.looted = 0
        self.bank_trips = 0
        self.wanders = 0
        self.eats = 0
        self.last_hp = 0
        self.last_damage_at = 0
        self.last_damage_tile = None
        # (id, tile, at) of the last pickup, while a hit beside it could still be its fault.
        self.recent_pickup = None
        self.last_wander_dir = None
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.loot_names = [name.strip() for name in self.settings.list('loot', DEFAULT_LOOT) if name.strip()]
        if len(self.loot_names) == 0:
            raise ValueError('WanderLooter: loot list is empty')
        self.food_name = self.settings.str('food', '').strip() or script_food(self.settings, 'Trout')
        self.food_withdraw = self.settings.num('food_withdraw', 0)
        self.panic_at = self.settings.num('panic_hp', 25) / 100
        self.bank_at = self.settings.num('bank_at_loot_slots', 28)
        self.wander_distance = self.settings.num('wander_distance', 30)
        self.bank_after_ms = self.settings.num('bank_after_minutes', 10) * 60000
        now = now_ms()
        self.started_at = now
        self.last_loot_at = now

        sustain.set(lambda: eat_one(self))
        self.add(ContinueDialog(), EatFood(self), FleeLowHealth(self), BankRun(self), IdleBank(self), LootDrops(self), Wander(self))
        self.log(f"WanderLooter starting — loot [{', '.join(self.loot_names)}], food '{self.food_name}'x{self.food_withdraw}, "
                 + f'bank at {self.bank_at} slots, wander {self.wander_distance} tiles when idle, bank after {self.bank_after_ms // 60000}m without loot')

    def on_stop(self, reason):
        sustain.set(None)

    def loop(self):
        self.observe_health()
        yield from TaskBot.loop(self)

    def on_progress_report(self):
        return {
            'Status': self.status,
            'Runtime': f'{round((now_ms() - self.started_at) / 60000)}m',
            'Looted': self.looted,
            'Trips': self.bank_trips,
            'Wanders': self.wanders,
            'Blocked': self.blacklist.count(),
            'Food': self.food_count(),
            'Recent loot': f'{self.recent_pickup[1]}' if self.recent_pickup is not None else 'wandering',
        }

    def food_count(self):
        return food_count(inventory.items(), self.food_name)

    def need_eat(self):
        return should_eat_food(self.food_name, skills.effective('hitpoints'), skills.level('hitpoints'), self.food_count())

    def loot_slots(self):
        return len([item for item in inventory.items() if matches_loot(item.name, self.loot_names)])

    def find_loot(self):
        return ground_items.query().action('Take').where(
            lambda g: matches_loot(g.name, self.loot_names) and not self.blacklist.blocked(g.id, g.tile()) and reachability.walkable(g.tile())).nearest()

    def find_loot_at(self, id, tile):
        return ground_items.query().where(lambda g: g.id == id and g.tile().equals(tile)).nearest()

    def can_wander_to(self, tile):
        """A cheap filter of candidates; can_walk_to does the door-aware route check."""
        here = game.tile()
        if here is None:
            return False
        if tile.level == here.level:
            return True
        return here.level > 0 and tile.level == here.level - 1 and tile.x == here.x and tile.z == here.z

    def can_walk_to(self, tile):
        """The loaded area's reach first, since it's quick, then the walker's map, so doors and stairs count."""
        here = game.tile()
        if here is None:
            return False
        if tile.level == here.level and reachability.walkable(tile) and reachability.can_reach(tile):
            return True
        return navigator.find_path(here, tile, max_expansions=WANDER_PATH_EXPANSIONS, policy={'use_teleports': False}).ok

    def note_loot(self, now):
        self.last_loot_at = now
        self.looted += 1

    def observe_health(self, now=None):
        """Notes damage, and blacklists the last pickup's tile when a hit lands beside it soon after. Returns the
        hitpoints."""
        now = now if now is not None else now_ms()
        hp = skills.effective('hitpoints')
        tile = game.tile()
        if self.recent_pickup is not None and now - self.recent_pickup[2] > DANGER_WINDOW_MS:
            self.recent_pickup = None
        if self.last_hp > 0 and hp < self.last_hp and tile is not None:
            self.last_damage_at = now
            self.last_damage_tile = Tile.from_tile(tile)
            pickup = self.recent_pickup
            if pickup is not None and now - pickup[2] <= DANGER_WINDOW_MS and pickup[1].distance_to(tile) <= DANGER_RADIUS:
                self.blacklist.mark_unsafe(pickup[0], pickup[1])
                self.log(f'blacklisting loot at {pickup[1]} for 30m — took damage after looting')
                self.recent_pickup = None
        self.last_hp = hp
        return hp

    def damage_near(self, tile, now=None):
        now = now if now is not None else now_ms()
        return self.last_damage_tile is not None and now - self.last_damage_at <= DANGER_WINDOW_MS and self.last_damage_tile.distance_to(tile) <= DANGER_RADIUS

    def note_pickup(self, id, tile, now):
        self.recent_pickup = (id, Tile.from_tile(tile), now)

    def note_wander(self, start=None, end=None):
        if start is not None and end is not None and start.level == end.level:
            dx = sign(end.x - start.x)
            dz = sign(end.z - start.z)
            self.last_wander_dir = None if dx == 0 and dz == 0 else (dx, dz)
        self.wanders += 1

    def restart_idle_timer(self):
        self.last_loot_at = now_ms()


def sign(n):
    return 1 if n > 0 else (-1 if n < 0 else 0)


BOT = define_bot(
    name='WanderLooter',
    create=WanderLooter,
    description='Wanders the overworld looting exact-name drops without fighting. Eats configured food, flees to the nearest bank when low on health without food, banks excess loot and food, and avoids tiles where it took damage.',
    category='Money making',
    tags=['loot', 'wandering', 'banking', 'food', 'event', 'pumpkin'],
    settings_schema=SETTINGS,
)

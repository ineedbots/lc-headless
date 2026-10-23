# Fights chaos druids, in Edgeville dungeon, the Chaos Druid Tower or Yanille dungeon, looting herbs and law and
# nature runes, and banks the haul with a fresh, exact load of food each trip: rs2b0t's ChaosDruidKiller (MIT, see
# thirdparty/rs2b0t).

import math
import time

from rs2004.catalogs import LOADOUT_SETTING, ContinueDialog, food_count, food_heal_amount, is_food_item, script_food, should_eat_to_use_food


class Bounds:
    def __init__(self, min_x, max_x, min_z, max_z):
        self.min_x = min_x
        self.max_x = max_x
        self.min_z = min_z
        self.max_z = max_z

    def contains(self, tile):
        return tile.x >= self.min_x and tile.x <= self.max_x and tile.z >= self.min_z and tile.z <= self.max_z


class DruidSpot:
    def __init__(self, npc, field, radius, bank_stand, dungeon, requires):
        self.npc = npc
        self.field = field
        self.radius = radius
        self.bank_stand = bank_stand
        self.dungeon = dungeon
        # (skill, level), or None
        self.requires = requires


# 3110,9936 is in the room's main walkable area; the 3109,9937 at its centre is a two-tile pocket that can't be
# walked to.
CHAOS_DRUID_FIELD = Tile(3110, 9936, 0)
CHAOS_DRUID_FIELD_RADIUS = 14
EDGEVILLE_DUNGEON_BOUNDS = Bounds(3072, 3199, 9792, 10047)
# m40_148 (the warriors' and the ledge's levels) and m40_149 (the pit under the ledge)
YANILLE_DUNGEON_BOUNDS = Bounds(2560, 2623, 9472, 9599)
CHAOS_DRUID_TOWER_BOUNDS = Bounds(2560, 2564, 3352, 3360)
SWARM_ID = 411
DRUID_SPOTS = {
    'Edgeville Dungeon': DruidSpot('Chaos druid', CHAOS_DRUID_FIELD, CHAOS_DRUID_FIELD_RADIUS, Tile(3094, 3491, 0), EDGEVILLE_DUNGEON_BOUNDS, None),
    'Chaos Druid Tower': DruidSpot('Chaos druid', Tile(2562, 3356, 0), 4, Tile(2616, 3332, 0), None, ('thieving', 46)),
    'Yanille Dungeon': DruidSpot('Chaos druid warrior', Tile(2580, 9501, 0), 8, Tile(2612, 3092, 0), YANILLE_DUNGEON_BOUNDS, ('agility', 40)),
}
DRUID_LOCATION_NAMES = list(DRUID_SPOTS)

LADDER_NAME = 'Ladder'
LADDER_OP = 'Climb-up'
LADDER_STAND = Tile(3096, 9868, 0)
TRAPDOOR_NAME = 'Trapdoor'
TRAPDOOR_STAND = Tile(3096, 3468, 0)
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
INTERMEDIATE_GATE = Tile(3103, 9909, 0)
WILDERNESS_GATE = Tile(3130, 9914, 0)
TOWER_DOOR_NAME = 'Door'
TOWER_DOOR_OP = 'Pick Lock'
TOWER_DOOR_STAND = Tile(2565, 3356, 0)
LEDGE_NAME = 'Balancing ledge'
LEDGE_OP = 'Walk-across'
LEDGE_NORTH_STAND = Tile(2580, 9520, 0)
LEDGE_SOUTH_STAND = Tile(2580, 9512, 0)
MAX_LEDGE_FALL_STREAK = 8
COMBAT_SKILLS = ['attack', 'strength', 'defence', 'hitpoints']
SLASH_WEAPONS = ['scimitar', 'sword', 'dagger', 'axe', 'halberd']
STYLE_RETRY_MS = 60000
FIGHT_MS = 90000

SETTINGS = {
    'location': SettingDef('string', 'Edgeville Dungeon', 'Location', options=DRUID_LOCATION_NAMES, group='Location',
                           help='Tower: picklock the door (46 Thieving). Yanille: Chaos druid warriors past the 40 Agility ledge — bring a slash weapon or knife for the entrance web'),
    'loadout': LOADOUT_SETTING,
    'combat_style_index': SettingDef('string', '1', 'Combat style', options=['0', '1', '2', '3'], group='Combat',
                                     option_labels={'0': '0 — first button', '1': '1 — second button', '2': '2 — third button', '3': '3 — fourth button'},
                                     help='which combat-tab style button to select, counted top-to-bottom. What each one trains depends on the weapon (the resolved name is logged at startup), so this works with weapons that have no Controlled or no Defensive option.'),
    'food_withdraw': SettingDef('number', 12, 'Food per trip', 1, 27, group='Food & healing'),
    'panic_hp': SettingDef('number', 35, 'Bank below HP% (no food)', 1, 98, group='Food & healing',
                           help='leave the dungeon when food is gone and HP reaches this threshold'),
}


# The pure decisions, kept apart from the game so they can be tested without a client.

def yanille_zone(tile):
    if not YANILLE_DUNGEON_BOUNDS.contains(tile):
        return 'outside'
    if tile.z >= 9536:
        return 'pit'
    return 'north' if tile.z >= 9519 else 'warrior'


def chaos_druid_bank_reason(trip_prepared, inventory_full, wanted_loot_visible, food, hp_fraction, panic_hp_fraction):
    """The three ends to a trip, or None."""
    if not trip_prepared:
        return 'prepare-trip'
    if inventory_full and (food == 0 or not wanted_loot_visible):
        return 'loot-full'
    if food == 0 and hp_fraction <= panic_hp_fraction:
        return 'low-health'
    return None


def chaos_druid_loot_space_action(inventory_full, food, hp, max_hp, merges_into_existing_stack=False):
    """How to make room for a wanted drop without throwing that drop away."""
    if not inventory_full or merges_into_existing_stack:
        return 'take'
    if food == 0:
        return 'bank'
    return 'eat-food' if hp < max_hp else 'drop-food'


def chaos_druid_drop_merges(drop_name, carried_names):
    """Law runes are the only wanted drop that stacks."""
    wanted = (drop_name or '').strip().lower()
    return wanted == 'law rune' and len([n for n in carried_names if (n or '').strip().lower() == wanted]) > 0


def chaos_druid_food_shortfall(configured, carried):
    return max(0, math.floor(configured) - max(0, math.floor(carried)))


def is_chaos_druid_loot(name):
    n = (name or '').strip().lower()
    return n == 'herb' or n == 'law rune' or n == 'nature rune'


def chaos_druid_area(tile, dungeon):
    if tile is None:
        return 'unknown'
    if dungeon is not None and dungeon.contains(tile):
        return 'druid-dungeon'
    return 'other-underground' if tile.z > 6400 else 'surface'


def chaos_druid_respawned(previous, current, trip_prepared):
    """A missed death message, read from the otherwise impossible jump from the dungeon to the surface."""
    return trip_prepared and previous == 'druid-dungeon' and current == 'surface'


def in_edgeville_dungeon(tile):
    return chaos_druid_area(tile, EDGEVILLE_DUNGEON_BOUNDS) == 'druid-dungeon'


def in_chaos_druid_tower(tile):
    """The locked room is 5x9, and Swarm's evade can't leave its tile."""
    return tile is not None and tile.level == 0 and CHAOS_DRUID_TOWER_BOUNDS.contains(tile)


def in_chaos_druid_field(tile, spot):
    if tile is None:
        return False
    area = chaos_druid_area(tile, spot.dungeon)
    if spot.dungeon is not None:
        if area != 'druid-dungeon':
            return False
    elif area != 'surface' or tile.level != spot.field.level:
        return False
    return max(abs(tile.x - spot.field.x), abs(tile.z - spot.field.z)) <= spot.radius


def swarm_npc_nearby(within=8):
    return len([n for n in npcs.all() if n.distance() <= within and ((n.name or '').lower() == 'swarm' or n.id == SWARM_ID)]) > 0


def is_open_op(a):
    return a.lower() == 'open'


def open_op(loc):
    ops = [a for a in loc.actions() if is_open_op(a)]
    return ops[0] if len(ops) > 0 else None


def openable_at(tile):
    """Whether a loc on tile still offers Open."""
    return locs.query().within(5).where(lambda l: l.tile().x == tile.x and l.tile().z == tile.z and open_op(l) is not None).first() is not None


def now_ms():
    return time.time() * 1000


def bank_reason(bot):
    bot.observe_lifecycle()
    wanted_visible = ground_items.query().where(lambda g: is_chaos_druid_loot(g.name)).within(bot.spot.radius + 3).nearest() is not None
    return chaos_druid_bank_reason(bot.trip_prepared, inventory.is_full(), wanted_visible, bot.food_count(), skills.hp_fraction(), bot.panic_hp_fraction)


def eat_once(bot):
    """Use with yield from."""
    food = bot.selected_food()
    if food is None:
        return False
    bot.status = f"eating {food.name} ({skills.effective('hitpoints')}/{skills.level('hitpoints')} hp)"
    before_hp = skills.effective('hitpoints')
    before_name = food.name
    before_used = inventory.used()
    if not food.interact('Eat'):
        return False

    def ate():
        now = bot.selected_food()
        return skills.effective('hitpoints') > before_hp or inventory.used() < before_used or (now.name if now is not None else None) != before_name

    done = yield from execution.delay_until(ate, 4000)
    return done


def drop_one_food(bot):
    """Use with yield from."""
    food = bot.selected_food()
    if food is None:
        return False
    before = inventory.used()
    bot.status = f'dropping {food.name} for loot'
    if not food.interact('Drop'):
        return False
    dropped = yield from execution.delay_until(lambda: inventory.used() < before, 4000)
    if dropped:
        bot.food_sacrificed += 1
        bot.log(f'dropped 1 {food.name} to make room for a Chaos-druid drop')
    return dropped


class Parked(Task):
    def __init__(self, bot):
        Task.__init__(self, label='parked')
        self.bot = bot

    def validate(self):
        return self.bot.parked

    def execute(self):
        yield from execution.delay_ticks(10)


class LocationGuard(Task):
    def __init__(self, bot):
        Task.__init__(self, label='location guard')
        self.bot = bot

    def validate(self):
        return chaos_druid_area(game.tile(), self.bot.spot.dungeon) == 'other-underground'

    def execute(self):
        self.bot.park('entered an underground map this route cannot exit. Reach the surface or the druid field, then restart.')


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return not bank.is_open() and self.bot.need_eat()

    def execute(self):
        yield from eat_once(self.bot)


class EvadeTowerSwarm(Task):
    def __init__(self, bot):
        Task.__init__(self, label='evade tower swarm')
        self.bot = bot

    # Swarm never despawns while it stays in the room, so it walks out first.
    def validate(self):
        return self.bot.inside_tower() and swarm_npc_nearby()

    def execute(self):
        bot = self.bot
        bot.status = 'leaving the tower to lose Swarm'
        bot.log('Swarm in the tower — opening the door so we can run it off outside')
        out = yield from bot.walk_opening(TOWER_DOOR_STAND, 1)
        if not out:
            door = locs.query().name('Door').within(4).where(lambda l: open_op(l) is not None).nearest()
            if door is not None:
                door.interact(open_op(door))
            yield from execution.delay_until(lambda: not bot.inside_tower(), 8000)
        if bot.inside_tower():
            bot.log('still inside the tower after the Swarm exit — will retry')


# Why: which of Accurate, Aggressive, Controlled and Defensive a weapon has differs, so the style is picked by its
# button's place, as a pick by name lands on the wrong one; the style isn't saved, so it's set again after a login.
class SetCombatStyle(Task):
    """Selects the configured combat-tab button."""

    def __init__(self, bot):
        Task.__init__(self, label='set combat style')
        self.bot = bot
        self.announced = False
        self.retry_at = 0

    # The bank's window owns the screen; a tab button pressed under it is refused.
    def validate(self):
        bot = self.bot
        if bot.parked or bank.is_open() or now_ms() < self.retry_at:
            return False
        offered = game.combat_styles()
        # The combat tab isn't loaded yet.
        if not offered:
            return False
        index = bot.combat_style_index
        return index >= len(offered) or game.combat_mode() != offered[index][0]

    def execute(self):
        bot = self.bot
        offered = game.combat_styles() or []
        index = bot.combat_style_index
        if index >= len(offered):
            listed = ', '.join([f'{i}={offered[i][1]}' for i in range(len(offered))])
            bot.park(f'combat style {index} does not exist for the wielded weapon — it offers {len(offered)}: {listed}. Pick one of those, then restart.')
            return
        mode, label = offered[index]
        bot.status = f'setting combat style {index} ({label})'
        game.set_combat_mode(mode)
        ok = yield from execution.delay_until(lambda: game.combat_mode() == mode, 3000)
        if not ok:
            self.retry_at = now_ms() + STYLE_RETRY_MS
            bot.log(f'could not select combat style {index} ({label}) — retrying in 60s')
            return
        if not self.announced:
            self.announced = True
            bot.log(f"combat style {index} = {label} (of {', '.join([l for _, l in offered])})")


class BankRun(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank run')
        self.bot = bot

    def validate(self):
        return bank.is_open() or bank_reason(self.bot) is not None

    def execute(self):
        yield from self.bot.bank_and_restock(bank_reason(self.bot) or 'prepare-trip')


class GoToField(Task):
    def __init__(self, bot):
        Task.__init__(self, label='go to field')
        self.bot = bot

    def validate(self):
        return not self.bot.in_field()

    def execute(self):
        yield from self.bot.go_to_field()


class Loot(Task):
    def __init__(self, bot):
        Task.__init__(self, label='loot')
        self.bot = bot

    def find(self):
        return ground_items.query().where(lambda g: is_chaos_druid_loot(g.name)).within(self.bot.spot.radius + 3).nearest()

    def validate(self):
        return not game.in_combat() and self.find() is not None

    def execute(self):
        bot = self.bot
        for _ in range(4):
            if game.in_combat():
                return
            drop = self.find()
            if drop is None:
                return
            merges = chaos_druid_drop_merges(drop.name, [i.name for i in inventory.items()])
            space = chaos_druid_loot_space_action(inventory.is_full(), bot.food_count(), skills.effective('hitpoints'), skills.level('hitpoints'), merges)
            if space == 'bank':
                return
            if space == 'eat-food':
                yield from eat_once(bot)
                continue
            if space == 'drop-food':
                yield from drop_one_food(bot)
                continue
            name = drop.name or ''
            before_used = inventory.used()
            before_count = inventory.count(name)
            bot.status = f'looting {name}'
            if not drop.interact('Take'):
                yield from execution.delay_ticks(2)
                return
            took = yield from execution.delay_until(lambda: inventory.used() > before_used or inventory.count(name) > before_count, 5000)
            if took:
                bot.looted += 1
                bot.log(f'picked up {name}')
            return


class Regroup(Task):
    def __init__(self, bot):
        Task.__init__(self, label='regroup')
        self.bot = bot

    def validate(self):
        bot = self.bot
        here = game.tile()
        return here is not None and bot.in_field() and bot.spot.field.distance_to(here) > min(5, bot.spot.radius)

    def execute(self):
        bot = self.bot
        bot.status = 'returning to the druid camp'
        yield from bot.walk_opening(bot.spot.field, min(4, bot.spot.radius - 1))


class Fight(Task):
    def __init__(self, bot):
        Task.__init__(self, label='fight')
        self.bot = bot

    def find_druid(self):
        spot = self.bot.spot
        return npcs.query().name(spot.npc).action('Attack').where(lambda n: not n.in_combat and n.tile().distance_to(spot.field) <= spot.radius).nearest()

    def target(self, index):
        for n in npcs.all():
            if n.index == index and n.name == self.bot.spot.npc:
                return n
        return None

    def validate(self):
        bot = self.bot
        return not game.in_combat() and bot.in_field() and bank_reason(bot) is None and self.find_druid() is not None

    def down(self):
        bot = self.bot
        bot.kills += 1
        bot.log(f'{bot.spot.npc} down')

    def execute(self):
        bot = self.bot
        druid = self.find_druid()
        if druid is None:
            return
        index = druid.index
        bot.status = f'attacking {bot.spot.npc} at {druid.tile()}'
        if not druid.interact('Attack'):
            yield from execution.delay_ticks(2)
            return
        engaged = yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 6000)
        if not engaged or chat_dialog.can_continue():
            return
        bot.status = f'fighting {bot.spot.npc}'
        deadline = now_ms() + FIGHT_MS
        reattacks = 0
        while now_ms() < deadline:
            if bot.died or chat_dialog.can_continue():
                return
            if bot.need_eat():
                yield from eat_once(bot)
            if bot.food_count() == 0 and skills.hp_fraction() <= bot.panic_hp_fraction:
                bot.log(f'out of food at {round(skills.hp_fraction() * 100)}% HP — breaking off to bank')
                return
            target = self.target(index)
            if target is None:
                self.down()
                return
            if target.health == 0 and target.max_health > 0:
                yield from execution.delay_until(lambda: self.target(index) is None, 10000)
                self.down()
                return
            if not game.in_combat() and not target.in_combat:
                if reattacks >= 2:
                    return
                reattacks += 1
                target.interact('Attack')
                yield from execution.delay_until(lambda: game.in_combat() or chat_dialog.can_continue(), 5000)
            yield from execution.delay_ticks(2)


class Wait(Task):
    def __init__(self, bot):
        Task.__init__(self, label='wait')
        self.bot = bot

    def validate(self):
        return True

    def execute(self):
        self.bot.status = 'fighting' if game.in_combat() else 'waiting for a druid or drop'
        yield from execution.delay_ticks(2)


class ChaosDruidKiller(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.trip_prepared = False
        self.parked = False
        self.died = False
        self.kills = 0
        self.looted = 0
        self.trips = 0
        self.deaths = 0
        self.food_sacrificed = 0
        self.ledge_fall_streak = 0
        self.status = 'starting'
        self.location_name = 'Edgeville Dungeon'
        self.spot = DRUID_SPOTS['Edgeville Dungeon']
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        location = s.str('location', 'Edgeville Dungeon')
        if location not in DRUID_SPOTS:
            self.park(f"unknown location '{location}' — pick one of: {', '.join(DRUID_LOCATION_NAMES)}")
            return
        self.location_name = location
        self.spot = DRUID_SPOTS[location]
        self.food_name = script_food(s, 'Lobster')
        self.food_withdraw = s.num('food_withdraw', 12)
        self.combat_style_index = int(s.str('combat_style_index', '1'))
        self.panic_hp_fraction = s.num('panic_hp', 35) / 100
        self.started_at = time.time()
        self.xp_at_start = sum([skills.xp(k) for k in COMBAT_SKILLS])
        starting_area = chaos_druid_area(game.tile(), self.spot.dungeon)
        self.last_area = starting_area
        self.trip_prepared = self.in_field() and self.food_count() >= self.food_withdraw
        f = self.spot.field
        self.log(f'ChaosDruidKiller starting — {self.location_name} ({self.spot.npc}), {self.food_withdraw} {self.food_name}, combat style {self.combat_style_index}, smart-eat, bank without food <{round(self.panic_hp_fraction * 100)}%, field {f.x},{f.z}')
        req = self.spot.requires
        if req is not None and skills.level(req[0]) < req[1]:
            self.park(f'{self.location_name} needs {req[1]} {req[0]} — you have {skills.level(req[0])}. Train it or pick another location, then restart.')
        if starting_area == 'other-underground':
            self.park(f'started in an underground map this route cannot exit. Reach the surface or the {self.location_name} field, then restart.')
        if self.location_name == 'Yanille Dungeon' and len([i for i in equipment.items() if len([w for w in SLASH_WEAPONS if w in (i.name or '').lower()]) > 0]) == 0:
            self.log('warning: no slash weapon wielded — the entrance web needs one (a carried knife is deposited every bank trip)')
        self.on('chat_message', self.heard)
        # SetCombatStyle comes before the walk, so a style the weapon doesn't have parks the bot at once rather than
        # after a trip out to the field.
        self.add(ContinueDialog(), Parked(self), LocationGuard(self), Eat(self), EvadeTowerSwarm(self), SetCombatStyle(self), BankRun(self),
                 GoToField(self), Loot(self), Regroup(self), Fight(self), Wait(self))

    def heard(self, e):
        t = (e.text or '').lower()
        if 'oh dear' in t and 'you are dead' in t:
            self.note_death('death message detected')

    def grind_targets(self):
        return [self.spot.npc]

    def recovery_anchor(self):
        return self.spot.field

    # Why: the guardian's evade walks inside the 5x9 room and never loses Swarm, so it's ignored only while inside,
    # for this bot to open the door first; outside, the usual evade runs.
    def ignored_randoms(self):
        return ['swarm'] if in_chaos_druid_tower(game.tile()) else []

    def in_field(self):
        return in_chaos_druid_field(game.tile(), self.spot)

    def inside_tower(self):
        return in_chaos_druid_tower(game.tile())

    def food_count(self):
        return food_count(inventory.items(), self.food_name)

    def need_eat(self):
        n = self.food_count()
        if n <= 0:
            return False
        return should_eat_to_use_food(skills.effective('hitpoints'), skills.level('hitpoints'), food_heal_amount(self.food_name), n)

    def selected_food(self):
        if bank.is_open():
            return None
        for item in inventory.items():
            if is_food_item(item.name, self.food_name):
                return item
        return None

    def observe_lifecycle(self):
        area = chaos_druid_area(game.tile(), self.spot.dungeon)
        if chaos_druid_respawned(self.last_area, area, self.trip_prepared):
            self.note_death('surface respawn detected after leaving the dungeon unexpectedly')
        if area != 'unknown':
            self.last_area = area

    def note_death(self, source):
        if not self.died:
            self.deaths += 1
        self.died = True
        self.trip_prepared = False
        self.status = 'died — restocking'
        self.log(f'{source} — will bank for a fresh trip before returning')

    def park(self, reason):
        if self.parked:
            return
        self.parked = True
        self.status = f'stopped — {reason}'
        self.log(f'STOPPED: {reason}')

    def arrived(self, dest, radius):
        here = game.tile()
        return here is not None and here.level == dest.level and dest.distance_to(here) <= radius

    def walk_opening(self, dest, radius):
        """Walks to dest, opening a gate or door in the way. Use with yield from."""
        for _ in range(12):
            if self.arrived(dest, radius):
                return True
            yield from traversal.walk_to(dest, radius=radius, timeout_ms=25000, log=lambda m: self.log(f'  {m}'))
            if self.arrived(dest, radius):
                return True
            obstacle = locs.query().name('Gate', 'Door', 'Large door').within(5).where(lambda l: open_op(l) is not None).nearest()
            if obstacle is None:
                yield from execution.delay_ticks(2)
                continue
            ot = obstacle.tile()
            self.log(f'opening {obstacle.name} at {ot}')
            obstacle.interact(open_op(obstacle))
            yield from execution.delay_until(lambda: not openable_at(ot), 4000)
        return self.arrived(dest, radius)

    def open_nearest_gate(self):
        """Use with yield from."""
        gate = locs.query().name('Gate').within(6).where(lambda l: open_op(l) is not None).nearest()
        if gate is None:
            return
        self.log(f'opening {gate.name} at {gate.tile()}')
        gate.interact(open_op(gate))
        yield from execution.delay_ticks(4)

    def cross_dungeon_gates(self, toward_field):
        """Use with yield from."""
        gates = [INTERMEDIATE_GATE, WILDERNESS_GATE] if toward_field else [WILDERNESS_GATE, INTERMEDIATE_GATE]
        for gate in gates:
            yield from traversal.walk_resilient(gate, radius=4, attempts=8, timeout_ms=25000, log=lambda m: self.log(f'  {m}'))
            yield from self.open_nearest_gate()

    def ascend_to_surface(self):
        """Use with yield from."""
        area = chaos_druid_area(game.tile(), self.spot.dungeon)
        if area == 'surface':
            return True
        if area != 'druid-dungeon':
            self.park('cannot use the Edgeville ladder from a different underground map. Reach the surface, then restart.')
            return False
        self.status = 'leaving the dungeon'
        yield from self.cross_dungeon_gates(False)
        reached = yield from self.walk_opening(LADDER_STAND, 2)
        if not reached:
            self.log('could not reach the Edgeville dungeon ladder')
            return False
        for _ in range(5):
            ladder = locs.query().name(LADDER_NAME).within(8).action(LADDER_OP).nearest()
            if ladder is None:
                yield from execution.delay_ticks(2)
                continue
            self.log(f'climbing out via {ladder.name} at {ladder.tile()}')
            ladder.interact(LADDER_OP)
            out = yield from execution.delay_until(lambda: not in_edgeville_dungeon(game.tile()), 8000)
            if out:
                self.trip_prepared = False
                return True
        return not in_edgeville_dungeon(game.tile())

    def descend_to_dungeon(self):
        """Use with yield from."""
        area = chaos_druid_area(game.tile(), self.spot.dungeon)
        if area == 'druid-dungeon':
            return True
        if area != 'surface':
            self.park('cannot reach the Edgeville trapdoor from a different underground map. Reach the surface, then restart.')
            return False
        self.status = 'walking to the Edgeville trapdoor'
        reached = yield from self.walk_opening(TRAPDOOR_STAND, 1)
        if not reached:
            self.log('could not reach the Edgeville trapdoor')
            return False
        for _ in range(7):
            trapdoor = locs.query().name(TRAPDOOR_NAME).within(6).nearest()
            if trapdoor is None:
                yield from execution.delay_ticks(2)
                continue
            downs = [a for a in trapdoor.actions() if 'climb-down' in a.lower()]
            action = downs[0] if len(downs) > 0 else open_op(trapdoor)
            if not action:
                yield from execution.delay_ticks(2)
                continue
            self.log(f'{action.lower()} {trapdoor.name} at {trapdoor.tile()}')
            trapdoor.interact(action)
            down = yield from execution.delay_until(lambda: in_edgeville_dungeon(game.tile()), 2500 if is_open_op(action) else 8000)
            if down:
                return True
        return in_edgeville_dungeon(game.tile())

    def eat_if_low(self):
        """Use with yield from."""
        if self.need_eat():
            yield from eat_once(self)

    def pick_tower_door(self):
        """The tower's door only yields to Pick Lock, and a success walks the player through. Use with yield from."""
        self.status = 'picking the tower door lock'
        for _ in range(20):
            if self.inside_tower():
                self.log('picked the tower lock — inside')
                return True
            yield from self.eat_if_low()
            door = locs.query().name(TOWER_DOOR_NAME).action(TOWER_DOOR_OP).within(5).nearest()
            if door is None:
                yield from execution.delay_ticks(2)
                continue
            mark = game_messages.mark()
            if not door.interact(TOWER_DOOR_OP):
                yield from execution.delay_ticks(2)
                continue

            def saw(*parts):
                return game_messages.saw_since(mark, lambda t: len([p for p in parts if p in t.lower()]) > 0)

            yield from execution.delay_until(lambda: self.inside_tower() or saw('fail to pick', 'trap on the lock', 'need level', 'members'), 8000)
            if game_messages.saw_since(mark, lambda t: 'need level' in t.lower() and 'thieving' in t.lower()):
                self.park('the server refused the picklock (needs 46 Thieving). Train Thieving, then restart.')
                return False
            if saw('members'):
                self.park('the tower door is members-only on this world.')
                return False
            if saw('trap on the lock'):
                self.log('lock trap triggered — took damage, trying again')
            elif saw('fail to pick the lock'):
                self.log('picklock failed — trying again')
        self.log('could not pick the tower lock after 20 tries — will retry')
        return self.inside_tower()

    def tower_to_field(self):
        """Use with yield from."""
        if self.inside_tower():
            self.died = False
            return True
        self.status = 'walking to the Chaos Druid Tower'
        reached = yield from self.walk_opening(TOWER_DOOR_STAND, 1)
        if not reached:
            self.log('could not reach the tower door')
            return False
        picked = yield from self.pick_tower_door()
        return picked

    def walk_exact(self, dest):
        """Use with yield from."""
        def here():
            t = game.tile()
            return t is not None and t.x == dest.x and t.z == dest.z and t.level == dest.level

        for _ in range(4):
            if here():
                break
            yield from traversal.walk_resilient(dest, radius=0, attempts=6, timeout_ms=25000, log=lambda m: self.log(f'  {m}'))
        return here()

    def zone(self):
        t = game.tile()
        return 'unknown' if t is None else yanille_zone(t)

    def cross_ledge(self, direction):
        """Crosses the balancing ledge. A fail drops into the m40_149 pit for a fifth of current HP; the walker knows
        the pit's stairs, so recovering is a plain walk. Use with yield from."""
        stand = LEDGE_NORTH_STAND if direction == 'south' else LEDGE_SOUTH_STAND
        self.status = 'crossing the balancing ledge'
        yield from self.eat_if_low()
        stood = yield from self.walk_exact(stand)
        if not stood:
            yield from execution.delay_ticks(2)
            return False
        ledge = locs.query().name(LEDGE_NAME).action(LEDGE_OP).within(4).nearest()
        if ledge is None or not ledge.interact(LEDGE_OP):
            yield from execution.delay_ticks(2)
            return False
        far_zone = 'warrior' if direction == 'south' else 'north'
        yield from execution.delay_until(lambda: self.zone() == far_zone or self.zone() == 'pit', 15000)
        if self.zone() == far_zone:
            self.ledge_fall_streak = 0
            self.log('crossed the balancing ledge')
            return True
        if self.zone() == 'pit':
            self.ledge_fall_streak += 1
            self.log(f'slipped off the ledge into the pit (fall {self.ledge_fall_streak}) — recovering via the pit stairs')
            if self.ledge_fall_streak >= MAX_LEDGE_FALL_STREAK:
                self.park(f'fell off the balancing ledge {MAX_LEDGE_FALL_STREAK} times in a row — is Agility high enough for this route?')
        return False

    def yanille_to_field(self):
        """Use with yield from."""
        for _ in range(10):
            if self.parked:
                break
            here = game.tile()
            if here is None:
                return False
            if self.in_field():
                self.died = False
                return True
            yield from self.eat_if_low()
            if chaos_druid_area(here, self.spot.dungeon) == 'other-underground':
                self.park('cannot route to Yanille from a different underground map. Reach the surface, then restart.')
                return False
            zone = yanille_zone(here)
            if zone == 'warrior':
                self.status = 'walking to the Chaos druid warriors'
                walked = yield from traversal.walk_resilient(self.spot.field, radius=4, attempts=8, timeout_ms=25000, log=lambda m: self.log(f'  {m}'))
                if walked:
                    self.died = False
                    return True
                continue
            if zone == 'north':
                yield from self.cross_ledge('south')
                continue
            # On the surface or in the pit: the walker knows the entrance's web and stairs and the pit's stairs.
            self.status = 'climbing out of the ledge pit' if zone == 'pit' else 'walking to the Yanille dungeon'
            yield from traversal.walk_resilient(LEDGE_NORTH_STAND, radius=1, attempts=8, timeout_ms=60000, log=lambda m: self.log(f'  {m}'))
        return False

    def leave_field_for_bank(self):
        """Gets to ground the web walker can plan a bank route from. Use with yield from."""
        if self.location_name == 'Edgeville Dungeon':
            up = yield from self.ascend_to_surface()
            return up
        if self.location_name == 'Yanille Dungeon':
            # Surfacing on purpose: otherwise the jump from the dungeon to the surface reads as a missed death.
            self.trip_prepared = False
            self.status = 'leaving the Yanille dungeon'
            for _ in range(10):
                if self.parked:
                    break
                here = game.tile()
                if here is None:
                    return False
                if yanille_zone(here) != 'warrior':
                    return True
                yield from self.cross_ledge('north')
            return False
        return True

    def bank_and_restock(self, reason):
        """Use with yield from."""
        # Each reason has one hyphen.
        why = reason.replace('-', ' ')
        self.status = f'banking — {why}'
        self.log(f'trip ended ({why}) — preparing the next trip')
        stand = self.spot.bank_stand
        if bank.is_open():
            self.trip_prepared = False
            self.log('bank was already open — resuming the interrupted restock')
        else:
            left = yield from self.leave_field_for_bank()
            if not left:
                return False
            reached = yield from self.walk_opening(stand, 2)
            if not reached:
                self.log('could not reach the bank')
                return False
            opened = yield from bank.open_booth(stand, BOOTH_NAME, BOOTH_OP)
            if not opened:
                self.log('could not open the bank')
                return False
        self.status = 'banking loot'
        # Why: equipment isn't in the pack, so depositing the pack banks the haul and leaves a clean slate for the
        # withdraw: every trip starts the same, with nothing left over above the configured amount.
        yield from bank.deposit_inventory()
        yield from execution.delay_ticks(1)
        shortfall = chaos_druid_food_shortfall(self.food_withdraw, 0)
        if shortfall > 0:
            yield from execution.delay_until(bank.loaded, 4000)
            available = bank.count(self.food_name)
            if available < shortfall:
                yield from bank.close()
                self.park(f'configured for {self.food_withdraw} {self.food_name}, but only {available} are in the bank. Add food, then restart.')
                return False
            self.status = f'withdrawing {shortfall} {self.food_name}'
            took = yield from bank.withdraw_x(self.food_name, shortfall)
            if not took:
                yield from bank.close()
                self.log(f'withdraw of {shortfall} {self.food_name} did not complete — will retry')
                return False
        closed = yield from bank.close()
        if not closed:
            self.log('bank did not close cleanly — will retry before walking')
            return False
        if self.food_count() < self.food_withdraw:
            self.park(f'restock verification failed: expected {self.food_withdraw} {self.food_name}, found {self.food_count()}. Add food, then restart.')
            return False
        self.trip_prepared = True
        self.died = False
        self.trips += 1
        self.log(f'banked the haul and restocked exactly {self.food_count()} {self.food_name}')
        return True

    def go_to_field(self):
        """Use with yield from."""
        if self.location_name == 'Chaos Druid Tower':
            there = yield from self.tower_to_field()
            return there
        if self.location_name == 'Yanille Dungeon':
            there = yield from self.yanille_to_field()
            return there
        if chaos_druid_area(game.tile(), self.spot.dungeon) == 'other-underground':
            self.park('cannot route to Edgeville from a different underground map. Reach the surface, then restart.')
            return False
        if not in_edgeville_dungeon(game.tile()):
            down = yield from self.descend_to_dungeon()
            if not down:
                return False
        self.status = 'walking to the Chaos druids'
        yield from self.cross_dungeon_gates(True)
        arrived = yield from traversal.walk_resilient(self.spot.field, radius=4, attempts=8, timeout_ms=25000, log=lambda m: self.log(f'  {m}'))
        if arrived:
            self.died = False
            self.log(f'arrived at the Chaos-druid field ({self.spot.field.x},{self.spot.field.z})')
        else:
            self.log('could not reach the Chaos-druid field — will retry')
        return arrived

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        gained = sum([skills.xp(k) for k in COMBAT_SKILLS]) - self.xp_at_start
        report = {'Status': self.status, 'Location': self.location_name, 'Kills': self.kills, 'Combat xp': gained,
                  'XP/hr': f'{gained / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—', 'Looted': self.looted, 'Food': self.food_count(), 'Banks': self.trips}
        if self.food_sacrificed > 0 or self.deaths > 0:
            report['Food used for space'] = self.food_sacrificed
            report['Deaths'] = self.deaths
        return report


BOT = define_bot(
    name='ChaosDruidKiller',
    create=ChaosDruidKiller,
    description='Kills Chaos druids — Edgeville dungeon, the picklocked Chaos Druid Tower (46 Thieving), or Yanille dungeon Chaos druid warriors past the 40 Agility ledge — loots Herb/Law/Nature rune drops, banks them',
    category='Combat',
    tags=['wilderness', 'edgeville', 'ardougne', 'yanille', 'herbs', 'banking'],
    settings_schema=SETTINGS,
)

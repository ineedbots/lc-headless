# The Brimhaven Agility Arena: banks food and coins at Ardougne south, takes the ship to Brimhaven, pays Cap'n
# Izzy, chases the ticket pillar the hint arrow points at along the shortest path its level allows, and waits at the
# centre between tags: rs2b0t's BrimhavenAgility (MIT, see thirdparty/rs2b0t). Steal restock (Thieving 20) takes
# cakes from Ardougne's Baker's stall, and coins from its guards at 40.

import math
import time

from rs2004.catalogs import CAKE_ITEMS, FLEE_TILE, LOADOUT_SETTING, STUN_COMBAT_TICKS, ContinueDialog, carried_cakes, food_count, food_forms
from rs2004.catalogs import matches_any, script_food, steal_cakes, target_spot

BOAT_FARE = 30
ENTRANCE_FEE = 200
DEFAULT_FOOD_PER_TRIP = 25
DEFAULT_BANK_TICKETS = 1000
EAT_AT_HP = 5
TICKET_NAME = 'Agility arena ticket'
ARENA_VARP = 309
PAID_BIT = 1
PILLAR_TAGGED_BIT = 0
STEAL_THIEVING_MIN = 20
GUARD_THIEVING_MIN = 40
CAKE_GUARD_BUFFER = 4
OBSTACLE_APPROACH_RADIUS = 3
CENTRE_PLATFORM = 12
TICKET_PILLAR_COUNT = 24
PILLAR_CYCLE_TICKS = 98
TICKET_CAP_PER_HOUR = 3600000 // (PILLAR_CYCLE_TICKS * 600)
ARDY_BANK = Tile(2655, 3283, 0)
ARENA_ENTRANCE = Tile(2809, 3194, 0)
LADDER_DOWN_STAND = Tile(2809, 3194, 0)
KARAMJA_GENERAL = Tile(2902, 3146, 0)
# Why: indices 0-23 are the server's ticket pillars, and 24 is the south-east landing Climb-down drops you on, which
# has no dispenser.
PILLARS = []
for _z in [9546, 9557, 9568, 9579, 9590]:
    for _x in [2761, 2772, 2783, 2794, 2805]:
        PILLARS.append((_x, _z))

SETTINGS = {
    'loadout': LOADOUT_SETTING,
    'food_withdraw': SettingDef('number', DEFAULT_FOOD_PER_TRIP, 'Food per trip', 1, 27, help='default 25 leaves one slot for the coin stack (26 used)'),
    'bank_at_tickets': SettingDef('number', DEFAULT_BANK_TICKETS, 'Bank at X tickets', 1, 5000, help='also banks when out of food'),
    'steal_restock': SettingDef('boolean', False, 'Steal cakes / GP when out',
                                help="Thieving 20: Baker's stall cakes when the selected food is gone. Thieving 40: pickpocket Ardougne guards for boat/entrance coins, eating cakes after stuns"),
}


class Edge:
    def __init__(self, a, b, kind, min_level, mode, loc_name=None, op=None):
        self.a = a
        self.b = b
        self.kind = kind
        self.min_level = min_level
        # 'interact' with the loc, or 'walk' across a trap.
        self.mode = mode
        self.loc_name = loc_name
        self.op = op


def _ledge(a, b):
    return Edge(a, b, 'ledge', 1, 'interact', 'Balancing ledge', 'Walk-across')


def _pillar(a, b):
    return Edge(a, b, 'pillar', 1, 'interact', 'Pillar', 'Jump-on')


def _monkey(a, b):
    return Edge(a, b, 'monkey', 1, 'interact', 'Monkey bars', 'Swing-across')


def _handholds(a, b):
    return Edge(a, b, 'handholds', 20, 'interact', 'Hand holds', 'Climb-across')


def _rope(a, b):
    return Edge(a, b, 'rope', 1, 'interact', 'Balancing rope', 'Walk-on')


def _log(a, b):
    return Edge(a, b, 'log', 1, 'interact', 'Log balance', 'Walk-on')


def _plank(a, b):
    return Edge(a, b, 'plank', 1, 'interact', 'Plank', 'Walk-on')


def _wall(a, b):
    return Edge(a, b, 'wall', 1, 'interact', 'Low wall', 'Climb-over')


def _swing(a, b):
    return Edge(a, b, 'swing', 1, 'interact', 'Rope swing', 'Swing-on')


def _trap(a, b, kind, level):
    return Edge(a, b, kind, level, 'walk')


ARENA_EDGES = [
    _ledge(0, 1), _pillar(0, 5), _monkey(1, 2), _trap(1, 6, 'spikes', 20), _handholds(2, 3), _trap(2, 7, 'blade', 1), _ledge(3, 4), _rope(3, 8),
    _log(4, 9), _plank(5, 6), _handholds(5, 10), _trap(6, 7, 'saws', 40), _rope(6, 11), _wall(7, 12), _trap(8, 9, 'pressure', 20), _monkey(8, 13),
    _wall(9, 14), _swing(10, 11), _trap(10, 15, 'spikes', 20), _monkey(11, 16), _pillar(12, 13), _trap(12, 17, 'saws', 40), _trap(13, 14, 'spikes', 20),
    _trap(13, 18, 'darts', 40), _pillar(14, 19), _log(15, 16), _trap(15, 20, 'blade', 1), _trap(16, 17, 'saws', 40), _trap(16, 21, 'pressure', 20),
    _trap(17, 18, 'blade', 1), _rope(17, 22), _trap(18, 19, 'pressure', 20), _log(18, 23), _ledge(20, 21), _wall(21, 22), _handholds(22, 23),
    _swing(24, 19), _plank(24, 23),
]


# The pure decisions, kept apart from the game so they can be tested without a client.

# Why: on this footprint the outbound boat is paid, so only the return fare and an unpaid entrance remain; charging
# both legs here funds them again and loops the bot between the bank and the boat.
def on_brimhaven_surface(x, z, level):
    """Karamja's surface around Brimhaven, from the ship's landing to the arena's entrance."""
    return level == 0 and x >= 2740 and x <= 2960 and z >= 3130 and z <= 3280


def sign(n):
    return 1 if n > 0 else (-1 if n < 0 else 0)


def obstacle_axis(source, dest):
    """The cardinal direction from one platform to the next, or None for a pair that isn't."""
    a = PILLARS[source]
    b = PILLARS[dest]
    dx = sign(b[0] - a[0])
    dz = sign(b[1] - a[1])
    # The arena's edges are cardinal; a diagonal or the same tile is refused, so a stand never lands on an
    # arbitrary side of an obstacle.
    if (dx == 0) == (dz == 0):
        return None
    return (dx, dz)


# Why: the server's obstacle scripts key off these directional start tiles, not any tile on the same platform.
def edge_approach_point(source, dest, loc):
    """The ideal stand: two tiles from the loc, toward the source platform."""
    axis = obstacle_axis(source, dest)
    if axis is None:
        return None
    return (loc.x - axis[0] * 2, loc.z - axis[1] * 2)


def approach_key(offset, axis):
    ox, oz = offset
    axial = ox * axis[0] + oz * axis[1]
    lateral = ox * -axis[1] + oz * axis[0]
    return (max(abs(ox), abs(oz)), abs(axial), lateral, axial, ox, oz)


# Why: candidates stay within three tiles of the ideal stand, on the source platform, strictly on the loc's source
# side. The ideal comes first, and at the same radius moving sideways comes before moving along the obstacle.
def edge_approach_candidates(source, dest, loc, radius=3):
    """Stands to try, in order, for a live reachability filter: (x, z) pairs."""
    axis = obstacle_axis(source, dest)
    ideal = edge_approach_point(source, dest, loc)
    if axis is None or ideal is None:
        return []
    r = max(0, min(OBSTACLE_APPROACH_RADIUS, math.floor(radius)))
    offsets = []
    for ox in range(-r, r + 1):
        for oz in range(-r, r + 1):
            offsets.append((ox, oz))
    offsets.sort(key=lambda o: approach_key(o, axis))
    out = []
    for ox, oz in offsets:
        x = ideal[0] + ox
        z = ideal[1] + oz
        source_side = (x - loc.x) * axis[0] + (z - loc.z) * axis[1] < 0
        if source_side and platform_at(x, z) == source:
            out.append((x, z))
    return out


def hint_missed(prev_hint, next_hint, tagged_this_hint):
    """A hint that moves on before the last pillar was tagged is a missed ticket, and breaks the streak."""
    return prev_hint >= 0 and next_hint >= 0 and next_hint != prev_hint and not tagged_this_hint


def needs_food_sale_for_boat(coins, food, at_brimhaven):
    """The return ship can't be paid, but there's food to sell."""
    return at_brimhaven and coins < BOAT_FARE and food > 0


def stranded_without_boat_fare(coins, food, at_brimhaven):
    """The return ship can't be paid, and there's nothing to sell."""
    return at_brimhaven and coins < BOAT_FARE and food <= 0


def has_paid(varp):
    return (varp >> PAID_BIT) & 1 == 1


def pillar_tagged(varp):
    return (varp >> PILLAR_TAGGED_BIT) & 1 == 1


# Why: from Ardougne both boat legs and an unpaid entrance are owed; on Brimhaven the outbound boat is spent. Without
# the split, the 230gp left after the 30gp ship read as short of 260 and the bot banked instead of going in.
def coins_needed(already_paid, outbound_boat_done=False):
    """The coins the rest of the trip needs."""
    boats = BOAT_FARE * (1 if outbound_boat_done else 2)
    return boats if already_paid else boats + ENTRANCE_FEE


def coins_to_withdraw(already_paid, coins_in_pack):
    """What to withdraw at Ardougne, for a full round trip from the mainland."""
    return max(0, coins_needed(already_paid, False) - coins_in_pack)


def should_bank(tickets, food, bank_at_tickets, steal_restock):
    if tickets >= bank_at_tickets:
        return True
    if steal_restock:
        return False
    return food <= 0


def steal_reserve_slots(coins, tickets):
    """The slots the stall leaves empty, so a new coin stack and the first ticket can land."""
    return (1 if coins <= 0 else 0) + (1 if tickets <= 0 else 0)


def needs_cake_steal(selected_food, cakes, steal_restock, need_coins, free_slots):
    """It steals while the pack has room: the stall's cakes, breads and slices don't stack."""
    if not steal_restock or free_slots <= 0:
        return False
    if selected_food <= 0:
        return True
    return need_coins and cakes < CAKE_GUARD_BUFFER


def should_leave_for_steal(steal_restock, inside, edible, need_coins):
    """It leaves the arena to steal only with nothing left to eat, or no coins for the next trip."""
    return steal_restock and inside and (edible <= 0 or need_coins)


def ticket_inventory_gain(e, bank_open):
    """The tickets an inventory change brought into the pack, outside the bank."""
    if bank_open or e.id == -1 or e.name != TICKET_NAME:
        return 0
    return max(1, e.count) if e.previous_id != e.id else max(0, e.count - e.previous_count)


# Why: these shortfalls trigger the bank trip, so one still missing after it sends the next loop straight back, and
# the caller stops on one rather than opening and shutting the bank when the account ran out.
def restock_shortfall(food, food_in_pack, food_per_trip, coins, already_paid):
    """What the bank couldn't supply, or None when the trip is funded."""
    if food_in_pack < food_per_trip:
        return f'out of {food} — only {food_in_pack} in the pack after restocking, need {food_per_trip} per trip. Bank more {food} (or lower "Food per trip") and restart.'
    need = coins_needed(already_paid, False)
    if coins < need:
        entrance = '' if already_paid else ' + arena entrance'
        return f'out of coins — only {coins} after restocking, need {need} for the boats{entrance}. Bank more coins and restart.'
    return None


def needs_coins_restock(coins, already_paid, at_brimhaven):
    return coins < coins_needed(already_paid, at_brimhaven)


def should_eat(hp, food):
    return hp > 0 and hp < EAT_AT_HP and food > 0


def platform_at(x, z, max_dist=6):
    """The nearest platform to a tile, or -1 away from the arena's grid."""
    best = -1
    best_d = max_dist + 1
    for i in range(len(PILLARS)):
        px, pz = PILLARS[i]
        d = max(abs(px - x), abs(pz - z))
        if d < best_d:
            best_d = d
            best = i
    return best


def pillar_from_hint(hx, hz):
    """The ticket pillar (0-23) a hint arrow's tile is on, never the landing."""
    p = platform_at(hx, hz, 3)
    return p if p >= 0 and p < TICKET_PILLAR_COUNT else -1


# Why: the arena is all of the m43_149 map square, which keeps other floors and dungeons from matching on z alone.
def in_arena(x, z):
    return x >= 2752 and x <= 2815 and z >= 9536 and z <= 9599


def on_arena_platform(level):
    """On the ticket platforms (plane 3), not the pit below."""
    return level >= 3


# Why: a failed obstacle drops the player to plane 0 under the same x and z; the pillars still match there, but the
# edges' locs exist only on plane 3, so it climbs the rope before pathing.
def in_arena_pit(x, z, level):
    return in_arena(x, z) and level < 3


# Why: 'fallen' is the pit, so the rope comes next; 'arrived' is the destination, where leftover animation is fine
# since the next hop can queue; 'elsewhere' left for another platform, which is progress; 'pending' is mid-attempt.
def obstacle_outcome(platform, source, dest, pit):
    if pit:
        return 'fallen'
    if platform == dest:
        return 'arrived'
    if platform >= 0 and platform != source:
        return 'elsewhere'
    return 'pending'


def hop_kind_cost(kind):
    """Lower is faster: monkey bars and handholds are long animations, the traps a one-tick dive."""
    if kind in ['saws', 'spikes', 'pressure', 'darts']:
        return 0
    if kind in ['wall', 'pillar']:
        return 1
    if kind in ['ledge', 'log']:
        return 2
    if kind in ['monkey', 'handholds']:
        return 4
    if kind == 'plank':
        return 5
    if kind == 'blade':
        return 9
    return 3


def platform_geo_dist(a, b):
    pa = PILLARS[a]
    pb = PILLARS[b]
    return abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])


def usable_edges(agility):
    return [e for e in ARENA_EDGES if agility >= e.min_level]


# Why: the blades knock you back on a 7-tick cycle, a stall rather than a hop; a random grid plank breaks into the
# pit with no roll, and from 20 the spikes and handholds replace it, though the landing still needs 24-23. The darts
# drain current agility and always fail below 40, so taking them as a cheap hop is a loop to ruin.
def pathing_edge(e, agility):
    if e.a == 24 or e.b == 24:
        return True
    if e.kind == 'blade' or e.kind == 'darts':
        return False
    return not (e.kind == 'plank' and agility >= 20)


def pathing_edges(agility):
    return [e for e in usable_edges(agility) if pathing_edge(e, agility)]


def arena_adj(agility):
    adj = {}
    for e in pathing_edges(agility):
        for one, other in [(e.a, e.b), (e.b, e.a)]:
            if one not in adj:
                adj[one] = []
            adj[one].append(other)
    return adj


def hop_dist_from(src, adj):
    """Hops from src to every platform it reaches."""
    dist = {src: 0}
    queue = [src]
    while len(queue) > 0:
        cur = queue.pop(0)
        for n in adj.get(cur, []):
            if n in dist:
                continue
            dist[n] = dist[cur] + 1
            queue.append(n)
    return dist


def edge_between(a, b, agility):
    lo = min(a, b)
    hi = max(a, b)
    for e in usable_edges(agility):
        if min(e.a, e.b) == lo and max(e.a, e.b) == hi:
            return e
    return None


def hop_key(cur, n, goal, agility):
    edge = edge_between(cur, n, agility)
    return (platform_geo_dist(n, goal), hop_kind_cost(edge.kind if edge is not None else None), n)


# Why: among routes of the same hops each step takes the neighbour nearer the goal, so the search's order can't send
# it the long way round.
def path_platforms(source, goal, agility):
    """The shortest path of platforms from source to goal, or None."""
    if source < 0 or goal < 0 or source >= len(PILLARS) or goal >= len(PILLARS):
        return None
    if source == goal:
        return []
    adj = arena_adj(agility)
    rem = hop_dist_from(goal, adj)
    if source not in rem:
        return None
    path = []
    cur = source
    for _ in range(rem[source]):
        need = rem[cur] - 1
        opts = [n for n in adj.get(cur, []) if rem.get(n) == need]
        if len(opts) == 0:
            return None
        here = cur
        opts.sort(key=lambda n: hop_key(here, n, goal, agility))
        cur = opts[0]
        path.append(cur)
    return path


def next_hop(source, goal, agility, avoid=-1):
    """The next platform toward goal, or None when stuck or there."""
    path = path_platforms(source, goal, agility)
    if path is None or len(path) == 0:
        return None
    first = path[0]
    if first != avoid:
        return first
    rem = hop_dist_from(goal, arena_adj(agility))
    need = rem.get(source, 0) - 1
    # Why: the usable edges still list the darts and blades, and taking them after a fall is the drain loop.
    for e in pathing_edges(agility):
        n = e.b if e.a == source else (e.a if e.b == source else -1)
        if n >= 0 and n != avoid and rem.get(n) == need:
            return n
    return first


def walk_trap_stand(source, dest):
    """The trap's trigger on the source side, five tiles toward dest; a click on the far island paths round the loc
    and into the pit."""
    a = PILLARS[source]
    b = PILLARS[dest]
    return (a[0] + sign(b[0] - a[0]) * 5, a[1] + sign(b[1] - a[1]) * 5)


def on_ticket_hub(platform):
    """The centre and the two spike islands, from where the next random pillar is a short chase."""
    return platform == CENTRE_PLATFORM or platform == 13 or platform == 14


def now_ms():
    return time.time() * 1000


def find_edible(food):
    forms = food_forms(food)
    for i in inventory.items():
        if (i.name or '').lower() in forms:
            return i
    for i in inventory.items():
        if matches_any(i.name, CAKE_ITEMS):
            return i
    return None


def first_op(loc, part):
    for a in loc.actions():
        if part in a.lower():
            return a
    return None


def flee(bot):
    """Use with yield from."""
    yield from traversal.walk_resilient(FLEE_TILE, radius=2, attempts=2, timeout_ms=20000, log=lambda m: bot.log(f'  {m}'))


class LeaveForSteal(Task):
    def __init__(self, bot):
        Task.__init__(self, label='leave for steal')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return should_leave_for_steal(bot.steal_restock, bot.in_arena_now(), bot.edible_in_pack(), bot.needs_coins_now())

    def execute(self):
        self.bot.status = 'leaving arena to steal restock'
        yield from leave_arena(self.bot)


class SellFoodForBoat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='sell food for boat')
        self.bot = bot

    def validate(self):
        return self.bot.needs_food_sale_for_boat_now() and not self.bot.in_arena_now()

    def stop(self, msg):
        self.bot.status = f'stopped — {msg}'
        self.bot.request_finish(msg)

    def execute(self):
        bot = self.bot
        bot.status = 'selling food at the Karamja General Store'
        arrived = yield from traversal.walk_resilient(KARAMJA_GENERAL, radius=3, attempts=4, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('could not reach the Karamja General Store')
            return
        opened = yield from shop.open('Shop keeper')
        if not opened:
            opened = yield from shop.open('Shop assistant')
        if not opened:
            bot.log('could not open the Karamja General Store')
            return
        for _ in range(28):
            if bot.coin_count() >= BOAT_FARE:
                break
            item = find_edible(bot.food_name)
            if item is None or not item.name:
                break
            before = bot.coin_count()
            sold = yield from shop.sell(item.name, 1)
            if sold <= 0 or bot.coin_count() <= before:
                yield from shop.close()
                self.stop(f'Karamja store did not buy {item.name} — still {bot.coin_count()} coins, need {BOAT_FARE} for the Ardougne ship')
                return
            bot.log(f'sold {item.name} ({bot.coin_count()} coins)')
        yield from shop.close()
        if stranded_without_boat_fare(bot.coin_count(), bot.edible_in_pack(), True):
            self.stop(f'sold food but only have {bot.coin_count()} coins — need {BOAT_FARE} for the Ardougne ship')


class StealFood(Task):
    def __init__(self, bot):
        Task.__init__(self, label='steal food')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.needs_cakes_now() and not bot.in_arena_now() and not bot.needs_food_sale_for_boat_now()

    def execute(self):
        bot = self.bot
        if game.in_combat():
            bot.status = 'kiting the stall guard'
            yield from flee(bot)
            yield from execution.delay_until(lambda: not game.in_combat(), 15000)
            return
        bot.status = "stealing cakes at the Baker's stall"
        result = yield from steal_cakes(lambda: not bot.needs_cakes_now(), bot.set_status, lambda m: bot.log(f'  {m}'),
                                        should_eat=lambda: should_eat(bot.hp(), bot.edible_in_pack()))
        if result == 'combat':
            bot.status = 'caught at the stall — kiting'
            yield from flee(bot)


class StealCoins(Task):
    def __init__(self, bot):
        Task.__init__(self, label='steal coins')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return bot.steal_restock and bot.needs_coins_now() and not bot.in_arena_now() and not bot.needs_cakes_now() and not bot.needs_food_sale_for_boat_now()

    def lull(self):
        bot = self.bot
        return not bot.stunned() or should_eat(bot.hp(), bot.edible_in_pack())

    def execute(self):
        bot = self.bot
        thieving = skills.level('thieving')
        if thieving < GUARD_THIEVING_MIN:
            msg = f'stealing coins from guards needs Thieving {GUARD_THIEVING_MIN} (have {thieving})'
            bot.log(msg)
            bot.request_finish(msg)
            return
        if should_eat(bot.hp(), bot.edible_in_pack()):
            return
        if bot.stunned():
            bot.status = 'stunned — waiting'
            yield from execution.delay_until(self.lull, 9000)
            return
        if game.in_combat():
            bot.status = 'kiting the guard'
            yield from flee(bot)
            yield from execution.delay_until(lambda: not game.in_combat(), 15000)
            return
        spot = target_spot('Guard')
        here = game.tile()
        if here is not None and spot.anchor.distance_to(here) > spot.leash:
            bot.status = 'walking to Ardougne guards'
            yield from traversal.walk_resilient(spot.anchor, radius=4, attempts=3, timeout_ms=90000, log=lambda m: bot.log(f'  {m}'))
            return
        guard = npcs.query().name('Guard').action('Pickpocket').where(lambda n: n.tile().distance_to(spot.anchor) <= spot.leash).nearest()
        if guard is None:
            bot.status = 'no guard in range — waiting'
            yield from execution.delay_ticks(2)
            return
        if not reachability.can_reach(guard.tile(), adjacent_ok=True):
            yield from traversal.walk_resilient(guard.tile(), radius=1, attempts=2, timeout_ms=20000, log=lambda m: bot.log(f'  {m}'))
            return
        bot.status = 'pickpocketing a guard'
        coins_before = bot.coin_count()
        xp_before = skills.xp('thieving')
        guard.interact('Pickpocket')
        yield from execution.delay_until(lambda: bot.coin_count() > coins_before or skills.xp('thieving') > xp_before or bot.stunned() or chat_dialog.can_continue(), 2500)
        if bot.coin_count() > coins_before:
            bot.log(f'pickpocketed a guard ({bot.coin_count()} coins)')
        if bot.stunned():
            yield from execution.delay_until(self.lull, 9000)


class Eat(Task):
    def __init__(self, bot):
        Task.__init__(self, label='eat')
        self.bot = bot

    def validate(self):
        return should_eat(self.bot.hp(), self.bot.edible_in_pack())

    def execute(self):
        bot = self.bot
        item = find_edible(bot.food_name)
        if item is None:
            return
        bot.status = f'eating {item.name} ({bot.hp()} hp)'
        before = inventory.used()
        item.interact('Eat')
        yield from execution.delay_until(lambda: inventory.used() < before or bot.hp() >= EAT_AT_HP, 3000)


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.needs_food_sale_for_boat_now():
            return False
        due = should_bank(bot.ticket_count(), bot.food_in_pack(), bot.bank_at_tickets, bot.steal_restock)
        if bot.in_arena_now() or due:
            return due
        if bot.steal_restock:
            return False
        at_brim = bot.at_brimhaven_now()
        # On Brimhaven it doesn't top the food up to a full trip, which alone would ship it back after one lobster.
        need_food = bot.food_in_pack() <= 0 or (not at_brim and bot.food_in_pack() < bot.food_per_trip)
        return need_food or needs_coins_restock(bot.coin_count(), bot.paid(), at_brim)

    def execute(self):
        bot = self.bot
        food = bot.food_name
        if bot.in_arena_now():
            bot.status = 'leaving arena to bank'
            yield from leave_arena(bot)
            return
        bot.status = 'banking at Ardougne south'
        arrived = yield from traversal.walk_resilient(ARDY_BANK, radius=3, attempts=3, timeout_ms=180000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('could not reach Ardougne south bank')
            return
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            bot.log('could not open the bank')
            return
        keep = ['coins'] + food_forms(food) + ([c.lower() for c in CAKE_ITEMS] if bot.steal_restock else [])
        yield from bank.deposit_all_matching(lambda name, *_args: name.lower() not in keep)
        # A full round trip from the mainland, always.
        coins = coins_to_withdraw(bot.paid(), bot.coin_count())
        if coins > 0:
            yield from bank.withdraw_x('Coins', coins)
        have = bot.food_in_pack()
        if have < bot.food_per_trip:
            yield from bank.withdraw_x(food, bot.food_per_trip - have)
        shortfall = restock_shortfall(food, bot.food_in_pack(), bot.food_per_trip, bot.coin_count(), bot.paid())
        yield from bank.close()
        if shortfall is not None:
            if bot.steal_restock:
                bot.log(f'bank shortfall ({shortfall}) — steal restock will cover food/coins')
            else:
                bot.status = f'stopped — {shortfall}'
                bot.request_finish(shortfall)
                return
        bot.log(f'restocked: {bot.food_in_pack()} {food}, {bot.coin_count()} coins, {bot.ticket_count()} tickets banked (threshold {bot.bank_at_tickets})')


class TravelToArena(Task):
    def __init__(self, bot):
        Task.__init__(self, label='travel to arena')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.in_arena_now() or should_bank(bot.ticket_count(), bot.food_in_pack(), bot.bank_at_tickets, bot.steal_restock):
            return False
        if bot.needs_cakes_now() or (bot.steal_restock and bot.needs_coins_now()):
            return False
        here = game.tile()
        if here is None:
            return False
        # The food and coins the legs left still need, not a full trip when already on Brimhaven.
        if bot.edible_in_pack() < 1 or needs_coins_restock(bot.coin_count(), bot.paid(), on_brimhaven_surface(here.x, here.z, here.level)):
            return False
        return not (here.level == 0 and max(abs(here.x - ARENA_ENTRANCE.x), abs(here.z - ARENA_ENTRANCE.z)) <= 8)

    def execute(self):
        bot = self.bot
        bot.status = 'walking to Brimhaven arena'
        # The web walker takes the ship between Ardougne and Brimhaven when it's needed.
        arrived = yield from traversal.walk_resilient(ARENA_ENTRANCE, radius=4, attempts=4, timeout_ms=300000, log=lambda m: bot.log(f'  {m}'))
        if not arrived:
            bot.log('could not reach the arena entrance')


def izzy_like(name):
    n = (name or '').lower()
    return 'izzy' in n or 'no-beard' in n or "cap'n" in n or 'capn' in n


class EnterArena(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter arena')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if bot.in_arena_now():
            return False
        if bot.needs_cakes_now() or (bot.steal_restock and bot.needs_coins_now()):
            return False
        # On Brimhaven the outbound boat is paid: only the return and the entrance are needed.
        if bot.edible_in_pack() < 1 or needs_coins_restock(bot.coin_count(), bot.paid(), True):
            return False
        here = game.tile()
        return here is not None and here.level == 0 and max(abs(here.x - ARENA_ENTRANCE.x), abs(here.z - ARENA_ENTRANCE.z)) <= 12

    def pay(self):
        """Use with yield from."""
        bot = self.bot
        bot.status = "paying Cap'n Izzy"
        clerk = npcs.query().name("Cap'n Izzy No-Beard").within(10).nearest()
        if clerk is None:
            clerk = npcs.query().within(10).where(lambda n: izzy_like(n.name)).nearest()
        if clerk is None:
            bot.log("Cap'n Izzy not nearby — walking to entrance")
            yield from traversal.walk_resilient(LADDER_DOWN_STAND, radius=2, attempts=2, timeout_ms=30000)
            return False
        before = bot.coin_count()
        # Pay takes the 200gp at once while unpaid; Talk-to otherwise.
        if len([a for a in clerk.actions() if a.lower() == 'pay']) > 0:
            clerk.interact('Pay')
        else:
            clerk.interact('Talk-to')
            for _ in range(10):
                if bot.paid() or bot.coin_count() < before:
                    break
                if chat_dialog.can_continue():
                    yield from chat_dialog.continue_()
                elif len(chat_dialog.options()) > 0:
                    chose = yield from chat_dialog.choose_option('use the Agility Arena')
                    if not chose:
                        chose = yield from chat_dialog.choose_option("Okay, here's 200")
                    if not chose:
                        yield from chat_dialog.choose_option()
                else:
                    break
                yield from execution.delay_ticks(1)
        yield from execution.delay_until(lambda: bot.paid() or bot.coin_count() < before, 5000)
        if not bot.paid() and bot.coin_count() >= before:
            bot.log('payment did not register — retrying')
            return False
        bot.log('paid 200 coins entrance')
        return True

    def execute(self):
        bot = self.bot
        if not bot.paid():
            paid = yield from self.pay()
            if not paid:
                return
        bot.status = 'climbing into the arena'
        yield from traversal.walk_resilient(LADDER_DOWN_STAND, radius=2, attempts=2, timeout_ms=20000)
        ladder = locs.query().name('Ladder').within(6).where(lambda l: first_op(l, 'climb-down') is not None).nearest()
        if ladder is None:
            bot.log('no ladder down at the entrance')
            return
        ladder.interact(first_op(ladder, 'climb-down') or 'Climb-Down')
        yield from execution.delay_until(bot.in_arena_now, 8000)


def climbing_rope():
    return locs.query().within(20).where(lambda l: 'climbing rope' in (l.name or '').lower()).nearest()


class ClimbOutOfPit(Task):
    """After a failed obstacle the player lands on plane 0, under the arena."""

    def __init__(self, bot):
        Task.__init__(self, label='climb out of pit')
        self.bot = bot

    def validate(self):
        return self.bot.in_pit_now()

    def execute(self):
        bot = self.bot
        bot.note_fall()
        bot.status = 'climbing out of the pit'
        rope = climbing_rope()
        if rope is None:
            bot.log('fallen into the pit but no Climbing rope in range — waiting')
            yield from execution.delay_ticks(2)
            return
        acts = rope.actions()
        op = first_op(rope, 'climb') or (acts[0] if len(acts) > 0 else None)
        rt = rope.tile()
        if not op:
            bot.log(f'Climbing rope at {rt.x},{rt.z} has no climb op')
            return
        bot.log(f'climbing rope at {rt.x},{rt.z} ({op})')
        if not rope.interact(op):
            bot.log('Climbing rope interact failed')
            return
        # It waits until it's back on the platforms and idle, so the next hop can go at once.
        out = yield from execution.delay_until(lambda: not bot.in_pit_now() and not game.animating(), 8000)
        if not out:
            bot.log('still in the pit after climbing rope')
            return
        bot.was_in_pit = False


def dispenser_near():
    found = locs.query().name('Ticket Dispenser').within(6).nearest()
    if found is not None:
        return found
    return locs.query().within(6).where(lambda l: 'ticket' in (l.name or '').lower() and first_op(l, 'tag') is not None).nearest()


class TagPillar(Task):
    def __init__(self, bot):
        Task.__init__(self, label='tag pillar')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.in_arena_now() or bot.in_pit_now() or bot.tagged():
            return False
        target = bot.target_pillar()
        return target >= 0 and target < TICKET_PILLAR_COUNT and bot.platform() == target

    def execute(self):
        bot = self.bot
        bot.note_hint()
        bot.status = 'tagging ticket dispenser'
        tickets_before = bot.ticket_count()
        tagged_before = bot.tagged()
        dispenser = dispenser_near()
        if dispenser is None:
            bot.log(f'no Ticket Dispenser on platform {bot.platform()}')
            return
        op = first_op(dispenser, 'tag') or 'Tag'
        dt = dispenser.tile()
        here = game.tile()
        if here is not None and here.distance_to(dt) > 1:
            yield from direct_navigator.walk_to(dt, 1, 3000)

        def landed():
            m = reader.modals()
            return bot.tagged() != tagged_before or bot.ticket_count() > tickets_before or m.chat != -1 or m.main != -1

        # The first tag shows a message box; later ones give a ticket and an item box.
        for _ in range(5):
            if bot.tagged() != tagged_before or bot.ticket_count() > tickets_before:
                break
            (dispenser_near() or dispenser).interact(op)
            started = yield from execution.delay_until(landed, 800)
            if started:
                break
        # The boxes are cleared so the next task can run.
        for _ in range(4):
            if not chat_dialog.can_continue():
                break
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
        if bot.ticket_count() > tickets_before or bot.tagged():
            bot.note_tag()


class CrossObstacle(Task):
    def __init__(self, bot):
        Task.__init__(self, label='cross obstacle')
        self.bot = bot

    def validate(self):
        bot = self.bot
        if not bot.in_arena_now() or bot.in_pit_now():
            return False
        if should_bank(bot.ticket_count(), bot.food_in_pack(), bot.bank_at_tickets, bot.steal_restock):
            return False
        here = bot.platform()
        if here < 0:
            return False
        target = bot.target_pillar()
        if not bot.tagged() and target >= 0:
            return here != target and next_hop(here, target, bot.agility()) is not None
        # After a tag it goes back to the centre: waiting on a tagged corner turns the next arrow into a 50s miss.
        if on_ticket_hub(here):
            return False
        return next_hop(here, CENTRE_PLATFORM, bot.agility()) is not None

    def execute(self):
        bot = self.bot
        bot.note_hint()
        here = bot.platform()
        target = bot.target_pillar()
        chasing = not bot.tagged() and target >= 0
        goal = target if chasing else CENTRE_PLATFORM
        hop = next_hop(here, goal, bot.agility(), bot.avoid_hop)
        if hop is None:
            bot.log(f'no path from platform {here} to {goal} at agility {bot.agility()}')
            return
        edge = edge_between(here, hop, bot.agility())
        if edge is None:
            bot.log(f'no usable edge {here}->{hop}')
            return
        bot.last_hop_to = hop
        if bot.avoid_hop == hop:
            bot.avoid_hop = -1
        bot.hops += 1
        bot.log(f"crossing {edge.kind} {here}→{hop} (goal {goal}{'' if chasing else ', back to centre'})")
        bot.status = f'crossing {edge.kind} {here}→{hop}' if chasing else f'back to centre {here}→{hop}'
        # Runs while chasing a ticket pillar, walks back to the centre to save energy for the next tag.
        if game.run_enabled() != chasing:
            game.set_run(chasing)
            yield from execution.delay_until(lambda: game.run_enabled() == chasing, 1200)
        yield from cross_edge(bot, edge, here, hop)


class SpikeWait(Task):
    def __init__(self, bot):
        Task.__init__(self, label='spike wait')
        self.bot = bot

    # It waits while the pillar is tagged already, or before any hint.
    def validate(self):
        bot = self.bot
        if not bot.in_arena_now() or bot.in_pit_now():
            return False
        if should_bank(bot.ticket_count(), bot.food_in_pack(), bot.bank_at_tickets, bot.steal_restock):
            return False
        return bot.tagged() or bot.target_pillar() < 0 or bot.platform() == bot.target_pillar()

    def execute(self):
        bot = self.bot
        bot.note_hint()
        bot.status = 'waiting for next pillar' if bot.tagged() else 'on target — tag'
        yield from execution.delay_ticks(1)


def leave_arena(bot):
    """Climbs out of the pit if fallen, then up the exit ladder. Use with yield from."""
    if bot.in_pit_now():
        rope = climbing_rope()
        if rope is not None:
            bot.status = 'climbing rope out of the pit'
            rope.interact(first_op(rope, 'climb') or 'Climb')
            yield from execution.delay_until(lambda: not bot.in_pit_now() and not game.animating(), 6000)
    exit = locs.query().name('Ladder').within(40).where(lambda l: first_op(l, 'climb-up') is not None).nearest()
    here = bot.platform()
    if exit is None:
        # The exit ladder is in the south-east, so it heads for platform 4 (or 14) and looks again.
        if here >= 0:
            hop = next_hop(here, 4, bot.agility())
            if hop is None:
                hop = next_hop(here, 14, bot.agility())
            if hop is not None:
                e = edge_between(here, hop, bot.agility())
                if e is not None:
                    yield from cross_edge(bot, e, here, hop)
        return
    bot.status = 'climbing out of the arena'
    # It may have to cross platforms to reach it first.
    dest = exit.tile()
    dest_plat = platform_at(dest.x, dest.z, 12)
    if here >= 0 and dest_plat >= 0 and here != dest_plat:
        hop = next_hop(here, dest_plat, bot.agility())
        if hop is not None:
            e = edge_between(here, hop, bot.agility())
            if e is not None:
                yield from cross_edge(bot, e, here, hop)
                return
    exit.interact(first_op(exit, 'climb-up') or 'Climb-up')
    yield from execution.delay_until(lambda: not bot.in_arena_now(), 8000)


# Why: arriving on dest is success, with leftover animation fine, and a fall or progress onto another platform
# settles the hop too. A soft fail starts and goes idle on the start (the saws' and pressure pad's bounce), so a few
# idle ticks there settle it rather than the whole timeout.
def wait_obstacle_settled(bot, source, dest, timeout_ms):
    """Waits until the hop is far enough along to act again. Use with yield from."""
    left_start = False
    idle_ticks = 0
    anim_streak = 0
    last_tile = game.tile()
    sx, sz = PILLARS[source]
    start = now_ms()
    while now_ms() - start < timeout_ms:
        platform = bot.platform()
        anim = game.animating()
        pit = bot.in_pit_now()
        tile = game.tile()
        moved = tile is not None and last_tile is not None and (tile.x != last_tile.x or tile.z != last_tile.z or tile.level != last_tile.level)
        # Why: walking a trap keeps the platform the start until near dest, so leaving means off the start island, a
        # fall or a held animation; a one-frame click flash would fail it before the hop starts.
        dist_from_start = max(abs(tile.x - sx), abs(tile.z - sz)) if tile is not None else 0
        anim_streak = anim_streak + 1 if anim else 0
        if pit or dist_from_start > 4 or (platform >= 0 and platform != source) or anim_streak >= 2:
            left_start = True
        outcome = obstacle_outcome(platform, source, dest, pit)
        if outcome != 'pending':
            bot.log(f'  settled {outcome} platform {platform} (from {source}, want {dest}) anim={anim} pit={pit}')
            return
        idle_ticks = idle_ticks + 1 if not anim and not moved else 0
        # A bounce or a stall in a trap after leaving: a few idle ticks without arriving retries at once.
        if left_start and idle_ticks >= 3:
            bot.log(f'  settled failed (stalled after leave) platform {platform} distStart={dist_from_start} (from {source}, want {dest})')
            return
        # The click or walk never took: it retries without waiting out the timeout.
        if not left_start and platform == source and idle_ticks >= 6:
            bot.log(f'  settled failed (never left start) platform {platform} (from {source}, want {dest})')
            return
        if tile is not None:
            last_tile = tile
        yield from execution.delay_ticks(1)
    bot.log(f'  settled timeout platform {bot.platform()} (from {source}, want {dest}) anim={game.animating()} pit={bot.in_pit_now()}')


def find_edge_loc(edge, source, dest):
    if not edge.loc_name:
        return None
    ax, az = PILLARS[source]
    bx, bz = PILLARS[dest]
    mid_x = (ax + bx) / 2
    mid_z = (az + bz) / 2
    # The candidate on the source side wins, so a rope swing faces the right way.
    candidates = locs.query().name(edge.loc_name).within(16).where(lambda l: len(l.actions()) > 0).results()
    if len(candidates) == 0:
        return locs.query().name(edge.loc_name).within(16).nearest()
    best = None
    best_score = 0
    for loc in candidates:
        t = loc.tile()
        score = ((t.x - mid_x) ** 2 + (t.z - mid_z) ** 2) ** 0.5 + ((t.x - ax) ** 2 + (t.z - az) ** 2) ** 0.5 * 0.25
        if best is None or score < best_score:
            best_score = score
            best = loc
    return best


def edge_started(bot, source, dest):
    p = bot.platform()
    return game.animating() or p == dest or bot.in_pit_now() or (p >= 0 and p != source)


def cross_edge(bot, edge, source, dest):
    """Use with yield from."""
    if edge.mode == 'walk':
        # The traps fire on the gap's tiles, so it walks onto the trigger on the source side.
        x, z = walk_trap_stand(source, dest)
        trigger = Tile(x, z, 3)
        if not direct_navigator.walk(trigger):
            bot.log(f'  walk to {x},{z} refused — DirectNavigator')
            walked = yield from direct_navigator.walk_to(trigger, 0, 4000)
            if not walked:
                bot.log(f'  could not walk trap trigger {x},{z}')
                return
        yield from wait_obstacle_settled(bot, source, dest, 8000)
        return
    loc = find_edge_loc(edge, source, dest)
    if loc is None:
        bot.log(f'no {edge.loc_name or edge.kind} loc for edge {source}->{dest}')
        return
    acts = loc.actions()
    named = [a for a in acts if edge.op and a.lower() == edge.op.lower()]
    op = named[0] if len(named) > 0 else (acts[0] if len(acts) > 0 else None)
    lt = loc.tile()
    if not op:
        bot.log(f'{edge.loc_name} has no actions at {lt.x},{lt.z}')
        return
    # Why: it stands on the source side before every interaction; being on the platform isn't enough, since the
    # recovery ladders and dispensers can part the player from the obstacle's usable side on one island.
    approach = None
    for x, z in edge_approach_candidates(source, dest, lt):
        t = Tile(x, z, lt.level)
        if reachability.walkable(t) and reachability.can_reach(t, max_steps=512):
            approach = t
            break
    if approach is None:
        bot.log(f'  no reachable source-side stage for {edge.kind} {source}→{dest}')
        return
    here = game.tile()
    if (here is None or not here == approach) and bot.platform() == source:
        bot.log(f'  stage {approach.x},{approach.z} before {edge.kind} {source}→{dest}')
        staged = yield from direct_navigator.walk_to(approach, 0, 4000)
        if not staged:
            bot.log(f'  stage {approach.x},{approach.z} missed — clicking {edge.kind} from here')
    bot.log(f'  {op} {edge.loc_name} @ {lt.x},{lt.z}')
    # It clicks at once, even mid-animation, and again while still on the start until the obstacle takes.
    for attempt in range(5):
        p = bot.platform()
        if bot.in_pit_now() or p == dest or (p >= 0 and p != source):
            break
        live = find_edge_loc(edge, source, dest) or loc
        if not live.interact(op):
            bot.log(f'  interact failed (attempt {attempt + 1})')
        started = yield from execution.delay_until(lambda: edge_started(bot, source, dest), 700)
        if started or bot.platform() != source:
            break
        yield from execution.delay_ticks(1)
    yield from wait_obstacle_settled(bot, source, dest, 10000)


class BrimhavenAgility(TaskBot):
    def on_start(self):
        # A server tick between loops, so the next hop can start the tick it goes idle.
        self.loop_delay = 600
        self.loop_cadence = {'kind': 'server_tick', 'ticks': 1}
        self.status = 'starting'
        self.stunned_until_tick = 0
        self.tickets_collected = 0
        self.tags = 0
        self.misses = 0
        self.falls = 0
        self.hops = 0
        self.last_hint = -1
        self.pending_hint = -1
        self.tagged_this_hint = False
        self.chase_started_at = 0
        self.last_tag_ms = 0
        self.was_in_pit = False
        self.last_hop_to = -1
        self.avoid_hop = -1
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.food_name = script_food(s, 'Lobster')
        self.food_per_trip = s.num('food_withdraw', DEFAULT_FOOD_PER_TRIP)
        self.bank_at_tickets = s.num('bank_at_tickets', DEFAULT_BANK_TICKETS)
        self.steal_restock = s.bool('steal_restock', False)
        if self.steal_restock and skills.level('thieving') < STEAL_THIEVING_MIN:
            msg = f"steal restock needs Thieving {STEAL_THIEVING_MIN} (have {skills.level('thieving')})"
            self.log(msg)
            raise RuntimeError(f'BrimhavenAgility: {msg}')
        self.on('chat_message', self.heard)
        self.on('inventory_changed', self.inventory_changed)
        self.started_at = time.time()
        self.xp_at_start = skills.xp('agility')
        steal = ', steal restock on' if self.steal_restock else ''
        self.log(f"BrimhavenAgility — food '{self.food_name}' x{self.food_per_trip}, bank@{self.bank_at_tickets} tickets, eat@{EAT_AT_HP}hp, ticket cap {TICKET_CAP_PER_HOUR}/hr{steal}")
        self.add(ContinueDialog(), Eat(self), ClimbOutOfPit(self), LeaveForSteal(self), SellFoodForBoat(self), StealFood(self), StealCoins(self), BankTrip(self),
                 TravelToArena(self), EnterArena(self), TagPillar(self), CrossObstacle(self), SpikeWait(self))

    def heard(self, e):
        t = (e.text or '').lower()
        if 'been stunned' in t or 'fail to pick' in t:
            self.stunned_until_tick = game.tick() + STUN_COMBAT_TICKS

    def inventory_changed(self, e):
        gained = ticket_inventory_gain(e, bank.is_open())
        if gained > 0:
            self.tickets_collected += gained

    def set_status(self, s):
        self.status = s

    def note_hint(self):
        hint = self.target_pillar()
        if hint < 0 or hint == self.last_hint:
            self.pending_hint = -1
            return
        # A hint's tile can match a neighbour for one read, so it takes two in a row.
        if hint != self.pending_hint:
            self.pending_hint = hint
            return
        if hint_missed(self.last_hint, hint, self.tagged_this_hint):
            self.misses += 1
            self.log(f'missed pillar {self.last_hint} — streak broken (misses {self.misses})')
        self.last_hint = hint
        self.pending_hint = -1
        self.tagged_this_hint = False
        self.chase_started_at = now_ms()
        self.log(f'hint → pillar {hint}')

    def note_fall(self):
        if self.was_in_pit:
            return
        self.was_in_pit = True
        self.falls += 1
        self.avoid_hop = self.last_hop_to
        self.log(f'fell into the pit (falls {self.falls}) — avoiding hop to {self.avoid_hop}')

    def note_tag(self):
        self.tags += 1
        self.tagged_this_hint = True
        self.last_tag_ms = int(now_ms() - self.chase_started_at) if self.chase_started_at > 0 else 0
        self.log(f'tagged pillar {self.platform()} in {self.last_tag_ms}ms (tickets {self.ticket_count()})')

    def food_in_pack(self):
        return food_count(inventory.items(), self.food_name)

    def edible_in_pack(self):
        selected = self.food_in_pack()
        cakes = carried_cakes()
        if len([f for f in food_forms(self.food_name) if 'cake' in f]) > 0:
            return max(selected, cakes)
        return selected + cakes

    def at_brimhaven_now(self):
        here = game.tile()
        return here is not None and on_brimhaven_surface(here.x, here.z, here.level)

    def needs_coins_now(self):
        return needs_coins_restock(self.coin_count(), self.paid(), self.at_brimhaven_now() or self.in_arena_now())

    def needs_cakes_now(self):
        return needs_cake_steal(self.food_in_pack(), carried_cakes(), self.steal_restock, self.needs_coins_now(),
                                inventory.free() - steal_reserve_slots(self.coin_count(), self.ticket_count()))

    def needs_food_sale_for_boat_now(self):
        return needs_food_sale_for_boat(self.coin_count(), self.edible_in_pack(), self.at_brimhaven_now())

    def stunned(self):
        return game.tick() <= self.stunned_until_tick

    def ticket_count(self):
        return inventory.count(TICKET_NAME)

    def coin_count(self):
        return inventory.count('Coins')

    # Why: the darts and saws roll current agility and always fail below their gate, so a base level would walk them
    # after a drain.
    def agility(self):
        return skills.effective('agility')

    def hp(self):
        return skills.effective('hitpoints')

    def paid(self):
        return has_paid(reader.varp(ARENA_VARP))

    def tagged(self):
        return pillar_tagged(reader.varp(ARENA_VARP))

    # Only on the platforms' plane: the pit shares x and z with the pillars but has none of their locs.
    def platform(self):
        t = game.tile()
        if t is None or not on_arena_platform(t.level) or not in_arena(t.x, t.z):
            return -1
        return platform_at(t.x, t.z)

    def in_pit_now(self):
        t = game.tile()
        return t is not None and in_arena_pit(t.x, t.z, t.level)

    def target_pillar(self):
        """The ticket pillar the hint arrow points at."""
        h = reader.hint_tile()
        return pillar_from_hint(h.x, h.z) if h is not None else -1

    def in_arena_now(self):
        t = game.tile()
        return t is not None and in_arena(t.x, t.z)

    # Why: Swarm leaves only once you leave its tile, which the 5x5 platforms can't, so its evade would loop forever.
    def ignored_randoms(self):
        return ['swarm'] if self.in_arena_now() else []

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        per_hour = f'{self.tickets_collected / minutes * 60:.0f}' if minutes > 0.2 else '—'
        return {'Status': self.status, 'Tickets': self.tickets_collected, 'Tickets/hr': per_hour, 'Cap/hr': TICKET_CAP_PER_HOUR, 'Tags': self.tags,
                'Misses': self.misses, 'Falls': self.falls, 'Hops': self.hops, 'Agility xp': skills.xp('agility') - self.xp_at_start,
                'Food': self.food_in_pack(), 'Coins': self.coin_count()}


BOT = define_bot(
    name='BrimhavenAgility',
    create=BrimhavenAgility,
    description="Brimhaven Agility Arena — banks food+coins at Ardougne south, ships to Brimhaven, pays Cap'n Izzy, tags ticket pillars on the level-optimal path, and grinds centre spikes between tags. Optional steal restock (Thieving 20) takes cakes from the Baker's stall and coins from guards.",
    category='Agility',
    tags=['brimhaven', 'arena', 'tickets', 'banking', 'food'],
    settings_schema=SETTINGS,
)

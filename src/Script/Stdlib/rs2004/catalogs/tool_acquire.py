"""Planning how to get a missing or better tool: buy it, repair a broken one, or smith an axe. Ported from
rs2b0t's api/acquisition/ToolAcquire.ts (MIT, see thirdparty/rs2b0t).

The planners are pure: they read an AcquireWorld of counts and levels and give a plan. A script carries the
plan out itself (bank, walk, shop), with walk_to_tool_vendor for the walk.
"""

from rs2004.catalogs.mining import BROKEN_PICKAXE
from rs2004.catalogs.tools import AXES, HAMMER, PICKAXES
from rs2004.geometry import Tile

COINS = 'Coins'
BROKEN_AXE = 'Broken axe'

TOOL_ACQUIRE_OPTIONS = ['Off', 'Buy / repair']
FORGETFUL_BANK_ODDS = 100


def parse_tool_acquire_mode(raw):
    """'on' or 'off' from a setting's value."""
    if raw is True:
        return 'on'
    if raw is False or raw is None:
        return 'off'
    text = str(raw).strip().lower()
    return 'on' if text in ['on', 'buy / repair', 'buy/repair', 'true', 'yes'] else 'off'


class ToolVendor:
    """keeper (the shopkeeper's name), stand, bank_stand, and for one underground, the hop: hop_from, hop_loc
    and hop_action."""

    def __init__(self, keeper, stand, bank_stand, hop_from=None, hop_loc=None, hop_action=None):
        self.keeper = keeper
        self.stand = stand
        self.bank_stand = bank_stand
        self.hop_from = hop_from
        self.hop_loc = hop_loc
        self.hop_action = hop_action

    def __repr__(self):
        return f'ToolVendor({repr(self.keeper)})'


class ShopOffer:
    def __init__(self, name, cost, vendor):
        self.name = name
        self.cost = cost
        self.vendor = vendor

    def __repr__(self):
        return f'ShopOffer({repr(self.name)}, {self.cost}, {self.vendor.keeper})'


# Bob in Lumbridge: axes, bronze to steel.
BOB_VENDOR = ToolVendor('Bob', Tile(3231, 3203, 0), Tile(3093, 3243, 0))
# Nurmof in the Dwarven Mine: pickaxes, bronze to rune, down the trapdoor north of Falador.
NURMOF_VENDOR = ToolVendor('Nurmof', Tile(2997, 9844, 0), Tile(3013, 3355, 0), Tile(3019, 3449, 0), 'Trapdoor', 'Climb-down')
# Gerrant in Port Sarim: fishing gear, feathers and the fly fishing rod.
GERRANT_VENDOR = ToolVendor('Gerrant', Tile(3013, 3224, 0), Tile(3092, 3243, 0))
# Harry in Catherby: fishing gear, but no feathers or fly fishing rod.
HARRY_VENDOR = ToolVendor('Harry', Tile(2833, 3443, 0), Tile(2809, 3441, 0))
GERRANT_ONLY_FISHING = ['feather', 'fly fishing rod']

VARROCK_ANVIL_STAND = Tile(3188, 3425, 0)
VARROCK_ANVIL_BANK = Tile(3185, 3440, 0)

PICKAXE_SHOP_COSTS = {
    'Bronze pickaxe': 1,
    'Iron pickaxe': 140,
    'Steel pickaxe': 500,
    'Mithril pickaxe': 1300,
    'Adamant pickaxe': 3200,
    'Rune pickaxe': 32000,
}
AXE_SHOP_COSTS = {
    'Bronze axe': 16,
    'Iron axe': 56,
    'Steel axe': 200,
}
FISHING_SHOP_COSTS = {
    'Small fishing net': 5,
    'Fishing rod': 5,
    'Fly fishing rod': 5,
    'Harpoon': 5,
    'Lobster pot': 20,
    'Big fishing net': 20,
    'Fishing bait': 3,
    'Feather': 2,
}
AXE_SMITH_LEVEL = {
    'Bronze axe': 1,
    'Iron axe': 16,
    'Steel axe': 31,
    'Mithril axe': 51,
    'Adamant axe': 71,
    'Rune axe': 86,
}
AXE_BAR_FOR = {
    'Bronze axe': 'Bronze bar',
    'Iron axe': 'Iron bar',
    'Steel axe': 'Steel bar',
    'Mithril axe': 'Mithril bar',
    'Adamant axe': 'Adamantite bar',
    'Rune axe': 'Runite bar',
}
REPAIR_CHOICES = ['repair', 'fix', 'fix my', 'yes']


class ToolAcquirePlan:
    """kind 'repair' (broken_name, label, vendor, prefer), 'buy' (name, cost, qty, vendor, equip, reason) or
    'smith' (name, bar, smith_level, vendor_bank, anvil_stand, equip, reason)."""

    def __init__(self, kind, **fields):
        self.kind = kind
        self.name = None
        self.cost = 0
        self.qty = 1
        self.vendor = None
        self.equip = False
        self.reason = ''
        self.broken_name = None
        self.label = None
        self.prefer = []
        self.bar = None
        self.smith_level = 0
        self.vendor_bank = None
        self.anvil_stand = None
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self):
        if self.kind == 'repair':
            return f'ToolAcquirePlan(repair {self.broken_name} at {self.vendor.keeper})'
        if self.kind == 'buy':
            return f'ToolAcquirePlan(buy {self.qty} {self.name} for {self.cost} at {self.vendor.keeper})'
        return f'ToolAcquirePlan(smith {self.name} from {self.bar})'


class AcquireWorld:
    """What the planners read: skill_level(skill), held_count(name) (backpack and worn), inv_count(name),
    bank_count(name) and worn(name), all functions."""

    def __init__(self, skill_level, held_count, inv_count, bank_count, worn):
        self.skill_level = skill_level
        self.held_count = held_count
        self.inv_count = inv_count
        self.bank_count = bank_count
        self.worn = worn


def _total_coins(world):
    return world.inv_count(COINS) + world.bank_count(COINS)


_NOT_RANKED = 1000000


def _tier_rank(tiers, name):
    for i in range(len(tiers)):
        if tiers[i].name.lower() == name.lower():
            return i
    return _NOT_RANKED


def best_owned_tier(level, tiers, count):
    """The best tier level can use that count(name) says is owned."""
    for tier in tiers:
        if level >= tier.level and count(tier.name) > 0:
            return tier.name
    return None


def pickaxe_shop_offers():
    return [ShopOffer(name, cost, NURMOF_VENDOR) for name, cost in PICKAXE_SHOP_COSTS.items()]


def axe_shop_offers():
    return [ShopOffer(name, cost, BOB_VENDOR) for name, cost in AXE_SHOP_COSTS.items()]


def best_affordable_shop_tier(level, tiers, offers, coins, owned):
    """The best usable, affordable offer better than owned (any usable one when owned is None)."""
    owned_rank = _tier_rank(tiers, owned) if owned is not None else _NOT_RANKED
    for tier in tiers:
        if level < tier.level or _tier_rank(tiers, tier.name) >= owned_rank:
            continue
        for offer in offers:
            if offer.name.lower() == tier.name.lower() and offer.cost <= coins:
                return offer
    return None


def best_smithable_axe(woodcutting_level, smithing_level, owned, bar_count, has_hammer):
    """(name, bar, smith_level) of the best axe better than owned that a bar on hand can make, or None."""
    if not has_hammer:
        return None
    owned_rank = _tier_rank(AXES, owned) if owned is not None else _NOT_RANKED
    for tier in AXES:
        if woodcutting_level < tier.level or _tier_rank(AXES, tier.name) >= owned_rank:
            continue
        need = AXE_SMITH_LEVEL.get(tier.name)
        bar = AXE_BAR_FOR.get(tier.name)
        if need is None or bar is None or smithing_level < need or bar_count(bar) < 1:
            continue
        return (tier.name, bar, need)
    return None


def plan_broken_tool_repair(held_or_worn):
    """A repair plan for a broken pickaxe (Nurmof) or axe (Bob) that's held, or None."""
    if held_or_worn(BROKEN_PICKAXE):
        return ToolAcquirePlan('repair', broken_name=BROKEN_PICKAXE, label='pickaxe', vendor=NURMOF_VENDOR, prefer=REPAIR_CHOICES)
    if held_or_worn(BROKEN_AXE):
        return ToolAcquirePlan('repair', broken_name=BROKEN_AXE, label='axe', vendor=BOB_VENDOR, prefer=REPAIR_CHOICES)
    return None


def _buy(offer, owned):
    reason = f'upgrade {owned} to {offer.name}' if owned is not None else f'buy {offer.name}'
    return ToolAcquirePlan('buy', name=offer.name, cost=offer.cost, qty=1, vendor=offer.vendor, equip=True, reason=reason)


def plan_pickaxe_acquire(world, upgrade=False):
    """Repair a broken pickaxe, or buy one when none is owned, or a better affordable one with upgrade."""
    repair = plan_broken_tool_repair(lambda n: world.held_count(n) > 0)
    if repair is not None and repair.label == 'pickaxe':
        return repair
    level = world.skill_level('mining')
    owned = best_owned_tier(level, PICKAXES, lambda n: world.held_count(n) + world.bank_count(n))
    if owned is not None and not upgrade:
        return None
    offer = best_affordable_shop_tier(level, PICKAXES, pickaxe_shop_offers(), _total_coins(world), owned)
    return _buy(offer, owned) if offer is not None else None


def plan_axe_acquire(world, upgrade=False):
    """Repair a broken axe, or get one when none is owned (or a better one with upgrade): Bob's shop up to
    steel, or smith one from a bar and a hammer on hand, whichever is the better axe."""
    repair = plan_broken_tool_repair(lambda n: world.held_count(n) > 0)
    if repair is not None and repair.label == 'axe':
        return repair
    level = world.skill_level('woodcutting')
    owned = best_owned_tier(level, AXES, lambda n: world.held_count(n) + world.bank_count(n))
    if owned is not None and not upgrade:
        return None

    shop = best_affordable_shop_tier(level, AXES, axe_shop_offers(), _total_coins(world), owned)
    smith = best_smithable_axe(level, world.skill_level('smithing'), owned,
                               lambda bar: world.held_count(bar) + world.bank_count(bar),
                               world.held_count(HAMMER) + world.bank_count(HAMMER) > 0)
    best = None
    best_rank = _NOT_RANKED
    if shop is not None:
        best = _buy(shop, owned)
        best_rank = _tier_rank(AXES, shop.name)
    if smith is not None and _tier_rank(AXES, smith[0]) < best_rank:
        name, bar, smith_level = smith
        reason = f'smith upgrade {owned} to {name}' if owned is not None else f'smith {name}'
        best = ToolAcquirePlan('smith', name=name, bar=bar, smith_level=smith_level, vendor_bank=VARROCK_ANVIL_BANK,
                               anvil_stand=VARROCK_ANVIL_STAND, equip=True, reason=reason)
    return best


def _distance(x, z, tile):
    dx = x - tile.x
    dz = z - tile.z
    return (dx * dx + dz * dz) ** 0.5


def fishing_vendor_for(name, near=None):
    """Gerrant for feathers and fly rods, which Harry doesn't stock; otherwise whichever is nearer near (a
    Tile), or without one, Harry for bait and big nets and Gerrant for the rest."""
    lower = name.lower()
    if lower in GERRANT_ONLY_FISHING:
        return GERRANT_VENDOR
    if near is not None:
        harry = _distance(near.x, near.z, HARRY_VENDOR.stand)
        gerrant = _distance(near.x, near.z, GERRANT_VENDOR.stand)
        return HARRY_VENDOR if harry <= gerrant else GERRANT_VENDOR
    if lower == 'fishing bait' or lower == 'big fishing net':
        return HARRY_VENDOR
    return GERRANT_VENDOR


def fishing_shop_cost(name):
    for key, cost in FISHING_SHOP_COSTS.items():
        if key.lower() == name.lower():
            return cost
    return None


def is_fishing_bait_piece(piece):
    """Bait or feathers: a stack whose restock target applies."""
    if piece.restock <= 1:
        return False
    return piece.name.lower() in ['fishing bait', 'feather']


def with_bait_target(method, bait_qty):
    """The method's gear with bait and feathers topped up to bait_qty; tools as they are."""
    from rs2004.catalogs.fishing import FishingGearPiece
    target = max(1, int(bait_qty))
    gear = []
    for piece in method.gear:
        gear.append(FishingGearPiece(piece.name, piece.min, target) if is_fishing_bait_piece(piece) else piece)
    return gear


def plan_fishing_gear_buys(method, world, near=None, bait_qty=1000):
    """Buy plans for each missing piece that's for sale and affordable, in the method's order. Tools are
    bought when none is owned; bait and feathers are topped up to bait_qty, or as many as the coins left buy."""
    out = []
    coins_left = _total_coins(world)
    for piece in with_bait_target(method, bait_qty):
        is_bait = is_fishing_bait_piece(piece)
        need_at_least = piece.restock if is_bait else piece.min
        if world.held_count(piece.name) + world.bank_count(piece.name) >= need_at_least:
            continue
        unit = fishing_shop_cost(piece.name)
        if unit is None:
            continue
        need_qty = max(1, need_at_least - world.held_count(piece.name))
        qty = max(piece.min, need_qty) if is_bait else 1
        cost = unit * qty
        if coins_left < cost:
            if qty > 1 and coins_left >= unit:
                qty = coins_left // unit
                cost = unit * qty
            else:
                continue
        out.append(ToolAcquirePlan('buy', name=piece.name, cost=cost, qty=qty, vendor=fishing_vendor_for(piece.name, near),
                                   equip=False, reason=f'buy {qty} {piece.name}'))
        coins_left -= cost
    return out


def plan_fishing_gear_acquire(method, world, near=None, bait_qty=1000):
    plans = plan_fishing_gear_buys(method, world, near, bait_qty)
    return plans[0] if plans else None


def buy_plans_cost(plans):
    return sum([p.cost for p in plans])


def fishing_gear_shop_cart(method, world, near=None, bait_qty=1000):
    """The buy plans at the first plan's shopkeeper, so a fly rod and feathers are one visit."""
    plans = plan_fishing_gear_buys(method, world, near, bait_qty)
    if not plans:
        return []
    keeper = plans[0].vendor.keeper
    return [p for p in plans if p.vendor.keeper == keeper]


def plan_gather_tool_acquire(reqs, world, upgrade=False):
    """A plan for the first tiered requirement, pickaxe or axe, that needs one; a broken tool first."""
    repair = plan_broken_tool_repair(lambda n: world.held_count(n) > 0)
    if repair is not None:
        return repair
    for req in reqs:
        if req.kind != 'tiered':
            continue
        plan = None
        if req.skill == 'mining':
            plan = plan_pickaxe_acquire(world, upgrade)
        elif req.skill == 'woodcutting':
            plan = plan_axe_acquire(world, upgrade)
        if plan is not None:
            return plan
    return None


def coins_to_withdraw(need, inv_coins):
    return max(0, need - inv_coins)


def can_fund_plan(plan, inv_coins, bank_coins):
    if plan.kind == 'repair' or plan.kind == 'smith':
        return True
    return inv_coins + bank_coins >= plan.cost


def acquire_keep_names(plan, extra=None):
    """What a deposit before the trip keeps: coins, the broken tool, or the bar and hammer."""
    keep = [COINS] + list(extra or [])
    if plan.kind == 'repair':
        keep.append(plan.broken_name)
    if plan.kind == 'smith':
        keep.append(plan.bar)
        keep.append(HAMMER)
    out = []
    for name in keep:
        if name not in out:
            out.append(name)
    return out


def shopable_missing_fishing_gear(gear, count):
    return [g.name for g in gear if count(g.name) < g.min and fishing_shop_cost(g.name) is not None]


def needs_tool_vendor_surface_hop(vendor, here):
    """Whether an underground vendor's trapdoor is needed: still above ground and far from the stand."""
    if vendor.hop_from is None or here is None:
        return False
    if not (vendor.stand.z > 9000 and here.z < 9000):
        return False
    return max(abs(here.x - vendor.stand.x), abs(here.z - vendor.stand.z)) > 20


def walk_to_tool_vendor(vendor, log=None):
    """Walks to the vendor's stand, through Nurmof's trapdoor when above ground. Use with yield from; True on
    arrival."""
    import _core
    from rs2004 import execution
    from rs2004.entities import locs, local_tile
    from rs2004.traversal import traversal
    say = log if log is not None else (lambda message: None)
    here = local_tile()
    if here.z > 9000 and vendor.stand.z > 9000:
        arrived = yield from traversal.walk_resilient(vendor.stand, radius=4, timeout_ms=120000, log=say)
        return arrived
    if needs_tool_vendor_surface_hop(vendor, here):
        say(f'acquire: to the {vendor.hop_loc} at {vendor.hop_from}')
        arrived = yield from traversal.walk_resilient(vendor.hop_from, radius=2, timeout_ms=90000, log=say)
        if not arrived:
            return False
        if local_tile().z <= 9000:
            hop_loc = vendor.hop_loc
            hop_action = vendor.hop_action
            trap = locs.query().name(hop_loc).action(hop_action).nearest()
            if trap is None:
                trap = locs.query().name(hop_loc).nearest()
            for attempt in range(2):
                if trap is None:
                    break
                op = hop_action if hop_action in trap.actions() else trap.actions()[0]
                say(f'acquire: {op} {trap.name}')
                trap.interact(op)
                entered = yield from execution.delay_until_ticks(lambda: _core.get_z() >= 9000, 17)
                if entered:
                    break
    arrived = yield from traversal.walk_resilient(vendor.stand, radius=4, timeout_ms=120000, log=say)
    return arrived

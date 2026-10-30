"""Ported from rs2b0t's src/bot/api/ai/quests/defs/sheepherder/herdPath.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

__all__ = ['HerdPlan', 'HERD_DIRS', 'pushable', 'in_box', 'pinned', 'risky', 'herd_distances', 'herd_plan', 'herd_cost', 'herd_directions', 'herd_distance']

# docs/QUESTS.md
HERD_DIRS = [
    Record({'dx': 0, 'dz': 1}),
    Record({'dx': 1, 'dz': 0}),
    Record({'dx': 0, 'dz': -1}),
    Record({'dx': -1, 'dz': 0}),
]
MARGIN = 24


def key(x, z):
    return x * 100000 + z


# Why: `prod_sheep` walks the sheep 1 tile along `coord_direction(player, sheep)`, which is cardinal and points away from the player, so a push is legal only where the opposite tile is standable.
# Why: that tile also has to be able to step onto the sheep, or the Prod op cannot reach it from there; the fence east of the second sheep's field is walkable on both sides and passable on neither.
def pushable(grid, x, z, dir):
    """Whether a sheep on (x,z) can be pushed one tile in `dir`."""
    return grid.can_step(x, z, dir.dx, dir.dz) and grid.walkable(x + dir.dx, z + dir.dz) and grid.walkable(x - dir.dx, z - dir.dz) and grid.can_step(x - dir.dx, z - dir.dz, dir.dx, dir.dz)


def in_box(box, x, z):
    return x >= box.x0 and x <= box.x1 and z >= box.z0 and z <= box.z1


# Why: a walkable tile with no standable side is a trap: a sheep can wander in, no prod can move it, and the engine only frees it by teleporting it home 500 ticks later.
def pinned(grid, x, z):
    """Whether no push at all can be issued at (x,z)."""
    return grid.walkable(x, z) and not any([pushable(grid, x, z, dir) for dir in HERD_DIRS])


def risky(grid, x, z, is_pinned=None):
    """Whether (x,z) touches a trap, and so is one wander step from losing the sheep."""
    if is_pinned is None:
        is_pinned = lambda px, pz: pinned(grid, px, pz)
    for dx in range(-1, 1 + 1):
        for dz in range(-1, 1 + 1):
            if is_pinned(x + dx, z + dz):
                return True
    return False


def bounds(sheep, goal):
    return Record({
        'x0': min(sheep.x, goal.x0) - MARGIN,
        'x1': max(sheep.x, goal.x1) + MARGIN,
        'z0': min(sheep.z, goal.z0) - MARGIN,
        'z1': max(sheep.z, goal.z1) + MARGIN,
    })


def search(grid, box, goal, skip=None):
    dist = {}
    queue = []
    for x in range(goal.x0, goal.x1 + 1):
        for z in range(goal.z0, goal.z1 + 1):
            if not grid.walkable(x, z) or (skip(x, z) if skip is not None else None) == True:
                continue
            # Why: the jump prod needs a stand of its own, or a sheep parked in the gate zone can never be sent over.
            if not any([grid.walkable(x - d.dx, z - d.dz) for d in HERD_DIRS]):
                continue
            dist[key(x, z)] = 0
            queue.append(Record({'x': x, 'z': z}))
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        next_ = dist.get(key(cur.x, cur.z)) + 1
        for dir in HERD_DIRS:
            px = cur.x - dir.dx
            pz = cur.z - dir.dz
            if not in_box(box, px, pz) or (key(px, pz) in dist) or (skip(px, pz) if skip is not None else None) == True:
                continue
            if not grid.walkable(px, pz) or not pushable(grid, px, pz, dir):
                continue
            dist[key(px, pz)] = next_
            queue.append(Record({'x': px, 'z': pz}))
    return dist


def herd_distances(grid, sheep, goal):
    """Prod distances to `goal`, measured in pushes. Why: searching backwards from the pen gives every tile its own next push, so a sheep that wanders mid-herd is re-routed from where it is."""
    return search(grid, bounds(sheep, goal), goal)


class HerdPlan:
    """The two route maps, prod distances by tile key: clear avoids every tile beside a trap, and any doesn't."""

    # Why: a class, not a Record, which would copy each dict into a Record of its own.
    def __init__(self, clear, any_):
        self.clear = clear
        self.any = any_


# Why: 2 plain searches, since a per-step penalty isn't a consistent potential and the greedy follow oscillated between 2 tiles forever.
def herd_plan(grid, sheep, goal):
    """Both route maps, sharing one trap lookup."""
    box = bounds(sheep, goal)
    memo = {}

    def is_pinned(x, z):
        k = key(x, z)
        hit = memo.get(k)
        if hit is not None:
            return hit
        value = pinned(grid, x, z)
        memo[k] = value
        return value

    return HerdPlan(search(grid, box, goal, lambda x, z: risky(grid, x, z, is_pinned)), search(grid, box, goal))


# Why: Use one potential across both maps; switching potentials at the boundary can send sheep back and forth.
OFF_NETWORK = 1000


def herd_cost(plan, x, z):
    """Pushes from (x,z) to the pen; a route that touches a trap counts as far worse."""
    clear = plan.clear.get(key(x, z))
    if clear is not None:
        return clear
    any_ = plan.any.get(key(x, z))
    return (None if any_ is None else any_ + OFF_NETWORK)


def herd_directions(grid, sheep, goal, plan=None):
    """Every legal push from the sheep's tile, closest-to-the-pen first."""
    routes = (plan if plan is not None else herd_plan(grid, sheep, goal))
    scored = []
    for dir in HERD_DIRS:
        if not pushable(grid, sheep.x, sheep.z, dir):
            continue
        cost = herd_cost(routes, sheep.x + dir.dx, sheep.z + dir.dz)
        if cost is None:
            continue
        scored.append(Record({'dir': dir, 'cost': cost}))
    scored.sort(key=lambda a: a.cost)
    return [s.dir for s in scored]


def herd_distance(dist, x, z):
    return dist.get(key(x, z))

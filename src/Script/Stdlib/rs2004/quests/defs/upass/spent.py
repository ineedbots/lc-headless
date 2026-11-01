"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/spent.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record

__all__ = ['spent_state_here', 'spent_here', 'spend_from', 'cell_of', 'new_journey']

# Why: Mark the departure stand as spent only after it becomes unreachable; the same cage seam is also the cell's only exit.
def spent_state_here(sides, key, reachable):
    """Whether this seam has been used, and from where. Why: a seam used from this side is finished, while one used from the far side is the way back out of a cul-de-sac, worth having last. As an equal candidate it turns the maze into a pendulum."""
    used = sides.get(key)
    if used is None or len(used) == 0:
        return 'fresh'
    return ('here' if any([reachable(_x) for _x in used]) else 'elsewhere')


def spent_here(sides, key, reachable):
    return spent_state_here(sides, key, reachable) == 'here'


def spend_from(sides, key, stand):
    _v1 = sides.get(key)
    used = (_v1 if _v1 is not None else [])
    if not any([tile.x == stand.x and tile.z == stand.z and tile.level == stand.level for tile in used]):
        used.append(stand)
    sides[key] = used


def cell_of(x, z, level):
    """Ground is remembered in 8-tile cells, coarse enough that a wander lands back inside one."""
    return f'{x >> 3},{z >> 3},{level}'


def new_journey():
    # Why: a Record would turn the dict of sides into a Record, which has no item assignment.
    journey = Record({'visited': set()})
    journey.sides = {}
    return journey


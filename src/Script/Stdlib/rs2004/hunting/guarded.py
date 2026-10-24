"""Loot under guard. Ported from rs2b0t's api/combat/hunting/guarded.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.hunting.logic import gap_to

__all__ = ['LOOT_GUARD', 'guarded']

# How close a demon may stand to a drop before the walk to it is a walk into its hunt range; guarded's default.
LOOT_GUARD = 4


# Why: a black demon hunts within three tiles with line of sight, so a drop at its feet is a walk into melee, and
# the drop outlasts its wander.
def guarded(drop, bodies, radius=4):
    """Whether any of bodies, each with a tile field and a size, stands close enough to drop that fetching it
    means fighting on foot."""
    for body in bodies:
        if gap_to(drop, body.tile, body.size) <= radius:
            return True
    return False

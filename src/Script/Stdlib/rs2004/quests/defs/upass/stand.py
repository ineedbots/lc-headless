"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/stand.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.geometry import Tile
from rs2004.walkgeom import chebyshev

__all__ = ['crossing_landing', 'by_side_that_lands']

def crossing_landing(at, stand):
    """Landing tile when crossing the seam at `at` from `stand`. Why: Crossings move one tile past the seam; mirroring a distant stand overstates that movement."""
    return Tile(at.x + (1 if at.x - stand.x > 0 else (-1 if at.x - stand.x < 0 else 0)), at.z + (1 if at.z - stand.z > 0 else (-1 if at.z - stand.z < 0 else 0)), at.level)


def by_side_that_lands(at, dest, me):
    """A sort key that ranks stands by landing progress, seam distance, then player distance. Why: Manhattan distance preserves the cage's 11-tile southward gain, and the op-click approaches the seam before crossing."""

    def toward(tile):
        return abs(tile.x - dest.x) + abs(tile.z - dest.z)

    def key(stand):
        from_me = chebyshev(stand, me if me is not None else stand)
        return toward(crossing_landing(at, stand)) * 1000000 + chebyshev(stand, at) * 1000 + min(from_me, 999)

    return key

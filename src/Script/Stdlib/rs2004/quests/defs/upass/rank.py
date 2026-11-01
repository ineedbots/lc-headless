"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/rank.ts (MIT, see thirdparty/rs2b0t)."""


__all__ = ['seam_bucket', 'order_seams']

BUCKET_WEIGHT = 100000

# Why: Reachability outranks straight-line gain, which can favor blocked bridges over a necessary detour to an open exit.
# Why: still an ordering. The scene can call a bridge you walked 140 tiles to stand beside "walled off", so a seam the flood refuses keeps its turn, last.
def seam_bucket(seam):
    if seam.gains and seam.open:
        return 0
    if not seam.gains and seam.open:
        return 1
    return (2 if seam.gains else 3)


def order_seams(seams, rank, dist):
    """Order seams by what the pocket can reach first, then by what gains, then by distance. Why: `byDistance` alone can't separate a seam in this pocket from one behind a wall, and both are in the list because neither test vetoes."""
    # Why: pocketpy's sort takes a key, not a comparator; the bucket outweighs any distance in a 104-tile scene.
    return sorted(list(seams), key=lambda seam: seam_bucket(rank(seam)) * BUCKET_WEIGHT + dist(seam))


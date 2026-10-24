"""The team's shared loadout, by item id: rs2b0t's scripts/JiveKQ/loadout.ts (MIT, see thirdparty/rs2b0t)."""

MACE = 1434
BOW = 861
ARROWS = 892
RECOIL = 2550
FOOD = 385
PASS = 1854
AIR = 556
LAW = 563
DUELING_RINGS = [2552, 2554, 2556, 2558, 2560, 2562, 2564, 2566]
GEAR = [MACE, 1163, 2503, 2497, 2491, 1731, 1061, RECOIL, ARROWS]


def trip_pack(slot):
    """(id, count) pairs a trip carries; the first account also carries the two ropes."""
    ropes = [(954, 2)] if slot == 0 else []
    return [(BOW, 1)] + ropes + [(2434, 2), (2448, 1), (2436, 1), (2440, 1), (2442, 1), (RECOIL, 1), (DUELING_RINGS[0], 1), (AIR, 5), (LAW, 1),
                                 (PASS, 1), (FOOD, 14 if slot == 0 else 16)]

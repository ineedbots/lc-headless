"""The lair, the queen's phases and the team's cross: rs2b0t's scripts/JiveKQ/policy.ts (MIT, see thirdparty/rs2b0t).
Points are Tiles; a dict off a teammate's message is turned into one before it gets here."""

BANK = Tile(3308, 3120, 0)
SURFACE = Tile(3226, 3108, 0)
UPPER = Tile(3508, 9497, 2)
ARRIVAL = Tile(3508, 9493, 0)
WAIT_CORNER = Tile(3470, 9503, 0)

GROUND_QUEEN = 1158
FLYING_QUEEN = 1160


def lure_tile(queen):
    return Tile(3508, 9493, 0) if queen.x <= 3487 else Tile(3466, 9494, 0)


def near(a, b, radius):
    return a is not None and a.level == b.level and max(abs(a.x - b.x), abs(a.z - b.z)) <= radius


def in_nest(p):
    return p is not None and p.x >= 3456 and p.x < 3520 and p.z >= 9472 and p.z < 9536


def in_lair(p):
    return in_nest(p) and p.level == 0


def queen_phase(id):
    """'melee' for the ground form, 'ranged' for the flying one, None for any other npc."""
    if id == GROUND_QUEEN:
        return 'melee'
    return 'ranged' if id == FLYING_QUEEN else None


def known_dead(health, total_health):
    return total_health > 0 and health == 0


class QueenTracker:
    """The kill clock: when the ground form appeared, when the flying form died and how long that took."""

    def __init__(self):
        self.killed_at = 0
        self.started_at = 0
        self.last_kill_ms = 0
        self._flying_alive = False
        self._flying_dead = False

    def observe(self, npc, now):
        """(dead, killed): whether the queen in sight is known dead, and whether she just left the scene dead.
        npc has id, health and total_health, or is None when she isn't in sight."""
        if npc is None:
            killed = self._flying_dead
            self._flying_dead = False
            if killed:
                self.killed_at = now
                self.last_kill_ms = now - self.started_at
            return (False, killed)
        if not self.started_at or (npc.id == GROUND_QUEEN and self.killed_at):
            self.started_at = now
            self.killed_at = 0
        if npc.id == GROUND_QUEEN:
            self._flying_alive = False
        if npc.id == FLYING_QUEEN and npc.health > 0:
            self._flying_alive = True
        dead = known_dead(npc.health, npc.total_health) and (npc.id == GROUND_QUEEN or self._flying_alive)
        if npc.id == FLYING_QUEEN and dead:
            self._flying_dead = True
        return (dead, False)


SIDES = ['West', 'East', 'North', 'South']
_DX = [-1, 1, 0, 0]
_DZ = [0, 0, 1, -1]


def combat_tile(centre, size, slot, phase='melee'):
    radius = 6 if phase == 'ranged' else size // 2 + 1
    return Tile(centre.x + _DX[slot] * radius, centre.z + _DZ[slot] * radius, centre.level)


def combat_formation(centre, size, phase, usable):
    """The four tiles of the cross, west, east, north and south, or None when no usable set exists. Ranged arms
    keep more than five tiles apart, out of each other's splash."""
    radii = [size // 2 + 1] if phase == 'melee' else [6, 5, 7, 4, 8, 3, 9]
    choices = []
    for slot in range(len(SIDES)):
        tiles = [Tile(centre.x + _DX[slot] * r, centre.z + _DZ[slot] * r, centre.level) for r in radii]
        choices.append([p for p in tiles if usable(p)])
    ranged = phase == 'ranged'

    def choose(tiles):
        if len(tiles) == 4:
            return tiles
        for tile in choices[len(tiles)]:
            if ranged and any([near(p, tile, 5) for p in tiles]):
                continue
            result = choose(tiles + [tile])
            if result is not None:
                return result
        return None

    return choose([])


def combat_mode(phase, styles):
    """The combat mode a phase fights in: rapid for the bow, the aggressive style for the mace. styles is
    game.combat_styles(), (mode, label) pairs."""
    if phase == 'ranged':
        return parse_range_style('rapid')
    for mode, label in (styles or []):
        if 'aggressive' in label.lower():
            return mode
    return None


class Supplies:
    def __init__(self, hp=0, food=0, prayer=0, prayer_doses=0, escape=False, arrows=0):
        self.hp = hp
        self.food = food
        self.prayer = prayer
        self.prayer_doses = prayer_doses
        self.escape = escape
        self.arrows = arrows


def retreat_reason(s):
    if s.food <= 1:
        return 'food reserve reached'
    if s.prayer <= 10 and s.prayer_doses == 0:
        return 'prayer reserve exhausted'
    if not s.escape:
        return 'escape supplies missing'
    if s.arrows == 0:
        return 'out of arrows'
    return None

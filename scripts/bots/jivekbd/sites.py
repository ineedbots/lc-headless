"""JiveKBD's lair and the way to it: rs2b0t's scripts/JiveKBD/sites.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.hunting.sites import DragonSite, in_box


class LocStop:
    """A loc to use on the way: its tile, how far from it the op may be sent (0 stands on it, 1 beside it), its id
    and its op."""

    def __init__(self, tile, radius, loc_id, op):
        self.tile = tile
        self.radius = radius
        self.loc_id = loc_id
        self.op = op


class LairRoute:
    """The way into the lair and the way back out on foot."""

    def __init__(self, ladder=None, dungeon_arrival=None, lever=None, lair_arrival=None, out_lever=None, dungeon_return=None, up_ladder=None,
                 surface=None, in_dungeon=None):
        self.ladder = ladder
        self.dungeon_arrival = dungeon_arrival
        self.lever = lever
        self.lair_arrival = lair_arrival
        self.out_lever = out_lever
        self.dungeon_return = dungeon_return
        self.up_ladder = up_ladder
        self.surface = surface
        self._in_dungeon = in_dungeon

    def in_dungeon(self, tile):
        return self._in_dungeon(tile)


_EDGEVILLE_BANK = Tile(3094, 3493, 0)

# Why: the alcove is walled on the south and open only north, and no five-wide footprint fits on the row beside it,
# so the dragon reaches row 9803 and never adjacency. The derivation's one other melee-proof tile, (2714, 9830), sits
# by the ice spiders and is left out.
# Why: the dragon breathes at anything it can see within 15 tiles, capped at 15 by the shield, so ranged_threat keeps
# the ladder from reading each breath as a bad tile.
KBD_LAIR = DragonSite(
    key='kbd-lair',
    label='King Black Dragon lair',
    target='King black dragon',
    bones='Dragon bones',
    safespots=[Tile(2717, 9801, 0), Tile(2716, 9801, 0)],
    melee_anchor=Tile(2714, 9829, 0),
    bank=_EDGEVILLE_BANK,
    escape_teleport_id='varrock',
    walk_out=_EDGEVILLE_BANK,
    fire_at_range=True,
    ranged_threat=True,
    in_area=in_box(2688, 2751, 9792, 9855, 0),
)

# Why: both levers are straight wall decorations, which the server only lets a player use from the tile they sit on;
# each teleport lands you on the tile north of the other lever.
KBD_ROUTE = LairRoute(
    ladder=LocStop(Tile(3017, 3849, 0), 1, 1765, 'Climb-down'),
    dungeon_arrival=Tile(3069, 10255, 0),
    lever=LocStop(Tile(3067, 10253, 0), 0, 1816, 'Pull'),
    lair_arrival=Tile(2717, 9802, 0),
    out_lever=LocStop(Tile(2717, 9801, 0), 0, 1817, 'Pull'),
    dungeon_return=Tile(3067, 10254, 0),
    up_ladder=LocStop(Tile(3069, 10256, 0), 1, 1766, 'Climb-up'),
    surface=Tile(3016, 3849, 0),
    in_dungeon=in_box(3008, 3071, 10240, 10303, 0),
)

KBD_SITES = {KBD_LAIR.key: KBD_LAIR}

SITE_OPTIONS = list(KBD_SITES.keys())


def site_for(key):
    site = KBD_SITES.get(key)
    return site if site is not None else KBD_LAIR

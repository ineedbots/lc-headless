# ---- api/ai/quests/defs/upass/doors.ts
"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/doors.ts (MIT, see thirdparty/rs2b0t). A ts2py draft: fix what's
marked "ts2py:", then this line."""

from rs2004.geometry import Tile

__all__ = ['door_across', 'door_stands', 'MUD_CAGE', 'MUD_CELL', 'mud_cell_door']

# Why: `~open_and_close_door2` crosses a WALL_STRAIGHT edge only from the railing tile or the tile opposite it.
# Why: the pairs are the map's angles run through `~door_open`: `^loc_west` 0 gives (-1,0), `^loc_north` 1 gives (0,1), `^loc_east` 2 gives (1,0), `^loc_south` 3 gives (0,-1). The collision pack agrees each pair joins 2 pockets.
def key(tile):
    return f'{tile.x},{tile.z},{tile.level}'


def pair(at, across):
    return [key(at), across]


ACROSS = {_k: _v for _k, _v in [
    pair(Tile(2381, 9655, 0), Tile(2381, 9654, 0)),
    pair(Tile(2384, 9655, 0), Tile(2384, 9654, 0)),
    pair(Tile(2387, 9655, 0), Tile(2387, 9654, 0)),
    pair(Tile(2390, 9655, 0), Tile(2390, 9654, 0)),
    pair(Tile(2393, 9655, 0), Tile(2393, 9654, 0)),
    pair(Tile(2381, 9656, 0), Tile(2381, 9657, 0)),
    pair(Tile(2384, 9656, 0), Tile(2384, 9657, 0)),
    pair(Tile(2387, 9656, 0), Tile(2387, 9657, 0)),
    pair(Tile(2390, 9656, 0), Tile(2390, 9657, 0)),
    pair(Tile(2393, 9656, 0), Tile(2393, 9657, 0)),
    pair(Tile(2380, 9619, 0), Tile(2381, 9619, 0)),
    pair(Tile(2404, 9620, 0), Tile(2403, 9620, 0)),
]}


def door_across(at):
    """The tile a railing's edge runs against, or null where the loc is not one of them."""
    _v1 = ACROSS.get(key(at))
    return (_v1 if _v1 is not None else None)


def door_stands(at):
    """The only tiles a railing may be operated from: its own tile to go through, the tile across it to come back."""
    across = door_across(at)
    return ([] if across is None else [at, across])


# Why: 9 of the 10 slave cages open onto a 7 to 14 tile dead end. The mud at (2393,9650) is the only way south and sits in the cell behind (2393,9655) alone, and by distance no search can tell that cage from its 9 neighbours.
MUD_CAGE = Tile(2393, 9655, 0)
MUD_CELL = Tile(2393, 9651, 0)


def mud_cell_door(at):
    """Where a cage lands you, for the one cage whose cell is worth entering."""
    return ([MUD_CELL] if at.x == MUD_CAGE.x and at.z == MUD_CAGE.z and at.level == MUD_CAGE.level else [])


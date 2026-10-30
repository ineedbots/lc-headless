"""Scorpion Catcher's way out of Velrak's cell, which a live run found 6 tiles from the door after following him."""

from rs2004 import execution
from rs2004.entities import locs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.quests.defs.scorpcatcher.areas import SC_ID, SC_TILE
from rs2004.quests.defs.scorpcatcher.dungeon import leave_cell


class Cell:
    def __init__(self):
        self.here = Tile(2932, 9684, 0)
        self.walks = []
        self.door = Fake(id=SC_ID.JAIL_DOOR, name='Door', actions=lambda: ['Open'], distance=self.door_distance, interact=self.open)

    def tile(self):
        return self.here

    def door_distance(self):
        return max(abs(self.here.x - SC_TILE.JAIL_DOOR.x), abs(self.here.z - SC_TILE.JAIL_DOOR.z))

    def walk_to(self, dest, radius=2, timeout_ms=45000, run=False):
        self.walks.append(dest)
        self.here = dest
        return True
        yield

    def open(self, op):
        self.here = SC_TILE.JAIL_DOOR
        return True


def steps_to_the_door_first():
    cell = Cell()
    spy_on(game, 'tile', cell.tile)
    spy_on(direct_navigator, 'walk_to', cell.walk_to)
    spy_on(locs, 'query', querying(lambda: [cell.door]))
    patch(execution, 'delay_ticks', instant_ticks)
    patch(execution, 'delay_until', instant_until)
    expect(cell.door_distance()).to_be(6)
    left = yield from leave_cell(lambda message: None)
    expect(left).to_be(True)
    expect(cell.walks).to_equal([SC_TILE.JAIL_CELL])
    expect(cell.here).to_equal(SC_TILE.JAIL_DOOR)


test('leaves the cell from beside Velrak by stepping to the door before opening it', steps_to_the_door_first)


def pockets():
    from rs2004.quests.defs.scorpcatcher import scorpcatcher
    from rs2004.quests.defs.scorpcatcher.dungeon import locked_in
    expect(scorpcatcher.resume_at).to_be(locked_in)
    expect(locked_in(Tile(2932, 9684, 0))).to_be(True)
    expect(locked_in(SC_TILE.SECRET_ROOM)).to_be(True)
    expect(locked_in(SC_TILE.JAIL_DOOR)).to_be(False)
    expect(locked_in(SC_TILE.BANK)).to_be(False)


test("a restart in Velrak's cell or past the dusty-key gate resumes there before any banking", pockets)

"""Sheep Herder's scene grid, which a live run found outrunning the script's step budget when every route search asked
the client for each tile again."""

from rs2004.navigation import reachability
from rs2004.quests.defs.sheepherder.herd import SceneGrid


def asks_each_tile_once():
    walks = spy_on(reachability, 'walkable', returns=True)
    steps = spy_on(reachability, 'can_step', returns=False)
    grid = SceneGrid()
    for i in range(3):
        expect(grid.walkable(2600, 3350)).to_be(True)
        expect(grid.can_step(2600, 3350, 0, -1)).to_be(False)
    expect(grid.can_step(2600, 3350, 1, 0)).to_be(False)
    expect(len(walks.calls)).to_be(1)
    expect(len(steps.calls)).to_be(2)
    grid.reset()
    grid.walkable(2600, 3350)
    expect(len(walks.calls)).to_be(2)


test('the scene grid asks the client once per tile and direction until reset', asks_each_tile_once)

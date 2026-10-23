# rs2004.random_events: the random-event handler's pure helpers. See docs/scripting/upkeep.md.

from __builtins__ import Tile

def step_off_candidates(here: Tile, away: Tile) -> list[Tile]: ...

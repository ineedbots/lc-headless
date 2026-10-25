# rs2004.quests.strike_combat: fighting with Strike spells from cover. See docs/scripting/quests.md.

from typing import Callable, Optional

from __builtins__ import Npc, Tile, Wait

ARENA_COVER: Tile
ARENA_LURE: list[Tile]
DEMON_COVER: Tile
EXPERIMENT_COVER: Tile
EXPERIMENT_TRAP: Tile

def at_cover(tile: Tile) -> bool: ...
def cast_from_cover(spot: Tile, target: Npc) -> bool: ...
def ready_strikes(log: Callable[[str], None]) -> Wait[bool]: ...
def take_strike_cover(spot: Tile, log: Callable[[str], None], lure_target: Optional[Callable[[], Optional[Npc]]] = None) -> Wait[bool]: ...
def cast_strike(spot: Tile, target: Npc, log: Callable[[str], None]) -> Wait[bool]: ...

# Earn a stranded traveller's boat fare, preserving the pack and yielding to events.
from typing import Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.routeplan import MissingItem

def missing_boat_fare(from_: Optional[Tile], dest: Tile, coins: int, missing: list[MissingItem]) -> bool: ...
def recover_boat_fare(dest: Tile, missing: list[MissingItem], log: Callable[[str], None]) -> Wait[bool]: ...

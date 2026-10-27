# Garlic from Morgan's upstairs cupboard. Each climb or Open takes one pass.
from typing import Callable
from __builtins__ import Tile, Wait

GARLIC: str
MORGAN_STAIRS_TOP: Tile

def take_garlic(log: Callable[[str], None]) -> Wait[bool]: ...

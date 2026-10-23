# rs2004.quests.exec.prompts: answering what locs and doors ask. See docs/scripting/quests.md.

from typing import Any, Callable, Optional, Sequence

from __builtins__ import Loc, Pattern, Tile, Wait

Log = Callable[[str], None]

DOOR_MS: int
DIALOG_MS: int
DOOR_WALK_MS: int

def held_id(id: int) -> int: ...
def loc_near(name: str, op: str, within: int = 12) -> Optional[Loc]: ...
def settle_scene() -> Wait[None]: ...
def drive_choice(prefer: Sequence[str], log: Log) -> Wait[bool]: ...
def drive_until(expect: Callable[[], bool], prefer: Sequence[str], log: Log, ms: int = 30000) -> Wait[bool]: ...
def drive_boxes(expect: Callable[[], bool], ms: int, prefer: Optional[Sequence[str]] = None, log: Optional[Log] = None) -> Wait[bool]: ...
def clear_boxes(max_boxes: int = 8) -> Wait[None]: ...

class DoorCrossing:
    id: int
    stand: Tile
    is_far: Callable[[], bool]
    log: Log
    prefer: Optional[list[str]]
    name: Optional[str]
    op: Optional[str]
    use_item: Optional[int]
    stand_radius: Optional[int]
    def __init__(self, id: int, stand: Tile, is_far: Callable[[], bool], log: Log, prefer: Optional[Sequence[str]] = None, name: Optional[str] = None, op: Optional[str] = None, use_item: Optional[int] = None, stand_radius: Optional[int] = None) -> None: ...

def cross_teleport_door(door: Any) -> Wait[bool]: ...

class LocPrompt:
    name: str
    op: str
    near: Tile
    expect: Callable[[], bool]
    prefer: Optional[list[str]]
    expect_ms: Optional[int]
    within: Optional[int]
    id: Optional[int]
    refused: Optional[Pattern]
    def __init__(self, name: str, op: str, near: Tile, expect: Callable[[], bool], prefer: Optional[Sequence[str]] = None, expect_ms: Optional[int] = None, within: Optional[int] = None, id: Optional[int] = None, refused: Optional[Pattern] = None) -> None: ...

def prompt_loc(step: Any, log: Log) -> Wait[bool]: ...
def use_on_loc(item_id: int, loc: Any, prefer: Sequence[str], expect: Callable[[], bool], log: Log) -> Wait[bool]: ...

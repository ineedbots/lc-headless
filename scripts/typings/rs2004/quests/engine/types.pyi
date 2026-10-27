# rs2004.quests.engine.types: what a quest module reads and answers. See docs/scripting/quests.md.

from typing import Any, Callable, Mapping, Optional

from __builtins__ import Tile
from rs2004.quests.exec.primitives import LadderHop
from rs2004.quests.types import QuestRecord

class QuestProgress:
    stage: int
    flags: set[str]
    def __init__(self, stage: int = 0, flags: Optional[set[str]] = None) -> None: ...

def has_flag(progress: Optional[QuestProgress], name: str) -> bool: ...
def flag_value(progress: Optional[QuestProgress], name: str) -> Optional[int]: ...

class QuestSnapshot:
    FIELDS: list[str]
    journal: str
    inv: dict[str, int]
    inv_ids: Optional[dict[int, int]]
    worn: set[str]
    worn_ids: Optional[set[int]]
    no_progress: int
    bank_coins: int
    stage: Optional[int]
    progress: Optional[QuestProgress]
    bank: Optional[dict[str, int]]
    bank_ids: Optional[dict[int, int]]
    bank_known: Optional[bool]
    tile: Optional[Tile]
    prayer: Optional[int]
    attack: Optional[int]
    ranged: Optional[int]
    magic: Optional[int]
    free_slots: Optional[int]
    combat_xp: Optional[int]
    def __init__(self, journal: str = 'unknown', inv: Optional[dict[str, int]] = None, inv_ids: Optional[dict[int, int]] = None,
                 worn: Optional[set[str]] = None, worn_ids: Optional[set[int]] = None, no_progress: int = 0, bank_coins: int = 0,
                 stage: Optional[int] = None, progress: Optional[QuestProgress] = None, bank: Optional[dict[str, int]] = None,
                 bank_ids: Optional[dict[int, int]] = None, bank_known: Optional[bool] = None, tile: Optional[Tile] = None,
                 prayer: Optional[int] = None, attack: Optional[int] = None, ranged: Optional[int] = None, magic: Optional[int] = None,
                 free_slots: Optional[int] = None, combat_xp: Optional[int] = None) -> None: ...
    def with_fields(self, changes: Mapping[str, Any]) -> QuestSnapshot: ...

def held_id(snap: QuestSnapshot, id: int) -> int: ...
def banked_id(snap: QuestSnapshot, id: int) -> int: ...
def quest_step(kind: str, **fields: Any) -> Any: ...

class QuestPrayer:
    protect: str
    potions: Optional[int]
    def __init__(self, protect: str = 'melee', potions: Optional[int] = None) -> None: ...

class QuestSustain:
    foods: list[str]
    eat_below_hp: float
    def __init__(self, foods: Optional[list[str]] = None, eat_below_hp: float = 0.5) -> None: ...

class QuestModule:
    record: QuestRecord
    decide: Callable[[QuestSnapshot], Any]
    on_start: Optional[Callable[[], None]]
    hops: Optional[list[LadderHop]]
    bank: Any
    grind: Optional[list[str]]
    food: Optional[int]
    gather: Optional[dict[str, Callable[[QuestSnapshot, int], Any]]]
    tools: Optional[list[str] | Callable[[], list[str]]]
    exit: Optional[Callable[[Callable[[str], None]], Any]]
    owns_inventory: bool
    food_ready: Optional[Callable[[QuestSnapshot], bool]]
    read_stage: Optional[Callable[[], Any]]
    read_progress: Optional[Callable[[], Any]]
    sustain: Optional[QuestSustain]
    pray: Optional[QuestPrayer]
    coin_float: Optional[int]
    warn_readiness: Optional[Callable[[], Optional[str]]]
    observe: Optional[Callable[[QuestSnapshot, Any], list[str]]]
    def __init__(self, record: Any = None, decide: Any = None, on_start: Any = None, hops: Any = None, bank: Any = None, grind: Any = None,
                 food: Any = None, gather: Any = None, tools: Any = None, exit: Any = None, owns_inventory: bool = False, food_ready: Any = None,
                 read_stage: Any = None, read_progress: Any = None, sustain: Any = None, pray: Any = None, coin_float: Any = None,
                 warn_readiness: Any = None, observe: Any = None) -> None: ...

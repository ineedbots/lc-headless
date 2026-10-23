# rs2004.quests.prayer: holding a quest's protection prayer. See docs/scripting/quests.md.

from typing import Any, Callable, Optional

from __builtins__ import Wait

PRAYER_FLOOR: int
PROTECT_LEVEL: dict[str, int]
PROTECTION_NAME: dict[str, str]
PRAYER_POTION: str
PRAYER_POTION_IDS: list[int]

def prayer_upkeep_action(in_combat: bool, protect_active: bool, protect_available: bool, points: int, doses: int) -> str: ...
def protection_name(pray: Any) -> str: ...
def protection_level(pray: Any) -> int: ...

class _QuestPrayerState:
    current: Any
    warned: bool
    log: Optional[Callable[[str], None]]

quest_prayer_state: _QuestPrayerState

def set_quest_prayer(pray: Any, log: Optional[Callable[[str], None]]) -> None: ...
def prayer_upkeep() -> Wait[bool]: ...

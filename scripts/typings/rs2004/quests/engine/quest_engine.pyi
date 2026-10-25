# rs2004.quests.engine.quest_engine: the quest engine, a Task. Its host is the bot driving it. See
# docs/scripting/quests.md.

from typing import Any, Optional

from __builtins__ import Task, Tile, Wait

PROVISION_BANK: Tile
COIN_FLOAT: int

def describe_step(step: Any) -> str: ...

class QuestEngine(Task):
    host: Any
    running_id: Optional[str]
    def __init__(self, host: Any) -> None: ...
    def validate(self) -> bool: ...
    def execute(self) -> Wait[None]: ...

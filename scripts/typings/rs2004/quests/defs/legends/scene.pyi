from typing import Any, Callable, Optional, Sequence
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestModule, QuestProgress, QuestSnapshot

def offer_to(item_id: Any, npc: Any, log: Any) -> Wait[Any]: ...
def here() -> Any: ...
def drive_to_end(prefer: Any, log: Any, ms: Any = ..., required: Any = ...) -> Wait[Any]: ...
def modal_text() -> Any: ...
def said_any(text: Any, needles: Any) -> Any: ...
from rs2004.quests.exec.prompts import clear_boxes as clear_boxes
from rs2004.quests.exec.prompts import drive_boxes as drive_boxes
from rs2004.quests.exec.prompts import drive_choice as drive_choice
from rs2004.quests.exec.prompts import drive_until as drive_until
from rs2004.quests.exec.prompts import held_id as held_id
from rs2004.quests.exec.prompts import loc_near as loc_near
from rs2004.quests.exec.prompts import prompt_loc as prompt_loc
from rs2004.quests.exec.prompts import settle_scene as settle_scene
from rs2004.quests.exec.prompts import use_on_loc as use_on_loc

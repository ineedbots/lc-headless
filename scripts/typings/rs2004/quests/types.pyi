# rs2004.quests.types: the quest records and what eligibility reads and gives. See docs/scripting/quests.md.

from typing import Optional

class SkillReq:
    skill: str
    level: int
    def __init__(self, skill: str = '', level: int = 0) -> None: ...

class QuestRequirements:
    min_quest_points: Optional[int]
    skills: Optional[list[SkillReq]]
    quests: Optional[list[str]]
    def __init__(self, min_quest_points: Optional[int] = None, skills: Optional[list[SkillReq]] = None, quests: Optional[list[str]] = None) -> None: ...

class QuestItem:
    name: str
    qty: int
    kind: str
    def __init__(self, name: str = '', qty: int = 1, kind: str = 'acquirable') -> None: ...

class QuestRecord:
    id: str
    name: str
    quest_points: int
    requirements: QuestRequirements
    items: list[QuestItem]
    def __init__(self, id: str = '', name: str = '', quest_points: int = 0, requirements: Optional[QuestRequirements] = None, items: Optional[list[QuestItem]] = None) -> None: ...

class PlayerState:
    quest_points: int
    skill_levels: dict[str, int]
    completed_quests: set[str]
    def __init__(self, quest_points: int = 0, skill_levels: Optional[dict[str, int]] = None, completed_quests: Optional[set[str]] = None) -> None: ...

class BankInventorySnapshot:
    counts: dict[str, int]
    bank_known: Optional[bool]
    def __init__(self, counts: Optional[dict[str, int]] = None, bank_known: Optional[bool] = None) -> None: ...

class QuestEligibility:
    id: str
    name: str
    status: str
    reasons: list[str]
    def __init__(self, id: str = '', name: str = '', status: str = 'READY', reasons: Optional[list[str]] = None) -> None: ...

class RequirementResult:
    ok: bool
    reason: str
    def __init__(self, ok: bool = True, reason: str = '') -> None: ...

class ItemResult:
    name: str
    qty: int
    kind: str
    present: int
    ok: bool
    will_gather: bool
    def __init__(self, name: str = '', qty: int = 0, kind: str = 'acquirable', present: int = 0, ok: bool = True, will_gather: bool = False) -> None: ...

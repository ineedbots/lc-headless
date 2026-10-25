"""The quest records and what eligibility reads and gives: rs2b0t's api/ai/quests/types.ts (MIT, see
thirdparty/rs2b0t). Each is a plain value, equal to another of its kind when every field is."""

__all__ = [
    'SkillReq', 'QuestRequirements', 'QuestItem', 'QuestRecord', 'PlayerState', 'BankInventorySnapshot',
    'QuestEligibility', 'RequirementResult', 'ItemResult',
]


class _Value:
    FIELDS = []

    def __eq__(self, other):
        if type(other) is not type(self):
            return False
        for name in self.FIELDS:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        fields = ', '.join([f'{name}={repr(getattr(self, name))}' for name in self.FIELDS])
        return f'{type(self).__name__}({fields})'


class SkillReq(_Value):
    FIELDS = ['skill', 'level']

    def __init__(self, skill='', level=0):
        self.skill = skill
        self.level = level


class QuestRequirements(_Value):
    """What a quest asks before it starts. Each part is None when the quest doesn't ask it."""
    FIELDS = ['min_quest_points', 'skills', 'quests']

    def __init__(self, min_quest_points=None, skills=None, quests=None):
        self.min_quest_points = min_quest_points
        self.skills = skills
        self.quests = quests


class QuestItem(_Value):
    """An item a quest uses. kind is 'mustHave', which the account must bring, or 'acquirable', which the quest
    gathers."""
    FIELDS = ['name', 'qty', 'kind']

    def __init__(self, name='', qty=1, kind='acquirable'):
        self.name = name
        self.qty = qty
        self.kind = kind


class QuestRecord(_Value):
    """A quest: its id, its name as the quest list shows it, its quest points, requirements and items."""
    FIELDS = ['id', 'name', 'quest_points', 'requirements', 'items']

    def __init__(self, id='', name='', quest_points=0, requirements=None, items=None):
        self.id = id
        self.name = name
        self.quest_points = quest_points
        self.requirements = requirements if requirements is not None else QuestRequirements()
        self.items = items if items is not None else []


class PlayerState(_Value):
    """Quest points, levels by skill name, and the ids of the quests complete."""
    FIELDS = ['quest_points', 'skill_levels', 'completed_quests']

    def __init__(self, quest_points=0, skill_levels=None, completed_quests=None):
        self.quest_points = quest_points
        self.skill_levels = skill_levels if skill_levels is not None else {}
        self.completed_quests = completed_quests if completed_quests is not None else set()


class BankInventorySnapshot(_Value):
    """Item counts across the pack and the bank, by lower-case name. bank_known is False until a bank has been
    read, since an unread bank isn't an empty one."""
    FIELDS = ['counts', 'bank_known']

    def __init__(self, counts=None, bank_known=None):
        self.counts = counts if counts is not None else {}
        self.bank_known = bank_known


class QuestEligibility(_Value):
    """status is 'DONE', 'READY' or 'BLOCKED', with the reasons it's blocked."""
    FIELDS = ['id', 'name', 'status', 'reasons']

    def __init__(self, id='', name='', status='READY', reasons=None):
        self.id = id
        self.name = name
        self.status = status
        self.reasons = reasons if reasons is not None else []


class RequirementResult(_Value):
    FIELDS = ['ok', 'reason']

    def __init__(self, ok=True, reason=''):
        self.ok = ok
        self.reason = reason


class ItemResult(_Value):
    FIELDS = ['name', 'qty', 'kind', 'present', 'ok', 'will_gather']

    def __init__(self, name='', qty=0, kind='acquirable', present=0, ok=True, will_gather=False):
        self.name = name
        self.qty = qty
        self.kind = kind
        self.present = present
        self.ok = ok
        self.will_gather = will_gather

"""The quest records: rs2b0t's api/ai/quests/data/quests.ts (MIT, see thirdparty/rs2b0t), generated into
rs2004.catalogs._quests by tools/catalogs/export_rs2b0t.ts. All 63 journal quests, whether or not a module runs
them yet, so a prerequisite reads complete either way."""

from rs2004.catalogs._quests import QUESTS as _ROWS
from rs2004.quests.types import QuestItem, QuestRecord, QuestRequirements, SkillReq

__all__ = ['QUESTS', 'quest_record']


def _record(row):
    req = row['requirements']
    skills = req.get('skills')
    requirements = QuestRequirements(
        req.get('min_quest_points'),
        [SkillReq(s['skill'], s['level']) for s in skills] if skills is not None else None,
        req.get('quests'),
    )
    items = [QuestItem(i['name'], i['qty'], i['kind']) for i in row['items']]
    return QuestRecord(row['id'], row['name'], row['quest_points'], requirements, items)


QUESTS = [_record(row) for row in _ROWS]


def quest_record(id):
    """The record with this id, or None."""
    for record in QUESTS:
        if record.id == id:
            return record
    return None

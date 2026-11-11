"""Prerequisite and quest point expansion from rs2b0t's questSelection.ts (MIT, see thirdparty/rs2b0t)."""


def plan_quest_selection(selected, excluded, records, completed, points):
    picked = set(selected)
    by_id = {record.id: record for record in records}
    pending = list(picked)
    processed = set()
    while pending:
        id = pending.pop(0)
        if id in processed or id not in by_id:
            continue
        processed.add(id)
        record = by_id[id]
        candidates = list(record.requirements.quests or [])
        for skill in record.requirements.skills or []:
            if skill.skill == 'herblore':
                candidates.append('druid')
            if skill.skill == 'runecraft':
                candidates.append('runemysteries')
        required = record.requirements.min_quest_points or 0
        projected = points + sum([r.quest_points for r in records if r.id in picked and r.id not in completed and (r.requirements.min_quest_points or 0) < required])
        for candidate in records:
            if projected >= required:
                break
            if candidate.id in picked or candidate.id in excluded or candidate.id in completed or (candidate.requirements.min_quest_points or 0) >= required:
                continue
            candidates.append(candidate.id)
            projected += candidate.quest_points
        for candidate in candidates:
            if candidate in picked or candidate in excluded or candidate in completed or candidate not in by_id:
                continue
            picked.add(candidate)
            pending.append(candidate)
    return picked

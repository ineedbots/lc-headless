"""Whether a quest can start: rs2b0t's api/ai/quests/EligibilityEvaluator.ts, RequirementChecker.ts and
ItemChecker.ts (MIT, see thirdparty/rs2b0t). Pure, over a PlayerState and a BankInventorySnapshot."""

from rs2004.quests.types import ItemResult, QuestEligibility, RequirementResult

__all__ = ['check_requirements', 'check_items', 'evaluate', 'evaluate_all']


def _skill_label(skill):
    return skill if len(skill) == 0 else skill[0].upper() + skill[1:]


def check_requirements(record, player):
    """One RequirementResult per gate, in order: quest points, skills, quests."""
    out = []
    req = record.requirements
    if req.min_quest_points is not None:
        ok = player.quest_points >= req.min_quest_points
        out.append(RequirementResult(ok, '' if ok else f'needs {req.min_quest_points} quest points (have {player.quest_points})'))
    for s in req.skills or []:
        have = player.skill_levels.get(s.skill, 0)
        ok = have >= s.level
        out.append(RequirementResult(ok, '' if ok else f'needs {_skill_label(s.skill)} {s.level} (have {have})'))
    for q in req.quests or []:
        ok = q in player.completed_quests
        out.append(RequirementResult(ok, '' if ok else f'prerequisite quest not complete: {q}'))
    return out


def _have(snapshot, name):
    wanted = name.lower()
    for key, value in snapshot.counts.items():
        if key.lower() == wanted:
            return value
    return 0


def check_items(record, snapshot):
    """One ItemResult per item the record names."""
    out = []
    for item in record.items:
        present = _have(snapshot, item.name)
        if item.kind == 'mustHave':
            # Why: the bank is read only after a quest starts, so blocking on an unread one stopped the queue before it
            # ever opened a booth.
            ok = present >= item.qty or snapshot.bank_known is False
            out.append(ItemResult(item.name, item.qty, item.kind, present, ok, False))
        else:
            out.append(ItemResult(item.name, item.qty, item.kind, present, True, present < item.qty))
    return out


def evaluate(record, player, snapshot, journal_status):
    """The quest's QuestEligibility, given its journal status as quests.status reads it."""
    if journal_status == 'complete':
        return QuestEligibility(record.id, record.name, 'DONE', [])
    reasons = []
    for r in check_requirements(record, player):
        if not r.ok:
            reasons.append(r.reason)
    # Why: item requirements gate starting a quest; re-imposing them mid-quest blocks resuming, since the items may be
    # gone (handed over, ground up, drunk).
    # Why: past the start, the module's decide() sources what it still needs.
    # Why: the requirements above are checked either way, as nothing consumes a skill level or a quest point.
    if journal_status != 'in_progress':
        for it in check_items(record, snapshot):
            if not it.ok:
                reasons.append(f'missing item: {it.name} x{it.qty} (have {it.present})')
    return QuestEligibility(record.id, record.name, 'READY' if len(reasons) == 0 else 'BLOCKED', reasons)


def evaluate_all(records, player, snapshot, status_of):
    return [evaluate(r, player, snapshot, status_of(r.name)) for r in records]

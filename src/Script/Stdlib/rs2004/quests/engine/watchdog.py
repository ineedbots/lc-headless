"""The no-progress watchdog: rs2b0t's api/ai/quests/engine/watchdog.ts (MIT, see thirdparty/rs2b0t). A step that
changes nothing the snapshot shows makes no progress, and a quest that makes none for long enough is parked."""

__all__ = ['NO_PROGRESS_WARN', 'NO_PROGRESS_PARK', 'progress_signature', 'ProgressWatchdog']

NO_PROGRESS_WARN = 3
NO_PROGRESS_PARK = 8


def _number_key(entry):
    return entry[0]


def progress_signature(snap):
    """Everything about a snapshot that a step can move, as one string."""
    items = ','.join([f'{n}:{snap.inv[n]}' for n in sorted(list(snap.inv.keys()))])
    item_ids = ''
    if snap.inv_ids is not None:
        item_ids = ','.join([f'{id}:{c}' for id, c in sorted(list(snap.inv_ids.items()), key=_number_key)])
    worn = ','.join(sorted(list(snap.worn)))
    worn_ids = ','.join([str(id) for id in sorted(list(snap.worn_ids or []))])
    tile = f'{snap.tile.x},{snap.tile.z},{snap.tile.level}' if snap.tile is not None else '?'
    # Why: journal sub-progress counts as progress, since reading a scroll or searching a lock moves nothing else.
    # Why: without it such a step burns the no-progress budget on its way to being parked.
    flags = ','.join(sorted(list(snap.progress.flags))) if snap.progress is not None else ''
    stage = snap.stage if snap.stage is not None else '?'
    head = f'{snap.journal}|stage:{stage}|flags:{flags}|tile:{tile}|inv:{items}|invIds:{item_ids}'
    return head + f'|worn:{worn}|wornIds:{worn_ids}|combatXp:{snap.combat_xp or 0}'


class ProgressWatchdog:
    """Counts the steps in a row whose signature didn't change."""

    def __init__(self):
        self.last = ''
        self.count = 0

    def note(self, signature):
        """After a step that worked: the count of unchanged signatures."""
        if signature != self.last:
            self.last = signature
            self.count = 0
        else:
            self.count += 1
        return self.count

    def note_failure(self, before, after):
        """After a step that failed: counts it when it left the snapshot as it found it."""
        if before != self.last:
            self.count = 0
        self.last = after
        self.count = self.count + 1 if before == after else 0
        return self.count

    def reset(self):
        self.last = ''
        self.count = 0

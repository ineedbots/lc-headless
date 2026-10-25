"""Which quest runs next, and the queue's rows: rs2b0t's api/ai/quests/engine/queue.ts (MIT, see thirdparty/rs2b0t)."""

__all__ = ['QueueRow', 'next_quest', 'queue_rows']


class QueueRow:
    """A quest in the queue: status is 'DONE', 'RUNNING', 'READY', 'PARKED', 'BLOCKED' or 'UNKNOWN', with why."""

    def __init__(self, id='', name='', status='UNKNOWN', reasons=None):
        self.id = id
        self.name = name
        self.status = status
        self.reasons = reasons if reasons is not None else []

    def __repr__(self):
        return f'QueueRow({repr(self.id)}, {repr(self.status)}, {repr(self.reasons)})'


def next_quest(order, picked, elig, parked):
    """The first picked quest that's READY and not parked; else the first READY one; else None."""
    ready = [id for id in order if id in picked and elig.get(id) is not None and elig[id].status == 'READY']
    for id in ready:
        if id not in parked:
            return id
    return ready[0] if len(ready) > 0 else None


def queue_rows(order, picked, elig, parked, running_id):
    rows = []
    for id in order:
        if id not in picked:
            continue
        el = elig.get(id)
        if id == running_id:
            rows.append(QueueRow(id, el.name if el is not None else id, 'RUNNING', []))
        elif el is None:
            rows.append(QueueRow(id, id, 'UNKNOWN', ['eligibility not evaluated yet']))
        elif id in parked and el.status == 'READY':
            rows.append(QueueRow(id, el.name, 'PARKED', ['no progress — parked']))
        else:
            rows.append(QueueRow(id, el.name, el.status, el.reasons))
    return rows

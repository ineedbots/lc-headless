"""rs2b0t's test/api/ai/quests/engine/skip-quest.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.execution import event_signal
from rs2004.quests.engine.queue import QueueRow, next_quest, queue_rows

def e(id, status, reasons=None):
    if reasons is None:
        reasons = []
    return [id, Record({'id': id, 'name': id.upper(), 'status': status, 'reasons': reasons})]


ORDER = ['runemysteries', 'doric', 'sheep', 'priest']


def after_user_skip(skipped_id, order, picked, elig, blocked):
    """Mirrors QuestEngine after a user Skip: the skipped id is blocked for the session and removed from the selectable set before nextQuest runs."""
    blocked[skipped_id] = ['skipped by user this session']
    selectable = set([id for id in list(picked) if not (id in blocked)])
    return next_quest(order, selectable, elig, set())


def _fn1():
    def _fn2():
        elig = {_k: _v for _k, _v in [e('runemysteries', 'READY'), e('doric', 'READY'), e('sheep', 'READY')]}
        blocked = {}
        next_ = after_user_skip('runemysteries', ORDER, set(ORDER), elig, blocked)
        expect(next_).to_be('doric')
        expect(blocked.get('runemysteries')).to_equal(['skipped by user this session'])
    test('skip stops the current quest and advances to the next READY', _fn2)

    def _fn3():
        elig = {_k: _v for _k, _v in [e('runemysteries', 'READY'), e('doric', 'READY')]}
        blocked = {}
        after_user_skip('runemysteries', ORDER, set(['runemysteries', 'doric']), elig, blocked)
        # even if nothing else is ready, the skipped id stays out of selectable
        only_skipped = next_quest(ORDER, set([id for id in ['runemysteries'] if not (id in blocked)]), elig, set())
        expect(only_skipped).to_be_null()
        # A park alone still returns the id; only the session block takes it out of selectable.
        expect(next_quest(ORDER, set(['runemysteries']), elig, set(['runemysteries']))).to_be('runemysteries')
    test('a skipped quest is never selected again this session', _fn3)

    def _fn4():
        elig = {_k: _v for _k, _v in [e('runemysteries', 'READY'), e('doric', 'READY')]}
        blocked = {_k: _v for _k, _v in [['runemysteries', ['skipped by user this session']]]}

        def mark(r):
            reasons = blocked.get(r.id)
            return QueueRow(r.id, r.name, 'BLOCKED', reasons) if reasons else r
        rows = [mark(_x) for _x in queue_rows(ORDER, set(['runemysteries', 'doric']), elig, set(), 'doric')]
        expect(([r for r in rows if r.id == 'runemysteries'] or [None])[0]).to_match_object(Record({'status': 'BLOCKED', 'reasons': ['skipped by user this session']}))
        expect((([r for r in rows if r.id == 'doric'] or [None])[0].status if ([r for r in rows if r.id == 'doric'] or [None])[0] is not None else None)).to_be('RUNNING')
    test('queue rows mark a skipped quest BLOCKED with the skip reason', _fn4)

    def _fn9():
        elig = {_k: _v for _k, _v in [e('doric', 'READY')]}
        # park fallback re-picks the only ready quest
        expect(next_quest(ORDER, set(['doric']), elig, set(['doric']))).to_be('doric')
        # session block leaves nothing to run
        expect(next_quest(ORDER, set(), elig, set())).to_be_null()
    test('skip is not the same as temporary park (park retries, skip does not)', _fn9)


describe('Skip quest (#432) session block', _fn1)


def _fn10():
    def _fn11():
        flags = {'main': False, 'extra': False}
        provider = event_signal._provider
        event_signal.set_provider(lambda: flags['main'])
        event_signal.set_interrupt(lambda: flags['extra'])
        expect(event_signal.pending()).to_be(False)
        flags['main'] = True
        expect(event_signal.pending()).to_be(True)
        flags['main'] = False
        flags['extra'] = True
        expect(event_signal.pending()).to_be(True)
        event_signal.set_interrupt(None)
        expect(event_signal.pending()).to_be(False)
        event_signal.set_provider(provider)
    test('setInterrupt ORs with the main provider', _fn11)


describe('EventSignal interrupt (#432 skip yields walks)', _fn10)

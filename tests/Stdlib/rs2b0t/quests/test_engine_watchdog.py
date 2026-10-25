"""rs2b0t's test/api/ai/quests/engine/watchdog.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.engine.watchdog import NO_PROGRESS_PARK, NO_PROGRESS_WARN, ProgressWatchdog, progress_signature


def snap(journal, items):
    return QuestSnapshot(journal=journal, inv={_k: _v for _k, _v in items}, worn=set(), no_progress=0, bank_coins=0)


def _fn1():
    def _fn2():
        expect(progress_signature(snap('in_progress', [['egg', 1], ['pot', 2]]))).to_be(progress_signature(snap('in_progress', [['pot', 2], ['egg', 1]])))
    test('same state -> same signature regardless of map insertion order', _fn2)

    def _fn3():
        base = progress_signature(snap('in_progress', [['egg', 1]]))
        expect(progress_signature(snap('complete', [['egg', 1]]))).not_.to_be(base)
        expect(progress_signature(snap('in_progress', [['egg', 2]]))).not_.to_be(base)
    test('journal or count change -> different signature', _fn3)

    def _fn4():
        base = snap('in_progress', [['knife', 1]])
        expect(progress_signature(base.with_fields({'stage': 2}))).not_.to_be(progress_signature(base.with_fields({'stage': 3})))
    test('quest-stage transitions count as progress even when inventory is unchanged', _fn4)

    def _fn7():
        base = snap('in_progress', [['knife', 1]])
        empty = progress_signature(base)
        first = progress_signature(base.with_fields({'worn': set(['bronze axe', 'dramen staff'])}))
        reordered = progress_signature(base.with_fields({'worn': set(['dramen staff', 'bronze axe'])}))
        expect(first).to_be(reordered)
        expect(first).not_.to_be(empty)
    test('equipment changes count as progress and worn ordering is stable', _fn7)

    def _fn10():
        base = snap('in_progress', [['a key', 1]])
        golrie = progress_signature(base.with_fields({'inv_ids': {293: 1, 954: 1}, 'worn_ids': set([295, 100])}))
        reordered = progress_signature(base.with_fields({'inv_ids': {954: 1, 293: 1}, 'worn_ids': set([100, 295])}))
        baxtorian = progress_signature(base.with_fields({'inv_ids': {298: 1, 954: 1}, 'worn_ids': set([295, 100])}))
        expect(golrie).to_be(reordered)
        expect(golrie).not_.to_be(baxtorian)
    test('same-named exact item changes count as progress and ID ordering is stable', _fn10)

    def _fn14():
        base = snap('in_progress', [['knife', 1]])
        a = base.with_fields({'tile': Record({'x': 3046, 'z': 3235, 'level': 0})})
        b = base.with_fields({'tile': Record({'x': 2834, 'z': 3334, 'level': 1})})
        expect(progress_signature(a)).not_.to_be(progress_signature(b))
    test('travel between quest areas counts as progress', _fn14)

    def _fn17():
        base = snap('in_progress', [['knife', 1]])
        before_scan = base.with_fields({'bank': {}, 'bank_known': False})
        after_scan = base.with_fields({'bank': {'dramen staff': 1}, 'bank_known': True})
        expect(after_scan.bank_known).to_be(True)
        expect(after_scan.bank.get('dramen staff')).to_be(1)
        expect(progress_signature(before_scan)).to_be(progress_signature(after_scan))
    test('bank-aware snapshot fields remain available without destabilizing the world signature', _fn17)


describe('progressSignature', _fn1)


def _fn20():
    def _fn21():
        w = ProgressWatchdog()
        expect(w.note_failure('ore:0', 'ore:0')).to_be(1)
        expect(w.note_failure('ore:0', 'ore:1')).to_be(0)
        expect(w.note_failure('ore:1', 'ore:1')).to_be(1)
    test('failed attempts count only unchanged observations', _fn21)

    def _fn22():
        w = ProgressWatchdog()
        w.note_failure('stage:0', 'stage:0')
        w.note_failure('stage:0', 'stage:0')
        expect(w.note_failure('stage:1', 'stage:1')).to_be(1)
    test('progress observed between failed attempts resets their budget', _fn22)

    def _fn23():
        w = ProgressWatchdog()
        w.note_failure('a', 'a')
        w.reset()
        expect(w.note_failure('a', 'a')).to_be(1)
    test('reset clears the failed-attempt budget', _fn23)

    def _fn24():
        w = ProgressWatchdog()
        expect(w.note('a')).to_be(0)
        expect(w.note('a')).to_be(1)
        expect(w.note('a')).to_be(2)
        expect(w.note('b')).to_be(0)
        expect(w.note('b')).to_be(1)
    test('unchanged signature counts up; change resets', _fn24)

    def _fn25():
        expect(NO_PROGRESS_WARN).to_be(3)
        expect(NO_PROGRESS_PARK).to_be(8)
    test('thresholds are 3 warn / 8 park (park must exceed the longest probe cycle — R&J needs 7)', _fn25)


describe('ProgressWatchdog', _fn20)


def with_flags(flags):
    return snap('in_progress', [['knife', 1]]).with_fields({'stage': 7, 'progress': QuestProgress(7, set(flags))})


def _fn26():
    def _fn28():
        # Reading a scroll or searching a lock moves nothing else at all. Without flags in the signature such a step
        # burns the no-progress budget.
        expect(progress_signature(with_flags(['read-tattered']))).not_.to_be(progress_signature(with_flags(['read-tattered', 'read-crumpled'])))
    test('a flag-only change counts as progress', _fn28)

    def _fn29():
        expect(progress_signature(with_flags(['b', 'a']))).to_be(progress_signature(with_flags(['a', 'b'])))
    test('the same flags in a different order are the same signature', _fn29)


describe('progressSignature — journal flags', _fn26)

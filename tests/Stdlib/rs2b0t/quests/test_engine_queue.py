"""rs2b0t's test/api/ai/quests/engine/queue.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs.record import Record
from rs2004.quests.engine.queue import next_quest, queue_rows

def e(id, status, reasons=None):
    if reasons is None:
        reasons = []
    return [id, Record({'id': id, 'name': id.upper(), 'status': status, 'reasons': reasons})]


ORDER = ['runemysteries', 'doric', 'sheep', 'priest']


def _fn1():
    def _fn2():
        elig = {_k: _v for _k, _v in [e('runemysteries', 'DONE'), e('doric', 'READY'), e('sheep', 'READY'), e('priest', 'BLOCKED', ['x'])]}
        expect(next_quest(ORDER, set(ORDER), elig, set())).to_be('doric')
    test('first READY in def order wins', _fn2)

    def _fn3():
        elig = {_k: _v for _k, _v in [e('doric', 'READY'), e('sheep', 'READY')]}
        expect(next_quest(ORDER, set(['sheep']), elig, set())).to_be('sheep')
    test('unpicked quests are invisible', _fn3)

    def _fn4():
        elig = {_k: _v for _k, _v in [e('doric', 'READY'), e('sheep', 'READY')]}
        expect(next_quest(ORDER, set(['doric', 'sheep']), elig, set(['doric']))).to_be('sheep')
        expect(next_quest(ORDER, set(['doric']), elig, set(['doric']))).to_be('doric')
    test('parked quests defer to unparked, then retry', _fn4)

    def _fn5():
        elig = {_k: _v for _k, _v in [e('doric', 'DONE'), e('sheep', 'BLOCKED', ['missing item'])]}
        expect(next_quest(ORDER, set(['doric', 'sheep']), elig, set())).to_be_null()
    test('nothing runnable -> null', _fn5)


describe('nextQuest', _fn1)


def _fn6():
    def _fn7():
        elig = {_k: _v for _k, _v in [e('runemysteries', 'DONE'), e('doric', 'READY'), e('sheep', 'READY'), e('priest', 'BLOCKED', ['qp'])]}
        rows = queue_rows(ORDER, set(['runemysteries', 'doric', 'sheep', 'priest']), elig, set(['sheep']), 'doric')
        expect([f'{r.id}:{r.status}' for r in rows]).to_equal(['runemysteries:DONE', 'doric:RUNNING', 'sheep:PARKED', 'priest:BLOCKED'])
        expect(rows[3].reasons).to_equal(['qp'])
    test('def order, picked only, RUNNING and PARKED stamped over eligibility', _fn7)


describe('queueRows', _fn6)

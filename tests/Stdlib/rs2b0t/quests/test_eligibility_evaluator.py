"""rs2b0t's test/api/ai/quests/eligibility-evaluator.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.types import BankInventorySnapshot
from rs2004.quests.data import QUESTS
from rs2004.quests.eligibility import evaluate, evaluate_all

def rec(over=None):
    if over is None:
        over = Record({})
    return Record({
        'id': (over.id if over.id is not None else 't'),
        'name': (over.name if over.name is not None else 'Test Quest'),
        'quest_points': (over.quest_points if over.quest_points is not None else 1),
        'requirements': (over.requirements if over.requirements is not None else Record({})),
        'items': (over.items if over.items is not None else []),
    })


def player(p=None):
    if p is None:
        p = Record({})
    return Record({
        'quest_points': (p.quest_points if p.quest_points is not None else 0),
        'skill_levels': (p.skill_levels if p.skill_levels is not None else {}),
        'completed_quests': (p.completed_quests if p.completed_quests is not None else set()),
    })


def snap(entries=None):
    if entries is None:
        entries = []
    return BankInventorySnapshot({_k: _v for _k, _v in entries})


def _fn1():
    r = rec(Record({
        'requirements': Record({'min_quest_points': 999}),
        'items': [Record({'name': 'X', 'qty': 1, 'kind': 'mustHave'})],
    }))
    e = evaluate(r, player(), snap(), 'complete')
    expect(e.status).to_be('DONE')
    expect(e.reasons).to_equal([])


test('complete journal status is DONE and skips requirement checks', _fn1)


def _fn2():
    r = rec(Record({
        'requirements': Record({'skills': [Record({'skill': 'mining', 'level': 10})]}),
        'items': [Record({'name': 'Iron bar', 'qty': 2, 'kind': 'mustHave'})],
    }))
    e = evaluate(r, player(Record({'skill_levels': {_k: _v for _k, _v in [['mining', 10]]}})), snap([['Iron bar', 2]]), 'not_started')
    expect(e.status).to_be('READY')
    expect(e.reasons).to_equal([])


test('all gates met and must-have present is READY', _fn2)


def _fn3():
    r = rec(Record({
        'requirements': Record({'min_quest_points': 32, 'skills': [Record({'skill': 'mining', 'level': 10})]}),
        'items': [Record({'name': 'Redberry pie', 'qty': 1, 'kind': 'mustHave'})],
    }))
    e = evaluate(r, player(Record({'quest_points': 18, 'skill_levels': {_k: _v for _k, _v in [['mining', 7]]}})), snap(), 'not_started')
    expect(e.status).to_be('BLOCKED')
    expect(e.reasons).to_contain('needs 32 quest points (have 18)')
    expect(e.reasons).to_contain('needs Mining 10 (have 7)')
    expect(e.reasons).to_contain('missing item: Redberry pie x1 (have 0)')


test('unmet requirement and missing item both appear in BLOCKED reasons', _fn3)


def _fn4():
    r = rec(Record({'items': [Record({'name': 'Egg', 'qty': 1, 'kind': 'acquirable'})]}))
    expect(evaluate(r, player(), snap(), 'not_started').status).to_be('READY')


test('acquirable-only missing items do not block READY', _fn4)


def _fn5():
    records = [rec(Record({'id': 'a', 'name': 'A'})), rec(Record({'id': 'b', 'name': 'B'}))]
    statuses = {_k: _v for _k, _v in [['A', 'complete'], ['B', 'not_started']]}
    res = evaluate_all(records, player(), snap(), lambda n: (statuses.get(n) if statuses.get(n) is not None else 'unknown'))
    expect(([x for x in res if x.id == 'a'] or [None])[0].status).to_be('DONE')
    expect(([x for x in res if x.id == 'b'] or [None])[0].status).to_be('READY')


test('evaluateAll maps names to statuses via statusOf', _fn5)


def _fn6():
    r = rec(Record({'items': [Record({'name': 'Dragon bones', 'qty': 1, 'kind': 'mustHave'})]}))
    e = evaluate(r, player(), snap(), 'in_progress')
    expect(e.status).to_be('READY')
    expect(e.reasons).to_equal([])


test('a started quest is not blocked by items it has already consumed', _fn6)


def _fn7():
    r = rec(Record({
        'requirements': Record({'min_quest_points': 32}),
        'items': [Record({'name': 'Dragon bones', 'qty': 1, 'kind': 'mustHave'})],
    }))
    e = evaluate(r, player(Record({'quest_points': 18})), snap(), 'in_progress')
    expect(e.status).to_be('BLOCKED')
    expect(e.reasons).to_equal(['needs 32 quest points (have 18)'])


test('a started quest is still blocked by requirements, which are never consumed', _fn7)


def _fn8():
    record = ([q for q in QUESTS if q.id == 'squire'] or [None])[0]
    low_cooking = player(Record({'skill_levels': {_k: _v for _k, _v in [['mining', 10], ['cooking', 9]]}}))
    expect(evaluate(record, low_cooking, snap(), 'not_started')).to_match_object(Record({'status': 'BLOCKED', 'reasons': ['needs Cooking 10 (have 9)']}))
    requirements_met = player(Record({'skill_levels': {_k: _v for _k, _v in [['mining', 10], ['cooking', 10]]}}))
    expect(evaluate(record, requirements_met, snap(), 'not_started').status).to_be('READY')


test("the knight's sword cannot start below Cooking 10", _fn8)

"""rs2b0t's test/api/ai/quests/requirement-checker.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs.record import Record
from rs2004.quests.eligibility import check_requirements

def rec(requirements):
    return Record({'id': 't', 'name': 'Test', 'quest_points': 1, 'requirements': requirements, 'items': []})


def player(p=None):
    if p is None:
        p = Record({})
    return Record({
        'quest_points': (p.quest_points if p.quest_points is not None else 0),
        'skill_levels': (p.skill_levels if p.skill_levels is not None else {}),
        'completed_quests': (p.completed_quests if p.completed_quests is not None else set()),
    })


def _fn1():
    expect(check_requirements(rec(Record({})), player())).to_equal([])


test('no requirements yields no results', _fn1)


def _fn2():
    pass_ = check_requirements(rec(Record({'min_quest_points': 32})), player(Record({'quest_points': 40})))
    expect(pass_).to_equal([Record({'ok': True, 'reason': ''})])
    fail = check_requirements(rec(Record({'min_quest_points': 32})), player(Record({'quest_points': 18})))
    expect(fail[0].ok).to_be(False)
    expect(fail[0].reason).to_be('needs 32 quest points (have 18)')


test('quest-point gate passes and fails with a reason showing have-value', _fn2)


def _fn3():
    r = rec(Record({'skills': [Record({'skill': 'mining', 'level': 10})]}))
    expect((check_requirements(r, player(Record({'skill_levels': {_k: _v for _k, _v in [['mining', 10]]}}))) or [None])[0].ok).to_be(True)
    fail = check_requirements(r, player(Record({'skill_levels': {_k: _v for _k, _v in [['mining', 7]]}})))
    expect(fail[0]).to_equal(Record({'ok': False, 'reason': 'needs Mining 10 (have 7)'}))


test('skill gate compares base level and reports the shortfall', _fn3)


def _fn4():
    r = rec(Record({'skills': [Record({'skill': 'mining', 'level': 10})]}))
    expect((check_requirements(r, player()) or [None])[0].reason).to_be('needs Mining 10 (have 0)')


test('missing skill level reads as 0', _fn4)


def _fn5():
    r = rec(Record({'quests': ['runemysteries']}))
    done = check_requirements(r, player(Record({'completed_quests': set(['runemysteries'])})))
    expect(done[0].ok).to_be(True)
    missing = check_requirements(r, player())
    expect(missing[0]).to_equal(Record({'ok': False, 'reason': 'prerequisite quest not complete: runemysteries'}))


test('prerequisite quest gate uses completedQuests set', _fn5)


def _fn6():
    r = rec(Record({'min_quest_points': 5, 'skills': [Record({'skill': 'cooking', 'level': 2})], 'quests': ['cook']}))
    res = check_requirements(r, player(Record({
        'quest_points': 5,
        'skill_levels': {_k: _v for _k, _v in [['cooking', 3]]},
        'completed_quests': set(['cook']),
    })))
    expect([x.ok for x in res]).to_equal([True, True, True])


test('multiple gates return one result each in order QP, skills, quests', _fn6)

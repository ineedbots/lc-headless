"""rs2b0t's test/api/ai/quests/data.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""


from rs2004.catalogs import QUEST_ROCK_TYPES, ROCK_OPTIONS
from rs2004.catalogs.record import Record
from rs2004.quests.data import QUESTS

def _fn1():
    ids = [r.id for r in QUESTS]
    expect(len(set(ids))).to_be(len(ids))


test('records have unique ids', _fn1)


def _fn2():
    names = [r.name for r in QUESTS]
    expect(len(set(names))).to_be(len(names))


test('records have unique names (name is the live journal-lookup key)', _fn2)


def _fn3():
    records = QUESTS
    ids = set([r.id for r in records])
    for r in records:
        for pre in (r.requirements.quests if r.requirements.quests is not None else []):
            expect((pre in ids)).to_be(True)


test('every prerequisite quest id resolves to a real record', _fn3)


def _fn4():
    for r in QUESTS:
        expect(len(r.name)).to_be_greater_than(0)
        expect((isinstance(r.quest_points, int) or isinstance(r.quest_points, float))).to_be(True)


test('every record has a non-empty name and a numeric questPoints', _fn4)


def _fn5():
    for r in QUESTS:
        for it in r.items:
            expect(['mustHave', 'acquirable']).to_contain(it.kind)
            expect(it.qty).to_be_greater_than(0)


test('item kinds are valid and quantities positive', _fn5)


def _fn6():
    expect(len(QUESTS)).to_be(63)


test('the dataset covers all 63 journal quests', _fn6)


def _fn7():
    expect(QUEST_ROCK_TYPES.get('Blurite')).to_equal([2110])
    expect(ROCK_OPTIONS).not_.to_contain('Blurite')


test('blurite is a quest rock, and never a GatheringBot option', _fn7)


def _fn8():
    squire = ([q for q in QUESTS if q.id == 'squire'] or [None])[0]
    expect(all([i.kind == 'acquirable' for i in squire.items])).to_be(True)
    expect(squire.requirements.skills).to_equal([Record({'skill': 'mining', 'level': 10}), Record({'skill': 'cooking', 'level': 10})])


test("the knight's sword requires Mining and Cooking 10 and acquires its items", _fn8)

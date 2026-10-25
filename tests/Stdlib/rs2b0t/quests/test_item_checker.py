"""rs2b0t's test/api/ai/quests/item-checker.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.quests.types import BankInventorySnapshot
from rs2004.quests.eligibility import check_items

def rec(items):
    return Record({'id': 't', 'name': 'T', 'quest_points': 1, 'requirements': Record({}), 'items': items})


def snap(entries=None):
    if entries is None:
        entries = []
    return BankInventorySnapshot({_k: _v for _k, _v in entries})


def _fn1():
    expect(check_items(rec([]), snap())).to_equal([])


test('no items yields no results', _fn1)


def _fn2():
    r = rec([Record({'name': 'Iron bar', 'qty': 2, 'kind': 'mustHave'})])
    res = check_items(r, snap([['Iron bar', 2]]))
    expect(res[0]).to_equal(Record({'name': 'Iron bar', 'qty': 2, 'kind': 'mustHave', 'present': 2, 'ok': True, 'will_gather': False}))


test('mustHave present in sufficient qty is ok', _fn2)


def _fn3():
    r = rec([Record({'name': 'Iron bar', 'qty': 2, 'kind': 'mustHave'})])
    res = check_items(r, snap([['Iron bar', 1]]))
    expect(res[0].ok).to_be(False)
    expect(res[0].present).to_be(1)


test('mustHave with insufficient qty fails', _fn3)


def _fn4():
    res = check_items(rec([Record({'name': 'Redberry pie', 'qty': 1, 'kind': 'mustHave'})]), snap())
    expect(res[0].ok).to_be(False)
    expect(res[0].present).to_be(0)


test('mustHave absent fails with present 0', _fn4)


def _fn5():
    r = rec([Record({'name': 'Egg', 'qty': 1, 'kind': 'acquirable'})])
    absent = check_items(r, snap())
    expect(absent[0].ok).to_be(True)
    expect(absent[0].will_gather).to_be(True)
    present = check_items(r, snap([['Egg', 1]]))
    expect(present[0].ok).to_be(True)
    expect(present[0].will_gather).to_be(False)


test('acquirable never blocks and flags willGather when absent', _fn5)


def _fn6():
    r = rec([Record({'name': 'Iron bar', 'qty': 1, 'kind': 'mustHave'})])
    expect((check_items(r, snap([['iron bar', 3]])) or [None])[0].ok).to_be(True)


test('name match is case-insensitive', _fn6)


# Why: the engine reads the bank only after a quest starts, so blocking on an unread one stopped the
# queue before it ever opened a booth, Watch Tower reported four missing items it had two of each.
def _fn7():
    r = rec([Record({'name': 'Gold bar', 'qty': 1, 'kind': 'mustHave'})])
    res = check_items(r, BankInventorySnapshot({}, False))
    expect(res[0].ok).to_be(True)
    expect(res[0].present).to_be(0)


test('an unread bank does not block a mustHave item', _fn7)


def _fn8():
    r = rec([Record({'name': 'Gold bar', 'qty': 1, 'kind': 'mustHave'})])
    expect((check_items(r, BankInventorySnapshot({}, True)) or [None])[0].ok).to_be(False)


test('a read bank that really lacks the item still blocks', _fn8)


def _fn9():
    r = rec([Record({'name': 'Gold bar', 'qty': 1, 'kind': 'mustHave'})])
    expect((check_items(r, BankInventorySnapshot({'gold bar': 2}, True)) or [None])[0].ok).to_be(True)


test('a read bank holding the item is ok', _fn9)


def _fn10():
    r = rec([Record({'name': 'Clay', 'qty': 6, 'kind': 'acquirable'})])
    for bank_known in [True, False]:
        res = check_items(r, BankInventorySnapshot({}, bank_known))
        expect(res[0].ok).to_be(True)
        expect(res[0].will_gather).to_be(True)


test('acquirable items are unaffected by whether the bank has been read', _fn10)

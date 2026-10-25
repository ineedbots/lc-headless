"""rs2b0t's test/api/ai/quests/engine/bank-empty-counts.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
rs2b0t stubs the client's bank reads; here the bank facade is spied on."""

from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.quests.engine.quest_engine import QuestEngine


def coins(count):
    return Record({'id': 995, 'name': 'Coins', 'count': count})


def _fn2():
    state = {'items': [coins(400)]}
    spy_on(bank, 'is_open', returns=True)
    spy_on(bank, 'ready', returns=True)
    spy_on(bank, 'items', impl=lambda: state['items'])
    internals = QuestEngine(Record({}))
    internals._refresh_bank_counts()
    expect(internals._last_bank_counts.get('coins')).to_be(400)
    # The quest spends the lot. The bank still answers, and the answer is zero.
    state['items'] = []
    internals._refresh_bank_counts()
    expect(internals._last_bank_counts.get('coins')).to_be_undefined()
    expect(internals._last_bank_id_counts.get(995)).to_be_undefined()


test('a bank the quest drains to empty clears the counts, it does not keep the old ones', _fn2)


def _fn3():
    state = {'arrived': True}
    spy_on(bank, 'is_open', returns=True)
    spy_on(bank, 'ready', impl=lambda: state['arrived'])
    spy_on(bank, 'items', impl=lambda: [coins(400)] if state['arrived'] else [])
    internals = QuestEngine(Record({}))
    internals._refresh_bank_counts()
    expect(internals._last_bank_counts.get('coins')).to_be(400)
    state['arrived'] = False
    internals._refresh_bank_counts()
    expect(internals._last_bank_counts.get('coins')).to_be(400)


test('a bank still transmitting keeps the last known counts', _fn3)

"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerStock.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.stock import LevelerStock

def _fn1(*_args):
    view = LevelerStock()
    view.observe([Record({'id': 1511, 'name': 'Logs', 'count': 50})], True)
    view.observe([], False)
    expect(view.total([]).get('logs')).to_be(50)
    expect(view.ready).to_be(True)
test('closing the bank retains its last observed stock instead of reporting empty supplies', _fn1)

def _fn2(*_args):
    view = LevelerStock()
    view.observe([Record({'id': 1511, 'name': 'Logs', 'count': 50})], True)
    view.observe([Record({'id': 1511, 'name': 'Logs', 'count': 24})], True)
    expect(view.total([Record({'id': 1511, 'name': 'Logs', 'count': 26})]).get('logs')).to_be(50)
test('withdrawal updates bank stock before adding the carried items', _fn2)

def _fn3(*_args):
    view = LevelerStock()
    view.observe([Record({'id': 995, 'name': 'Coins', 'count': 10000})], True)
    view.invalidate()
    view.observe([], False)
    expect(view.ready).to_be(False)
    view.observe([], True)
    expect(view.ready).to_be(True)
    expect(view.total([])).to_equal(Record({}))
test('restart invalidation requires a fresh bank read and a confirmed empty bank is valid', _fn3)

def resolved_wait(value):
    if False:
        yield
    return value

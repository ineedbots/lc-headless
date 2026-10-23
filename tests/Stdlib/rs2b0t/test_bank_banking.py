"""rs2b0t's test/api/bank/banking.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record


def state(o):
    _merged1 = {}
    for _k, _v in {'loot_count': 20, 'minutes_since_last_bank': 0, 'items_threshold': 15, 'minutes_threshold': 10}.items():
        _merged1[_k] = _v
    for _k, _v in (o._fields if isinstance(o, Record) else o).items():
        _merged1[_k] = _v
    return (Record(_merged1))


def _fn2():
    expect(should_bank_now('off', state(Record({})))).to_be(False)


test('off never banks', _fn2)


def _fn3():
    for s in ['items', 'time', 'either']:
        expect(should_bank_now(s, state(Record({'loot_count': 0, 'minutes_since_last_bank': 99})))).to_be(False)


test('no loot never banks, any strategy', _fn3)


def _fn4():
    expect(should_bank_now('items', state(Record({'loot_count': 15})))).to_be(True)
    expect(should_bank_now('items', state(Record({'loot_count': 14})))).to_be(False)
    expect(should_bank_now('items', state(Record({'loot_count': 14, 'minutes_since_last_bank': 99})))).to_be(False)


test('items banks at/over the item threshold only', _fn4)


def _fn5():
    expect(should_bank_now('time', state(Record({'minutes_since_last_bank': 10, 'loot_count': 1})))).to_be(True)
    expect(should_bank_now('time', state(Record({'minutes_since_last_bank': 9, 'loot_count': 99})))).to_be(False)


test('time banks at/over the minute threshold only (with loot)', _fn5)


def _fn6():
    expect(should_bank_now('either', state(Record({'loot_count': 20, 'minutes_since_last_bank': 0})))).to_be(True)
    expect(should_bank_now('either', state(Record({'loot_count': 1, 'minutes_since_last_bank': 10})))).to_be(True)
    expect(should_bank_now('either', state(Record({'loot_count': 1, 'minutes_since_last_bank': 0})))).to_be(False)


test('either banks when items OR time trips', _fn6)


def _fn7():
    expect(parse_bank_strategy('Off')).to_be('off')
    expect(parse_bank_strategy('Loot count')).to_be('items')
    expect(parse_bank_strategy('Time')).to_be('time')
    expect(parse_bank_strategy('Either')).to_be('either')
    expect(parse_bank_strategy('nonsense')).to_be('off')


test('parseBankStrategy maps labels, unknown -> off', _fn7)

"""rs2b0t's test/api/market/priceBook.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import DEFAULT_MARGIN, parse_books, remove_book, row_of, serialize_books, unique_book_name, upsert_book


import json


BOOK = Record({
    'name': 'seers',
    'margin': 20,
    'max_trade_value': 500000,
    'rows': [Record({'id': 440, 'mid': 17, 'cap': 5000, 'buying': True, 'selling': True})],
})


def _fn1():
    def _fn2():
        expect(parse_books(serialize_books([BOOK]))).to_equal([BOOK])
    test('round-trips through serialize', _fn2)

    def _fn3():
        expect(parse_books('not json')).to_equal([])
        expect(parse_books('{}')).to_equal([])
    test('bad JSON yields an empty list rather than throwing', _fn3)

    def _fn4():
        expect(parse_books(json.dumps(plain([Record({'rows': []}), Record({'name': '  '})])))).to_equal([])
    test('an unnamed book is dropped', _fn4)

    def _fn5():
        parsed = parse_books(json.dumps(plain([Record({'name': 'x', 'rows': [Record({'id': 440}), Record({'mid': 5}), Record({'id': 'nope', 'mid': 5})]})])))
        expect(parsed).to_have_length(1)
        expect(parsed[0].margin).to_be(DEFAULT_MARGIN)
        expect(parsed[0].max_trade_value).to_be(1000000)
        expect(parsed[0].rows).to_equal([Record({'id': 440, 'mid': 1, 'cap': 0, 'buying': True, 'selling': True})])
    test('fills missing fields with defaults and drops malformed rows', _fn5)

    def _fn6():
        parsed = parse_books(json.dumps(plain([Record({
        'name': 'x',
        'rows': [Record({'id': 440, 'mid': 20, 'buy': 15, 'margin': 40, 'cap': 10, 'selling': False})],
    })])))
        expect(parsed[0].rows[0]).to_equal(Record({'id': 440, 'mid': 20, 'buy': 15, 'margin': 40, 'cap': 10, 'buying': True, 'selling': False}))
    test('keeps overrides that are present', _fn6)


describe('parseBooks', _fn1)


def _fn7():
    def _fn8():
        _merged9 = {}
        for _k, _v in (BOOK._fields if isinstance(BOOK, Record) else BOOK).items():
            _merged9[_k] = _v
        for _k, _v in {'margin': 30}.items():
            _merged9[_k] = _v
        changed = Record(_merged9)
        expect(upsert_book([BOOK], changed)).to_equal([changed])
        _merged10 = {}
        for _k, _v in (BOOK._fields if isinstance(BOOK, Record) else BOOK).items():
            _merged10[_k] = _v
        for _k, _v in {'name': 'varrock'}.items():
            _merged10[_k] = _v
        expect(upsert_book([BOOK], Record(_merged10))).to_have_length(2)
    test('upsert replaces by name and appends otherwise', _fn8)

    def _fn11():
        expect(remove_book([BOOK], 'SEERS')).to_equal([])
    test('remove drops by name, case-insensitively', _fn11)

    def _fn12():
        expect(unique_book_name([BOOK], 'seers')).to_be('seers 2')
        expect(unique_book_name([BOOK], 'varrock')).to_be('varrock')
    test('uniqueBookName suffixes a collision', _fn12)

    def _fn13():
        expect((row_of(BOOK, 440).mid if row_of(BOOK, 440) is not None else None)).to_be(17)
        expect(row_of(BOOK, 441)).to_be_null()
    test('rowOf finds by id', _fn13)


describe('upsertBook / removeBook / uniqueBookName / rowOf', _fn7)


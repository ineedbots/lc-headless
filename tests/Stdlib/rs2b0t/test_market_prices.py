"""rs2b0t's test/api/market/prices.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import resolve_prices, row_valid


def book(over=None):
    if over is None:
        over = Record({})
    _merged1 = {}
    for _k, _v in {'name': 'default', 'margin': 20, 'max_trade_value': 1000000, 'rows': []}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged1[_k] = _v
    return Record(_merged1)


def row(over=None):
    if over is None:
        over = Record({})
    _merged2 = {}
    for _k, _v in {'id': 440, 'mid': 100, 'cap': 5000, 'buying': True, 'selling': True}.items():
        _merged2[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged2[_k] = _v
    return Record(_merged2)


def _fn3():
    def _fn4():
        expect(resolve_prices(book(), row())).to_equal(Record({'buy': 90, 'sell': 110}))
    test('splits the spread either side of mid', _fn4)

    def _fn5():
        expect(resolve_prices(book(Record({'margin': 15})), row(Record({'mid': 17})))).to_equal(Record({'buy': 15, 'sell': 19}))
    test('buy floors and sell ceils', _fn5)

    def _fn6():
        expect(resolve_prices(book(), row(Record({'margin': 50})))).to_equal(Record({'buy': 75, 'sell': 125}))
    test('a row margin beats the book margin', _fn6)

    def _fn7():
        expect(resolve_prices(book(), row(Record({'buy': 60, 'sell': 500})))).to_equal(Record({'buy': 60, 'sell': 500}))
    test('an explicit override beats both', _fn7)

    def _fn8():
        expect(resolve_prices(book(Record({'margin': 200})), row(Record({'mid': 1}))).buy).to_be(1)
    test('buy never drops below 1gp', _fn8)

    def _fn9():
        _o10 = resolve_prices(book(Record({'margin': 1})), row(Record({'mid': 1})))
        buy = _o10.buy
        sell = _o10.sell
        expect(sell).to_be_greater_than(buy)
    test('sell is forced above buy when rounding collapses them', _fn9)

    def _fn11():
        _o12 = resolve_prices(book(Record({'margin': 0})), row(Record({'mid': 50})))
        buy = _o12.buy
        sell = _o12.sell
        expect(buy).to_be(50)
        expect(sell).to_be(51)
    test('a zero margin still leaves a 1gp spread', _fn11)


describe('resolvePrices', _fn3)


def _fn13():
    def _fn14():
        expect(row_valid(book(), row())).to_be(True)
    test('true for a normal row', _fn14)

    def _fn15():
        expect(row_valid(book(), row(Record({'buy': 200, 'sell': 100})))).to_be(False)
    test('false when an override inverts the spread', _fn15)

    def _fn16():
        expect(row_valid(book(), row(Record({'buy': 100, 'sell': 100})))).to_be(False)
    test('false when overrides are equal', _fn16)

    def _fn17():
        expect(row_valid(book(), row(Record({'mid': 0})))).to_be(False)
    test('false for a non-positive mid with no overrides', _fn17)

    def _fn18():
        expect(row_valid(book(), row(Record({'cap': -1})))).to_be(False)
    test('false for a negative cap', _fn18)


describe('rowValid', _fn13)


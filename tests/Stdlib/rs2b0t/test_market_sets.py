"""rs2b0t's test/api/market/sets.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect. Its
quotes go through MarketMaker's resolve_quote, as rs2b0t's do."""

from rs2004.catalogs import Record, item_db
from rs2004.market import appraise, build_catalog, describe_appraisal
from bots.marketmaker.logic import resolve_quote

cat = build_catalog([Record({'id': item.id, 'name': item.name, 'cost': item.cost, 'members': item.members, 'stackable': False,
                             'equippable': item.slot is not None, 'certlink': -1, 'certtemplate': -1}) for item in item_db()])
rune = Record({'name': 'Rune set', 'item_ids': [1163, 1127, 1079]})


def make_book(rows, max_trade_value=100000):
    return Record({'name': 'Sets', 'margin': 20, 'max_trade_value': max_trade_value, 'rows': rows})


def row(id, mid, sell=None, selling=True):
    fields = {'id': id, 'mid': mid, 'cap': 100, 'buying': True, 'selling': selling}
    if sell is not None:
        fields['sell'] = sell
    return Record(fields)


book = make_book([row(1163, 80, 101), row(1127, 160, 202), row(1079, 240, 303)])


def quote(query, price_book=None, qty_implied=False):
    return resolve_quote(Record({'cat': cat, 'book': price_book if price_book is not None else book, 'query': query, 'side': 'selling', 'qty_implied': qty_implied}))


SET_QUERIES = [
    ['rune sets', [1163, 1127, 1079]],
    ['addy sets', [1161, 1123, 1073]],
    ['adamant set', [1161, 1123, 1073]],
    ['mithril sets', [1159, 1121, 1071]],
    ['mith set', [1159, 1121, 1071]],
    ['black sets', [1165, 1125, 1077]],
    ['steel sets', [1157, 1119, 1069]],
    ['black dragonhide sets', [2503, 2497, 2491]],
    ['red dragonhide sets', [2501, 2495, 2489]],
    ['blue dragonhide sets', [2499, 2493, 2487]],
    ['green dragonhide sets', [1135, 1099, 1065]],
    ['black dhide set', [2503, 2497, 2491]],
    ["black d'hide sets", [2503, 2497, 2491]],
    ['leather set', [1129, 1095, 1063]],
    ['super sets', [157, 145, 163]],
]


def resolves(query, item_ids):
    def run():
        priced = make_book([row(id, 100) for id in item_ids])
        found = quote(query, priced)
        expect(found.kind, query).to_be('set')
        expect(found.set.item_ids).to_equal(item_ids)
    return run


def broken(mode):
    def run():
        rows = []
        for r in book.rows:
            if r.id != 1163:
                rows.append(r)
            elif mode == 'disabled':
                rows.append(row(r.id, r.mid, r.sell, False))
            elif mode == 'invalid':
                rows.append(row(r.id, 0, r.sell))
        expect(quote('rune sets', make_book(rows)).kind).to_be('miss')
    return run


def _fn1():
    for query, item_ids in SET_QUERIES:
        test(f'resolves {query} to one of each piece', resolves(query, item_ids))

    def _fn4():
        expect(quote('Rune Set', None, True)).to_equal(Record({'kind': 'set', 'set': rune}))
    test('singular sets work with an implied quantity and mixed case', _fn4)

    for mode in ['missing', 'disabled', 'invalid']:
        test(f'does not sell a set with a {mode} component price', broken(mode))

    def _fn11():
        expect(quote('black dragonhide sets').kind).to_be('miss')
        expect(quote('rune full helm')).to_equal(Record({'kind': 'hit', 'id': 1163, 'name': 'Rune full helm'}))
    test('does not confuse black armour with black dragonhide or a single item', _fn11)


describe('set names', _fn1)


class Desk:
    def __init__(self, stock):
        self.stock = stock
        self.purse = 200000

    def available(self, id):
        return self.stock.get(id, 0)

    def held(self, id):
        return self.stock.get(id, 0)


def sale(stock=None, price_book=None):
    return appraise(price_book if price_book is not None else book, cat, Desk(stock if stock is not None else {1163: 10, 1127: 10, 1079: 10}),
                    995, [], Record({'set': rune, 'max_qty': 10}))


def pairs(counts):
    return [[id, counts[id]] for id in counts]


def _fn12():
    def _fn13():
        result = sale()
        expect(result.kind).to_be('sell')
        expect(pairs(result.owe)).to_equal([[1163, 10], [1127, 10], [1079, 10]])
        expect(pairs(result.want)).to_equal([[995, 6060]])
        expect(result.total).to_be(6060)
        expect(describe_appraisal(result)).to_contain('You owe 6,060gp.')
    test('ten sets offer ten of every component for the sum of individual sell prices', _fn13)

    def _fn14():
        result = sale({1163: 10, 1127: 3, 1079: 8})
        expect(pairs(result.owe)).to_equal([[1163, 3], [1127, 3], [1079, 3]])
        expect(result.total).to_be(1818)
    test('the least stocked component limits every component to complete sets', _fn14)

    def _fn15():
        expect(sale({1163: 10, 1127: 10}).kind).to_be('nothing')
    test('a missing component never produces a partial set', _fn15)

    def _fn16():
        result = sale(None, make_book(book.rows, 1500))
        expect(pairs(result.owe)).to_equal([[1163, 2], [1127, 2], [1079, 2]])
        expect(result.total).to_be(1212)
    test('the trade value cap applies to the combined set price', _fn16)

    def _fn18():
        changed = make_book([row(r.id, r.mid, r.sell, r.id != 1127) for r in book.rows])
        expect(sale(None, changed).kind).to_be('nothing')
    test('disabling a component after the quote stops the whole sale', _fn18)


describe('set prices and quantities', _fn12)

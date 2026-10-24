"""Price books: what a market bot buys and sells, at what, and how many it holds; reading them from settings and
writing them back, and the buy and sell prices a row resolves to. Ported from rs2b0t's api/market/priceBook.ts,
prices.ts and bookStore.ts (MIT, see thirdparty/rs2b0t).

A book is a Record with name, margin (the total spread, percent), max_trade_value and rows; a row one with id
(the unnoted obj id, the book's only key), mid, cap (the most held before buying stops), buying, selling, and,
where set, buy, sell and margin. Books are saved as JSON in the account file's settings, under
"PriceBooks"'s "books", with rs2b0t's keys, so a book moves between the two clients as it is.
"""

import json
import math

from rs2004.catalogs.record import Record
from rs2004.settings import settings_store

# The total spread a new book quotes, split either side of mid.
DEFAULT_MARGIN = 5
DEFAULT_MAX_TRADE = 1000000

PRICE_BOOK_SETTINGS_NS = 'PriceBooks'
BOOKS_KEY = 'books'


def _is_number(value):
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool) and value == value and value not in [float('inf'), float('-inf')]


def _int(value, fallback):
    return int(value) if _is_number(value) else fallback


def _opt_int(value):
    return int(value) if _is_number(value) else None


def make_row(id, mid, cap=0, buying=True, selling=True, buy=None, sell=None, margin=None):
    fields = {'id': id, 'mid': mid, 'cap': cap, 'buying': buying, 'selling': selling}
    if buy is not None:
        fields['buy'] = buy
    if sell is not None:
        fields['sell'] = sell
    if margin is not None:
        fields['margin'] = margin
    return Record(fields)


def make_book(name, margin=5, max_trade_value=1000000, rows=None):
    return Record({'name': name, 'margin': margin, 'max_trade_value': max_trade_value, 'rows': rows if rows is not None else []})


def _parse_row(raw):
    if not isinstance(raw, dict):
        return None
    if not _is_number(raw.get('id')):
        return None
    return make_row(int(raw['id']), max(1, _int(raw.get('mid'), 1)), max(0, _int(raw.get('cap'), 0)), raw.get('buying') is not False, raw.get('selling') is not False,
                    _opt_int(raw.get('buy')), _opt_int(raw.get('sell')), _opt_int(raw.get('margin')))


def parse_books(text):
    """The books in a JSON string; an empty list when it isn't a list of books.

    Why: the setting is player-edited JSON, so a malformed book degrades to nothing rather than raising."""
    try:
        raw = json.loads(text)
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        if not isinstance(name, str) or name.strip() == '':
            continue
        max_trade = entry.get('maxTradeValue')
        if max_trade is None:
            max_trade = entry.get('max_trade_value')
        rows = []
        if isinstance(entry.get('rows'), list):
            for raw_row in entry['rows']:
                row = _parse_row(raw_row)
                if row is not None:
                    rows.append(row)
        out.append(make_book(name, _int(entry.get('margin'), DEFAULT_MARGIN), _int(max_trade, DEFAULT_MAX_TRADE), rows))
    return out


def _row_json(row):
    out = {'id': row.id, 'mid': row.mid}
    for field in ['buy', 'sell', 'margin']:
        if getattr(row, field) is not None:
            out[field] = getattr(row, field)
    out['cap'] = row.cap
    out['buying'] = row.buying
    out['selling'] = row.selling
    return out


def serialize_books(books):
    return json.dumps([{'name': b.name, 'margin': b.margin, 'maxTradeValue': b.max_trade_value, 'rows': [_row_json(r) for r in b.rows]} for b in books])


def upsert_book(books, book):
    """The books with `book` in place of the one of its name, or added."""
    out = list(books)
    for i in range(len(out)):
        if out[i].name.lower() == book.name.lower():
            out[i] = book
            return out
    out.append(book)
    return out


def remove_book(books, name):
    wanted = name.strip().lower()
    return [b for b in books if b.name.lower() != wanted]


def unique_book_name(books, wanted):
    """wanted, or with the first number that makes it a name no book has: "Runes 2"."""
    taken = set([b.name.lower() for b in books])
    if wanted.lower() not in taken:
        return wanted
    n = 2
    while True:
        candidate = f'{wanted} {n}'
        if candidate.lower() not in taken:
            return candidate
        n += 1


def row_of(book, id):
    for row in book.rows:
        if row.id == id:
            return row
    return None


# Prices (prices.ts)


def resolve_prices(book, row):
    """The row's buy and sell prices, a Record: its own, else mid less and plus half the margin.

    Why: margin is the total spread, so it splits either side of mid and a 20% book quotes 90/110 on a 100gp
    item. It multiplies before dividing: 100 * (1 + 20/200) is 110.00000000000001, and the ceil would overcharge
    every round number by 1gp."""
    m = row.margin if row.margin is not None else book.margin
    buy = max(1, row.buy if row.buy is not None else (row.mid * (200 - m)) // 200)
    sell = max(buy + 1, row.sell if row.sell is not None else int(math.ceil((row.mid * (200 + m)) / 200)))
    return Record({'buy': buy, 'sell': sell})


def row_valid(book, row):
    if row.cap < 0 or row.mid < 1:
        return False
    if row.buy is not None and row.sell is not None and row.sell <= row.buy:
        return False
    prices = resolve_prices(book, row)
    return prices.buy >= 1 and prices.sell > prices.buy


# The saved books (bookStore.ts)


class _PriceBooks:
    """The account's books, in its settings."""

    def all(self):
        """The saved books: a list in the account file, or rs2b0t's JSON string of one."""
        saved = settings_store.saved(PRICE_BOOK_SETTINGS_NS, BOOKS_KEY)
        if isinstance(saved, list):
            return parse_books(json.dumps(saved))
        return parse_books(saved) if isinstance(saved, str) else []

    def names(self):
        return [b.name for b in self.all()]

    def by_name(self, name):
        wanted = name.strip().lower()
        for b in self.all():
            if b.name.lower() == wanted:
                return b
        return None

    def save(self, books):
        """Writes the books into the account file as a list, which reads more easily there than a string."""
        settings_store.save(PRICE_BOOK_SETTINGS_NS, BOOKS_KEY, json.loads(serialize_books(books)))


PriceBooks = _PriceBooks()

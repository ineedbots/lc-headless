"""Pricing a trade: what the customer has put up or asked for, what each side owes by the book, and the line
that tells them. Also the sets a market sells whole, what it holds between bank trips, and checking a trade
screen against the deal. Ported from rs2b0t's api/market/appraise.ts, saleIntent.ts, sets.ts, ledger.ts,
driveMarketTrade.ts and quote.ts (MIT, see thirdparty/rs2b0t).

An offer item is anything with id, name and count (an InvItem). A sale intent is a Record with max_qty and
either item_id or set (a set has name and item_ids). The desk is anything with available(id), held(id) and
purse.
"""

from rs2004.catalogs.record import Record
from rs2004.market._text import format_gp, replace_word, squash_spaces, starts_with_word
from rs2004.market.catalog import display_name, unnoted_id
from rs2004.market.chat_protocol import truncate_chat
from rs2004.market.price_book import resolve_prices, row_of, row_valid

# Sets (sets.ts)

SETS = {
    'rune': Record({'name': 'Rune set', 'item_ids': [1163, 1127, 1079]}),
    'adamant': Record({'name': 'Adamant set', 'item_ids': [1161, 1123, 1073]}),
    'mithril': Record({'name': 'Mithril set', 'item_ids': [1159, 1121, 1071]}),
    'black': Record({'name': 'Black set', 'item_ids': [1165, 1125, 1077]}),
    'steel': Record({'name': 'Steel set', 'item_ids': [1157, 1119, 1069]}),
    'black dragonhide': Record({'name': 'Black dragonhide set', 'item_ids': [2503, 2497, 2491]}),
    'red dragonhide': Record({'name': 'Red dragonhide set', 'item_ids': [2501, 2495, 2489]}),
    'blue dragonhide': Record({'name': 'Blue dragonhide set', 'item_ids': [2499, 2493, 2487]}),
    'green dragonhide': Record({'name': 'Green dragonhide set', 'item_ids': [1135, 1099, 1065]}),
    'leather': Record({'name': 'Leather set', 'item_ids': [1129, 1095, 1063]}),
    'super': Record({'name': 'Super set', 'item_ids': [157, 145, 163]}),
}


def resolve_set(query):
    """The set a query such as 'rune sets' or 'addy set' names, or None."""
    key = squash_spaces(query.lower())
    if starts_with_word(key, 'addy'):
        key = 'adamant' + key[4:]
    elif starts_with_word(key, 'mith'):
        key = 'mithril' + key[4:]
    for spelling in ['dhide', "d'hide", 'd-hide', 'd hide']:
        replaced = replace_word(key, spelling, 'dragonhide')
        if replaced != key:
            key = replaced
            break
    if key.endswith(' sets'):
        base = key[:len(key) - 5]
    elif key.endswith(' set'):
        base = key[:len(key) - 4]
    else:
        return None
    return SETS.get(base) if len(base) > 0 else None


# Sale intents (saleIntent.ts)


def sale_items(intent):
    return intent.set.item_ids if intent.set is not None else [intent.item_id]


def sale_name(cat, intent):
    return intent.set.name if intent.set is not None else display_name(cat, intent.item_id)


def sale_stock(intent, count):
    """How many of the sale the counts make up: the fewest of any one item."""
    return min([count(id) for id in sale_items(intent)])


def sale_price(book, intent):
    """What one of the sale costs, summed over a set's items; None when the book won't sell any of them."""
    total = 0
    for id in sale_items(intent):
        row = row_of(book, id)
        if row is None or not row.selling or not row_valid(book, row):
            return None
        total += resolve_prices(book, row).sell
    return total if total > 0 else None


# The ledger (ledger.ts)


class Ledger:
    """What the bank held at the last look, adjusted by trades since.

    Why: the bank can't be read while shut, and the per-item cap has to mean something between trips."""

    def __init__(self):
        self._stock = {}

    def set_stock(self, entries):
        """From entries with id and count, such as bank.items()."""
        self._stock = {}
        for e in entries:
            self._stock[e.id] = self._stock.get(e.id, 0) + e.count

    def held(self, id):
        return self._stock.get(id, 0)

    def add(self, id, qty):
        self._stock[id] = max(0, self.held(id) + qty)


# Offers on the screen (driveMarketTrade.ts)


def normalise_offer(cat, items):
    """A trade side as {unnoted id: count}, so noted and unnoted of one row count together."""
    out = {}
    for item in items:
        id = unnoted_id(cat, item.id)
        out[id] = out.get(id, 0) + max(1, item.count)
    return out


def offers_match(actual, expected):
    """Exactly the ids and counts expected, with nothing extra on either side.

    Why: the confirm screen is checked against what was accepted, so "close enough" is how a swapped offer gets
    through."""
    if len(actual) != len(expected):
        return False
    for id in expected:
        if actual.get(id) != expected[id]:
            return False
    return True


def offer_covers(actual, expected):
    """Their side carries at least what was asked for, whatever else is on it.

    Why: rounding up, or leaving something else in the window, is still the deal; an exact side would wait out a
    good trade."""
    for id in expected:
        if actual.get(id, 0) < expected[id]:
            return False
    return len(expected) > 0


# Appraisal (appraise.ts)


class Appraisal:
    """appraise's answer. Not a Record, since owe and want are {id: count} dicts."""

    def __init__(self, kind, owe, want, total, lines, ignored, note, sale_set=None):
        self.kind = kind
        self.owe = owe
        self.want = want
        self.total = total
        self.lines = lines
        self.ignored = ignored
        self.note = note
        self.set = sale_set

    @property
    def _fields(self):
        """Its fields as a dict, as a Record's, so two appraisals compare by value."""
        return {'kind': self.kind, 'owe': self.owe, 'want': self.want, 'total': self.total, 'lines': self.lines, 'ignored': self.ignored, 'note': self.note, 'set': self.set}

    def __repr__(self):
        return f'Appraisal({self.kind}, total={self.total})'


def _nothing(ignored, note):
    return Appraisal('nothing', {}, {}, 0, [], ignored, note)


def _fold(cat, items, coin_id):
    """A trade side merged onto unnoted ids, keeping the coins apart."""
    goods = {}
    coins = 0
    for item in items:
        units = max(1, item.count)
        if item.id == coin_id:
            coins += units
            continue
        id = unnoted_id(cat, item.id)
        if id in cat.by_id:
            name = display_name(cat, id)
        else:
            name = item.name if item.name is not None else f'item {id}'
        if id in goods:
            goods[id]['count'] += units
        else:
            goods[id] = {'name': name, 'count': units}
    return goods, coins


def _price_of(book, id, side):
    """The unit price, or None when the book won't trade that item that way ('buying' or 'selling')."""
    row = row_of(book, id)
    if row is None or not row_valid(book, row) or not getattr(row, side):
        return None
    prices = resolve_prices(book, row)
    return prices.buy if side == 'buying' else prices.sell


def _line(id, name, count, each):
    return Record({'id': id, 'name': name, 'count': count, 'each': each, 'value': count * each})


def _ignored(name, count):
    return Record({'name': name, 'count': count})


def appraise(book, cat, desk, coin_id, their_offer, intent):
    """The deal, given what the customer has up and what they asked for (`intent`, or None): an Appraisal with kind
    ('buy', 'sell' or 'nothing'), owe (what the bot puts up, {id: count}), want (the least the customer must put
    up), total, lines (each id, name, count, each and value), ignored (what the customer should take back, each
    name and count), note, and for a set, set (name and count).

    Why: it's worked out afresh every beat, so nothing can go stale, and running it twice changes nothing."""
    goods, coins = _fold(cat, their_offer, coin_id)
    ignored = []
    if intent is not None:
        for id in goods:
            ignored.append(_ignored(goods[id]['name'], goods[id]['count']))
        return _sale(book, cat, desk, coin_id, intent, coins, ignored)
    if coins > 0:
        ignored.append(_ignored('coins', coins))
    return _purchase(book, desk, coin_id, goods, ignored)


def _short_note(name, desk, intent):
    """Short of what was asked: the bank still holding some is a different thing from being out."""
    if sale_stock(intent, desk.held) > sale_stock(intent, desk.available):
        return f'that is all the {name} I am carrying'
    return f'that is all the {name} I have'


def _sale(book, cat, desk, coin_id, intent, coins, ignored):
    """They named x, the book says y, they owe x * y."""
    name = sale_name(cat, intent)
    each = sale_price(book, intent)
    if each is None:
        return _nothing(ignored, f"I don't sell {name} any more")
    qty = min(intent.max_qty, sale_stock(intent, desk.available), book.max_trade_value // each)
    if qty <= 0:
        return _nothing(ignored, f"I'm out of {name}")
    total = qty * each
    if coins > total:
        ignored.append(_ignored('coins', coins - total))
    owe = {}
    lines = []
    for id in sale_items(intent):
        owe[id] = qty
        lines.append(_line(id, display_name(cat, id), qty, _price_of(book, id, 'selling')))
    note = _short_note(name, desk, intent) if qty < intent.max_qty else None
    sale_set = Record({'name': name, 'count': qty}) if intent.set is not None else None
    return Appraisal('sell', owe, {coin_id: total}, total, lines, ignored, note, sale_set)


def _purchase(book, desk, coin_id, goods, ignored):
    """They put x up, the book says y, the bot owes x * y."""
    lines = []
    note = None
    for id in goods:
        name = goods[id]['name']
        count = goods[id]['count']
        each = _price_of(book, id, 'buying')
        row = row_of(book, id)
        take = 0 if each is None or row is None else min(count, max(0, row.cap - desk.held(id)))
        if take < count:
            ignored.append(_ignored(name, count - take))
            if each is not None:
                note = 'some of that is over my cap'
        if take > 0 and each is not None:
            lines.append(_line(id, name, take, each))

    # Why: the window can't say which units of a stack it's paying for, so over the ceiling the shop bids the
    # ceiling for the pile and the customer takes items back for full price.
    ceiling = min(desk.purse, book.max_trade_value)
    value = sum([line.value for line in lines])
    total = min(value, ceiling)
    if value > ceiling:
        note = f'max I can offer is {format_gp(ceiling)}gp per trade'
    if total <= 0:
        return _nothing(ignored, note)
    want = {}
    for line in lines:
        want[line.id] = line.count
    return Appraisal('buy', {coin_id: total}, want, total, lines, ignored, note)


def describe_appraisal(a):
    """One line, so the customer sees the deal before the bot accepts anything."""
    # Why: the line is cut at the chat limit and 2 priced lines already reach it, so the reason goes first or goes
    # unread.
    parts = [] if a.note is None else [f'{a.note}.']
    if a.set is not None:
        parts.append(f'{a.set.name} x{format_gp(a.set.count)} = {format_gp(a.total)}.')
    else:
        for line in a.lines:
            parts.append(f'{line.name} x{format_gp(line.count)} = {format_gp(line.value)}.')
    for i in a.ignored:
        parts.append(f'{format_gp(i.count)} {i.name}: not counted, keep them.')
    if len(parts) == 0:
        # Why: an empty window is where a customer is most likely lost, so the line says what to do.
        return 'Put items in and I price them as you go. To buy, say what you want first.'
    if a.kind == 'nothing':
        return truncate_chat(' '.join(parts))
    # Why: on a sale the total is what the customer owes, and saying so is the only prompt for the coins.
    total = f'You owe {format_gp(a.total)}gp.' if a.kind == 'sell' else f'Total {format_gp(a.total)}gp.'
    return truncate_chat(f"{' '.join(parts)} {total}")

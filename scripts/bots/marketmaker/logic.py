# MarketMaker's decisions, apart from the client: the desk of chat intents, cooldowns and the one open window, a
# window's beat, when to bank, reading the chat, rate limits, quotes, listings and the deal log. Ported from
# rs2b0t's scripts/MarketMaker/marketMakerLogic.ts (MIT, see thirdparty/rs2b0t). The decisions with many inputs
# keep rs2b0t's one input object (a Record, or anything with the fields), as its tests pass them.

import time

from rs2004.catalogs import Record
from rs2004.market import display_name, format_gp, resolve_by_name, resolve_set, row_of, row_valid, sale_price

# Bank once free slots drop this low, so a purchase always has room to land.
FREE_SLOT_FLOOR = 4


def _key(name):
    return name.strip().lower()


class Window:
    """The window in flight; everything here dies with it. still_beats: beats the customer's side hasn't moved.
    re_offers: how often the bot has changed its own side. last_sig: the customer's side last beat. saw_open: the
    modal has been seen open. accepted: what was accepted, give and get, checked again on the confirm screen.
    waited: beats spent waiting on the customer to put their side up."""

    def __init__(self, customer, opened_at_ms):
        self.customer = customer
        self.opened_at_ms = opened_at_ms
        self.still_beats = 0
        self.re_offers = 0
        self.last_sig = ''
        self.saw_open = False
        self.accepted = None
        self.expected_receipt = None
        self.waited = 0


class Desk:
    """Chat intents, cooldowns, and the one open window. An intent is a sale intent (max_qty and item_id or set)
    with customer and asked_at_ms, and renewed and misses once set.

    Why: the server allows one trade window per player, so the window is the transaction lock."""

    def __init__(self, intent_cap):
        self._intent_cap = intent_cap
        self._intents = {}
        self._cooldowns = {}
        self._window = None

    # Intents.

    def remember(self, intent):
        k = _key(intent.customer)
        self._intents.pop(k, None)
        self._intents[k] = intent
        while len(self._intents) > self._intent_cap:
            oldest = list(self._intents.keys())[0]
            self._intents.pop(oldest, None)

    def intent_for(self, customer, now_ms, ttl_ms):
        i = self._intents.get(_key(customer))
        if i is None or now_ms - i.asked_at_ms > ttl_ms:
            return None
        return i

    def forget(self, customer):
        self._intents.pop(_key(customer), None)

    def renew(self, customer, now_ms):
        """Restarts an intent's clock, for the moment the customer is told the goods are ready, once.

        Why: the bank trip and the wait for a window aren't the customer's time; but repeated announcements mustn't
        keep an intent alive for ever."""
        i = self._intents.get(_key(customer))
        if i is not None and i.renewed is not True:
            i.asked_at_ms = now_ms
            i.renewed = True

    def prune_intents(self, now_ms, ttl_ms):
        for k in list(self._intents.keys()):
            if now_ms - self._intents[k].asked_at_ms > ttl_ms:
                self._intents.pop(k, None)

    def limit_to(self, customer, qty):
        """Cuts an order down to what the shop managed to get, so it stops trying to top it up."""
        i = self._intents.get(_key(customer))
        if i is not None and qty > 0 and qty < i.max_qty:
            i.max_qty = qty

    def missed_stock(self, customer, limit):
        """Counts a bank trip that fetched none of it, and says whether to give up on the order.

        Why: an unfillable oldest intent is dropped, so later customers can advance."""
        i = self._intents.get(_key(customer))
        if i is None:
            return False
        i.misses = (i.misses or 0) + 1
        return i.misses >= limit

    def next_intent(self, now_ms, ttl_ms):
        """The oldest live intent, whose goods the bot fetches next."""
        for k in self._intents:
            i = self._intents[k]
            if now_ms - i.asked_at_ms <= ttl_ms:
                return i
        return None

    def intent_count(self):
        return len(self._intents)

    def clear(self):
        """Drops everything the desk holds: what was asked for, who's waiting out a cooldown, and the window, to
        recover from a trade flow that can't be used."""
        self._intents.clear()
        self._cooldowns.clear()
        self._window = None

    # The trade window.

    def open(self, customer, now_ms):
        self._window = Window(customer, now_ms)
        return self._window

    def current(self):
        return self._window

    def close(self):
        self._window = None

    def expired(self, now_ms, window_ms):
        """The window has run past its deadline."""
        return self._window is not None and now_ms - self._window.opened_at_ms > window_ms

    # Cooldowns.

    def cool(self, customer, until_ms):
        self._cooldowns[_key(customer)] = until_ms

    def on_cooldown(self, customer, now_ms):
        until = self._cooldowns.get(_key(customer))
        if until is None:
            return False
        if now_ms > until:
            self._cooldowns.pop(_key(customer), None)
            return False
        return True


def _beat(do, reason=None):
    return Record({'do': do, 'reason': reason}) if reason is not None else Record({'do': do})


def decide_beat(input):
    """One beat of an open window: 'wait', 'offer', 'accept' or 'give-up', with a reason. input has window,
    their_sig, still_beats_needed, owe_anything, owe_matched, want_matched, owe_fixed, re_offer_cap and wait_cap.

    Why: the customer's side has to be stable, since any change resets both accepts; and idle time is capped,
    since one open window blocks every customer behind it."""
    beat = _beat_for(input)
    if beat.do == 'wait' and input.window.waited >= input.wait_cap:
        return _beat('give-up', 'you left your side up too long')
    return beat


def _beat_for(input):
    # Why: a sale owes what the customer asked for, which nothing on their side changes, so the goods go up the beat
    # the window opens rather than after their coins have settled; the money is still what the accept is judged on.
    if input.owe_fixed and input.owe_anything and not input.owe_matched:
        if input.window.re_offers >= input.re_offer_cap:
            return _beat('give-up', 'too many changes in one trade')
        return _beat('offer', 'the goods asked for do not depend on their side')
    if input.their_sig != input.window.last_sig:
        return _beat('wait', 'their side moved')
    if input.window.still_beats < input.still_beats_needed:
        return _beat('wait', 'settling')
    if not input.owe_anything:
        return _beat('wait', 'nothing to trade yet')
    if not input.owe_matched:
        if input.window.re_offers >= input.re_offer_cap:
            return _beat('give-up', 'too many changes in one trade')
        return _beat('offer', 'my side does not match what I owe')
    # Why: a sale is x * y = z, so short money isn't a smaller deal, it's not the deal.
    if not input.want_matched:
        return _beat('wait', 'their side is not the deal yet')
    return _beat('accept')


def side_signature(side):
    """A trade side's signature ({id: count}), so "unchanged" can be decided."""
    return ','.join([f'{id}x{side[id]}' for id in sorted(list(side.keys()))])


def advertise_due(last_ms, now_ms, every_seconds):
    return every_seconds > 0 and now_ms - last_ms >= every_seconds * 1000


def trade_is_stalled(trade_active, has_window, window_expired):
    """A trade window that isn't advancing: gone from the desk, or past the engagement timeout.

    Why: ServeWindow outranks Listen, and only Listen drops expired windows, so a customer who opens the confirm
    screen and walks away would hold the trade open for ever, read as progress, and never be rescued."""
    return trade_active and (not has_window or window_expired)


def should_settle(free_slots, pack_coins, coin_floor, sale_ready=False):
    return (not sale_ready and free_slots <= FREE_SLOT_FLOOR) or pack_coins > coin_floor


def settle_due(free_slots, pack_coins, coin_floor, forced, sale_ready=False):
    """A bank trip is owed: no room, takings over the float, or a reset asked for one.

    Why: a reset is what an operator reaches for when the shop is wedged, so it owes a trip whatever the pack."""
    return forced or should_settle(free_slots, pack_coins, coin_floor, sale_ready)


def settle_runs(due, float_short, order_live):
    """Settle takes the tick: a due trip always, a float top-up only while no order is live.

    Why: OpenWindow holds every window while a trip is due, so an order that held Settle back waited on a window
    that couldn't open; a live order now delays only a float top-up."""
    return due or (float_short and not order_live)


def window_candidates(requests, sale_customer):
    """The requests a window may open with: the sale's customer alone while a sale is live, else every request.

    Why: a sale in progress has its goods fetched for one customer, and a window with anyone else would take
    their stock into the same pack."""
    if sale_customer is None:
        return list(requests)
    return [name for name in requests if _key(name) == _key(sale_customer)]


def buy_owes_settle(give, coin_id):
    """A completed trade owes a bank trip: the shop bought something, so its coins went out.

    Why: goods bought sit in the pack until a trip, and the operator wants them banked before the next customer."""
    return coin_id in give


def bank_before_serving(free_slots, pack_coins, coin_floor, bank_ready, forced=False, sale_ready=False):
    """The next window should wait for a bank trip.

    Why: OpenWindow runs above Settle, so a queue of customers dumping goods kept it opening windows on a pack with
    no room and it never reached the bank; a bank it can't reach mustn't shut the shop, so a backed-off one
    leaves it serving."""
    return bank_ready and settle_due(free_slots, pack_coins, coin_floor, forced, sale_ready)


def float_shortfall(pack_coins, bank_coins, coin_floor):
    """Coins worth going to the bank for: the gap up to the float, capped at what the bank holds.

    Why: asking for the whole float is an order the shop can never fill once the bank runs dry, and Settle deposits
    before it tops up, so it banked and withdrew the same stack every loop."""
    return max(0, min(coin_floor, pack_coins + bank_coins) - pack_coins)


def fresh_chat_lines(prev, now):
    """The chat lines new since the last read, oldest first. Both lists are signatures, newest first.

    Why: marking the place with only the newest signature loses a verbatim repeat, since the mark and the new line
    look the same, so a customer who says the same thing twice would be heard once."""
    if len(prev) == 0 or len(now) == 0:
        return []
    for shift in range(len(now)):
        aligned = True
        i = 0
        while i < len(prev) and shift + i < len(now):
            if now[shift + i] != prev[i]:
                aligned = False
                break
            i += 1
        if aligned:
            out = now[0:shift]
            out.reverse()
            return out
    out = list(now)
    out.reverse()
    return out


class RateLimiter:
    """A per-player command budget: max commands a window_ms, then penalty_ms of silence.

    Why: without one, fifty item queries build a fifty-line backlog and the shop lags for everyone, at no cost to
    the flooder."""

    def __init__(self, max_, window_ms, penalty_ms):
        self._max = max_
        self._window_ms = window_ms
        self._penalty_ms = penalty_ms
        self._hits = {}
        self._penalised = {}

    def allow(self, name, now_ms):
        k = _key(name)
        until = self._penalised.get(k)
        if until is not None:
            if now_ms <= until:
                return False
            self._penalised.pop(k, None)
            self._hits.pop(k, None)
        recent = [t for t in self._hits.get(k, []) if now_ms - t < self._window_ms]
        if len(recent) >= self._max:
            self._penalised[k] = now_ms + self._penalty_ms
            self._hits.pop(k, None)
            return False
        recent.append(now_ms)
        self._hits[k] = recent
        return True


def _quotable(book, side, id):
    row = row_of(book, id)
    return row is not None and getattr(row, side) and row_valid(book, row)


def resolve_quote(input):
    """What a customer's words name on the side of the book they ask about (input has cat, book, query, side
    'buying' or 'selling', and qty_implied): a Record of kind 'miss' (with answer), 'ambiguous' (with
    candidates), 'hit' (with id and name) or 'set' (with set).

    Why: an implied count means the line may be ordinary chat opening with "buy", so it has to name an item
    outright, and a miss goes unanswered instead of quoting back at every passing sentence."""
    cat = input.cat
    book = input.book
    side = input.side
    qty_implied = input.qty_implied
    found_set = resolve_set(input.query) if side == 'selling' else None
    if found_set is not None:
        known = len([id for id in found_set.item_ids if id not in cat.by_id]) == 0
        if known and sale_price(book, Record({'set': found_set, 'max_qty': 1})) is not None:
            return Record({'kind': 'set', 'set': found_set})
        return Record({'kind': 'miss', 'answer': not qty_implied})
    candidates = [r for r in resolve_by_name(cat, input.query, qty_implied) if _quotable(book, side, r.id)]
    if len(candidates) == 0:
        return Record({'kind': 'miss', 'answer': not qty_implied})
    if len(candidates) > 1:
        out = []
        for c in candidates:
            alias = cat.aliases.get(c.id)
            word = alias.words[0] if alias is not None and len(alias.words) > 0 else None
            out.append(Record({'id': c.id, 'name': display_name(cat, c.id), 'base': c.name, 'word': word}))
        return Record({'kind': 'ambiguous', 'candidates': out})
    return Record({'kind': 'hit', 'id': candidates[0].id, 'name': display_name(cat, candidates[0].id)})


def listed_rows(input):
    """The rows a listing reads out (input has book, side 'both', 'buy' or 'sell', and stocked(id)), and why the
    answer came back empty: 'no-book', 'no-stock' or None.

    Why: a row the shop holds none of isn't a quote worth sending a customer to, and an empty book is a different
    problem from an empty shelf, since only one of them fixes itself."""
    book = input.book
    side = input.side
    listed = []
    for r in book.rows:
        if not row_valid(book, r):
            continue
        if (side == 'buy' and r.buying) or (side == 'sell' and r.selling) or (side != 'buy' and side != 'sell' and (r.buying or r.selling)):
            listed.append(r)
    rows = [r for r in listed if input.stocked(r.id) > 0]
    if len(rows) > 0:
        return Record({'rows': rows, 'empty': None})
    return Record({'rows': rows, 'empty': 'no-book' if len(listed) == 0 else 'no-stock'})


def deal_of(give, get, coin_id, customer, at_ms):
    """A settled window read back as one deal (give and get are the two sides, {id: count}), or None: a Record of
    at_ms, customer, kind ('sold' or 'bought'), item_id and count of the biggest line, gp (taken in, or paid out
    as a negative) and mixed (more than one kind changed hands). Its fields are arguments here, where rs2b0t's is
    one input object, since a Record would make Records of the two sides.

    Why: the shop's own side carries the coins when it's buying, so the direction is decidable without tracking
    who opened the window."""
    paid = give.get(coin_id, 0)
    took = get.get(coin_id, 0)
    side = get if paid > 0 else give
    goods = [(id, side[id]) for id in side if id != coin_id]
    if len(goods) == 0:
        return None
    headline = goods[0]
    for one in goods:
        if one[1] > headline[1]:
            headline = one
    return Record({
        'at_ms': at_ms,
        'customer': customer,
        'kind': 'bought' if paid > 0 else 'sold',
        'item_id': headline[0],
        'count': headline[1],
        'gp': -paid if paid > 0 else took,
        'mixed': len(goods) > 1,
    })


def deal_totals(deals):
    """What the deals add up to: count, net, sold and bought."""
    net = 0
    sold = 0
    bought = 0
    for d in deals:
        net += d.gp
        if d.kind == 'sold':
            sold += 1
        else:
            bought += 1
    return Record({'count': len(deals), 'net': net, 'sold': sold, 'bought': bought})


def _pad(text, width):
    return text[0:width] if len(text) >= width else text + ' ' * (width - len(text))


def _pad_start(text, width):
    return text if len(text) >= width else ' ' * (width - len(text)) + text


def deal_line(input):
    """One line of the deal log, in columns that line up down the list. input has clock, customer, kind, count,
    item, gp and mixed."""
    arrow = '+' if input.kind == 'sold' else '-'
    more = ' +more' if input.mixed else ''
    what = _pad_start(format_gp(input.count), 5) + ' ' + input.item + more
    money = ('+' if input.gp >= 0 else '') + format_gp(input.gp)
    verb = 'sold' if input.kind == 'sold' else 'bght'
    return f'{input.clock}  {_pad(input.customer, 12)} {arrow} {verb} {_pad(what, 20)} {_pad_start(money, 9)}'


def clock_of(at_ms):
    """hh:mm:ss in the operator's own clock."""
    # pocketpy's localtime() reads only now, so the zone's offset is taken from it and applied to at_ms.
    now = time.localtime()
    day = 86400
    offset = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec - int(time.time()) % day) % day
    seconds = (int(at_ms // 1000) + offset) % day
    return ':'.join([str(n).rjust(2, '0') for n in [seconds // 3600, (seconds // 60) % 60, seconds % 60]])

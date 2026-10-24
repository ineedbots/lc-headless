# A player shop: stands at a bank, buys and sells what an order book lists, quotes in public chat ("buying 100
# iron ore"), prices whatever a customer puts up, and declines any trade that doesn't match what it quoted:
# rs2b0t's MarketMaker (MIT, see thirdparty/rs2b0t). The book is the account's own, under the PriceBooks
# settings (see rs2004.market's price_book).

import math
import time

from rs2004.banksort import sort_bank
from rs2004.catalogs import Record
from rs2004.market import CHAT_LIMIT, HELP_LINES, Ledger, PriceBooks, appraise, client_name, describe_appraisal, display_name
from rs2004.market import format_ambiguous, format_gp, format_price_list, live_catalog, normalise_offer, noted_id, offer_covers
from rs2004.market import offers_match, parse_command, resolve_prices, row_valid, sale_items, sale_name, sale_price, sale_stock
from rs2004.market import truncate_chat, unnoted_id
from bots.marketmaker.logic import Desk, RateLimiter, advertise_due, bank_before_serving, buy_owes_settle, clock_of, deal_line
from bots.marketmaker.logic import deal_of, deal_totals, decide_beat, float_shortfall, listed_rows, resolve_quote, settle_due
from bots.marketmaker.logic import settle_runs, side_signature, trade_is_stalled, window_candidates

BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
COIN_NAME = 'Coins'
# Why: fake_coins shares the "Coins" name and stackability, so real currency is pinned to obj 995.
COIN_ID = 995
CHAT_GAP_MS = 2000
CHAT_REPEAT_MS = 15000
CHAT_BACKLOG_CAP = 6
# Lines heard and not yet handled, the most kept.
HEARD_CAP = 40
DEAL_LOG_CAP = 250
STOCK_TRIES = 2
COMMANDS_PER_WINDOW = 3
COMMAND_WINDOW_MS = 10000
COMMAND_PENALTY_MS = 30000
RESET_EVERY_TICKS = 1000
RESET_EVERY_MS = RESET_EVERY_TICKS * 600
INTENT_CAP = 24
BANK_REACH = 12
# Why: Recover walks back with radius 1, so a leash under that never reads as arrived and the shop paces for ever.
SPOT_LEASH = 1
ADVERTISE_ITEMS = 4
STILL_BEATS = 3
REOFFER_CAP = 12
WAIT_BEATS = 25
FAILED_TRADE_LIMIT = 5
# Why: the engine shuts the offer screen a tick before it opens the confirm screen, so a bare "not open" read
# drops a trade that's completing normally.
TRADE_GONE_MS = 3000
OPEN_WAIT_MS = 10000
BANK_BACKOFF_MS = 30000
DEFAULT_SPOT = Tile(2725, 3491, 0)

SETTINGS = {
    'price_book': SettingDef('string', '', 'Order book', options_from='price_books',
                             help="the name of one of the account's PriceBooks (see the docs' market section)"),
    'spot': SettingDef('tile', DEFAULT_SPOT, 'Stand tile (x,z)', help='where the shop stands between trades; defaults to the middle of the Seers bank floor'),
    'advertise_seconds': SettingDef('number', 60, 'Advertise every (s)', min=0, max=600, help='0 turns advertising off; under 30 reads as spam'),
    'engagement_timeout_seconds': SettingDef('number', 90, 'Transaction window (s)', min=15, max=600, help='a trade that runs past this is declined and the customer is cooled off'),
    'intent_seconds': SettingDef('number', 90, 'Buy request lifetime (s)', min=15, max=600, help='how long "buy 100 iron ore" stays live before the bot forgets it'),
    'cooldown_seconds': SettingDef('number', 15, 'Cooldown after a failed trade (s)', min=0, max=3600, help='a customer who opens a trade and does not finish it is ignored for this long'),
    'coin_float': SettingDef('number', 200000, 'Coins to carry (float)', min=0, max=100000000, help='the most the shop can pay in one trade, since only coins in the pack can be offered'),
    'blacklist': SettingDef('string[]', [], 'Refuse these names'),
}


def now_ms():
    return time.time() * 1000


def same_name(a, b):
    return a.strip().lower() == b.strip().lower()


def bare_name(username):
    """The name without the @cr1@ or @cr2@ the client puts before a moderator's, for the crown."""
    raw = (username or '').strip()
    if len(raw) >= 5 and raw.startswith('@cr') and '0' <= raw[3] and raw[3] <= '9' and raw[4] == '@':
        return raw[5:]
    return raw


class Accepted:
    """What was on each side the moment the bot accepted, as {id: count}: give is ours, get theirs."""

    def __init__(self, give, get):
        self.give = give
        self.get = get


class DeskView:
    """What the bot can hand over and pay with now: the pack, plus whatever is already on its own side."""

    def __init__(self, bot, mine):
        self.bot = bot
        self.mine = mine
        self.purse = bot.pack_coins() + mine.get(bot.coin_id, 0)

    def available(self, id):
        return self.bot.pack_count(id) + self.mine.get(id, 0)

    def held(self, id):
        return self.bot.ledger.held(id) + self.bot.pack_count(id) + self.mine.get(id, 0)


class MarketMaker(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.book = None
        self.coin_id = COIN_ID
        self.ledger = Ledger()
        self.desk = Desk(INTENT_CAP)
        self.deals = []
        self.limiter = RateLimiter(COMMANDS_PER_WINDOW, COMMAND_WINDOW_MS, COMMAND_PENALTY_MS)
        self.failed_trades = {}
        self.pending = []
        self.said_recently = {}
        self.heard = []
        self.trade_requests = set()
        self.last_said_at = 0
        self.trade_closed_at = None
        self.last_told = ''
        self.bank_backoff_until = 0
        self.last_stray_log = 0
        self.last_advertise_at = 0
        self.last_reset_at = 0
        self.reset_asked = False
        self.settle_owed = False
        self.sort_owed = False
        self.advertise_cursor = 0
        self.advert_cycle = 0
        self.status = 'starting'
        self.bought = 0
        self.sold = 0
        self.refused = 0
        self.gp_in = 0
        self.gp_out = 0
        self.started_at = time.time()

        # Why: reading the catalog before the cache's objs are in reports the coin as missing, the same symptom as a
        # genuine cache mismatch.
        yield from execution.delay_until(lambda: len(live_catalog().items) > 0, 15000)
        self.cat = live_catalog()
        coin = self.cat.by_id.get(COIN_ID)
        if coin is None or coin.name != COIN_NAME or not coin.stackable:
            self.log(f"obj {COIN_ID} is '{coin.name if coin is not None else 'missing'}', not stackable {COIN_NAME} — the cache does not match this build, stopping")
            self.request_finish('coin id does not match the cache')
            return
        self.spot = self.settings.tile('spot', DEFAULT_SPOT)
        self.window_ms = self.settings.num('engagement_timeout_seconds', 90) * 1000
        self.intent_ttl_ms = self.settings.num('intent_seconds', 90) * 1000
        self.cooldown_ms = self.settings.num('cooldown_seconds', 15) * 1000
        self.advertise_seconds = self.settings.num('advertise_seconds', 60)
        self.coin_float = self.settings.num('coin_float', 200000)
        self.blacklist = [n.strip().lower() for n in self.settings.list('blacklist', []) if n.strip()]
        book_name = self.settings.str('price_book', '')
        self.book = PriceBooks.by_name(book_name)
        if self.book is None or len(self.book.rows) == 0:
            self.log(f"order book '{book_name}' is missing or empty, stopping")
            self.request_finish('no order book')
            return
        self.sort_owed = True
        near = nearest_bank(self.spot)
        reach = None
        if near is not None:
            t = near['tile']
            reach = self.spot.distance_to(Tile(t['x'], t['z'], t['level']))
        if reach is None or reach > BANK_REACH:
            where = f'{reach} tiles' if reach is not None else 'nowhere'
            self.log(f"stand tile ({self.spot.x},{self.spot.z}) is {where} from a bank (nearest: {near['name'] if near is not None else 'none'}) — stopping")
            self.request_finish('stand tile is not at a bank')
            return
        self.last_advertise_at = now_ms()
        self.log(f"MarketMaker — book '{self.book.name}', {len(self.book.rows)} items, {self.book.margin}% spread, at {near['name']}")
        read = yield from self.refresh_ledger()
        if not read:
            self.log('could not read the bank at startup — stopping rather than trade stock I cannot prove')
            self.request_finish('bank unreadable')
            return
        self.on('chat_message', self.heard_line)
        self.add(Recover(self), ServeWindow(self), OpenWindow(self), Restock(self), Settle(self), Advertise(self), Listen(self))

    def loop(self):
        """Listening and talking aren't tasks.

        Why: in the lowest task the shop would go deaf and mute for the length of any bank trip."""
        self.pump_chat()
        self.drain_chat()
        if self.reset_asked:
            self.reset_asked = False
            yield from self.reset_state()
        if self.at_station() and not self.trade_stalled():
            # Why: standing open is the work, and it makes no xp and no change of tile, so the stall guard would
            # restart a healthy shop unless this says otherwise.
            execution.note_progress()
        result = yield from TaskBot.loop(self)
        return result

    # Chat.

    def heard_line(self, e):
        if e.type == 'public' or e.type == 'trade_request':
            self.heard.append((e.type, e.username, e.text))
            while len(self.heard) > HEARD_CAP:
                self.heard.pop(0)

    def pump_chat(self):
        """Acts on what's been said since the last pass. Here chat arrives as events, where rs2b0t reads the chat
        box's last lines and works out which are new (fresh_chat_lines)."""
        me = game.my_name() or ''
        now = now_ms()
        lines = self.heard
        self.heard = []
        for kind, username, text in lines:
            from_ = bare_name(username)
            if len(from_) == 0 or same_name(from_, me) or self.blocked(from_):
                continue
            if kind == 'trade_request':
                self.trade_requests.add(from_)
                continue
            # Why: the cooldown and the budget come before the parse, so a flood costs the flooder nothing to send and
            # the bot nothing to answer.
            if self.desk.on_cooldown(from_, now) or not self.limiter.allow(from_, now):
                continue
            self.handle_command(from_, text or '')

    def say(self, text):
        """Queues a line; the queue drains at a pace that doesn't read as spam.

        Why: the backlog is capped and drops the oldest, so no flood can push the bot minutes behind."""
        line = truncate_chat(text)
        if len(line) == 0 or len([p for p in self.pending if p == line]) > 0:
            return
        self.pending.append(line)
        while len(self.pending) > CHAT_BACKLOG_CAP:
            self.pending.pop(0)

    def drain_chat(self):
        now = now_ms()
        if len(self.pending) == 0 or now - self.last_said_at < CHAT_GAP_MS:
            return
        line = self.pending.pop(0)
        said_at = self.said_recently.get(line)
        if said_at is not None and now - said_at < CHAT_REPEAT_MS:
            return
        chat.say(line)
        self.last_said_at = now
        self.said_recently[line] = now

    def blocked(self, name):
        return name.strip().lower() in self.blacklist

    # Where the shop stands.

    def at_station(self):
        """Where the shop belongs: on its stand tile, with nothing in the way.

        Why: the offer screen shuts a tick before the confirm opens, and a shop that read that tick as off station
        walked out of its own trade, so an open window counts."""
        if trade.active() or self.desk.current() is not None:
            return True
        here = game.tile()
        return modals.main() == -1 and (here is None or here.distance_to(self.spot) <= SPOT_LEASH)

    def trade_stalled(self):
        """A window nobody is advancing, which mustn't read as the shop doing its job."""
        return trade_is_stalled(trade.active(), self.desk.current() is not None, self.desk.expired(now_ms(), self.window_ms))

    def note_stray(self, com_id):
        now = now_ms()
        if now - self.last_stray_log > 5000:
            self.last_stray_log = now
            self.log(f'stray modal {com_id} open, closing it')

    def cool_note(self):
        """How long a dropped customer waits, in words."""
        return 'Try again.' if self.cooldown_ms <= 0 else f'Ask again in {round(self.cooldown_ms / 1000)}s.'

    # Why: the sort rides the forced trip a reset owes, so the shop sorts before it serves at startup and straight
    # after a reset; the flag outlives a trip that never opened the bank.
    def settle_forced(self):
        return self.settle_owed or self.sort_owed

    def sort_bank_now(self):
        """Sorts the open bank by the bank sorter's rules, once per sort owed. Use with yield from."""
        self.status = 'sorting the bank'
        result = yield from sort_bank(self.log)
        self.sort_owed = False
        if result.sorted:
            unplaced = f', {len(result.unmatched)} item(s) the rules do not place' if len(result.unmatched) > 0 else ''
            self.log(f'bank sorted, {result.moves} move(s){unplaced}')
        else:
            self.log(f'bank sort stopped: {result.reason} after {result.moves} move(s)')

    def bank_ready(self, at_ms):
        return at_ms >= self.bank_backoff_until

    def back_off_bank(self, reason):
        self.bank_backoff_until = now_ms() + BANK_BACKOFF_MS
        self.log(f'bank trip fell short ({reason}) — backing off {BANK_BACKOFF_MS // 1000}s')

    # The pack and the bank.

    def pack_count(self, id):
        """Units of one row in the pack, noted and unnoted together."""
        noted = noted_id(self.cat, id)
        return inventory.count_by_id(id) + (0 if noted is None else inventory.count_by_id(noted))

    def sale_ready(self):
        want = self.desk.next_intent(now_ms(), self.intent_ttl_ms)
        return want is not None and sale_stock(want, self.pack_count) >= want.max_qty

    def stocked(self, id):
        """Everything the shop could put on the table, carried or banked: what a quote is sized against."""
        return self.ledger.held(id) + self.pack_count(id)

    def pack_coins(self):
        return inventory.count_by_id(self.coin_id)

    def float_short(self):
        """The coins the shop is short of its float that the bank can supply.

        Why: the bank's coins move only on a settle trip, and the ledger is read at the end of each, so this is
        right the moment Settle asks."""
        return float_shortfall(self.pack_coins(), self.ledger.held(self.coin_id), self.coin_float)

    def desk_state(self):
        """Why: an item in the offer has left the pack view, so counting the pack alone would appraise the bot as
        empty the moment it puts something up."""
        mine = normalise_offer(self.cat, trade.my_offer()) if trade.active() else {}
        return DeskView(self, mine)

    def refresh_ledger(self):
        """Reads the bank into the ledger. Use with yield from: False when the bank won't open or list."""
        if not bank.is_open():
            opened = yield from banking.open(stand=self.spot, booth_name=BOOTH_NAME, booth_op=BOOTH_OP, log=self.log)
            if not opened:
                return False
        ready = yield from execution.delay_until(lambda: bank.snapshot_ready(), 6000)
        if not ready:
            return False
        units = {}
        for item in bank.items():
            id = unnoted_id(self.cat, item.id)
            units[id] = units.get(id, 0) + item.count
        self.ledger.set_stock([Record({'id': id, 'count': units[id]}) for id in units])
        return True

    # Requests in chat.

    def handle_command(self, from_, text):
        cmd = parse_command(text)
        if cmd.kind == 'prices':
            self.list_prices('both')
        elif cmd.kind == 'buying':
            self.list_prices('buy')
        elif cmd.kind == 'selling':
            self.list_prices('sell')
        elif cmd.kind == 'help':
            for line in HELP_LINES:
                self.say(line)
        elif cmd.kind == 'reset':
            self.reset_asked = True
        elif cmd.kind == 'quoteSell':
            self.want_to_buy(from_, cmd.qty, cmd.query, cmd.qty_implied)
        elif cmd.kind == 'quoteBuy':
            # Why: selling to the bot needs no words at all, so the command is answered with the shorter path.
            target = resolve_quote(Record({'cat': self.cat, 'book': self.book, 'query': cmd.query, 'side': 'buying', 'qty_implied': cmd.qty_implied}))
            if target.kind != 'miss' or not cmd.qty_implied:
                self.say('Just trade me and put it up. I price what I see.')

    def greet(self, customer):
        """The first thing a customer hears when their window opens.

        Why: the shop's interface is invisible, and the moment someone opens a trade is the one moment they're
        certain to be looking."""
        want = self.desk.intent_for(customer, now_ms(), self.intent_ttl_ms)
        if want is None:
            self.say('Put items in and I price them as you go. To buy, say what you want first.')
            return
        each = sale_price(self.book, want) or 0
        self.say(f'{format_gp(want.max_qty)} x {sale_name(self.cat, want)} = {format_gp(want.max_qty * each)}gp. Put that up.')

    def reset_state(self):
        """Back to an empty desk: no window, nothing owed, nobody cooling off. Rate limited, since it discards
        work. Use with yield from.

        Why: the shop can tie itself up past talking to, and the alternative is an operator restarting it."""
        now = now_ms()
        since = now - self.last_reset_at
        if self.last_reset_at > 0 and since < RESET_EVERY_MS:
            self.say(f'Already reset. Ask again in {math.ceil((RESET_EVERY_MS - since) / 60000)}m.')
            return
        self.last_reset_at = now
        self.log('reset asked for in chat, clearing the desk')
        self.say('Resetting. Trade me again in a moment.')
        if trade.active():
            yield from trade.decline()
        self.desk.clear()
        self.trade_requests.clear()
        self.trade_closed_at = None
        self.last_told = ''
        self.settle_owed = True
        self.sort_owed = True
        self.status = 'reset, banking the pack'

    def _price_entries(self, rows):
        entries = []
        for r in rows:
            prices = resolve_prices(self.book, r)
            entries.append(Record({'name': display_name(self.cat, r.id), 'buy': prices.buy, 'sell': prices.sell}))
        return entries

    def list_prices(self, side):
        """The book, cut to what the shop holds."""
        listed = listed_rows(Record({'book': self.book, 'side': side, 'stocked': self.stocked}))
        if listed.empty is not None:
            self.say('Nothing listed right now.' if listed.empty == 'no-book' else 'I am out of stock right now.')
            return
        for line in format_price_list(self._price_entries(listed.rows), side):
            self.say(line)

    def want_to_buy(self, from_, want, query, qty_implied):
        target = resolve_quote(Record({'cat': self.cat, 'book': self.book, 'query': query, 'side': 'selling', 'qty_implied': qty_implied}))
        if target.kind == 'miss':
            if target.answer:
                self.say(f"I don't sell '{query}'.")
            return
        if target.kind == 'ambiguous':
            self.say(format_ambiguous(target.candidates))
            return
        order = Record({'set': target.set, 'max_qty': 0}) if target.kind == 'set' else Record({'item_id': target.id, 'max_qty': 0})
        name = sale_name(self.cat, order)
        sell = sale_price(self.book, order)
        asked = self.book.max_trade_value // sell if want == 'all' else want
        # Why: the bank is the shop's stock and the pack only what it's carrying, so the quote is sized against both,
        # and the difference is a bank trip, not a refusal.
        max_qty = min(asked, sale_stock(order, self.desk_state().held), self.book.max_trade_value // sell)
        if max_qty <= 0:
            self.say(f'I have no {name} right now.')
            return
        intent = Record({'customer': from_, 'max_qty': max_qty, 'asked_at_ms': now_ms(), 'set': order.set, 'item_id': order.item_id})
        self.desk.remember(intent)
        carried = sale_stock(order, self.pack_count) >= max_qty
        price = f'{format_gp(max_qty)} x {name} = {format_gp(max_qty * sell)}gp ({format_gp(sell)}ea).'
        self.say(f"{price} {'Trade me.' if carried else 'Give me a moment.'}")

    # The trade window.

    def appraise_now(self, customer):
        """What the bot should have on its side, given what the customer has on theirs."""
        their_offer = trade.their_offer()
        intent = self.desk.intent_for(customer, now_ms(), self.intent_ttl_ms)
        if intent is not None and len([o for o in their_offer if o.id != self.coin_id]) > 0:
            # Why: once the shop has staked the goods it asked to be paid for, it stays a sale and names the items it
            # won't count; but nothing staked means the request was never acted on, so the goods in front of it win.
            mine = normalise_offer(self.cat, trade.my_offer())
            if len([id for id in sale_items(intent) if mine.get(id, 0) > 0]) == 0:
                self.desk.forget(customer)
                intent = None
        return appraise(self.book, self.cat, self.desk_state(), self.coin_id, their_offer, intent)

    def tell_appraisal(self, a):
        """Tells the customer what their side is worth, once per valuation."""
        line = describe_appraisal(a)
        if line != self.last_told:
            self.last_told = line
            self.say(line)

    def put_up(self, owe):
        """Clears our side and builds it again from what we owe. Use with yield from.

        Why: two operations that can't drift, where nudging item by item has to reason about what's already up."""
        yield from trade.remove_all()
        for id in owe:
            want = owe[id]
            # Why: this name aims a click at the pack, so it's the client's own, never the shop's label.
            name = client_name(self.cat, id)
            if name is None:
                return False
            left = want
            noted = noted_id(self.cat, id)
            for candidate in ([id] if noted is None else [noted, id]):
                if left <= 0:
                    break
                have = inventory.count_by_id(candidate)
                if have <= 0:
                    continue
                take = min(left, have)
                put = yield from trade.offer(name, take, lambda i: i.id == candidate)
                if not put:
                    return False
                expected = want - left + take
                shown = yield from execution.delay_until(lambda: normalise_offer(self.cat, trade.my_offer()).get(id, 0) >= expected, 4000)
                if not shown:
                    return False
                left -= take
            if left > 0:
                return False
        return True

    def confirm_matches(self, accepted):
        """Whether the confirm screen shows what was accepted; None until it has filled."""
        if not trade.confirm_ready():
            return None
        return offers_match(normalise_offer(self.cat, trade.my_offer()), accepted.give) and offers_match(normalise_offer(self.cat, trade.their_offer()), accepted.get)

    def completed(self, accepted, customer):
        self.failed_trades.pop(customer.strip().lower(), None)
        for id in accepted.give:
            if id == self.coin_id:
                self.gp_out += accepted.give[id]
            else:
                self.ledger.add(id, -accepted.give[id])
        for id in accepted.get:
            if id == self.coin_id:
                self.gp_in += accepted.get[id]
            else:
                self.ledger.add(id, accepted.get[id])
        if buy_owes_settle(accepted.give, self.coin_id):
            self.bought += 1
            # Why: what was bought goes to the bank before anyone else is served, so the forced trip is owed here too.
            self.settle_owed = True
        else:
            self.sold += 1
        deal = deal_of(accepted.give, accepted.get, self.coin_id, customer, now_ms())
        if deal is not None:
            self.deals.insert(0, deal)
            self.deals = self.deals[:DEAL_LOG_CAP]
        self.desk.forget(customer)
        self.desk.close()
        self.trade_closed_at = None
        self.last_told = ''
        self.log(f'trade complete with {customer}')
        self.say(f'Thanks {customer}. Pleasure doing business.')

    def release(self, customer, reason):
        """Lets a customer go without a cooldown, for a failure that wasn't theirs."""
        self.desk.close()
        self.trade_closed_at = None
        self.last_told = ''
        self.log(f'released {customer}: {reason}')

    def abandon(self, customer, reason):
        """Drops the window in flight and ignores the customer for a while, and for good after FAILED_TRADE_LIMIT
        in a row.

        Why: a stall and a probe of the refusal rules look the same from here, so the cost lands on whoever failed
        the trade rather than on everyone behind them."""
        window = self.desk.current()
        if window is not None and window.saw_open and same_name(window.customer, customer) and not self.blocked(customer):
            name = customer.strip().lower()
            failures = self.failed_trades.get(name, 0) + 1
            if failures >= FAILED_TRADE_LIMIT:
                self.blacklist.append(name)
                self.failed_trades.pop(name, None)
                settings_store.save('MarketMaker', 'blacklist', list(self.blacklist))
                self.log(f'blacklisted {customer} after {failures} consecutive failed trades')
            else:
                self.failed_trades[name] = failures
        self.refused += 1
        self.desk.forget(customer)
        self.desk.close()
        self.trade_closed_at = None
        self.last_told = ''
        if self.cooldown_ms > 0:
            self.desk.cool(customer, now_ms() + self.cooldown_ms)
        self.log(f'dropped {customer}: {reason}')

    def describe_window(self, a):
        """One line, since the harness shows a bounded number of log lines a poll."""
        def show(m):
            parts = []
            for id in m:
                r = self.cat.by_id.get(id)
                parts.append(f'{r.name if r is not None else id}({id})x{m[id]}')
            return '+'.join(parts) or 'nothing'

        mine = normalise_offer(self.cat, trade.my_offer())
        theirs = normalise_offer(self.cat, trade.their_offer())
        return f'window: owe={show(a.owe)}; mine={show(mine)} theirs={show(theirs)}'

    def drop_expired(self):
        """Ages out the window's deadline and an abandoned window."""
        now = now_ms()
        open_ = self.desk.current()
        if open_ is not None and self.desk.expired(now, self.window_ms):
            self.say(f'Trade declined. {self.cool_note()}')
            self.abandon(open_.customer, 'ran past the transaction window')
            return
        # Why: a request sent as a modal closes can open the window on their client alone, leaving the bot holding
        # one it can't see until the deadline.
        if open_ is not None and not open_.saw_open and now - open_.opened_at_ms > OPEN_WAIT_MS:
            self.say('That did not open. Trade me again.')
            self.release(open_.customer, 'the window never opened on my side')
            return
        if open_ is not None and open_.saw_open and not trade.active():
            if self.trade_closed_at is None:
                self.trade_closed_at = now
            elif now - self.trade_closed_at >= TRADE_GONE_MS:
                self.say(f'Trade closed. {self.cool_note()}')
                self.abandon(open_.customer, 'customer closed the window')
        else:
            self.trade_closed_at = None
        self.desk.prune_intents(now, self.intent_ttl_ms)

    # Advertising.

    def advertise_now(self):
        rows = [r for r in self.book.rows if row_valid(self.book, r) and (r.buying or r.selling)]
        if len(rows) == 0:
            return
        picked = []
        for i in range(min(ADVERTISE_ITEMS, len(rows))):
            picked.append(rows[(self.advertise_cursor + i) % len(rows)])
        self.advertise_cursor = (self.advertise_cursor + len(picked)) % len(rows)
        # Why: a price list alone never tells a passer-by how to trade at all, so every other line is the how-to.
        self.advert_cycle += 1
        if self.advert_cycle % 2 == 0:
            self.say(HELP_LINES[0])
            self.say(HELP_LINES[1])
        else:
            lines = format_price_list(self._price_entries(picked), 'both')
            if len(lines) > 0:
                self.say(truncate_chat(('Trading: ' + lines[0])[0:CHAT_LIMIT]))
        self.last_advertise_at = now_ms()

    def advertise_is_due(self):
        return advertise_due(self.last_advertise_at, now_ms(), self.advertise_seconds)

    def on_progress_report(self):
        minutes = (time.time() - self.started_at) / 60
        totals = deal_totals(self.deals)
        window = self.desk.current() if self.book is not None else None
        report = {
            'Status': self.status,
            'Runtime': f'{int(minutes)}m',
            'Book': f'{self.book.name}, {self.book.margin}% spread' if self.book is not None else '-',
            'Sold': self.sold,
            'Bought': self.bought,
            'Refused': self.refused,
            'GP in': format_gp(self.gp_in),
            'GP out': format_gp(self.gp_out),
            'Net': ('+' if totals.net >= 0 else '') + format_gp(totals.net),
            'Per hour': format_gp(round(totals.net / (minutes / 60))) if minutes > 1 else '-',
            'Serving': window.customer if window is not None else 'nobody',
            'Float': format_gp(self.pack_coins()),
        }
        for i in range(min(3, len(self.deals))):
            d = self.deals[i]
            report[f'Deal {i + 1}'] = deal_line(Record({'clock': clock_of(d.at_ms), 'customer': d.customer, 'kind': d.kind, 'count': d.count,
                                                        'item': display_name(self.cat, d.item_id), 'gp': d.gp, 'mixed': d.mixed}))
        return report


class Recover(Task):
    """Closes stray modals and goes back to the stand tile."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return not self.bot.at_station()

    def execute(self):
        main = modals.main()
        if main != -1:
            self.bot.status = 'closing a stray window'
            self.bot.note_stray(main)
            yield from modals.close()
            yield from execution.delay_ticks(1)
            return
        self.bot.status = 'walking back to the stand'
        yield from traversal.walk_resilient(self.bot.spot, radius=1, timeout_ms=60000, log=self.bot.log)


class ServeWindow(Task):
    """The window is the transaction, and owns the loop while it's open, since movement cancels it.

    Why: the bot's side is worked out afresh from the customer's every beat, so nothing here outlives the window."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        w = self.bot.desk.current()
        return w is not None and (trade.active() or w.expected_receipt is not None)

    def execute(self):
        bot = self.bot
        w = bot.desk.current()
        if not trade.active() and w.expected_receipt is not None:
            yield from self.settle(w)
            return
        if not w.saw_open:
            bot.log(f'window with {w.customer} is open on my side')
            bot.greet(w.customer)
        w.saw_open = True
        partner = trade.partner()
        if partner is not None and not same_name(partner, w.customer):
            bot.log(f'window opened with {partner}, not {w.customer} — declining')
            yield from trade.decline()
            bot.release(w.customer, 'someone else opened the window')
            return
        if bot.trade_stalled():
            yield from trade.decline()
            bot.abandon(w.customer, 'ran past the transaction window')
            return
        if trade.on_confirm_screen():
            yield from self.confirm(w)
            return

        a = bot.appraise_now(w.customer)
        mine = normalise_offer(bot.cat, trade.my_offer())
        theirs = normalise_offer(bot.cat, trade.their_offer())
        their_sig = side_signature(theirs)
        beat = decide_beat(Record({
            'their_sig': their_sig,
            'window': w,
            'owe_matched': offers_match(mine, a.owe),
            'want_matched': offer_covers(theirs, a.want),
            'owe_anything': len(a.owe) > 0,
            'owe_fixed': a.kind == 'sell',
            'still_beats_needed': STILL_BEATS,
            're_offer_cap': REOFFER_CAP,
            'wait_cap': WAIT_BEATS,
        }))
        w.waited = w.waited + 1 if beat.do == 'wait' else 0
        if their_sig == w.last_sig:
            w.still_beats += 1
        else:
            w.still_beats = 0
            w.last_sig = their_sig
            bot.tell_appraisal(a)
        bot.status = f'{w.customer}: {beat.do}'
        if beat.do == 'offer':
            w.re_offers += 1
            put = yield from bot.put_up(a.owe)
            if not put:
                bot.log(bot.describe_window(a))
                yield from trade.decline()
                bot.abandon(w.customer, 'could not put up what I owe')
        elif beat.do == 'accept':
            give = {}
            for id in a.owe:
                give[id] = a.owe[id]
            w.accepted = Accepted(give, theirs)
            trade.accept()
        elif beat.do == 'give-up':
            bot.say(f'Trade declined: {beat.reason}. {bot.cool_note()}')
            yield from trade.decline()
            bot.abandon(w.customer, beat.reason)
        else:
            yield from execution.delay_ticks(1)

    def confirm(self, w):
        """The screen the accept lands on, read again from its own lists."""
        bot = self.bot
        accepted = w.accepted
        if accepted is None:
            yield from trade.decline()
            bot.abandon(w.customer, 'confirm screen with nothing agreed')
            return
        ok = bot.confirm_matches(accepted)
        if ok is None:
            yield from execution.delay_ticks(1)
            return
        if not ok:
            bot.say(f'Trade declined: the confirm screen changed. {bot.cool_note()}')
            yield from trade.decline()
            bot.abandon(w.customer, 'confirm screen does not match what was accepted')
            return
        if w.expected_receipt is None:
            w.expected_receipt = [Record({'id': id, 'expected': bot.pack_count(id) + accepted.get[id]}) for id in accepted.get if id not in accepted.give]
        trade.accept()
        yield from execution.delay_until(lambda: not trade.active(), 8000)
        if not trade.active():
            yield from self.settle(w)

    def settle(self, w):
        bot = self.bot
        received = w.expected_receipt if w.expected_receipt is not None else []
        settled = yield from execution.delay_until(lambda: len(received) > 0 and len([r for r in received if bot.pack_count(r.id) < r.expected]) == 0, TRADE_GONE_MS)
        if settled and w.accepted is not None:
            bot.completed(w.accepted, w.customer)
        else:
            bot.abandon(w.customer, 'trade closed without receiving the agreed items')


class OpenWindow(Task):
    """Takes whoever asked first. The engine turns the rest away while a window is open."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.told_waiting = {}

    def ready_for(self, name, now):
        """A request that can open now: one to be dropped, or one whose goods are in the pack."""
        bot = self.bot
        if bot.blocked(name) or bot.desk.on_cooldown(name, now):
            return True
        want = bot.desk.intent_for(name, now, bot.intent_ttl_ms)
        return want is None or sale_stock(want, bot.pack_count) >= want.max_qty

    def validate(self):
        bot = self.bot
        # Why: a request while the bank is still closing opens the window on their client and not ours.
        if bot.desk.current() is not None or len(bot.trade_requests) == 0 or trade.active() or modals.main() != -1:
            return False
        # Why: Settle sits below this task, so a pack with no room has to yield the tick, or the queue keeps it
        # opening windows it can't take goods into.
        now = now_ms()
        if bank_before_serving(inventory.free(), bot.pack_coins(), bot.coin_float, bot.bank_ready(now), bot.settle_forced(), bot.sale_ready()):
            return False
        # Why: this runs ahead of Restock, so claiming the tick when every request waits on a bank trip would starve
        # the fetch that lets any of them open.
        return len([name for name in self.candidates(now) if self.ready_for(name, now)]) > 0

    def candidates(self, now):
        """Whose request may open a window now: a sale in progress first, the rest told why, once.

        Why: otherwise the goods fetched for a sale sit in a pack another customer is filling."""
        bot = self.bot
        sale = bot.desk.next_intent(now, bot.intent_ttl_ms)
        names = list(bot.trade_requests)
        picked = window_candidates(names, sale.customer if sale is not None else None)
        if sale is not None:
            for name in names:
                if name not in picked and self.told_waiting.get(name) != sale.customer:
                    self.told_waiting[name] = sale.customer
                    bot.say(f'{name}, serving {sale.customer} first. One moment.')
        return picked

    def execute(self):
        bot = self.bot
        now = now_ms()
        for name in self.candidates(now):
            if bot.blocked(name) or bot.desk.on_cooldown(name, now):
                bot.trade_requests.discard(name)
                continue
            # Why: opening before the goods are in the pack strands the window, since Restock can't run while one is
            # open.
            want = bot.desk.intent_for(name, now, bot.intent_ttl_ms)
            if want is not None and sale_stock(want, bot.pack_count) < want.max_qty:
                bot.say(f'Fetching your {sale_name(bot.cat, want)}, one moment.')
                continue
            bot.trade_requests.discard(name)
            bot.status = f'opening a window with {name}'
            bot.log(f'opening a window with {name}')
            bot.desk.open(name, now)
            if not trade.request(name):
                bot.log(f'{name} is not in range to trade')
                bot.say(f'{name}, stand next to me.')
            return
        yield from execution.delay_ticks(1)


class Restock(Task):
    """Fetches the goods a chat request named, before its customer turns up."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        bot = self.bot
        if trade.active() or bot.desk.current() is not None:
            return False
        # Why: a trip that's owed runs before the fetch, or Settle's deposit takes the fetched goods back with the
        # takings.
        now = now_ms()
        if not bot.bank_ready(now) or settle_due(inventory.free(), bot.pack_coins(), bot.coin_float, bot.settle_forced(), bot.sale_ready()):
            return False
        want = bot.desk.next_intent(now, bot.intent_ttl_ms)
        return want is not None and sale_stock(want, bot.pack_count) < want.max_qty

    def execute(self):
        bot = self.bot
        want = bot.desk.next_intent(now_ms(), bot.intent_ttl_ms)
        name = sale_name(bot.cat, want)
        bot.status = f'fetching {name} for {want.customer}'
        opened = yield from banking.open(stand=bot.spot, booth_name=BOOTH_NAME, booth_op=BOOTH_OP, log=bot.log)
        if not opened:
            bot.log('could not open the bank to restock')
            return
        yield from bank.set_note_mode(True)
        for id in sale_items(want):
            short = want.max_qty - bot.pack_count(id)
            if short <= 0:
                continue
            yield from bank.withdraw_x_by_id(id, short, noted_id(bot.cat, id))
            # Why: note mode delivers the note's id, so the withdrawal is judged on the units that landed.
            landed = yield from execution.delay_until(lambda: bot.pack_count(id) >= want.max_qty, 5000)
            if not landed:
                bot.back_off_bank(f'{display_name(bot.cat, id)} {bot.pack_count(id)}/{want.max_qty}')
        yield from bot.refresh_ledger()
        yield from bank.close()
        # Why: the modal reads closed a tick before the engine has settled it, and a trade request in that gap opens
        # the window on the customer's client alone.
        yield from execution.delay_ticks(2)
        got = sale_stock(want, bot.pack_count)
        if got >= want.max_qty:
            bot.desk.renew(want.customer, now_ms())
            # Why: the chat filter masks a name and the letters after it, so the name goes last.
            bot.say(f'Got your {name}. Trade me, {want.customer}.')
            return
        if got > 0:
            # Why: the order is cut to what arrived, or Restock keeps going back for the rest and Settle never runs.
            bot.desk.limit_to(want.customer, got)
            bot.desk.renew(want.customer, now_ms())
            bot.say(f'I could only get {format_gp(got)} x {name}. Trade me, {want.customer}.')
            return
        if bot.desk.missed_stock(want.customer, STOCK_TRIES):
            bot.say(f'{want.customer}, I could not get your {name}. Ask me again.')
            bot.desk.forget(want.customer)


class Settle(Task):
    """Banks the takings and keeps the coin float topped up."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        bot = self.bot
        now = now_ms()
        if trade.active() or bot.desk.current() is not None or not bot.bank_ready(now):
            return False
        due = settle_due(inventory.free(), bot.pack_coins(), bot.coin_float, bot.settle_forced(), bot.sale_ready())
        return settle_runs(due, bot.float_short() > 0, bot.desk.next_intent(now, bot.intent_ttl_ms) is not None)

    def execute(self):
        bot = self.bot
        bot.settle_owed = False
        bot.status = 'banking the takings'
        opened = yield from banking.open(stand=bot.spot, booth_name=BOOTH_NAME, booth_op=BOOTH_OP, log=bot.log)
        if not opened:
            bot.back_off_bank('could not open the bank')
            return
        if inventory.used() > 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
        # Why: the float is read off the live bank rather than the ledger, which goes stale when a trip has gone wrong.
        short = bot.coin_float - bot.pack_coins()
        in_bank = bank.count_by_id(bot.coin_id)
        if short > 0 and in_bank > 0:
            yield from bank.set_note_mode(False)
            yield from bank.withdraw_x_by_id(bot.coin_id, min(short, in_bank))
            yield from execution.delay_until(lambda: bot.pack_coins() >= min(bot.coin_float, in_bank), 5000)
        read = yield from bot.refresh_ledger()
        if not read or bot.pack_coins() < min(bot.coin_float, in_bank):
            bot.back_off_bank(f'float {bot.pack_coins()}/{bot.coin_float}')
        if bot.sort_owed:
            yield from bot.sort_bank_now()
            yield from bot.refresh_ledger()
        yield from bank.close()
        yield from execution.delay_ticks(2)


class Advertise(Task):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return not trade.active() and self.bot.advertise_is_due()

    def execute(self):
        self.bot.advertise_now()
        yield from execution.delay_ticks(1)


class Listen(Task):
    """Always last: ages out the window. Chat is pumped from the loop, not here."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def validate(self):
        return True

    def execute(self):
        w = self.bot.desk.current()
        self.bot.status = f'serving {w.customer}' if w is not None else 'open for business'
        self.bot.drop_expired()
        yield from execution.delay_ticks(1)


BOT = define_bot(
    name='MarketMaker',
    create=MarketMaker,
    description='Player shop — stands at a bank, buys and sells the items in an order book, quotes in public chat ("buy 100 iron ore"), and declines any trade that does not match what it quoted',
    category='Money making',
    tags=['trading', 'shop', 'bank', 'chat', 'afk'],
    settings_schema=SETTINGS,
)

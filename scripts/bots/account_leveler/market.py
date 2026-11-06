"""Ported from rs2b0t's src/bot/scripts/AccountLeveler/market.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs import names_match
from rs2004.market.catalog import live_catalog
from rs2004.events import events
from rs2004.execution import event_signal
from bots.account_leveler.travel import leveler_travel_zones
from bots.account_leveler.record import Record

__all__ = ['SeersAxeBuyer']

MAKER = 'seers market'
STAND = Tile(2725, 3491, 0)
AXES = Record({'Rune axe': 1359, 'Adamant axe': 1357, 'Mithril axe': 1355})
COINS = 995
RESERVE = 200


def safe():
    return game.scene_ready() and not game.in_combat() and not event_signal.pending()


def signature(line):
    return f'{line.type}|{line.username}|{line.text}'


def exact(items, ids, count):
    return len(items) == 1 and (items[0].id in ids) and items[0].count == count


def quote(item, budget, read_lines):
    seen = list(read_lines())
    if not chat.say(f'buying 1 {item}'):
        return None
    for poll in range(20):
        if not safe():
            break
        current = list(read_lines())
        fresh = [line for line in current if line not in seen]
        seen = current
        for line in fresh:
            if line.type != 'public' or not names_match(line.username or '', MAKER):
                continue
            if line.text.lower() == f'i have no {item.lower()} right now.':
                return None
            price = quoted_price(line.text, item, budget)
            if price is not None:
                return price
        yield from execution.delay(500)
    return None


def safe_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= 9007199254740991


def quoted_price(text, item, budget):
    prefix = f'1 x {item} = '.lower()
    lower = text.lower()
    if not lower.startswith(prefix) or 'gp (' not in lower or 'ea).' not in lower:
        return None
    rest = lower[len(prefix):]
    price_text, unit_text = rest.split('gp (')
    unit_text = unit_text.split('ea).')[0]
    price_text = price_text.replace(',', '')
    unit_text = unit_text.replace(',', '')
    if not price_text or not unit_text or any([c not in '0123456789' for c in price_text + unit_text]):
        return None
    price = int(price_text)
    return price if safe_integer(price) and price > 0 and price == int(unit_text) and price <= budget else None


class SeersAxeBuyer:
    _attempted = False

    def buy(self, request):
        self._lines = []
        subscription = events.on('chat_message', self._receive)
        try:
            result = yield from self._buy(request)
        except Exception as error:
            subscription()
            if trade.active():
                trade.decline()
            raise error
        subscription()
        if trade.active():
            trade.decline()
        return result

    def _receive(self, message):
        self._lines.insert(0, message)
        self._lines = self._lines[:100]

    def _chat_lines(self):
        return self._lines

    def _buy(self, request):
        id = AXES.get(request.item)
        if self._attempted or request.world != 1 or not id or not safe_integer(request.max_price) or request.max_price <= 0 or not safe() or trade.active() or inventory.free() < 1:
            return False
        catalog = live_catalog()
        if (catalog.by_id.get(id).name if catalog.by_id.get(id) is not None else None) != request.item:
            return False
        noted = catalog.noted_of.get(id)
        ids = ([id] if noted is None else [id, noted])

        def held():
            return sum([inventory.count_by_id(item_id) for item_id in ids])

        before = held()
        coins = inventory.count_by_id(COINS)
        budget = min(request.max_price, coins - RESERVE)
        if before > 0 or budget < 1:
            return False
        self._attempted = True
        _fn1 = getattr(request, 'log', None)
        if _fn1 is not None:
            _fn1(f'Trying {MAKER} for one {request.item}, up to {budget} coins')
        _w2 = yield from traversal.walk_resilient(STAND, radius=3, attempts=1, timeout_ms=60000, avoid_zones=leveler_travel_zones(), log=request.log)
        if not (_w2) or not safe():
            return False
        here = game.tile()
        if here is None or STAND.distance_to(here) > 5 or not players.query().name(MAKER).within(5).first():
            return False
        price = yield from quote(request.item, budget, self._chat_lines)
        if price is None or not safe() or trade.active():
            return False
        if not (trade.request(MAKER)):
            return False
        poll = 0
        while poll < 40 and safe() and (not trade.on_offer_screen() or trade.partner() is None):
            if trade.on_confirm_screen():
                return False
            yield from execution.delay(500)
            poll += 1
        if not safe() or not trade.on_offer_screen() or not names_match((trade.partner() if trade.partner() is not None else ''), MAKER) or len(trade.my_offer()) > 0:
            return False
        coins_before_trade = inventory.count_by_id(COINS)
        _c3 = coins_before_trade < price + RESERVE
        if not _c3:
            _w4 = yield from trade.offer('Coins', price, lambda item: item.id == COINS)
            _c3 = not (_w4)
        if _c3:
            return False
        accepted = False
        confirmed = False
        for poll in range(60):
            if not (safe()):
                break
            if trade.on_offer_screen():
                if confirmed or not names_match((trade.partner() if trade.partner() is not None else ''), MAKER) or not exact(trade.my_offer(), [COINS], price):
                    return False
                theirs = trade.their_offer()
                if len(theirs) > 0 and not exact(theirs, ids, 1):
                    return False
                if exact(theirs, ids, 1):
                    accepted = trade.accept()
            elif trade.on_confirm_screen():
                if not accepted or not names_match((trade.partner() if trade.partner() is not None else ''), MAKER):
                    return False
                if trade.confirm_ready():
                    offers = Record({'mine': trade.my_offer(), 'theirs': trade.their_offer()})
                    if not exact(offers.mine, [COINS], price) or not exact(offers.theirs, ids, 1):
                        return False
                    if not confirmed:
                        confirmed = trade.accept()
            else:
                if confirmed and held() == before + 1 and inventory.count_by_id(COINS) == coins_before_trade - price:
                    _fn5 = getattr(request, 'log', None)
                    if _fn5 is not None:
                        _fn5(f'Bought one {request.item} for {price} coins')
                    return True
            yield from execution.delay(500)
        return False

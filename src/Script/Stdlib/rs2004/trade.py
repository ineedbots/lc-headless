"""Shops and player trades. Mirrors rs2b0t's api/shop/Shop.ts and api/trade/Trade.ts (MIT, see thirdparty/rs2b0t).

    opened = yield from shop.open('Shop keeper')
    if opened:
        bought = yield from shop.buy('Bucket', 3)

Each interface is found by what its inventories offer, not by id: a shop's stock offers "Buy 1" and the
backpack beside it "Sell 1"; the trade's offer screen has your offer, which offers "Remove", beside theirs, and
the backpack beside it offers "Offer"; the confirm screen lists the two offers as text, yours on the left.
"""

import _core
from rs2004 import execution
from rs2004.entities import npcs, players
from rs2004.items import inventory

__all__ = ['shop', 'trade', 'shop_op_batch', 'parse_trade_partner_header', 'SELL_STACK_STEP']

OPEN_TIMEOUT_MS = 3000
LAND_TIMEOUT_MS = 3000
CLOSE_TIMEOUT_MS = 3000
COUNT_DIALOG_TIMEOUT_MS = 3000
OFFER_TIMEOUT_MS = 4000
# The engine runs at most this many clicks on interfaces a tick, and keeps the rest for later ones.
USER_OPS_PER_TICK = 5
SHOP_STEPS = (10, 5, 1)
# A stack sale asks for ten at a time, and the last click takes what's left.
SELL_STACK_STEP = 10
SELL_STACK_CLICKS = 40
REMOVE_ROUNDS = 28
FIXED_AMOUNTS = (1, 5, 10)


def _inventories(root):
    return _core.get_inventories(root) if root >= 0 else []


def _first_option(options):
    for option in options:
        if option is not None:
            return option.lower()
    return ''


def _offers(options, text):
    wanted = text.lower()
    return len([option for option in options if option is not None and option.lower() == wanted]) > 0


def _find_inventory(root, test):
    for com, type, x, options in _inventories(root):
        if type == 'inv' and test(options):
            return com
    return -1


def _items(com):
    return _core.get_inventory(com) if com >= 0 else []


def _all_items(coms):
    items = []
    for com in coms:
        items.extend(_items(com))
    return items


def _same_name(items, name):
    wanted = name.strip().lower()
    return [item for item in items if item.name is not None and item.name.lower() == wanted]


def _option_number(item, label):
    wanted = label.lower()
    for i in range(len(item._ops)):
        if item._ops[i] is not None and item._ops[i].lower() == wanted:
            return i + 1
    return -1


def _use(item, label):
    op = _option_number(item, label)
    return op != -1 and _core.inv_button(item, op)


def shop_op_batch(ops, verb, remaining):
    """The option numbers, 1 to 5, of the clicks that buy or sell remaining, 10s then 5s then 1s, as many as
    the engine runs in a tick."""
    batch = []
    left = remaining
    while len(batch) < USER_OPS_PER_TICK and left > 0:
        step = None
        for size in SHOP_STEPS:
            if size <= left and _offers(ops, f'{verb} {size}'):
                step = size
                break
        if step is None:
            break
        wanted = f'{verb} {step}'
        for i in range(len(ops)):
            if ops[i] is not None and ops[i].lower() == wanted:
                batch.append(i + 1)
                break
        left -= step
    return batch


def _held_by_name(name):
    return inventory.count(name)


def _held_by_id(id):
    return inventory.count_by_id(id)


class _Shop:
    """A shop's interface. Nothing here walks: be near the keeper first. Names match whole, without regard to
    case."""

    def stock_com(self):
        """The shop's stock inventory, or -1 when no shop is open."""
        return _find_inventory(_core.get_main_modal(), lambda options: _offers(options, 'Buy 1'))

    def side_com(self):
        """The backpack beside the shop, or -1."""
        return _find_inventory(_core.get_side_modal(), lambda options: _offers(options, 'Sell 1'))

    def is_open(self):
        return self.stock_com() != -1

    def open(self, npc_name):
        """Trades with the nearest keeper of that name, and waits for the shop. Use with yield from."""
        if self.is_open():
            return True
        for attempt in range(3):
            keeper = npcs.query().name(npc_name).action('Trade').nearest()
            if keeper is None:
                return False
            keeper.interact('Trade')
            opened = yield from execution.delay_until(lambda: self.is_open(), OPEN_TIMEOUT_MS)
            if opened:
                return True
        return False

    def stock(self):
        """The shop's items, as InvItems with name, id, count and slot."""
        return [item for item in _items(self.stock_com()) if item.name is not None]

    def _trade(self, item, verb, wanted, held):
        """Clicks batches of 10s, 5s and 1s on item until wanted have moved, giving how many did."""
        moved = 0
        while moved < wanted and self.is_open():
            current = item()
            if current is None or current.count == 0:
                break
            batch = shop_op_batch(current._ops, verb, wanted - moved)
            if not batch:
                break
            before = held()
            for op in batch:
                _core.inv_button(current, op)
            yield from execution.delay_until(lambda: held() != before, LAND_TIMEOUT_MS)
            # A batch lands over a tick; let it settle before counting.
            yield from execution.delay_ticks(1)
            got = abs(held() - before)
            if got <= 0:
                break
            moved += got
        return moved

    def buy(self, name, n):
        """Buys n of the item, or as many as the shop has, and gives how many were bought."""
        def item():
            found = _same_name(_items(self.stock_com()), name)
            return found[0] if found else None
        bought = yield from self._trade(item, 'buy', n, lambda: _held_by_name(name))
        return bought

    def buy_by_id(self, id, n):
        """The same by id, for stock that shares a name with other stock."""
        def item():
            for candidate in _items(self.stock_com()):
                if candidate.id == id:
                    return candidate
            return None
        bought = yield from self._trade(item, 'buy', n, lambda: _held_by_id(id))
        return bought

    def _side_item(self, name, pick):
        found = _same_name(_items(self.side_com()), name)
        if pick is not None:
            found = [item for item in found if pick(item)]
        return found[0] if found else None

    def sell(self, name, n, pick=None):
        """Sells n of the item, and gives how many were sold. pick(item) chooses among stacks of that name."""
        sold = yield from self._trade(lambda: self._side_item(name, pick), 'sell', n, lambda: _held_by_name(name))
        return sold

    def sell_all(self, name, pick=None):
        """Sells every one of the item, ten to a click, and gives how many were sold."""
        sold = 0
        for click in range(SELL_STACK_CLICKS):
            if not self.is_open():
                break
            item = self._side_item(name, pick)
            if item is None:
                break
            batch = shop_op_batch(item._ops, 'sell', SELL_STACK_STEP)
            if not batch:
                break
            before = _held_by_name(name)
            for op in batch:
                _core.inv_button(item, op)
            yield from execution.delay_until(lambda: _held_by_name(name) != before, LAND_TIMEOUT_MS)
            yield from execution.delay_ticks(1)
            gone = before - _held_by_name(name)
            if gone <= 0:
                break
            sold += gone
        return sold

    def close(self):
        if not self.is_open():
            return True
        _core.close_interfaces()
        closed = yield from execution.delay_until(lambda: not self.is_open(), CLOSE_TIMEOUT_MS)
        return closed


def parse_trade_partner_header(header):
    """The name in the offer screen's "Trading With: name", or None while it's empty."""
    if header is None:
        return None
    name = header.strip()
    colon = name.find(':')
    if colon != -1:
        name = name[colon + 1:].strip()
    elif name.lower().startswith('trading with '):
        name = name[len('trading with '):].strip()
    return name if name else None


class _Trade:
    """Trading with another player. Both players ask to trade, then both accept the offer and then confirm it.
    Moving or fighting closes the trade, so keep one task on it until it's done."""

    def _main(self):
        return _core.get_main_modal()

    def _offer_coms(self):
        """Your offer's and their offer's inventories on the offer screen, or (-1, -1)."""
        main = self._main()
        mine = -1
        theirs = -1
        for com, type, x, options in _inventories(main):
            if type != 'inv':
                continue
            if _first_option(options).startswith('remove'):
                mine = com
            elif theirs == -1:
                theirs = com
        return (mine, theirs) if mine != -1 else (-1, -1)

    def _confirm_coms(self):
        """Your lists and their lists on the confirm screen: the text inventories left and right of centre."""
        main = self._main()
        texts = [(com, x) for com, type, x, options in _inventories(main) if type == 'invtext']
        if len(texts) < 2:
            return ([], [])
        root = _core.get_component(main)
        centre = root.width // 2 if root is not None else 256
        return ([com for com, x in texts if x < centre], [com for com, x in texts if x >= centre])

    def _side_com(self):
        return _find_inventory(_core.get_side_modal(), lambda options: _first_option(options).startswith('offer'))

    def on_offer_screen(self):
        return self._offer_coms()[0] != -1

    def on_confirm_screen(self):
        if self.on_offer_screen():
            return False
        mine, theirs = self._confirm_coms()
        return len(mine) > 0 and len(theirs) > 0

    def active(self):
        return self.on_offer_screen() or self.on_confirm_screen()

    def partner(self):
        """The other player's name, from the offer screen's "Trading With:", or None."""
        main = self._main()
        if main < 0:
            return None
        for text in _core.get_texts(main):
            if text.lower().startswith('trading with'):
                return parse_trade_partner_header(text)
        return None

    def status(self):
        """The screen's own lines, such as "Other player has accepted." or "Waiting for other player..."."""
        main = self._main()
        if main < 0:
            return []
        return [text for text in _core.get_texts(main) if 'player' in text.lower() or 'accept' in text.lower()]

    def their_accepted(self):
        return len([text for text in self.status() if 'other player has accepted' in text.lower()]) > 0

    def waiting(self):
        """You've accepted, and the other player hasn't yet."""
        return len([text for text in self.status() if 'waiting for other player' in text.lower()]) > 0

    def my_offer(self):
        """What you offer, as InvItems, on either screen."""
        if self.on_offer_screen():
            return _items(self._offer_coms()[0])
        mine, theirs = self._confirm_coms()
        return _all_items(mine)

    def their_offer(self):
        if self.on_offer_screen():
            return _items(self._offer_coms()[1])
        mine, theirs = self._confirm_coms()
        return _all_items(theirs)

    def request(self, player_name):
        """Asks the nearest player of that name to trade."""
        target = players.query().name(player_name).nearest()
        if target is None:
            return False
        return target.interact('Trade with')

    def _pack_item(self, item_name, pick):
        found = _same_name(_items(self._side_com()), item_name)
        if pick is not None:
            found = [item for item in found if pick(item)]
        return found[0] if found else None

    def offer_all(self, item_name, pick=None):
        """Offers every one of the item. pick(item) chooses among stacks of that name."""
        if not self.on_offer_screen():
            return False
        item = self._pack_item(item_name, pick)
        return item is not None and _use(item, 'Offer All')

    def offer(self, item_name, n, pick=None):
        """Offers n of the item, never more, and waits for them to show in your offer. Use with yield from."""
        if n <= 0 or not self.on_offer_screen():
            return False
        item = self._pack_item(item_name, pick)
        if item is None:
            return False
        if n in FIXED_AMOUNTS and _option_number(item, f'Offer {n}') != -1:
            if not _use(item, f'Offer {n}'):
                return False
        else:
            if not _use(item, 'Offer X'):
                return False
            opened = yield from execution.delay_until(lambda: _core.is_count_dialog_open(), COUNT_DIALOG_TIMEOUT_MS)
            if not opened or not _core.answer_count(n):
                return False
        offered = yield from execution.delay_until(lambda: sum([max(1, offer.count) for offer in self.my_offer()]) >= n, OFFER_TIMEOUT_MS)
        return offered

    def remove_all(self):
        """Takes everything back off your side of the offer."""
        if not self.on_offer_screen():
            return False
        for guard in range(REMOVE_ROUNDS):
            mine = self.my_offer()
            if not mine:
                return True
            _use(mine[0], 'Remove All')
            yield from execution.delay_ticks(1)
        return len(self.my_offer()) == 0

    def accept(self):
        """Accepts the offer or confirms the trade, whichever screen is open."""
        if not self.active():
            return False
        return _core.click_text('Accept', self._main())

    def decline(self):
        """Declines, and waits for the trade to close."""
        if not self.active():
            return True
        if not _core.click_text('Decline', self._main()):
            _core.close_interfaces()
        closed = yield from execution.delay_until(lambda: not self.active(), CLOSE_TIMEOUT_MS)
        return closed


shop = _Shop()
trade = _Trade()

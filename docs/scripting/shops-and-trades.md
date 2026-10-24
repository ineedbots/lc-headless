# Shops and trades: `shop` and `trade`

Neither looks for interface ids. A shop is the main interface's inventory that offers "Buy 1", beside a backpack that offers "Sell 1". The trade offer screen holds your offer, which offers "Remove", beside theirs; the confirm screen lists the two offers as text, yours on the left. Item names match whole, without regard to case.

## `shop`

Nothing in `shop` walks: be near the keeper first, with [`traversal`](walking.md#traversal).

```python
opened = yield from shop.open('Shop keeper')
if opened:
    bought = yield from shop.buy('Bucket', 3)
    yield from shop.close()
```

| Method | Gives or does |
|---|---|
| `shop.is_open()` | A shop is open |
| `shop.open(npc_name)` | **Wait.** Uses Trade on the nearest NPC of that name offering it, and waits up to 3 seconds for the shop, trying 3 times. `False` when there's no such NPC |
| `shop.stock()` | The shop's items as [`InvItem`](items.md#invitem)s: `name`, `id`, `count` (the stock) and `slot` |
| `shop.buy(name, n)` | **Wait.** Buys `n`, or as many as the shop has. Gives how many were bought |
| `shop.buy_by_id(id, n)` | **Wait.** The same by id, for stock that shares a name |
| `shop.sell(name, n, pick=None)` | **Wait.** Sells `n` from the backpack. Gives how many were sold. `pick(item)` chooses among stacks of that name, such as the noted one |
| `shop.sell_all(name, pick=None)` | **Wait.** Sells every one, ten to a click. Gives how many were sold |
| `shop.close()` | **Wait.** Closes the shop and waits up to 3 seconds. `True` when closed, or when none was open |
| `shop.stock_com()`, `shop.side_com()` | The component ids of the stock and the backpack beside it, or -1 |

`buy` and `sell` click "10", then "5", then "1", up to five clicks a tick, because the server runs no more than that, and wait for each batch to land before the next. They stop early when the stock or the coins run out.

2004 shows no prices; a shop only tells you one in a "Value" game message.

### Helpers

| Function or constant | Gives |
|---|---|
| `shop_op_batch(ops, verb, remaining)` | The option numbers (1 to 5) of the clicks that buy or sell `remaining`, for `verb` `'buy'` or `'sell'`: 10s, then 5s, then 1s, up to five |
| `SELL_STACK_STEP` | `10`, what one `sell_all` click asks for |

## `trade`

Trading with another player. Both ask, then both accept the offer screen, then both accept the confirm screen. Moving or fighting closes the trade, so keep one task on it until it's done.

```python
partner = None

def on_trade_request(name):
    global partner
    partner = name

def loop():
    if partner is not None and not trade.active():
        trade.request(partner)
        yield from execution.delay_until(lambda: trade.active(), 10000)
    if trade.on_offer_screen():
        if not trade.my_offer():
            yield from trade.offer('Logs', 27)
        if not trade.waiting():
            trade.accept()
    elif trade.on_confirm_screen() and not trade.waiting():
        trade.accept()
```

### Reading

| Method | Gives |
|---|---|
| `trade.active()` | Either trade screen is open |
| `trade.on_offer_screen()` | The first screen, where items are offered |
| `trade.on_confirm_screen()` | The second screen, where the offers are confirmed |
| `trade.partner()` | The other player's name from the offer screen's "Trading With:", or `None` |
| `trade.my_offer()`, `trade.their_offer()` | The offers as `InvItem`s, on either screen |
| `trade.status()` | The screen's own status lines, such as "Other player has accepted." |
| `trade.their_accepted()` | The other player has accepted this screen |
| `trade.waiting()` | You've accepted this screen and they haven't yet |
| `trade.confirm_ready()` | The confirm screen has filled in: each side lists its items or says "Absolutely nothing!", since an empty offer is allowed |

### Acting

| Method | Gives or does |
|---|---|
| `trade.request(player_name)` | Uses "Trade with" on the nearest player of that name. Doesn't wait; `False` when they aren't in view |
| `trade.offer(item_name, n, pick=None)` | **Wait.** Offers `n`, never more: Offer 1, 5 or 10 when `n` is one of those, otherwise Offer X and the count dialog. Waits up to 4 seconds for them to show in your offer. `pick(item)` chooses among stacks with that name |
| `trade.offer_all(item_name, pick=None)` | Offers the whole stack with Offer All. Doesn't wait |
| `trade.remove_all()` | **Wait.** Takes your whole offer back |
| `trade.accept()` | Clicks Accept on whichever screen is open. Doesn't wait |
| `trade.decline()` | **Wait.** Declines (or closes the screen) and waits up to 3 seconds for the trade to close |

A trade request from another player arrives as the `trade_request` event (`on_trade_request(name)`), and as a `chat_message` whose `type` is `'trade_request'`.

`parse_trade_partner_header(header)` gives the name in a "Trading With: name" line, or `None` while it's empty.

Driving a trade with a partner bot, one screen at a time, and handing one item over, are [`rs2004.catalogs`' partner trades](catalogs.md#trading-partners). Shop prices and a buyout's plan are [its shops](catalogs.md#shops).

For trading between your own accounts, see the partner helpers in [catalogs](catalogs.md#trading-partners) and [messages between scripts](console-and-messages.md#messages-between-scripts).

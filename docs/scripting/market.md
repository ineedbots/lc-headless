# The market

`rs2004.market` is rs2b0t's market: the catalog of what can be traded, the shelves it's shown on, price books, appraising a trade window, and the chat protocol a player shop speaks. MarketMaker and JiveMarketDumper (`scripts/bots/`) are built on it. A script imports it:

```python
from rs2004.market import live_catalog, resolve_by_name, PriceBooks, appraise, describe_appraisal

cat = live_catalog()
book = PriceBooks.by_name('Seers')
found = resolve_by_name(cat, 'blue dhide')       # [the Blue dragonhide's ObjRecord]
```

- [The catalog](#the-catalog)
- [Shelves](#shelves)
- [Price books](#price-books)
- [Appraising a trade](#appraising-a-trade)
- [Chat](#chat)
- [The tables](#the-tables)

## The catalog

`live_catalog()` builds the catalog once a session from [`reader.obj_catalog()`](game.md#reader), every named obj in the cache. `build_catalog(records)` builds one from any records (each with `id`, `name`, `stackable`, `equippable`, and `note_of`, or rs2b0t's `certlink` and `certtemplate`).

| Member | Meaning |
|---|---|
| `cat.by_id` | Every record by id, notes included |
| `cat.noted_of`, `cat.unnoted_of` | Unnoted id to noted id, and back |
| `cat.items` | The unnoted items a book can list, name-sorted. Left out: notes, a stackable's pile-size models, untradeables, and poisoned ammunition and fire arrows |
| `cat.aliases` | For an obj whose name the content repeats, the `words` that tell it apart and the `label` the shop says back |

| Function | Gives |
|---|---|
| `display_name(cat, id)` | What the shop calls the obj: its alias label, such as "Blue dragonhide", else its name, else `'item <id>'` |
| `client_name(cat, id)` | What the client calls it, the only name a click can aim by, or `None`. Offer and withdraw by this |
| `unnoted_id(cat, id)`, `noted_id(cat, id)` | The item a note is of, and an item's note or `None` |
| `resolve_by_name(cat, query, exact_only=False)` | The items a player's words name: `'#440'` by id, then the exact name (a plural forgiven), an alias (`'loop half of key'`, `'green dragonhide'`), shorthand (`'dhide'`), `'maple longbow u'` for the unstrung bow, and failing those, unless `exact_only`, every item whose name contains the words. Several back is an ambiguity to ask about |
| `search_catalog(cat, query, limit=50)` | Items whose name or label contains the words |
| `tradeable(id)`, `worth_stocking(name)` | Whether an obj can cross a trade window, and whether a shop would carry it as its own row |

The names are this cache's. A few objs are named otherwise than in the rs2b2t content rs2b0t's tables come from, such as the holy books' torn pages, which carry their god's letter here ("Torn page 1(s)"); the tables key on ids, so only the labels differ, and the real-cache test lists them.

## Shelves

`shelves(cat)` sorts the catalog's items onto `CATEGORIES`, in order: Popular, Runes, Ores, Bars, Logs, Bows, Arrows, Weapons, Armour, Jewellery, Gems, Herbs, Potions, Herblore, Food, Tools, Hides, Bones, Seeds and Other. Popular overlaps the rest. `shelf_of(rec)` is one item's, and `category_of(rec, known=None)` decides from the name and, where `known` gives them, the item database's slot and consumable.

## Price books

A book says what a shop buys and sells: a `Record` with `name`, `margin` (the total spread, in percent, split either side of each row's mid), `max_trade_value` and `rows`. A row has `id` (the unnoted obj, the book's key), `mid`, `cap` (the most held before buying stops), `buying`, `selling`, and where set its own `buy`, `sell` or `margin`.

`PriceBooks` keeps an account's books in its file, under `script.settings["PriceBooks"]["books"]`:

```jsonc
"PriceBooks": {
    "books": [
        {"name": "Seers", "margin": 20, "maxTradeValue": 100000, "rows": [
            {"id": 440, "mid": 20, "cap": 1000, "buying": true, "selling": true}
        ]}
    ]
}
```

The keys are rs2b0t's, so a book exported from its panel works as it is, and rs2b0t's JSON string of the list is read too. `PriceBooks.all()`, `names()`, `by_name(name)` and `save(books)` read and write them; `save` writes the list into the file, keeping its comments.

| Function | Gives |
|---|---|
| `parse_books(text)`, `serialize_books(books)` | Books from JSON, and back. Malformed books and rows are dropped, not raised |
| `make_book(name, margin=5, max_trade_value=1000000, rows=None)`, `make_row(id, mid, cap=0, buying=True, selling=True, buy=None, sell=None, margin=None)` | Building them in a script |
| `upsert_book(books, book)`, `remove_book(books, name)`, `unique_book_name(books, wanted)` | Editing the list |
| `row_of(book, id)` | A row, or `None` |
| `resolve_prices(book, row)` | The row's `buy` and `sell`: its own, else mid less and plus half the margin. A 20% book quotes 90 and 110 on a 100gp item |
| `row_valid(book, row)` | A row it can trade: a cap of 0 or more, a mid of 1 or more, and sell above buy |

## Appraising a trade

`appraise(book, cat, desk, coin_id, their_offer, intent)` prices a window. `their_offer` is the customer's side (`trade.their_offer()`); `intent` is what they asked to buy, a `Record` of `max_qty` and `item_id` or `set`, or `None`; `desk` is anything with `available(id)` and `held(id)` (pack, and pack plus bank) and `purse` (coins it can pay). It gives an `Appraisal`:

| Field | Meaning |
|---|---|
| `kind` | `'buy'` (the shop buys what's up), `'sell'` (it sells what was asked for) or `'nothing'` |
| `owe` | What the shop puts up, `{id: count}` |
| `want` | The least the customer must put up |
| `total`, `lines` | The coins, and each line's `id`, `name`, `count`, `each` and `value` |
| `ignored` | What the customer should take back, each `name` and `count`: coins on a purchase, goods on a sale, units over a row's cap |
| `note` | Why the deal is short, such as `'max I can offer is 5,000gp per trade'` |
| `set` | For a set, its `name` and `count` |

A purchase over the purse or the book's `max_trade_value` bids the ceiling for the pile. `describe_appraisal(a)` is the one chat line telling the customer the deal.

Sets sell whole: `resolve_set('rune sets')` (also `'addy set'`, `'black dhide set'` and so on) names three items, and `sale_price`, `sale_stock`, `sale_items` and `sale_name` read a sale intent of one. `Ledger` keeps what the bank held at the last look (`set_stock(items)`, `held(id)`, `add(id, qty)`). `normalise_offer(cat, items)` folds a trade side onto unnoted ids; `offers_match(actual, expected)` is exact and `offer_covers(actual, expected)` at least.

## Chat

| Name | Meaning |
|---|---|
| `parse_command(text)` | A `Record` with `kind`: `'quoteSell'` ("buying 100 iron ore", with `qty`, `query` and `qty_implied`), `'quoteBuy'` ("selling …"), `'prices'` (list, book, rates, stock, or "****es", the engine's filtering of "prices"), `'buying'`, `'selling'`, `'help'`, `'reset'` or `'none'`. A command has to lead the line |
| `parse_count(token)` | `'all'`, or 5, 1k, 2m as a number; `None` otherwise |
| `CHAT_LIMIT`, `truncate_chat(text)` | 80 characters, 2004's limit |
| `format_gp(n)` | `1,234` |
| `format_price_list(entries, side)` | Entries (`name`, `buy`, `sell`) as chat lines under the limit, for `'both'`, `'buy'` or `'sell'`. Prices are joined with `-`, since the chat can't send `/` |
| `format_ambiguous(candidates)` | Asks which, naming the words that tell them apart, or `#id` |
| `HELP_LINES` | How to use a shop, in chat lines none of which parses as a command |

## The tables

`MARKET_PRICES` (a snapshot of what items changed hands for), `ITEM_ALIASES`, `NAME_SYNONYMS`, `NAME_COLLISIONS` and `UNTRADEABLE_IDS` are generated into `rs2004/market/_data.py` by `tools/catalogs/export_rs2b0t.ts`. A real-cache test checks every id they name is an obj with the name they give it.

"""What a market bot hears in public chat and says back: the commands, counts, and lines fitted to the chat
limit. Ported from rs2b0t's api/market/chatProtocol.ts (MIT, see thirdparty/rs2b0t).

A command is a Record with `kind`: 'quoteSell' or 'quoteBuy' (with qty, a number or 'all', query and
qty_implied), 'prices', 'buying', 'selling', 'help', 'reset' or 'none'.
"""

from rs2004.catalogs.record import Record
from rs2004.market._text import format_gp, is_digits

# The 2004 chat input cap.
CHAT_LIMIT = 80

NONE = Record({'kind': 'none'})


def parse_count(token):
    """'all', or a count such as 5, 1k or 2m; None for anything else, or nothing."""
    t = token.strip().lower()
    if t == 'all':
        return 'all'
    scale = 1
    if t.endswith('k'):
        scale = 1000
        t = t[:len(t) - 1]
    elif t.endswith('m'):
        scale = 1000000
        t = t[:len(t) - 1]
    if not is_digits(t):
        return None
    n = int(t) * scale
    return n if n > 0 else None


# The buy and sell verbs.
BUYING = set(['buy', 'buying'])
SELLING = set(['sell', 'selling'])
# The ways of asking for the book.
LISTING = set(['list', 'book', 'rates', 'stock', 'prices'])


def _censored_prices(head):
    """Why: the engine filters every public message before broadcasting it, and it reads "pric" as an obfuscated
    slur, so "prices" reaches the shop as "****es" and never parses."""
    return len(head) > 2 and head.endswith('es') and len([c for c in head[:len(head) - 2] if c != '*']) == 0


def parse_command(text):
    """The command a chat line gives, or a 'none' one.

    Why: it needs a leading keyword, so ordinary chat can't parse as a command."""
    trimmed = text.strip()
    if trimmed.startswith('/'):
        trimmed = trimmed[1:]
    parts = trimmed.split()
    if len(parts) == 0:
        return NONE
    head = parts[0].lower()

    if len(parts) == 1:
        if head in LISTING or _censored_prices(head):
            return Record({'kind': 'prices'})
        if head == 'buying':
            return Record({'kind': 'buying'})
        if head == 'selling':
            return Record({'kind': 'selling'})
        if head == 'help' or head == 'commands' or head == 'shop':
            return Record({'kind': 'help'})
        # A busy shop takes only the bare cancel command.
        if head == 'reset' or head == 'unstick':
            return Record({'kind': 'reset'})
        return NONE

    if head not in BUYING and head not in SELLING:
        return NONE
    # Why: 'buying rune scimitar' means one of them, so a missing count is a count of 1.
    stated = parse_count(parts[1])
    query = ' '.join(parts[1:] if stated is None else parts[2:])
    if len(query) == 0:
        return NONE
    qty = stated if stated is not None else 1
    kind = 'quoteSell' if head in BUYING else 'quoteBuy'
    return Record({'kind': kind, 'qty': qty, 'query': query, 'qty_implied': stated is None})


# How to use the shop, in lines that fit the chat limit.
# Why: the engine's filter eats "pric" and a line leading with buy or sell parses back as a command, so the shop
# "values" things and no line starts on a keyword.
HELP_LINES = [
    'To SELL to me: trade me and add items. I value each one as you put it up.',
    "To BUY: 'buying 100 iron ore' or 'buying 10 rune sets', then trade with coins.",
    "Say 'list' for what I hold now. 'buying' and 'selling' show one side each.",
    "Repeated names need a word: 'blue dragonhide', 'loop half of key', 'yew u'.",
    "If I name several and ask which, answer with the '#number' I gave you.",
    "Say 'reset' if I get stuck, or 'help' for this again.",
]


def truncate_chat(text):
    return text if len(text) <= CHAT_LIMIT else text[:CHAT_LIMIT]


def _compose(parts, head, tail, n):
    more = f' +{len(parts) - n} more' if n < len(parts) else ''
    return head + ', '.join(parts[:n]) + more + tail


def _fit_parts(parts, head, tail):
    """As many parts as fit in chat, saying how many were left out.

    Why: the "+N more" it ends with costs characters of its own, so the count has to be inside the
    measurement."""
    for n in range(len(parts), 0, -1):
        line = _compose(parts, head, tail, n)
        if len(line) <= CHAT_LIMIT:
            return line
    return truncate_chat(_compose(parts, head, tail, 1))


def format_ambiguous(items):
    """Asks which one of the candidates (each with id, name, base and word), naming the words that separate them,
    and falling back to '#id' where no word does.

    Why: 4 objs are called "Dragonhide", so listing the name 4 times says nothing; the colour is the answer."""
    one_name = len([i for i in items if i.base != items[0].base]) == 0
    if one_name and len([i for i in items if i.word is None]) == 0:
        return _fit_parts([i.word for i in items], f'{len(items)} matches: ', f" '{items[0].base}'. Which?")
    seen = {}
    for i in items:
        seen[i.name] = seen.get(i.name, 0) + 1
    parts = [f"'{i.name}' #{i.id}" if seen.get(i.name, 0) > 1 else f"'{i.name}'" for i in items]
    return _fit_parts(parts, f'{len(items)} matches: ', '. Which?')


def _entry_field(entry, field):
    return entry[field] if isinstance(entry, dict) else getattr(entry, field)


def format_price_list(entries, side):
    """The entries (each with name, buy and sell) as chat lines, for `side` 'both', 'buy' or 'sell'.

    Why: WordPack's alphabet has no '/', and a character it can't carry is sent as a space, so 18/22 would
    arrive as "18 22"; the two prices are joined with '-'."""
    parts = []
    for e in entries:
        name = _entry_field(e, 'name')
        if side == 'buy':
            parts.append(f"{name} {format_gp(_entry_field(e, 'buy'))}")
        elif side == 'sell':
            parts.append(f"{name} {format_gp(_entry_field(e, 'sell'))}")
        else:
            parts.append(f"{name} {format_gp(_entry_field(e, 'buy'))}-{format_gp(_entry_field(e, 'sell'))}")

    lines = []
    current = ''
    for part in parts:
        next_ = part if current == '' else f'{current}, {part}'
        if len(next_) > CHAT_LIMIT:
            if current != '':
                lines.append(current)
            current = truncate_chat(part)
        else:
            current = next_
    if current != '':
        lines.append(current)
    return lines

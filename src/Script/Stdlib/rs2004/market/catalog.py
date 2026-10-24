"""The tradeable catalog: every obj a market can list, its noted and unnoted ids, the names repeated objs answer
to, and finding an item by what a player types. Ported from rs2b0t's api/market/catalog.ts (MIT, see
thirdparty/rs2b0t).

A record is an ObjRecord from reader.obj_catalog(), or anything with its fields. A note is one whose `note_of`
is set, or, as rs2b0t's records have it, whose `certlink` and `certtemplate` are both set.
"""

from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.market._data import ITEM_ALIASES, NAME_COLLISIONS, NAME_SYNONYMS, UNTRADEABLE_IDS
from rs2004.market._text import is_digits, key

UNTRADEABLE = set(UNTRADEABLE_IDS)


def tradeable(id):
    """Whether the content lets this obj cross a trade window at all."""
    return id not in UNTRADEABLE


def worth_stocking(name):
    """Whether a shop would carry this item as its own row.

    Why: every ammo has a poisoned twin and fire arrows are a lighting step, so listing them multiplies the
    shelf with rows nobody trades in bulk. Poisoned melee weapons stay in, since a dragon dagger(p) is bought on
    purpose."""
    n = name.strip().lower()
    for ammo in ['arrow', 'bolt', 'dart', 'javelin', 'knife']:
        if n.endswith(ammo + '(p)') or n.endswith(ammo + 's(p)'):
            return False
    if n.endswith('fire arrow') or n.endswith('fire arrows'):
        return False
    return n not in ['lit arrow', 'lit arrows', 'unlit arrow', 'unlit arrows']


def _titled(name, word):
    return word[:1].upper() + word[1:] + ' ' + name.lower()


def _build_aliases():
    """The words taken from the debug names, joined to the hand-written ones, the hand-written winning.

    Why: the debug name supplies blue, red and black for free; green, loop and tooth appear in no file, so they
    are written down."""
    out = {}
    for group in NAME_COLLISIONS:
        for member in group['objs']:
            if len(member['words']) > 0:
                out[member['id']] = Record({'words': member['words'], 'label': _titled(group['name'], member['words'][0])})
    for id in ITEM_ALIASES:
        alias = ITEM_ALIASES[id]
        out[id] = Record({'words': alias['words'], 'label': alias['label']})
    return out


ALIASES = _build_aliases()
# key(label) -> the ids answering to it.
BY_LABEL = {}
# Every word that narrows a repeated name to one obj.
ALIAS_WORDS = set()
for _id in ALIASES:
    _alias = ALIASES[_id]
    _k = key(_alias.label)
    BY_LABEL[_k] = BY_LABEL.get(_k, []) + [_id]
    for _word in _alias.words:
        ALIAS_WORDS.add(key(_word))

# key(shorthand) -> key(display name), in the table's order.
SYNONYMS = []
for _name in NAME_SYNONYMS:
    for _short in NAME_SYNONYMS[_name]:
        SYNONYMS.append((key(_short), key(_name)))


class Catalog:
    """by_id: every record by id. noted_of: unnoted id -> noted id. unnoted_of: noted -> unnoted. items: the
    unnoted entries a book can list, name-sorted. aliases: id -> the words that tell it from its same-named
    siblings, and the label to say back."""

    def __init__(self, by_id, noted_of, unnoted_of, items, aliases):
        self.by_id = by_id
        self.noted_of = noted_of
        self.unnoted_of = unnoted_of
        self.items = items
        self.aliases = aliases


def _note_of(r):
    note_of = getattr(r, 'note_of', None)
    if note_of is not None:
        return note_of
    link = getattr(r, 'certlink', None)
    template = getattr(r, 'certtemplate', None)
    if link is not None and template is not None and link != -1 and template != -1:
        return link
    return None


def build_catalog(records):
    by_id = {}
    noted_of = {}
    unnoted_of = {}
    items = []
    for r in records:
        by_id[r.id] = r
        unnoted = _note_of(r)
        if unnoted is not None:
            noted_of[unnoted] = r.id
            unnoted_of[r.id] = unnoted
        elif getattr(r, 'stack_variant', None) is not True and tradeable(r.id) and worth_stocking(r.name):
            # Why: pile-size models and untradeables stay reachable by id but aren't offered as book items.
            items.append(r)
    items.sort(key=lambda r: (r.name.lower(), r.id))
    return Catalog(by_id, noted_of, unnoted_of, items, ALIASES)


def display_name(cat, id):
    """What the shop calls an obj, which is the plain name until the content repeats it.

    Why: for speaking only; anything that clicks an item needs client_name."""
    alias = cat.aliases.get(id)
    if alias is not None:
        return alias.label
    r = cat.by_id.get(id)
    return r.name if r is not None else f'item {id}'


def client_name(cat, id):
    """What the client itself calls an obj, the only name a click can be aimed by, or None.

    Why: trade.offer finds the pack's slot by the client's own name, so the shop's label finds none and the bot
    stakes nothing; None makes a caller refuse instead of clicking."""
    r = cat.by_id.get(id)
    return r.name if r is not None else None


def unnoted_id(cat, id):
    return cat.unnoted_of.get(id, id)


def noted_id(cat, id):
    return cat.noted_of.get(id)


def _named(cat, r, q):
    """Whether the words name this obj, by its own name or by what the shop calls it."""
    return q in key(r.name) or q in key(display_name(cat, r.id))


def search_catalog(cat, query, limit=50):
    q = _expand_synonyms(key(query))
    hits = cat.items if len(q) == 0 else [r for r in cat.items if _named(cat, r, q)]
    return hits[:limit]


def _prefer_worn(found, unstrung):
    """A name collision narrowed to the strung or the unstrung half.

    Why: every bow shares its display name with its unstrung twin, and the only thing separating them in the
    client's data is that the strung one can be worn."""
    if len(found) < 2:
        return list(found)
    wanted = [r for r in found if r.equippable != unstrung]
    return wanted if len(wanted) == 1 else list(found)


def _exactish(cat, q):
    """An exact match, forgiving a plural.

    Why: people ask for "1k maple longbows", and the item is called "Maple longbow"."""
    hit = [r for r in cat.items if key(r.name) == q]
    if len(hit) > 0 or not q.endswith('s'):
        return hit
    singular = q[:len(q) - 1]
    return [r for r in cat.items if key(r.name) == singular]


def _expand_synonyms(q):
    """"dhide" and the like swapped for the display name they stand in for."""
    out = q
    for short, full in SYNONYMS:
        padded = f' {out} '
        at = padded.find(f' {short} ')
        if at >= 0:
            out = ' '.join((padded[:at] + ' ' + full + ' ' + padded[at + len(short) + 2:]).split())
    return out


def _with_ids(cat, ids):
    want = set(ids)
    return [r for r in cat.items if r.id in want]


def _by_label(cat, q):
    """The name the shop would say back, said to it."""
    direct = _with_ids(cat, BY_LABEL.get(q, []))
    if len(direct) > 0 or not q.endswith('s'):
        return direct
    return _with_ids(cat, BY_LABEL.get(q[:len(q) - 1], []))


def _has_alias_words(cat, r, words):
    alias = cat.aliases.get(r.id)
    if alias is None:
        return False
    for w in words:
        if len([x for x in alias.words if key(x) == w]) == 0:
            return False
    return True


def _resolve_aliased(cat, q):
    """A repeated name narrowed by the words the customer gave.

    Why: 4 objs are called "Dragonhide" and 2 are "Half of a key", so the colour or the half is the only thing
    separating them, and it never appears in the name."""
    spoken = _by_label(cat, q)
    if len(spoken) > 0:
        return spoken
    tokens = [t for t in q.split(' ') if t]
    words = [t for t in tokens if t in ALIAS_WORDS]
    rest = _expand_synonyms(' '.join([t for t in tokens if t not in ALIAS_WORDS]))
    if len(rest) == 0 or (len(words) == 0 and rest == q):
        return []
    base = _exactish(cat, rest)
    if len(base) == 0 or len(words) == 0:
        return base
    return [r for r in base if _has_alias_words(cat, r, words)]


def resolve_by_name(cat, query, exact_only=False):
    """The catalog items a player's words name: '#440' by id, else the exact name, an alias, "maple longbow u"
    for the unstrung bow, and failing those, unless exact_only, every item whose name contains the words."""
    trimmed = query.strip()
    if trimmed.startswith('#') and is_digits(trimmed[1:]):
        wanted = int(trimmed[1:])
        return [r for r in cat.items if r.id == wanted][:1]

    q = key(query)
    if len(q) == 0:
        return []

    # Why: the plain name is tried first, so "guam leaf" stays a herb instead of matching the alias word "guam".
    exact = _exactish(cat, q)
    if len(exact) > 0:
        return _prefer_worn(exact, False)

    aliased = _resolve_aliased(cat, q)
    if len(aliased) > 0:
        return aliased

    # "maple longbow u" is the unstrung "Maple longbow".
    if len(q) > 2 and q.endswith(' u'):
        base = _exactish(cat, q[:len(q) - 2])
        if len(base) > 0:
            return _prefer_worn(base, True)

    if exact_only:
        return []
    expanded = _expand_synonyms(q)
    return _prefer_worn([r for r in cat.items if _named(cat, r, expanded)], False)


_live = [None]


def live_catalog():
    """The cache's catalog, built once a session from reader.obj_catalog()."""
    if _live[0] is None or len(_live[0].items) == 0:
        _live[0] = build_catalog(reader.obj_catalog())
    return _live[0]


def reset_live_catalog():
    _live[0] = None

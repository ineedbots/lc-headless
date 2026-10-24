"""The order book's shelves: which an item sits on, by its name and the item database's slot and use. Ported
from rs2b0t's api/market/categories.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.tables import item_db
from rs2004.market._text import ends_with_word

# The shelves in display order.
CATEGORIES = [
    'Popular', 'Runes', 'Ores', 'Bars', 'Logs', 'Bows', 'Arrows', 'Weapons', 'Armour', 'Jewellery', 'Gems',
    'Herbs', 'Potions', 'Herblore', 'Food', 'Tools', 'Hides', 'Bones', 'Seeds', 'Other',
]

HERBS = [
    'guam', 'marrentill', 'tarromin', 'harralander', 'ranarr', 'irit',
    'avantoe', 'kwuarm', 'cadantine', 'lantadyme', 'dwarf weed', 'torstol',
]

SECONDARIES = [
    'vial', 'eye of newt', 'unicorn horn', 'red spiders', 'limpwurt', 'snape grass',
    'white berries', 'dragon scale', 'wine of zamorak', 'potato cactus', 'jangerberries',
    'chocolate dust', 'pestle and mortar', 'ashes',
]

# Why: matching the stone anywhere in the name swept up every ring and amulet cut from it, which belong with the
# jewellery.
GEM_NAMES = ['sapphire', 'emerald', 'ruby', 'diamond', 'dragonstone', 'opal', 'jade', 'red topaz']

TOOLS = [
    'fishing rod', 'fishing net', 'lobster pot', 'harpoon', 'fishing bait', 'karambwan vessel',
    'tinderbox', 'chisel', 'shears', 'needle', 'spade', 'rake', 'seed dibber', 'watering can',
]


def _has(name, needles):
    for needle in needles:
        if needle in name:
            return True
    return False


def _is_gem(name):
    bare = name[len('uncut '):] if name.startswith('uncut ') else name
    return bare in GEM_NAMES


def _ends_with_dose(name):
    # rs2b0t's /\(\d\)$/.
    return len(name) >= 3 and name[len(name) - 1] == ')' and name[len(name) - 3] == '(' and '0' <= name[len(name) - 2] and name[len(name) - 2] <= '9'


def _known_field(known, field):
    if known is None:
        return None
    return known.get(field) if isinstance(known, dict) else getattr(known, field, None)


def category_of(rec, known=None):
    """The shelf for an item (anything with a `name`), from its name and, where given, `known`'s slot and
    consumable (the item database's).

    Why: the client's obj data has no category field, so the display name decides."""
    name = rec.name.lower()
    slot = _known_field(known, 'slot')
    consumable = _known_field(known, 'consumable')

    # Why: "Chocolate bar" is the one bar you eat, and it would otherwise shelve with the smithing bars.
    if 'chocolate bar' in name:
        return 'Food'
    if ends_with_word(name, 'rune') or ends_with_word(name, 'runes') or 'essence' in name:
        return 'Runes'
    if ends_with_word(name, 'ore'):
        return 'Ores'
    if ends_with_word(name, 'bar'):
        return 'Bars'
    if ends_with_word(name, 'log') or ends_with_word(name, 'logs'):
        return 'Logs'
    if 'arrow' in name or 'bolt' in name or 'dart' in name:
        return 'Arrows'
    # Why: a bow string is fletching stock and "bowl" only shares the letters.
    if 'bow' in name and 'bow string' not in name and 'bowl' not in name:
        return 'Bows'
    if 'bones' in name:
        return 'Bones'
    if 'seed' in name:
        return 'Seeds'
    if 'hide' in name or 'leather' in name:
        return 'Hides'
    if _ends_with_dose(name) or 'potion' in name:
        return 'Potions'
    if _has(name, HERBS):
        return 'Herbs'
    if _has(name, SECONDARIES):
        return 'Herblore'
    if _is_gem(name):
        return 'Gems'
    # The loadout's own categories first; most food names have no useful suffix.
    if consumable == 'eat' or consumable == 'drink' or name.startswith('raw ') or 'burnt' in name:
        return 'Food'
    if _has(name, TOOLS):
        return 'Tools'
    if slot == 'righthand':
        return 'Weapons'
    if slot == 'ring' or slot == 'front':
        return 'Jewellery'
    if slot is not None:
        return 'Armour'
    return 'Other'


# Shelves that are popular stock wholesale.
# Why: the Arrows shelf also holds bolts, javelins, tips and shafts, which nobody stocks by the load.
POPULAR_SHELVES = ['Runes', 'Ores', 'Bars', 'Herbs', 'Gems']

# Popular named stock besides the whole shelves.
# Why: potions are the 3-dose, which is what gets traded; the other doses can still be added one at a time.
POPULAR_NAMES = [
    'Bronze arrow', 'Iron arrow', 'Steel arrow', 'Mithril arrow', 'Adamant arrow', 'Rune arrow',
    'Rune full helm', 'Rune platebody', 'Rune chainbody', 'Rune platelegs', 'Rune kiteshield',
    'Rune scimitar', 'Rune longsword',
    'Super attack(3)', 'Super strength(3)', 'Super defence(3)', 'Superantipoison(3)', 'Prayer potion(3)',
    'Amulet of glory(4)',
    'Half of a key', 'Crystal key',
    'Raw lobster', 'Lobster', 'Raw shark', 'Shark',
    'Feather', 'Vial', 'Vial of water', 'Rune essence', 'Flax', 'Bow string',
]

POPULAR_SET = set([n.lower() for n in POPULAR_NAMES])


def is_popular(rec, known=None):
    """Whether an item is on the Popular shelf, which overlaps the others: a nature rune is on Runes and
    Popular."""
    return rec.name.strip().lower() in POPULAR_SET or category_of(rec, known) in POPULAR_SHELVES


_slots = [None]


def _known_of(id):
    if _slots[0] is None:
        table = {}
        for r in item_db():
            table[r.id] = {'slot': r.slot, 'consumable': r.consumable}
        _slots[0] = table
    return _slots[0].get(id, {})


def shelves(cat):
    """Every unnoted item the catalog knows, by shelf, in CATEGORIES' order, each shelf name-sorted."""
    out = {}
    for name in CATEGORIES:
        out[name] = []
    for rec in cat.items:
        known = _known_of(rec.id)
        out[category_of(rec, known)].append(rec)
        # Why: Popular is an overlay, so an item sits on it as well as on the shelf it naturally belongs to.
        if is_popular(rec, known):
            out['Popular'].append(rec)
    return out


def shelf_of(rec):
    """The shelf one item sits on, using the item database where it knows the item."""
    return category_of(rec, _known_of(rec.id))

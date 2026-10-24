"""Sorting the bank: each item's category and place within it, the moves that get there in the fewest drags,
and the drags themselves. Also the quest items a finished quest leaves behind. Ported from rs2b0t's
api/bank/bankSort.ts, bankSortPlan.ts, bankSortRank.ts, bankSortRules.ts and bankQuestJunk.ts (MIT, see
thirdparty/rs2b0t).

    result = yield from sort_bank(log=log)
    log(result.reason, result.moves)

An item to sort is anything with `slot`, `id`, `name` and `cost`: `sortable_bank_items()` reads the open bank's.
"""

import _core
from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.interfaces import interfaces

__all__ = [
    'sort_bank', 'plan_bank_sort', 'sortable_bank_items', 'CATEGORY_ORDER', 'QUEST_JUNK', 'find_quest_junk',
    'ARRANGE_SWAP_COM', 'ARRANGE_INSERT_COM', 'BANK_INSERT_VARP',
]

# Categories (bankSortRules.ts)

CATEGORY_ORDER = [
    'coins', 'runes', 'staves', 'ammunition', 'weapons', 'armour', 'rangedArmour',
    'food', 'potions', 'jewellery', 'herbs', 'oresBarsGems', 'logs', 'supplies',
    'tools', 'teleports', 'questLive', 'questObsolete', 'junk',
]

COINS = 995
RUNE_IDS = [554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 1436]


def _is_word_char(c):
    lower = c.lower()
    return ('a' <= lower and lower <= 'z') or ('0' <= c and c <= '9') or c == '_'


def _bounded(name, at, length):
    """The text at name[at:at + length] has no word character either side, as a regex's \\b...\\b reads."""
    before = at == 0 or not _is_word_char(name[at - 1])
    end = at + length
    after = end >= len(name) or not _is_word_char(name[end])
    return before and after


def _occurrences(name, part):
    out = []
    at = name.find(part)
    while at >= 0:
        out.append(at)
        at = name.find(part, at + 1)
    return out


def has_word(name, part):
    """part occurs in name as a whole word."""
    for at in _occurrences(name, part):
        if _bounded(name, at, len(part)):
            return True
    return False


def _contains_any(name, parts):
    for part in parts:
        if part in name:
            return True
    return False


def _has_any_word(name, parts):
    for part in parts:
        if part in name and has_word(name, part):
            return True
    return False


def _any(parts):
    return lambda name: _contains_any(name, parts)


# Why: "ring" sits inside "bow string" and "herring", so the short words need a boundary.
def _word(parts):
    return lambda name: _has_any_word(name, parts)


def _is_axe(name):
    # rs2b0t's /\baxe$/, less the battleaxe.
    return name.endswith('axe') and (len(name) == 3 or not _is_word_char(name[len(name) - 4])) and 'battleaxe' not in name


# Why: a bare 'sword' also sits inside "Swordfish", which belongs with the rest of the food.
def _is_sword(name):
    return len([at for at in _occurrences(name, 'sword') if name[at + 5:at + 9] != 'fish']) > 0


# Why: a bare "bow" also sits inside "bowl", so it needs a trailing boundary.
def _is_bow(name):
    return len([at for at in _occurrences(name, 'bow') if at + 3 >= len(name) or not _is_word_char(name[at + 3])]) > 0


def _rule(category, ids=None, matches=None):
    return Record({'category': category, 'ids': ids, 'matches': matches})


RULES = [
    _rule('coins', ids=[COINS]),
    _rule('runes', ids=RUNE_IDS),
    _rule('ammunition', matches=_any(['arrow', 'bolt', 'dart', 'javelin', 'knife', 'knives', 'cannonball'])),
    _rule('teleports', matches=_any(['teleport'])),
    _rule('potions', matches=_any([
        'potion', 'vial', 'brew', 'antipoison', 'restore', 'antifire',
        'super attack', 'super strength', 'super defence', 'super energy',
    ])),
    _rule('jewellery', matches=_any(['amulet', 'necklace', 'bracelet'])),
    _rule('jewellery', matches=_word(['ring'])),
    _rule('tools', matches=_any([
        'pickaxe', 'hatchet', 'hammer', 'chisel', 'tinderbox', 'needle', 'spade', 'rope',
        'harpoon', 'lobster pot', 'fishing rod', 'fishing net', 'bucket', 'jug', 'tiara',
    ])),
    _rule('tools', matches=_is_axe),
    _rule('supplies', matches=_any(['bowstring', 'bow string'])),
    _rule('staves', matches=_any(['staff'])),
    _rule('weapons', matches=_any([
        'scimitar', 'mace', 'dagger', 'battleaxe', 'warhammer',
        'halberd', 'spear', 'crossbow', 'wand', 'claws', 'whip',
    ])),
    _rule('weapons', matches=_is_sword),
    _rule('weapons', matches=_is_bow),
    # Why: worn hide is ranged kit; the raw "Dragonhide", "Leather" and "Hard leather" stay materials.
    _rule('rangedArmour', matches=_any([
        'dragonhide body', 'dragonhide chaps', 'dragon vambraces',
        'studded ', 'hardleather', 'leather ', 'coif',
    ])),
    _rule('armour', matches=_any([
        'platebody', 'plateskirt', 'platelegs', 'chainbody', 'helm', 'shield', 'boots',
        'gloves', 'gauntlets', 'vambraces', 'chaps', 'cape', 'cloak', 'robe', 'hat',
        'body', 'legs', 'skirt',
    ])),
    _rule('food', matches=_any([
        'shark', 'lobster', 'swordfish', 'tuna', 'trout', 'salmon', 'bass', 'pike',
        'shrimps', 'anchovies', 'herring', 'sardine', 'mackerel', 'manta ray',
        'bread', 'cake', 'stew', 'meat', 'chicken', 'kebab', 'wine', 'beer',
    ])),
    _rule('food', matches=_word(['cod', 'pie'])),
    # Why: the strange plant's reward is an edible, so it belongs with the food rather than falling through to junk.
    _rule('food', matches=_any(['strange fruit'])),
    _rule('herbs', matches=_any([
        'grimy', 'clean ', 'guam', 'marrentill', 'tarromin', 'harralander', 'ranarr',
        'irit', 'avantoe', 'kwuarm', 'cadantine', 'dwarf weed', 'torstol',
        'lantadyme', 'snapdragon', 'snake weed', 'ardrigal', 'sito foil',
        'volencia moss', 'rogues purse',
        'eye of newt', 'unicorn horn', 'limpwurt', 'snape grass', 'white berries',
        'red spiders', 'chocolate dust', 'toadflax',
    ])),
    # Why: an unidentified herb of any kind is named "Herb", so only the rank's id table tells them apart.
    _rule('herbs', matches=lambda name: name == 'herb'),
    _rule('oresBarsGems', matches=lambda name: name == 'half of a key' or name == 'crystal key'),
    _rule('oresBarsGems', matches=_any(['sapphire', 'emerald', 'ruby', 'diamond', 'dragonstone', 'opal', 'jade', 'topaz'])),
    _rule('oresBarsGems', matches=_word(['ore', 'bar', 'bars', 'coal', 'gem'])),
    _rule('logs', matches=_any(['logs', 'plank'])),
    _rule('supplies', matches=_any([
        'feather', 'leather', 'hide', 'thread', 'bowstring', 'bow string', 'seed',
        'bait', 'shaft', 'wool', 'flax', 'molten glass', 'soda ash',
    ])),
    # Why: an explicit junk entry is filed as junk instead of counting as a rule the table is missing.
    _rule('junk', ids=[526, 532]),
]


def _rule_for(item):
    name = (item.name or '').lower()
    for rule in RULES:
        if rule.ids is not None and item.id in rule.ids:
            return rule
        if len(name) > 0 and rule.matches is not None and rule.matches(name):
            return rule
    return None


def category_of(item):
    """The item's bank category, one of CATEGORY_ORDER; 'junk' when no rule names it."""
    rule = _rule_for(item)
    return rule.category if rule is not None else 'junk'


def is_unmatched(item):
    """No rule names the item, so it's filed as junk by default."""
    return _rule_for(item) is None


# Place within a category (bankSortRank.ts)

UNRANKED = 9999

METALS = ['dragon', 'rune', 'adamant', 'mithril', 'black', 'steel', 'iron', 'bronze']


def _family(suffix):
    return [f'{metal} {suffix}' for metal in METALS]


ORES = ['copper ore', 'tin ore', 'iron ore', 'silver ore', 'coal', 'gold ore', 'mithril ore', 'adamantite ore', 'runite ore']
BARS = ['bronze bar', 'iron bar', 'silver bar', 'steel bar', 'gold bar', 'mithril bar', 'adamantite bar', 'runite bar']
KEYS = ['half of a key', 'crystal key']
GEMS = ['dragonstone', 'diamond', 'ruby', 'emerald', 'sapphire']

BOW_WOODS = ['magic ', 'yew ', 'maple ', 'willow ', 'oak ', '']
BOWS = []
for _wood in BOW_WOODS:
    BOWS.append(f'{_wood}longbow')
    BOWS.append(f'{_wood}shortbow')

AMMUNITION = (_family('arrow') + _family('arrowtips') + ['headless arrow', 'barbed bolts', 'pearl bolts', 'opal bolts', 'bolts',
              'barb bolttips', 'pearl bolttips', 'opal bolttips'] + _family('dart') + _family('dart tip') + _family('javelin')
              + _family('knife') + _family('thrownaxe') + ['cannonball'])

STAVES = [
    'mystic lava staff', 'mystic fire staff', 'mystic water staff',
    'mystic earth staff', 'mystic air staff',
    'lava battlestaff', 'fire battlestaff', 'water battlestaff',
    'earth battlestaff', 'air battlestaff', 'battlestaff',
    'staff of saradomin', 'staff of guthix', 'staff of zamorak', 'staff of iban',
    'staff of fire', 'staff of water', 'staff of earth', 'staff of air',
    'magic staff', 'dramen staff', 'staff',
]

RUNES = [
    'blood rune', 'death rune', 'soul rune', 'chaos rune', 'mind rune', 'body rune',
    'nature rune', 'cosmic rune', 'law rune',
    'air rune', 'earth rune', 'water rune', 'fire rune',
    'rune essence',
]

LOGS = ['logs', 'achey tree logs', 'oak logs', 'willow logs', 'maple logs', 'yew logs', 'magic logs']

HERBS = [
    'guam leaf', 'snake weed', 'ardrigal', 'sito foil', 'volencia moss', 'rogues purse',
    'marrentill', 'tarromin', 'harralander', 'ranarr weed', 'toadflax', 'irit leaf',
    'avantoe', 'kwuarm', 'snapdragon', 'cadantine', 'lantadyme', 'dwarf weed', 'torstol',
]

# Why: every unidentified herb is named "Herb", so only the id says which. Karamja's 5 have no noted form.
UNID_HERB_IDS = [
    ('guam leaf', [199, 200]), ('snake weed', [1525]), ('ardrigal', [1527]), ('sito foil', [1529]),
    ('volencia moss', [1531]), ('rogues purse', [1533]), ('marrentill', [201, 202]), ('tarromin', [203, 204]),
    ('harralander', [205, 206]), ('ranarr weed', [207, 208]), ('toadflax', [3049, 3050]), ('irit leaf', [209, 210]),
    ('avantoe', [211, 212]), ('kwuarm', [213, 214]), ('snapdragon', [3051, 3052]), ('cadantine', [215, 216]),
    ('lantadyme', [2485, 2486]), ('dwarf weed', [217, 218]), ('torstol', [219, 220]),
]

UNID_HERB_RANK = {}
for _herb, _ids in UNID_HERB_IDS:
    for _id in _ids:
        UNID_HERB_RANK[_id] = len(HERBS) + HERBS.index(_herb)

# Why: green, blue, red and black hide armour all read back as one name, so the colour is only in the id.
DHIDE_IDS = [
    [2503, 2501, 2499, 1135],
    [2497, 2495, 2493, 1099],
    [2491, 2489, 2487, 1065],
]

DHIDE_RANK = {}
for _slot in range(len(DHIDE_IDS)):
    _piece = DHIDE_IDS[_slot]
    for _colour in range(len(_piece)):
        DHIDE_RANK[_piece[_colour]] = _slot * len(_piece) + _colour
        DHIDE_RANK[_piece[_colour] + 1] = _slot * len(_piece) + _colour

DHIDE_RANKS = len(DHIDE_IDS) * len(DHIDE_IDS[0])

RANGED_ARMOUR = [
    'dragonhide body', 'dragonhide chaps', 'dragon vambraces',
    'studded body', 'studded chaps', 'hardleather body',
    'leather body', 'leather chaps', 'leather vambraces', 'leather gloves', 'leather boots',
    'coif', 'leather cowl',
]

FOOD = [
    'manta ray', 'shark', 'swordfish', 'bass', 'lobster', 'tuna', 'salmon', 'pike',
    'cod', 'trout', 'mackerel', 'herring', 'sardine', 'anchovies', 'shrimps',
    'chocolate cake', 'cake', 'meat pie', 'apple pie', 'redberry pie', 'stew',
    'pitta bread', 'bread', 'chicken', 'meat', 'ugthanki kebab', 'kebab', 'jug of wine', 'beer',
]

POTIONS = [
    'super attack', 'super strength', 'super defence',
    'attack potion', 'strength potion', 'defence potion',
    'ranging potion', 'magic potion', 'zamorak potion', 'prayer potion',
    'super restore', 'restore potion', 'superantipoison', 'antipoison', 'antifire potion',
    'super energy', 'energy potion', 'agility potion', 'fishing potion',
]

DOSES = 4
COOKING_STATES = [('', 0), ('raw ', 1), ('burnt ', 2), ('cooked ', 0)]

# Each list is the category's layout top to bottom.
NAME_ORDER = {
    'oresBarsGems': ORES + BARS + KEYS + GEMS + [f'uncut {gem}' for gem in GEMS],
    'staves': STAVES,
    'ammunition': AMMUNITION,
    'weapons': METALS + BOWS,
    'armour': METALS,
    'rangedArmour': RANGED_ARMOUR,
    'runes': RUNES,
    'logs': LOGS,
    'herbs': HERBS,
}


def _table_rank(order, name):
    """The exact name first, then a prefix that ends on a word boundary, so "Bronze arrowtips" never picks up the
    "bronze arrow" rank."""
    if name in order:
        return order.index(name)
    for i in range(len(order)):
        if name.startswith(order[i] + ' ') or name.startswith(order[i] + '('):
            return i
    return UNRANKED


def _food_rank(name):
    prefix = ''
    block = 0
    for state, state_block in COOKING_STATES:
        if state != '' and name.startswith(state):
            prefix = state
            block = state_block
            break
    rank = _table_rank(FOOD, name[len(prefix):])
    return UNRANKED if rank == UNRANKED else rank + block * len(FOOD)


def _potion_rank(name):
    # rs2b0t's /^(.*)\((\d)\)$/: a name ending in a dose, "(3)".
    if len(name) < 3 or name[len(name) - 1] != ')' or name[len(name) - 3] != '(':
        return UNRANKED
    dose = name[len(name) - 2]
    if not ('0' <= dose and dose <= '9'):
        return UNRANKED
    base = name[:len(name) - 3]
    if base not in POTIONS:
        return UNRANKED
    return POTIONS.index(base) * DOSES + (DOSES - int(dose))


def rank_within(category, item):
    """The item's place within its category, lower first. Anything the tables miss sorts behind everything they
    name."""
    by_id = None
    if category == 'herbs':
        by_id = UNID_HERB_RANK.get(item.id)
    elif category == 'rangedArmour':
        by_id = DHIDE_RANK.get(item.id)
    if by_id is not None:
        return by_id

    name = (item.name or '').lower()
    if len(name) == 0:
        return UNRANKED
    if category == 'food':
        return _food_rank(name)
    if category == 'potions':
        return _potion_rank(name)

    order = NAME_ORDER.get(category)
    if order is None:
        return UNRANKED
    rank = _table_rank(order, name)
    # Why: hide armour ranks by id above, so the name table has to start past that block.
    return rank + DHIDE_RANKS if category == 'rangedArmour' and rank != UNRANKED else rank


# The plan (bankSortPlan.ts)


def longest_increasing_subsequence(values):
    """The longest strictly increasing run of values, in order, not necessarily adjacent."""
    if len(values) == 0:
        return []
    tails = []
    prev = [-1] * len(values)
    for i in range(len(values)):
        lo = 0
        hi = len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if values[tails[mid]] < values[i]:
                lo = mid + 1
            else:
                hi = mid
        if lo > 0:
            prev[i] = tails[lo - 1]
        if lo == len(tails):
            tails.append(i)
        else:
            tails[lo] = i
    out = []
    i = tails[len(tails) - 1]
    while i != -1:
        out.append(values[i])
        i = prev[i]
    out.reverse()
    return out


def _move(from_, to):
    return Record({'from_': from_, 'to': to})


def apply_move(order, move, mode):
    """The order after one move. An insert's `to` is the index after the item's removal, which is what the
    engine's @insert_bank does in both directions."""
    out = list(order)
    if mode == 'swap':
        held = out[move.from_]
        out[move.from_] = out[move.to]
        out[move.to] = held
        return out
    item = out.pop(move.from_)
    out.insert(move.to, item)
    return out


def _plan_swaps(target_of):
    moves = []
    at = list(target_of)
    slot_of = [0] * len(at)
    for slot in range(len(at)):
        slot_of[at[slot]] = slot
    for want in range(len(at)):
        if at[want] == want:
            continue
        from_ = slot_of[want]
        displaced = at[want]
        moves.append(_move(from_, want))
        at[want] = want
        at[from_] = displaced
        slot_of[want] = want
        slot_of[displaced] = from_
    return moves


def _plan_inserts(target_of):
    anchors = set(longest_increasing_subsequence(target_of))
    settled = set(anchors)
    moves = []
    order = list(target_of)
    for want in range(len(target_of)):
        if want in anchors:
            continue
        from_ = order.index(want)
        rest = [order[i] for i in range(len(order)) if i != from_]
        to = 0
        for i in range(len(rest)):
            if rest[i] in settled and rest[i] < want:
                to = i + 1
        if to != from_:
            moves.append(_move(from_, to))
        rest.insert(to, want)
        order = rest
        settled.add(want)
    return moves


def plan_bank_sort(items, overrides=None, force=None):
    """The moves that sort `items` (each with slot, id, name and cost) by category, then rank, then cost, dearest
    first, then id: a Record with `mode` ('swap' or 'insert', whichever needs fewer moves, unless `force` names
    one), `moves` (each `from_` and `to`), `layout` (the ids in their sorted order) and `unmatched` (ids no rule
    names). `overrides` maps an id to the category it's filed under. The slots must run 0 to n-1, as the server
    compacts the bank on opening; otherwise nothing is planned."""
    current = sorted(list(items), key=lambda item: item.slot)
    if len([i for i in range(len(current)) if current[i].slot != i]) > 0:
        return Record({'mode': 'swap', 'moves': [], 'layout': [item.id for item in current], 'unmatched': []})

    # Each item is classified once, not at every comparison.
    keys = {}
    unmatched = []
    for item in current:
        if overrides is not None and item.id in overrides:
            category = overrides[item.id]
        else:
            rule = _rule_for(item)
            category = rule.category if rule is not None else 'junk'
            if rule is None:
                unmatched.append(item.id)
        keys[item.slot] = (CATEGORY_ORDER.index(category), rank_within(category, item), -item.cost, item.id)

    ranked = sorted(current, key=lambda item: keys[item.slot])
    target_index = {}
    for index in range(len(ranked)):
        target_index[ranked[index].slot] = index
    target_of = [target_index[item.slot] for item in current]

    swaps = _plan_swaps(target_of)
    inserts = _plan_inserts(target_of)
    use_insert = force == 'insert' if force is not None else len(inserts) < len(swaps)
    return Record({
        'mode': 'insert' if use_insert else 'swap',
        'moves': inserts if use_insert else swaps,
        'layout': [item.id for item in ranked],
        'unmatched': unmatched,
    })


# Sorting the open bank (bankSort.ts)

# bank_main's com_99 and com_100 at 289, Swap and Insert. sort_bank clicks them by their labels instead.
ARRANGE_SWAP_COM = 8130
ARRANGE_INSERT_COM = 8131
# %bankinsert: 1 when the bank inserts.
BANK_INSERT_VARP = 304

MOVES_PER_BATCH = 4
# Why: a full 240-slot bank is 239 moves, which is 60 rounds before any re-plan.
MAX_ROUNDS = 200
STALL_LIMIT = 3


def sortable_bank_items():
    """The open bank's items as the planner reads them, each with its slot, id, name and cost (the cache's
    value)."""
    out = []
    for item in bank.items():
        kind = reader.item_type(item.id)
        out.append(Record({'slot': item.slot, 'id': item.id, 'name': item.name, 'cost': kind.value if kind is not None else 0}))
    return out


def _signature(items):
    return ','.join([f'{item.slot}:{item.id}' for item in items])


def set_arrange_mode(mode):
    """Sets the bank's Swap or Insert button. Use with yield from: True once the varp shows it.

    Why: the server reads %bankinsert and ignores the drag packet's mode byte, so an unconfirmed varp desyncs
    the bank silently."""
    wanted = 1 if mode == 'insert' else 0
    if reader.varp(BANK_INSERT_VARP) == wanted:
        return True
    if not interfaces.click_text('Insert' if wanted == 1 else 'Swap', bank.root()):
        return False
    done = yield from execution.delay_until(lambda: reader.varp(BANK_INSERT_VARP) == wanted, 2000)
    return done


def _result(sorted_, moves, mode, unmatched, reason):
    return Record({'sorted': sorted_, 'moves': moves, 'mode': mode, 'unmatched': unmatched, 'reason': reason})


def sort_bank(log=None, category_overrides=None):
    """Sorts the open bank, four drags a tick, planning again each round. Use with yield from. Gives a Record:
    `sorted`, `moves` sent, the `mode` used, the `unmatched` ids, and the `reason` it stopped ('sorted', 'bank
    not open', 'snapshot not ready', 'bank closed', 'arrange mode stuck', 'no progress' or 'round limit'). The
    bank's Swap/Insert setting is put back afterwards."""
    if not bank.is_open():
        return _result(False, 0, None, [], 'bank not open')
    if not bank.snapshot_ready():
        return _result(False, 0, None, [], 'snapshot not ready')

    restore_to = reader.varp(BANK_INSERT_VARP)
    sent = 0
    mode = None
    unmatched = []
    swap_only = False
    stalled = 0
    reason = 'round limit'
    sorted_ = False

    for round_ in range(MAX_ROUNDS):
        if not bank.is_open():
            reason = 'bank closed'
            break
        items = sortable_bank_items()
        before = _signature(items)
        plan = plan_bank_sort(items, category_overrides, 'swap' if swap_only else None)
        unmatched = plan.unmatched
        if len(plan.moves) == 0:
            reason = 'sorted'
            sorted_ = True
            break

        set_ok = yield from set_arrange_mode(plan.mode)
        if not set_ok:
            if swap_only:
                reason = 'arrange mode stuck'
                break
            if log is not None:
                log('bank sort: arrange mode did not stick, falling back to swaps')
            swap_only = True
            continue

        mode = plan.mode
        applied = 0
        generation = bank.snapshot_generation()
        for move in plan.moves[:MOVES_PER_BATCH]:
            _core.move_item(BANK, move.from_, move.to, plan.mode == 'insert')
            applied += 1
            sent += 1

        # Why: the next round plans from the bank as it then reads, and the drags' answer can come a tick or more
        # later than rs2b0t's one-tick wait allows; a plan made on the old order, sent on the new, scrambles it.
        yield from bank.wait_snapshot_after(generation, 3000)
        yield from execution.delay_ticks(1)
        if log is not None:
            log(f'bank sort: round {round_ + 1}, {plan.mode}, {applied} sent, {len(plan.moves)} to go')

        stalled = stalled + 1 if _signature(sortable_bank_items()) == before else 0
        if stalled >= STALL_LIMIT:
            reason = 'no progress'
            break

    yield from set_arrange_mode('insert' if restore_to == 1 else 'swap')
    return _result(sorted_, sent, mode, unmatched, reason)


# Quest junk (bankQuestJunk.ts)

# Why: https://oldschool.runescape.wiki/w/Wise_Old_Man/Recycling_Centre, kept to the objs and quest-tab names at
# rev 289. Dropping one, and filing it as questObsolete, stays gated on its quest being complete.
_QUEST_JUNK_BY_QUEST = [
    ('Demon Slayer', [(2399, 'Key'), (2400, 'Key'), (2401, 'Key')]),
    ('Dragon Slayer', [(1535, 'Map part'), (1536, 'Map part'), (1537, 'Map part'), (1538, 'Crandor map'), (1543, 'Key'), (1544, 'Key'), (1545, 'Key'), (1546, 'Key'), (1547, 'Key'), (1548, 'Key')]),
    ('Ernest the Chicken', [(271, 'Pressure gauge'), (274, 'Poisoned fish food'), (275, 'Key'), (276, 'Rubber tube'), (277, 'Oil can')]),
    ('Goblin Diplomacy', [(286, 'Orange goblin mail'), (287, 'Blue goblin mail')]),
    ('Imp Catcher', [(1470, 'Red bead'), (1472, 'Yellow bead'), (1474, 'Black bead'), (1476, 'White bead')]),
    ("The Knight's Sword", [(666, 'Portrait')]),
    ("Pirate's Treasure", [(432, 'Chest key'), (433, 'Pirate message')]),
    ('Romeo & Juliet', [(755, 'Message'), (756, 'Cadava potion')]),
    ('Rune Mysteries Quest', [(290, 'Research package'), (291, 'Notes')]),
    ('Shield of Arrav', [(761, 'Scroll'), (763, 'Broken shield'), (765, 'Broken shield'), (769, 'Certificate')]),
    ('Vampire Slayer', [(1549, 'Stake')]),
    ("Witch's Potion", [(300, "Rat's tail")]),
    ('Biohazard', [(415, 'Ethanea'), (416, 'Liquid honey'), (417, 'Sulphuric broline'), (418, 'Plague sample'), (419, 'Touch paper'), (420, 'Distillator'), (421, "Lathas' amulet"), (422, 'Bird feed'), (424, 'Pigeon cage'), (425, 'Pigeon cage'), (430, "Doctors' gown")]),
    ('Clock Tower', [(20, 'Cog'), (21, 'Cog'), (22, 'Cog'), (23, 'Cog')]),
    ('Digsite Quest', [(669, 'Specimen jar'), (674, 'Rock sample'), (677, 'Panning tray'), (678, 'Panning tray'), (679, 'Panning tray'), (680, 'Nuggets'), (681, 'Talisman of zaros'), (682, 'Unstamped letter'), (683, 'Stamped letter'), (684, 'Belt buckle'), (686, 'Rusty sword'), (687, 'Broken arrow'), (688, 'Buttons'), (689, 'Broken staff'), (690, 'Broken glass'), (691, 'Level 1 certificate'), (692, 'Level 2 certificate'), (693, 'Level 3 certificate'), (694, 'Ceramic remains'), (695, 'Old tooth'), (696, 'Invitation letter'), (697, 'Damaged armour'), (698, 'Broken armour'), (699, 'Stone tablet'), (701, 'Ammonium nitrate'), (703, 'Nitroglycerin'), (705, 'Mixed chemicals'), (706, 'Mixed chemicals'), (707, 'Chemical compound'), (708, 'Arcenia root'), (709, 'Chest key'), (710, 'Vase'), (711, 'Book on chemicals'), (712, 'Cup of tea')]),
    ('Druidic Ritual', [(522, 'Enchanted beef'), (523, 'Enchanted rat'), (524, 'Enchanted bear'), (525, 'Enchanted chicken')]),
    ('Dwarf Cannon', [(0, 'Dwarf remains'), (1, 'Tool kit'), (3, "Nulodion's notes."), (14, 'Railing')]),
    ("Eadgar's Ruse", [(3262, 'Troll thistle'), (3263, 'Dried thistle'), (3264, 'Ground thistle'), (3265, 'Troll potion'), (3266, 'Drunk parrot'), (3267, 'Dirty robe'), (3268, 'Fake man'), (3269, 'Storeroom key'), (3270, 'Alco-chunks')]),
    ('Elemental Workshop', [(2886, 'Battered book'), (2888, 'A stone bowl'), (2889, 'A stone bowl')]),
    ('Family Crest', [(773, "'perfect' ring"), (774, "'perfect' necklace"), (779, 'Crest part'), (780, 'Crest part'), (781, 'Crest part'), (782, 'Family crest')]),
    ('Fight Arena', [(74, 'Khazard helmet'), (75, 'Khazard armour'), (76, 'Khazard cell keys'), (77, 'Khali brew')]),
    ('Fishing Contest', [(25, 'Red vine worm'), (26, 'Fishing trophy'), (27, 'Fishing pass')]),
    ('The Grand Tree', [(783, 'Bark sample'), (785, "Glough's journal"), (786, "Hazelmere's scroll"), (787, 'Lumber order'), (788, "Glough's key"), (793, 'Daconia rock'), (794, 'Invasion plans')]),
    ('Hazeel Cult', [(2403, 'Scroll of hazeel'), (2404, 'Key'), (2406, 'Mark of hazeel')]),
    ("Hero's Quest", [(1579, "Thieves' armband"), (1583, 'Fire feather'), (1584, 'Id papers'), (1586, 'Miscellaneous key'), (1588, "Grips' keyring"), (1591, 'Jail key')]),
    ('Holy Grail', [(15, 'Holy table napkin'), (16, 'Magic whistle'), (17, 'Grail bell'), (18, 'Magic gold feather'), (19, 'Holy grail')]),
    ('Horror from the Deep', [(3845, 'Journal'), (3846, 'Diary'), (3847, 'Manual'), (3848, 'Lighthouse key'), (3849, 'Rusty casket')]),
    ('Temple of Ikov', [(78, 'Ice arrows'), (83, 'Lever'), (84, 'Staff of armadyl'), (86, 'Pendant of lucien'), (87, 'Armadyl pendant')]),
    ('Legends Quest', [(714, 'Radimus notes'), (715, 'Radimus notes'), (717, 'Scrawled note'), (718, 'A scribbled note'), (719, 'Scrumpled note'), (720, 'Sketch'), (727, 'Hollow reed'), (729, 'Shamans tome'), (733, 'Smashed glass'), (735, 'Yommi tree seeds'), (736, 'Yommi tree seeds'), (739, 'Bravery potion'), (740, 'Blue hat'), (741, 'Chunk of crystal'), (742, 'Hunk of crystal'), (743, 'Lump of crystal'), (744, 'Heart crystal'), (745, 'Heart crystal'), (748, 'Holy force'), (749, 'Yommi totem'), (750, 'Gilded totem')]),
    ('Throne of Miscellania', [(3894, 'Awful anthem'), (3895, 'Good anthem'), (3896, 'Treaty'), (3897, 'Giant nib'), (3898, 'Giant pen'), (3901, "Ghrim's book")]),
    ('Monkey Madness', [(4002, 'Spare controls'), (4004, 'Gnome royal seal'), (4005, "Narnode's orders"), (4007, 'Enchanted bar'), (4008, 'Eye of gnome'), (4010, 'Monkey magic'), (4018, 'Monkey wrench'), (4033, 'Monkey')]),
    ('Murder Mystery', [(1796, 'Silver necklace'), (1797, 'Silver necklace'), (1798, 'Silver cup'), (1799, 'Silver cup'), (1800, 'Silver bottle'), (1801, 'Silver bottle'), (1802, 'Silver book'), (1803, 'Silver book'), (1804, 'Silver needle'), (1805, 'Silver needle'), (1806, 'Silver pot'), (1807, 'Silver pot'), (1808, "Criminals' thread"), (1809, "Criminals' thread"), (1810, "Criminals' thread"), (1811, 'Flypaper'), (1812, 'Pungent pot'), (1813, "Criminals' dagger"), (1814, "Criminals' dagger")]),
    ('Nature Spirit', [(2964, 'Washing bowl'), (2966, 'Mirror'), (2967, 'Journal'), (2968, 'Druidic spell'), (2969, 'A used spell')]),
    ('Observatory Quest', [(600, 'Astrology book'), (601, 'Keep key'), (602, 'Lens mould'), (603, 'Lens')]),
    ('Plague City', [(1503, 'Warrant'), (1507, 'A small key'), (1508, 'A scruffy note'), (1509, 'Book'), (1510, 'Picture')]),
    ('Priest in Peril', [(2953, 'Bucket of water'), (2954, 'Bucket of water')]),
    ('Regicide', [(3206, "King's message"), (3207, 'Iorwerths message'), (3208, 'Crystal pendant'), (3209, 'Sulphur'), (3213, 'Quicklime'), (3214, 'Pot of quicklime'), (3215, 'Ground sulphur'), (3219, 'Barrel bomb'), (3222, 'Naphtha mix'), (3223, 'Naphtha mix'), (3230, 'Big book of bangs')]),
    ('Sea Slug Quest', [(1466, 'Sea slug'), (1467, 'Damp sticks'), (1468, 'Dry sticks'), (1469, 'Broken glass')]),
    ('Sheep Herder', [(278, 'Prod'), (279, 'Feed')]),
    ('Tai Bwo Wannai Trio', [(3161, 'Crafting manual'), (3164, 'Karamjan rum'), (3165, 'Karamjan rum'), (3166, 'Monkey corpse'), (3167, 'Monkey skin'), (3168, 'Seaweed sandwich'), (3169, 'Stuffed monkey')]),
    ('The Tourist Trap', [(1841, 'Barrel'), (1844, "Slaves' shirt"), (1845, 'Slave robe'), (1846, 'Slave boots'), (1847, 'Scrumpled paper'), (1848, 'Shantay disclaimer'), (1849, 'Prototype dart'), (1850, 'Technical plans'), (1851, 'Tenti pineapple'), (1853, 'Prototype dart tip')]),
    ('Tribal Totem', [(1856, 'Guide book'), (1857, 'Totem'), (1858, 'Address label')]),
    ('Troll Stronghold', [(3135, 'Prison key'), (3136, 'Cell key 1'), (3137, 'Cell key 2')]),
    ('Troll Romance', [(4086, 'Trollweiss')]),
    ('Watch Tower', [(2372, 'Ogre relic'), (2373, 'Relic part 1'), (2374, 'Relic part 2'), (2375, 'Relic part 3'), (2377, 'Ogre tooth'), (2378, 'Toban key'), (2379, 'Rock cake'), (2384, 'Finger nails'), (2385, 'Old robe'), (2386, 'Unusual armour'), (2387, 'Damaged dagger'), (2388, 'Tattered eye patch'), (2389, 'Vial'), (2390, 'Vial'), (2391, 'Ground bat bones'), (2393, 'Gold'), (2394, 'Potion'), (2395, 'Magic ogre potion'), (2397, 'Shaman robe')]),
    ('Waterfall Quest', [(292, 'Book on baxtorian'), (296, "Glarial's urn"), (297, "Glarial's urn")]),
    ("Witch's House", [(2407, 'Ball'), (2408, 'Diary'), (2409, 'Door key'), (2410, 'Magnet'), (2411, 'Key')]),
    ('Shilo Village', [(604, 'Bone shard'), (605, 'Bone key'), (606, 'Stone-plaque'), (607, 'Tattered scroll'), (608, 'Crumpled scroll'), (609, 'Rashiliya corpse'), (610, 'Zadimus corpse'), (611, 'Locating crystal'), (612, 'Locating crystal'), (613, 'Locating crystal'), (614, 'Locating crystal'), (615, 'Locating crystal'), (618, 'Bone beads'), (619, 'Paramaya ticket'), (623, 'Sword pommel'), (624, 'Bervirius notes'), (625, 'Wampum belt')]),
    ('Underground Pass', [(1492, 'Doll of iban'), (1494, 'History of iban')]),
    ('Haunted Mine', [(4073, 'Damp tinderbox'), (4075, 'Glowing fungus'), (4078, "Zealot's key")]),
    ('Death Plateau', [(3102, 'Combination'), (3103, 'Iou'), (3104, 'Secret way map'), (3109, 'Stone ball'), (3110, 'Stone ball'), (3111, 'Stone ball'), (3112, 'Stone ball'), (3113, 'Stone ball'), (3114, 'Certificate')]),
]

QUEST_JUNK = []
for _quest, _items in _QUEST_JUNK_BY_QUEST:
    for _id, _name in _items:
        QUEST_JUNK.append(Record({'id': _id, 'name': _name, 'quest': _quest}))


def find_quest_junk(banked, status_of):
    """The banked items (anything with an `id`) that are some quest's leftovers, each a Record with id, name,
    quest, the quest's `status_of(quest)`, and `droppable`: its quest is complete."""
    held = set([item.id for item in banked])
    out = []
    for entry in QUEST_JUNK:
        if entry.id in held:
            status = status_of(entry.quest)
            out.append(Record({'id': entry.id, 'name': entry.name, 'quest': entry.quest, 'status': status, 'droppable': status == 'complete'}))
    return out

"""Ported from rs2b0t's src/bot/scripts/MuleDepot/MuleDepotLogic.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.traversal import BANK_LOCATIONS
from rs2004.geometry import Tile
from rs2004.catalogs.record import Record

__all__ = ['PACK', 'DEFAULT_BANK', 'MODE_OPTIONS', 'ROLE_OPTIONS', 'BANK_OPTIONS', 'resolve_role', 'is_giver_role', 'is_receiver_role', 'bank_choice', 'bank_tile', 'normalize_account', 'parse_accounts', 'is_configured_account', 'parse_item_names', 'parse_loadout', 'line_key', 'shortfall_for', 'plan_deliveries', 'pick_bank_rows', 'pick_bank_row', 'listed_rows', 'plan_withdrawal', 'next_batch_index', 'pick_request_target', 'next_unserved', 'describe_lines']

# Why: the depot is one bank and one item list, so every role difference is a mode, a designation,
# or a parsed CSV. Keeping them here keeps the policy layer unit testable without the client.
PACK = 28
DEFAULT_BANK = 'Seers'
MODE_OPTIONS = ['Dump', 'Supply']
ROLE_OPTIONS = ['Mule', 'Supermule', 'Supplier', 'Client']
BANK_OPTIONS = [bank['name'] for bank in BANK_LOCATIONS]
ROLE_BY_PAIR = Record({'dump:mule': 'Mule', 'dump:supermule': 'Supermule', 'supply:supplier': 'Supplier', 'supply:client': 'Client'})


def resolve_role(mode, designation):
    """The role a (mode, designation) pair means, or null when the pairing makes no sense."""
    # Why: null rather than a guess, so a caller refuses a nonsense pair at startup instead of
    # running a role that has nothing to do.
    _v1 = ROLE_BY_PAIR.get(f'{mode.strip().lower()}:{designation.strip().lower()}')
    return (_v1 if _v1 is not None else None)


def is_giver_role(role):
    """Giver roles stake items; receiver roles take them."""
    return role == 'Mule' or role == 'Supplier'


def is_receiver_role(role):
    return not is_giver_role(role)


def bank_choice(name):
    """The bank a setting names, or the default when the name is blank or unknown."""
    want = name.strip().lower()
    _v2 = ([bank for bank in BANK_LOCATIONS if bank['name'].lower() == want] or [None])[0]
    _v3 = (_v2 if _v2 is not None else ([bank for bank in BANK_LOCATIONS if bank['name'] == DEFAULT_BANK] or [None])[0])
    return (_v3 if _v3 is not None else BANK_LOCATIONS[0])


def bank_tile(name):
    tile = bank_choice(name)['tile']
    return Tile(tile['x'], tile['z'], tile.get('level', 0))


def normalize_account(name):
    """The name the client shows, which is what `Players.query().name()` matches on."""
    return name.lower().replace('_', ' ').replace(chr(160), ' ').strip()


def parse_accounts(raw):
    """Configured partner names, split on commas, normalized and deduped."""
    out = []
    for part in raw.split(','):
        name = normalize_account(part)
        if len(name) > 0 and not (name in out):
            out.append(name)
    return out


def is_configured_account(name, accounts):
    """True when `name` is one of the configured accounts."""
    if name is None or len(accounts) == 0:
        return False
    return (normalize_account(name) in accounts)


def parse_item_names(raw):
    """Item names from the dump list: trimmed, blanks dropped, deduped case-insensitively.  First-seen casing wins, so the log lines read as the operator wrote them."""
    out = []
    seen = set()
    for entry in raw:
        name = entry.strip()
        key = name.lower()
        if len(name) == 0 or (key in seen):
            continue
        seen.add(key)
        out.append(name)
    return out


def parse_loadout(raw):
    lines = []
    by_key = {}
    problems = []
    for index, entry in enumerate(raw):
        text = entry.strip()
        if not text or text.startswith('#'):
            continue
        parts = text.split()
        quantity = 1
        item = text
        if len(parts) > 1 and all([c in '0123456789' for c in parts[0]]):
            quantity = int(parts[0])
            item = text[len(parts[0]):].strip()
        if quantity < 1 or quantity > 2147483647:
            problems.append(Record({'line': index + 1, 'raw': text, 'reason': 'quantity must be 1..2147483647'}))
            continue
        id = int(item) if all([c in '0123456789' for c in item]) else -1
        if id > 65535:
            problems.append(Record({'line': index + 1, 'raw': text, 'reason': 'item id must be 0..65535'}))
            continue
        line = Record({'id': id, 'name': item if id < 0 else '', 'quantity': quantity, 'raw': text})
        key = line_key(line)
        if key in by_key:
            by_key[key].quantity += quantity
            continue
        by_key[key] = line
        lines.append(line)
    return Record({'lines': lines, 'problems': problems})


def line_key(line):
    """A resolved id distinguishes same-named goods; unresolved lines retain their exact name."""
    return f'#{line.id}' if line.id >= 0 else line.name.lower()


def shortfall_for(lines, held):
    """What a batch still needs from the bank, once the pack's share is counted."""
    out = []
    for line in lines:
        quantity = line.quantity - max(0, held(line))
        if quantity > 0:
            out.append(Record({'id': line.id, 'name': line.name, 'quantity': quantity}))
    return out


def plan_deliveries(lines, slots_for, slots=28):
    width = max(1, math.floor(slots))
    batches = []
    current = []
    used = 0
    for line in lines:
        remaining = max(0, math.floor(line.quantity))
        while remaining > 0:
            if used >= width:
                batches.append(Record({'index': len(batches), 'lines': current}))
                current = []
                used = 0
            per = max(1, slots_for(Record({'id': line.id, 'name': line.name, 'quantity': remaining})))
            take = remaining if per <= 1 else min(remaining, width - used)
            current.append(Record({'id': line.id, 'name': line.name, 'quantity': take}))
            used += 1 if per <= 1 else take
            remaining -= take
    if current:
        batches.append(Record({'index': len(batches), 'lines': current}))
    return batches


def pick_bank_rows(name, bank, noted_ids=None):
    """Every bank row a name means, unnoted first. Why: one name can sit on several rows, and taking the first alone leaves the rest for a later trip, so the mule looks stalled between passes."""
    want = name.strip().lower()
    rows = [row for row in bank if ((row.name if row.name is not None else '')).strip().lower() == want and row.count > 0]
    if len(rows) <= 1 or not noted_ids or len(noted_ids) == 0:
        return rows
    # Why: unnoted first, because it is the form a trade takes cleanly, but the noted rows are kept
    # so a bank that holds only the noted form still has something to give.
    unnoted = [row for row in rows if not (row.id in noted_ids)]
    noted = [row for row in rows if (row.id in noted_ids)]
    return (list(unnoted) + list(noted) if len(unnoted) > 0 else noted)


def pick_bank_row(name, bank, noted_ids=None):
    """The first row a name means, for callers that want one row."""
    _v5 = (pick_bank_rows(name, bank, noted_ids) or [None])[0]
    return (_v5 if _v5 is not None else None)


def listed_rows(csv_names, bank, noted_ids=None):
    """The bank rows the dump list names, in list order. Why: this is a dumper's keep set, and the withdrawal plan cannot be, since it is empty on a full pack and would bank the carried haul."""
    out = []
    seen = set()
    for name in csv_names:
        for row in pick_bank_rows(name, bank, noted_ids):
            if not row.name or row.count < 1 or (row.id in seen):
                continue
            seen.add(row.id)
            out.append(Record({'id': row.id, 'name': row.name, 'quantity': row.count}))
    return out


def plan_withdrawal(csv_names, bank, free_slots, noted_ids=None):
    """The lines one withdrawal pass takes, in CSV order. Why: a line costs one slot whatever its depth, so free room admits entries rather than capping them, or the first entry eats the whole pack."""
    out = []
    room = max(0, math.floor(free_slots))
    for name in csv_names:
        # Why: every row the name sits on, so one pass drains the name rather than one row of it.
        for row in pick_bank_rows(name, bank, noted_ids):
            if room <= 0:
                return out
            if not row.name or row.count < 1:
                continue
            out.append(Record({'id': row.id, 'name': row.name, 'quantity': row.count}))
            room -= 1
    return out


def next_batch_index(index, batch_count):
    """Where the batch cursor moves once a batch lands. Why: a client is only done when its last batch is away, or advancing per batch serves everyone a partial loadout."""
    next_ = index + 1
    return (Record({'index': next_, 'client_done': False}) if next_ < batch_count else Record({'index': 0, 'client_done': True}))


def pick_request_target(asker, accounts, cursor, acceptable, visible):
    """Which account a receiver should ask next. Why: an account that asked goes first, and the cursor advances on every attempt, or a stopped account keeps the rotation for ever."""
    eligible = [name for name in accounts if acceptable(name)]
    if len(eligible) == 0:
        return None
    if asker is not None and (asker in eligible) and visible(asker):
        return asker
    for i in range(len(eligible)):
        name = eligible[(cursor + i) % len(eligible)]
        if visible(name):
            return name
    return None


def next_unserved(accounts, served):
    """The next client still owed a loadout, in configured order, or null when everyone is served."""
    _v6 = ([account for account in accounts if not (normalize_account(account) in served)] or [None])[0]
    return (_v6 if _v6 is not None else None)


def describe_line(line):
    """`500 Cooked meat`, for a log line."""
    return f"{line.quantity} {line.name or str(line.id)}"


def describe_lines(lines):
    return ('nothing' if len(lines) == 0 else ' + '.join([describe_line(_x) for _x in lines]))

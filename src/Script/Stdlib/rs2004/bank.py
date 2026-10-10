"""The bank, opening one, and when to go. Mirrors rs2b0t's api/bank/Bank.ts, Banking.ts, bankOps.ts and
bankRules.ts, and api/tasks/PeriodicBank.ts (MIT, see third_party/rs2b0t).

    opened = yield from banking.open()
    if opened:
        yield from bank.deposit_all_matching(deposit_all_except(['Bronze pickaxe']))
        yield from bank.withdraw_x('Lobster', 10)
        yield from bank.close()

Bank items are InvItems whose actions are the bank's options ("Withdraw 1" to "Withdraw X"), and the backpack
beside the bank's are its ("Deposit 1" to "Deposit X"). Options match without regard to case, with a hyphen
as good as a space, so rs2b0t's 'Withdraw-1' works too.
"""

import _core
from rs2004 import execution
from rs2004.bot import Task, is_generator
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.items import inventory
from rs2004.settings import SettingDef

__all__ = [
    'bank', 'banking', 'withdraw_op', 'deposit_all_except', 'deposit_matcher', 'matches_common_bank_loot',
    'is_disposable_gather_junk', 'parse_bank_strategy', 'should_bank_now', 'PeriodicBank', 'COMMON_BANK_LOOT',
    'RANDOM_EVENT_CASKET_ID', 'PERIODIC_BANK_SETTINGS', 'NEARBY_BANK_RADIUS',
]

READY_TIMEOUT_MS = 4000
LOAD_TIMEOUT_MS = 4000
COUNT_DIALOG_TIMEOUT_MS = 3000
CLOSE_TIMEOUT_MS = 3000
OPEN_TIMEOUT_MS = 8000
ADJACENT_OPEN_TIMEOUT_MS = 4000
DEPOSIT_TIMEOUT_MS = 2000
STAND_TIMEOUT_MS = 15000
DEPOSIT_ROUNDS = 32
OPEN_ATTEMPTS = 6
# Withdraw 1, 5 and 10 need no count dialog, which makes them surer than X.
FIXED_AMOUNTS = (1, 5, 10)

# A bank already this near counts as here.
NEARBY_BANK_RADIUS = 14


def _norm(text):
    return ' '.join(text.lower().replace('-', ' ').split())


def _option_index(item, label):
    """The item's option number for label, 1 to 5, or -1."""
    wanted = _norm(label)
    for i in range(len(item._ops)):
        op = item._ops[i]
        if op is not None and _norm(op) == wanted:
            return i + 1
    return -1


def _named(items, name):
    wanted = name.strip().lower()
    for item in items:
        if item.name is not None and item.name.lower() == wanted:
            return item
    return None


def _with_id(items, id):
    for item in items:
        if item.id == id:
            return item
    return None


def _use(item, label):
    if item is None:
        return False
    op = _option_index(item, label)
    if op == -1:
        return False
    return _core.inv_button(item, op)


def withdraw_op(ops, amount):
    """The withdraw option for amount ('all', '10', '5', '1', 'x' or 'any') among ops, or None."""
    named = [op for op in ops if op is not None]
    for op in named:
        words = _norm(op).split()
        if not words or words[0] != 'withdraw':
            continue
        rest = ' '.join(words[1:])
        if amount == 'any' or rest == str(amount).lower():
            return op
    return None


class _Bank:
    """The bank interface. is_open() is the interface; its items come with it, and ready() says they have."""

    _root = None

    def root(self):
        """The bank's interface id."""
        if self._root is None:
            component = _core.get_component(BANK)
            self._root = component.root if component is not None else -1
        return self._root

    def is_open(self):
        root = self.root()
        return root >= 0 and _core.get_main_modal() == root

    def ready(self):
        """Open, with its items and the backpack beside it sent."""
        return self.is_open() and _core.has_inventory(BANK) and _core.has_inventory(BANK_INVENTORY)

    def wait_ready(self, timeout_ms=4000):
        """Waits for the items the open promises. Use with yield from."""
        if not self.is_open():
            return False
        yield from execution.delay_until(lambda: not self.is_open() or self.ready(), timeout_ms)
        return self.ready()

    def set_note_mode(self, on):
        """Withdraws as notes, or as items. Opening the bank sets items, so set it after."""
        if not self.is_open():
            return False
        if not _core.click_text('Note' if on else 'Item', self.root()):
            return False
        yield from execution.delay_ticks(1)
        return True

    def items(self):
        return _core.get_inventory(BANK) if self.is_open() else []

    def side_items(self):
        """The backpack beside the bank, whose actions deposit."""
        return _core.get_inventory(BANK_INVENTORY) if self.is_open() else []

    def count(self, name):
        wanted = name.strip().lower()
        return sum([item.count for item in self.items() if item.name is not None and item.name.lower() == wanted])

    def count_by_id(self, id):
        return sum([item.count for item in self.items() if item.id == id])

    def withdraw(self, name, op='Withdraw 1'):
        """Uses the option on the bank item, without waiting."""
        return _use(_named(self.items(), name), op)

    def withdraw_by_id(self, id, op='Withdraw 1'):
        return _use(_with_id(self.items(), id), op)

    def _withdraw_x(self, item, count, landed):
        """Withdraws min(count, what's there) of the bank item and waits for landed() to count them in."""
        if count <= 0:
            return True
        ready = yield from self.wait_ready(READY_TIMEOUT_MS)
        if not ready or item is None or item.count <= 0:
            return False
        take = min(count, item.count)
        before = landed()
        target = before + take
        fixed = withdraw_op(item._ops, str(take)) if take in FIXED_AMOUNTS else None
        if fixed is not None:
            if not _use(item, fixed):
                return False
        else:
            x = withdraw_op(item._ops, 'x')
            if x is None or not _use(item, x):
                return False
            opened = yield from execution.delay_until(lambda: _core.is_count_dialog_open(), COUNT_DIALOG_TIMEOUT_MS)
            if not opened or not _core.answer_count(take):
                return False
        arrived = yield from execution.delay_until(lambda: landed() >= target or (landed() > before and inventory.is_full()), LOAD_TIMEOUT_MS)
        return arrived

    def withdraw_x(self, name, count):
        """Withdraws count of the item, or all there is, with Withdraw 1, 5 or 10 where one fits and X
        otherwise, and waits for them to land. Use with yield from."""
        result = yield from self._withdraw_x(_named(self.items(), name), count, lambda: inventory.count(name))
        return result

    def withdraw_x_by_id(self, id, count, lands_as_id=None):
        """The same by id. In note mode the backpack gets the note, a different id: give it as lands_as_id."""
        lands = id if lands_as_id is None else lands_as_id
        result = yield from self._withdraw_x(_with_id(self.items(), id), count, lambda: inventory.count_by_id(lands))
        return result

    def withdraw_load(self, name):
        """Fills the backpack from one bank item: Withdraw All, or else X for the free slots."""
        ready = yield from self.wait_ready(READY_TIMEOUT_MS)
        item = _named(self.items(), name)
        if not ready or item is None:
            return False
        all_op = withdraw_op(item._ops, 'all')
        if all_op is not None:
            before = inventory.used()
            if not _use(item, all_op):
                return False
            loaded = yield from execution.delay_until(lambda: inventory.used() > before or inventory.is_full() or self.count(item.name) == 0, LOAD_TIMEOUT_MS)
            return loaded
        free = inventory.free()
        if free <= 0:
            return True
        result = yield from self.withdraw_x(item.name, free)
        return result

    def deposit(self, name, op='Deposit 1'):
        """Uses the option on the backpack item beside the bank, without waiting."""
        return _use(_named(self.side_items(), name), op)

    def deposit_inventory(self):
        """Deposits everything. Use with yield from."""
        yield from self.deposit_all_matching(lambda name, id: True)

    def deposit_all_matching(self, matches):
        """Deposits every backpack item for which matches(name, id) holds, a stack at a time with Deposit All,
        waiting for each to go. A nameless item is passed as ''."""
        for _ in range(DEPOSIT_ROUNDS):
            if self.is_open() and not _core.has_inventory(BANK_INVENTORY):
                yield from execution.delay_until(lambda: _core.has_inventory(BANK_INVENTORY) or not self.is_open(), 1200)
            items = self.side_items()
            item = None
            for candidate in items:
                if matches(candidate.name or '', candidate.id):
                    item = candidate
                    break
            if item is None:
                return
            ops = [op for op in item._ops if op is not None]
            all_ops = [op for op in ops if 'all' in op.lower()]
            label = all_ops[0] if all_ops else (ops[-1] if ops else None)
            if label is None or not _use(item, label):
                return
            slot = item.slot
            id = item.id
            yield from execution.delay_until(lambda: _with_slot(self.side_items(), slot, id) is None, DEPOSIT_TIMEOUT_MS)

    def _opened(self):
        if not self.is_open():
            return False
        yield from self.wait_ready(READY_TIMEOUT_MS)
        return self.is_open()

    def _open_with(self, target, op):
        """Uses op on the booth or banker, continuing a dialogue the bank comes after."""
        if not target.interact(op):
            return False
        opened = yield from execution.delay_until(lambda: self.is_open() or chat_dialog.can_continue(), OPEN_TIMEOUT_MS)
        if opened and not self.is_open():
            yield from chat_dialog.continue_()
            yield from execution.delay_until(lambda: self.is_open(), ADJACENT_OPEN_TIMEOUT_MS)
        return self.is_open()

    def open_booth(self, stand, booth_name='Bank booth', op='Use-quickly'):
        """Opens the bank at the booth nearest stand, walking to stand when a try from here fails."""
        for attempt in range(4):
            if self.is_open():
                break
            booth = locs.query().name(booth_name).where(lambda l: len(l.actions()) > 0).nearest()
            if booth is None:
                yield from execution.delay_ticks(2)
                continue
            opened = yield from self._open_with(booth, _pick(booth.actions(), op))
            if opened:
                break
            yield from direct_navigator.walk_to(stand, 1, STAND_TIMEOUT_MS)
            yield from execution.delay_ticks(1)
        opened = yield from self._opened()
        return opened

    def open_nearest(self, booth_name='Bank booth', op='Use-quickly'):
        """Opens the bank at the nearest booth in the area, stepping beside it when a try from here fails."""
        for attempt in range(OPEN_ATTEMPTS):
            if self.is_open():
                break
            booth = locs.query().name(booth_name).where(lambda l: len(l.actions()) > 0).nearest()
            if booth is None:
                return False
            opened = yield from self._open_with(booth, _pick(booth.actions(), op))
            if opened:
                break
            if booth.distance() > 1:
                yield from direct_navigator.walk_to(booth.tile(), 1, STAND_TIMEOUT_MS)
        opened = yield from self._opened()
        return opened

    def open_nearest_access(self, access):
        """Opens a bank by its access: {'name': 'Bank chest', 'op': 'Use', 'open_first': {'name', 'op'}},
        where open_first is something to open before it can be used, such as a closed chest."""
        if self.is_open():
            opened = yield from self._opened()
            return opened
        first = access.get('open_first')
        if first is not None and _loc_with_action(access['name'], access['op']) is None:
            closed = _loc_with_action(first['name'], first['op'])
            if closed is None or not closed.interact(first['op']):
                return False
            yield from execution.delay_until(lambda: self.is_open() or _loc_with_action(access['name'], access['op']) is not None, OPEN_TIMEOUT_MS)
        if self.is_open():
            opened = yield from self._opened()
            return opened
        opened = yield from self.open_nearest(access['name'], access['op'])
        return opened

    def open_npc_access(self, access):
        """Opens a bank through a banker: {'name': 'Banker', 'op': 'Bank', 'choose': None}, where choose is the
        dialogue option that opens it, for a banker who talks first."""
        for attempt in range(3):
            if self.is_open():
                break
            if not chat_dialog.is_open():
                banker = npcs.query().name(access['name']).action(access['op']).nearest()
                if banker is None:
                    yield from execution.delay_ticks(1)
                    continue
                banker.interact(access['op'])
                yield from execution.delay_until(lambda: chat_dialog.is_open() or self.is_open(), 6000)
            choose = access.get('choose')
            for guard in range(12):
                if self.is_open():
                    break
                if choose is not None and len([o for o in chat_dialog.options() if choose.lower() in o.lower()]) > 0:
                    yield from chat_dialog.choose_option(choose)
                elif chat_dialog.can_continue():
                    yield from chat_dialog.continue_()
                else:
                    break
            yield from execution.delay_until(lambda: self.is_open(), 3000)
        opened = yield from self._opened()
        return opened

    def close(self, timeout_ms=3000):
        """Closes the bank, so the backpack's own options work again, and waits for it to go."""
        if not self.is_open():
            return True
        _core.close_interfaces()
        closed = yield from execution.delay_until(lambda: not self.is_open(), timeout_ms)
        return closed


def _with_slot(items, slot, id):
    for item in items:
        if item.slot == slot and item.id == id:
            return item
    return None


def _pick(actions, op):
    """op among the actions, else the first that starts with Use or Bank, else the first."""
    for action in actions:
        if action.lower() == op.lower():
            return action
    for action in actions:
        lower = action.lower()
        if lower.startswith('use') or lower.startswith('bank'):
            return action
    return actions[0] if actions else op


def _loc_with_action(name, op):
    wanted = op.lower()
    return locs.query().name(name).where(lambda l: wanted in [a.lower() for a in l.actions()]).nearest()


class _Banking:
    """Opening a bank for a trip, and the whole trip. Until walking across the map arrives (BotApiDesign.md
    phase 6), a bank has to be in the area the server has loaded, or at a stand reachable within it."""

    def open(self, stand=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, destination=None, prefer_nearby=True, nearby_radius=14):
        """Opens a bank: a booth nearby, else a banker nearby, else the booth at stand. Use with yield from."""
        if bank.is_open():
            return True
        booth = locs.query().name(booth_name).where(lambda l: len(l.actions()) > 0).nearest()
        if booth is not None and (not prefer_nearby or booth.distance() <= nearby_radius or stand is None):
            opened = yield from bank.open_nearest_access({'name': booth_name, 'op': booth_op})
            return opened
        banker = npcs.query().action('Bank').nearest()
        if banker is not None and (not prefer_nearby or banker.distance() <= nearby_radius or stand is None):
            opened = yield from bank.open_npc_access({'name': banker.name, 'op': 'Bank'})
            return opened
        if stand is not None:
            arrived = yield from direct_navigator.walk_to(stand, 2, 120000)
            if not arrived:
                return False
            opened = yield from bank.open_booth(stand, booth_name, booth_op)
            return opened
        return False

    def bank_nearest(self, deposit, common_junk=True, destination=None, return_to=None, booth_name='Bank booth', booth_op='Use-quickly', after_deposit=None):
        """Opens a bank, deposits what deposit(name) picks (and common junk), runs after_deposit, and walks back
        to return_to. Use with yield from."""
        opened = yield from self.open(None, booth_name, booth_op, None, destination)
        if not opened:
            return False
        yield from bank.deposit_all_matching(deposit_matcher(deposit, common_junk))
        if after_deposit is not None:
            result = after_deposit()
            if is_generator(result):
                yield from result
        yield from execution.delay_ticks(1)
        if return_to is not None:
            yield from direct_navigator.walk_to(return_to, 6, 120000)
        return True


# Deposit rules and when to bank.

COMMON_BANK_LOOT = ['uncut', 'sapphire', 'emerald', 'ruby', 'diamond', 'opal', 'jade', 'topaz', 'strange fruit', 'beer', 'kebab']
RANDOM_EVENT_CASKET_ID = 405
_DISPOSABLE = ('flier', 'half a meat pie', 'half a redberry pie', 'half an apple pie')

PERIODIC_BANK_SETTINGS = {
    'bank_strategy': SettingDef('string', 'Off', 'Periodic bank', None, None, 'save accumulated loot so a death does not lose it all', ['Off', 'Loot count', 'Time', 'Either']),
    'bank_every_items': SettingDef('number', 15, 'Bank at N loot items', 1, 27),
    'bank_every_minutes': SettingDef('number', 10, 'Bank every N minutes', 1, 120),
    'bank_common_junk': SettingDef('boolean', True, 'Also bank gems/fruit/beer/kebabs/caskets'),
}


def matches_common_bank_loot(name, id=-1):
    """Gems, fruit, beer, kebabs and the random event casket."""
    if id == RANDOM_EVENT_CASKET_ID:
        return True
    if not name:
        return False
    lower = name.lower()
    return len([part for part in COMMON_BANK_LOOT if part in lower]) > 0


def is_disposable_gather_junk(name, id=-1):
    """Common bank loot, and random event leftovers that are neither gear nor a gathered product."""
    if matches_common_bank_loot(name or '', id):
        return True
    return (name or '').strip().lower() in _DISPOSABLE


def deposit_matcher(own, include_common):
    """A matcher for deposit_all_matching: own(name), or common bank loot when include_common."""
    return lambda name, id=-1: own(name) or (include_common and matches_common_bank_loot(name, id))


def deposit_all_except(keep):
    """A matcher that deposits every named item except those in keep, by whole name without regard to case."""
    kept = [name.lower() for name in keep]
    return lambda name, id=-1: len(name) > 0 and name.lower() not in kept


def parse_bank_strategy(label):
    """'off', 'items', 'time' or 'either', from a setting's label ('Off', 'Loot count', 'Time', 'Either')."""
    lower = label.strip().lower()
    if lower == 'loot count':
        return 'items'
    if lower == 'time' or lower == 'either':
        return lower
    return 'off'


def should_bank_now(strategy, state):
    """Whether to bank, from state's loot_count, minutes_since_last_bank, items_threshold and
    minutes_threshold (a dict or an object)."""
    def read(key):
        return state[key] if isinstance(state, dict) else getattr(state, key)

    loot = read('loot_count')
    if loot <= 0:
        return False
    by_items = loot >= read('items_threshold')
    by_time = read('minutes_since_last_bank') >= read('minutes_threshold')
    if strategy == 'items':
        return by_items
    if strategy == 'time':
        return by_time
    if strategy == 'either':
        return by_items or by_time
    return False


FAILURE_BACKOFF_MS = 180000


class PeriodicBank(Task):
    """A task that banks loot every so often, by items or time, as rs2b0t's PeriodicBank. Give it callables:
    strategy() ('off', 'items', 'time' or 'either'), items_threshold(), minutes_threshold(), count_loot()
    and deposit(name), and optionally after_deposit(), common_junk(), return_to() and log(message)."""

    def __init__(self, strategy=None, items_threshold=None, minutes_threshold=None, count_loot=None, deposit=None, after_deposit=None, common_junk=None, return_to=None, log=None):
        Task.__init__(self, None, None, 'periodic bank')
        self.strategy = strategy
        self.items_threshold = items_threshold
        self.minutes_threshold = minutes_threshold
        self.count_loot = count_loot
        self.deposit = deposit
        self.after_deposit = after_deposit
        self.common_junk = common_junk
        self.return_to = return_to
        self.log = log
        self.last_bank_at = _core.step_time()
        self.suppress_until = 0

    def validate(self):
        strategy = self.strategy()
        if strategy == 'off' or game.in_combat() or _core.step_time() < self.suppress_until:
            return False
        return should_bank_now(strategy, {
            'loot_count': self.count_loot(),
            'minutes_since_last_bank': (_core.step_time() - self.last_bank_at) / 60000,
            'items_threshold': self.items_threshold(),
            'minutes_threshold': self.minutes_threshold(),
        })

    def execute(self):
        common = True if self.common_junk is None else self.common_junk()
        back = None if self.return_to is None else self.return_to()
        ok = yield from banking.bank_nearest(self.deposit, common, None, back, 'Bank booth', 'Use-quickly', self.after_deposit)
        self.last_bank_at = _core.step_time()
        if not ok:
            self.suppress_until = _core.step_time() + FAILURE_BACKOFF_MS
            if self.log is not None:
                self.log('periodic bank: no bank reachable, will retry later')
            yield from execution.delay_ticks(3)
        elif self.log is not None:
            self.log('periodic bank: completed')


bank = _Bank()
banking = _Banking()

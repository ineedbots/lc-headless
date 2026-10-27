"""The bank, opening one, and when to go. Mirrors rs2b0t's api/bank/Bank.ts, Banking.ts, bankOps.ts and
bankRules.ts, and api/tasks/PeriodicBank.ts (MIT, see thirdparty/rs2b0t).

    opened = yield from banking.open()
    if opened:
        yield from bank.deposit_all_matching(deposit_all_except(['Bronze pickaxe']))
        yield from bank.withdraw_x('Lobster', 10)
        yield from bank.close()

Bank items are InvItems whose actions are the bank's options ("Withdraw 1" to "Withdraw X"), and the backpack
beside the bank's are its ("Deposit 1" to "Deposit X"). Options match without regard to case, with a hyphen
as good as a space, so rs2b0t's 'Withdraw-1' works too.
"""

import random

import _core
from rs2004 import execution
from rs2004.bot import Task, is_generator
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import direct_navigator, game
from rs2004.geometry import Tile
from rs2004.navigation import navigator, walk_opening
from rs2004.traversal import locked_bank_at, nearest_bank, nearest_bank_reachable, traversal
from rs2004.items import inventory
from rs2004.settings import SettingDef

__all__ = [
    'bank', 'banking', 'withdraw_op', 'deposit_all_except', 'deposit_matcher', 'matches_common_bank_loot',
    'is_disposable_gather_junk', 'parse_bank_strategy', 'should_bank_now', 'PeriodicBank', 'COMMON_BANK_LOOT',
    'RANDOM_EVENT_CASKET_ID', 'PERIODIC_BANK_SETTINGS', 'NEARBY_BANK_RADIUS', 'resolve_bank_open_route', 'open_bank_access',
    'purge_pack_at_bank', 'bank_pace_ticks', 'bank_pace', 'wait_bank_ready', 'withdraw_coins',
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


def _tile_of(place):
    """A Tile from a Tile, a bank's {'tile': {...}} or {'x', 'z', 'level'}."""
    if isinstance(place, dict):
        place = place.get('tile', place)
        return Tile(place['x'], place['z'], place.get('level', 0))
    return Tile.from_tile(place)


def _straight(a, b):
    dx = b.x - a.x
    dz = b.z - a.z
    return (dx * dx + dz * dz) ** 0.5


def resolve_bank_open_route(bank_open=False, here=None, stand=None, nearby_booth_dist=None, nearest=None, prefer_nearby=True, nearby_radius=14):
    """How banking.open should get a bank open, as rs2b0t's resolveBankOpenRoute decides it: 'already-open',
    'scene-booth' (a booth within nearby_radius), 'local-bank' (a known bank that near, when the preset stand
    isn't), 'preset-stand' or 'nearest-fallback'. nearest is a bank from bank_locations()."""
    if bank_open:
        return 'already-open'
    if prefer_nearby and nearby_booth_dist is not None and nearby_booth_dist <= nearby_radius:
        return 'scene-booth'
    if prefer_nearby and here is not None and nearest is not None:
        here = _tile_of(here)
        if _straight(here, _tile_of(nearest)) <= nearby_radius:
            if stand is None or _straight(here, _tile_of(stand)) > nearby_radius:
                return 'local-bank'
    if stand is not None:
        return 'preset-stand'
    return 'nearest-fallback'


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

    def loaded(self):
        """rs2b0t's: the bank's item list isn't empty, which an empty bank never is."""
        return len(self.items()) > 0

    def snapshot_ready(self):
        """rs2b0t's: open, with its item list sent."""
        return self.is_open() and _core.has_inventory(BANK)

    def snapshot_generation(self):
        """rs2b0t's: which update of the bank's item list this is, as the tick it came on, or -1 while the bank
        is shut. An action's answer comes a tick after it at the soonest, so wait_snapshot_after(generation) waits
        for it."""
        return _core.inventory_tick(BANK) if self.is_open() else -1

    def wait_snapshot_after(self, generation, timeout_ms=4000):
        """Waits for the bank's item list to update after generation. False when it doesn't, or the bank
        shuts. Use with yield from."""
        if generation < 0:
            return False
        yield from execution.delay_until(lambda: not self.is_open() or self.snapshot_generation() > generation, timeout_ms)
        return self.snapshot_ready() and self.snapshot_generation() > generation

    def normal_backpack_snapshot(self):
        """rs2b0t's: the backpack's items while the bank is shut, to compare the bank's side view against once
        it opens; None while it's open."""
        return None if self.is_open() else inventory.items()

    def backpack_ready(self, expected=None, log=None):
        """Waits up to 2 seconds for the backpack beside the open bank, and with expected, a
        normal_backpack_snapshot(), up to 4 more for it to hold the same items in the same slots. Use with yield
        from."""
        def side_ready():
            return self.is_open() and _core.has_inventory(BANK_INVENTORY)

        if not self.is_open():
            return False
        if not side_ready():
            yield from execution.delay_until(lambda: side_ready() or not self.is_open(), 2000)
        if not side_ready():
            if log is not None:
                log('bank: side backpack modal did not become ready')
            return False
        if expected is None:
            return True
        yield from execution.delay_until(lambda: not self.is_open() or _same_backpack(self.side_items(), expected), 4000)
        return self.is_open() and _same_backpack(self.side_items(), expected)

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
        """Fills the backpack from one bank item, named or by id: Withdraw All, or else X for the free slots.
        Waits for the whole load to land, not just the first of it."""
        ready = yield from self.wait_ready(READY_TIMEOUT_MS)
        by_id = isinstance(name, int)
        item = _with_id(self.items(), name) if by_id else _named(self.items(), name)
        if not ready or item is None or item.count <= 0:
            return False
        free = inventory.free()
        if free <= 0:
            return True
        all_op = withdraw_op(item._ops, 'all')
        if all_op is None:
            result = yield from self._withdraw_x(item, free, lambda: inventory.count_by_id(item.id))
            return result
        before = inventory.count_by_id(item.id)
        target = before + min(free, item.count)
        if not _use(item, all_op):
            return False
        loaded = yield from execution.delay_until(lambda: inventory.count_by_id(item.id) >= target or (inventory.count_by_id(item.id) > before and inventory.is_full()), LOAD_TIMEOUT_MS)
        return loaded

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
    """Opening a bank for a trip, and the whole trip, walking to one across the map when none is near."""

    def open(self, stand=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, destination=None, prefer_nearby=True, nearby_radius=14, log=None):
        """Opens a bank, the way resolve_bank_open_route picks: a booth within nearby_radius; else a known bank
        that near, when the preset stand isn't; else the booth at stand, walked to through the obstacles named
        ('door', 'gate') when there are some; else destination, or the nearest bank a route reaches. A bank the
        account can't use is never opened. Use with yield from."""
        say = log if log is not None else _quiet
        wanted = [o.strip().lower() for o in (obstacles or []) if o and o.strip()]
        fallback = {'name': booth_name, 'op': booth_op}
        if bank.is_open():
            return True

        here = game.tile()
        scene_booth = _real_booth(booth_name, say)
        booth_near = scene_booth if prefer_nearby and scene_booth is not None and scene_booth.distance() <= nearby_radius else None
        nearest = nearest_bank(here) if here is not None else None
        route = resolve_bank_open_route(False, here, stand, booth_near.distance() if booth_near is not None else None, nearest, prefer_nearby, nearby_radius)

        if route == 'scene-booth':
            say(f'bank: booth within {nearby_radius}; opening here')
            opened = yield from bank.open_nearest_access(fallback)
            if opened:
                return True
            # A nearby booth can be behind a house door. The world route can open it; direct clicks cannot.
            say('bank: nearby booth did not open; walking the bank route')
            route = 'preset-stand' if stand is not None else 'nearest-fallback'
            scene_booth = None

        if route == 'local-bank' and nearest is not None:
            say(f"bank: local {nearest['name']} bank; using it instead of the distant preset")
            arrived = yield from traversal.walk_resilient(_tile_of(nearest), 4, None, 120000, log=log)
            if not arrived:
                return False
            opened = yield from open_bank_access(nearest, fallback, log)
            return opened

        if route == 'preset-stand' and stand is not None:
            stand = _tile_of(stand)
            locked = locked_bank_at(stand)
            if locked is not None:
                say(f"bank: cannot use {locked['name']}; access requirements not met")
                return False
            if wanted:
                yield from walk_opening(stand, 2, wanted, log)
            else:
                arrived = yield from traversal.walk_resilient(stand, 2, None, 120000, log=log)
                if not arrived:
                    return False
            # Shantay, the Duel Arena and Gundai: the known bank's access beats a booth by name.
            known = nearest_bank(stand)
            if known is not None and (known.get('access') is not None or known.get('npcAccess') is not None) and _straight(stand, _tile_of(known)) <= nearby_radius:
                say(f"bank: {known['name']} uses {'npc' if known.get('npcAccess') is not None else 'object'} access")
                opened = yield from open_bank_access(known, fallback, log)
                return opened
            opened = yield from bank.open_booth(stand, booth_name, booth_op)
            return opened

        # No stand: a booth anywhere in the scene, else the cheapest bank a route reaches, walked to.
        dest = None
        if scene_booth is None:
            # Why: the straight line ranks every bank about the same from a dungeon, so routes rank them, with the
            # nearest by the straight line when none is reached.
            dest = destination
            if dest is None and here is not None:
                dest = nearest_bank_reachable(here, navigator)
            if dest is None:
                dest = nearest
            if dest is not None:
                say(f"no booth in scene; walking to the {dest['name']} bank")
                arrived = yield from traversal.walk_resilient(_tile_of(dest), 4, None, 120000, log=log)
                if not arrived:
                    say(f"bank: could not reach {dest['name']}")
                    return False
        else:
            say(f"bank: opening the {booth_name} in view")
        opened = yield from open_bank_access(dest, fallback, log)
        return opened

    def bank_nearest(self, deposit, common_junk=True, destination=None, return_to=None, booth_name='Bank booth', booth_op='Use-quickly', after_deposit=None, log=None):
        """Opens a bank, deposits what deposit(name) picks (and common junk), runs after_deposit, and walks back
        to return_to. Use with yield from."""
        opened = yield from self.open(None, booth_name, booth_op, None, destination, log=log)
        if not opened:
            return False
        yield from bank.deposit_all_matching(deposit_matcher(deposit, common_junk))
        if after_deposit is not None:
            result = after_deposit()
            if is_generator(result):
                yield from result
        yield from execution.delay_ticks(1)
        if return_to is not None:
            yield from traversal.walk_resilient(return_to, 6, None, 120000, log=log)
        return True


def _quiet(_):
    pass


def _same_backpack(left, right):
    """The same items, by slot, id and count."""
    if len(left) != len(right):
        return False
    held = [(item.slot, item.id, item.count) for item in right]
    return len([item for item in left if (item.slot, item.id, item.count) in held]) == len(left)


def _real_booth(booth_name, say):
    """The nearest booth of that name in the scene that has options and isn't at a bank the account can't use."""
    skipped = []

    def usable(loc):
        if len(loc.actions()) == 0:
            return False
        locked = locked_bank_at(loc.tile())
        if locked is None:
            return True
        if locked['name'] not in skipped:
            say(f"bank: skipping {locked['name']}; access requirements not met")
            skipped.append(locked['name'])
        return False

    return locs.query().name(booth_name).where(usable).nearest()


def _object_access(access):
    """A bank's access as bank.open_nearest_access takes it, from a bank_locations() entry's camelCase."""
    first = access.get('open_first', access.get('openFirst'))
    return {'name': access['name'], 'op': access['op'], 'open_first': first}


def open_bank_access(dest, fallback, log=None):
    """Opens the bank dest names, a bank_locations() entry: through its banker when it has npcAccess, else by
    its access, else by fallback ({'name': ..., 'op': ...}). Use with yield from."""
    npc = dest.get('npcAccess', dest.get('npc_access')) if dest is not None else None
    if npc is not None:
        opened = yield from bank.open_npc_access({'name': npc['name'], 'op': npc['op'], 'choose': npc.get('choose')})
        return opened
    access = dest.get('access') if dest is not None else None
    opened = yield from bank.open_nearest_access(_object_access(access if access is not None else fallback))
    return opened


def purge_pack_at_bank(keep, stand=None, destination=None, prefer_nearby=None, booth_name='Bank booth', booth_op='Use-quickly', obstacles=None, log=None):
    """rs2b0t's start-of-run cleanup: banks everything but the keep names, so a bot can start with a pack of
    junk. True when nothing needed banking or the backpack is clear; False when the bank couldn't be opened or
    junk is left. Use with yield from."""
    say = log if log is not None else (lambda message: None)
    deposit = deposit_all_except(keep)
    junk = [i for i in inventory.items() if deposit(i.name or '')]
    if not junk:
        return True
    say(f'start purge: banking {len(junk)} stack(s) (keep: {", ".join(list(keep)) or "none"})')
    opened = yield from banking.open(stand, booth_name, booth_op, obstacles, destination, prefer_nearby is not False, log=log)
    if not opened:
        say('start purge: could not open bank; leaving the backpack as it is')
        return False
    yield from bank.deposit_all_matching(lambda name, id=-1: deposit(name))
    yield from execution.delay_ticks(1)
    yield from bank.close()
    left = [i for i in inventory.items() if deposit(i.name or '')]
    if left:
        say(f'start purge: still holding {len(left)} junk stack(s) after depositing')
        return False
    say('start purge: backpack cleared')
    return True


def bank_pace_ticks(rand=None):
    """rs2b0t's pause between bank actions: 2 ticks about a third of the time, else 1, so an open, a scan and a
    close never land on one tick."""
    roll = rand() if rand is not None else random.random()
    return 2 if roll < 0.35 else 1


def bank_pace(log=None):
    """Pauses between bank actions. Use with yield from."""
    ticks = bank_pace_ticks()
    if log is not None:
        log(f'bank: pause {ticks}t')
    yield from execution.delay_ticks(ticks)


def wait_bank_ready(log=None):
    """Waits for the open bank's items, up to 7 ticks, pacing around it as rs2b0t does. False once it's
    closed. Use with yield from."""
    if not bank.is_open():
        return False
    yield from bank_pace(log)
    yield from execution.delay_until_ticks(lambda: bank.ready() or not bank.is_open(), 7)
    if not bank.is_open():
        return False
    yield from execution.delay_ticks(1)
    yield from bank_pace()
    return bank.is_open()


def withdraw_coins(need, inv_coins, bank_coins, coin_name='Coins', log=None):
    """With the bank open, withdraws coins until the backpack holds need. False when the bank has none or the
    withdraw fails. Use with yield from."""
    say = log if log is not None else (lambda message: None)
    take = max(0, need - inv_coins)
    if take <= 0:
        return True
    if not bank.is_open():
        return False
    if bank_coins <= 0:
        say(f'acquire: no coins in the bank (need {need}gp)')
        return False
    amount = min(take, bank_coins)
    say(f'acquire: withdraw {amount}gp')
    yield from bank_pace()
    withdrew = yield from bank.withdraw_x(coin_name, amount)
    if not withdrew:
        return False
    target = min(need, inv_coins + amount)
    ok = yield from execution.delay_until_ticks(lambda: inventory.count(coin_name) >= target, 7)
    if ok:
        yield from bank_pace()
    return ok


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
    and deposit(name), and optionally after_deposit(), common_junk(), return_to(), destination() (one of
    bank_locations() to bank at), log(message) and set_status(text), told when a run starts."""

    def __init__(self, strategy=None, items_threshold=None, minutes_threshold=None, count_loot=None, deposit=None, after_deposit=None, common_junk=None, return_to=None, log=None, destination=None, set_status=None):
        Task.__init__(self, None, None, 'periodic bank')
        self.destination = destination
        self.set_status = set_status
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
        if self.set_status is not None:
            self.set_status('periodic bank run')
        common = True if self.common_junk is None else self.common_junk()
        back = None if self.return_to is None else self.return_to()
        where = None if self.destination is None else self.destination()
        ok = yield from banking.bank_nearest(self.deposit, common, where, back, 'Bank booth', 'Use-quickly', self.after_deposit, log=self.log)
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

"""Bank transfers over delayed server snapshots, using the real bank implementation."""

import rs2004.bank as vault
from rs2004 import execution


class Item:
    def __init__(self, id, name, count, slot=0, ops=None):
        self.id = id
        self.name = name
        self.count = count
        self.slot = slot
        self._ops = ops if ops is not None else ['Withdraw 1', 'Withdraw 5', 'Withdraw 10', 'Withdraw All', 'Withdraw X']


class BankWorld:
    def __init__(self):
        self.bank = vault._Bank()
        self.bank._root = 100
        self.open = True
        self.bank_ready = True
        self.side_ready = True
        self.stock = [Item(1511, 'Logs', 50)]
        self.pack = []
        self.now = 0
        self.generation = 10
        self.free_slots = 28
        self.clicks = []
        self.answers = []
        self.waits = []
        self.events = []
        self.pending = None
        self.selected = None
        self.count_open = False
        self.accept_click = True
        self.accept_answer = True
        self.respond = True
        self.close_responds = True
        self.lands_as_id = None
        self.arrival_limit = None

    def __enter__(self):
        self.saved = (vault._core, vault.inventory, execution._core)
        vault._core = self
        vault.inventory = self
        execution._core = self
        # The empty test cache gives both built-in component ids the same sentinel.
        # Give the two inventories distinct ids, as a loaded game cache does.
        vault.BANK = 101
        vault.BANK_INVENTORY = 102
        return self

    def __exit__(self, *args):
        vault._core, vault.inventory, execution._core = self.saved
        del vault.BANK
        del vault.BANK_INVENTORY

    def step_time(self):
        return self.now

    def get_main_modal(self):
        return 100 if self.open else -1

    def has_inventory(self, com):
        assert com in [101, 102]
        return self.bank_ready if com == 101 else self.side_ready

    def get_inventory(self, com):
        assert com in [101, 102]
        return self.stock if com == 101 else self.pack

    def inventory_tick(self, com):
        assert com == 101
        return self.generation

    def items(self):
        return self.pack

    def count(self, name):
        return sum([i.count for i in self.pack if i.name is not None and i.name.lower() == name.strip().lower()])

    def count_by_id(self, id):
        return sum([i.count for i in self.pack if i.id == id])

    def free(self):
        return self.free_slots

    def is_full(self):
        return self.free_slots <= 0

    def inv_button(self, item, op):
        label = item._ops[op - 1]
        self.clicks.append((item.id, label))
        if not self.accept_click:
            return False
        self.selected = item
        words = label.lower().replace('-', ' ').split()
        if words[0] == 'deposit':
            self.pending = ('deposit', 0)
        elif words[-1] == 'x':
            self.pending = ('dialog', 0)
        else:
            amount = self.free_slots if words[-1] == 'all' else int(words[-1])
            self.pending = ('withdraw', amount)
        return True

    def is_count_dialog_open(self):
        return self.count_open

    def answer_count(self, amount):
        self.answers.append(amount)
        if not self.accept_answer:
            return False
        self.count_open = False
        self.pending = ('withdraw', amount)
        return True

    def click_text(self, text, root):
        assert root == 100
        self.clicks.append(text)
        return self.accept_click

    def close_interfaces(self):
        self.clicks.append('close')
        if self.close_responds:
            self.pending = ('close', 0)

    def advance(self):
        if self.events:
            key, value = self.events.pop(0)
            setattr(self, key, value)
        if not self.respond or self.pending is None:
            return
        kind, amount = self.pending
        self.pending = None
        if kind == 'dialog':
            self.count_open = True
        elif kind == 'close':
            self.open = False
        elif kind == 'deposit':
            self.pack = [i for i in self.pack if i is not self.selected]
            self.generation += 1
        elif kind == 'withdraw':
            take = min(amount, self.selected.count)
            if self.arrival_limit is not None:
                take = min(take, self.arrival_limit)
            self.selected.count -= take
            id = self.selected.id if self.lands_as_id is None else self.lands_as_id
            self.pack.append(Item(id, self.selected.name, take))
            self.free_slots = max(0, self.free_slots - take)
            self.generation += 1

    def run(self, task):
        for guard in range(180):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.waits.append(wait)
            self.now += 500
            self.advance()
        assert False, 'bank operation exceeded its simulated update budget'


def test_fixed_withdrawals_wait_for_items_and_skip_the_count_dialog():
    for amount in [1, 5, 10]:
        with BankWorld() as world:
            assert world.run(world.bank.withdraw_x(' logs ', amount))
            assert world.clicks == [(1511, 'Withdraw ' + str(amount))]
            assert world.answers == []
            assert world.count('Logs') == amount
            assert world.stock[0].count == 50 - amount
            assert len(world.waits) == 1


def test_custom_withdrawal_waits_for_dialog_and_inventory_update():
    with BankWorld() as world:
        assert world.run(world.bank.withdraw_x('Logs', 7))
        assert world.answers == [7]
        assert world.count('Logs') == 7
        assert len(world.waits) == 2


def test_withdrawal_is_clamped_to_available_bank_stock():
    with BankWorld() as world:
        world.stock[0].count = 5
        assert world.run(world.bank.withdraw_x('Logs', 30))
        assert world.clicks == [(1511, 'Withdraw 5')]
        assert world.count('Logs') == 5


def test_zero_and_negative_withdrawals_do_not_click():
    with BankWorld() as world:
        world.open = False
        for amount in [0, -1]:
            assert world.run(world.bank.withdraw_x('Missing', amount))
        assert world.clicks == []
        assert world.waits == []


def test_missing_empty_and_closed_bank_withdrawals_fail_without_clicking():
    with BankWorld() as world:
        assert not world.run(world.bank.withdraw_x('Missing', 5))
        world.stock[0].count = 0
        assert not world.run(world.bank.withdraw_x('Logs', 5))
        world.stock[0].count = 50
        world.open = False
        assert not world.run(world.bank.withdraw_x('Logs', 5))
        assert world.clicks == []


def test_withdrawal_waits_until_both_inventory_snapshots_are_ready():
    with BankWorld() as world:
        world.bank_ready = False
        world.side_ready = False
        world.events = [('bank_ready', True), ('side_ready', True)]
        assert world.run(world.bank.withdraw_x('Logs', 5))
        assert len(world.waits) == 3
        assert world.count('Logs') == 5


def test_unready_bank_times_out_without_sending_a_withdrawal():
    with BankWorld() as world:
        world.side_ready = False
        assert not world.run(world.bank.withdraw_x('Logs', 5))
        assert world.now >= vault.READY_TIMEOUT_MS
        assert world.clicks == []


def test_rejected_withdrawal_clicks_fail_without_waiting():
    for amount in [5, 7]:
        with BankWorld() as world:
            world.accept_click = False
            assert not world.run(world.bank.withdraw_x('Logs', amount))
            assert world.waits == []
            assert world.answers == []


def test_missing_count_dialog_and_rejected_answer_fail_without_items():
    with BankWorld() as world:
        world.respond = False
        assert not world.run(world.bank.withdraw_x('Logs', 7))
        assert world.now >= vault.COUNT_DIALOG_TIMEOUT_MS
        assert world.answers == []
        assert world.pack == []
    with BankWorld() as world:
        world.accept_answer = False
        assert not world.run(world.bank.withdraw_x('Logs', 7))
        assert world.answers == [7]
        assert world.pack == []


def test_missing_withdraw_options_do_not_send_a_different_amount():
    with BankWorld() as world:
        world.stock[0]._ops = ['Withdraw 1']
        assert not world.run(world.bank.withdraw_x('Logs', 7))
        assert world.clicks == []


def test_fixed_amount_falls_back_to_x_when_its_option_is_missing():
    with BankWorld() as world:
        world.stock[0]._ops = ['Withdraw X']
        assert world.run(world.bank.withdraw_x('Logs', 5))
        assert world.answers == [5]
        assert world.count('Logs') == 5


def test_existing_stack_does_not_acknowledge_an_unanswered_withdrawal():
    with BankWorld() as world:
        world.pack = [Item(1511, 'Logs', 10)]
        world.respond = False
        assert not world.run(world.bank.withdraw_x('Logs', 5))
        assert world.count('Logs') == 10
        assert world.now >= vault.LOAD_TIMEOUT_MS


def test_partial_withdrawal_only_succeeds_when_the_backpack_fills():
    for free in [2, 28]:
        with BankWorld() as world:
            world.free_slots = free
            world.arrival_limit = 2
            assert world.run(world.bank.withdraw_x('Logs', 5)) == (free == 2)
            assert world.count('Logs') == 2
            if free == 28:
                assert world.now >= vault.LOAD_TIMEOUT_MS


def test_full_backpack_without_new_items_does_not_count_as_a_withdrawal():
    with BankWorld() as world:
        world.free_slots = 0
        world.respond = False
        assert not world.run(world.bank.withdraw_x('Logs', 5))
        assert world.pack == []


def test_noted_withdrawal_waits_for_the_note_id():
    with BankWorld() as world:
        world.lands_as_id = 1512
        assert world.run(world.bank.withdraw_x_by_id(1511, 5, lands_as_id=1512))
        assert world.count_by_id(1512) == 5
        assert world.count_by_id(1511) == 0


def test_wrong_landing_id_does_not_acknowledge_a_withdrawal():
    with BankWorld() as world:
        world.lands_as_id = 1512
        assert not world.run(world.bank.withdraw_x_by_id(1511, 5))
        assert world.count_by_id(1512) == 5
        assert world.now >= vault.LOAD_TIMEOUT_MS


def test_withdraw_load_uses_all_and_waits_for_the_whole_load():
    for name in ['Logs', 1511]:
        with BankWorld() as world:
            world.free_slots = 12
            assert world.run(world.bank.withdraw_load(name))
            assert world.clicks == [(1511, 'Withdraw All')]
            assert world.count('Logs') == 12


def test_withdraw_load_falls_back_to_x_for_the_free_slots():
    with BankWorld() as world:
        world.free_slots = 12
        world.stock[0]._ops = ['Withdraw X']
        assert world.run(world.bank.withdraw_load(1511))
        assert world.answers == [12]
        assert world.count('Logs') == 12


def test_withdraw_load_handles_full_pack_missing_stock_and_refused_click():
    with BankWorld() as world:
        world.free_slots = 0
        assert world.run(world.bank.withdraw_load('Logs'))
        assert not world.run(world.bank.withdraw_load('Missing'))
        assert world.clicks == []
        world.free_slots = 28
        world.accept_click = False
        assert not world.run(world.bank.withdraw_load('Logs'))
        assert world.pack == []


def test_partial_load_with_free_space_times_out():
    with BankWorld() as world:
        world.arrival_limit = 3
        assert not world.run(world.bank.withdraw_load('Logs'))
        assert world.count('Logs') == 3
        assert world.now >= vault.LOAD_TIMEOUT_MS


def test_deposit_matching_preserves_keep_items_and_processes_multiple_slots():
    with BankWorld() as world:
        world.pack = [Item(1511, 'Logs', 5, 0, ['Deposit 1', 'Deposit All']), Item(590, 'Tinderbox', 1, 1, ['Deposit All']), Item(1511, 'Logs', 3, 2, ['Deposit All'])]
        world.run(world.bank.deposit_all_matching(vault.deposit_all_except(['Tinderbox'])))
        assert [(i.id, i.count) for i in world.pack] == [(590, 1)]
        assert world.clicks == [(1511, 'Deposit All'), (1511, 'Deposit All')]
        assert len(world.waits) == 2


def test_deposit_inventory_includes_nameless_items():
    with BankWorld() as world:
        world.pack = [Item(405, None, 1, 0, ['Deposit All']), Item(995, 'Coins', 50, 1, ['Deposit All'])]
        world.run(world.bank.deposit_inventory())
        assert world.pack == []
        assert len(world.clicks) == 2


def test_deposit_stops_on_missing_options_or_refused_click():
    for ops in [[], ['Deposit All']]:
        with BankWorld() as world:
            world.pack = [Item(1511, 'Logs', 5, 0, ops)]
            world.accept_click = False
            world.run(world.bank.deposit_inventory())
            assert world.pack[0].count == 5
            assert world.waits == []


def test_deposit_waits_for_the_side_inventory_to_arrive():
    with BankWorld() as world:
        world.side_ready = False
        world.events = [('side_ready', True)]
        world.pack = [Item(1511, 'Logs', 5, 0, ['Deposit All'])]
        world.run(world.bank.deposit_inventory())
        assert world.pack == []
        assert len(world.waits) == 2


def test_unacknowledged_deposits_stop_after_the_retry_budget():
    with BankWorld() as world:
        world.pack = [Item(1511, 'Logs', 5, 0, ['Deposit All'])]
        world.respond = False
        world.run(world.bank.deposit_inventory())
        assert len(world.clicks) == vault.DEPOSIT_ROUNDS
        assert world.pack[0].count == 5
        assert world.now == vault.DEPOSIT_ROUNDS * vault.DEPOSIT_TIMEOUT_MS


def test_direct_bank_actions_match_names_ids_and_normalized_options():
    with BankWorld() as world:
        world.stock.append(Item(1511, 'Logs', 3, 1))
        world.stock.append(Item(999, None, 1, 2))
        assert world.bank.count(' LOGS ') == 53
        assert world.bank.count_by_id(1511) == 53
        assert world.bank.withdraw(' logs ', 'withdraw-5')
        assert world.bank.withdraw_by_id(1511, 'WITHDRAW 10')
        assert not world.bank.withdraw_by_id(12345)
        assert not world.bank.withdraw('Missing')
        world.pack = [Item(1511, 'Logs', 5, 0, ['Deposit-All'])]
        assert world.bank.deposit(' LOGS ', 'deposit all')
        assert world.clicks == [(1511, 'Withdraw 5'), (1511, 'Withdraw 10'), (1511, 'Deposit-All')]


def test_snapshot_wait_requires_a_newer_generation():
    with BankWorld() as world:
        world.events = [('generation', 10), ('generation', 11)]
        assert world.run(world.bank.wait_snapshot_after(10))
        assert len(world.waits) == 2
    with BankWorld() as world:
        assert not world.run(world.bank.wait_snapshot_after(10, 1000))
        assert world.now == 1000
        assert not world.run(world.bank.wait_snapshot_after(-1))


def test_snapshot_wait_fails_if_bank_closes_or_snapshot_is_unavailable():
    with BankWorld() as world:
        world.events = [('open', False)]
        assert not world.run(world.bank.wait_snapshot_after(10))
    with BankWorld() as world:
        world.bank_ready = False
        world.events = [('generation', 11)]
        assert not world.run(world.bank.wait_snapshot_after(10))


def test_backpack_ready_compares_slot_id_and_count_after_delayed_updates():
    with BankWorld() as world:
        expected = [Item(1511, 'Logs', 5, 2)]
        world.pack = [Item(1511, 'Logs', 4, 2)]
        world.events = [('pack', [Item(1511, 'Logs', 5, 0)]), ('pack', expected)]
        assert world.run(world.bank.backpack_ready(expected))
        assert len(world.waits) == 2


def test_backpack_ready_logs_missing_side_snapshot_and_rejects_stale_items():
    with BankWorld() as world:
        messages = []
        world.side_ready = False
        assert not world.run(world.bank.backpack_ready(log=messages.append))
        assert len(messages) == 1
        world.side_ready = True
        assert not world.run(world.bank.backpack_ready([Item(1511, 'Logs', 5)]))
        world.open = False
        assert not world.run(world.bank.backpack_ready())


def test_note_mode_waits_a_tick_and_handles_refused_or_closed_interfaces():
    with BankWorld() as world:
        assert world.run(world.bank.set_note_mode(True))
        assert world.run(world.bank.set_note_mode(False))
        assert world.clicks == ['Note', 'Item']
        assert [wait.count for wait in world.waits] == [1, 1]
        world.accept_click = False
        assert not world.run(world.bank.set_note_mode(True))
        world.open = False
        assert not world.run(world.bank.set_note_mode(True))


def test_close_waits_for_acknowledgement_and_times_out_if_ignored():
    with BankWorld() as world:
        assert world.run(world.bank.close())
        assert not world.open
        assert world.run(world.bank.close())
        assert world.clicks == ['close']
    with BankWorld() as world:
        world.close_responds = False
        assert not world.run(world.bank.close(1000))
        assert world.open
        assert world.now == 1000

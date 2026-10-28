"""Bank transfers and opening over delayed server updates, using the real bank implementation."""

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


class AccessTarget:
    def __init__(self, world, name='Bank booth', ops=None, distance=3, response='open'):
        self.world = world
        self.name = name
        self.ops = ['Use-quickly'] if ops is None else ops
        self.dist = distance
        self.response = response
        self.refusals = 0
        self.position = Tile(3093, 3243)

    def actions(self):
        return self.ops

    def distance(self):
        return self.dist

    def tile(self):
        return self.position

    def interact(self, op):
        assert op in self.ops
        self.world.interactions.append((self.name, op))
        if self.refusals > 0:
            self.refusals -= 1
            return False
        self.world.scene_pending = self.response
        return True


class AccessQuery:
    def __init__(self, items):
        self.items = list(items)

    def name(self, name):
        return self.where(lambda item: item.name.lower() == name.lower())

    def action(self, op):
        return self.where(lambda item: op.lower() in [a.lower() for a in item.actions()])

    def where(self, predicate):
        self.items = [i for i in self.items if predicate(i)]
        return self

    def nearest(self):
        self.items.sort(key=lambda item: item.distance())
        return self.items[0] if self.items else None


class AccessEntities:
    def __init__(self, world, field):
        self.world = world
        self.field = field

    def query(self):
        return AccessQuery(getattr(self.world, self.field))


class AccessDialogue:
    def __init__(self, world):
        self.world = world
        self.open = False
        self.choices = []
        self.continued = 0
        self.chosen = []
        self.continue_opens = True
        self.choose_opens = True

    def is_open(self):
        return self.open

    def can_continue(self):
        return self.open and not self.choices

    def options(self):
        return self.choices

    def continue_(self):
        assert self.can_continue()
        self.continued += 1
        self.open = False
        self.world.scene_pending = 'open' if self.continue_opens else None
        yield execution.Ticks(1)

    def choose_option(self, choice):
        assert any([choice.lower() in option.lower() for option in self.choices])
        self.chosen.append(choice)
        self.open = False
        self.choices = []
        self.world.scene_pending = 'open' if self.choose_opens else None
        yield execution.Ticks(1)


class OpeningWorld(BankWorld):
    def __init__(self):
        super().__init__()
        self.open = False
        self.objects = []
        self.people = []
        self.interactions = []
        self.walks = []
        self.scene_pending = None
        self.revealed = None
        self.dialogue = AccessDialogue(self)

    def __enter__(self):
        super().__enter__()
        self.access_saved = (vault.locs, vault.npcs, vault.chat_dialog, vault.direct_navigator, vault.bank)
        vault.locs = AccessEntities(self, 'objects')
        vault.npcs = AccessEntities(self, 'people')
        vault.chat_dialog = self.dialogue
        vault.direct_navigator = self
        vault.bank = self.bank
        return self

    def __exit__(self, *args):
        vault.locs, vault.npcs, vault.chat_dialog, vault.direct_navigator, vault.bank = self.access_saved
        super().__exit__(*args)

    def walk_to(self, tile, radius, timeout):
        self.walks.append((tile, radius, timeout))
        yield execution.Ticks(1)
        for target in self.objects:
            target.dist = 1
        return True

    def advance(self):
        super().advance()
        response = self.scene_pending
        self.scene_pending = None
        if response == 'open':
            self.open = True
        elif response == 'dialogue':
            self.dialogue.open = True
        elif response == 'reveal':
            self.objects = [self.revealed]


def test_open_nearest_selects_an_actionable_booth_and_waits_for_open():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, ops=[], distance=0), AccessTarget(world, distance=4, response=None), AccessTarget(world, distance=2)]
        assert world.run(world.bank.open_nearest())
        assert world.interactions == [('Bank booth', 'Use-quickly')]
        assert len(world.waits) == 1
        assert world.walks == []


def test_opening_an_already_open_bank_does_not_interact_or_walk():
    with OpeningWorld() as world:
        world.open = True
        assert world.run(world.bank.open_booth(Tile(3093, 3243)))
        assert world.run(world.bank.open_nearest())
        assert world.run(world.bank.open_nearest_access({'name': 'Bank chest', 'op': 'Use'}))
        assert world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Bank'}))
        assert world.interactions == []
        assert world.walks == []
        assert world.waits == []


def test_open_booth_waits_for_a_missing_booth_to_appear():
    with OpeningWorld() as world:
        world.events = [('objects', [AccessTarget(world)])]
        assert world.run(world.bank.open_booth(Tile(3093, 3243)))
        assert isinstance(world.waits[0], execution.Ticks)
        assert world.waits[0].count == 2
        assert len(world.interactions) == 1


def test_missing_booth_has_bounded_retries_and_nearest_fails_immediately():
    with OpeningWorld() as world:
        assert not world.run(world.bank.open_nearest())
        assert world.waits == []
        assert not world.run(world.bank.open_booth(Tile(3093, 3243)))
        assert len(world.waits) == 4
        assert world.interactions == []


def test_refused_booth_interaction_walks_to_the_stand_before_retrying():
    with OpeningWorld() as world:
        booth = AccessTarget(world)
        booth.refusals = 1
        world.objects = [booth]
        stand = Tile(3092, 3243)
        assert world.run(world.bank.open_booth(stand))
        assert len(world.interactions) == 2
        assert world.walks == [(stand, 1, vault.STAND_TIMEOUT_MS)]


def test_nearest_booth_steps_beside_a_distant_target_after_refusal():
    with OpeningWorld() as world:
        booth = AccessTarget(world)
        booth.refusals = 1
        world.objects = [booth]
        assert world.run(world.bank.open_nearest())
        assert world.walks == [(booth.tile(), 1, vault.STAND_TIMEOUT_MS)]
        assert len(world.interactions) == 2


def test_adjacent_refusals_exhaust_attempts_without_walking():
    with OpeningWorld() as world:
        booth = AccessTarget(world, distance=1)
        booth.refusals = 100
        world.objects = [booth]
        assert not world.run(world.bank.open_nearest())
        assert len(world.interactions) == vault.OPEN_ATTEMPTS
        assert world.walks == []
        assert world.waits == []


def test_silent_booth_times_out_each_attempt_instead_of_reporting_open():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, distance=1, response=None)]
        assert not world.run(world.bank.open_nearest())
        assert len(world.interactions) == vault.OPEN_ATTEMPTS
        assert world.now == vault.OPEN_ATTEMPTS * vault.OPEN_TIMEOUT_MS
        assert not world.open


def test_booth_continues_a_greeting_before_the_bank_opens():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, response='dialogue')]
        assert world.run(world.bank.open_nearest())
        assert world.dialogue.continued == 1
        assert world.open


def test_greeting_without_a_following_bank_does_not_report_success():
    with OpeningWorld() as world:
        world.dialogue.continue_opens = False
        target = AccessTarget(world, response='dialogue')
        assert not world.run(world.bank._open_with(target, 'Use-quickly'))
        assert world.dialogue.continued == 1
        assert world.now >= vault.ADJACENT_OPEN_TIMEOUT_MS


def test_booth_action_selection_uses_available_use_or_bank_options():
    for ops in [['Examine', 'Use'], ['Examine', 'Bank'], ['Open'], ['Use', 'Use-quickly']]:
        with OpeningWorld() as world:
            world.objects = [AccessTarget(world, ops=ops)]
            assert world.run(world.bank.open_nearest())
            assert world.interactions == [('Bank booth', ops[-1])]


def test_closed_chest_is_opened_before_using_the_revealed_chest():
    for spelling in ['openFirst', 'open_first']:
        with OpeningWorld() as world:
            world.objects = [AccessTarget(world, 'Closed chest', ['Open'], response='reveal')]
            world.revealed = AccessTarget(world, 'Bank chest', ['Use'])
            access = {'name': 'Bank chest', 'op': 'Use', spelling: {'name': 'Closed chest', 'op': 'Open'}}
            assert world.run(vault.open_bank_access({'access': access}, {}))
            assert world.interactions == [('Closed chest', 'Open'), ('Bank chest', 'Use')]


def test_already_usable_chest_skips_the_open_first_action():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, 'Bank chest', ['Use'])]
        access = {'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}
        assert world.run(world.bank.open_nearest_access(access))
        assert world.interactions == [('Bank chest', 'Use')]


def test_missing_or_refused_closed_chest_does_not_use_another_object():
    for missing in [True, False]:
        with OpeningWorld() as world:
            closed = AccessTarget(world, 'Closed chest', ['Open'])
            closed.refusals = 1
            world.objects = [] if missing else [closed]
            access = {'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}
            assert not world.run(world.bank.open_nearest_access(access))
            assert world.waits == []
            assert not world.open


def test_opening_a_chest_can_open_the_bank_directly():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, 'Closed chest', ['Open'])]
        access = {'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}
        assert world.run(world.bank.open_nearest_access(access))
        assert world.interactions == [('Closed chest', 'Open')]


def test_chest_that_never_opens_times_out_without_bank_success():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, 'Closed chest', ['Open'], response=None)]
        access = {'name': 'Bank chest', 'op': 'Use', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}
        assert not world.run(world.bank.open_nearest_access(access))
        assert world.now == vault.OPEN_TIMEOUT_MS
        assert world.interactions == [('Closed chest', 'Open')]


def test_banker_access_uses_the_requested_npc_action():
    with OpeningWorld() as world:
        world.people = [AccessTarget(world, 'Banker', ['Talk-to'], distance=0), AccessTarget(world, 'Banker', ['Bank'])]
        assert world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Bank'}))
        assert world.interactions == [('Banker', 'Bank')]
        assert world.dialogue.continued == 0


def test_banker_access_continues_dialogue_and_matches_the_bank_choice():
    for spelling in ['npcAccess', 'npc_access']:
        with OpeningWorld() as world:
            world.people = [AccessTarget(world, 'Banker', ['Talk-to'], response='dialogue')]
            world.dialogue.choices = ['Show me my BANK account, please.', 'Goodbye.']
            destination = {spelling: {'name': 'Banker', 'op': 'Talk-to', 'choose': 'bank account'}}
            assert world.run(vault.open_bank_access(destination, {}))
            assert world.dialogue.chosen == ['bank account']
            assert world.interactions == [('Banker', 'Talk-to')]
    with OpeningWorld() as world:
        world.people = [AccessTarget(world, 'Banker', ['Talk-to'], response='dialogue')]
        assert world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Talk-to'}))
        assert world.dialogue.continued == 1


def test_existing_banker_dialogue_does_not_interact_with_the_npc_again():
    with OpeningWorld() as world:
        world.dialogue.open = True
        world.dialogue.choices = ['Bank, please.', 'Leave.']
        assert world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Talk-to', 'choose': 'Bank'}))
        assert world.interactions == []
        assert world.dialogue.chosen == ['Bank']


def test_missing_and_unresponsive_bankers_have_bounded_retries():
    with OpeningWorld() as world:
        assert not world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Bank'}))
        assert len(world.waits) == 3
        assert world.interactions == []
    with OpeningWorld() as world:
        world.people = [AccessTarget(world, 'Banker', ['Bank'], response=None)]
        assert not world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Bank'}))
        assert len(world.interactions) == 3
        assert world.now == 3 * (6000 + 3000)


def test_unrelated_banker_options_are_never_selected():
    with OpeningWorld() as world:
        world.people = [AccessTarget(world, 'Banker', ['Talk-to'], response='dialogue')]
        world.dialogue.choices = ['Tell me about yourself.', 'Goodbye.']
        assert not world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Talk-to', 'choose': 'bank'}))
        assert world.dialogue.chosen == []
        assert world.dialogue.continued == 0
        assert len(world.interactions) == 1


def test_accepted_banker_choice_without_an_open_bank_still_fails():
    with OpeningWorld() as world:
        world.people = [AccessTarget(world, 'Banker', ['Talk-to'], response='dialogue')]
        world.dialogue.choices = ['Bank, please.']
        world.dialogue.choose_opens = False
        world.dialogue.continue_opens = False
        assert not world.run(world.bank.open_npc_access({'name': 'Banker', 'op': 'Talk-to', 'choose': 'Bank'}))
        assert world.dialogue.chosen == ['Bank']
        assert len(world.interactions) == 3
        assert not world.open


def test_bank_access_without_destination_uses_the_fallback_object():
    with OpeningWorld() as world:
        world.objects = [AccessTarget(world, 'Bank chest', ['Use'])]
        assert world.run(vault.open_bank_access(None, {'name': 'Bank chest', 'op': 'Use'}))
        assert world.interactions == [('Bank chest', 'Use')]

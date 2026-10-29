"""Cake stealing and food banking react to delayed inventory, chat and combat updates."""

import rs2004.catalogs.thieving as thieving
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_bank_workflows import BankWorld, Item


class Stall:
    name = "Baker's stall"
    id = 2561

    def __init__(self, world, tile):
        self.world = world
        self.position = tile

    def tile(self):
        return self.position

    def distance(self):
        return self.position.distance_to(self.world.position)

    def actions(self):
        return ['Steal from']

    def interact(self, op):
        assert op == 'Steal from'
        self.world.steals += 1
        outcome = self.world.outcomes.pop(0) if self.world.outcomes else 'success'
        if outcome == 'reject':
            return False
        self.world.pending_steal = outcome
        return True


class ThievingWorld(BankWorld):
    def __init__(self):
        BankWorld.__init__(self)
        self.stock = [Item(1891, 'Cake', 50)]
        self.position = thieving.STAND
        self.combat = False
        self.walk_lands = True
        self.walks = []
        self.logs = []
        self.statuses = []
        self.listeners = []
        self.outcomes = []
        self.pending_steal = None
        self.steals = 0
        self.successes = 0
        self.resets = 0
        self.abort_at = None
        self.restock_at = None
        self.stalls = [Stall(self, thieving.STALL_TILE)]

    def __enter__(self):
        BankWorld.__enter__(self)
        replacements = {
            '_core': self, 'bank': self.bank, 'inventory': self,
            'game': FakeModule(tile=lambda: self.position, tick=self.tick, in_combat=lambda: self.combat),
            'traversal': FakeModule(walk_to=self.walk),
            'locs': FakeModule(query=lambda: EntityQuery(self.scene, lambda loc: True)),
            'events': FakeModule(on=self.subscribe),
            '_seen': {'attempt': False, 'lockout': False, 'listening': False},
        }
        self.thieving_saved = {}
        for name, value in replacements.items():
            self.thieving_saved[name] = getattr(thieving, name)
            setattr(thieving, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.thieving_saved.items():
            setattr(thieving, name, value)
        BankWorld.__exit__(self, *args)

    def used(self):
        return 28 - self.free_slots

    def tick(self):
        return self.now // 500

    def subscribe(self, name, callback):
        assert name == 'chat_message'
        self.listeners.append(callback)

    def scene(self, ids, names, radius, layer):
        return [loc for loc in self.stalls if names is None or loc.name in names]

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        kwargs['log']('walking to stand')
        yield execution.Ticks(1)
        if self.walk_lands:
            self.position = tile
        return self.walk_lands

    def aborted(self):
        return self.abort_at is not None and self.now >= self.abort_at

    def on_steal(self):
        self.successes += 1

    def on_reset(self):
        self.resets += 1

    def advance(self):
        BankWorld.advance(self)
        if self.restock_at is not None and self.now >= self.restock_at:
            self.stalls = [Stall(self, thieving.STALL_TILE)]
            self.restock_at = None
        outcome = self.pending_steal
        self.pending_steal = None
        if outcome == 'success':
            self.pack.append(Item(1891, 'Cake', 1))
            self.free_slots -= 1
        elif outcome == 'caught':
            self.combat = True
        elif outcome in ['lockout', 'refused']:
            text = thieving.LOCKOUT_TEXT if outcome == 'lockout' else thieving.ATTEMPT_TEXT
            for callback in self.listeners:
                callback(FakeModule(text=text.upper()))

    def run(self, task):
        for guard in range(500):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.waits.append(wait)
            self.now += 500
            self.advance()
        assert False, 'thieving exceeded its simulated update budget'

    def steal(self, fill_to=2, **kwargs):
        return self.run(thieving.steal_cakes(self.aborted, self.statuses.append, self.logs.append,
                                            fill_to=fill_to, on_steal=self.on_steal,
                                            on_reset=self.on_reset, **kwargs))


def test_cakes_steal_until_target_inventory_count_arrives():
    with ThievingWorld() as world:
        assert world.steal() == 'stocked'
        assert world.count('Cake') == 2 and world.steals == 2
        assert world.successes == 2 and world.resets == 0
        assert world.statuses == ['stealing cake (0/2)', 'stealing cake (1/2)']


def test_cakes_full_pack_and_existing_food_skip_stealing():
    for full in [True, False]:
        with ThievingWorld() as world:
            if full:
                world.free_slots = 0
            else:
                world.pack = [Item(1891, 'Cake', 2)]
            assert world.steal() == 'stocked'
            assert world.steals == 0 and world.waits == []


def test_cakes_without_fill_target_uses_remaining_slots():
    with ThievingWorld() as world:
        world.free_slots = 2
        assert world.steal(fill_to=None) == 'stocked'
        assert world.steals == 2
        assert world.statuses[0] == 'stealing cake (26/28 slots)'


def test_cakes_abort_and_food_interrupt_skip_clicking():
    for eating in [True, False]:
        with ThievingWorld() as world:
            if not eating:
                world.abort_at = 0
            assert world.steal(should_eat=lambda: eating) == 'aborted'
            assert world.steals == 0 and world.waits == []


def test_cakes_combat_before_or_after_click_stops_stealing():
    for already in [True, False]:
        with ThievingWorld() as world:
            world.combat = already
            world.outcomes = ['caught']
            assert world.steal() == 'combat'
            assert world.steals == (0 if already else 1)
            assert world.successes == 0


def test_cakes_walks_to_claim_before_stealing():
    with ThievingWorld() as world:
        world.position = Tile(2650, 3300)
        assert world.steal() == 'stocked'
        assert world.walks[0][0] == thieving.STAND
        assert world.walks[0][1]['radius'] == 0
        assert '  walking to stand' in world.logs


def test_cakes_failed_claim_never_steals_from_wrong_side():
    with ThievingWorld() as world:
        world.position = Tile(2650, 3300)
        world.walk_lands = False
        world.abort_at = 2000
        assert world.steal() == 'aborted'
        assert world.steals == 0
        assert any(['claim fell short at (2650,3300)' in line for line in world.logs])


def test_cakes_disappearing_position_after_claim_is_retried():
    with ThievingWorld() as world:
        world.position = Tile(2650, 3300)
        world.events = [('position', None)]
        world.walk_lands = False
        world.abort_at = 1000
        assert world.steal() == 'aborted'
        assert 'claim fell short; not stealing from the market side' in world.logs
        assert world.steals == 0


def test_cakes_empty_stall_waits_for_restock():
    with ThievingWorld() as world:
        world.stalls = []
        world.restock_at = 1500
        assert world.steal() == 'stocked'
        assert world.now >= 2500
        assert world.logs[0] == 'stall emptied; waiting for the restock'


def test_cakes_abort_interrupts_wait_for_restock():
    with ThievingWorld() as world:
        world.stalls = []
        world.abort_at = 1000
        assert world.steal() == 'aborted'
        assert world.now == 1000 and world.steals == 0


def test_cakes_filters_same_named_stalls_outside_market_spawn():
    with ThievingWorld() as world:
        world.stalls = [Stall(world, Tile(2675, 3310))]
        world.abort_at = 1000
        assert world.steal() == 'aborted'
        assert world.steals == 0


def test_cakes_external_combat_lockout_expires_before_click():
    with ThievingWorld() as world:
        assert world.steal(locked_out_until=lambda: 4) == 'stocked'
        assert world.now == 3000
        assert world.statuses[0] == 'waiting out the post-combat steal lockout'


def test_cakes_server_lockout_waits_ten_ticks_then_retries():
    with ThievingWorld() as world:
        world.outcomes = ['lockout', 'success']
        assert world.steal(fill_to=1) == 'stocked'
        assert world.steals == 2 and world.successes == 1
        assert world.now >= 6000 and world.resets == 0


def test_cakes_repeated_rejected_clicks_swap_stands():
    with ThievingWorld() as world:
        world.outcomes = ['reject', 'reject', 'reject', 'success']
        assert world.steal(fill_to=1) == 'stocked'
        assert world.resets == 1 and world.steals == 4
        assert world.walks[0][0] == thieving.STAND_ALT
        assert 'watched; swapping stands' in world.statuses


def test_cakes_refused_and_silent_attempts_also_trigger_reset():
    for outcome in ['refused', 'silent']:
        with ThievingWorld() as world:
            world.outcomes = [outcome, outcome, outcome]
            assert world.steal(fill_to=1) == 'stocked'
            assert world.resets == 1 and world.steals == 4
            assert world.count('Cake') == 1


def test_cakes_success_resets_consecutive_refusal_counter():
    with ThievingWorld() as world:
        world.outcomes = ['reject', 'reject', 'success', 'reject', 'reject', 'success']
        assert world.steal() == 'stocked'
        assert world.resets == 0 and world.successes == 2


def test_cakes_repeated_refusals_swap_back_to_original_stand():
    with ThievingWorld() as world:
        world.outcomes = ['reject'] * 6
        assert world.steal(fill_to=1) == 'stocked'
        assert world.resets == 2
        assert [row[0] for row in world.walks] == [thieving.STAND_ALT, thieving.STAND]


def test_cakes_no_progress_returns_after_deadline():
    with ThievingWorld() as world:
        world.stalls = []
        assert world.steal() == 'no-progress'
        assert world.now >= thieving.STEAL_DEADLINE_MS and world.steals == 0


def test_cakes_listener_is_registered_once_and_ignores_unrelated_messages():
    with ThievingWorld() as world:
        assert world.steal(fill_to=1) == 'stocked'
        assert world.steal(fill_to=1) == 'stocked'
        assert len(world.listeners) == 1
        world.listeners[0](FakeModule(text=None))
        assert not thieving._seen['attempt'] and not thieving._seen['lockout']


def test_thieving_withdraw_tops_up_using_fixed_and_custom_amounts():
    for target in [4, 8, 13, 20]:
        with ThievingWorld() as world:
            world.pack = [Item(1891, 'Cake', 3)]
            assert world.run(thieving.withdraw_to('Cake', target)) == target - 3
            assert world.count('Cake') == target
            assert world.run(thieving.withdraw_to('Cake', target)) == 0


def test_thieving_withdraw_falls_back_when_count_dialog_is_unavailable():
    with ThievingWorld() as world:
        world.stock[0]._ops = ['Withdraw 1', 'Withdraw 5', 'Withdraw 10']
        assert world.run(thieving.withdraw_to('Cake', 17)) == 17
        assert world.answers == []
        assert world.clicks == [(1891, 'Withdraw 10'), (1891, 'Withdraw 5'),
                                (1891, 'Withdraw 1'), (1891, 'Withdraw 1')]


def test_thieving_withdraw_stops_at_full_pack_or_missing_stock():
    for full in [True, False]:
        with ThievingWorld() as world:
            world.free_slots = 0 if full else 28
            world.stock = []
            assert world.run(thieving.withdraw_to('Cake', 5)) == 0
            assert world.clicks == []


def test_thieving_withdraw_counts_only_delivered_food():
    with ThievingWorld() as world:
        world.stock[0].count = 3
        assert world.run(thieving.withdraw_to('Cake', 8)) == 3
        assert world.count('Cake') == 3


def test_thieving_withdraw_can_count_multiple_food_variants():
    with ThievingWorld() as world:
        world.pack = [Item(1893, '2/3 cake', 2)]
        assert world.run(thieving.withdraw_to('Cake', 7, lambda: thieving.carried_cakes())) == 5
        assert thieving.carried_cakes() == 7


def test_thieving_close_bank_confirms_food_and_reports_failed_close():
    for closes in [True, False]:
        with ThievingWorld() as world:
            world.pack = [Item(1891, 'Cake', 5)]
            world.close_responds = closes
            assert world.run(thieving.close_bank_and_confirm_count(5, lambda: world.count('Cake'))) == closes
            assert world.clicks == ['close']


def test_thieving_close_bank_waits_for_delayed_pack_update():
    with ThievingWorld() as world:
        world.events = [('pack', []), ('pack', []), ('pack', [Item(1891, 'Cake', 5)])]
        assert world.run(thieving.close_bank_and_confirm_count(5, lambda: world.count('Cake')))
        assert world.now == 1500


def test_thieving_closed_bank_without_food_times_out():
    with ThievingWorld() as world:
        assert world.run(thieving.close_bank_and_confirm_count(5, lambda: world.count('Cake'))) is False
        assert not world.open and world.now >= 3000

"""Bank route selection, startup purges and periodic trips use acknowledged transfers."""

import rs2004.bank as vault
from rs2004 import execution
from rs2004.geometry import Tile
from helpers import FakeModule
from test_bank_workflows import OpeningWorld, AccessTarget, Item


class TripWorld(OpeningWorld):
    def __init__(self):
        OpeningWorld.__init__(self)
        self.position = Tile(3000, 3000)
        self.nearest = None
        self.locked = None
        self.walk_ok = True
        self.reveal_booth = True
        self.logs = []
        self.patches = []
        self.statuses = []

    def patch(self, name, value):
        self.patches.append((name, getattr(vault, name)))
        setattr(vault, name, value)

    def __enter__(self):
        OpeningWorld.__enter__(self)
        self.patch('game', FakeModule(tile=lambda: self.position, in_combat=lambda: False))
        self.patch('traversal', FakeModule(walk_resilient=self.walk))
        self.patch('nearest_bank', lambda tile: self.nearest)
        self.patch('nearest_bank_reachable', lambda *args: self.nearest)
        self.patch('locked_bank_at', lambda tile: self.locked)
        self.patch('walk_opening', self.walk_obstacles)
        return self

    def __exit__(self, *args):
        for name, value in reversed(self.patches):
            setattr(vault, name, value)
        OpeningWorld.__exit__(self, *args)

    def tick(self):
        return self.now // 500

    def walk(self, tile, *args, **kwargs):
        self.walks.append(tile)
        yield execution.Ticks(1)
        if self.walk_ok:
            self.position = tile
            if self.reveal_booth:
                self.objects = [AccessTarget(self, distance=1)]
        return self.walk_ok

    def walk_obstacles(self, tile, radius, obstacles, log):
        assert obstacles == ['door']
        result = yield from self.walk(tile)
        return result

    def bank_place(self, x=3001):
        return {'name': 'Test bank', 'tile': {'x': x, 'z': 3000, 'level': 0}}


def test_bank_trip_prefers_nearby_booth_and_local_bank_over_distant_preset():
    with TripWorld() as world:
        world.objects = [AccessTarget(world, distance=1)]
        assert world.run(vault.banking.open(Tile(3200, 3000), log=world.logs.append))
        assert world.walks == []
    with TripWorld() as world:
        world.nearest = world.bank_place()
        assert world.run(vault.banking.open(Tile(3200, 3000), log=world.logs.append))
        assert world.walks == [Tile(3001, 3000)]


def test_bank_trip_local_and_preset_failed_walks_do_not_open():
    for local in [True, False]:
        with TripWorld() as world:
            world.nearest = world.bank_place() if local else None
            world.walk_ok = False
            assert world.run(vault.banking.open(Tile(3200, 3000), log=world.logs.append)) is False
            assert world.interactions == []


def test_bank_trip_locked_preset_and_locked_scene_booth_are_not_used():
    with TripWorld() as world:
        world.locked = world.bank_place()
        world.objects = [AccessTarget(world)]
        assert world.run(vault.banking.open(Tile(3200, 3000), log=world.logs.append)) is False
        assert world.interactions == []
        assert any(['skipping' in line for line in world.logs])


def test_bank_trip_preset_uses_obstacle_walk_and_known_object_access():
    with TripWorld() as world:
        world.nearest = world.bank_place(3200)
        world.nearest['access'] = {'name': 'Bank booth', 'op': 'Use-quickly'}
        assert world.run(vault.banking.open(Tile(3200, 3000), obstacles=[' Door '], log=world.logs.append))
        assert world.walks == [Tile(3200, 3000)] and world.open


def test_bank_trip_no_preset_uses_destination_or_reachable_bank():
    for explicit in [True, False]:
        with TripWorld() as world:
            place = world.bank_place(3200)
            if not explicit:
                world.nearest = place
            assert world.run(vault.banking.open(destination=place if explicit else None, log=world.logs.append))
            assert world.walks == [Tile(3200, 3000)]


def test_bank_trip_fallback_failed_walk_and_distant_scene_booth():
    with TripWorld() as world:
        world.walk_ok = False
        assert world.run(vault.banking.open(destination=world.bank_place(3200), log=world.logs.append)) is False
        assert not world.open
    with TripWorld() as world:
        world.objects = [AccessTarget(world, distance=20)]
        assert world.run(vault.banking.open(prefer_nearby=False, log=world.logs.append))
        assert world.walks == []


def test_start_purge_preserves_keep_items_and_confirms_junk_deposit():
    with TripWorld() as world:
        world.open = True
        world.pack = [Item(1, 'Knife', 1, 0, ['Deposit All']), Item(2, 'Junk', 2, 1, ['Deposit All'])]
        assert world.run(vault.purge_pack_at_bank(['Knife'], log=world.logs.append))
        assert [i.name for i in world.pack] == ['Knife'] and not world.open
        assert 'cleared' in world.logs[-1]
        assert world.run(vault.purge_pack_at_bank(['Knife']))


def test_start_purge_failed_open_preserves_inventory():
    with TripWorld() as world:
        world.pack = [Item(2, 'Junk', 1, 0, ['Deposit All'])]
        world.walk_ok = False
        assert world.run(vault.purge_pack_at_bank([], destination=world.bank_place(3200), log=world.logs.append)) is False
        assert world.pack[0].name == 'Junk'


def test_start_purge_rejected_deposit_does_not_claim_clear_pack():
    with TripWorld() as world:
        world.open = True
        world.pack = [Item(2, 'Junk', 1, 0, [])]
        assert world.run(vault.purge_pack_at_bank([], log=world.logs.append)) is False
        assert 'still holding' in world.logs[-1]


def test_bank_trip_callback_runs_after_deposit_and_returns_to_anchor():
    with TripWorld() as world:
        world.open = True
        world.pack = [Item(2, 'Junk', 1, 0, ['Deposit All'])]
        calls = []
        def after():
            assert world.pack == []
            calls.append('deposited')
            yield execution.Ticks(1)
        assert world.run(vault.banking.bank_nearest(lambda name: True, False, return_to=Tile(3010, 3010), after_deposit=after))
        assert calls == ['deposited'] and world.walks == [Tile(3010, 3010)]


def test_bank_pacing_readiness_and_coin_withdrawal_boundaries():
    with TripWorld() as world:
        assert world.run(vault.wait_bank_ready()) is False
        assert world.run(vault.withdraw_coins(10, 0, 10)) is False
        assert world.run(vault.withdraw_coins(10, 10, 0))
        world.open = True
        assert world.run(vault.wait_bank_ready(world.logs.append))
        assert world.run(vault.withdraw_coins(10, 0, 0, log=world.logs.append)) is False
        world.stock = [Item(995, 'Coins', 100)]
        assert world.run(vault.withdraw_coins(13, 0, 100, log=world.logs.append))
        assert world.count('Coins') == 13
        world.accept_click = False
        assert world.run(vault.withdraw_coins(20, 13, 100)) is False
        assert world.bank.normal_backpack_snapshot() is None


def test_periodic_bank_success_and_failed_trip_backoff():
    for succeeds in [True, False]:
        with TripWorld() as world:
            world.open = succeeds
            world.walk_ok = succeeds
            task = vault.PeriodicBank(strategy=lambda: 'items', items_threshold=lambda: 1,
                minutes_threshold=lambda: 1, count_loot=lambda: 1, deposit=lambda name: True,
                destination=lambda: world.bank_place(3200), set_status=world.statuses.append, log=world.logs.append)
            assert task.validate()
            world.run(task.execute())
            assert world.statuses == ['periodic bank run']
            assert task.validate() == succeeds
            if not succeeds:
                assert task.suppress_until == world.now - 500 + vault.FAILURE_BACKOFF_MS

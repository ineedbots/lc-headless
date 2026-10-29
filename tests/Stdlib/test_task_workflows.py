"""Shared tasks acquire supplies, recover after death, and return to camp."""

import rs2004.catalogs.tasks as tasks
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule, raises
from test_bank_workflows import Item
from test_dialogue_workflows import DialogueWorld


class Spawn:
    name = 'Egg'
    id = 1944

    def __init__(self, world):
        self.world = world

    def distance(self):
        return 1

    def interact(self, op):
        assert op == 'Take'
        self.world.takes += 1
        if self.world.deliver:
            self.world.pending_item = Item(self.id, self.name, 1)
        return self.world.deliver


class TaskWorld(DialogueWorld):
    def __init__(self):
        DialogueWorld.__init__(self)
        self.position = Tile(3000, 3000)
        self.pack = []
        self.spawns = [Spawn(self)]
        self.walks = []
        self.can_walk = True
        self.opens = True
        self.buy_count = None
        self.shop_calls = []
        self.takes = 0
        self.deliver = True
        self.pending_item = None
        self.handlers = {}
        self.placed = True
        self.place_at = None
        self.deaths = 0
        self.recoveries = 0

    def __enter__(self):
        DialogueWorld.__enter__(self)
        replacements = {
            '_core': self, 'inventory': self,
            'local_tile': lambda: self.position,
            'ground_items': FakeModule(query=lambda: EntityQuery(self.scene, lambda item: True)),
            'traversal': FakeModule(walk_resilient=self.resilient, walk_to=self.direct),
            'shop': FakeModule(open=self.open_shop, buy=self.buy, close=self.close_shop),
        }
        self.task_saved = {}
        for name, value in replacements.items():
            self.task_saved[name] = getattr(tasks, name)
            setattr(tasks, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.task_saved.items():
            setattr(tasks, name, value)
        DialogueWorld.__exit__(self, *args)

    def count(self, name):
        return sum([item.count for item in self.pack if item.name == name])

    def scene(self, ids, names, radius, layer):
        return [item for item in self.spawns if names is None or item.name in names]

    def walk(self, kind, tile, kwargs):
        self.walks.append((kind, tile, kwargs))
        if 'log' in kwargs:
            kwargs['log']('walking')
        yield execution.Ticks(1)
        if self.can_walk:
            self.position = tile
        return self.can_walk

    def resilient(self, tile, **kwargs):
        result = yield from self.walk('resilient', tile, kwargs)
        return result

    def direct(self, tile, **kwargs):
        result = yield from self.walk('direct', tile, kwargs)
        return result

    def open_shop(self, keeper):
        self.shop_calls.append(('open', keeper))
        yield execution.Ticks(1)
        return self.opens

    def buy(self, name, count):
        self.shop_calls.append(('buy', name, count))
        bought = count if self.buy_count is None else self.buy_count
        if bought > 0:
            self.pending_item = Item(1, name, bought)
        yield execution.Ticks(1)
        return bought

    def close_shop(self):
        self.shop_calls.append(('close',))
        yield execution.Ticks(1)

    def on(self, name, callback):
        self.handlers[name] = callback

    def log(self, text):
        self.logs.append(text)

    def is_placed(self):
        return self.placed

    def died(self):
        self.deaths += 1

    def recovered(self):
        self.recoveries += 1

    def advance(self):
        DialogueWorld.advance(self)
        if self.pending_item is not None:
            self.pack.append(self.pending_item)
            self.pending_item = None
        if self.place_at is not None and self.now >= self.place_at:
            self.placed = True

    def acquire(self, needs):
        return tasks.AcquireTask(self, needs)

    def recovery(self, **kwargs):
        return tasks.DeathRecovery(self, Tile(3000, 3000), on_death=self.died,
                                   on_recovered=self.recovered, **kwargs)


def shop_need(count=5):
    return tasks.ItemNeed('Bread', count, ('shop', 'Baker', Tile(3100, 3100)))


def ground_need():
    return tasks.ItemNeed('Egg', 1, ('ground', Tile(3100, 3100)))


def test_acquire_shop_buys_only_missing_quantity_and_closes():
    with TaskWorld() as world:
        world.pack = [Item(1, 'Bread', 2)]
        task = world.acquire([shop_need()])
        assert task.validate()
        world.run(task.execute())
        assert world.shop_calls == [('open', 'Baker'), ('buy', 'Bread', 3), ('close',)]
        assert world.count('Bread') == 5 and not task.validate()
        assert world.walks[0][2]['radius'] == 4


def test_acquire_complete_needs_do_nothing():
    with TaskWorld() as world:
        world.pack = [Item(1, 'Bread', 5)]
        task = world.acquire([shop_need()])
        assert not task.validate()
        world.run(task.execute())
        assert world.waits == [] and world.shop_calls == []


def test_acquire_works_on_first_unmet_need_only():
    with TaskWorld() as world:
        task = world.acquire([ground_need(), shop_need()])
        world.run(task.execute())
        assert world.count('Egg') == 1 and world.shop_calls == []
        assert task.validate()
        world.run(task.execute())
        assert world.count('Bread') == 5 and not task.validate()


def test_acquire_failed_shop_walk_does_not_open_shop():
    with TaskWorld() as world:
        world.can_walk = False
        world.run(world.acquire([shop_need()]).execute())
        assert world.shop_calls == [] and world.count('Bread') == 0
        assert 'could not reach Baker' in world.logs[-1]


def test_acquire_failed_shop_open_does_not_buy_or_close():
    with TaskWorld() as world:
        world.opens = False
        world.run(world.acquire([shop_need()]).execute())
        assert world.shop_calls == [('open', 'Baker')]


def test_acquire_empty_shop_waits_before_closing_and_retrying():
    with TaskWorld() as world:
        world.buy_count = 0
        task = world.acquire([shop_need()])
        world.run(task.execute())
        assert any([isinstance(wait, execution.Ticks) and wait.count == 5 for wait in world.waits])
        assert world.shop_calls[-1] == ('close',) and task.validate()
        assert world.logs[-1] == 'bought no Bread: out of stock or coins'


def test_acquire_partial_shop_purchase_remains_needed():
    with TaskWorld() as world:
        world.buy_count = 2
        task = world.acquire([shop_need()])
        world.run(task.execute())
        assert world.count('Bread') == 2 and task.validate()
        assert world.shop_calls[-1] == ('close',)


def test_acquire_ground_waits_for_item_to_arrive():
    with TaskWorld() as world:
        task = world.acquire([ground_need()])
        world.run(task.execute())
        assert world.count('Egg') == 1 and world.takes == 1
        assert not task.validate() and world.now == 1000
        assert world.walks[0][2]['radius'] == 3


def test_acquire_missing_spawn_waits_without_clicking():
    with TaskWorld() as world:
        world.spawns = []
        task = world.acquire([ground_need()])
        world.run(task.execute())
        assert world.takes == 0 and task.validate()
        assert world.waits[-1].count == 5


def test_acquire_failed_ground_walk_does_not_take():
    with TaskWorld() as world:
        world.can_walk = False
        world.run(world.acquire([ground_need()]).execute())
        assert world.takes == 0
        assert 'could not reach the spawn of Egg' in world.logs[-1]


def test_acquire_rejected_take_times_out_and_remains_needed():
    with TaskWorld() as world:
        world.deliver = False
        task = world.acquire([ground_need()])
        world.run(task.execute())
        assert world.takes == 1 and world.count('Egg') == 0
        assert task.validate() and world.now == 5500


def test_acquire_unsupported_sources_fail_explicitly():
    with TaskWorld() as world:
        for source in ['gather', 'make']:
            task = world.acquire([tasks.ItemNeed('Logs', 1, (source,))])
            assert source in raises(NotImplementedError, lambda: world.run(task.execute()))


def test_continue_dialog_invokes_callback_and_waits_for_next_page():
    with TaskWorld() as world:
        world.pages = [('continue', ['Hello'])]
        task = tasks.ContinueDialog(world.died)
        assert task.validate()
        world.run(task.execute())
        assert world.deaths == 1 and world.clicks == ['continue']
        assert not task.validate()


def test_continue_dialog_without_callback_handles_rejected_click():
    with TaskWorld() as world:
        world.pages = [('continue', ['Hello'])]
        world.accept_click = False
        task = tasks.ContinueDialog()
        world.run(task.execute())
        assert task.validate() and world.waits == []


def test_death_recovery_activates_on_event_and_recovers_once_at_camp():
    with TaskWorld() as world:
        task = world.recovery()
        assert not task.validate()
        world.position = Tile(3200, 3200)
        world.handlers['death']()
        assert task.validate() and world.deaths == 1
        world.run(task.execute())
        assert world.walks[0][:2] == ('resilient', Tile(3000, 3000))
        assert '  walking' in world.logs
        assert not task.validate() and world.recoveries == 1
        assert not task.validate() and world.recoveries == 1


def test_death_recovery_needs_supplies_even_when_already_at_camp():
    with TaskWorld() as world:
        task = world.recovery(needs=[ground_need()])
        world.handlers['death']()
        assert task.validate()
        world.run(task.execute())
        assert world.count('Egg') == 1
        assert len(world.walks) == 1 and task.validate()
        world.run(task.execute())
        assert not task.validate() and world.recoveries == 1


def test_death_recovery_waits_for_placement_before_walking():
    with TaskWorld() as world:
        world.placed = False
        world.place_at = 1500
        task = world.recovery()
        world.run(task.execute())
        assert world.now == 2500 and world.placed
        assert world.waits[3].count == 3


def test_death_recovery_custom_plain_walk_skips_default_walker():
    with TaskWorld() as world:
        task = world.recovery(walk_back=world.recovered)
        world.run(task.execute())
        assert world.recoveries == 1 and world.walks == []


def test_death_recovery_custom_generator_is_driven():
    with TaskWorld() as world:
        task = world.recovery(walk_back=lambda: world.resilient(Tile(3200, 3200)))
        world.run(task.execute())
        assert world.position == Tile(3200, 3200) and len(world.walks) == 1


def test_death_recovery_other_floor_is_not_recovered():
    with TaskWorld() as world:
        task = world.recovery()
        world.position = Tile(3000, 3000, 1)
        world.handlers['death']()
        assert task.validate() and world.recoveries == 0


def test_death_recovery_without_callbacks_clears_at_radius_boundary():
    with TaskWorld() as world:
        task = tasks.DeathRecovery(world, Tile(3000, 3000), radius=6)
        world.position = Tile(3006, 3006)
        world.handlers['death']()
        assert not task.validate() and not task.died


def test_return_to_anchor_obeys_leash_slack_and_suppression():
    with TaskWorld() as world:
        host = tasks.AnchorHost(Tile(3000, 3000), 10)
        task = tasks.create_return_to_anchor_task(host, slack=6)
        world.position = Tile(3016, 3000)
        assert not task.validate()
        world.position = Tile(3017, 3000)
        assert task.validate()
        suppressed = tasks.create_return_to_anchor_task(host, suppress=lambda: True)
        assert not suppressed.validate()


def test_return_to_anchor_short_walk_uses_direct_traversal():
    with TaskWorld() as world:
        world.position = Tile(3020, 3000)
        host = tasks.AnchorHost(Tile(3000, 3000), 10)
        task = tasks.create_return_to_anchor_task(host, arrive_radius=4, timeout_ms=1234, long_range_tiles=30)
        world.run(task.execute())
        assert world.walks == [('direct', host.anchor, {'radius': 4, 'timeout_ms': 1234})]


def test_return_to_anchor_long_walk_uses_resilient_traversal_and_log():
    with TaskWorld() as world:
        world.position = Tile(3100, 3000)
        host = tasks.AnchorHost(Tile(3000, 3000), 10, world.log)
        task = tasks.create_return_to_anchor_task(host, long_range_tiles=30)
        world.run(task.execute())
        assert world.walks[0][0] == 'resilient' and world.logs == ['walking']


def test_return_to_anchor_already_arrived_does_not_walk():
    with TaskWorld() as world:
        host = tasks.AnchorHost(Tile(3000, 3000), 10)
        world.run(tasks.create_return_to_anchor_task(host).execute())
        assert world.waits == [] and world.walks == []


def test_return_to_anchor_long_walk_without_logger_still_completes():
    with TaskWorld() as world:
        world.position = Tile(3100, 3000)
        host = tasks.AnchorHost(Tile(3000, 3000), 10)
        world.run(tasks.create_return_to_anchor_task(host, long_range_tiles=30).execute())
        assert world.position == host.anchor and world.logs == []


def test_sustain_no_hook_and_plain_hook_reset_running_flag():
    upkeep = tasks._Sustain()
    with TaskWorld() as world:
        world.run(upkeep.run())
        assert not upkeep.running and world.waits == []
        upkeep.set(world.recovered)
        world.run(upkeep.run())
        assert world.recoveries == 1 and not upkeep.running


def test_sustain_generator_blocks_recursive_upkeep_and_resumes():
    upkeep = tasks._Sustain()
    calls = []

    def hook():
        calls.append('start')
        assert upkeep.running
        yield from upkeep.run()
        yield execution.Ticks(1)
        calls.append('end')

    with TaskWorld() as world:
        upkeep.set(hook)
        world.run(upkeep.run())
        world.run(upkeep.run())
        assert calls == ['start', 'end', 'start', 'end']
        assert len(world.waits) == 2 and not upkeep.running


def test_sustain_exception_clears_guard_so_next_hook_can_run():
    upkeep = tasks._Sustain()

    def failed_hook():
        yield execution.Ticks(1)
        raise ValueError('upkeep failed')

    with TaskWorld() as world:
        upkeep.set(failed_hook)
        assert raises(ValueError, lambda: world.run(upkeep.run())) == 'upkeep failed'
        assert not upkeep.running
        upkeep.set(world.recovered)
        world.run(upkeep.run())
        assert world.recoveries == 1 and not upkeep.running

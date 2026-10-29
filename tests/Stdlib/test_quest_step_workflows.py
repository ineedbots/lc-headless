"""Quest execution verifies inventory and level changes after delayed server updates."""

import rs2004.quests.exec.steps as steps
import rs2004.quests.exec.legs as legs
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from rs2004.quests.engine.types import quest_step
from helpers import FakeModule
from test_hunting_supply import SupplyWorld
from test_bank_workflows import Item


class QuestItem(Item):
    def __init__(self, world, id, name):
        Item.__init__(self, id, name, 1)
        self.world = world

    def use_on(self, target):
        self.world.uses.append((self.id, target.id))
        if self.world.recipe is None or self.world.recipe == (self.id, target.id):
            self.world.queue_gain()
        return self.world.accept_actions


class SceneObject:
    def __init__(self, world, id, name, op, distance=1):
        self.world = world
        self.id = id
        self.name = name
        self.op = op
        self.dist = distance

    def tile(self):
        return Tile(3001, 3000)

    def distance(self):
        return self.dist

    def actions(self):
        return [self.op]

    def interact(self, op):
        assert op == self.op
        self.world.actions.append((self.id, op))
        self.world.queue_gain()
        return self.world.accept_actions


class QuestWorld(SupplyWorld):
    def __init__(self):
        SupplyWorld.__init__(self)
        self.can_walk = True
        self.bank_opens = True
        self.shop_opens = True
        self.accept_actions = True
        self.gain = None
        self.pending_gain = None
        self.arrive_level = None
        self.pending_level = None
        self.recipe = None
        self.uses = []
        self.actions = []
        self.walks = []
        self.bank_stands = []
        self.shop_calls = []
        self.ground = []
        self.locs = []
        self.npcs = []
        self.appears_after_walk = None
        self.bank_rows = []
        self.paths = {}
        self.path_requests = []

    def __enter__(self):
        SupplyWorld.__enter__(self)
        replacements = {
            'inventory': self,
            'game': FakeModule(tile=lambda: self.position),
            'traversal': FakeModule(walk_resilient=self.walk),
            'bank': self.bank,
            'banking': FakeModule(open=self.open_bank),
            'modals': FakeModule(close=self.bank.close),
            'ground_items': FakeModule(query=lambda: self.query(self.ground)),
            'locs': FakeModule(query=lambda: self.query(self.locs)),
            'npcs': FakeModule(query=lambda: self.query(self.npcs)),
            'nearest_banks': lambda tile: self.bank_rows,
            'navigator': FakeModule(find_path=self.find_path),
            'shop': FakeModule(open=self.open_shop, buy=self.buy, close=self.close_shop),
        }
        self.step_saved = {}
        for name, value in replacements.items():
            self.step_saved[name] = getattr(steps, name)
            setattr(steps, name, value)
        self.leg_saved = (legs.inventory, legs.game, legs.traversal, legs.locs)
        legs.inventory = self
        legs.game = steps.game
        legs.traversal = steps.traversal
        legs.locs = steps.locs
        return self

    def __exit__(self, *args):
        legs.inventory, legs.game, legs.traversal, legs.locs = self.leg_saved
        for name, value in self.step_saved.items():
            setattr(steps, name, value)
        SupplyWorld.__exit__(self, *args)

    def contains(self, name):
        return self.count(name) > 0

    def query(self, scene):
        def supply(ids, names, radius, layer):
            return [obj for obj in scene if (ids is None or obj.id in ids)
                    and (names is None or obj.name in names)]
        return EntityQuery(supply, lambda obj: True)

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        if self.can_walk:
            self.position = tile
            if self.appears_after_walk is not None:
                self.ground.append(self.appears_after_walk)
        return self.can_walk

    def open_bank(self, **kwargs):
        self.bank_stands.append(kwargs['stand'])
        yield execution.Ticks(1)
        self.open = self.bank_opens
        return self.bank_opens

    def open_shop(self, npc):
        self.shop_calls.append(('open', npc))
        yield execution.Ticks(1)
        return self.shop_opens

    def buy(self, name, qty):
        self.shop_calls.append(('buy', name, qty))
        self.queue_gain()
        yield execution.Ticks(1)
        return self.accept_actions

    def close_shop(self):
        self.shop_calls.append(('close',))
        yield execution.Ticks(1)

    def find_path(self, start, dest):
        self.path_requests.append(dest)
        cost = self.paths.get(dest.x)
        return FakeModule(ok=cost is not None, cost=cost)

    def queue_gain(self):
        if self.accept_actions:
            self.pending_gain = self.gain
            self.pending_level = self.arrive_level

    def advance(self):
        SupplyWorld.advance(self)
        if self.respond and self.pending_gain is not None:
            self.pack.append(self.pending_gain)
            self.pending_gain = None
        if self.respond and self.pending_level is not None:
            self.position = Tile(self.position.x, self.position.z, self.pending_level)
            self.pending_level = None

    def execute(self, kind, **fields):
        return self.run(steps.execute_step(quest_step(kind, **fields), [], self.logs.append))


def test_ground_gather_requeries_after_walking_and_requires_item_arrival():
    with QuestWorld() as world:
        world.position = Tile(2900, 2900)
        world.appears_after_walk = SceneObject(world, 1944, 'Egg', 'Take')
        world.gain = Item(1944, 'Egg', 1)
        assert world.execute('grab_ground', item='Egg', anchor=Tile(3000, 3000))
        assert world.actions == [(1944, 'Take')]
        assert world.count('Egg') == 1 and len(world.walks) == 1


def test_ground_gather_does_not_report_success_for_arrival_at_empty_spawn():
    with QuestWorld() as world:
        assert world.execute('grab_ground', item='Egg', anchor=Tile(3000, 3000), wait_if_missing=True) is False
        assert world.actions == [] and world.count('Egg') == 0
        assert world.waits[-1].count == 2


def test_ground_take_rejected_or_unacknowledged_is_failure():
    for rejected in [True, False]:
        with QuestWorld() as world:
            world.ground = [SceneObject(world, 1944, 'Egg', 'Take')]
            world.accept_actions = not rejected
            assert world.execute('grab_ground', item='Egg', anchor=Tile(3000, 3000)) is False
            assert world.count('Egg') == 0


def test_pick_loc_waits_for_product_and_rejects_no_inventory_change():
    for arrives in [True, False]:
        with QuestWorld() as world:
            world.locs = [SceneObject(world, 100, 'Wheat', 'Pick')]
            world.gain = Item(1947, 'Grain', 1) if arrives else None
            assert world.execute('pick_loc', item='Grain', loc='Wheat', op='Pick', anchor=Tile(3000, 3000)) == arrives
            assert world.actions == [(100, 'Pick')]


def test_interact_loc_checks_expected_item_instead_of_only_click_success():
    for arrives in [True, False]:
        with QuestWorld() as world:
            world.locs = [SceneObject(world, 100, 'Chest', 'Search')]
            world.gain = Item(777, 'Key', 1) if arrives else None
            assert world.execute('interact_loc', loc='Chest', op='Search', expect_item='Key') == arrives


def test_item_use_on_item_waits_for_new_product_even_if_one_is_already_held():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A'), QuestItem(world, 2, 'B'), Item(3, 'Product', 1)]
        assert world.execute('use_on', target_kind='item', item='A', target='B', product='Product') is False
        world.gain = Item(3, 'Product', 1)
        assert world.execute('use_on', target_kind='item', item='A', target='B', product='Product')
        assert world.count('Product') == 2


def test_item_use_requires_both_named_items_before_clicking():
    for missing_source in [True, False]:
        with QuestWorld() as world:
            world.pack = [QuestItem(world, 2, 'B')] if missing_source else [QuestItem(world, 1, 'A')]
            assert world.execute('use_on', target_kind='item', item='A', target='B') is False
            assert world.uses == []
            assert 'in the pack' in world.logs[-1]


def test_item_use_on_loc_or_npc_selects_target_and_verifies_product():
    for kind in ['loc', 'npc']:
        with QuestWorld() as world:
            world.pack = [QuestItem(world, 1, 'A')]
            target = SceneObject(world, 100, 'Target', 'Talk-to')
            world.locs = [target] if kind == 'loc' else []
            world.npcs = [target] if kind == 'npc' else []
            world.gain = Item(3, 'Product', 1)
            assert world.execute('use_on', target_kind=kind, item='A', target='Target',
                                  anchor=Tile(3000, 3000), product='Product')
            assert world.uses == [(1, 100)] and world.count('Product') == 1


def test_use_on_missing_world_target_does_not_click_item():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A')]
        assert world.execute('use_on', target_kind='loc', item='A', target='Target', anchor=Tile(3000, 3000)) is False
        assert world.uses == [] and 'near the anchor' in world.logs[-1]


def test_ensure_at_requires_correct_floor_even_at_same_coordinates():
    with QuestWorld() as world:
        world.position = Tile(3000, 3000)
        assert world.run(steps.ensure_at(Tile(3000, 3000, 1), 4, world.logs.append))
        assert len(world.walks) == 1 and world.position.level == 1
        assert world.run(steps.ensure_at(Tile(3000, 3000, 1), 4, world.logs.append))
        assert len(world.walks) == 1


def test_reachable_bank_skips_unreachable_fares_and_compares_walking_cost():
    with QuestWorld() as world:
        world.bank_rows = [{'tile': {'x': x, 'z': 3000, 'level': 0}} for x in [3001, 3002, 3003, 3050]]
        world.paths = {3002: 30, 3003: 10, 3050: 60}
        assert steps.reachable_bank(Tile(3000, 3000), world.logs.append) == Tile(3003, 3000)
        assert world.path_requests == [Tile(3001, 3000), Tile(3002, 3000), Tile(3003, 3000)]


def test_reachable_bank_falls_back_to_closest_or_none_when_no_path_is_known():
    with QuestWorld() as world:
        assert steps.reachable_bank(Tile(3000, 3000), world.logs.append) is None
        world.bank_rows = [{'tile': {'x': 3001, 'z': 3000, 'level': 0}}]
        assert steps.reachable_bank(Tile(3000, 3000), world.logs.append) == Tile(3001, 3000)
        assert 'trying the closest anyway' in world.logs[-1]


def test_withdraw_uses_exact_id_for_same_named_items_and_closes_bank():
    with QuestWorld() as world:
        world.stock = [Item(1, 'Key', 10), Item(2, 'Key', 10)]
        assert world.execute('withdraw', bank=Tile(3000, 3000), items=[{'name': 'Key', 'id': 2, 'qty': 5}])
        assert world.count_by_id(1) == 0 and world.count_by_id(2) == 5
        assert not world.open


def test_withdraw_keeps_requested_bank_open_and_reports_missing_stock():
    with QuestWorld() as world:
        world.stock = [Item(1, 'Key', 10)]
        assert world.execute('withdraw', bank=Tile(3000, 3000), leave_open=True,
                             items=[{'name': 'Key', 'qty': 5}, {'name': 'Missing', 'qty': 1}]) is False
        assert world.open and world.count('Key') == 5
        assert 'Missing' in world.logs[-1] and 'failed' in world.logs[-1]


def test_deposit_preserves_exact_ids_and_configured_name_policy():
    for exact in [True, False]:
        with QuestWorld() as world:
            world.pack = [Item(1, 'Key', 1, ops=['Deposit All']),
                          Item(2, 'Brass key', 1, ops=['Deposit All']),
                          Item(3, 'Gem', 1, ops=['Deposit All']), Item(4, 'Junk', 1, ops=['Deposit All'])]
            assert world.execute('deposit', bank=Tile(3000, 3000), keep=['KEY'], keep_ids=[3], exact_keep=exact)
            assert [i.id for i in world.pack] == ([1, 3] if exact else [1, 2, 3])
            assert not world.open


def test_banking_step_stops_when_no_bank_can_be_opened():
    with QuestWorld() as world:
        assert world.execute('scan_bank') is False
        assert world.bank_stands == [] and world.logs[-1] == 'scan_bank: no known bank'
        world.bank_opens = False
        assert world.execute('withdraw', bank=Tile(3000, 3000), items=[]) is False
        assert world.clicks == []


def test_buy_uses_existing_purse_and_requires_product_to_arrive():
    for arrives in [True, False]:
        with QuestWorld() as world:
            world.pack = [Item(995, 'Coins', 1000)]
            world.gain = Item(1, 'Bucket', 1) if arrives else None
            assert world.execute('buy', item='Bucket', qty=1, est_gp=10,
                                  shop=FakeModule(anchor=Tile(3000, 3000), npc='Shopkeeper')) == arrives
            assert world.bank_stands == []
            assert world.shop_calls == [('open', 'Shopkeeper'), ('buy', 'Bucket', 1), ('close',)]


def test_buy_does_not_visit_shop_when_bank_cannot_cover_estimate():
    with QuestWorld() as world:
        assert world.execute('buy', item='Bucket', qty=1, est_gp=100, bank=Tile(3000, 3000),
                              shop=FakeModule(anchor=Tile(3000, 3000), npc='Shopkeeper')) is False
        assert world.shop_calls == [] and 'could not cover' in world.logs[-1]


def test_buy_rejected_shop_open_never_sends_buy_action():
    with QuestWorld() as world:
        world.pack = [Item(995, 'Coins', 1000)]
        world.shop_opens = False
        assert world.execute('buy', item='Bucket', qty=1, est_gp=10,
                              shop=FakeModule(anchor=Tile(3000, 3000), npc='Shopkeeper')) is False
        assert world.shop_calls == [('open', 'Shopkeeper')]


def test_mine_rock_uses_catalog_id_and_requires_ore_arrival():
    with QuestWorld() as world:
        rock_id = steps.ROCK_TYPES['Iron'][0]
        world.locs = [SceneObject(world, rock_id, 'Rocks', 'Mine')]
        world.gain = Item(440, 'Iron ore', 1)
        assert world.execute('mine_rock', rock='Iron ore', item='Iron ore', anchor=Tile(3000, 3000))
        assert world.actions == [(rock_id, 'Mine')] and world.count('Iron ore') == 1


def test_unknown_rock_mapping_does_not_walk_or_mine():
    with QuestWorld() as world:
        assert world.execute('mine_rock', rock='Unknown', item='Unknown', anchor=Tile(3000, 3000)) is False
        assert world.actions == [] and world.walks == []


def test_custom_steps_propagate_plain_and_generator_results():
    with QuestWorld() as world:
        def custom(log):
            yield execution.Ticks(1)
            return 'completed'

        assert world.execute('custom', run=lambda log: False) is False
        assert world.execute('custom', run=custom) == 'completed'
        assert world.execute('wait') is True and world.waits[-1].count == 2
        assert world.execute('done') is True
        assert world.execute('unknown') is False and 'unknown step kind' in world.logs[-1]


def test_combine_tries_reverse_recipe_and_verifies_product_by_id():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A'), QuestItem(world, 2, 'B')]
        world.recipe = (2, 1)
        world.gain = Item(3, 'Product', 1)
        assert world.run(legs.combine_by_id(1, 2, 3, world.logs.append))
        assert world.uses == [(1, 2), (2, 1)]
        assert world.count_by_id(3) == 1


def test_combine_skips_existing_product_and_rejects_missing_materials():
    with QuestWorld() as world:
        world.pack = [Item(3, 'Product', 1)]
        assert world.run(legs.combine_by_id(1, 2, 3, world.logs.append))
        assert world.uses == []
        world.pack = []
        assert world.run(legs.combine_by_id(1, 2, 3, world.logs.append)) is False
        assert 'not in the pack' in world.logs[-1]


def test_climb_verifies_arrival_floor_after_loc_click():
    for lands in [True, False]:
        with QuestWorld() as world:
            world.locs = [SceneObject(world, 123, 'Ladder', 'Climb-up')]
            world.arrive_level = 1 if lands else None
            assert world.run(legs.climb(123, 'Climb-up', Tile(3000, 3000), Tile(3000, 3000, 1), world.logs.append)) == lands
            assert world.actions == [(123, 'Climb-up')]
            assert world.position.level == (1 if lands else 0)


def test_climb_already_on_target_floor_does_not_walk_or_click():
    with QuestWorld() as world:
        world.position = Tile(3000, 3000, 1)
        assert world.run(legs.climb(123, 'Climb-up', Tile(3000, 3000), Tile(3000, 3000, 1), world.logs.append))
        assert world.walks == [] and world.actions == []


def test_buy_tops_purse_up_without_withdrawing_existing_coins_again():
    with QuestWorld() as world:
        world.pack = [Item(995, 'Coins', 100)]
        world.stock = [Item(995, 'Coins', 50000)]
        world.gain = Item(1, 'Expensive item', 1)
        assert world.execute('buy', item='Expensive item', qty=1, est_gp=20000, bank=Tile(3000, 3000),
                              shop=FakeModule(anchor=Tile(3000, 3000), npc='Shopkeeper'))
        assert world.count('Coins') == 20000
        assert world.stock[0].count == 30100
        assert len(world.bank_stands) == 1 and world.count('Expensive item') == 1


def test_world_item_use_stops_on_failed_walk_missing_source_or_rejected_use():
    for reason in ['walk', 'source', 'click']:
        with QuestWorld() as world:
            world.position = Tile(2900, 2900)
            world.can_walk = reason != 'walk'
            world.accept_actions = reason != 'click'
            world.pack = [] if reason == 'source' else [QuestItem(world, 1, 'A')]
            world.locs = [SceneObject(world, 100, 'Target', 'Open')]
            assert world.execute('use_on', target_kind='loc', item='A', target='Target',
                                  anchor=Tile(3000, 3000)) is False
            assert world.uses == ([(1, 100)] if reason == 'click' else [])


def test_item_use_without_declared_product_waits_after_accepted_action():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A'), QuestItem(world, 2, 'B')]
        assert world.execute('use_on', target_kind='item', item='A', target='B')
        assert world.uses == [(1, 2)] and world.waits[-1].count == 3


def test_item_use_rejected_on_inventory_target_does_not_wait_for_product():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A'), QuestItem(world, 2, 'B')]
        world.accept_actions = False
        assert world.execute('use_on', target_kind='item', item='A', target='B', product='Product') is False
        assert world.waits == []


def test_gather_steps_walk_toward_missing_scene_objects():
    for kind, fields in [('pick_loc', {'loc': 'Wheat', 'op': 'Pick', 'item': 'Grain'}),
                         ('interact_loc', {'loc': 'Chest', 'op': 'Search'}),
                         ('mine_rock', {'rock': 'Iron', 'item': 'Iron ore'})]:
        with QuestWorld() as world:
            world.position = Tile(2900, 2900)
            assert world.execute(kind, anchor=Tile(3000, 3000), **fields)
            assert world.walks[0][0] == Tile(3000, 3000) and world.actions == []


def test_interact_without_expected_item_waits_after_click():
    with QuestWorld() as world:
        world.locs = [SceneObject(world, 100, 'Chest', 'Search')]
        assert world.execute('interact_loc', loc='Chest', op='Search')
        assert world.waits[-1].count == 3


def test_gather_step_does_not_wait_after_rejected_loc_click():
    for kind, fields, op in [('pick_loc', {'item': 'Grain', 'loc': 'Wheat', 'op': 'Pick'}, 'Pick'),
                             ('interact_loc', {'loc': 'Wheat', 'op': 'Search'}, 'Search'),
                             ('mine_rock', {'item': 'Iron ore', 'rock': 'Iron'}, 'Mine')]:
        with QuestWorld() as world:
            world.accept_actions = False
            id = steps.ROCK_TYPES['Iron'][0] if kind == 'mine_rock' else 100
            world.locs = [SceneObject(world, id, 'Wheat', op)]
            assert world.execute(kind, **fields) is False
            assert world.waits == []


def test_climb_stops_on_failed_walk_missing_ladder_or_rejected_click():
    for reason in ['walk', 'ladder', 'click']:
        with QuestWorld() as world:
            world.can_walk = reason != 'walk'
            world.accept_actions = reason != 'click'
            if reason != 'ladder':
                world.locs = [SceneObject(world, 123, 'Ladder', 'Climb-up')]
            assert world.run(legs.climb(123, 'Climb-up', Tile(3000, 3000), Tile(3000, 3000, 1), world.logs.append)) is False
            assert len(world.waits) == 1


def test_combine_reports_failure_after_both_directions_produce_nothing():
    with QuestWorld() as world:
        world.pack = [QuestItem(world, 1, 'A'), QuestItem(world, 2, 'B')]
        assert world.run(legs.combine_by_id(1, 2, 3, world.logs.append)) is False
        assert world.uses == [(1, 2), (2, 1)]
        assert 'produced no 3' in world.logs[-1]

"""Ernest's supplies require confirmed pickups, safe closet exits and fountain dialogue."""

import rs2004.quests.defs.ernest.items as ernest
import rs2004.quests.exec.prompts as prompts
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_bank_workflows import Item
from test_quest_prompt_workflows import PromptWorld, Door

EC_ID = ernest.EC_ID
EC_NAME = ernest.EC_NAME
EC_TILE = ernest.EC_TILE


class QuestItem(Item):
    def __init__(self, world, id, name):
        Item.__init__(self, id, name, 1)
        self.world = world

    def interact(self, op):
        assert op == 'Take'
        self.world.takes.append(self.id)
        if self.id in self.world.reject_takes:
            return False
        if self.world.pickups_land:
            self.world.pending_gain = self.id
        return True

    def distance(self):
        return 1

    def use_on(self, target):
        self.world.uses.append((self.id, target.id))
        if self.id in self.world.reject_uses:
            return False
        if self.id == EC_ID.SPADE and self.world.key_lands:
            self.world.pending_gain = EC_ID.CLOSET_KEY
        elif self.id == EC_ID.CLOSET_KEY and self.world.door_crosses:
            self.world.pending_position = (EC_TILE.CLOSET_STAND if ernest.in_closet(self.world.position)
                                           else EC_TILE.CLOSET_INSIDE)
        elif self.id == EC_ID.POISON and self.world.combine_lands:
            self.world.pending_gain = EC_ID.POISONED_FISH_FOOD
        elif self.id == EC_ID.POISONED_FISH_FOOD and self.world.pour_lands:
            self.world.pending_remove = EC_ID.POISONED_FISH_FOOD
        return True


class ErnestWorld(PromptWorld):
    def __init__(self):
        PromptWorld.__init__(self)
        self.position = EC_TILE.CLOSET_STAND
        self.locations = [Door(self, id=100, name='Door'),
                          Door(self, id=101, name='Compost heap'), Door(self, id=102, name='Fountain')]
        self.spawns = [QuestItem(self, EC_ID.RUBBER_TUBE, EC_NAME.RUBBER_TUBE),
                       QuestItem(self, EC_ID.POISON, EC_NAME.POISON),
                       QuestItem(self, EC_ID.FISH_FOOD, EC_NAME.FISH_FOOD)]
        self.takes = []
        self.uses = []
        self.reject_takes = []
        self.reject_uses = []
        self.pickups_land = True
        self.key_lands = True
        self.door_crosses = True
        self.combine_lands = True
        self.pour_lands = True
        self.pending_gain = None
        self.pending_remove = None
        self.pending_position = None
        self.walk_results = []
        self.search_results = ['gauge']
        self.searches = 0
        self.gauge_after_chat = False
        self.lose_poison_on_food = False

    def __enter__(self):
        PromptWorld.__enter__(self)
        replacements = {
            'inventory': self, 'game': FakeModule(tile=lambda: self.position),
            'sustain': prompts.sustain, 'traversal': prompts.traversal,
            'ground_items': FakeModule(query=lambda: EntityQuery(self.ground_scene, lambda item: True)),
            'game_messages': FakeModule(mark=lambda: len(self.messages),
                                        since=lambda mark: self.messages[mark:], saw_since=self.saw_since),
        }
        self.ernest_saved = {}
        for name, value in replacements.items():
            self.ernest_saved[name] = getattr(ernest, name)
            setattr(ernest, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.ernest_saved.items():
            setattr(ernest, name, value)
        PromptWorld.__exit__(self, *args)

    def items(self):
        return self.pack

    def count_by_id(self, id):
        return sum([item.count for item in self.pack if item.id == id])

    def carry(self, id):
        self.pack.append(QuestItem(self, id, 'Carried supply'))

    def ground_scene(self, ids, names, radius, layer):
        return [item for item in self.spawns if names is None or item.name in names]

    def saw_since(self, mark, text):
        return any([text.lower() in message.text.lower() for message in self.messages[mark:]])

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        arrived = self.walk_results.pop(0) if self.walk_results else self.can_walk
        if arrived:
            self.position = tile
        return arrived

    def loc_op(self, name, op, near, expect, **kwargs):
        assert name == 'Fountain' and op == 'Search'
        self.loc_requests.append((name, op, near, kwargs))
        self.searches += 1
        result = self.search_results.pop(0) if self.search_results else 'unknown'
        yield execution.Ticks(1)
        if result == 'gauge':
            self.pages = [('continue', ['You search the water']), ('continue', ['You find a gauge'])]
            self.gauge_after_chat = True
            return 'done'
        if result == 'bitten':
            self.messages.append(FakeModule(text=ernest.BITTEN.upper()))
        elif result == 'unknown':
            self.messages.append(FakeModule(text='Nothing happens.'))
        return 'unavailable'

    def advance(self):
        PromptWorld.advance(self)
        if self.pending_gain is not None:
            id = self.pending_gain
            self.carry(id)
            if id == EC_ID.FISH_FOOD and self.lose_poison_on_food:
                self.pack = [item for item in self.pack if item.id != EC_ID.POISON]
            self.pending_gain = None
        if self.pending_remove is not None:
            self.pack = [item for item in self.pack if item.id != self.pending_remove]
            self.pending_remove = None
        if self.pending_position is not None:
            self.position = self.pending_position
            self.pending_position = None
        if self.gauge_after_chat and not self.pages:
            self.carry(EC_ID.PRESSURE_GAUGE)
            self.gauge_after_chat = False

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
        assert False, 'Ernest workflow exceeded its simulated update budget'

    def take_tube(self):
        return self.run(ernest.take_spawn(EC_ID.RUBBER_TUBE, EC_NAME.RUBBER_TUBE,
                                          EC_TILE.RUBBER_TUBE_SPAWN, self.logs.append))

    def tube(self):
        return self.run(ernest.fetch_rubber_tube(self.logs.append))

    def poison(self):
        return self.run(ernest.poison_fountain(self.logs.append))

    def gauge(self):
        return self.run(ernest.fetch_pressure_gauge(self.logs.append))


def test_ernest_spawn_already_held_skips_walk_and_pickup():
    with ErnestWorld() as world:
        world.carry(EC_ID.RUBBER_TUBE)
        assert world.take_tube()
        assert world.takes == [] and world.waits == []


def test_ernest_spawn_waits_for_inventory_after_settling_scene():
    with ErnestWorld() as world:
        assert world.take_tube()
        assert world.takes == [EC_ID.RUBBER_TUBE]
        assert world.count_by_id(EC_ID.RUBBER_TUBE) == 1
        assert world.waits[1].count == 2
        assert world.walks[0][1]['attempts'] == 4


def test_ernest_spawn_failed_walk_or_missing_spawn_is_failure():
    for missing in [True, False]:
        with ErnestWorld() as world:
            world.spawns = [] if missing else world.spawns
            world.can_walk = missing
            assert world.take_tube() is False
            assert world.takes == []
            assert ('no Rubber tube' if missing else 'could not reach') in world.logs[-1]


def test_ernest_spawn_rejected_or_unacknowledged_pickup_is_failure():
    for rejected in [True, False]:
        with ErnestWorld() as world:
            world.reject_takes = [EC_ID.RUBBER_TUBE] if rejected else []
            world.pickups_land = False
            assert world.take_tube() is False
            assert world.count_by_id(EC_ID.RUBBER_TUBE) == 0
            if not rejected:
                assert world.now >= 8000


def test_ernest_key_already_held_skips_compost():
    with ErnestWorld() as world:
        world.carry(EC_ID.CLOSET_KEY)
        assert world.run(ernest.dig_closet_key(world.logs.append))
        assert world.uses == [] and world.waits == []


def test_ernest_key_uses_spade_on_compost_and_waits_for_key():
    with ErnestWorld() as world:
        world.carry(EC_ID.SPADE)
        assert world.run(ernest.dig_closet_key(world.logs.append))
        assert world.uses == [(EC_ID.SPADE, 101)]
        assert world.count_by_id(EC_ID.CLOSET_KEY) == 1


def test_ernest_closet_boundaries_and_floor():
    for tile in [Tile(3108, 3366), Tile(3112, 3368)]:
        assert ernest.in_closet(tile)
    for tile in [None, Tile(3107, 3367), Tile(3113, 3367), Tile(3110, 3365),
                 Tile(3110, 3369), Tile(3110, 3367, 1)]:
        assert not ernest.in_closet(tile)


def test_ernest_closet_already_on_requested_side_skips_key_use():
    for direction in ['in', 'out']:
        with ErnestWorld() as world:
            world.position = EC_TILE.CLOSET_INSIDE if direction == 'in' else EC_TILE.CLOSET_STAND
            assert world.run(ernest.cross_closet_door(direction, world.logs.append))
            assert world.uses == [] and world.waits == []


def test_ernest_closet_missing_key_cannot_enter_or_leave():
    for direction in ['in', 'out']:
        with ErnestWorld() as world:
            world.position = EC_TILE.CLOSET_STAND if direction == 'in' else EC_TILE.CLOSET_INSIDE
            assert world.run(ernest.cross_closet_door(direction, world.logs.append)) is False
            assert 'no key in the pack' in world.logs[-1] and world.uses == []


def test_ernest_leave_closet_runs_upkeep_and_retains_key():
    with ErnestWorld() as world:
        world.position = EC_TILE.CLOSET_INSIDE
        world.carry(EC_ID.CLOSET_KEY)
        assert world.run(ernest.leave_closet(world.logs.append))
        assert not ernest.in_closet(world.position)
        assert world.sustain_calls == 1 and world.count_by_id(EC_ID.CLOSET_KEY) == 1


def test_ernest_tube_fetch_digs_key_enters_takes_and_exits():
    with ErnestWorld() as world:
        world.carry(EC_ID.SPADE)
        assert world.tube()
        assert world.uses == [(EC_ID.SPADE, 101), (EC_ID.CLOSET_KEY, 100), (EC_ID.CLOSET_KEY, 100)]
        assert world.count_by_id(EC_ID.RUBBER_TUBE) == 1
        assert not ernest.in_closet(world.position)


def test_ernest_tube_already_held_still_exits_closet():
    with ErnestWorld() as world:
        world.position = EC_TILE.CLOSET_INSIDE
        world.carry(EC_ID.RUBBER_TUBE)
        world.carry(EC_ID.CLOSET_KEY)
        assert world.tube()
        assert world.takes == [] and not ernest.in_closet(world.position)


def test_ernest_tube_missing_spade_stops_before_compost():
    with ErnestWorld() as world:
        assert world.tube() is False
        assert world.uses == [] and 'no spade' in world.logs[-1]


def test_ernest_tube_failed_key_dig_does_not_try_door():
    with ErnestWorld() as world:
        world.carry(EC_ID.SPADE)
        world.reject_uses = [EC_ID.SPADE]
        assert world.tube() is False
        assert world.uses == [(EC_ID.SPADE, 101)]
        assert world.logs[-1] == 'the compost heap did not give up a key'


def test_ernest_tube_failed_door_prevents_pickup():
    with ErnestWorld() as world:
        world.carry(EC_ID.SPADE)
        world.carry(EC_ID.CLOSET_KEY)
        world.reject_uses = [EC_ID.CLOSET_KEY]
        assert world.tube() is False
        assert world.takes == [] and world.logs[-1] == 'the closet door did not open to the key'


def test_ernest_tube_missing_spawn_still_keys_out_of_closet():
    with ErnestWorld() as world:
        world.carry(EC_ID.SPADE)
        world.carry(EC_ID.CLOSET_KEY)
        world.spawns = []
        assert world.tube() is False
        assert world.uses == [(EC_ID.CLOSET_KEY, 100), (EC_ID.CLOSET_KEY, 100)]
        assert not ernest.in_closet(world.position)


def test_ernest_fountain_search_drives_both_chat_pages_before_gauge_arrives():
    with ErnestWorld() as world:
        assert world.run(ernest.search_fountain(world.logs.append)) == 'gauge'
        assert world.clicks == ['continue', 'continue']
        assert world.count_by_id(EC_ID.PRESSURE_GAUGE) == 1 and world.searches == 1


def test_ernest_fountain_bite_requires_new_message_and_is_not_retried():
    with ErnestWorld() as world:
        world.search_results = ['bitten']
        assert world.run(ernest.search_fountain(world.logs.append)) == 'bitten'
        assert world.searches == 1


def test_ernest_fountain_old_bite_does_not_classify_failed_search_as_bitten():
    with ErnestWorld() as world:
        world.messages = [FakeModule(text=ernest.BITTEN)]
        world.search_results = ['unknown'] * 3
        assert world.run(ernest.search_fountain(world.logs.append)) == 'unknown'
        assert world.searches == 3
        assert len([line for line in world.logs if 'said: [Nothing happens.]' in line]) == 3


def test_ernest_fountain_failed_walk_does_not_search():
    with ErnestWorld() as world:
        world.can_walk = False
        assert world.run(ernest.search_fountain(world.logs.append)) == 'unknown'
        assert world.searches == 0 and world.logs[-1] == 'could not reach the fountain stand'


def test_ernest_poison_collects_ingredients_combines_then_pours():
    with ErnestWorld() as world:
        assert world.poison()
        assert world.takes == [EC_ID.POISON, EC_ID.FISH_FOOD]
        assert world.uses == [(EC_ID.POISON, EC_ID.FISH_FOOD), (EC_ID.POISONED_FISH_FOOD, 102)]
        assert world.count_by_id(EC_ID.POISONED_FISH_FOOD) == 0


def test_ernest_poison_precombined_food_skips_ingredients():
    with ErnestWorld() as world:
        world.carry(EC_ID.POISONED_FISH_FOOD)
        assert world.poison()
        assert world.takes == [] and world.uses == [(EC_ID.POISONED_FISH_FOOD, 102)]


def test_ernest_poison_missing_either_spawn_stops_before_combining():
    for missing in [EC_ID.POISON, EC_ID.FISH_FOOD]:
        with ErnestWorld() as world:
            world.spawns = [item for item in world.spawns if item.id != missing]
            assert world.poison() is False
            assert world.uses == []


def test_ernest_poison_disappearing_ingredient_is_reported():
    with ErnestWorld() as world:
        world.lose_poison_on_food = True
        assert world.poison() is False
        assert world.uses == []
        assert world.logs[-1] == 'poison or fish food went missing before they could be combined'


def test_ernest_poison_rejected_combine_or_missing_product_does_not_pour():
    for rejected in [True, False]:
        with ErnestWorld() as world:
            world.combine_lands = False
            world.reject_uses = [EC_ID.POISON] if rejected else []
            assert world.poison() is False
            assert world.uses == [(EC_ID.POISON, EC_ID.FISH_FOOD)]
            if not rejected:
                assert world.logs[-1] == 'combining the poison and the fish food produced nothing'


def test_ernest_poison_pour_requires_food_to_be_consumed():
    with ErnestWorld() as world:
        world.carry(EC_ID.POISONED_FISH_FOOD)
        world.pour_lands = False
        assert world.poison() is False
        assert world.count_by_id(EC_ID.POISONED_FISH_FOOD) == 1


def test_ernest_gauge_already_held_skips_all_interactions():
    with ErnestWorld() as world:
        world.carry(EC_ID.PRESSURE_GAUGE)
        assert world.gauge()
        assert world.searches == 0 and world.waits == []


def test_ernest_gauge_from_previously_poisoned_fountain_needs_no_ingredients():
    with ErnestWorld() as world:
        assert world.gauge()
        assert world.takes == [] and world.uses == []
        assert world.logs[-1] == 'the fountain was already poisoned'


def test_ernest_gauge_bite_poisons_then_waits_before_searching_again():
    with ErnestWorld() as world:
        world.search_results = ['bitten', 'gauge']
        assert world.gauge()
        assert world.searches == 2
        assert any([isinstance(wait, execution.Ticks) and wait.count == 6 for wait in world.waits])
        assert world.count_by_id(EC_ID.PRESSURE_GAUGE) == 1


def test_ernest_gauge_unknown_search_still_tries_poisoning():
    with ErnestWorld() as world:
        world.search_results = ['unknown'] * 3 + ['gauge']
        assert world.gauge()
        assert world.searches == 4
        assert 'the fountain would not answer — poisoning it anyway' in world.logs


def test_ernest_gauge_failed_poisoning_without_gauge_is_failure():
    with ErnestWorld() as world:
        world.search_results = ['bitten']
        world.spawns = []
        assert world.gauge() is False
        assert world.searches == 1


def test_ernest_gauge_post_poison_searches_are_bounded():
    with ErnestWorld() as world:
        world.search_results = ['bitten'] * 4
        assert world.gauge() is False
        assert world.searches == 4
        assert world.now >= 5000

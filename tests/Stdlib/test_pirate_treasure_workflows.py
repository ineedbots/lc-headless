"""Pirate's Treasure verifies item arrivals, scroll cleanup and server-confirmed digs."""

import rs2004.quests.defs.piratestreasure.treasure as treasure
import rs2004.quests.exec.prompts as prompts
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_bank_workflows import Item
from test_quest_prompt_workflows import PromptWorld, Door

PT_ID = treasure.PT_ID
PT_TILE = treasure.PT_TILE


class QuestItem(Item):
    def __init__(self, world, id, name):
        Item.__init__(self, id, name, 1)
        self.world = world

    def interact(self, op):
        self.world.item_clicks.append((self.id, op))
        accepted = self.world.accept_item
        if self.world.item_results:
            accepted = self.world.item_results.pop(0)
        if accepted:
            if op == 'Read' and self.world.scroll_opens:
                self.world.pending_scroll = True
            if op == 'Dig':
                self.world.pending_dig = True
        return accepted

    def use_on(self, target):
        self.world.key_uses.append((self.id, target.id))
        if self.world.accept_item and self.world.chest_gives_note:
            self.world.pending_gain = PT_ID.PIRATE_MESSAGE
        return self.world.accept_item


class Gardener:
    def __init__(self, world, id=None, distance=2):
        self.world = world
        self.id = PT_ID.GARDENER if id is None else id
        self.dist = distance

    def distance(self):
        return self.dist

    def interact(self, op):
        assert op == 'Attack'
        self.world.attacks += 1
        if self.world.accept_attack and self.world.gardener_dies:
            self.world.pending_death = True
        return self.world.accept_attack


class TreasureWorld(PromptWorld):
    def __init__(self):
        PromptWorld.__init__(self)
        self.position = PT_TILE.DIG_SITE
        self.accept_item = True
        self.item_results = []
        self.item_clicks = []
        self.rum_arrives = True
        self.chest_gives_note = True
        self.scroll_opens = True
        self.pending_scroll = False
        self.pending_gain = None
        self.pending_dig = False
        self.dig_messages = [treasure.DUG]
        self.gardeners = []
        self.accept_attack = True
        self.gardener_dies = True
        self.pending_death = False
        self.attacks = 0
        self.styles = []
        self.walk_results = []
        self.lose_spade = False
        self.locations = [Door(self, id=treasure.PT_LOC.PIRATE_CHEST, name='Chest')]

    def __enter__(self):
        PromptWorld.__enter__(self)
        replacements = {
            '_core': self, 'inventory': self,
            'sustain': prompts.sustain, 'traversal': prompts.traversal,
            'game': FakeModule(set_combat_style=self.styles.append),
            'reader': FakeModule(modals=lambda: FakeModule(main=self.get_main_modal())),
            'npcs': FakeModule(query=lambda: EntityQuery(self.npc_scene, lambda npc: True)),
            'game_messages': FakeModule(mark=lambda: len(self.messages),
                                        since=lambda mark: self.messages[mark:], saw_since=self.saw_since),
        }
        self.treasure_saved = {}
        for name, value in replacements.items():
            self.treasure_saved[name] = getattr(treasure, name)
            setattr(treasure, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.treasure_saved.items():
            setattr(treasure, name, value)
        PromptWorld.__exit__(self, *args)

    def items(self):
        return self.pack

    def count_by_id(self, id):
        return sum([item.count for item in self.pack if item.id == id])

    def carry(self, id, name='Quest item'):
        self.pack.append(QuestItem(self, id, name))

    def npc_scene(self, ids, names, radius, layer):
        return [npc for npc in self.gardeners if radius is None or npc.distance() <= radius]

    def saw_since(self, mark, text):
        return any([text.lower() in message.text.lower() for message in self.messages[mark:]])

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        arrived = self.walk_results.pop(0) if self.walk_results else self.can_walk
        if arrived:
            self.position = tile
        if self.lose_spade:
            self.pack = []
        return arrived

    def loc_op(self, name, op, near, expect, **kwargs):
        self.loc_requests.append((name, op, near, kwargs))
        if self.loc_status == 'done' and self.rum_arrives:
            self.pending_gain = PT_ID.RUM
        yield execution.Ticks(1)
        self.pages = list(self.prompt_pages)
        return self.loc_status

    def advance(self):
        PromptWorld.advance(self)
        if self.pending_gain is not None:
            self.carry(self.pending_gain)
            self.pending_gain = None
        if self.pending_scroll:
            self.pages = [('main', ['Buried treasure'])]
            self.pending_scroll = False
        if self.pending_death:
            self.gardeners = []
            self.position = Tile(3005, 3383)
            self.pending_death = False
        if self.pending_dig:
            if self.dig_messages:
                text = self.dig_messages.pop(0)
                if text is not None:
                    self.messages.append(FakeModule(text=text))
            self.pending_dig = False

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
        assert False, 'treasure exceeded its simulated update budget'

    def dig(self):
        return self.run(treasure.dig_treasure(self.logs.append))


def test_rum_already_carried_skips_crate_search():
    with TreasureWorld() as world:
        world.carry(PT_ID.RUM)
        assert world.run(treasure.collect_rum(world.logs.append))
        assert world.loc_requests == [] and world.waits == []


def test_rum_search_selects_exact_crate_and_requires_item_arrival():
    with TreasureWorld() as world:
        assert world.run(treasure.collect_rum(world.logs.append))
        request = world.loc_requests[0]
        assert request[:3] == ('Crate', 'Search', PT_TILE.GROCERY_CRATE)
        assert request[3]['id'] == treasure.PT_LOC.GROCERY_CRATE
        assert request[3]['within'] == 6
        assert world.count_by_id(PT_ID.RUM) == 1 and world.walks == []


def test_rum_missing_from_crate_declines_job_then_returns_to_plantation():
    with TreasureWorld() as world:
        world.rum_arrives = False
        world.loc_status = 'unavailable'
        world.prompt_pages = [('options', ['Yes', 'No, thanks'])]
        assert world.run(treasure.collect_rum(world.logs.append)) is False
        assert world.clicks == [111]
        assert world.walks[-1][0] == PT_TILE.BANANA_CRATE
        assert world.walks[-1][1]['timeout_ms'] == 300000


def test_rum_unanswered_search_times_out_before_crossing():
    with TreasureWorld() as world:
        world.rum_arrives = False
        assert world.run(treasure.collect_rum(world.logs.append)) is False
        assert world.now >= 15000 and len(world.walks) == 1


def test_chest_existing_message_or_missing_key_avoids_use():
    for has_message in [True, False]:
        with TreasureWorld() as world:
            if has_message:
                world.carry(PT_ID.PIRATE_MESSAGE)
            assert world.run(treasure.open_chest(world.logs.append)) == has_message
            assert world.key_uses == [] and world.waits == []
            if not has_message:
                assert world.logs == ['no chest key in the pack']


def test_chest_uses_key_on_exact_chest_and_waits_for_message():
    with TreasureWorld() as world:
        world.carry(PT_ID.CHEST_KEY)
        world.locations.insert(0, Door(world, id=99, name='Chest'))
        assert world.run(treasure.open_chest(world.logs.append))
        assert world.key_uses == [(PT_ID.CHEST_KEY, treasure.PT_LOC.PIRATE_CHEST)]
        assert world.count_by_id(PT_ID.PIRATE_MESSAGE) == 1


def test_chest_rejected_key_or_no_product_is_failure():
    for rejects in [True, False]:
        with TreasureWorld() as world:
            world.carry(PT_ID.CHEST_KEY)
            world.accept_item = not rejects
            world.chest_gives_note = False
            assert world.run(treasure.open_chest(world.logs.append)) is False
            assert world.count_by_id(PT_ID.PIRATE_MESSAGE) == 0


def test_read_message_waits_for_scroll_and_closes_it():
    with TreasureWorld() as world:
        world.carry(PT_ID.PIRATE_MESSAGE)
        assert world.run(treasure.read_message(world.logs.append))
        assert world.item_clicks == [(PT_ID.PIRATE_MESSAGE, 'Read')]
        assert world.clicks == ['close'] and world.get_main_modal() == -1


def test_read_missing_or_rejected_message_is_failure():
    for missing in [True, False]:
        with TreasureWorld() as world:
            if not missing:
                world.carry(PT_ID.PIRATE_MESSAGE)
                world.accept_item = False
            assert world.run(treasure.read_message(world.logs.append)) is False
            assert world.clicks == [] and world.waits == []


def test_read_message_without_scroll_bounds_wait_and_does_not_close():
    with TreasureWorld() as world:
        world.carry(PT_ID.PIRATE_MESSAGE)
        world.scroll_opens = False
        world.run(treasure.read_message(world.logs.append))
        assert world.now == 6000 and world.clicks == []


def test_clear_gardener_ignores_other_ids_and_out_of_range_gardener():
    with TreasureWorld() as world:
        world.gardeners = [Gardener(world, id=999), Gardener(world, distance=11)]
        world.run(treasure.clear_gardener(world.logs.append))
        assert world.attacks == 0 and world.styles == []
        assert world.logs == ['no gardener within the dig radius']


def test_clear_gardener_attacks_at_range_boundary_and_waits_for_removal():
    with TreasureWorld() as world:
        world.gardeners = [Gardener(world, distance=10)]
        world.run(treasure.clear_gardener(world.logs.append))
        assert world.attacks == 1 and world.gardeners == []
        assert world.styles == ['strength'] and world.logs[-1] == 'gardener down'


def test_clear_gardener_rejected_attacks_are_bounded():
    with TreasureWorld() as world:
        world.gardeners = [Gardener(world)]
        world.accept_attack = False
        world.run(treasure.clear_gardener(world.logs.append))
        assert world.attacks == 6
        assert all([wait.count == 2 for wait in world.waits])
        assert world.logs[-1] == 'the gardener would not go down — digging anyway'


def test_clear_gardener_unresolved_fight_retries_six_times():
    with TreasureWorld() as world:
        world.gardeners = [Gardener(world)]
        world.gardener_dies = False
        world.run(treasure.clear_gardener(world.logs.append))
        assert world.attacks == 6 and world.now == 120000


def test_dig_requires_spade_before_walking():
    with TreasureWorld() as world:
        assert world.dig() is False
        assert world.walks == [] and world.logs == ['no spade in the pack — cannot dig']


def test_dig_failed_initial_walk_does_not_click_spade():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.can_walk = False
        assert world.dig() is False
        assert world.item_clicks == [] and world.logs[-1] == 'could not reach the dig site'


def test_dig_returns_to_exact_tile_after_gardener_and_waits_for_quest_queue():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.gardeners = [Gardener(world)]
        assert world.dig()
        assert world.attacks == 1 and world.position == PT_TILE.DIG_SITE
        assert [request[1]['radius'] for request in world.walks] == [1, 0]
        assert world.item_clicks == [(PT_ID.SPADE, 'Dig')]
        assert world.waits[-1].count == 8


def test_dig_retries_failed_return_to_exact_tile():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.walk_results = [True, False, True, True]
        assert world.dig()
        assert len(world.walks) == 4 and len(world.item_clicks) == 1
        assert 'could not get back onto the dig tile after the gardener' in world.logs


def test_dig_exhausts_failed_return_attempts_without_using_spade():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.walk_results = [True, False] * 4
        assert world.dig() is False
        assert len(world.walks) == 8 and world.item_clicks == []


def test_dig_lost_spade_during_travel_returns_failure():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.lose_spade = True
        assert world.dig() is False
        assert world.item_clicks == []


def test_dig_rejected_spade_click_retries_until_accepted():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.item_results = [False, True]
        assert world.dig()
        assert len(world.item_clicks) == 2


def test_dig_repeated_rejected_clicks_stop_after_four_attempts():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.accept_item = False
        assert world.dig() is False
        assert len(world.item_clicks) == 4
        assert not any([isinstance(wait, execution.Ticks) and wait.count == 8 for wait in world.waits])


def test_dig_ignores_old_confirmation_and_requires_new_message():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.messages = [FakeModule(text=treasure.DUG)]
        world.dig_messages = [None] * 4
        assert world.dig() is False
        assert len(world.item_clicks) == 4
        assert len([line for line in world.logs if 'the dig landed nothing' in line]) == 4


def test_dig_unrelated_message_is_logged_then_new_confirmation_succeeds():
    with TreasureWorld() as world:
        world.carry(PT_ID.SPADE)
        world.dig_messages = ['Nothing interesting happens.', treasure.DUG.upper()]
        assert world.dig()
        assert len(world.item_clicks) == 2
        assert 'the dig landed nothing — said: [Nothing interesting happens.]' in world.logs

"""Arrav collection confirms loot and cleans up modals and sealed hideouts."""

import rs2004.quests.defs.shieldofarrav.phoenix as phoenix
import rs2004.quests.defs.shieldofarrav.blackarm as blackarm
import rs2004.quests.defs.shieldofarrav.state as state
import rs2004.quests.exec.legs as legs
import rs2004.quests.exec.prompts as prompts
from rs2004 import execution
from rs2004.entities import EntityQuery
from helpers import FakeModule
from test_bank_workflows import Item
from test_arrav_hideout_workflows import HideoutWorld, SOA_LOC, SOA_TILE

SOA_ID = phoenix.SOA_ID


class LootItem(Item):
    def __init__(self, world, id):
        Item.__init__(self, id, 'Quest loot', 1)
        self.world = world

    def distance(self):
        return 1

    def interact(self, op):
        self.world.loot_clicks.append((self.id, op))
        if not self.world.accept_loot:
            return False
        if op == 'Read':
            self.world.pages = [('main', ['The Shield of Arrav'])]
        elif self.world.loot_lands:
            self.world.pending_gain = self.id
        elif self.world.take_refusal:
            self.world.messages.append(FakeModule(text="I can't reach that!"))
        return True


class Jonny:
    id = phoenix.JONNY_NPC

    def __init__(self, world):
        self.world = world

    def distance(self):
        return 1

    def interact(self, op):
        assert op == 'Attack'
        self.world.attacks += 1
        if self.world.accept_attack and self.world.jonny_dies:
            self.world.pending_death = True
        return self.world.accept_attack


class Container:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def distance(self):
        return 1

    def actions(self):
        return ['Search', 'Shut']


class CollectionWorld(HideoutWorld):
    def __init__(self):
        HideoutWorld.__init__(self)
        self.pack = []
        self.drops = []
        self.targets = [Jonny(self)]
        self.loot_clicks = []
        self.styles = []
        self.accept_loot = True
        self.loot_lands = True
        self.take_refusal = False
        self.accept_attack = True
        self.jonny_dies = True
        self.pending_death = False
        self.pending_gain = None
        self.attacks = 0
        self.interrupted = False
        self.container_opens = True
        self.search_result = 'loot'
        self.report_consumed = True

    def __enter__(self):
        HideoutWorld.__enter__(self)
        self.collection_saved = []
        common = {
            '_core': self, 'inventory': self, 'sustain': prompts.sustain,
            'game': FakeModule(tile=lambda: self.position, set_combat_style=self.styles.append),
            'traversal': legs.traversal,
            'ground_items': FakeModule(query=lambda: EntityQuery(self.ground_scene, lambda item: True)),
            'npcs': FakeModule(query=lambda: EntityQuery(self.npc_scene, lambda npc: True)),
            'game_messages': FakeModule(mark=lambda: len(self.messages),
                                        since=lambda mark: self.messages[mark:], saw_since=self.saw_since),
            'event_signal': FakeModule(pending=lambda: self.interrupted),
        }
        for module in [phoenix, blackarm]:
            for name, value in common.items():
                self.collection_saved.append((module, name, getattr(module, name)))
                setattr(module, name, value)
        for name, value in {'inventory': self, 'reader': FakeModule(main_modal_texts=self.modal_texts)}.items():
            self.collection_saved.append((state, name, getattr(state, name)))
            setattr(state, name, value)
        return self

    def __exit__(self, *args):
        for module, name, value in self.collection_saved:
            setattr(module, name, value)
        HideoutWorld.__exit__(self, *args)

    def items(self):
        return self.pack

    def count_by_id(self, id):
        return sum([item.count for item in self.pack if item.id == id])

    def carry(self, id):
        self.pack.append(LootItem(self, id))

    def ground_scene(self, ids, names, radius, layer):
        return self.drops

    def npc_scene(self, ids, names, radius, layer):
        return self.targets

    def modal_texts(self):
        return self.pages[0][1] if self.kind() == 'main' else []

    def saw_since(self, mark, text):
        return any([text.lower() in message.text.lower() for message in self.messages[mark:]])

    def loc_op(self, name, op, near, expect, **kwargs):
        self.loc_requests.append((name, op, near, kwargs))
        if op == 'Open':
            if self.container_opens:
                id = SOA_LOC.CHEST_OPEN if name == 'Chest' else SOA_LOC.CUPBOARD_OPEN
                self.locations.append(Container(id, name))
            yield execution.Ticks(1)
            return 'done' if self.container_opens else 'unavailable'
        if self.search_result == 'loot':
            self.pending_gain = (SOA_ID.BOOK if name == 'Bookcase' else
                                 (SOA_ID.SHIELD_PHOENIX if name == 'Chest' else SOA_ID.SHIELD_BLACKARM))
        yield execution.Ticks(1)
        if self.search_result == 'empty':
            text = phoenix.CHEST_EMPTY if name == 'Chest' else blackarm.CUPBOARD_BARE
            self.pages = [('main', [text.upper()])]
        return 'unavailable' if self.search_result == 'silent' else 'done'

    def advance(self):
        HideoutWorld.advance(self)
        if self.pending_gain is not None:
            self.carry(self.pending_gain)
            self.pending_gain = None
        if self.pending_death:
            self.targets = []
            self.pending_death = False
        if self.report_consumed and 'continue' in self.clicks and not self.pages:
            self.pack = [item for item in self.pack if item.id != SOA_ID.REPORT]

    def half(self, gang):
        task = phoenix.take_phoenix_half if gang == 'phoenix' else blackarm.take_black_arm_half
        return self.run(task(self.logs.append))

    def kill(self):
        return self.run(phoenix.kill_jonny(self.logs.append))


def half_id(gang):
    return SOA_ID.SHIELD_PHOENIX if gang == 'phoenix' else SOA_ID.SHIELD_BLACKARM


def test_arrav_book_already_held_does_not_search_again():
    with CollectionWorld() as world:
        world.carry(SOA_ID.BOOK)
        assert world.run(phoenix.take_book(world.logs.append))
        assert world.loc_requests == [] and world.waits == []


def test_arrav_book_search_selects_quest_bookcase_and_waits_for_book():
    with CollectionWorld() as world:
        assert world.run(phoenix.take_book(world.logs.append))
        request = world.loc_requests[0]
        assert request[:3] == ('Bookcase', 'Check', SOA_TILE.BOOKCASE)
        assert request[3]['id'] == SOA_LOC.BOOKCASE and request[3]['within'] == 6
        assert world.count_by_id(SOA_ID.BOOK) == 1


def test_arrav_book_failed_search_reports_no_book():
    with CollectionWorld() as world:
        world.search_result = 'silent'
        assert world.run(phoenix.take_book(world.logs.append)) is False
        assert world.logs[-1] == 'the quest bookcase gave up no book'


def test_arrav_read_book_waits_then_closes_main_modal():
    with CollectionWorld() as world:
        world.carry(SOA_ID.BOOK)
        assert world.run(phoenix.read_book(world.logs.append))
        assert world.loot_clicks == [(SOA_ID.BOOK, 'Read')]
        assert world.waits[0].count == 3
        assert world.clicks == ['close'] and not world.pages


def test_arrav_read_missing_or_rejected_book_is_failure():
    for missing in [True, False]:
        with CollectionWorld() as world:
            if not missing:
                world.carry(SOA_ID.BOOK)
            world.accept_loot = False
            assert world.run(phoenix.read_book(world.logs.append)) is False
            assert world.waits == []


def test_arrav_report_already_held_skips_fight_and_pickup():
    with CollectionWorld() as world:
        world.carry(SOA_ID.REPORT)
        assert world.kill()
        assert world.attacks == 0 and world.loot_clicks == []


def test_arrav_report_on_ground_takes_priority_over_fighting():
    with CollectionWorld() as world:
        world.drops = [LootItem(world, SOA_ID.REPORT)]
        assert world.kill()
        assert world.attacks == 0 and world.count_by_id(SOA_ID.REPORT) == 1
        assert world.loot_clicks == [(SOA_ID.REPORT, 'Take')]


def test_arrav_report_rejected_pickup_is_failure_without_waiting():
    with CollectionWorld() as world:
        world.drops = [LootItem(world, SOA_ID.REPORT)]
        world.accept_loot = False
        assert world.kill() is False
        assert world.waits == [] and world.attacks == 0


def test_arrav_report_missing_inventory_arrival_times_out():
    with CollectionWorld() as world:
        world.drops = [LootItem(world, SOA_ID.REPORT)]
        world.loot_lands = False
        assert world.kill() is False
        assert world.now == 6000 and world.count_by_id(SOA_ID.REPORT) == 0


def test_arrav_report_unreachable_message_ends_pickup_wait_early():
    with CollectionWorld() as world:
        world.drops = [LootItem(world, SOA_ID.REPORT)]
        world.loot_lands = False
        world.take_refusal = True
        assert world.kill() is False
        assert world.now == 0 and world.waits == []


def test_arrav_missing_jonny_walks_to_inn_before_retry():
    for walked in [True, False]:
        with CollectionWorld() as world:
            world.targets = []
            world.can_walk = walked
            assert world.kill() == walked
            assert world.walks[0][0] == SOA_TILE.JONNY
            assert world.walks[0][1]['radius'] == 3
            assert world.attacks == 0


def test_arrav_jonny_combat_waits_for_death_and_runs_upkeep():
    with CollectionWorld() as world:
        assert world.kill()
        assert world.attacks == 1 and world.styles == ['strength']
        assert world.sustain_calls >= 2 and world.targets == []
        assert world.logs[-1] == 'Jonny the beard died'
        assert world.count_by_id(SOA_ID.REPORT) == 0


def test_arrav_rejected_jonny_attack_is_failure_without_waiting():
    with CollectionWorld() as world:
        world.accept_attack = False
        assert world.kill() is False
        assert world.attacks == 1 and world.waits == []


def test_arrav_jonny_combat_interrupt_stops_without_waiting_for_death():
    with CollectionWorld() as world:
        world.interrupted = True
        assert world.kill() is False
        assert world.attacks == 1 and world.waits == []


def test_arrav_jonny_fight_is_bounded_when_target_never_dies():
    with CollectionWorld() as world:
        world.jonny_dies = False
        assert world.kill() is False
        assert world.now == phoenix.KILL_MS
        assert 'outlived' in world.logs[-1]


def test_arrav_join_phoenix_uses_straven_preferred_dialogue():
    with CollectionWorld() as world:
        world.talk_pages = [('options', ['Leave', "I'd like to offer you my services."])]
        assert world.run(phoenix.join_phoenix_gang(world.logs.append))
        assert world.talks[0][0] == 'Straven' and world.clicks == [111]


def test_arrav_report_handin_requires_report_to_leave_pack():
    for consumed in [True, False]:
        with CollectionWorld() as world:
            world.carry(SOA_ID.REPORT)
            world.report_consumed = consumed
            world.talk_pages = [('continue', ['Thank you for the report'])]
            assert world.run(phoenix.hand_in_report(world.logs.append)) == consumed
            assert world.count_by_id(SOA_ID.REPORT) == (0 if consumed else 1)


def test_arrav_report_handin_failed_dialogue_retains_report():
    with CollectionWorld() as world:
        world.carry(SOA_ID.REPORT)
        world.talk_status = 'timeout'
        assert world.run(phoenix.hand_in_report(world.logs.append)) is False
        assert world.count_by_id(SOA_ID.REPORT) == 1


def test_arrav_both_halves_open_exact_container_search_then_leave():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            assert world.half(gang)
            assert world.count_by_id(half_id(gang)) == 1
            assert world.loc_requests[0][1] == 'Open'
            assert world.loc_requests[1][1] == 'Search'
            expected = SOA_LOC.CHEST_OPEN if gang == 'phoenix' else SOA_LOC.CUPBOARD_OPEN
            assert world.loc_requests[1][3]['id'] == expected
            if gang == 'phoenix':
                assert world.position == SOA_TILE.HQ_SURFACE
            else:
                assert world.position == SOA_TILE.BLACKARM_DOOR


def test_arrav_halves_already_held_still_leave_sealed_pockets():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.position = SOA_TILE.CHEST_STAND if gang == 'phoenix' else SOA_TILE.BLACKARM_STAIRS_TOP
            world.carry(half_id(gang))
            assert world.half(gang)
            assert world.loc_requests == [] and len(world.interactions) > 0


def test_arrav_halves_failed_entry_does_not_open_container():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.ladder_lands_on = None
            world.rejected = [SOA_LOC.BLACKARM_DOOR]
            assert world.half(gang) is False
            assert world.loc_requests == []


def test_arrav_halves_failed_container_open_still_leaves_hideout():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.container_opens = False
            assert world.half(gang) is False
            assert len(world.loc_requests) == 3
            assert all([request[1] == 'Open' for request in world.loc_requests])
            assert world.position == (SOA_TILE.HQ_SURFACE if gang == 'phoenix' else SOA_TILE.BLACKARM_DOOR)


def test_arrav_empty_containers_close_modal_log_reason_and_leave():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.search_result = 'empty'
            assert world.half(gang) is False
            assert world.count_by_id(half_id(gang)) == 0
            assert world.clicks == ['close'] and not world.pages
            assert any(['already held or banked' in line for line in world.logs])


def test_arrav_silent_container_searches_fail_without_claiming_empty():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.search_result = 'silent'
            assert world.half(gang) is False
            assert any(['search landed nothing' in line for line in world.logs])
            assert not any(['already held or banked' in line for line in world.logs])


def test_arrav_new_half_remains_success_when_exit_must_be_retried():
    for gang in ['phoenix', 'blackarm']:
        with CollectionWorld() as world:
            world.ladder_lands_on = 1
            world.rejected = [SOA_LOC.BLACKARM_STAIRS_TOP]
            # Entry's first ladder works; the exit cannot reach the surface.
            if gang == 'phoenix':
                world.position = SOA_TILE.CHEST_STAND
                world.ladder_lands_on = None
            assert world.half(gang)
            assert world.count_by_id(half_id(gang)) == 1
            assert 'retrying next pass' in world.logs[-1]

"""Weapon-store raids confirm unlocking, combat clearance, and two separate crossbow pickups."""

import rs2004.quests.defs.shieldofarrav.blackarm as blackarm
from rs2004 import execution
from rs2004.geometry import Tile
from helpers import FakeModule
from test_arrav_collection_workflows import CollectionWorld, LootItem, Jonny, SOA_ID, SOA_LOC, SOA_TILE
from test_arrav_hideout_workflows import RouteLoc


class StoreKey(LootItem):
    def use_on(self, target):
        self.world.key_uses.append((self.id, target.id))
        if not self.world.accept_key:
            self.world.messages.append(FakeModule(text='The lock will not turn.'))
            return False
        if self.world.unlock_lands:
            self.world.pending_position = SOA_TILE.STORE_DOOR_INNER
        if self.world.unlock_message:
            self.world.messages.append(FakeModule(text=blackarm.UNLOCKED))
        return True


class Crossbow(LootItem):
    def __init__(self, world, spawn):
        LootItem.__init__(self, world, SOA_ID.CROSSBOW)
        self.spawn = spawn

    def distance(self):
        return self.spawn.distance_to(self.world.position)

    def interact(self, op):
        accepted = LootItem.interact(self, op)
        if accepted and self.world.loot_lands:
            self.world.drops.remove(self)
        return accepted


class Weaponsmaster(Jonny):
    id = blackarm.WEAPONSMASTER_NPC

    def __init__(self, world, distance=1):
        Jonny.__init__(self, world)
        self.dist = distance

    def distance(self):
        return self.dist


class StoreWorld(CollectionWorld):
    def __init__(self):
        CollectionWorld.__init__(self)
        self.accept_key = True
        self.unlock_lands = True
        self.unlock_message = False
        self.escapes = False
        self.walk_results = []
        self.targets = [Weaponsmaster(self)]
        self.drops = [Crossbow(self, SOA_TILE.CROSSBOW_WEST), Crossbow(self, SOA_TILE.CROSSBOW_EAST)]
        self.locations.append(RouteLoc(self, SOA_LOC.STORE_LADDER, 'Ladder', 'Climb-up', SOA_TILE.STORE_LADDER_TOP))

    def carry(self, id):
        if id == SOA_ID.STORE_KEY:
            self.pack.append(StoreKey(self, id))
        else:
            CollectionWorld.carry(self, id)

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        arrived = self.walk_results.pop(0) if self.walk_results else self.can_walk
        if arrived:
            self.position = tile
        return arrived

    def advance(self):
        CollectionWorld.advance(self)
        if self.escapes and self.attacks > 0:
            for target in self.targets:
                target.dist = blackarm.MASTER_BLOCK + 1

    def unlock(self):
        return self.run(blackarm.unlock_store(self.logs.append))

    def clear(self):
        return self.run(blackarm.clear_weaponsmaster(self.logs.append))

    def take(self, spawn=None):
        at = SOA_TILE.CROSSBOW_WEST if spawn is None else spawn
        return self.run(blackarm.take_crossbow(at, self.logs.append))

    def raid(self):
        return self.run(blackarm.raid_weapon_store(self.logs.append))


def test_store_unlock_already_on_either_floor_skips_key_use():
    for position in [SOA_TILE.STORE_LADDER, SOA_TILE.STORE_LADDER_TOP]:
        with StoreWorld() as world:
            world.position = position
            assert world.unlock()
            assert world.key_uses == [] and world.waits == []


def test_store_unlock_uses_key_on_exact_door_and_confirms_inside():
    with StoreWorld() as world:
        world.carry(SOA_ID.STORE_KEY)
        assert world.unlock()
        assert world.key_uses == [(SOA_ID.STORE_KEY, SOA_LOC.STORE_DOOR)]
        assert blackarm.in_store_ground(world.position)
        assert world.waits[-1].count == 2
        assert world.count_by_id(SOA_ID.STORE_KEY) == 1


def test_store_unlock_missing_key_or_rejected_use_is_failure():
    for missing in [True, False]:
        with StoreWorld() as world:
            if not missing:
                world.carry(SOA_ID.STORE_KEY)
                world.accept_key = False
            assert world.unlock() is False
            assert 'store door refused the key:' in world.logs[-1]
            if not missing:
                assert 'The lock will not turn.' in world.logs[-1]


def test_store_unlock_message_alone_does_not_prove_entry():
    with StoreWorld() as world:
        world.carry(SOA_ID.STORE_KEY)
        world.unlock_lands = False
        world.unlock_message = True
        assert world.unlock() is False
        assert not blackarm.in_store_ground(world.position)
        assert world.now < 5000


def test_store_unlock_no_arrival_or_message_times_out():
    with StoreWorld() as world:
        world.carry(SOA_ID.STORE_KEY)
        world.unlock_lands = False
        assert world.unlock() is False
        assert world.now >= 30000


def test_store_clear_master_missing_or_out_of_range_skips_attack():
    for missing in [True, False]:
        with StoreWorld() as world:
            world.targets = [] if missing else [Weaponsmaster(world, distance=11)]
            assert world.clear()
            assert world.attacks == 0 and world.styles == [] and world.waits == []


def test_store_clear_master_at_boundary_attacks_then_waits_for_death():
    with StoreWorld() as world:
        world.targets = [Weaponsmaster(world, distance=10)]
        assert world.clear()
        assert world.attacks == 1 and world.styles == ['strength']
        assert world.targets == [] and world.logs[-1] == 'the Weaponsmaster is down'
        assert world.sustain_calls >= 2


def test_store_clear_master_leaving_refusal_radius_also_allows_pickups():
    with StoreWorld() as world:
        world.jonny_dies = False
        world.escapes = True
        assert world.clear()
        assert len(world.targets) == 1 and world.targets[0].distance() == 11


def test_store_clear_master_rejected_attack_and_interrupt_stop_early():
    for rejected in [True, False]:
        with StoreWorld() as world:
            world.accept_attack = not rejected
            world.interrupted = not rejected
            assert world.clear() is False
            assert world.attacks == 1 and world.waits == []


def test_store_clear_master_fight_is_bounded():
    with StoreWorld() as world:
        world.jonny_dies = False
        assert world.clear() is False
        assert world.now == blackarm.KILL_MS
        assert 'outlived' in world.logs[-1]


def test_store_take_crossbow_walks_to_spawn_and_waits_for_inventory():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        assert world.take()
        assert world.count_by_id(SOA_ID.CROSSBOW) == 1
        assert world.walks[0][0] == SOA_TILE.CROSSBOW_WEST
        assert world.walks[0][1]['radius'] == 1 and world.walks[0][1]['timeout_ms'] == 30000


def test_store_take_crossbow_failed_walk_does_not_click():
    with StoreWorld() as world:
        world.can_walk = False
        assert world.take() is False
        assert world.loot_clicks == []


def test_store_take_crossbow_ignores_wrong_item_and_distant_spawn():
    with StoreWorld() as world:
        world.drops = [LootItem(world, SOA_ID.REPORT), Crossbow(world, Tile(3300, 3383, 1))]
        assert world.take() is False
        assert world.loot_clicks == []
        assert 'no crossbow on the floor' in world.logs[-1]


def test_store_take_crossbow_rejected_or_unacknowledged_pickup_fails():
    for rejected in [True, False]:
        with StoreWorld() as world:
            world.accept_loot = not rejected
            world.loot_lands = False
            assert world.take() is False
            assert world.count_by_id(SOA_ID.CROSSBOW) == 0
            if not rejected:
                assert world.now >= 6000


def test_store_second_crossbow_must_increase_existing_count():
    with StoreWorld() as world:
        world.carry(SOA_ID.CROSSBOW)
        world.loot_lands = False
        assert world.take() is False
        assert world.count_by_id(SOA_ID.CROSSBOW) == 1 and world.now >= 6000


def test_store_raid_unlocks_climbs_fights_takes_two_and_exits():
    with StoreWorld() as world:
        world.carry(SOA_ID.STORE_KEY)
        assert world.raid()
        assert world.count_by_id(SOA_ID.CROSSBOW) == 2 and world.drops == []
        assert world.attacks == 1 and world.key_uses == [(SOA_ID.STORE_KEY, SOA_LOC.STORE_DOOR)]
        assert world.interactions == [(SOA_LOC.STORE_LADDER, 'Climb-up'),
                                      (SOA_LOC.STORE_LADDER_TOP, 'Climb-down'), (SOA_LOC.STORE_DOOR, 'Open')]
        assert world.position == SOA_TILE.STORE_DOOR


def test_store_raid_already_holds_two_crossbows_only_leaves():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.carry(SOA_ID.CROSSBOW)
        world.carry(SOA_ID.CROSSBOW)
        assert world.raid()
        assert world.attacks == 0 and world.loot_clicks == [] and world.key_uses == []
        assert world.position == SOA_TILE.STORE_DOOR


def test_store_raid_with_one_crossbow_takes_only_one_more():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.carry(SOA_ID.CROSSBOW)
        assert world.raid()
        assert len(world.loot_clicks) == 1 and world.count_by_id(SOA_ID.CROSSBOW) == 2


def test_store_raid_already_upstairs_skips_unlock_and_entry_ladder():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        assert world.raid()
        assert world.key_uses == []
        assert (SOA_LOC.STORE_LADDER, 'Climb-up') not in world.interactions


def test_store_raid_failed_unlock_does_not_fight_or_take():
    with StoreWorld() as world:
        assert world.raid() is False
        assert world.interactions == [] and world.attacks == 0 and world.loot_clicks == []


def test_store_raid_failed_entry_climb_does_not_fight_or_take():
    with StoreWorld() as world:
        world.carry(SOA_ID.STORE_KEY)
        world.rejected = [SOA_LOC.STORE_LADDER]
        assert world.raid() is False
        assert world.attacks == 0 and world.loot_clicks == []


def test_store_raid_failed_combat_does_not_take_crossbows():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.accept_attack = False
        assert world.raid() is False
        assert world.loot_clicks == []


def test_store_raid_missing_west_spawn_still_tries_east_then_retries_later():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.drops = [Crossbow(world, SOA_TILE.CROSSBOW_EAST)]
        assert world.raid() is False
        assert world.count_by_id(SOA_ID.CROSSBOW) == 1
        assert any(['not taken this pass' in line for line in world.logs])
        assert blackarm.in_weapon_store(world.position)


def test_store_raid_failed_exit_is_reported_with_both_crossbows_retained():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.rejected = [SOA_LOC.STORE_LADDER_TOP]
        assert world.raid() is False
        assert world.count_by_id(SOA_ID.CROSSBOW) == 2


def test_store_raid_with_crossbows_reports_failed_exit_on_next_pass_too():
    with StoreWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.carry(SOA_ID.CROSSBOW)
        world.carry(SOA_ID.CROSSBOW)
        world.rejected = [SOA_LOC.STORE_DOOR]
        assert world.raid() is False
        assert world.loot_clicks == [] and world.attacks == 0

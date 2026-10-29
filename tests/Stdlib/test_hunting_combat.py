"""Combat tasks over a simulated scene, with movement and deaths arriving on updates."""

import rs2004.hunting.combat as combat
from rs2004 import execution
from rs2004.entities import EntityQuery
from rs2004.geometry import Tile
from helpers import FakeModule
from test_hunting_supply import SupplyWorld


class Target:
    def __init__(self, world, index, name='Black dragon', x=3002):
        self.world = world
        self.index = index
        self.id = 50
        self.name = name
        self.position = Tile(x, 3000)
        self.size = 1
        self.in_combat = False
        self.mine = False
        self.other = False
        self.health = 100
        self.max_health = 100
        self.accept = True

    def tile(self):
        return self.position

    def network_tile(self):
        return self.position

    def distance(self):
        return self.world.position.distance_to(self.position)

    def actions(self):
        return ['Attack']

    def targets_me(self):
        return self.mine

    def targets_another_player(self):
        return self.other

    def interact(self, op):
        assert op == 'Attack'
        self.world.attacks.append(self.index)
        if self.accept and self.world.kill_on_attack:
            self.world.pending_death = self
        return self.accept


class CombatWorld(SupplyWorld):
    def __init__(self):
        SupplyWorld.__init__(self)
        self.now = 20000
        self.hp = 100
        self.style = 'range'
        self.spot_index = 0
        self.has_food = True
        self.shield_ready = True
        self.ready = True
        self.interrupted = False
        self.dialogue = False
        self.can_walk = True
        self.can_see = True
        self.can_reach = True
        self.scene = []
        self.walks = []
        self.attacks = []
        self.pending_walk = None
        self.pending_death = None
        self.kill_on_attack = False
        self.counted_kills = 0
        self.host.style = lambda: self.style
        self.host.safespot_index = lambda: self.spot_index
        self.host.set_safespot_index = self.set_spot
        self.host.hp_fraction = lambda: self.hp / 100
        self.host.panic_hp = lambda: 0.2
        self.host.retreat_hp = lambda: 0.6
        self.host.has_food = lambda: self.has_food
        self.host.need_eat = lambda: False
        self.host.shield_ready = lambda: self.shield_ready
        self.host.bury_bones = lambda: False
        self.host.count_kill = self.count_kill
        self.host.died = False
        self.host.target_idx = None
        self.site.key = 'test-black-dragons'
        self.site.target = 'Black dragon'
        self.site.also_hunt = []
        self.site.melee_anchor = Tile(3000, 3000)
        self.site.safespots = [Tile(3000, 3000), Tile(3000, 3004)]
        self.site.ranged_threat = False
        self.site.approach = []
        self.site.in_area = lambda tile: tile is not None and 2990 <= tile.x <= 3040

    def __enter__(self):
        SupplyWorld.__enter__(self)
        replacements = {
            '_core': self,
            'game': FakeModule(tile=lambda: self.position, scene_ready=lambda: self.ready, facing=lambda: None),
            'skills': FakeModule(effective=lambda name: self.hp),
            'npcs': FakeModule(all=lambda: self.scene, query=lambda: EntityQuery(self.entities, lambda n: True)),
            'reachability': FakeModule(line_of_sight=lambda *args: self.can_see,
                                       can_reach=lambda *args, **kwargs: self.can_reach),
            'direct_navigator': FakeModule(walk=self.walk),
            'traversal': FakeModule(walk_resilient=self.walk_resilient),
            'event_signal': FakeModule(pending=lambda: self.interrupted),
            'chat_dialog': FakeModule(can_continue=lambda: self.dialogue),
        }
        self.combat_saved = {}
        for name, value in replacements.items():
            self.combat_saved[name] = getattr(combat, name)
            setattr(combat, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.combat_saved.items():
            setattr(combat, name, value)
        SupplyWorld.__exit__(self, *args)

    def set_spot(self, index):
        self.spot_index = index

    def count_kill(self):
        self.counted_kills += 1

    def entities(self, ids, names, radius, layer):
        return [n for n in self.scene if (ids is None or n.id in ids)
                and (names is None or n.name in names) and (radius is None or n.distance() <= radius)]

    def walk(self, tile):
        self.walks.append(tile)
        if self.can_walk:
            self.pending_walk = tile
        return self.can_walk

    def walk_resilient(self, tile, **kwargs):
        self.walk(tile)
        yield execution.Ticks(1)
        return self.can_walk

    def advance(self):
        SupplyWorld.advance(self)
        if self.pending_walk is not None:
            self.position = self.pending_walk
            self.pending_walk = None
        if self.pending_death is not None:
            self.scene.remove(self.pending_death)
            self.pending_death = None

    def dragon(self, index=1, name='Black dragon', x=3002):
        target = Target(self, index, name, x)
        self.scene.append(target)
        return target


def test_field_excludes_other_players_combat_but_keeps_our_flickering_target():
    with CombatWorld() as world:
        free = world.dragon(1)
        busy = world.dragon(2)
        busy.in_combat = True
        ours = world.dragon(3)
        ours.in_combat = True
        taken = world.dragon(4)
        taken.other = True
        fight = combat.Fight(world.host, world.site)
        fight.engaged = ours.index
        assert fight._field(10) == [free, ours]
        busy.mine = True
        assert fight._field(10) == [free, busy, ours]


def test_field_requires_sight_and_range_and_stays_inside_site():
    with CombatWorld() as world:
        near = world.dragon(1)
        world.dragon(2, x=3020)
        outside = world.dragon(3, x=2989)
        fight = combat.Fight(world.host, world.site)
        assert fight._field(10) == [near]
        world.can_see = False
        assert fight._field(10) == []
        world.style = 'melee'
        assert fight._field(20) == world.scene[:2]
        assert outside not in fight._field(20)


def test_filler_is_used_during_downtime_and_kept_if_already_fighting_us():
    with CombatWorld() as world:
        world.site.also_hunt = ['Greater demon']
        filler = world.dragon(2, 'Greater demon')
        fight = combat.Fight(world.host, world.site)
        assert fight._field(10) == [filler]
        primary = world.dragon(1)
        assert fight._field(10) == [primary]
        filler.mine = True
        assert fight._field(10) == [filler, primary]
        filler.mine = False
        fight.engaged = filler.index
        assert fight._field(10) == [filler, primary]


def test_fight_validates_only_with_shield_health_and_fight_position():
    with CombatWorld() as world:
        world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert fight.validate()
        world.shield_ready = False
        assert not fight.validate()
        world.shield_ready = True
        world.hp = 19
        assert not fight.validate()
        world.hp = 100
        world.position = Tile(3001, 3000)
        assert not fight.validate()
        world.position = None
        assert not fight.validate()


def test_fight_counts_a_confirmed_kill_once_and_releases_loot():
    with CombatWorld() as world:
        world.dragon()
        world.kill_on_attack = True
        fight = combat.Fight(world.host, world.site)
        world.run(fight.execute())
        assert world.attacks == [1]
        assert world.counted_kills == 1
        assert fight.killed_spawns == {1: 1}
        assert fight.engaged is None and world.host.target_idx is None
        assert not fight.blocks_loot()
        assert not fight._settle_kill('black dragon')
        assert world.counted_kills == 1


def test_stale_disappearance_after_bank_trip_does_not_count_as_kill():
    with CombatWorld() as world:
        fight = combat.Fight(world.host, world.site)
        fight._set_target(1)
        world.now += combat.KILL_GRACE_MS
        assert fight._settle_kill('black dragon')
        assert world.counted_kills == 0
        assert fight.kills == 0
        assert fight.loot_target is None


def test_live_target_keeps_loot_blocked_until_its_disappearance():
    with CombatWorld() as world:
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        fight._set_target(target.index)
        assert not fight._settle_kill('black dragon')
        assert fight.blocks_loot()
        fight._clear_target()
        assert fight.blocks_loot()
        world.scene = []
        assert not fight.blocks_loot()
        world.ready = False
        assert fight.blocks_loot()


def test_refused_attack_is_skipped_without_claiming_target():
    with CombatWorld() as world:
        target = world.dragon()
        target.accept = False
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._engage(target, 'black dragon')) is False
        assert world.attacks == [1]
        assert fight.skip[1] > world.now
        assert fight.engaged is None and world.host.target_idx is None


def test_engage_rechecks_target_ownership_and_shield_before_clicking():
    with CombatWorld() as world:
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        target.other = True
        assert world.run(fight._engage(target, 'black dragon')) is False
        target.other = False
        world.shield_ready = False
        assert world.run(fight._engage(target, 'black dragon')) is False
        world.shield_ready = True
        world.scene = []
        assert world.run(fight._engage(target, 'black dragon')) is False
        assert world.attacks == []


def test_fight_hands_back_immediately_on_interrupt_dialogue_or_death():
    for reason in ['interrupted', 'dialogue', 'died', 'scene']:
        with CombatWorld() as world:
            world.dragon()
            fight = combat.Fight(world.host, world.site)
            world.interrupted = reason == 'interrupted'
            world.dialogue = reason == 'dialogue'
            world.host.died = reason == 'died'
            world.ready = reason != 'scene'
            world.run(fight.execute())
            assert world.attacks == [] and world.walks == []


def test_foodless_fight_at_ranged_threat_hands_back_without_attacking():
    with CombatWorld() as world:
        world.dragon()
        world.site.ranged_threat = True
        world.has_food = False
        world.run(combat.Fight(world.host, world.site).execute())
        assert world.attacks == []


def test_hurt_on_safespot_rotates_and_walks_to_next_tile():
    with CombatWorld() as world:
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._ladder()) == 'held'
        fight.skip[7] = world.now + 5000
        world.hp = 80
        assert world.run(fight._ladder()) == 'moved'
        assert world.spot_index == 1
        assert world.position.equals(world.site.safespots[1])
        assert fight.skip == {}


def test_expected_ranged_damage_does_not_rotate_safespot():
    with CombatWorld() as world:
        world.site.ranged_threat = True
        fight = combat.Fight(world.host, world.site)
        world.run(fight._ladder())
        world.hp = 80
        assert world.run(fight._ladder()) == 'held'
        assert world.spot_index == 0 and world.walks == []


def test_long_gap_in_fight_polls_resets_blind_timer():
    with CombatWorld() as world:
        fight = combat.Fight(world.host, world.site)
        fight._watch(True)
        world.now += combat.SAFESPOT_BLIND_MS
        assert fight._blind_due()
        fight._watch(True)
        assert not fight._blind_due()
        world.set_spot(1)
        fight._watch(True)
        assert fight.watched_anchor.equals(world.site.safespots[1])
        fight._watch(False)
        assert fight.watched_anchor is None


def test_retreat_moves_to_nearest_safespot_before_healing():
    with CombatWorld() as world:
        world.position = Tile(3001, 3003)
        world.hp = 40
        task = combat.Retreat(world.host, world.site)
        assert task.validate()
        world.run(task.execute())
        assert world.spot_index == 1
        assert world.position.equals(world.site.safespots[1])
        assert not task.validate()
        assert len(world.walks) == 1


def test_blocked_retreat_rotates_and_waits_before_retrying():
    with CombatWorld() as world:
        world.position = Tile(3001, 3000)
        world.hp = 40
        world.can_walk = False
        task = combat.Retreat(world.host, world.site)
        world.run(task.execute())
        assert len(world.walks) == combat.RETREAT_HOPS
        assert task.rotated == 1 and world.spot_index == 1
        assert not task.validate()
        world.now = task.retry_at
        assert task.validate()
        world.can_walk = True
        world.run(task.execute())
        assert world.position.equals(world.site.safespots[1])


def test_foodless_retreat_is_due_even_above_heal_threshold():
    with CombatWorld() as world:
        world.position = Tile(3002, 3000)
        world.has_food = False
        task = combat.Retreat(world.host, world.site)
        assert task.validate()
        world.run(task.execute())
        assert world.position.equals(world.site.safespots[0])
        assert not task.validate()


def test_hold_safespot_rotates_only_if_walk_did_not_arrive():
    for arrives in [True, False]:
        with CombatWorld() as world:
            world.position = Tile(3001, 3000)
            world.can_walk = arrives
            task = combat.HoldSafespot(world.host, world.site)
            assert task.validate()
            world.run(task.execute())
            assert world.spot_index == (0 if arrives else 1)
            assert len(world.walks) == 1


def test_foodless_hold_does_not_leave_a_safe_tile_for_melee_anchor():
    with CombatWorld() as world:
        world.style = 'melee'
        world.position = world.site.safespots[1]
        world.has_food = False
        task = combat.HoldSafespot(world.host, world.site)
        assert not task.validate()
        world.has_food = True
        assert task.validate()


def test_walk_to_spot_respects_distance_health_and_active_chase():
    with CombatWorld() as world:
        task = combat.WalkToSpot(world.host, world.site)
        world.position = Tile(3020, 3000)
        assert task.validate()
        world.hp = 19
        assert not task.validate()
        world.hp = 100
        world.style = 'melee'
        world.site.fire_at_range = True
        world.host.target_idx = 1
        assert not task.validate()
        assert not combat.HoldSafespot(world.host, world.site).validate()
        world.host.target_idx = None
        assert task.validate()
        world.run(task.execute())
        assert world.position.equals(world.site.melee_anchor)
        assert not task.validate()


def test_walk_to_spot_reports_when_walk_stops_short():
    with CombatWorld() as world:
        world.position = Tile(3020, 3000)
        world.can_walk = False
        world.run(combat.WalkToSpot(world.host, world.site).execute())
        assert 'stopped short' in world.logs[-1]
        assert world.position.equals(Tile(3020, 3000))


def test_fight_drops_a_target_taken_by_another_player():
    with CombatWorld() as world:
        target = world.dragon()
        target.other = True
        fight = combat.Fight(world.host, world.site)
        fight._set_target(target.index)
        world.run(fight.execute())
        assert fight.engaged is None
        assert world.host.target_idx is None
        assert fight.skip[target.index] > world.now
        assert world.attacks == [] and world.counted_kills == 0


def test_chase_abandons_target_that_has_taken_no_damage_for_timeout():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.fire_at_range = True
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        fight._set_target(target.index)
        world.now += combat.CHASE_STALL_MS + 1
        world.run(fight.execute())
        assert fight.engaged is None
        assert fight.skip[target.index] > world.now
        assert world.attacks == [] and world.counted_kills == 0
        assert 'took no damage' in world.logs[0]


def test_failed_chase_walk_skips_unreachable_target_without_attack():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.fire_at_range = True
        world.can_reach = False
        world.can_walk = False
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._engage(target, 'black dragon')) is False
        assert len(world.walks) == 1
        assert fight.skip[target.index] > world.now
        assert world.attacks == []


def test_chase_rechecks_reachability_after_walk_before_attack():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.fire_at_range = True
        world.can_reach = False
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._engage(target, 'black dragon')) is False
        assert world.position.equals(target.position)
        assert world.attacks == []


def test_special_attack_that_removes_shield_prevents_attack_click():
    with CombatWorld() as world:
        def arm():
            yield execution.Ticks(1)
            world.shield_ready = False

        world.host.arm_special = arm
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._engage(target, 'black dragon')) is False
        assert world.attacks == []
        assert world.host.target_idx is None


def test_walk_back_bounds_attempts_when_anchor_is_blocked():
    with CombatWorld() as world:
        world.position = Tile(3001, 3000)
        world.can_walk = False
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._walk_back()) is False
        assert len(world.walks) == combat.HOP_ATTEMPTS
        assert 'Handing back to the walk-back task' in world.logs[-1]


def test_walk_back_does_not_move_during_event_interrupt():
    with CombatWorld() as world:
        world.position = Tile(3001, 3000)
        world.interrupted = True
        assert world.run(combat.Fight(world.host, world.site)._walk_back()) is False
        assert world.walks == []


def test_melee_defends_against_baby_dragon_only_when_it_attacks_us():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.key = combat.TAVERLEY_BLUE.key
        world.site.target = 'Blue dragon'
        adult = world.dragon(1, 'Blue dragon')
        baby = world.dragon(2, 'Baby blue dragon')
        fight = combat.Fight(world.host, world.site)
        assert fight._field(10) == [adult]
        baby.mine = True
        assert fight._field(10) == [baby, adult]


def test_chase_target_checks_ignore_dying_and_temporarily_skipped_dragons():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.fire_at_range = True
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert fight.has_chase_target()
        fight.skip[target.index] = world.now + 1000
        assert not fight.has_chase_target()
        world.now += 1001
        assert fight.has_chase_target()
        target.health = 0
        assert not fight.has_chase_target()


def test_walk_tasks_do_not_interrupt_an_available_chase_target():
    with CombatWorld() as world:
        world.style = 'melee'
        world.site.fire_at_range = True
        world.position = Tile(3020, 3000)
        world.dragon(x=3021)
        world.host.fight = combat.Fight(world.host, world.site)
        assert not combat.HoldSafespot(world.host, world.site).validate()
        assert not combat.WalkToSpot(world.host, world.site).validate()

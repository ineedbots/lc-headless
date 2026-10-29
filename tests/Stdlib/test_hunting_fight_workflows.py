"""Fight loops react to changing health, retaliation and safespot reachability."""

import rs2004.hunting.combat as combat
from rs2004 import execution
from rs2004.geometry import Tile
from test_hunting_combat import CombatWorld


class FightWorld(CombatWorld):
    def __init__(self):
        CombatWorld.__init__(self)
        self.after_update = None
        self.stop_at = self.now + 6000
        self.host.vlog = self.logs.append
        self.face = None

    def __enter__(self):
        CombatWorld.__enter__(self)
        combat.game.facing = lambda: self.face
        return self

    def advance(self):
        CombatWorld.advance(self)
        if self.after_update is not None:
            self.after_update()
        if self.stop_at is not None and self.now >= self.stop_at:
            self.ready = False


def test_fight_eat_failure_and_panic_stop_before_attack():
    for failure in ['eat', 'panic', 'retreat', 'empty']:
        with FightWorld() as world:
            world.dragon()
            if failure == 'eat':
                world.host.need_eat = lambda: True
                def eat():
                    yield execution.Ticks(1)
                    return False
                world.host.eat_once = eat
            elif failure == 'panic':
                world.hp = 10
            elif failure == 'retreat':
                world.hp, world.has_food = 30, False
                world.site.ranged_threat = True
            else:
                world.has_food, world.site.ranged_threat = False, True
            world.run(combat.Fight(world.host, world.site).execute())
            assert world.attacks == []


def test_fight_repeated_engagement_logs_reissue_and_tracks_health_drop():
    with FightWorld() as world:
        target = world.dragon()
        fight = combat.Fight(world.host, world.site)
        assert world.run(fight._engage(target, 'black dragon'))
        assert world.run(fight._engage(target, 'black dragon'))
        assert fight.reissues == 1 and 'Re-issuing' in world.logs[-1]
        fight.engaged_health = 100
        target.health = 90
        world.stop_at = world.now + 2000
        world.run(fight.execute())
        assert fight.damaged_at > 0 and fight.engaged_health == 90


def test_fight_adopts_reachable_retaliation_target():
    with FightWorld() as world:
        target = world.dragon(1)
        world.face = ('npc', 1)
        fight = combat.Fight(world.host, world.site)
        world.run(fight.execute())
        assert fight.engaged == target.index
        assert any(['retaliating' in line for line in world.logs])


def test_fight_melee_adopts_attacker_and_keeps_dying_target_instead_of_switching():
    with FightWorld() as world:
        world.style, world.site.fire_at_range = 'melee', True
        target = world.dragon()
        target.mine = True
        fight = combat.Fight(world.host, world.site)
        world.run(fight.execute())
        assert world.attacks and fight.engaged == target.index
        target.health = 0
        world.ready, world.stop_at = True, world.now + 1000
        before = len(world.attacks)
        world.run(fight.execute())
        assert len(world.attacks) == before


def test_fight_out_of_range_retaliation_reclicks_our_chosen_target():
    with FightWorld() as world:
        target = world.dragon(1)
        world.dragon(2, x=3020)
        world.face = ('npc', 2)
        fight = combat.Fight(world.host, world.site)
        fight._set_target(1)
        fight.engaged_name = 'black dragon'
        world.run(fight.execute())
        assert world.attacks and all([index == 1 for index in world.attacks])
        assert any(['beyond reach' in line for line in world.logs])


def test_fight_diagnostics_explain_visible_but_unavailable_targets():
    with FightWorld() as world:
        world.dragon().other = True
        fight = combat.Fight(world.host, world.site)
        fight._explain_empty_field(world.now)
        assert 'other y' in world.logs[-1]
        world.scene = []
        before = len(world.logs)
        fight._explain_empty_field(world.now + combat.FIELD_DIAG_MS)
        assert len(world.logs) == before


def test_fight_spawn_rotation_ranks_never_killed_target_first():
    with FightWorld() as world:
        world.host.rotate_spawns = lambda: True
        first, second = world.dragon(1), world.dragon(2, x=3003)
        fight = combat.Fight(world.host, world.site)
        fight.killed_spawns[1] = 1
        world.run(fight.execute())
        assert world.attacks[0] == second.index


def test_fight_blue_range_field_keeps_only_engaged_target_and_expires_blind_target():
    with FightWorld() as world:
        world.site.key, world.site.target = combat.TAVERLEY_BLUE.key, 'Blue dragon'
        target = world.dragon(name='Blue dragon')
        world.dragon(2, 'Blue dragon')
        fight = combat.Fight(world.host, world.site)
        fight._set_target(1)
        assert fight._field(10) == [target]
        world.can_see = False
        fight.watched_anchor, fight.polled_at, fight.blind_since = world.position, world.now, world.now
        fight.unattackable_since = world.now - combat.SAFESPOT_BLIND_MS
        world.run(fight.execute())
        assert fight.engaged is None and fight.skip[1] > world.now


def test_fight_moves_to_known_black_dragon_safespot_with_target_in_reach():
    with FightWorld() as world:
        world.site.key = combat.TAVERLEY_BLACK.key
        world.site.in_area = lambda tile: True
        world.site.safespots = [Tile(3000, 3000)] + list(combat.TAVERLEY_BLACK.safespots)
        target = world.dragon()
        target.position = world.site.safespots[-1].translate(1, 0)
        fight = combat.Fight(world.host, world.site)
        alternate = fight._alternate()
        assert alternate is not None and alternate > 0
        assert world.run(fight._ladder()) == 'moved'
        assert world.spot_index == alternate and world.position == world.site.safespots[alternate]
        assert fight._alternate() is None


def test_fight_melee_gutanoth_defenders_and_empty_safespot_anchor():
    with FightWorld() as world:
        world.style, world.site.key = 'melee', combat.GUTANOTH_BLUE.key
        world.site.target, world.site.also_hunt = 'Blue dragon', ['Greater demon']
        defender = world.dragon(name='Ogre chieftain')
        defender.mine = True
        fight = combat.Fight(world.host, world.site)
        assert defender in fight._field(10)
        world.site.safespots = []
        assert combat.anchor_for(world.site, 'range', 0) == world.site.melee_anchor


def test_fight_leash_waits_until_target_closes_or_budget_expires():
    for closes in [True, False]:
        with FightWorld() as world:
            target = world.dragon(x=3009)
            fight = combat.Fight(world.host, world.site)
            world.stop_at = None
            if closes:
                world.after_update = lambda: setattr(target, 'position', Tile(3002, 3000))
            assert world.run(fight._leash(target.index)) == closes
            assert world.now <= 20000 + combat.LEASH_MS


def test_fight_leash_interrupt_or_failed_food_hands_back_safely():
    for interrupted in [True, False]:
        with FightWorld() as world:
            world.dragon(x=3009)
            world.interrupted = interrupted
            world.host.need_eat = lambda: True
            def eat():
                yield execution.Ticks(1)
                return False
            world.host.eat_once = eat
            assert world.run(combat.Fight(world.host, world.site)._leash(1))


def test_fight_interrupt_resets_watched_anchor_and_burial_uses_idle_tick():
    with FightWorld() as world:
        fight = combat.Fight(world.host, world.site)
        world.host.fight = fight
        fight.watched_anchor = world.position
        combat._interrupt_fight(world.host)
        assert fight.watched_anchor is None
        saved = combat.bury_one_in_fight
        def bury(name):
            assert name == 'Bones'
            yield execution.Ticks(1)
            return True
        combat.bury_one_in_fight = bury
        world.host.bury_bones = lambda: True
        world.host.bone_name = lambda: 'Bones'
        counts = []
        world.host.count_burial = lambda: counts.append(1)
        world.run(fight._idle())
        combat.bury_one_in_fight = saved
        assert counts == [1]

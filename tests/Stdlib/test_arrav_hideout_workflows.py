"""Arrav hideout routes confirm scene arrivals and leave sealed pockets safely."""

import rs2004.quests.defs.shieldofarrav.hideout as hideout
import rs2004.quests.exec.legs as legs
from rs2004 import execution
from rs2004.geometry import Tile
from helpers import FakeModule
from test_quest_leg_workflows import LegWorld

SOA_LOC = hideout.SOA_LOC
SOA_TILE = hideout.SOA_TILE


class RouteLoc:
    def __init__(self, world, id, name, op, destination):
        self.world = world
        self.id = id
        self.name = name
        self.op = op
        self.destination = destination

    def distance(self):
        return 1

    def actions(self):
        return [self.op]

    def interact(self, op):
        assert op == self.op
        self.world.interactions.append((self.id, op))
        if self.id in self.world.rejected:
            return False
        if self.id in self.world.refused:
            self.world.messages.append(FakeModule(text='The door is locked.'))
            return True
        if self.id not in self.world.unresponsive:
            if self.id == SOA_LOC.PHOENIX_DOOR:
                self.world.pending_position = (SOA_TILE.PHOENIX_DOOR if hideout.in_phoenix_inner(self.world.position)
                                               else SOA_TILE.PHOENIX_DOOR_INNER)
            elif self.id == SOA_LOC.BLACKARM_DOOR:
                self.world.pending_position = (SOA_TILE.BLACKARM_DOOR if hideout.in_black_arm_inner(self.world.position)
                                               else SOA_TILE.BLACKARM_DOOR_INNER)
            else:
                self.world.pending_position = self.destination
        return True


class HideoutWorld(LegWorld):
    def __init__(self):
        LegWorld.__init__(self)
        self.position = SOA_TILE.HQ_SURFACE
        self.pending_position = None
        self.ladder_status = 'retry'
        self.ladder_lands_on = 1
        self.ladder_calls = []
        self.interactions = []
        self.rejected = []
        self.refused = []
        self.unresponsive = []
        self.locations = [
            RouteLoc(self, SOA_LOC.PHOENIX_DOOR, 'Door', 'Open', None),
            RouteLoc(self, SOA_LOC.BLACKARM_DOOR, 'Door', 'Open', None),
            RouteLoc(self, SOA_LOC.STORE_DOOR, 'Door', 'Open', SOA_TILE.STORE_DOOR),
            RouteLoc(self, SOA_LOC.BLACKARM_STAIRS, 'Staircase', 'Climb-up', SOA_TILE.BLACKARM_STAIRS_TOP),
            RouteLoc(self, SOA_LOC.BLACKARM_STAIRS_TOP, 'Staircase', 'Climb-down', SOA_TILE.BLACKARM_STAIRS),
            RouteLoc(self, SOA_LOC.STORE_LADDER_TOP, 'Ladder', 'Climb-down', SOA_TILE.STORE_LADDER),
        ]

    def __enter__(self):
        LegWorld.__enter__(self)
        replacements = {
            'game': legs.game,
            'reach': FakeModule(loc_op=self.ladder),
            'game_messages': FakeModule(mark=lambda: len(self.messages), since=lambda mark: self.messages[mark:]),
        }
        self.hideout_saved = {}
        for name, value in replacements.items():
            self.hideout_saved[name] = getattr(hideout, name)
            setattr(hideout, name, value)
        return self

    def __exit__(self, *args):
        for name, value in self.hideout_saved.items():
            setattr(hideout, name, value)
        LegWorld.__exit__(self, *args)

    def ladder(self, name, op, near, expect, **kwargs):
        self.ladder_calls.append((name, op, near, kwargs))
        if self.ladder_lands_on is not None and len(self.ladder_calls) >= self.ladder_lands_on:
            self.pending_position = SOA_TILE.HQ_LADDER if op == 'Climb-down' else SOA_TILE.HQ_SURFACE
        yield execution.Ticks(1)
        return self.ladder_status

    def walk(self, tile, **kwargs):
        self.walks.append((tile, kwargs))
        yield execution.Ticks(1)
        if self.can_walk:
            self.position = tile
        return self.can_walk

    def advance(self):
        LegWorld.advance(self)
        if self.pending_position is not None:
            self.position = self.pending_position
            self.pending_position = None

    def enter(self):
        return self.run(hideout.enter_hideout(self.logs.append))

    def leave(self):
        return self.run(hideout.leave_hideout(self.logs.append))

    def black_upper(self):
        return self.run(hideout.enter_black_arm_upper(self.logs.append))

    def leave_black(self):
        return self.run(hideout.leave_black_arm_upper(self.logs.append))

    def leave_store(self):
        return self.run(hideout.leave_weapon_store(self.logs.append))


def test_arrav_hideout_already_underground_skips_ladder():
    with HideoutWorld() as world:
        world.position = SOA_TILE.HQ_LADDER
        assert world.enter()
        assert world.ladder_calls == [] and world.waits == []


def test_arrav_hideout_descent_accepts_retry_status_when_arrival_proves_success():
    with HideoutWorld() as world:
        assert world.enter()
        request = world.ladder_calls[0]
        assert request[:3] == ('Ladder', 'Climb-down', SOA_TILE.CELLAR_LADDER)
        assert request[3]['id'] == SOA_LOC.CELLAR_LADDER and request[3]['expect_ms'] == 15000
        assert world.waits[-1].count == 2
        assert world.walks == [] and hideout.in_phoenix_hq(world.position)


def test_arrav_hideout_descent_retries_initial_wrong_side_arrival():
    with HideoutWorld() as world:
        world.ladder_lands_on = 2
        assert world.enter()
        assert len(world.ladder_calls) == 2 and world.logs == []


def test_arrav_hideout_descent_failure_is_bounded_even_with_done_status():
    with HideoutWorld() as world:
        world.ladder_lands_on = None
        world.ladder_status = 'done'
        assert world.enter() is False
        assert len(world.ladder_calls) == 2
        assert world.logs[-1] == "descent into the hideout returned 'done' and left the character on the surface"


def test_arrav_talk_in_hideout_enters_before_driving_dialogue():
    with HideoutWorld() as world:
        world.stop = FakeModule(npc='Straven', anchor=SOA_TILE.HQ_LADDER, leash=6)
        world.talk_pages = [('continue', ['Welcome']), ('options', ['No', 'Yes'])]
        assert world.run(hideout.talk_in_hideout(world.stop, ['Yes'], world.logs.append))
        assert len(world.ladder_calls) == 1
        assert world.talks == [('Straven', SOA_TILE.HQ_LADDER)]
        assert world.clicks == ['continue', 111]


def test_arrav_talk_in_hideout_does_not_talk_after_failed_entry():
    with HideoutWorld() as world:
        world.ladder_lands_on = None
        assert world.run(hideout.talk_in_hideout(world.stop, [], world.logs.append)) is False
        assert world.talks == []


def test_arrav_leave_surface_skips_all_interactions():
    with HideoutWorld() as world:
        assert world.leave()
        assert world.ladder_calls == [] and world.interactions == [] and world.waits == []


def test_arrav_leave_outer_hideout_climbs_and_confirms_surface():
    with HideoutWorld() as world:
        world.position = SOA_TILE.HQ_LADDER
        assert world.leave()
        request = world.ladder_calls[0]
        assert request[:3] == ('Ladder', 'Climb-up', SOA_TILE.HQ_LADDER)
        assert request[3]['id'] == SOA_LOC.HQ_LADDER
        assert world.position == SOA_TILE.HQ_SURFACE and world.interactions == []


def test_arrav_leave_inner_hideout_crosses_gang_door_before_ladder():
    with HideoutWorld() as world:
        world.position = SOA_TILE.CHEST_STAND
        assert world.leave()
        assert world.interactions == [(SOA_LOC.PHOENIX_DOOR, 'Open')]
        assert world.walks[0][0] == SOA_TILE.PHOENIX_DOOR_INNER
        assert len(world.ladder_calls) == 1 and world.position == SOA_TILE.HQ_SURFACE


def test_arrav_failed_inner_door_prevents_exit_ladder():
    with HideoutWorld() as world:
        world.position = SOA_TILE.CHEST_STAND
        world.rejected = [SOA_LOC.PHOENIX_DOOR]
        assert world.leave() is False
        assert world.ladder_calls == [] and hideout.in_phoenix_inner(world.position)


def test_arrav_exit_ladder_done_without_surface_arrival_is_failure():
    with HideoutWorld() as world:
        world.position = SOA_TILE.HQ_LADDER
        world.ladder_lands_on = None
        world.ladder_status = 'done'
        assert world.leave() is False
        assert len(world.ladder_calls) == 1
        assert world.logs[-1] == "climb out of the hideout returned 'done' and left the character underground"


def test_arrav_enter_phoenix_inner_descends_then_crosses_door():
    with HideoutWorld() as world:
        assert world.run(hideout.enter_phoenix_inner(world.logs.append))
        assert len(world.ladder_calls) == 1
        assert world.interactions == [(SOA_LOC.PHOENIX_DOOR, 'Open')]
        assert hideout.in_phoenix_inner(world.position)


def test_arrav_enter_phoenix_inner_already_inside_skips_interactions():
    with HideoutWorld() as world:
        world.position = SOA_TILE.CHEST_STAND
        assert world.run(hideout.enter_phoenix_inner(world.logs.append))
        assert world.ladder_calls == [] and world.interactions == []


def test_arrav_enter_phoenix_inner_failed_descent_does_not_click_door():
    with HideoutWorld() as world:
        world.ladder_lands_on = None
        assert world.run(hideout.enter_phoenix_inner(world.logs.append)) is False
        assert world.interactions == []


def test_arrav_cross_door_logs_only_new_refusal_messages():
    with HideoutWorld() as world:
        world.position = SOA_TILE.HQ_LADDER
        world.messages = [FakeModule(text='Old message')]
        world.refused = [SOA_LOC.PHOENIX_DOOR]
        assert world.run(hideout.enter_phoenix_inner(world.logs.append)) is False
        assert 'door 2397: The door is locked.' in world.logs
        assert not any(['Old message' in line for line in world.logs])


def test_arrav_black_arm_upper_crosses_door_then_climbs():
    with HideoutWorld() as world:
        assert world.black_upper()
        assert world.interactions == [(SOA_LOC.BLACKARM_DOOR, 'Open'), (SOA_LOC.BLACKARM_STAIRS, 'Climb-up')]
        assert hideout.in_black_arm_upper(world.position)


def test_arrav_black_arm_upper_already_upstairs_skips_route():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS_TOP
        assert world.black_upper()
        assert world.interactions == [] and world.waits == []


def test_arrav_black_arm_inner_already_on_either_side_of_stairs_skips_door():
    for position in [SOA_TILE.BLACKARM_STAIRS, SOA_TILE.BLACKARM_STAIRS_TOP]:
        with HideoutWorld() as world:
            world.position = position
            assert world.run(hideout.enter_black_arm_inner(world.logs.append))
            assert world.interactions == [] and world.waits == []


def test_arrav_black_arm_upper_from_inner_only_climbs():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS
        assert world.black_upper()
        assert world.interactions == [(SOA_LOC.BLACKARM_STAIRS, 'Climb-up')]


def test_arrav_black_arm_failed_door_does_not_climb():
    with HideoutWorld() as world:
        world.rejected = [SOA_LOC.BLACKARM_DOOR]
        assert world.black_upper() is False
        assert world.interactions == [(SOA_LOC.BLACKARM_DOOR, 'Open')]


def test_arrav_black_arm_unacknowledged_climb_is_failure():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS
        world.unresponsive = [SOA_LOC.BLACKARM_STAIRS]
        assert world.black_upper() is False
        assert not hideout.in_black_arm_upper(world.position)
        assert 'never reached level 1' in world.logs[-1]


def test_arrav_leave_black_arm_upper_climbs_down_then_exits_sealed_pocket():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS_TOP
        assert world.leave_black()
        assert world.interactions == [(SOA_LOC.BLACKARM_STAIRS_TOP, 'Climb-down'), (SOA_LOC.BLACKARM_DOOR, 'Open')]
        assert world.position == SOA_TILE.BLACKARM_DOOR


def test_arrav_leave_black_arm_inner_only_crosses_door():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS
        assert world.leave_black()
        assert world.interactions == [(SOA_LOC.BLACKARM_DOOR, 'Open')]


def test_arrav_leave_black_arm_outside_skips_all_interactions():
    with HideoutWorld() as world:
        assert world.leave_black()
        assert world.interactions == [] and world.waits == []


def test_arrav_leave_black_arm_failed_descent_does_not_click_door():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS_TOP
        world.rejected = [SOA_LOC.BLACKARM_STAIRS_TOP]
        assert world.leave_black() is False
        assert world.interactions == [(SOA_LOC.BLACKARM_STAIRS_TOP, 'Climb-down')]


def test_arrav_leave_black_arm_failed_door_reports_failure_after_descent():
    with HideoutWorld() as world:
        world.position = SOA_TILE.BLACKARM_STAIRS_TOP
        world.rejected = [SOA_LOC.BLACKARM_DOOR]
        assert world.leave_black() is False
        assert hideout.in_black_arm_inner(world.position)


def test_arrav_leave_weapon_store_descends_then_opens_door_without_key():
    with HideoutWorld() as world:
        world.position = SOA_TILE.CROSSBOW_WEST
        assert world.leave_store()
        assert world.interactions == [(SOA_LOC.STORE_LADDER_TOP, 'Climb-down'), (SOA_LOC.STORE_DOOR, 'Open')]
        assert world.position == SOA_TILE.STORE_DOOR


def test_arrav_leave_weapon_store_ground_only_opens_door():
    with HideoutWorld() as world:
        world.position = SOA_TILE.STORE_LADDER
        assert world.leave_store()
        assert world.interactions == [(SOA_LOC.STORE_DOOR, 'Open')]


def test_arrav_leave_weapon_store_outside_skips_route():
    with HideoutWorld() as world:
        assert world.leave_store()
        assert world.interactions == [] and world.waits == []


def test_arrav_leave_weapon_store_failed_descent_does_not_click_door():
    with HideoutWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.rejected = [SOA_LOC.STORE_LADDER_TOP]
        assert world.leave_store() is False
        assert world.interactions == [(SOA_LOC.STORE_LADDER_TOP, 'Climb-down')]


def test_arrav_leave_weapon_store_failed_door_preserves_ground_pocket():
    with HideoutWorld() as world:
        world.position = SOA_TILE.STORE_LADDER_TOP
        world.rejected = [SOA_LOC.STORE_DOOR]
        assert world.leave_store() is False
        assert hideout.in_store_ground(world.position)

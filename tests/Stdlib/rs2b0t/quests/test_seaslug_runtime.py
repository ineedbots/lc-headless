"""Test regional boat transitions, ladder refusals and bounded ignition."""
import rs2004.quests.defs.seaslug.legs as sea
from rs2004 import execution


def result(value):
    return value
    yield


def boat_route():
    state = {'tile': sea.SS_TILE.ISLAND_ARRIVE}
    order = []
    spy_on(sea.game, 'tile', impl=lambda: state['tile'])
    def approach(stop, hops, log):
        order.append(stop.anchor)
        return True
        yield
    spy_on(sea, 'goto_npc', impl=approach)
    def talk(name, prefer, log):
        assert name == 'Holgart'
        state['tile'] = sea.SS_TILE.PLATFORM_ARRIVE if sea.region_of(state['tile']) == 'island' else sea.SS_TILE.SHORE
        return True
        yield
    spy_on(sea, 'talk_through', impl=talk)
    climbed = spy_on(sea, 'climb_to', impl=lambda level, log: result(level == 0))
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(sea.sail_to('mainland', lambda message: None))).to_be(True)
    expect(order).to_equal([sea.HOLGART_ISLAND.anchor, sea.HOLGART_PLATFORM.anchor])
    expect(len(climbed.calls)).to_be(1)


test('Sea Slug returns from the island through the platform and climbs down before boarding', boat_route)


def stuck_boat():
    spy_on(sea.game, 'tile', returns=sea.SS_TILE.SHORE)
    attempts = spy_on(sea, 'board_from', impl=lambda *args: result(True))
    expect(run_wait(sea.sail_to('island', lambda message: None))).to_be(False)
    expect(len(attempts.calls)).to_be(3)


test('Sea Slug bounds boat hops when transport never changes region', stuck_boat)


def ladder_climb(allowed):
    def run():
        state = {'tile': sea.SS_TILE.LADDER_FOOT}
        permits = allowed
        spy_on(sea.game, 'tile', impl=lambda: state['tile'])
        spy_on(sea.traversal, 'walk_resilient', impl=lambda *args, **kwargs: result(True))
        spy_on(sea.game_messages, 'mark', returns=1)
        spy_on(sea.game_messages, 'saw_since', returns=True)
        def climb(op):
            assert op == 'Climb-up'
            if permits:
                state['tile'] = sea.SS_TILE.LADDER_TOP
            return True
        ladder = Fake(name='Ladder', actions=lambda: ['Climb-up'], distance=lambda: 1, interact=climb)
        spy_on(sea.locs, 'query', impl=querying(lambda: [ladder]))
        spy_on(execution, 'delay_until', impl=instant_until)
        settled = spy_on(sea, 'settle_scene', impl=instant_ticks)
        expect(run_wait(sea.climb_to(1, lambda message: None))).to_be(allowed)
        expect(len(settled.calls)).to_be(1 if allowed else 0)
    return run


test('Sea Slug settles the scene only after a confirmed ladder level change', ladder_climb(True))
test('Sea Slug detects fishermen turning back an unlit-torch climb', ladder_climb(False))


def sticks_case(replies, expected):
    def run():
        messages = list(replies)
        state = {'message': '', 'rubs': 0}
        def rub(op):
            assert op == 'Rub-together'
            state['message'] = messages[min(state['rubs'], len(messages) - 1)]
            state['rubs'] += 1
            return True
        sticks = Fake(id=sea.SS_OBJ.DRY_STICKS, count=1, interact=rub)
        spy_on(sea.inventory, 'items', returns=[sticks])
        spy_on(sea.game_messages, 'mark', returns=1)
        def saw(mark, predicate):
            return predicate(state['message']) if callable(predicate) else predicate in state['message']
        spy_on(sea.game_messages, 'saw_since', impl=saw)
        spy_on(execution, 'delay_until', impl=instant_until)
        expect(run_wait(sea.rub_sticks(lambda message: None))).to_be(expected)
        expect(state['rubs']).to_be(2 if expected else (12 if replies[0] == 'smoke momentarily' else 1))
    return run


test('Sea Slug retries smoking sticks until they catch alight', sticks_case(['smoke momentarily', 'catch alight'], True))
test('Sea Slug stops ignition immediately below the Firemaking requirement', sticks_case(['firemaking level of 30'], False))
test('Sea Slug stops ignition when the server sends no recognized reply', sticks_case([''], False))
test('Sea Slug limits repeated smoke-only ignition attempts', sticks_case(['smoke momentarily'], False))


def retry_loc():
    spy_on(sea, 'climb_to', impl=lambda *args: result(True))
    spy_on(sea.reach, 'loc_op', impl=lambda *args, **kwargs: result('retry'))
    expect(run_wait(sea.pick_loc(sea.SS_LOC.CRATES, 'Shout-across', sea.SS_TILE.CRATES_STAND, 'Crates', lambda: True, lambda message: None))).to_be(False)


test('Sea Slug leaves an approaching loc operation unfinished for the next pass', retry_loc)

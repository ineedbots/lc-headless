"""Sea Slug ship, ladder, panel and crane operations verify their server outcomes."""

from rs2004.geometry import Tile
from rs2004.quests.defs.seaslug import legs


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def ladders():
    scene = Scene()
    scene.at = None
    expect(run_wait(legs.climb_to(1, scene.log))).to_be(False)
    scene.at = legs.SS_TILE.LADDER_TOP
    expect(run_wait(legs.climb_to(1, scene.log))).to_be(True)
    scene.walk_ok = False
    expect(run_wait(legs.climb_to(0, scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(legs.climb_to(0, scene.log))).to_be(False)
    scene.loc('Ladder', ['Climb-down'], tile=legs.SS_TILE.LADDER_TOP, effect=lambda op: False)
    expect(run_wait(legs.climb_to(0, scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Ladder', ['Climb-down'], tile=legs.SS_TILE.LADDER_TOP,
              effect=lambda op: scene.say('fishing rod'))
    expect(run_wait(legs.climb_to(0, scene.log))).to_be(False)
    climb = spy_on(legs, 'climb_to', impl=answer(False))
    expect(run_wait(legs.board_from('platform', scene.log))).to_be(False)
    climb.mock_implementation(answer(True))
    goto = spy_on(legs, 'goto_npc', impl=answer(False))
    expect(run_wait(legs.board_from('platform', scene.log))).to_be(False)
    goto.mock_implementation(answer(True))
    talk = spy_on(legs, 'talk_through', impl=answer(False))
    expect(run_wait(legs.board_from('platform', scene.log))).to_be(False)
    talk.mock_implementation(answer(True))
    spy_on(legs, 'region_of', returns='mainland')
    expect(run_wait(legs.board_from('platform', scene.log))).to_be(True)


test('platform ladders handle missing locs and torch refusals and boarding waits for a new region', ladders)


def rescue():
    scene = Scene(legs.SS_TILE.CRANE_STAND)
    sail = spy_on(legs, 'sail_to', impl=answer(False))
    for fn in [legs.call_kennith, legs.open_panel_and_call, legs.rotate_crane, legs.find_kent]:
        expect(run_wait(fn(scene.log))).to_be(False)
    sail.mock_implementation(answer(True))
    spy_on(legs, 'climb_to', impl=answer(True))
    scene.loc_op_status = 'done'
    spy_on(legs, 'drive_dialog', impl=answer(True))
    expect(run_wait(legs.call_kennith(scene.log))).to_be(True)
    scene.loc_op_status = 'retry'
    expect(run_wait(legs.call_kennith(scene.log))).to_be(False)
    expect(run_wait(legs.open_panel_and_call(scene.log))).to_be(False)
    expect(run_wait(legs.rotate_crane(scene.log))).to_be(False)
    scene.loc_op_status = 'done'
    expect(run_wait(legs.open_panel_and_call(scene.log))).to_be(True)
    scene.loc_op_effect = lambda *args: scene.say('get closer to use that')
    expect(run_wait(legs.rotate_crane(scene.log))).to_be(False)
    expect(scene.logged('crane refused')).to_be(True)
    scene.loc_op_effect = lambda *args: scene.say('lower kennith to the row boat')
    expect(run_wait(legs.rotate_crane(scene.log))).to_be(True)
    goto = spy_on(legs, 'goto_npc', impl=answer(False))
    expect(run_wait(legs.find_kent(scene.log))).to_be(False)
    goto.mock_implementation(answer(True))
    spy_on(legs, 'talk_through', impl=answer(True))
    expect(run_wait(legs.find_kent(scene.log))).to_be(True)
    expect(run_wait(legs.rub_sticks(scene.log))).to_be(False)
    scene.item(legs.SS_OBJ.DRY_STICKS, 'Dry sticks', effect=lambda op: False)
    expect(run_wait(legs.rub_sticks(scene.log))).to_be(False)


test('Kennith rescue retries panel and crane operations and requires the lowering message', rescue)

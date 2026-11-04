"""Fishing Contest gates, Bonzo conversations and exact pipe interactions."""

from rs2004.quests.defs.fishingcontest import contest


def answer(value):
    def wait(*args, **kwargs):
        return value
        yield
    return wait


def contest_gate():
    scene = Scene(contest.FC_TILE.GATE_OUTSIDE)
    scene.walk_ok = False
    expect(run_wait(contest.enter_compound(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(contest.enter_compound(scene.log))).to_be(False)
    scene.loc('Gate', ['Open'], id=contest.FC_LOC.GATE_LEFT, effect=lambda op: False)
    expect(run_wait(contest.enter_compound(scene.log))).to_be(False)
    scene.locs = []
    scene.loc('Gate', ['Open'], id=contest.FC_LOC.GATE_RIGHT,
              effect=lambda op: setattr(scene, 'at', contest.FC_TILE.GATE_INSIDE))
    expect(run_wait(contest.enter_compound(scene.log))).to_be(True)
    scene.talk_status = 'unreachable'
    expect(run_wait(contest.walk_and_talk(contest.BONZO_ENTER, scene.log))).to_be(False)
    scene.talk_status = 'done'
    spy_on(contest, 'drive_choice', impl=answer(True))
    expect(run_wait(contest.walk_and_talk(contest.BONZO_ENTER, scene.log))).to_be(True)
    expect(run_wait(contest.pay_entry_fee(scene.log))).to_be(True)
    expect(run_wait(contest.claim_pass(scene.log))).to_be(True)


test('contest gates accept either half and Bonzo dialogue reports unreachable approaches', contest_gate)


def contest_failures():
    scene = Scene(contest.FC_TILE.PIPE_STAND)
    enter = spy_on(contest, 'enter_compound', impl=answer(False))
    for fn in [contest.pay_entry_fee, contest.stash_garlic, contest.fish_at_pipes,
               contest.hand_over_catch, contest.claim_spare_trophy]:
        expect(run_wait(fn(scene.log))).to_be(False)
    enter.mock_implementation(answer(True))
    scene.walk_ok = False
    expect(run_wait(contest.stash_garlic(scene.log))).to_be(False)
    expect(run_wait(contest.fish_at_pipes(scene.log))).to_be(False)
    scene.walk_ok = True
    expect(run_wait(contest.stash_garlic(scene.log))).to_be(False)
    expect(run_wait(contest.fish_at_pipes(scene.log))).to_be(False)
    scene.loc('Pipe', id=contest.FC_LOC.WALL_PIPE, tile=contest.FC_TILE.PIPE_STAND)
    scene.item(contest.FC_ID.GARLIC, 'Garlic', on_use=lambda target: False)
    expect(run_wait(contest.stash_garlic(scene.log))).to_be(False)
    scene.pack = []
    scene.item(contest.FC_ID.GARLIC, 'Garlic', on_use=lambda target: scene.take(contest.FC_ID.GARLIC))
    expect(run_wait(contest.stash_garlic(scene.log))).to_be(True)
    scene.npc('Fishing spot', ['Fish'], id=contest.FC_NPC.PIPES_SPOT, tile=contest.FC_TILE.PIPES_SPOT,
              effect=lambda op: False)
    expect(run_wait(contest.fish_at_pipes(scene.log))).to_be(False)
    talk = spy_on(contest, 'walk_and_talk', impl=answer(False))
    expect(run_wait(contest.hand_over_catch(scene.log))).to_be(False)
    expect(run_wait(contest.claim_spare_trophy(scene.log))).to_be(False)
    leave = spy_on(contest, 'leave_compound', impl=answer(False))
    expect(run_wait(contest.deliver_trophy(scene.log))).to_be(False)
    leave.mock_implementation(answer(True))
    talk.mock_implementation(answer(True))
    expect(run_wait(contest.deliver_trophy(scene.log))).to_be(True)


test('pipe stashing and contest handovers stop at failed travel, missing materials and refused sends', contest_failures)

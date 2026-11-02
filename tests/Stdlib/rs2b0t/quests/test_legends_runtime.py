"""Legends Quest's game legs, against what phase 17i's live runs found."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.quests.defs.legends import guild, jungle
from rs2004.quests.defs.legends.areas import LQ_NPC

W = {'gujuo': False, 'ticks': 0, 'upkeep': 0, 'fights': [], 'savage': False}


def tick(n=1):
    W['ticks'] += n
    return None
    yield


def upkeep():
    W['upkeep'] += 1
    return None
    yield


def fake_fight(plan, log):
    W['fights'].append(plan.npc)
    expect(plan.pray).to_be(False)
    W['savage'] = False
    return plan.done()
    yield


def npc_rows():
    rows = []
    if W['gujuo']:
        rows.append(Fake(name=LQ_NPC.GUJUO, distance=lambda: 3, actions=lambda: ['Talk-to'], targets_me=lambda: False))
    if W['savage']:
        rows.append(Fake(name='Jungle Savage', distance=lambda: 1, actions=lambda: ['Attack'], targets_me=lambda: True))
    return rows


def world():
    W['gujuo'] = False
    W['ticks'] = 0
    W['upkeep'] = 0
    W['fights'] = []
    W['savage'] = False
    spy_on(execution, 'delay_ticks', impl=tick)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(sustain, 'run', impl=upkeep)
    spy_on(npcs, 'query', impl=querying(npc_rows))
    patch(jungle, 'fight', fake_fight)


def savage_fought():
    world()
    W['savage'] = True
    run_wait(jungle.wait_for_gujuo(lambda line: None))
    expect(W['fights']).to_equal(['Jungle Savage'])
    expect(W['upkeep']).to_be_greater_than(0)


test('the wait after a swing kills what the noise set on us, and eats', savage_fought)


def wait_is_in_ticks():
    world()
    run_wait(jungle.wait_for_gujuo(lambda line: None))
    expect(W['ticks']).to_be(jungle.SWING_WAIT_TICKS)
    expect(W['upkeep']).to_be(jungle.SWING_WAIT_TICKS)


test('the wait after a swing is counted in ticks, so a fast world does not idle longer under attack', wait_is_in_ticks)


def stops_when_he_comes():
    world()
    W['gujuo'] = True
    run_wait(jungle.wait_for_gujuo(lambda line: None))
    expect(W['ticks']).to_be(0)


test('the wait ends as soon as Gujuo walks in', stops_when_he_comes)


TRAINING = {'boxes': 0}


def ok_walk(*args, **opts):
    return True
    yield


def said_done(*args, **opts):
    return 'done'
    yield


def close_training_box():
    TRAINING['boxes'] -= 1
    return True
    yield


def training_boxes_clicked():
    world()
    TRAINING['boxes'] = 4
    patch(guild, 'enter_main_hall', ok_walk)
    spy_on(traversal, 'walk_resilient', impl=ok_walk)
    spy_on(reach, 'npc_dialog', impl=said_done)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(chat_dialog, 'options', returns=[])
    spy_on(modals, 'is_open', impl=lambda: TRAINING['boxes'] > 0)
    spy_on(modals, 'close', impl=close_training_box)
    spy_on(quests, 'status', impl=lambda name: 'complete' if TRAINING['boxes'] == 0 else 'in_progress')
    expect(run_wait(guild.take_training(lambda line: None))).to_be(True)
    expect(TRAINING['boxes']).to_be(0)


test("Radimus' training clicks the box after each session", training_boxes_clicked)


def training_shut_early():
    world()
    TRAINING['boxes'] = 1
    patch(guild, 'enter_main_hall', ok_walk)
    spy_on(traversal, 'walk_resilient', impl=ok_walk)
    spy_on(reach, 'npc_dialog', impl=said_done)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(chat_dialog, 'options', returns=[])
    spy_on(modals, 'is_open', impl=lambda: TRAINING['boxes'] > 0)
    spy_on(modals, 'close', impl=close_training_box)
    spy_on(quests, 'status', returns='in_progress')
    # Why: the step's clock doesn't move under instant ticks, so a wait for the quest instead of the chat's end would never return here.
    expect(run_wait(guild.take_training(lambda line: None))).to_be(False)


test("a training conversation that shuts with sessions owed fails at once, for the engine's next attempt", training_shut_early)

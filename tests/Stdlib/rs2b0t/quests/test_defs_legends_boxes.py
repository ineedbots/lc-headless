"""Ported from rs2b0t's test/api/ai/quests/defs/legends-boxes.test.ts and legends-drive-to-end.test.ts (MIT, see
thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.quests.defs.legends.scene import drive_to_end
from rs2004.quests.exec.prompts import clear_boxes, drive_boxes

world = {'chain': [], 'ticks': 0, 'closes': 0, 'continues': 0}


def count_tick(n=1):
    world['ticks'] += 1
    return None
    yield


def close_one():
    world['closes'] += 1
    world['chain'].pop(0)
    return True
    yield


def continue_one():
    world['continues'] += 1
    world['chain'].pop(0)
    return True
    yield


def stay_open():
    world['closes'] += 1
    return False
    yield


def no_upkeep():
    return None
    yield


def showing():
    return world['chain'][0] if len(world['chain']) > 0 else ''


def setup(chain):
    world['chain'] = chain
    world['ticks'] = 0
    world['closes'] = 0
    world['continues'] = 0
    spy_on(execution, 'delay_ticks', impl=count_tick)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(modals, 'is_open', impl=lambda: len(world['chain']) > 0)
    spy_on(modals, 'close', impl=close_one)
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(chat_dialog, 'options', returns=[])
    spy_on(sustain, 'run', impl=no_upkeep)


def as_chat():
    spy_on(modals, 'is_open', returns=False)
    spy_on(chat_dialog, 'is_open', impl=lambda: len(world['chain']) > 0)
    spy_on(chat_dialog, 'can_continue', impl=lambda: len(world['chain']) > 0)
    spy_on(chat_dialog, 'continue_', impl=continue_one)


# Why: `~mesbox` uses the main modal, which the chat driver cannot advance.
def box_chain():
    setup(['You attempt to pick the lock...', 'It looks very sophisticated...', 'You carefully insert your lockpick into the lock.', 'You feel for the pins and levers in the mechanism.', 'But you fail to pick the lock.'])
    got = yield from drive_boxes(lambda: 'fail to pick the lock' in showing(), 30000)
    expect(got).to_be(True)
    # Leave the result visible for the caller.
    expect(world['closes']).to_be(4)
    expect(showing()).to_be('But you fail to pick the lock.')


# Why: a failed close must yield instead of spinning until the deadline.
def stuck_box():
    setup(['a box with no close button'])
    spy_on(modals, 'close', impl=stay_open)
    # Why: the step's clock doesn't move under instant ticks, so the goal is what ends the loop, and it only comes if the loop yields.
    got = yield from drive_boxes(lambda: world['ticks'] > 3, 60)
    expect(got).to_be(True)
    expect(world['closes']).to_be_greater_than(0)


# Why: recheck the goal before advancing past the result message.
def goal_box_as_chat():
    setup(['You ripple your muscles.', 'You brace yourself against the doors.', 'You start to force the doors open.', 'And you just manage to force the doors open slightly.'])
    as_chat()
    got = yield from drive_boxes(lambda: 'manage to force the doors open' in showing(), 30000)
    expect(got).to_be(True)
    expect(world['continues']).to_be(3)
    expect(showing()).to_be('And you just manage to force the doors open slightly.')


# Why: chat continues can suspend the server script that performs the crossing.
def clear_as_chat():
    setup(['You see a lever which you pull on to open the door.'])
    as_chat()
    yield from clear_boxes()
    expect(world['continues']).to_be(1)
    expect(world['chain']).to_have_length(0)


# Why: an unmatched choice cannot progress, so fail without spending the full budget.
def unmatched_gives_up():
    setup([])
    said = []
    spy_on(chat_dialog, 'is_open', returns=True)
    spy_on(chat_dialog, 'options', returns=['Sorry for bothering you.', "Ungadulu mumbled something about 'pure' water?"])
    got = yield from drive_boxes(lambda: False, 30000, ['I need some pure water to douse some magic flames.'], lambda m: said.append(m))
    expect(got).to_be(False)
    expect(said[0]).to_contain('no preferred option')
    expect(said[0]).to_contain('mumbled')


# Why: clearing after success closed the combination lock the caller needed.
def panel_stays_open():
    setup([])
    panel = [42]
    spy_on(modals, 'is_open', impl=lambda: panel[0] != -1)
    got = yield from drive_boxes(lambda: panel[0] == 42, 5000)
    expect(got).to_be(True)
    expect(panel[0]).to_be(42)


# Why: `~mesbox` can suspend a chain without opening chat, so silence does not mean completion.
def box_is_not_silence():
    setup(['the shaman throws himself down on the floor and starts convulsing.'])
    got = yield from drive_to_end([], lambda line: None, 5000)
    expect(got).to_be(True)
    expect(world['chain']).to_have_length(0)


test('clicks the box chain through to its result', box_chain)
test('a box that will not close yields instead of spinning', stuck_box)
test('stops on the goal box when the chain renders as chat continues', goal_box_as_chat)
test('clearBoxes dismisses a chain that rendered as chat continues', clear_as_chat)
test('an option list nothing matches gives up at once, and says what it saw', unmatched_gives_up)
test('a prompt whose goal is an open panel leaves it open', panel_stays_open)
test('a chain suspended on a message box is driven, not counted as silence', box_is_not_silence)

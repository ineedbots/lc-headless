"""Partial surplus deposits require server acknowledgement before the next click."""

import rs2004.quests.exec.steps as steps
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import quest_step


def result(value):
    yield from ()
    return value


def caps():
    scene = Scene()
    state = [4, True, True]
    def deposit(op):
        if state[1] and state[2]:
            state[0] -= 1
        return state[1]
    normal = Fake(id=42, name='Quest item', count=4, actions=lambda: ['Eat', 'Drop'], interact=lambda op: False)
    spy_on(steps.inventory, 'items', returns=[normal])
    spy_on(steps.bank, 'side_items', impl=lambda: [Fake(id=42, name='Quest item', count=state[0],
                                                   actions=lambda: ['Deposit-1'], interact=deposit)] if state[0] else [])
    # The normal panel may still show its old count while the bank side updates.
    spy_on(steps.inventory, 'count_by_id', returns=4)
    spy_on(steps, 'open_bank_leg', impl=lambda reason, anchor, log: result(True))
    spy_on(steps.bank, 'backpack_ready', impl=lambda log=None: result(True))
    spy_on(steps.bank, 'deposit_all_matching', impl=lambda predicate: result(True))
    step = quest_step('deposit', keep=[], keep_ids=[42], caps=[Record({'id': 42, 'qty': 2})])
    expect(run_wait(steps.execute_step(step, [], scene.log))).to_be(True)
    expect(state[0]).to_be(2)
    state[0], state[1] = 4, False
    expect(run_wait(steps.execute_step(step, [], scene.log))).to_be(False)
    expect(state[0]).to_be(4)
    state[1], state[2] = True, False
    expect(run_wait(steps.execute_step(step, [], scene.log))).to_be(False)
    expect(state[0]).to_be(4)
    state[2] = True
    zero = quest_step('deposit', keep=[], keep_ids=[42], caps=[Record({'id': 42, 'qty': 0})])
    expect(run_wait(steps.execute_step(zero, [], scene.log))).to_be(True)
    expect(state[0]).to_be(0)


test('deposit caps retain the requested quantity and stop when a deposit is refused', caps)

"""rs2b0t's test/api/ai/quests/engine/exact-item-steps.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.bank import bank, banking
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.engine.types import quest_step
from rs2004.quests.exec.steps import execute_step
from rs2004.traversal import traversal


def quiet(m):
    pass


def answers(value):
    """A generator function that gives value at once, as an async stub that resolves to it."""
    def run(*args, **kwargs):
        return value
        yield
    return run


# Why: the buy step walks to the counter once the coin question is settled, and these tests only care about the coin
# question.
def no_walk():
    spy_on(traversal, 'walk_resilient', impl=answers(False))


def bank_opens():
    # open_bank_leg uses banking.open (Shantay chest and booths), not bank.open_nearest.
    spy_on(banking, 'open', impl=answers(True))


def _fn4():
    bank_opens()
    calls = []

    def by_name(name, qty):
        calls.append({'type': 'name', 'value': name, 'qty': qty})
        return True
        yield

    def by_id(id, qty):
        calls.append({'type': 'id', 'value': id, 'qty': qty})
        return True
        yield

    spy_on(bank, 'withdraw_x', impl=by_name)
    spy_on(bank, 'withdraw_x_by_id', impl=by_id)
    step = quest_step('withdraw', bank=Tile(2616, 3332, 0), leave_open=True,
                      items=[{'name': 'A key', 'id': 298, 'qty': 1}, {'name': 'Rope', 'qty': 2}])
    ok = yield from execute_step(step, [], quiet)
    expect(ok).to_be(True)
    expect(calls).to_equal([{'type': 'id', 'value': 298, 'qty': 1}, {'type': 'name', 'value': 'Rope', 'qty': 2}])


test('withdraw steps route exact item specs through the ID-aware helper', _fn4)


def _fn7():
    bank_opens()
    decisions = {}

    def deposit(matches):
        decisions[293] = matches('A key', 293)
        decisions[298] = matches('A key', 298)
        decisions[954] = matches('Rope', 954)
        decisions[1] = matches('Pot', 1)
        if False:
            yield

    spy_on(bank, 'deposit_all_matching', impl=deposit)
    step = quest_step('deposit', bank=Tile(2616, 3332, 0), leave_open=True, keep=['rope'], keep_ids=[293], exact_keep=True)
    ok = yield from execute_step(step, [], quiet)
    expect(ok).to_be(True)
    expect(decisions).to_equal({293: False, 298: True, 954: False, 1: True})


test('deposit keepIds preserves one exact object while same-named objects are deposited', _fn7)


def buy_orb():
    return quest_step('buy', item='Unpowered orb', qty=1, shop={'npc': 'Magic store', 'anchor': Tile(2591, 3089, 0)}, est_gp=60000,
                      bank=Tile(2616, 3332, 0))


# Why: bank.withdraw_x takes its count ON TOP of the pack, so asking for est_gp over a float draws the estimate twice,
# 50k plus the guild's 60k estimate walked 110k into the jungle.
# Why: and est_gp estimates the counter's full list, so requiring all of it before every purchase sent the run back to
# the bank after each one.
def _fn9():
    bank_opens()
    no_walk()
    calls = []

    def withdraw(name, qty):
        calls.append({'name': name, 'qty': qty})
        return True
        yield

    spy_on(bank, 'withdraw_x', impl=withdraw)
    spy_on(inventory, 'count', impl=lambda name: 50000 if name == 'Coins' else 0)
    yield from execute_step(buy_orb(), [], quiet)
    expect(calls).to_equal([])


test('a buy step with a purse above the floor makes no bank trip at all', _fn9)


def _fn11():
    bank_opens()
    no_walk()
    calls = []

    def withdraw(name, qty):
        calls.append({'name': name, 'qty': qty})
        return True
        yield

    spy_on(bank, 'withdraw_x', impl=withdraw)
    spy_on(inventory, 'count', impl=lambda name: 1000 if name == 'Coins' else 0)
    yield from execute_step(buy_orb(), [], quiet)
    expect(calls).to_equal([{'name': 'Coins', 'qty': 59000}])


test('a buy step below the floor draws the shortfall, never the estimate twice', _fn11)

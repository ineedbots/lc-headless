"""rs2b0t's test/scripts/AIOQuester/AIOQuesterFood.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004 import execution
from rs2004.catalogs import Record
from rs2004.game import skills
from rs2004.items import inventory
from bots.aio_quester import AIOQuester

S = {}


class Food:
    def __init__(self, name, on_interact):
        self.name = name
        self.on_interact = on_interact

    def actions(self):
        return ['Eat']

    def interact(self, action):
        self.on_interact(self.name, action)
        return True


def noted(name, action):
    S['interactions'].append(f'{name}:{action}')


def eaten_cake(name, action):
    S['interactions'].append(f'{name}:{action}')
    S['hp'] = 10


def answered(cond, ms=0):
    return cond()
    yield


def fixture():
    S['hp'] = 6
    S['pack'] = []
    S['interactions'] = []
    spy_on(inventory, 'items', impl=lambda: S['pack'])
    spy_on(skills, 'effective', impl=lambda name: S['hp'] if name == 'hitpoints' else 0)
    spy_on(skills, 'level', impl=lambda name: 10 if name == 'hitpoints' else 0)
    spy_on(execution, 'delay_until', impl=answered)
    bot = AIOQuester()
    spy_on(bot, 'sustain_policy', returns=Record({'foods': ['lobster']}))
    return bot


def _fn2():
    bot = fixture()
    S['pack'] = [Food('Lobster', noted), Food('Cake', eaten_cake)]
    expect(bot.should_eat()).to_be(True)
    yield from bot.eat_once()
    expect(S['interactions']).to_equal(['Cake:Eat'])


test('AIOQuester reselects the fitting mixed-pack food at execution time', _fn2)


def _fn5():
    bot = fixture()
    S['pack'] = [Food('Lobster', noted), Food('Cake', noted)]
    expect(bot.should_eat()).to_be(True)
    S['pack'] = [Food('Lobster', noted)]
    yield from bot.eat_once()
    expect(S['interactions']).to_equal([])


test('AIOQuester does not consume a stale selection after inventory changes', _fn5)


def consumed_during_damage():
    bot = fixture()
    def consume(name, action):
        S['pack'] = []
        # The same update includes incoming damage, leaving HP unchanged.
    S['pack'] = [Food('Cake', consume)]
    results = []
    def answered_by_inventory(cond, ms=0):
        results.append(cond())
        return results[-1]
        yield
    spy_on(execution, 'delay_until', impl=answered_by_inventory)
    yield from bot.eat_once()
    expect(results).to_equal([True])


test('AIOQuester recognises consumed food when incoming damage masks its heal', consumed_during_damage)

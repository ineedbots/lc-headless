"""Ported from rs2b0t's test/api/ai/quests/defs/deathplateau-drink.test.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog, modals
from rs2004.execution import event_signal
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.deathplateau.harold import gamble_with_harold, give_blurberry_to_harold

HAROLD_ROOM = Tile(2905, 3539, 1)


# rs2b0t's stubProps on the singletons, as spies on their classes; the game clock advances a tick a read, so a
# deadline loop that never finds what it waits for ends rather than spinning.
def stub_world(items):
    clock = {'ms': 0}

    def step_time():
        clock['ms'] += 600
        return clock['ms']
    spy_on(_core, 'step_time', impl=step_time)
    spy_on(game, 'tile', returns=HAROLD_ROOM)
    spy_on(inventory, 'items', impl=items)
    spy_on(event_signal, 'pending', returns=False)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(sustain, 'run', impl=instant_ticks)


def blurberry(id):
    return Fake(id=id, count=1, name='Blurberry special')


def _fn1():
    stakes = []
    stub_world(lambda: [])
    spy_on(inventory, 'count', returns=500)
    spy_on(chat_dialog, 'is_open', returns=True)
    spy_on(reader, 'count_dialog_open', returns=True)
    spy_on(reader, 'modals', returns=Record({'main': -1, 'chat': -1, 'side': -1}))
    spy_on(_core, 'answer_count', impl=lambda bet: stakes.append(bet) and False)
    expect(run_wait(gamble_with_harold(lambda *_args: None))).to_be(False)
    expect(len(stakes)).to_be(0)


test('never submits a stake without confirming the second drink', _fn1)


class DrinkScene:
    """Harold's menu, the confirmation, the box the drink raises, and his verdict once the box is shut."""

    def __init__(self, id):
        self.phase = 'menu'
        self.held = True
        self.box = False
        self.item = blurberry(id)

    def items(self):
        return [self.item] if self.held else []

    def is_open(self):
        return self.phase != 'closed' and self.phase != 'box'

    def can_continue(self):
        return self.phase == 'confirm' or self.phase == 'drunk'

    def options(self):
        return ['Can I buy you a drink?'] if self.phase == 'menu' else []

    def texts(self):
        return ['Now THAT hit the spot!'] if self.phase == 'drunk' else []

    def choose_option(self, pick):
        self.phase = 'confirm'
        return True
        yield

    def continue_(self):
        if self.phase == 'confirm':
            self.held = False
            self.box = True
            self.phase = 'box'
        else:
            self.phase = 'closed'
        return True
        yield

    def modal_open(self):
        return self.box

    def close_modal(self):
        self.box = False
        self.phase = 'drunk'
        return True
        yield


def confirms_cocktail(id):
    def run():
        scene = DrinkScene(id)
        stub_world(scene.items)
        for name in ['is_open', 'can_continue', 'options', 'texts', 'choose_option', 'continue_']:
            spy_on(chat_dialog, name, impl=getattr(scene, name))
        spy_on(modals, 'is_open', impl=scene.modal_open)
        spy_on(modals, 'close', impl=scene.close_modal)
        expect(run_wait(give_blurberry_to_harold(lambda *_args: None))).to_be(True)
        expect(scene.held).to_be(False)
        expect(scene.box).to_be(False)
    return run


for id in [2028, 2064]:
    test(f'confirms consumption of cocktail {id}', confirms_cocktail(id))


def _fn2():
    state = {'open': True}

    def finish():
        state['open'] = False
        return True
        yield
    stub_world(lambda: [blurberry(2028)])
    spy_on(chat_dialog, 'is_open', impl=lambda: state['open'])
    spy_on(chat_dialog, 'can_continue', impl=lambda: state['open'])
    spy_on(chat_dialog, 'options', returns=[])
    spy_on(chat_dialog, 'texts', impl=lambda: ["I fink I've had enough!"] if state['open'] else [])
    spy_on(chat_dialog, 'continue_', impl=finish)
    spy_on(modals, 'is_open', returns=False)
    expect(run_wait(give_blurberry_to_harold(lambda *_args: None))).to_be(True)
    expect(state['open']).to_be(False)


test('recognizes an already drunk Harold after a restarted run', _fn2)

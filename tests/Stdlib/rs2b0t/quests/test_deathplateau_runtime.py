"""Death Plateau's legs against spied facades, for what this client does differently from rs2b0t's webclient."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.quests.defs.deathplateau import read_iou
from rs2004.quests.defs.deathplateau.areas import DEATH_ITEM


def _fn1():
    events = []
    state = {'menu': True, 'combo': False}

    def close():
        events.append('close')
        state['menu'] = False

    def read(op):
        events.append(f'read:{op}')
        # The server refuses a held op behind an open dialogue.
        if not state['menu']:
            state['combo'] = True
        return True

    def items():
        if state['combo']:
            return [Fake(id=DEATH_ITEM.COMBINATION.id, count=1, name='Combination')]
        return [Fake(id=DEATH_ITEM.IOU.id, count=1, name='Iou', actions=lambda: ['Read'], interact=read)]
    spy_on(inventory, 'items', impl=items)
    spy_on(chat_dialog, 'is_open', impl=lambda: state['menu'])
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(reader, 'modals', returns=Record({'main': -1, 'side': -1, 'chat': -1}))
    spy_on(_core, 'close_interfaces', impl=close)
    spy_on(modals, 'close_if_open', impl=instant_ticks)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    expect(run_wait(read_iou(lambda *_args: None))).to_be(True)
    expect(events).to_equal(['close', 'read:Read'])


test("reading the IOU shuts Harold's menu first, since the server ignores a held op behind it", _fn1)

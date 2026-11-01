"""Regicide's game legs, against what phase 17h's live run found."""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.items import inventory
from rs2004.quests.defs.regicide import isafdar


def first_wait_relogs_once():
    relogs = []
    isafdar.messenger.armed = False
    patch(_core, 'relog', lambda delay=0: relogs.append(delay))
    spy_on(inventory, 'items', returns=[])
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    patch(isafdar, 'find_messenger', lambda: None)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    expect(run_wait(isafdar.take_summons(lambda line: None))).to_be(True)
    expect(relogs).to_equal([0])
    # Armed, it waits for him rather than logging in again.
    expect(run_wait(isafdar.take_summons(lambda line: None))).to_be(False)
    expect(relogs).to_equal([0])
    isafdar.messenger.armed = False


test("the messenger is armed by logging in again, once, since his timer starts at login", first_wait_relogs_once)

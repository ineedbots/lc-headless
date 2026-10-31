"""Eadgar's Ruse's legs against spied facades, where this port departs from rs2b0t."""

from rs2004 import execution
from rs2004.entities import ground_items
from rs2004.items import inventory
from rs2004.quests.defs.eadgar.supplies import take_ground


def _fn1():
    held = {'count': 1}
    drop = Fake(interact=lambda op: True)
    spy_on(ground_items, 'query', impl=querying(lambda: [drop]))
    spy_on(inventory, 'count', impl=lambda name: held['count'])
    spy_on(inventory, 'contains', impl=lambda name: held['count'] > 0)
    spy_on(execution, 'delay_until', impl=instant_until)
    # The Take hasn't landed: one chicken in the pack already must not read as success.
    expect(run_wait(take_ground('Raw chicken', lambda *_args: None))).to_be(False)


test('a ground take waits for the count to rise, not for the pack to hold one already', _fn1)

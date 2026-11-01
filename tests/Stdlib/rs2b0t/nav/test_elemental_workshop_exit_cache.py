"""Elemental Workshop ends down its spiral stairs, and phase 17f's live run found the walker had no route up them, so the
retreat to a bank and the next quest in the queue were stranded there."""

from rs2004.navigation import navigator
from rs2004.quests.defs.elementalworkshop.areas import SEERS_BANK, WORKSHOP_ARRIVAL


def _fn1():
    found = navigator.find_path(WORKSHOP_ARRIVAL, SEERS_BANK, max_expansions=400000, policy={'use_teleports': False})
    expect(found.ok, found.reason).to_be(True)


test('the walker climbs out of the workshop to the Seers bank', _fn1)

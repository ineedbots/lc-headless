"""Shilo Village ends at the dolmen in Bervirius' tomb, and phase 17d's live run found the walker had no route out of
it, so the retreat to a bank and the next quest in the queue were stranded there. The climbing rocks are the way out."""

from rs2004.navigation import navigator
from rs2004.quests.defs.shilo.areas import SV_TILE

HANDHOLDS = 2236


def route(start, dest):
    found = navigator.find_path(start, dest, max_expansions=400000, policy={'use_teleports': False})
    expect(found.ok, found.reason).to_be(True)
    return found


def climbs_out(found):
    for w in found.raw.get('waypoints', []):
        hop = w.get('transport') if isinstance(w, dict) else None
        if hop and hop.get('loc_id') == HANDHOLDS:
            return True
    return False


def _fn1():
    found = route(SV_TILE.BERVIRIUS_DOLMEN, SV_TILE.WELL_STACKED_ROCKS)
    expect(climbs_out(found)).to_be(True)


test("the dolmen is left by the climbing rocks to the tomb's entrance", _fn1)


# The ferry to the quest's Ardougne bank is gated on coins held, which this state has none of, so the island stands in.
def _fn2():
    found = route(SV_TILE.BERVIRIUS_DOLMEN, SV_TILE.TRUFITUS)
    expect(climbs_out(found)).to_be(True)


test("a walk from Bervirius' tomb to Tai Bwo Wannai climbs out", _fn2)

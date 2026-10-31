"""Ported from rs2b0t's src/bot/api/ai/quests/defs/eadgar/travel.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.quests.defs.trollstronghold.combat import protected_walk
from rs2004.quests.exec.primitives import goto_npc, talk_through

__all__ = ['guarded', 'guarded_talk']

THROWER = 'Thrower Troll'
THROWER_RANGE = 11


def thrower_near():
    return npcs.query().name(THROWER).within(THROWER_RANGE).nearest() is not None


# Why: 5 thrower trolls stand across the only way onto Trollheim and open on sight, and nothing in a walk fights back; Protect from Missiles refuses the chip damage.
# Why: this quest crosses it a dozen times on the thin food float the scarecrow leg leaves room for, and the chip damage kills runs.
# Why: the prayer follows the threat, so it is up only while something is shooting and the bar is still full for the next crossing.
def guarded(name, run):
    """Run a leg with Protect from Missiles tracking the throwers."""
    return Record({'kind': 'custom', 'name': name, 'run': lambda log: guarded_run(run, log)})


def guarded_run(run, log):
    return protected_walk('missiles', thrower_near, lambda: run(log), log)


def guarded_talk(stop):
    """A `talk` step that holds the prayer through the mountain crossing."""

    def _fn1(log):
        _w3 = yield from goto_npc(stop, [], log)
        _c2 = (_w3)
        if not (_c2):
            return _c2
        _result4 = yield from talk_through(stop.npc, stop.prefer, log)
        return _result4
    return guarded(f'talk to {stop.npc}', _fn1)

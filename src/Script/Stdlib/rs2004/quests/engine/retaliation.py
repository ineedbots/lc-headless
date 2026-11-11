"""Ported from rs2b0t's src/bot/api/ai/quests/engine/retaliation.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.execution import event_signal
from rs2004.game import game

__all__ = ['prepare_quest_retaliation']

def prepare_quest_retaliation(module, snap):
    if event_signal.pending():
        return False
    wanted = (module.auto_retaliate(snap) if callable(module.auto_retaliate) else (module.auto_retaliate if module.auto_retaliate is not None else True))
    if game.auto_retaliate_on() == wanted:
        return True
    if not game.set_auto_retaliate(wanted):
        return False
    _w1 = yield from execution.delay_until_ticks(lambda: game.auto_retaliate_on() == wanted, 5)
    return _w1 and not event_signal.pending()

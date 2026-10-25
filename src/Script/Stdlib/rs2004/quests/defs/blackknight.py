"""Black Knights' Fortress: rs2b0t's api/ai/quests/defs/blackknight.ts (MIT, see thirdparty/rs2b0t). In the iron
chainbody and bronze med helm, past the fortress guard to listen at the grill, then a cabbage down the hole."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['SIR_AMIK', 'IRON_CHAINBODY', 'BRONZE_MED_HELM', 'bkf_state', 'decide', 'infiltrate', 'pick_cabbage', 'blackknight']

SIR_AMIK = NpcStop('Sir Amik Varze', Tile(2962, 3338, 2), 6, ['I seek a quest!', 'I laugh in the face of danger!'])
IRON_CHAINBODY = 'Iron chainbody'
BRONZE_MED_HELM = 'Bronze med helm'

GRILL = Tile(3025, 3507, 0)
HOLE = Tile(3031, 3507, 1)
CABBAGE_FIELD = Tile(3053, 3306, 0)


def _has(snap, name):
    return snap.inv.get(name.lower(), 0) > 0


def _worn(snap, name):
    return name.lower() in snap.worn


def _near_tile(t, r):
    me = game.tile()
    return me is not None and me.level == t.level and max(abs(me.x - t.x), abs(me.z - t.z)) <= r


class _BkfState:
    """Whether the grill has been listened at this run."""

    def __init__(self):
        self.listened = False


bkf_state = _BkfState()


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        bkf_state.listened = False
        return quest_step('talk', stop=SIR_AMIK)
    if not _worn(snap, IRON_CHAINBODY) and _has(snap, IRON_CHAINBODY):
        return quest_step('equip', item=IRON_CHAINBODY)
    if not _worn(snap, BRONZE_MED_HELM) and _has(snap, BRONZE_MED_HELM):
        return quest_step('equip', item=BRONZE_MED_HELM)
    if _has(snap, 'Cabbage'):
        return quest_step('custom', name='infiltrate', run=infiltrate)
    return quest_step('talk', stop=SIR_AMIK)


def _grill_answered():
    return chat_dialog.is_open() or chat_dialog.can_continue() or _near_tile(GRILL, 1)


def infiltrate(log):
    """Listens at the grill once, then drops the cabbage down the hole. Use with yield from."""
    if not inventory.contains('Cabbage'):
        return True
    if not bkf_state.listened:
        log('infiltrating the fortress to eavesdrop at the grill')
        grill = yield from reach.loc_op('Grill', 'Listen-at', GRILL, _grill_answered, log=log)
        if grill == 'unreachable':
            log('bkf: Grill unreachable — re-planning')
            return False
        if grill != 'done':
            return False
        yield from execution.delay_until(lambda: chat_dialog.is_open(), 2500)
        for i in range(40):
            if not chat_dialog.is_open():
                break
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
        bkf_state.listened = True
        return False
    yield from traversal.walk_resilient(HOLE, radius=1, attempts=6, timeout_ms=120000, log=log)
    hole = locs.query().name('Hole').within(8).nearest()
    cabbage = inventory.first('Cabbage')
    if hole is not None and cabbage is not None:
        before = inventory.count('Cabbage')
        cabbage.use_on(hole)
        yield from execution.delay_until(lambda: inventory.count('Cabbage') < before, 6000)
    return False


def pick_cabbage(log):
    """A cabbage from the field by Draynor Manor. Use with yield from."""
    if inventory.contains('Cabbage'):
        return True
    before = inventory.count('Cabbage')
    log('picking a cabbage from the Draynor Manor field')
    # Why: the field is fenced, and its gate north of the cabbages starts shut on a fresh world, where every cabbage
    # answers "I can't reach that!"; reach opens the gate in the way, which a plain interact can't.
    yield from reach.loc_op('Cabbage', 'Pick', CABBAGE_FIELD, lambda: inventory.count('Cabbage') > before, within=14, log=log)
    return False


def _gather_cabbage(snap, need=1):
    return quest_step('custom', name='pick cabbage', run=pick_cabbage)


blackknight = QuestModule(
    record=quest_record('blackknight'),
    bank=Tile(2946, 3369, 0),
    grind=['black knight', 'aggressive black knight'],
    gather={'cabbage': _gather_cabbage},
    decide=decide,
)

"""Black Knights' Fortress: rs2b0t's api/ai/quests/defs/blackknight.ts (MIT, see thirdparty/rs2b0t). In the iron
chainbody and bronze med helm, past the fortress guard to listen at the grill, then a cabbage down the hole."""

from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop, drive_dialog
from rs2004.tabs import quests
from rs2004.dialogue import modals
from rs2004.quests.journal_text import normalize_journal
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['SIR_AMIK', 'IRON_CHAINBODY', 'BRONZE_MED_HELM', 'bkf_state', 'decide', 'infiltrate', 'pick_cabbage', 'blackknight']

SIR_AMIK = NpcStop('Sir Amik Varze', Tile(2962, 3338, 2), 6, ['I seek a quest!', 'I laugh in the face of danger!'])
IRON_CHAINBODY = 'Iron chainbody'
BRONZE_MED_HELM = 'Bronze med helm'

GRILL = Tile(3025, 3507, 0)
HOLE = Tile(3031, 3508, 1)
CABBAGE_FIELD = Tile(3053, 3295, 0)


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


def source_item(snap, item):
    if not snap.bank_known:
        return quest_step('scan_bank')
    count = (snap.bank_ids or {}).get(1965, 0) if item == 'Cabbage' and snap.bank_ids is not None else (snap.bank or {}).get(item.lower(), 0)
    if count > 0:
        line = {'name': item, 'qty': 1}
        if item == 'Cabbage':
            line['id'] = 1965
        return quest_step('withdraw', items=[line])
    if item == IRON_CHAINBODY:
        return quest_step('buy', item=item, qty=1, shop={'npc': 'Wayne', 'anchor': Tile(2973, 3312, 0)}, est_gp=300)
    if item == BRONZE_MED_HELM:
        return quest_step('buy', item=item, qty=1, shop={'npc': 'Peksa', 'anchor': Tile(3076, 3429, 0)}, est_gp=50)
    return quest_step('custom', name='pick cabbage', run=pick_cabbage)


def read_stage():
    status = quests.status("Black Knight's Fortress")
    if status == 'complete':
        return 4
    if status == 'not_started':
        return 0
    if status != 'in_progress':
        return None
    lines = yield from quests.journal("Black Knight's Fortress")
    text = normalize_journal(lines)
    yield from modals.close_if_open()
    for needle, stage in [('quest complete!', 4), ("now that i have sabotaged the witch's potion", 3), ('i eavesdropped on a witch', 2), ('asked me to investigate', 1)]:
        if needle in text:
            return stage
    return None


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started' or snap.stage == 3:
        return quest_step('talk', stop=SIR_AMIK)
    if snap.stage is None:
        return quest_step('wait', reason='fortress journal stage unavailable')
    for item in [IRON_CHAINBODY, BRONZE_MED_HELM]:
        if not _worn(snap, item):
            return quest_step('equip', item=item) if _has(snap, item) else source_item(snap, item)
    held = (snap.inv_ids or {}).get(1965, 0) > 0 if snap.inv_ids is not None else _has(snap, 'Cabbage')
    if not held:
        return source_item(snap, 'Cabbage')
    listen = snap.stage == 1
    return quest_step('custom', name='listen at the grill' if listen else 'sabotage the potion', run=lambda log: infiltrate(log, listen))


def _grill_answered():
    return chat_dialog.is_open() or chat_dialog.can_continue()


def cabbage():
    return ([item for item in inventory.items() if item.id == 1965 and not item.noted] or [None])[0]


def infiltrate(log, listen=True):
    if cabbage() is None:
        return True
    game.set_auto_retaliate(False)
    if listen:
        grill = yield from reach.loc_op('Grill', 'Listen-at', GRILL, _grill_answered, log=log)
        if grill != 'done':
            return False
        answered = yield from drive_dialog([], log)
        return answered
    arrived = yield from traversal.walk_resilient(HOLE, radius=1, attempts=6, timeout_ms=120000, log=log)
    if not arrived:
        return False
    hole = locs.query().name('Hole').within(8).nearest()
    item = cabbage()
    if hole is None or item is None or not item.use_on(hole):
        return False
    sabotaged = yield from execution.delay_until(lambda: any(['successfully sabotaged' in text for text in chat_dialog.texts()]), 15000)
    if not sabotaged:
        return False
    answered = yield from drive_dialog([], log)
    return answered


def pick_cabbage(log):
    if cabbage() is not None:
        return True
    result = yield from reach.loc_op('Cabbage', 'Pick', CABBAGE_FIELD, lambda: cabbage() is not None, within=14, log=log)
    return result == 'done' and cabbage() is not None


def _gather_cabbage(snap, need=1):
    return quest_step('custom', name='pick cabbage', run=pick_cabbage)


blackknight = QuestModule(
    auto_retaliate=False,
    record=quest_record('blackknight'),
    bank=Tile(2946, 3369, 0),
    grind=['black knight', 'aggressive black knight'],
    read_stage=read_stage,
    gather={'cabbage': lambda snap, need=1: source_item(snap, 'Cabbage'),
            'iron chainbody': lambda snap, need=1: source_item(snap, IRON_CHAINBODY),
            'bronze med helm': lambda snap, need=1: source_item(snap, BRONZE_MED_HELM)},
    decide=decide,
)

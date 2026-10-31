"""Ported from rs2b0t's src/bot/api/ai/quests/defs/observatory/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.observatory.areas import OBS_QUEST, OBS_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests
import _core

__all__ = ['parse_observatory_journal', 'read_observatory_stage']

# Why: `itgronigen_journal.rs2` appends, so every earlier stage's text is still on the page and only the newest paragraph separates one stage from the next.
# Why: the tests run highest-first; the completion page still lists "1 lens mould" and the lens page still says "molten glass".
MARKERS = [
    Record({'stage': OBS_STAGE.COMPLETE, 'text': 'quest complete!'}),
    Record({'stage': OBS_STAGE.SENT_TELESCOPE, 'text': 'gone ahead to the observatory'}),
    Record({'stage': OBS_STAGE.GIVEN_MOULD, 'text': 'create the lens by using the molten glass'}),
    Record({'stage': OBS_STAGE.GIVEN_GLASS, 'text': '1 lens mould'}),
    Record({'stage': OBS_STAGE.GIVEN_BRONZE, 'text': '1 molten glass'}),
    Record({'stage': OBS_STAGE.GIVEN_PLANKS, 'text': '1 bronze bar'}),
    Record({'stage': OBS_STAGE.STARTED, 'text': '3 wooden planks'}),
    Record({'stage': OBS_STAGE.NOT_STARTED, 'text': 'i can start this quest by talking to the'}),
]


def parse_observatory_journal(lines):
    """The `%itgronigen` value the rendered journal describes, or undefined for an unreadable page."""
    text = normalize(lines)
    hit = ([m for m in MARKERS if m.text in text] or [None])[0]
    return hit.stage if hit is not None else None


def read_observatory_stage():
    status = quests.status(OBS_QUEST)
    if status == 'complete':
        return OBS_STAGE.COMPLETE
    if status == 'not_started':
        return OBS_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(OBS_QUEST)
    stage = parse_observatory_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return stage

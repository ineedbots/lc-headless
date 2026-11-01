"""Ported from rs2b0t's src/bot/api/ai/quests/defs/elementalworkshop/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['ELEMENTAL_WORKSHOP_QUEST', 'EW_STAGE', 'EW_FLAG', 'parse_elemental_workshop_journal', 'read_elemental_workshop_progress']

ELEMENTAL_WORKSHOP_QUEST = 'Elemental Workshop'
# Why: the journal appends the water, bellows and furnace paragraphs while the entered branch is active, so they're flags.
EW_STAGE = Record({'NOT_STARTED': 0, 'READ_BOOK': 1, 'SLASHED': 2, 'ENTERED': 3, 'COMPLETE': 4})
EW_FLAG = Record({'WATER': 'water-flowing', 'BELLOWS': 'bellows-fixed', 'FURNACE': 'furnace-lit', 'MADE_BAR': 'made-bar'})


def read_flags(text):
    flags = set()
    if ('waterwheel in the northern water' in text) or ('water wheel in the northern water' in text) or ('get the waterwheel' in text) or ('get the water wheel' in text):
        flags.add(EW_FLAG.WATER)
    if ('bellows in the eastern air area are now fixed' in text) or ('stitch some leather' in text):
        flags.add(EW_FLAG.BELLOWS)
    if ('lit the furnace with lava' in text) or ('using the stone bowl' in text):
        flags.add(EW_FLAG.FURNACE)
    if ('made a bar from the elemental ore' in text) or ('just need to make something from it' in text):
        flags.add(EW_FLAG.MADE_BAR)
    return flags


def read_stage(text):
    # Newest branch first: later text retains earlier history.
    if ('quest complete!' in text):
        return EW_STAGE.COMPLETE
    if ('secret door in the seers village smithy' in text) or ('there is obviously lots to do here' in text) or ('made a bar from the elemental ore' in text) or ('managed to get the waterwheel' in text) or ('managed to get the water wheel' in text) or ('bellows in the eastern air area' in text) or ('lit the furnace with lava' in text):
        return EW_STAGE.ENTERED
    if ('cutting open the spine of the book' in text) or ('key hidden under the leather binding' in text):
        return EW_STAGE.SLASHED
    if ('found a battered book' in text) or ('tells of magic ore and a workshop' in text):
        return EW_STAGE.READ_BOOK
    if ('i can start this quest by reading a' in text):
        return EW_STAGE.NOT_STARTED
    return None


def parse_elemental_workshop_journal(lines):
    text = normalize(lines)
    stage = read_stage(text)
    if stage is None:
        return None
    return QuestProgress(stage, read_flags(text))


def read_elemental_workshop_progress():
    status = quests.status(ELEMENTAL_WORKSHOP_QUEST)
    if status == 'complete':
        return QuestProgress(EW_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(EW_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(ELEMENTAL_WORKSHOP_QUEST)
    progress = parse_elemental_workshop_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.interfaces import interfaces
from rs2004.quests.defs.piratestreasure.areas import PT_QUEST, PT_STAGE
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests


__all__ = ['parse_pirates_treasure_journal', 'read_pirates_treasure_progress']

def read_stage(text):
    if ('quest complete!' in text):
        return PT_STAGE.COMPLETE
    if ('the note reads' in text):
        return PT_STAGE.READ_NOTE
    if ('i have given the rum to' in text):
        return PT_STAGE.RECEIVED_KEY
    if ('he has agreed to tell me' in text):
        return PT_STAGE.FETCH_RUM
    if ('i can start this quest by speaking to' in text):
        return PT_STAGE.NOT_STARTED
    return None


# Why: the page keeps every earlier line struck through, so an early needle still matches late and only this order separates them.
# Why: `rum-lost` leads because the lost-rum page is reachable with every shipping line already behind it.
SMUGGLE = [
    ['but i seem to have lost it', 'rum-lost'],
    ['i should take it to redbeard frank', 'rum-in-hand'],
    ["i have taken a job at wydin's store", 'store-job'],
    ['the crate has been shipped to', 'rum-shipped'],
    ['in the crate and filled it with bananas', 'crate-full'],
    ['i should fill it with', 'rum-in-crate'],
    ['hide my rum in the next crate', 'rum-held-employed'],
    ['now all i need is some rum', 'employed-need-rum'],
    ['find a way to get the rum off', 'rum-held-unemployed'],
    ['and buy some rum', 'need-rum'],
]


def parse_pirates_treasure_journal(lines):
    text = normalize(lines)
    stage = read_stage(text)
    if stage is None:
        return None
    flags = set()
    if stage == PT_STAGE.FETCH_RUM:
        hit = ([needle for needle in SMUGGLE if (needle[0] in text)] or [None])[0]
        if hit:
            flags.add(hit[1])
    return Record({'stage': stage, 'flags': flags})


last_good = None


def read_pirates_treasure_progress():
    global last_good
    status = quests.status(PT_QUEST)
    if status == 'complete':
        return Record({'stage': PT_STAGE.COMPLETE, 'flags': set()})
    if status == 'not_started':
        return Record({'stage': PT_STAGE.NOT_STARTED, 'flags': set()})
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(PT_QUEST)
    progress = parse_pirates_treasure_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/journal.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.engine.types import QuestProgress

import _core

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.tbwt.areas import TBWT_QUEST, TB_LUBUFU, TB_MAIN, TB_TAMAYU, TB_TINSAY, TB_VARP
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['TB_FLAG', 'parse_tbwt_journal', 'reset_tbwt_progress_cache', 'read_tbwt_progress']

TB_FLAG = Record({
    'TIADECHE': 'tiadeche',
    'TINSAY': 'tinsay',
    'TAMAYU': 'tamayu',
    'LUBUFU': 'lubufu',
    'AGILITY': 'agility',
    'SPEAR': 'spear',
})
LABELS = ['tiadeche', 'tinsay', 'tamayu', 'lubufu']


# Why: every brother's block is appended in a fixed order and "Nothing of interest." is the intro line for 3 of them, so a marker only counts inside its own section.
def section(text, label):
    """The slice of the page between one brother's heading and the next."""
    start = text.find(f'{label}:')
    if start < 0:
        return ''
    end = len(text)
    for other in LABELS:
        at = text.find(f'{other}:', start + len(label) + 1)
        if at >= 0 and at < end:
            end = at
    return text[start:end]


def first_match(text, markers):
    """Newest marker first: every later stage re-prints the lines of the ones before it."""
    hit = ([marker for marker in markers if marker[0] in text] or [None])[0]
    return None if hit is None else hit[1]


TINSAY_MARKERS = [
    ['marinated in karambwanji paste.', TB_TINSAY.COMPLETE],
    ['he requires burnt jogre bones', TB_TINSAY.FETCH_BONES],
    ['i have given him a seaweed in monkey skin sandwich.', TB_TINSAY.GIVEN_SANDWICH],
    ['he requires a seaweed in monkey skin sandwich', TB_TINSAY.FETCH_SANDWICH],
    ['i have given him sliced banana in karamja rum.', TB_TINSAY.GIVEN_RUM],
    ['he requires banana in karamja rum', TB_TINSAY.FETCH_RUM],
    ['nothing of interest.', TB_TINSAY.INTRO],
]
TAMAYU_MARKERS = [
    ['tamayu has slain the shaikahan!', TB_TAMAYU.COMPLETE],
    ['he appears to be having difficulty in the hunt.', TB_TAMAYU.WATCHED_CUTSCENE],
    ['once he has slain', TB_TAMAYU.SLAY_SHAIKAHAN],
    ['nothing of interest.', TB_TAMAYU.INTRO],
]
# Why: `became_apprentice` and `complete` render the same page, and the first is a single tick inside the second's own dialogue, so both read as complete.
LUBUFU_MARKERS = [
    ["i have accepted lubufu's offer.", TB_LUBUFU.COMPLETE],
    ['lubufu has offered to train me as his apprentice.', TB_LUBUFU.OFFERED_APPRENTICE],
    ['i have given lubufu 20 karambwanji.', TB_LUBUFU.GIVEN_KARAMBWANJI],
    ['i need to give lubufu 20 karambwanji.', TB_LUBUFU.FETCH_KARAMBWANJI],
    ['lubufu has accepted', TB_LUBUFU.FETCH_KARAMBWANJI],
    ['i have offered to help collect bait', TB_LUBUFU.OFFERED_TO_HELP],
    ['lubufu is a crochety old fisherman', TB_LUBUFU.INITIAL_OPS],
]


def parse_tbwt_journal(lines):
    """Sub-progress for the 3 brothers the client has no varp for; `main` and `tiadeche` come from their transmitted varps. Why: undefined marks a page that did not render, so it isn't mistaken for a quest at zero."""
    text = normalize(lines)
    # Every in-progress page opens by naming the 3 sons; a blank read is a modal that never opened.
    if not ('sons of' in text):
        return None
    flags = set()
    tinsay = first_match(section(text, 'tinsay'), TINSAY_MARKERS)
    flags.add(f'{TB_FLAG.TINSAY}:{(tinsay if tinsay is not None else TB_TINSAY.UNKNOWN)}')
    tamayu_text = section(text, 'tamayu')
    tamayu = first_match(tamayu_text, TAMAYU_MARKERS)
    flags.add(f'{TB_FLAG.TAMAYU}:{(tamayu if tamayu is not None else TB_TAMAYU.UNKNOWN)}')
    if ('i have increased his agility' in tamayu_text):
        flags.add(TB_FLAG.AGILITY)
    if ('karambwan poisoned spear' in tamayu_text):
        flags.add(TB_FLAG.SPEAR)
    # Why: the 2 lines are only written while he is still hunting; past the kill both are facts.
    if tamayu is not None and tamayu >= TB_TAMAYU.COMPLETE:
        flags.add(TB_FLAG.AGILITY)
        flags.add(TB_FLAG.SPEAR)
    # Why: the block is skipped below `initial_ops`, so a missing section means "not spoken to yet".
    lubufu = first_match(section(text, 'lubufu'), LUBUFU_MARKERS)
    flags.add(f'{TB_FLAG.LUBUFU}:{(lubufu if lubufu is not None else TB_LUBUFU.UNKNOWN)}')
    return flags


last_good = None


def reset_tbwt_progress_cache():
    global last_good
    last_good = None


# Why: the journal is only opened during the brothers phase; before it the 2 varps say everything, after it the quest is one talk from done.
def read_tbwt_progress():
    global last_good
    status = quests.status(TBWT_QUEST)
    if status == 'unknown':
        return None
    if status == 'complete':
        return QuestProgress(TB_MAIN.COMPLETE, set())
    main = reader.varp(TB_VARP.MAIN)
    tiadeche = reader.varp(TB_VARP.TIADECHE)
    if main != TB_MAIN.STARTED:
        return QuestProgress(main, set([f'{TB_FLAG.TIADECHE}:{tiadeche}']))
    _w3 = yield from quests.journal(TBWT_QUEST)
    flags = parse_tbwt_journal(_w3)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    # A page that rendered nothing is a failed read.
    if not flags:
        return last_good
    flags.add(f'{TB_FLAG.TIADECHE}:{tiadeche}')
    last_good = QuestProgress(main, flags)
    return last_good

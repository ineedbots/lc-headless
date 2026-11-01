"""Ported from rs2b0t's src/bot/api/ai/quests/defs/horror/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.horror.areas import HD_QUEST, HD_STAGE
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['HD_FLAG', 'parse_horror_journal', 'read_horror_progress']

_TAG_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'
HD_FLAG = Record({'BRIDGE': 'bridge', 'KEY': 'key', 'GLASS': 'glass', 'TAR': 'tar', 'LIGHT': 'light'})


# Why: `@str@` is the only oracle for the bridge, and `~quest_journal`'s `split_init` wrapper re-emits active tags at the head of every line, so the struck line arrives as `@str@@bla@I need to repair...` and the other tags must be stripped.
def struck(lines):
    """Normalise journal lines, keeping only the `@str@` marker."""
    text = lines if isinstance(lines, str) else ' '.join(lines)
    # pocketpy's character indexing fails on the loading ellipsis in journal placeholders.
    text = text.replace('…', '...')
    out = ''
    i = 0
    while i < len(text):
        if text[i] == '@' and i + 4 < len(text) and text[i + 4] == '@':
            tag = text[i + 1:i + 4].lower()
            if tag != 'str' and tag[0] in _TAG_CHARS and tag[1] in _TAG_CHARS and tag[2] in _TAG_CHARS:
                i += 5
                continue
        out += text[i]
        i += 1
    return ' '.join(out.replace('|', ' ').split()).lower()


def bridge_done(tagged):
    return ('@str@i need to repair the bridge' in tagged) or ('@str@ i need to repair the bridge' in tagged)


def read_stage(text):
    """Newest marker first: horror_journal.rs2 appends, so earlier prose is still on the scroll."""
    if ('quest complete!' in text):
        return HD_STAGE.COMPLETE
    if ('i must defeat these sea monsters' in text):
        return HD_STAGE.DEFEATED_DAGJR
    if ('i found jossik in an underground cavern' in text):
        return HD_STAGE.DEFEATED_DAGJR
    if ('i must search this place' in text):
        return HD_STAGE.REPAIRED_LIGHTHOUSE
    if ('i managed to repair the lighthouse light' in text):
        return HD_STAGE.REPAIRED_LIGHTHOUSE
    if ('now i need to find some way of' in text):
        return HD_STAGE.ENTERED_LIGHTHOUSE
    if ('i repaired the bridge leading to rellekka and got a key' in text):
        return HD_STAGE.ENTERED_LIGHTHOUSE
    if ('larrissa is very worried about her boyfriend' in text):
        return HD_STAGE.STARTED
    if ('i can start this quest by speaking to' in text):
        return HD_STAGE.NOT_STARTED
    return None


# Why: both bridge lines say the same words, `@str@` for done and `@dbl@` for outstanding, so that flag is read off the tagged text.
def read_flags(text, tagged):
    """Read the journal's progress flags."""
    flags = set()
    if bridge_done(tagged):
        flags.add(HD_FLAG.BRIDGE)
    if ('use the key i got from gunnjorn' in text):
        flags.add(HD_FLAG.KEY)
    if ('i have fixed the lighthouse lens' in text):
        flags.add(HD_FLAG.GLASS)
    if ('i have re-tarred the lighthouse torch' in text):
        flags.add(HD_FLAG.TAR)
    if ('i have relit the lighthouse torch' in text):
        flags.add(HD_FLAG.LIGHT)
    return flags


def parse_horror_journal(lines):
    text = normalize(lines)
    stage = read_stage(text)
    if stage is None:
        return None
    flags = read_flags(text, struck(lines))
    # Why: past the bridge stage the journal folds both errands into one struck-out line, so the flags have to be re-asserted or every later decide() reads the bridge as unbuilt.
    if stage >= HD_STAGE.ENTERED_LIGHTHOUSE:
        flags.add(HD_FLAG.BRIDGE)
        flags.add(HD_FLAG.KEY)
    if stage >= HD_STAGE.REPAIRED_LIGHTHOUSE:
        flags.add(HD_FLAG.GLASS)
        flags.add(HD_FLAG.TAR)
        flags.add(HD_FLAG.LIGHT)
    return QuestProgress(stage, flags)


last_good = None


def tagged_page(lines):
    """The open page with its colour tags, which quests.journal's lines have lost and the bridge flag reads."""
    main = reader.modals().main
    if main == -1:
        return lines
    return [c.text for c in _core.get_interface(main) if c.text and c.visible]


def read_horror_progress():
    global last_good
    status = quests.status(HD_QUEST)
    if status == 'complete':
        return QuestProgress(HD_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(HD_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(HD_QUEST)
    progress = parse_horror_journal(tagged_page(lines))
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.fremenniktrials.areas import FT_NAME
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['FT_STAGE', 'TRIALS', 'parse_fremennik_journal', 'reset_fremennik_journal_cache', 'read_fremennik_progress']

FT_STAGE = Record({'NOT_STARTED': -1, 'COMPLETE': 100})
TRIALS = ['navigator', 'merchant', 'hunter', 'seer', 'warrior', 'reveller', 'bard']
MERCHANT_STEPS = [
    ['all askeladden wants is some money', 'thora'],
    ['the reveller is looking for a legendary cocktail', 'manni'],
    ['the warrior is looking for a champions token', 'thorvald'],
    ['the seer is looking for a warrior to be his bodyguard', 'seer'],
    ['the navigator is looking for a weather forecast', 'swensen'],
    ['the fisherman is looking for a map of fishing spots', 'fisherman'],
    ['the armourer is looking for a rare inedible fish', 'skul'],
    ['the hunter is looking for a custom bowstring', 'sigli'],
    ['the chieftan wants a map of new hunting grounds', 'chief'],
    ['the shopkeeper is looking for a tax reduction', 'yrsa'],
    ['the bard is looking for some new boots', 'olaf'],
]
VOTES = [
    ['i have seven votes', 7],
    ['i have six votes so far', 6],
    ['i have five votes so far', 5],
    ['i have four votes so far', 4],
    ['i have three votes so far', 3],
    ['i have two votes so far', 2],
    ['i have one vote so far', 1],
    ["i don't have any votes yet", 0],
]


def parse_fremennik_journal(lines):
    text = normalize(lines)
    if len(text) == 0:
        return None
    if ('quest complete!' in text):
        return QuestProgress(FT_STAGE.COMPLETE)
    if not ('council' in text):
        return None
    flags = set()
    for trial in TRIALS:
        if (f'i now have the {trial}\'s vote' in text):
            flags.add(f'{trial}-done')
        elif (f'the {trial} will vote for me if i can pass his trial' in text):
            flags.add(f'{trial}-started')
    step = ([(needle, _2) for needle, _2 in MERCHANT_STEPS if (needle in text)] or [None])[0]
    if step:
        flags.add(f'merchant-at:{step[1]}')
    votes = ([(needle, _2) for needle, _2 in VOTES if (needle in text)] or [None])[0]
    return QuestProgress(votes[1] if votes else 0, flags)


last_good = None


def reset_fremennik_journal_cache():
    global last_good
    last_good = None


def read_fremennik_progress():
    global last_good
    status = quests.status(FT_NAME)
    if status == 'complete':
        return QuestProgress(FT_STAGE.COMPLETE)
    if status == 'not_started':
        return QuestProgress(FT_STAGE.NOT_STARTED)
    if status != 'in_progress':
        return None
    _w3 = yield from quests.journal(FT_NAME)
    progress = parse_fremennik_journal(_w3)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress:
        last_good = progress
    return (progress if progress is not None else last_good)

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/deathplateau/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests

__all__ = ['DEATH_PLATEAU_QUEST', 'DP_STAGE', 'DP_FLAG', 'parse_death_plateau_journal', 'read_death_plateau_progress']

DEATH_PLATEAU_QUEST = 'Death Plateau'
DP_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 10,
    'SPOKEN_EOHRIC': 20,
    'SPOKEN_HAROLD': 30,
    'SPOKEN_EOHRIC2': 40,
    'GIVEN_ALE': 50,
    'GIVEN_IOU': 55,
    'FOUND_COMBO': 60,
    'UNLOCKED_DOOR': 70,
    'COMPLETE': 80,
})
DP_FLAG = Record({
    'SABA': 'saba',
    'TENZING': 'tenzing',
    'SMITHY': 'smithy',
    'ENTRANCE_CERT': 'entrancecert',
    'GIVEN_CERT': 'given_cert',
    'SUPPLIES': 'supplies',
    'GOT_MAP': 'got_map',
    'SCOUTED': 'scouted',
})


def read_equip_stage(text):
    # Newest first: later paragraphs retain earlier history.
    if ('quest complete!' in text):
        return DP_STAGE.COMPLETE
    if ('i can start this quest' in text):
        return DP_STAGE.NOT_STARTED
    if ('unlocked the door' in text) or ('found the combination to the equipment room and unlocked' in text):
        return DP_STAGE.UNLOCKED_DOOR
    if ('written on the back of the combination' in text):
        return DP_STAGE.FOUND_COMBO
    if ('wrote me an iou' in text) or ('he wrote me an iou' in text):
        return DP_STAGE.GIVEN_IOU
    if ('bought the guard a drink' in text):
        return DP_STAGE.GIVEN_ALE
    if ('buy the guard a drink' in text) or ('eohric says to buy' in text):
        return DP_STAGE.SPOKEN_EOHRIC2
    if ("wouldn't talk to me" in text) or ('wouldnt talk to me' in text):
        return DP_STAGE.SPOKEN_HAROLD
    if ('equipment room guard is staying' in text) or ('eohric said that the equipment room guard' in text) or (('toad and chicken' in text) and ('equipment room guard' in text)):
        return DP_STAGE.SPOKEN_EOHRIC
    if ('offered to help denulth' in text) or ('finding another way' in text) or ('another way up death plateau' in text) or ('combination to the equipment room' in text):
        return DP_STAGE.STARTED
    return None


def read_map_flags(text):
    flags = set()
    # Past-tense only: "I need to check that the secret way is safe" must not match.
    if ('checked the secret way' in text) or ('and it is safe for the imperial' in text) or ('i checked the secret way' in text):
        flags.add(DP_FLAG.SCOUTED)
    if ('map of the secret way' in text) or ('has given me a map' in text) or ('need to check that the secret way' in text):
        flags.add(DP_FLAG.GOT_MAP)
    if ('gave tenzing the ten loaves' in text) or ('gave tenzing the ten loaves of bread' in text) or ('ten cooked trout and the spiked boots' in text):
        flags.add(DP_FLAG.SUPPLIES)
    # "Dunstan made me the Spiked boots" appears after supplies and when only the boots are done; given_cert is the stronger hand-in signal.
    if ('given dunstan the certificate' in text) or ('i have given dunstan the certificate' in text) or ('dunstan made me the spiked boots' in text):
        flags.add(DP_FLAG.GIVEN_CERT)
    if ('denulth gave me a certificate' in text):
        flags.add(DP_FLAG.ENTRANCE_CERT)
    if ('dunstan will help me if i get his son' in text) or ('son signed up for the imperial guard' in text):
        flags.add(DP_FLAG.SMITHY)
    if ('tenzing will show me a secret way' in text) or ('ten loaves of bread' in text) or ('found the sherpa' in text) or ('climbing boots' in text):
        flags.add(DP_FLAG.TENZING)
    if ('saba says that there is a sherpa' in text) or ('saba says that there is a sherpa living' in text):
        flags.add(DP_FLAG.SABA)
    # Cascading: later map milestones imply earlier ones.
    if (DP_FLAG.SCOUTED in flags):
        flags.add(DP_FLAG.GOT_MAP)
        flags.add(DP_FLAG.SUPPLIES)
        flags.add(DP_FLAG.GIVEN_CERT)
        flags.add(DP_FLAG.ENTRANCE_CERT)
        flags.add(DP_FLAG.SMITHY)
        flags.add(DP_FLAG.TENZING)
        flags.add(DP_FLAG.SABA)
    elif (DP_FLAG.GOT_MAP in flags) or (DP_FLAG.SUPPLIES in flags):
        flags.add(DP_FLAG.GIVEN_CERT)
        flags.add(DP_FLAG.ENTRANCE_CERT)
        flags.add(DP_FLAG.SMITHY)
        flags.add(DP_FLAG.TENZING)
        flags.add(DP_FLAG.SABA)
    else:
        if (DP_FLAG.GIVEN_CERT in flags):
            flags.add(DP_FLAG.ENTRANCE_CERT)
            flags.add(DP_FLAG.SMITHY)
            flags.add(DP_FLAG.TENZING)
            flags.add(DP_FLAG.SABA)
        elif (DP_FLAG.ENTRANCE_CERT in flags):
            flags.add(DP_FLAG.SMITHY)
            flags.add(DP_FLAG.TENZING)
            flags.add(DP_FLAG.SABA)
        else:
            if (DP_FLAG.SMITHY in flags):
                flags.add(DP_FLAG.TENZING)
                flags.add(DP_FLAG.SABA)
            elif (DP_FLAG.TENZING in flags):
                flags.add(DP_FLAG.SABA)
    return flags


# Why: stage is the equip-room track and the map bits are flags.
# Why: live journals always open with the equip-room lines, but unit tests and a partial journal open may carry only map paragraphs.
# Why: progress is still emitted at stage STARTED when only map paragraphs are present.
def parse_death_plateau_journal(lines):
    """Turn journal lines into quest progress."""
    text = normalize_journal(lines)
    flags = read_map_flags(text)
    stage = read_equip_stage(text)
    if stage is None:
        if len(flags) == 0:
            return None
        stage = DP_STAGE.STARTED
    return QuestProgress(stage, flags)


def read_death_plateau_progress():
    status = quests.status(DEATH_PLATEAU_QUEST)
    if status == 'complete':
        return QuestProgress(DP_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(DP_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w1 = yield from quests.journal(DEATH_PLATEAU_QUEST)
    progress = parse_death_plateau_journal(_w1)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/journal.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.game import reader
from rs2004.quests.defs.legends.areas import LEGENDS_QUEST, LQ_STAGE
from rs2004.quests.engine.types import QuestProgress
from rs2004.quests.journal_text import normalize_journal as normalize
from rs2004.tabs import quests

__all__ = ['parse_legends_journal', 'reset_legends_progress', 'read_legends_progress']

# Why: the journal is cumulative, every entry keeps the earlier history, so the newest line present names the stage.
# Why: stages 35 and 40 render identically, as the "I replaced the evil totem" line is gated on 45 and nothing else separates them; `decide()` splits that pair by what is carried.
# Needles avoid anything a colour tag sits next to: stripping "@dbl@" leaves a space, so "Ungadulu@dbl@." normalises to "ungadulu .".
STAGE_LINES = [
    ['quest complete!', LQ_STAGE.COMPLETE],
    ['radimus has given me four training sessions as reward', LQ_STAGE.TRAINING_4],
    ['radimus has given me three training sessions as reward', LQ_STAGE.TRAINING_3],
    ['radimus has given me two training sessions as reward', LQ_STAGE.TRAINING_2],
    ['radimus has given me one training session as reward', LQ_STAGE.TRAINING_1],
    ['radimus asked me to join him inside the legends guild', LQ_STAGE.RETURNED_TO_RADIMUS],
    ["i've handed the totem pole and map over to radimus", LQ_STAGE.RETURNED_TO_RADIMUS],
    ['i replaced the evil totem with the good one i made', LQ_STAGE.GOT_GILDED_TOTEM],
    ['i fought nezikchened and finally defeated him', LQ_STAGE.DEFEATED_NEZI_FINAL],
    ['i fought them all and eventually defeated nezikchened', LQ_STAGE.DEFEATED_NEZI_FINAL],
    ['i have to defeat the demon nezikchened', LQ_STAGE.SPAWNED_NEZI_FINAL],
    ["i've got a yommi tree totem pole", LQ_STAGE.COLLECTED_TOTEM],
    ['i can now try to grow a yommi tree', LQ_STAGE.SACRED_WATER],
    ['i need to collect some sacred water in order to grow a yommi tree', LQ_STAGE.DEFEATED_NEZI_WATER],
    ['the spirit gave me a dagger and said i have to kill viyeldi', LQ_STAGE.RECEIVED_DAGGER],
    ['a strange spirit seems to be guarding the sacred water', LQ_STAGE.PUSHED_BOULDER],
    ['i made a glowing dragon heart stone from chunks of', LQ_STAGE.HEART_IN_RECESS],
    ['i fixed chunks of crystal into dragon heart shape', LQ_STAGE.CRYSTAL_SMELTED],
    ["i'm able to access the viyeldi caves", LQ_STAGE.ENTER_LOWER_DUNGEON],
    ['i need to find the viyeldi caves and the source of the', LQ_STAGE.TALK_GUJUO_POOL],
    ['gujuo said the viyeldi caves might be the source', LQ_STAGE.TALK_GUJUO_POOL],
    ['i need to make the bravery potion using the snake weed', LQ_STAGE.TALK_GUJUO_POOL],
    ['i need to get some more sacred water in order for the yommi tree', LQ_STAGE.POOL_DRIED],
    ['i have some germinated yommi tree seeds', LQ_STAGE.GERMINATED_SEEDS],
    ['i used the book of binding to force the demon', LQ_STAGE.DEFEATED_NEZI_FIRE],
    ['i need to release ungadulu so that i can get some yommi tree seeds', LQ_STAGE.SUMMONED_NEZI_FIRE],
    ['ungadulu mentioned that it may help me to get closer', LQ_STAGE.FILLED_BOWL],
    ['gujuo mentioned a blessed vessel', LQ_STAGE.ASKED_GUJUO_WATER],
    ['now i need some sacred water', LQ_STAGE.ASKED_GUJUO_WATER],
    ['now it needs to be blessed', LQ_STAGE.ASKED_GUJUO_WATER],
    ['is acting weird and talking a lot of nonsense', LQ_STAGE.SPOKE_UNGADULU],
    ['i need to get some yommi tree seeds from ungadulu', LQ_STAGE.FOUND_ENTRANCE],
    ['i agreed to help gujuo by releasing a shaman', LQ_STAGE.ACCEPTED_RESCUE],
    ['which i used to attract', LQ_STAGE.SWUNG_BULLROARER],
    ['a kharazi jungle native', LQ_STAGE.SWUNG_BULLROARER],
    ['which may attract a native', LQ_STAGE.GOT_BULLROARER],
    ['i have mapped the kharazi jungle for radimus erkle', LQ_STAGE.MAPPED_JUNGLE],
    ['asked me to map the kharazi jungle', LQ_STAGE.STARTED],
    ['i can start this quest by speaking to', LQ_STAGE.NOT_STARTED],
]
FLAG_LINES = [
    ["i've killed viyeldi with a dagger the spirit gave me", 'killed-viyeldi'],
    ['i was tricked by the demon into killing viyeldi', 'killed-viyeldi'],
    ['i killed viyeldi with the black dagger and i returned it to', 'killed-viyeldi'],
    ['i killed viyeldi with the black dagger and i returned it to', 'given-dagger'],
    ['i told ungadulu about the spirit', 'told-ungadulu'],
]


# Why: the one sub-progress the stage number can't carry: the 3 crystal sections live in `%legends_bits`, which never reaches the client.
def crystals_placed(text):
    if ("i've place some crystal chunks in a lava furnace" in text):
        return 2
    if ("i've placed a crystal chunk in a lava furnace" in text):
        return 1
    return 0


def read_flags(text):
    flags = set()
    for needle, flag in FLAG_LINES:
        if (needle in text):
            flags.add(flag)
    flags.add(f'crystals-placed:{crystals_placed(text)}')
    return flags


def parse_legends_journal(lines):
    text = normalize(lines)
    for needle, stage in STAGE_LINES:
        if needle in text:
            return QuestProgress(stage, read_flags(text))
    return None


# Why: a read taken while a message box is up comes back empty, and this quest raises one for nearly every action it takes, mapping, mining, jumping, climbing.
# Why: the stage only ever moves forward, so the last one read is a sound floor to act on where `wait` would stall the leg.
_last_read = [None]


def reset_legends_progress():
    """Forget the cached progress. Tests and a fresh account want a clean slate."""
    _last_read[0] = None


def read_legends_progress():
    status = quests.status(LEGENDS_QUEST)
    if status == 'complete':
        _last_read[0] = QuestProgress(LQ_STAGE.COMPLETE, set())
        return _last_read[0]
    if status == 'not_started':
        _last_read[0] = QuestProgress(LQ_STAGE.NOT_STARTED, set())
        return _last_read[0]
    if status != 'in_progress':
        return _last_read[0]
    lines = yield from quests.journal(LEGENDS_QUEST)
    progress = parse_legends_journal(lines)
    # Why: the journal is a main modal, and leaving it up makes every later read come back empty.
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    if progress is not None:
        _last_read[0] = progress
        return progress
    return _last_read[0]

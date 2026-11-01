"""rs2b0t's test/api/ai/quests/defs/chompybird-resume.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs.record import Record
from rs2004.game import skills
from rs2004.quests.defs.chompybird import decide
from rs2004.quests.defs.chompybird.areas import CB_ID, CB_STAGE
from rs2004.quests.defs.chompybird.cook import cook_state
from rs2004.quests.defs.chompybird.hunt import chest_state
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot

# Why: the quest is killed and restarted from any point, so every reachable (stage, pack) pair has to
# name a next move rather than a wait, a wait with nothing to resolve it parks the queue after fifteen ticks.
STAGES = [
    CB_STAGE.NOT_STARTED,
    CB_STAGE.STARTED,
    CB_STAGE.GIVEN_ARROWS,
    CB_STAGE.KIDS_PLAY_WITH_TOAD,
    CB_STAGE.REMOVED_ROCK,
    CB_STAGE.SHOWN_TOAD,
    CB_STAGE.DROPPED_TOAD,
    CB_STAGE.CHOMPY_SPAWNED,
    CB_STAGE.RANTZ_MISSED,
    CB_STAGE.GOT_BOW,
    CB_STAGE.KILLED_CHOMPY,
    CB_STAGE.TOLD_TO_COOK,
    CB_STAGE.CHOMPY_COOKED,
]
PACKS = [
    Record({'name': 'nothing but the loadout', 'inv_ids': []}),
    Record({'name': 'knife and chisel', 'inv_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1]]}),
    Record({'name': 'a log part-way to a shaft', 'inv_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1], [CB_ID.ACHEY_LOGS, 2]]}),
    Record({'name': 'six shafts and no tips', 'inv_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1], [CB_ID.SHAFT, 6]]}),
    Record({
    'name': 'flighted arrows waiting on tips',
    'inv_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1], [CB_ID.FLIGHTED, 6]],
}),
    Record({'name': 'a full quiver', 'inv_ids': [[CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1], [CB_ID.ARROW, 12]]}),
    Record({'name': 'bellows and bait', 'inv_ids': [[CB_ID.BELLOWS1, 1], [CB_ID.TOAD, 2]]}),
    Record({'name': 'bow, arrows and bellows', 'inv_ids': [[CB_ID.BOW, 1], [CB_ID.ARROW, 6], [CB_ID.BELLOWS3, 1]]}),
    Record({'name': 'a plucked chompy', 'inv_ids': [[CB_ID.RAW_CHOMPY, 1], [CB_ID.BOW, 1], [CB_ID.ARROW, 4]]}),
    Record({'name': 'a seasoned chompy', 'inv_ids': [[CB_ID.SEASONED_CHOMPY, 1]]}),
    Record({
    'name': 'every seasoning and a bird',
    'inv_ids': [
    [CB_ID.RAW_CHOMPY, 1],
    [CB_ID.POTATO, 1],
    [CB_ID.ONION, 1],
    [CB_ID.CABBAGE, 1],
    [CB_ID.TOMATO, 1],
    [CB_ID.EQUA, 1],
    [CB_ID.DOOGLE, 1],
],
}),
]


def snap(stage, inv_ids):
    """An established account: the bank holds every tool this quest can fall back on."""
    return QuestSnapshot(**{
        'journal': ('not_started' if stage == CB_STAGE.NOT_STARTED else 'in_progress'),
        'inv': {_k: _v for _k, _v in [['coins', 2000], ['trout', 6], ['bronze axe', 1]]},
        'inv_ids': {_k: _v for _k, _v in [[CB_ID.FEATHER, 48]] + list(inv_ids)},
        'worn': set(['rune scimitar', 'rune chainbody', 'rune platelegs', 'rune full helm', 'rune kiteshield']),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 2000000,
        'stage': stage,
        'progress': QuestProgress(stage, set()),
        'bank': {_k: _v for _k, _v in [['coins', 2000000], ['bronze axe', 1], ['lobster', 40]]},
        'bank_ids': {_k: _v for _k, _v in [[CB_ID.FEATHER, 500], [CB_ID.KNIFE, 1], [CB_ID.CHISEL, 1], [CB_ID.BELLOWS_EMPTY, 1]]},
        'bank_known': True,
        'tile': Record({'x': 2630, 'z': 2981, 'level': 0}),
        'free_slots': 18,
    })


def resumes(chest_refused, kids_asked, stage, pack):
    def check():
        spy_on(skills, 'level', impl=lambda skill: 70)
        chest_state.refused = chest_refused
        cook_state.kids_asked = kids_asked
        step = decide(snap(stage, pack.inv_ids))
        expect(step.kind).not_.to_be('wait')
        expect(step.kind).not_.to_be('done')
    return check


def _fn1():
    for chest_refused in [False, True]:
        for kids_asked in [False, True]:
            for stage in STAGES:
                for pack in PACKS:
                    test(f"stage {stage}, {pack.name}, chest {('refused' if chest_refused else 'untried')}, kids {('asked' if kids_asked else 'unasked')}", resumes(chest_refused, kids_asked, stage, pack))


describe('big chompy bird hunting resumes from anywhere', _fn1)

"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/scorpcatcher-resume.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.scorpcatcher import decide
from rs2004.quests.defs.scorpcatcher.areas import EVERY_CAGE, SC_STAGE
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.types import QuestProgress

STAGES = [SC_STAGE.STARTED, SC_STAGE.FIRST_HINT, SC_STAGE.SECOND_HINT]
WHERE = ['pack', 'bank', 'lost']


def snap(stage, cage, where):
    held = ({_k: _v for _k, _v in [[cage, 1]]} if where == 'pack' and cage is not None else {})
    banked = ({_k: _v for _k, _v in [[cage, 1]]} if where == 'bank' and cage is not None else {})
    return QuestSnapshot(**{
        'journal': 'in_progress',
        'inv': {},
        'inv_ids': held,
        'worn': set(),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': 5000,
        'progress': QuestProgress(stage, set()),
        'bank': {},
        'bank_ids': banked,
        'bank_known': True,
        'free_slots': 20,
    })


# Why: the engine restarts a killed run by re-deciding from the snapshot, so a state that answers `wait` is a state the quest can never leave.
def _fn1():
    def _fn2():
        parked = []
        for stage in STAGES:
            for where in WHERE:
                for cage in ([None] if where == 'lost' else EVERY_CAGE):
                    step = decide(snap(stage, cage, where))
                    if step.kind == 'wait' or step.kind == 'done':
                        parked.append(f"stage {stage} · cage {(cage if cage is not None else 'none')} in the {where} → {step.kind}")
        expect(parked).to_equal([])
    test('every stage and cage position decides on work to do', _fn2)

    def _fn3():
        for stage in STAGES:
            step = decide(snap(stage, None, 'lost'))
            expect(step.kind == 'talk' and step.stop.npc).to_be('Thormac')
    test('a lost cage is replaced rather than waited on', _fn3)

    # Why: a cage in the bank is the caught scorpions in the bank, and the journal cannot see them, so the withdraw has to name the exact obj.
    def _fn4():
        for stage in STAGES:
            for cage in EVERY_CAGE:
                step = decide(snap(stage, cage, 'bank'))
                expect(step.kind).to_be('withdraw')
                expect(step.kind == 'withdraw' and (step.items[0]['id'] if step.items[0] is not None else None)).to_be(cage)
    test('a banked cage is always withdrawn before anything else', _fn4)


describe('Scorpion Catcher resumability', _fn1)

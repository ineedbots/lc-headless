"""Rune Mysteries: rs2b0t's api/ai/quests/defs/runemysteries.ts (MIT, see thirdparty/rs2b0t). The Duke's talisman to
Sedridor under the Wizards' Tower, his package to Aubury, and Aubury's notes back."""

from rs2004.geometry import Tile
from rs2004.tabs import quests
from rs2004.dialogue import modals
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import LadderHop, NpcStop

__all__ = ['DUKE', 'SEDRIDOR', 'AUBURY', 'WIZARD_HOPS', 'RECOVER_PROBES', 'decide', 'runemysteries']

DUKE = NpcStop('Duke Horacio', Tile(3212, 3220, 1), 6, ['Have you any quests for me?', 'Sure, no problem.'])
SEDRIDOR = NpcStop('Sedridor', Tile(3103, 9572, 0), 8, ["I'm looking for the head wizard.", 'Ok, here you are.', 'Yes, certainly.'],
                   approach=[Tile(3108, 9572, 0)])
AUBURY = NpcStop('Aubury', Tile(3253, 3402, 0), 8, ['I have been sent here with a package for you.'])

WIZARD_HOPS = [
    LadderHop(Tile(3105, 3162, 0), 'Ladder', 'Climb-down', Tile(3104, 9576, 0), walk=Tile(3108, 3162, 0)),
    LadderHop(Tile(3104, 9576, 0), 'Ladder', 'Climb-up', Tile(3105, 3162, 0)),
]

RECOVER_PROBES = [AUBURY, SEDRIDOR, DUKE]


def _talk(stop):
    return quest_step('talk', stop=stop)


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return _talk(DUKE)
    stage = snap.progress.stage if snap.progress is not None else snap.stage
    if stage == 2:
        return _talk(SEDRIDOR)
    if stage == 4:
        return _talk(AUBURY)
    for name, stop in [('Notes', SEDRIDOR), ('Research package', AUBURY), ('Air talisman', SEDRIDOR)]:
        if snap.inv.get(name.lower(), 0) > 0:
            return _talk(stop)
        if (snap.bank or {}).get(name.lower(), 0) > 0:
            return quest_step('withdraw', items=[{'name': name, 'qty': 1}])
    if not snap.bank_known:
        return quest_step('scan_bank')
    return _talk(RECOVER_PROBES[snap.no_progress % len(RECOVER_PROBES)])


def parse_rune_mysteries_journal(lines):
    text = normalize_journal(lines)
    needles = ['i can start this quest by speaking to', 'i need to find the head wizard',
               'i should talk to the head wizard again', 'i should take this research package',
               'i should speak to aubury again', 'i should take the notes to sedridor', 'quest complete!']
    for stage, needle in enumerate(needles):
        if needle in text:
            return stage
    return None


def read_stage():
    status = quests.status(runemysteries.record.name)
    if status == 'complete':
        return 6
    if status == 'not_started':
        return 0
    if status != 'in_progress':
        return None
    lines = yield from quests.journal(runemysteries.record.name)
    stage = parse_rune_mysteries_journal(lines)
    yield from modals.close_if_open()
    return stage


runemysteries = QuestModule(
    record=quest_record('runemysteries'),
    bank=Tile(3093, 3243, 0),
    tools=['air talisman', 'research package', 'notes'],
    hops=WIZARD_HOPS,
    read_stage=read_stage,
    decide=decide,
)

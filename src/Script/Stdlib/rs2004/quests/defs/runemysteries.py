"""Rune Mysteries: rs2b0t's api/ai/quests/defs/runemysteries.ts (MIT, see thirdparty/rs2b0t). The Duke's talisman to
Sedridor under the Wizards' Tower, his package to Aubury, and Aubury's notes back."""

from rs2004.geometry import Tile
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
    # Why: Sedridor takes one talisman and leaves any extras; the package is the delivery to Aubury.
    if 'notes' in snap.inv:
        return _talk(SEDRIDOR)
    if 'research package' in snap.inv:
        return _talk(AUBURY)
    if 'air talisman' in snap.inv:
        return _talk(SEDRIDOR)
    return _talk(RECOVER_PROBES[snap.no_progress % len(RECOVER_PROBES)])


runemysteries = QuestModule(
    record=quest_record('runemysteries'),
    bank=Tile(3093, 3243, 0),
    tools=['air talisman', 'research package', 'notes'],
    hops=WIZARD_HOPS,
    decide=decide,
)

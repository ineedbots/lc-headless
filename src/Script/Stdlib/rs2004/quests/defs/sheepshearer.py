"""Sheep Shearer: rs2b0t's api/ai/quests/defs/sheepshearer.ts (MIT, see thirdparty/rs2b0t). Twenty balls of wool,
sheared at Fred's pen and spun in Falador, for Fred the Farmer."""

from rs2004.geometry import Tile
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop
from rs2004.quests.exec.wool import WoolSites, gather_wool

__all__ = ['FRED', 'BALLS_NEEDED', 'SITES', 'gather_balls', 'decide', 'sheepshearer']

FRED = NpcStop('Fred the Farmer', Tile(3189, 3273, 0), 6, ["I'm looking for a quest.", 'Yes okay. I can do that.'])
BALLS_NEEDED = 20

SITES = WoolSites(Tile(3197, 3266, 0), Tile(2982, 3315, 0), Tile(3152, 3306, 0), 'spin wool at Falador')


def gather_balls(snap, need=20):
    return gather_wool(snap, need, SITES)


def decide(snap):
    if snap.journal == 'complete':
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.journal == 'not_started':
        return quest_step('talk', stop=FRED)
    if snap.inv.get('ball of wool', 0) > 0:
        return quest_step('talk', stop=FRED)
    return gather_balls(snap, BALLS_NEEDED)


sheepshearer = QuestModule(
    record=quest_record('sheep'),
    bank=Tile(3093, 3243, 0),
    coin_float=0,
    tools=['shears', 'wool'],
    gather={'ball of wool': gather_balls},
    decide=decide,
)

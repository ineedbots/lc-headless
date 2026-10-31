"""The stubbed half of rs2b0t's test/api/ai/quests/defs/deathplateauScout.test.ts (MIT, see thirdparty/rs2b0t). Its
route checks over rs2b0t's collision pack are nav/test_deathplateau_scout_cache.py, over this cache."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.quests.defs.deathplateau import decide
from rs2004.quests.defs.deathplateau.areas import DEATH_ITEM, TILE
from rs2004.quests.defs.deathplateau.journal import DP_FLAG, DP_STAGE
from rs2004.quests.defs.deathplateau.nav import walk_secret_path
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.traversal import traversal


def _fn1():
    state = {'tile': TILE.TENZING_BACK}
    walks = []

    # Both walks land radius tiles short of the goal, south of it, as rs2b0t's stubs do.
    def walk_resilient(dest, radius=2, attempts=None, timeout_ms=None, scene_radius=None, max_budget=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None):
        walks.append([dest, False])
        state['tile'] = Tile(dest.x, dest.z - radius, dest.level)
        return True
        yield

    def walk_to(dest, radius=2, timeout_ms=None, max_expansions=None, use_teleport_catalog=None, policy=None, bank_item_counts=None, avoid_zones=None, log=None, force_repath=False, path_follow=None):
        walks.append([dest, len(avoid_zones or []) > 0])
        state['tile'] = Tile(dest.x, dest.z - radius, dest.level)
        return True
        yield
    spy_on(game, 'tile', impl=lambda: state['tile'])
    spy_on(reader, 'modals', returns=Record({'main': -1, 'chat': -1, 'side': -1}))
    spy_on(chat_dialog, 'is_open', returns=False)
    spy_on(chat_dialog, 'can_continue', returns=False)
    spy_on(execution, 'delay_ticks', impl=instant_ticks)
    spy_on(execution, 'delay_until', impl=instant_until)
    spy_on(traversal, 'walk_resilient', impl=walk_resilient)
    spy_on(traversal, 'walk_to', impl=walk_to)
    stage = DP_STAGE.UNLOCKED_DOOR
    flags = set([DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY, DP_FLAG.ENTRANCE_CERT, DP_FLAG.GIVEN_CERT, DP_FLAG.SUPPLIES, DP_FLAG.GOT_MAP])
    step = decide(QuestSnapshot(**{
        'journal': 'in_progress',
        'stage': stage,
        'progress': QuestProgress(stage, flags),
        'inv': {'secret way map': 1, 'combination': 1},
        'inv_ids': {DEATH_ITEM.SECRET_MAP.id: 1, DEATH_ITEM.COMBINATION.id: 1},
        'bank': {},
        'bank_known': True,
        'tile': state['tile'],
    }))
    expect(step.kind).to_be('custom')
    expect(run_wait(step.run(lambda *_args: None))).to_be(True)
    expect(all([walk[1] for walk in walks])).to_be(True)
    expect([walks[0][0].x, walks[0][0].z]).to_equal([2817, 3564])
    here = state['tile']
    expect(here.x).to_be_greater_than_or_equal(2864)
    expect(here.x).to_be_less_than(2872)
    expect(here.z).to_be_greater_than_or_equal(3608)
    expect(here.z).to_be_less_than(3616)


test('scouting enters the trigger zone instead of stopping south of it', _fn1)


def _fn2():
    fallback = []
    spy_on(traversal, 'walk_to', impl=lambda *_args, **_kwargs: run_false())

    def walk_resilient(*_args, **_kwargs):
        fallback.append(True)
        return True
        yield
    spy_on(traversal, 'walk_resilient', impl=walk_resilient)
    expect(run_wait(walk_secret_path(TILE.SCOUT, lambda *_args: None))).to_be(False)
    expect(len(fallback)).to_be(0)


def run_false():
    return False
    yield


test('a blocked secret path stops without falling back to unconstrained walking', _fn2)

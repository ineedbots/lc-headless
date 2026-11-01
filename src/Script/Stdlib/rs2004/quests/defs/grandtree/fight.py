"""Ported from rs2b0t's src/bot/api/ai/quests/defs/grandtree/fight.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.quests.defs.fightarena.fights import run_fight
from rs2004.quests.defs.grandtree.areas import GT_LOC, GT_NPC, GT_TILE, in_caves
from rs2004.quests.defs.grandtree.legs import climb_to_pillars, leave_caves
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.quests.strike_combat import DEMON_COVER, ready_strikes
from rs2004.traversal import traversal

__all__ = ['descend_trapdoor', 'fight_black_demon']

DEMON_GUARD = 1200


def demon():
    return npcs.query().where(lambda n: n.id == GT_NPC.BLACK_DEMON).within(20).nearest()


def here():
    t = game.tile()
    return (Tile(t.x, t.z, t.level) if t else None)


# Why: the trapdoor is ground decor and blocks its own tile, so the stand is the tile north of it and the server paths the last step.
# Why: `[oploc1,grandtree_trapdoorclosed]` opens at every stage from 130 up, so a death after the demon is recoverable; the caves have no other way in until the quest is done.
def descend_trapdoor(log):
    if in_caves(here()):
        return True
    _w1 = yield from climb_to_pillars(log)
    if not (_w1):
        return False
    _w2 = yield from traversal.walk_resilient(GT_TILE.trapdoor_stand, radius=0, attempts=3, timeout_ms=60000, log=log)
    if not (_w2):
        return False
    yield from settle_scene()
    trapdoor = locs.query().where(lambda l: l.id == GT_LOC.TRAPDOOR_SHUT).action('Open').within(4).nearest()
    if not trapdoor:
        log(f'no trapdoor at ({GT_TILE.trapdoor_stand.x},{GT_TILE.trapdoor_stand.z})')
        return False
    if not (trapdoor.interact('Open')):
        return False
    _w3 = yield from execution.delay_until(lambda: in_caves(here()), 12000)
    if not (_w3):
        log('the trapdoor did not drop us into the caves')
        return False
    yield from settle_scene()
    return True


# Why: Glough's speech ends in `if_close`, a camera move and an `npc_add`, so the demon appearing is what ends the cutscene.
# Why: `ai_timer` deletes the demon once you're more than 17 tiles away and only stage 130 re-runs the cutscene, so after wandering off you climb out and drop in again.
def fight_black_demon(log):
    """Take the trapdoor, sit through Glough's speech, kill the demon."""
    _w4 = yield from ready_strikes(log)
    if not (_w4):
        return False
    dropping = not in_caves(here())
    _w5 = yield from descend_trapdoor(log)
    if not (_w5):
        return False
    if not demon():
        if dropping:
            log("waiting out Glough's speech for the demon to land")
        yield from drive_until(lambda: demon() is not None, [], log, (90000 if dropping else 15000))
    target = demon()
    if not target:
        log('no Black Demon in the caves — climbing back out to re-enter the trapdoor')
        yield from leave_caves(log)
        return False
    result = yield from run_fight(Record({'what': 'Black Demon', 'npc_id': GT_NPC.BLACK_DEMON, 'guard': DEMON_GUARD, 'cover': DEMON_COVER}), log)
    return result == 'won'

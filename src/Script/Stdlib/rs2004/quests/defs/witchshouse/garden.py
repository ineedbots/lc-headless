"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/garden.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import modals
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.traversal import traversal
from rs2004.quests.strike_combat import at_cover, cast_strike, EXPERIMENT_COVER, EXPERIMENT_TRAP, ready_strikes, take_strike_cover
from rs2004.quests.strike import strike_spell
from rs2004.quests.exec.prompts import clear_boxes, cross_teleport_door, prompt_loc, settle_scene
from rs2004.quests.defs.witchshouse.areas import EXPERIMENT_IDS, WH_LOC, WH_OBJ, WH_TILE, in_garden, in_shed
from rs2004.quests.defs.witchshouse.house import held
from rs2004.quests.defs.witchshouse.patrol import FOUNTAIN_STAND, GARDEN_ENTRY, GARDEN_SHED, walk_garden
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['experiment', 'fountain_key', 'fight_experiment', 'kill_experiment', 'take_ball', 'leave_garden']

FIGHT_MS = 900000
SPAWN_TICKS = 25
KILLED = 'kill the shapeshifter once and for all'
NOTHING_IN_FOUNTAIN = 'nothing in the fountain'


def experiment():
    return npcs.query().where(lambda n: (n.id in EXPERIMENT_IDS) and not n.targets_another_player()).action('Attack').within(14).nearest()


def fountain_key(log):
    """Check the fountain's secret compartment for the shed key."""
    if held(WH_OBJ.SHED_KEY) > 0:
        return True
    _w1 = yield from walk_garden(FOUNTAIN_STAND, log)
    if not (_w1):
        log(('stopped short of the fountain inside the garden' if in_garden(game.tile()) else 'never reached the garden. The witch throws a caught bot back to the boy'))
        return False
    yield from settle_scene()
    took = yield from prompt_loc(Record({
        'name': 'Fountain',
        'op': 'Check',
        'near': WH_TILE.FOUNTAIN,
        'id': WH_LOC.FOUNTAIN,
        'within': 6,
        'expect': lambda: held(WH_OBJ.SHED_KEY) > 0,
        'expect_ms': 12000,
        'refused': NOTHING_IN_FOUNTAIN,
    }), log)
    yield from modals.close()
    return took and held(WH_OBJ.SHED_KEY) > 0


# Why: Before stage 6, plain Open is locked; using the leaf key also spawns the shapeshifter.
def enter_shed(log):
    """Cross the shed door with the key, which is also what spawns the first form."""
    if in_shed(game.tile()):
        return True
    if held(WH_OBJ.SHED_KEY) == 0:
        log('no shed key in the pack. The witch deletes it when she catches you')
        return False
    _w2 = yield from walk_garden(GARDEN_SHED, log)
    if not (_w2):
        return False
    _result3 = yield from cross_teleport_door(Record({
        'id': WH_LOC.SHED_DOOR,
        'stand': WH_TILE.SHED_DOOR,
        'stand_radius': 0,
        'use_item': WH_OBJ.SHED_KEY,
        'is_far': lambda: in_shed(game.tile()),
        'log': log,
    }))
    return _result3


def ball_drop():
    return ground_items.query().where(lambda g: g.id == WH_OBJ.BALL).within(10).nearest()


# Why: `opobj3,ball` re-adds a `shapeshifterglob` whenever the quest is short of stage 6 and none is in range, so touching the ball restarts an interrupted fight.
def summon_experiment(log):
    """Touch the ball to bring a shapeshifter back."""
    ball = ball_drop()
    if not ball:
        log('no ball in the shed to draw the shapeshifter out with')
        return False
    if not (ball.interact('Take')):
        return False
    came = yield from execution.delay_until(lambda: experiment() is not None, 8000)
    yield from clear_boxes()
    if not came:
        log('the ball raised no shapeshifter')
    return came


BEAR_COVER = Tile(2936, 3459, 0)
CORNER_APPROACH = Tile(2937, 3465, 0)


def trap_experiment(log):
    target = experiment()
    if not target:
        return None
    if target.size > 1:
        _w4 = yield from take_strike_cover(BEAR_COVER, log)
        return (BEAR_COVER if _w4 else None)
    if (EXPERIMENT_TRAP.distance_to(target.network_tile()) == 0):
        _w5 = yield from take_strike_cover(EXPERIMENT_COVER, log)
        return (EXPERIMENT_COVER if _w5 else None)
    _w6 = yield from take_strike_cover(EXPERIMENT_TRAP, log)
    if not (_w6):
        return None
    spell = strike_spell(skills.effective('magic'), lambda rune: inventory.count(rune))
    if not spell:
        return None
    if not target.targets_me():
        before = inventory.count('Mind rune')
        cast = False
        spent = False
        try:
            cast = game.cast_on_npc(spell, target)
            if cast:
                spent = yield from execution.delay_until_ticks(lambda: inventory.count('Mind rune') < before, 8)
        except Exception as e:
            direct_navigator.walk(EXPERIMENT_TRAP)
            raise e
        direct_navigator.walk(EXPERIMENT_TRAP)
        if not cast or not spent:
            return None
    for tick in range(80):
        if event_signal.pending():
            return None
        yield from sustain.run()
        current = experiment()
        if not current or current.id != target.id:
            return None
        if (EXPERIMENT_TRAP.distance_to(current.network_tile()) == 0) and not at_cover(EXPERIMENT_TRAP):
            _w8 = yield from take_strike_cover(EXPERIMENT_COVER, log)
            return (EXPERIMENT_COVER if _w8 else None)
        under = (CORNER_APPROACH.distance_to(current.network_tile()) == 0)
        direct_navigator.walk((CORNER_APPROACH if under else EXPERIMENT_TRAP))
        yield from execution.delay_ticks(1)
    log('experiment did not enter the northeast trap')
    return None


def fight_experiment(log):
    mark = game_messages.mark()

    def won():
        return game_messages.saw_since(mark, KILLED)

    _w9 = yield from ready_strikes(log)
    if not (_w9):
        return False
    deadline = _core.step_time() + FIGHT_MS
    shape = -1
    cover = None
    idle = 0
    while _core.step_time() < deadline:
        if won():
            return True
        if event_signal.pending():
            return False
        yield from sustain.run()
        target = experiment()
        if not target:
            idle += 1
            if idle > SPAWN_TICKS:
                return won()
            yield from execution.delay_ticks(1)
            continue
        idle = 0
        if target.id != shape or not cover or not at_cover(cover):
            shape = target.id
            here = game.tile()
            if target.id == EXPERIMENT_IDS[0] or target.id == EXPERIMENT_IDS[1]:
                _c10 = ((Tile(here.x, here.z, here.level) if here else None))
            else:
                _w11 = yield from trap_experiment(log)
                _c10 = _w11
            cover = _c10
            if not cover:
                return won()
            continue
        _w12 = yield from cast_strike(cover, target, log)
        if not (_w12):
            return won()
    return won()


def kill_experiment(log):
    """Unlock the shed and take the fight through to the kill message."""
    _w13 = yield from ready_strikes(log)
    if not (_w13):
        return False
    _w14 = yield from enter_shed(log)
    if not (_w14):
        return False
    yield from settle_scene()
    _c15 = not experiment()
    if _c15:
        _w16 = yield from summon_experiment(log)
        _c15 = not (_w16)
    if _c15:
        return False
    _result17 = yield from fight_experiment(log)
    return _result17


def take_ball(log):
    """Take the ball, which only answers Take once the shapeshifter is dead."""
    if held(WH_OBJ.BALL) > 0:
        return True
    if not in_shed(game.tile()):
        _w18 = yield from walk_garden(GARDEN_SHED, log)
        if not (_w18):
            return False
        # Why: past stage 6 the shed door's own `oploc1` opens, so no second key is needed after a catch.
        _w19 = yield from cross_teleport_door(Record({
            'id': WH_LOC.SHED_DOOR,
            'stand': WH_TILE.SHED_DOOR,
            'stand_radius': 0,
            'is_far': lambda: in_shed(game.tile()),
            'log': log,
        }))
        if not (_w19):
            return False
    _w20 = yield from traversal.walk_resilient(WH_TILE.BALL, radius=1, attempts=2, timeout_ms=60000, log=log)
    if not (_w20):
        return False
    yield from settle_scene()
    ball = ball_drop()
    if not ball:
        log('no ball on the shed floor. It respawns on its map timer')
        return False
    if not (ball.interact('Take')):
        return False
    _result21 = yield from execution.delay_until(lambda: held(WH_OBJ.BALL) > 0, 8000)
    return _result21


def leave_garden(log):
    _c22 = in_shed(game.tile())
    if _c22:
        _w23 = yield from cross_teleport_door(Record({
        'id': WH_LOC.SHED_DOOR,
        'stand': WH_TILE.SHED_DOOR.translate(1, 0),
        'stand_radius': 0,
        'is_far': lambda: in_garden(game.tile()),
        'log': log,
    }))
        _c22 = not (_w23)
    if _c22:
        return False
    _w24 = yield from walk_garden(GARDEN_ENTRY, log)
    if not (_w24):
        return False
    _result25 = yield from traversal.walk_resilient(WH_TILE.PORCH, radius=0, attempts=2, timeout_ms=30000, log=log)
    return _result25

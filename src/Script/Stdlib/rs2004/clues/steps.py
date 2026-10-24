"""The talk steps that need more than a walk and a chat: Hans, who never stands still, and the gnome pilot on White
Wolf Mountain, among the wolves. rs2b0t's api/ai/clues/hans.ts and gnomePilot.ts (MIT, see thirdparty/rs2b0t). The
Waits are used with yield from; walk(tile) is the trail's own walk to a tile, a Wait."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.exec import primitives
from rs2004.clues.data import TALK_ANCHORS
from rs2004.clues.plan import SHARK_ID
from rs2004.clues import puzzle_box

# Hans (hans.ts)

HANS_WAIT_SPOT = Tile(3221, 3218, 0)
PATROL_TICKS = 200
CHASE_TICKS = 40
CHASE_ENERGY = 50
STOP_ENERGY = 20


def _dialogue_ready():
    return chat_dialog.is_open() or chat_dialog.can_continue()


def _find_hans():
    return npcs.query().name('Hans').action('Talk-to').nearest()


def _reachable(npc):
    return reachability.can_reach(npc.tile(), adjacent_ok=True, max_steps=128)


def _return_to_spot(walk):
    if event_signal.pending():
        return False
    if not direct_navigator.walk(HANS_WAIT_SPOT):
        return False
    back = yield from walk(HANS_WAIT_SPOT)
    return back


def _talk(npc, clue_id, chase, ticks, log):
    if not npc.interact('Talk-to'):
        return False
    for _ in range(ticks):
        yield from sustain.run()
        if event_signal.pending():
            return False
        if not inventory.count_by_id(clue_id):
            return True
        if _dialogue_ready():
            yield from primitives.drive_dialog([], log, 5000)
            return True
        live = _find_hans()
        here = game.tile()
        if live is None or here is None or live.tile().distance_to(here) > (32 if chase else 3):
            return False
        if chase and (game.energy() < STOP_ENERGY or not game.run_enabled()):
            return False
        yield from execution.delay_ticks(1)
    if event_signal.pending():
        return False
    if not inventory.count_by_id(clue_id):
        return True
    if _dialogue_ready():
        yield from primitives.drive_dialog([], log, 5000)
        return True
    return False


# Why: Hans walks a loop round the castle, so the bot waits where his loop passes, by the Lumbridge teleport, and
# talks to him when he comes by; only with run energy to spare does it chase him.
def solve_hans(clue_id, walk, log):
    """None once the clue is handed on, 'yield' to try again later."""
    if event_signal.pending():
        return 'yield'
    if _dialogue_ready():
        yield from primitives.drive_dialog([], log, 5000)
        return None
    there = yield from walk(HANS_WAIT_SPOT)
    if not there:
        return 'yield'
    log('waiting near the Lumbridge teleport for Hans to finish his patrol')
    deadline = game.tick() + PATROL_TICKS
    for _ in range(PATROL_TICKS):
        if game.tick() >= deadline:
            break
        yield from sustain.run()
        if event_signal.pending():
            return 'yield'
        if not inventory.count_by_id(clue_id):
            return None
        if _dialogue_ready():
            yield from primitives.drive_dialog([], log, 5000)
            return None
        npc = _find_hans()
        here = game.tile()
        if npc is not None and here is not None and npc.tile().distance_to(here) <= 1 and _reachable(npc):
            talked = yield from _talk(npc, clue_id, False, min(30, deadline - game.tick()), log)
            if talked:
                return None
            back = yield from _return_to_spot(walk)
            if not back:
                return 'yield'
        yield from execution.delay_ticks(1)
    if event_signal.pending():
        return 'yield'
    if not inventory.count_by_id(clue_id):
        return None
    if _dialogue_ready():
        yield from primitives.drive_dialog([], log, 5000)
        return None
    npc = _find_hans()
    here = game.tile()
    if npc is None or here is None or npc.tile().distance_to(here) > 32 or game.energy() < CHASE_ENERGY or not _reachable(npc):
        return 'yield'
    if not game.run_enabled():
        game.set_run(True)
        yield from execution.delay_until_ticks(lambda: game.run_enabled() or event_signal.pending() or _dialogue_ready(), 5)
    if event_signal.pending():
        return 'yield'
    if _dialogue_ready():
        yield from primitives.drive_dialog([], log, 5000)
        return None
    if not game.run_enabled() or game.energy() < CHASE_ENERGY:
        return 'yield'
    log('run energy is high enough; trying a short chase to catch Hans')
    live = _find_hans()
    here = game.tile() or here
    if live is not None and live.tile().distance_to(here) <= 32 and _reachable(live):
        talked = yield from _talk(live, clue_id, True, CHASE_TICKS, log)
        if talked:
            return None
    yield from _return_to_spot(walk)
    return 'yield'


# The gnome pilot (gnomePilot.ts)

PILOT_REFUGE = Tile(2852, 3500, 0)
PILOT_APPROACH = Tile(2846, 3500, 0)
PILOT_CLUE = 3570
PILOT_PUZZLE_ID = 3571


def _shelter(walk, log):
    log('moving behind the glider to lose wolf aggro')
    there = yield from walk(PILOT_REFUGE)
    if not there:
        return False
    quiet = 0
    for _ in range(20):
        yield from sustain.run()
        if event_signal.pending() or skills.effective('hitpoints') <= 0:
            return False
        quiet = 0 if game.in_combat() else quiet + 1
        if quiet >= 2:
            return True
        yield from execution.delay_ticks(1)
    log('still in combat behind the glider; keeping the clue for another attempt')
    return False


def _run_pilot(walk, log):
    off = yield from execution.delay_until_ticks(lambda: not game.auto_retaliate_on(), 5)
    if not off or event_signal.pending():
        return 'yield'
    if skills.effective('hitpoints') <= 0:
        return 'dead'
    if inventory.count_by_id(SHARK_ID) < 4:
        return 'supplies-needed'
    puzzle = inventory.count_by_id(PILOT_PUZZLE_ID) > 0
    here = game.tile()
    anchor = TALK_ANCHORS[PILOT_CLUE]
    if puzzle or game.in_combat() or here is None or anchor.distance_to(here) > 8:
        sheltered = yield from _shelter(walk, log)
        if not sheltered:
            return 'yield'
    if puzzle:
        solved = yield from puzzle_box.solve_held(PILOT_PUZZLE_ID, log)
        if not solved:
            return 'yield'
    if skills.effective('hitpoints') <= 0:
        return 'dead'
    if event_signal.pending():
        return 'yield'
    if not _dialogue_ready():
        there = yield from walk(PILOT_APPROACH)
        if not there or event_signal.pending():
            return 'yield'
        if skills.effective('hitpoints') <= 0:
            return 'dead'
        if game.in_combat():
            yield from _shelter(walk, log)
            return 'yield'
        pilot = npcs.query().name('Gnome pilot').where(lambda n: n.tile().distance_to(anchor) <= 4).nearest()
        if pilot is None or not pilot.interact('Talk-to'):
            return 'yield'
        for _ in range(5):
            yield from sustain.run()
            if skills.effective('hitpoints') <= 0:
                return 'dead'
            if event_signal.pending():
                return 'yield'
            if game.in_combat():
                yield from _shelter(walk, log)
                return 'yield'
            if _dialogue_ready():
                break
            yield from execution.delay_ticks(1)
    if _dialogue_ready():
        yield from primitives.talk_through('Gnome pilot', [], log)
    if skills.effective('hitpoints') <= 0:
        return 'dead'
    if event_signal.pending():
        return 'yield'
    if game.in_combat():
        yield from _shelter(walk, log)
        return 'yield'
    return None


def solve_mountain_pilot(walk, log):
    """None, 'yield', 'supplies-needed' or 'dead'. Auto retaliate is off for it, and put back after."""
    retaliate = game.auto_retaliate_on()
    game.set_auto_retaliate(False)
    result = yield from _run_pilot(walk, log)
    game.set_auto_retaliate(retaliate)
    return 'dead' if skills.effective('hitpoints') <= 0 else result

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fishingcontest/contest.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.reach import reach
from rs2004.traversal import traversal
from rs2004.quests.exec.prompts import drive_choice, drive_until, held_id, settle_scene
from rs2004.quests.defs.fishingcontest.areas import BONZO_ENTER, BONZO_REPORT, DWARF_REPORT, DWARF_START, FC_ID, FC_LOC, FC_NPC, FC_TILE, in_compound, nearest_dwarf
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['leave_compound', 'start_quest', 'claim_pass', 'pay_entry_fee', 'stash_garlic', 'fish_at_pipes', 'hand_over_catch', 'claim_spare_trophy', 'deliver_trophy']

WALK_MS = 180000
GATE_MS = 20000
CATCH_MS = 20000
STASH_MS = 20000


def walk_and_talk(stop, log):
    here = game.tile()
    if not here or here.level != stop.anchor.level or stop.anchor.distance_to(here) > stop.leash:
        yield from traversal.walk_resilient(stop.anchor, radius=2, attempts=3, timeout_ms=WALK_MS, log=log)
    status = yield from reach.npc_dialog(stop.npc, stop.anchor, log=log)
    if status != 'done':
        log(f'could not open a dialogue with {stop.npc} ({status})')
        return False
    _result1 = yield from drive_choice(list(stop.prefer), log)
    return _result1


def dwarf_stop(prefer):
    """Whichever tunnel mouth is nearer, with the preference list this stage needs."""
    _merged2 = {}
    for _k, _v in (DWARF_START._fields if isinstance(DWARF_START, Record) else DWARF_START).items():
        _merged2[_k] = _v
    for _k, _v in {'anchor': nearest_dwarf(game.tile()), 'prefer': list(prefer)}.items():
        _merged2[_k] = _v
    return Record(_merged2)


# Why: both halves run the crossing, but only the left leaves without Bonzo's prompt on a merely-started quest, so it goes first.
def gate_loc():
    def find(match_):
        return locs.query().where(lambda l: match_(l.id)).action('Open').within(5).nearest()

    _v3 = find(lambda id: id == FC_LOC.GATE_LEFT)
    return (_v3 if _v3 is not None else find(lambda id: id == FC_LOC.GATE_RIGHT))


# Why: leaving before the win puts Bonzo's "calling it quits" in the way and its other option leaves the gate shut, so the exit takes the reset: it costs the 5gp fee and keeps the stashed pipe.
QUIT_CONTEST = "Yes I'll compete again another day."


def cross_gate(stand, inside, log):
    if in_compound(game.tile()) == inside:
        return True
    _w4 = yield from traversal.walk_resilient(stand, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w4):
        return False
    yield from settle_scene()
    door = gate_loc()
    if not door:
        log(f'no Hemenster Gate at ({stand.x},{stand.z})')
        return False
    if not (door.interact('Open')):
        return False
    _result5 = yield from drive_until(lambda: in_compound(game.tile()) == inside, ([] if inside else [QUIT_CONTEST]), log, GATE_MS)
    return _result5


# Why: the gate is a baked door edge but crossing inbound is a conversation: Morris asks for the pass, spends 2 continues and an objbox, then teleports you through, which no door handler drives.
def enter_compound(log):
    """Get past Morris onto the competition ground."""
    return cross_gate(FC_TILE.GATE_OUTSIDE, True, log)


def leave_compound(log):
    """Step back out through the gate, taking the reset if the contest is still running."""
    return cross_gate(FC_TILE.GATE_INSIDE, False, log)


def start_quest(log):
    return walk_and_talk(dwarf_stop(DWARF_START.prefer), log)


def claim_pass(log):
    return walk_and_talk(dwarf_stop(DWARF_REPORT.prefer), log)


def pay_entry_fee(log):
    _w6 = yield from enter_compound(log)
    if not (_w6):
        return False
    _result7 = yield from walk_and_talk(BONZO_ENTER, log)
    return _result7


# Why: the pipe moves the stranger off the winning spot and Bonzo only re-seats the contest before any fish is caught, so this runs before the first cast.
# Why: the stand is the pipe's own tile; `useOnLoc`'s radius-2 walk would settle beside it and the engine refuses a straight wall decoration from there.
def stash_garlic(log):
    """Push the clove into the wall pipe; the stranger smells it and swaps spots."""
    _w8 = yield from enter_compound(log)
    if not (_w8):
        return False
    _w9 = yield from traversal.walk_resilient(FC_TILE.PIPE_STAND, radius=0, attempts=3, timeout_ms=60000, log=log)
    if not (_w9):
        return False
    yield from settle_scene()
    here = game.tile()
    pipe = locs.query().where(lambda l: l.id == FC_LOC.WALL_PIPE and here is not None and l.tile().x == here.x and l.tile().z == here.z).nearest()
    garlic = ([item for item in inventory.items() if item.id == FC_ID.GARLIC] or [None])[0]
    if not pipe or not garlic:
        log(f'no Wall Pipe underfoot at ({FC_TILE.PIPE_STAND.x},{FC_TILE.PIPE_STAND.z}) or no garlic to stash')
        return False
    if not (garlic.use_on(pipe)):
        return False
    _result10 = yield from drive_until(lambda: held_id(FC_ID.GARLIC) == 0, [], log, STASH_MS)
    return _result10


# Why: one cast per call; the 3rd fish triggers Bonzo's hand-over inside the same script, and the trophy proves the contest is over.
def fish_at_pipes(log):
    """Cast once at the pipes spot."""
    _w11 = yield from enter_compound(log)
    if not (_w11):
        return False
    _w12 = yield from traversal.walk_resilient(FC_TILE.PIPES_SPOT, radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w12):
        return False
    yield from settle_scene()
    spot = npcs.query().where(lambda n: n.id == FC_NPC.PIPES_SPOT).action('Fish').within(8).nearest()
    if not spot:
        log(f'no contest Fishing spot at ({FC_TILE.PIPES_SPOT.x},{FC_TILE.PIPES_SPOT.z})')
        return False
    before = held_id(FC_ID.RAW_GIANT_CARP)
    if not (spot.interact('Fish')):
        return False
    _result13 = yield from drive_until(lambda: held_id(FC_ID.RAW_GIANT_CARP) > before or held_id(FC_ID.TROPHY) > 0, [], log, CATCH_MS)
    return _result13


# Why: sardines mean the willow spot was fished, which can't win; handing them to Bonzo loses the round and resets the entry, and the stashed pipe seats the re-entry beside the pipes.
def hand_over_catch(log):
    """Lose the round on purpose, back to a payable entry."""
    _w14 = yield from enter_compound(log)
    if not (_w14):
        return False
    _w15 = yield from walk_and_talk(BONZO_REPORT, log)
    if not (_w15):
        return False
    return held_id(FC_ID.RAW_SARDINE) == 0


def claim_spare_trophy(log):
    """Bonzo keeps a spare trophy for a champion who lost theirs."""
    _w16 = yield from enter_compound(log)
    if not (_w16):
        return False
    _w17 = yield from walk_and_talk(BONZO_REPORT, log)
    if not (_w17):
        return False
    _result18 = yield from execution.delay_until(lambda: held_id(FC_ID.TROPHY) > 0, 5000)
    return _result18


def deliver_trophy(log):
    _w19 = yield from leave_compound(log)
    if not (_w19):
        return False
    _result20 = yield from walk_and_talk(dwarf_stop(DWARF_REPORT.prefer), log)
    return _result20

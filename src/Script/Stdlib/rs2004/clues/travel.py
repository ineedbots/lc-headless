"""Getting a trail to places the walker's graph doesn't reach: the Duel Arena's pens, the Kharazi Jungle and
Isafdar. rs2b0t's api/ai/clues/duelTravel.ts, kharaziTravel.ts and tirannwnTravel.ts (MIT, see thirdparty/rs2b0t).

The Kharazi Jungle is cut into tile by tile with a machete, and Isafdar is crossed on Regicide's seams; both are the
members' quests' code, phase 17's. Until then a leg that has to cross either says so and fails, and the clue is
abandoned: the Isafdar clues are gated on Regicide anyway (data.CLUE_GATES)."""

import time

from rs2004 import execution
from rs2004.catalogs.tools import AXES, best_axe
from rs2004.duel import CLUE_DUEL_LOBBY, ClueDuelHandshake, ClueDuelSearch, clue_duel_name, duel, fight_arena_at, leave_clue_duel
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import equipment, inventory
from rs2004.settings import settings_store
from rs2004.tabs import quests
from rs2004.traversal import traversal
from rs2004.bank import bank

# The trail's walks

ARRIVE_RADIUS = 1
WALK_ATTEMPTS = 4
WALK_TIMEOUT_MS = 45000
# Why: long clue legs may use affordable catalog teleports; short legs stay on foot.
TELEPORT_MIN_SPAN = 40

_teleports = [True]


def set_trail_teleports(on):
    """Whether trail legs route through the teleport catalog (spells, the ring of dueling)."""
    _teleports[0] = on


def trail_walk_opts(log, radius=1):
    """walk_resilient's keyword arguments for a cross-map clue leg, so the teleport policy lives in one place. Close
    walks (onto an NPC or a dropped key) don't use this."""
    opts = {'radius': radius, 'attempts': WALK_ATTEMPTS, 'timeout_ms': WALK_TIMEOUT_MS, 'log': log}
    if _teleports[0]:
        opts['use_teleport_catalog'] = True
        opts['policy'] = {'use_teleports': True, 'distance_before_teleport': TELEPORT_MIN_SPAN}
    else:
        opts['use_teleport_catalog'] = False
        opts['policy'] = {'use_teleports': False}
    return opts


def _walk(dest, opts):
    arrived = yield from traversal.walk_resilient(dest, **opts)
    return arrived


def _now_ms():
    return time.time() * 1000


# The Duel Arena leg (duelTravel.ts)

DUEL_CLUE_ID = 3554
DUEL_CLUE_TILE = Tile(3374, 3250, 0)
_tried_partners = {}


def reset_clue_duel_search():
    _tried_partners.clear()


def crosses_clue_duel(dest):
    return (dest.level == 0 and dest.x == DUEL_CLUE_TILE.x and dest.z == DUEL_CLUE_TILE.z) or fight_arena_at(game.tile()) is not None


def walk_across_clue_duel(dest, radius, log):
    """Into the pen the clue wants, by an unstaked obstacle duel: with the Global clue_duel_partner when it names
    another account, else with whoever in the lobby will take one."""
    target = fight_arena_at(dest)
    here_pen = fight_arena_at(game.tile())
    if here_pen is not None and here_pen is not target:
        left = yield from leave_clue_duel(log)
        if not left:
            return False
    if target is not None and fight_arena_at(game.tile()) is None:
        configured = settings_store.global_bag().str('clue_duel_partner', '').strip()
        partner = '' if clue_duel_name(configured) == clue_duel_name(game.my_name()) else configured
        for _ in range(2):
            reached = yield from traversal.walk_resilient(CLUE_DUEL_LOBBY, radius=3, attempts=3, timeout_ms=60000, log=log)
            if not reached:
                return False
            handshake = ClueDuelHandshake(partner, True, log) if partner else ClueDuelSearch(log, _tried_partners)
            deadline = _now_ms() + 120000
            log(f'waiting for clue helper {partner}' if partner else 'looking for a lobby player for an unstaked obstacle duel')
            while fight_arena_at(game.tile()) is None and _now_ms() < deadline:
                if event_signal.pending():
                    if duel.active():
                        yield from duel.cancel()
                    return False
                ok = yield from handshake.tick()
                if ok == False:
                    return False
                yield from execution.delay_ticks(1)
            if fight_arena_at(game.tile()) is target:
                break
            if duel.active():
                yield from duel.cancel()
            if fight_arena_at(game.tile()) is None:
                log('no clue duel completed yet; keeping the clue and waiting in the lobby')
                return False
            log('assigned a different obstacle arena, retrying')
            left = yield from leave_clue_duel(log)
            if not left:
                return False
        if fight_arena_at(game.tile()) is not target:
            return False
    arrived = yield from traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=45000, log=log)
    return arrived


# The Kharazi Jungle (kharaziTravel.ts)

# The three hard coordinate digs inside the jungle.
KHARAZI_CLUES = set([3532, 3534, 3536])
MACHETE = 'Machete'
# Radimus Erkle's notes, the blank copy and the finished one, which share a name.
RADIMUS_NOTES = 'Radimus notes'
LEGENDS_QUEST = "Legends' Quest"
# The z of the last open jungle tile and of the first open mainland tile north of the band.
JUNGLE_SOUTH = 2936
JUNGLE_NORTH = 2940


def in_kharazi(p):
    """Whether a tile is in the jungle, the band's own three rows included: Legends' Quest's legendsArea."""
    return p is not None and p.level == 0 and 2757 <= p.x <= 3006 and 2882 <= p.z < JUNGLE_NORTH


def jungle_crossing(dest, at):
    """'enter', 'leave' or 'none': which way the band has to be cut for this walk."""
    if in_kharazi(dest) == in_kharazi(at):
        return 'none'
    return 'enter' if in_kharazi(dest) else 'leave'


def crosses_kharazi(dest):
    return jungle_crossing(dest, game.tile()) != 'none'


def walk_across_kharazi(dest, radius, log):
    log(f"the Kharazi Jungle is cut into with Legends' Quest's jungle code, which comes with the members' quests; can't reach ({dest.x},{dest.z}) yet")
    return False
    yield


def _worn_or_held(name):
    return inventory.first(name) is not None or equipment.contains(name)


AXE_NAMES = [axe.name for axe in AXES]


# Why: woodcutting_axe_checker reads the pack and the right hand, and this era puts no level on an axe, so the best one
# the bank holds is the one to bring.
def jungle_axe():
    """The best axe to take into the jungle, or None when neither pack nor bank has one."""
    return best_axe(99, lambda n: _worn_or_held(n) or bank.count(n) > 0)


def held_axe():
    return best_axe(99, _worn_or_held)


def has_jungle_map():
    """Whether start_chop_jungle will pass the map check: the notes held, or the quest done."""
    return _worn_or_held(RADIMUS_NOTES) or quests.status(LEGENDS_QUEST) == 'complete'


def jungle_kit_missing():
    """What start_chop_jungle checks before the first swing that the pack is short of."""
    missing = []
    if not _worn_or_held(MACHETE):
        missing.append(MACHETE)
    if held_axe() is None:
        missing.append('an axe')
    if not has_jungle_map():
        missing.append(f'{RADIMUS_NOTES} ({LEGENDS_QUEST} reads {quests.status(LEGENDS_QUEST)})')
    return missing


def jungle_keep_names():
    """The names a Kharazi trail mustn't let the bank stop deposit."""
    return [MACHETE, RADIMUS_NOTES] + AXE_NAMES


# Isafdar (tirannwnTravel.ts)

# Why: rs2b0t finds an Isafdar pocket by Regicide's seam spans; until those come, the forest west of Arandar is a
# box, which is all crosses_tirannwn needs to send the walk here rather than to a graph that has no edges there.
def in_isafdar(p):
    return p is not None and p.level == 0 and 2140 <= p.x <= 2390 and 3140 <= p.z <= 3340


def crosses_tirannwn(dest):
    return in_isafdar(dest) or in_isafdar(game.tile())


def walk_across_tirannwn(dest, radius, log, opts=None):
    log(f"Isafdar is crossed on Regicide's seams, which come with the members' quests; can't reach ({dest.x},{dest.z}) yet")
    return False
    yield

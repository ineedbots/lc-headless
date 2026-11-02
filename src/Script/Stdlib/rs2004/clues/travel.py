"""Getting a trail to places the walker's graph doesn't reach: the Duel Arena's pens, the Kharazi Jungle and
Isafdar. rs2b0t's api/ai/clues/duelTravel.ts, kharaziTravel.ts and tirannwnTravel.ts (MIT, see thirdparty/rs2b0t).

The Kharazi Jungle is cut into tile by tile with Legends Quest's jungle code, and Isafdar is crossed on Regicide's
seams. Both quests are big, so they're imported the first time a walk needs them, not by every bot that carries a
clue."""

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
from rs2004.navigation import navigator
from rs2004.traversal import execute_teleport_hop, traversal
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
# Why: a list, as a bank stop asks about a pack holding only a casket, whose scroll id is None, and in pocketpy None in a set raises.
KHARAZI_CLUES = [3532, 3534, 3536]
MACHETE = 'Machete'
# Radimus Erkle's notes, the blank copy and the finished one, which share a name.
RADIMUS_NOTES = 'Radimus notes'
LEGENDS_QUEST = 'Legends Quest'
KHARAZI_WALK_ATTEMPTS = 4
KHARAZI_WALK_TIMEOUT_MS = 240000
# The tile the band is cut south from.
JUNGLE_MOUTH = Tile(2816, 2940, 0)
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


def walk_across_kharazi(dest, radius, log, options=None):
    """Cut through the dense band, then walk the rest on the ordinary graph."""
    from rs2004.quests.defs.legends.jungle import enter_jungle, leave_jungle
    cut = leave_jungle if jungle_crossing(dest, game.tile()) == 'leave' else enter_jungle
    through = yield from cut(log)
    if not through:
        return False
    fields = {'radius': radius, 'attempts': KHARAZI_WALK_ATTEMPTS, 'timeout_ms': KHARAZI_WALK_TIMEOUT_MS, 'log': log}
    if options is not None:
        for key in ('use_teleport_catalog', 'policy'):
            if key in options:
                fields[key] = options[key]
    arrived = yield from traversal.walk_resilient(Tile(dest.x, dest.z, dest.level), **fields)
    return arrived


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

# Why: 3 callers walk a clue somewhere and only one is the trail itself; the talk step reaches its NPC through reach
# and the bank stop picks its own booth, so each needs the seam graph or the walker calls Isafdar unreachable.
def _pocket_at(tile):
    from rs2004.quests.defs.regicide.pockets import pocket_at
    return pocket_at(tile)


def _teleport_out(dest, log, options):
    start = game.tile()
    if not start or _pocket_at(start) is None or _pocket_at(dest) is not None or event_signal.pending():
        return
    catalog = options.get('use_teleport_catalog')
    policy = options.get('policy') or {}
    if catalog == False or policy.get('use_teleports') == False:
        return
    if not (catalog or policy.get('use_teleports') or traversal.teleports_enabled()):
        return
    merged = {}
    for key in policy.keys():
        merged[key] = policy[key]
    merged['use_teleports'] = True
    path = navigator.find_path(start, dest, policy=merged, use_teleport_catalog=True)
    if event_signal.pending():
        return
    waypoints = path.raw.get('waypoints', []) if path.ok else []
    hop = waypoints[1].get('transport') if len(waypoints) > 1 else None
    if hop is None or hop.get('kind') != 'teleport':
        return
    log(f"leaving Isafdar using {hop['loc_name']}")
    landed = yield from execute_teleport_hop(hop, log)
    if not landed:
        log('Isafdar teleport failed; trying the exit crossings')


# Why: the seam graph gates the dense forests on stage 8 and the palisade southbound on 13, so a journal short of
# complete must not be handed a stage that opens them.
def tirannwn_stage():
    from rs2004.quests.defs.regicide.journal import RG_STAGE
    return RG_STAGE.COMPLETE if quests.status('Regicide') == 'complete' else RG_STAGE.NOT_STARTED


def crosses_tirannwn(dest):
    """Whether either end of the walk sits in a pocket the walker's graph has no edges through."""
    return (dest is not None and _pocket_at(dest) is not None) or _pocket_at(game.tile()) is not None


def walk_across_tirannwn(dest, radius, log, opts=None):
    """Travel to dest using teleports out or the Isafdar crossings."""
    from rs2004.quests.defs.legends.jungle import leave_jungle
    from rs2004.quests.defs.regicide.pockets import travel_tirannwn
    options = opts if opts is not None else {}
    if in_kharazi(game.tile()):
        left = yield from leave_jungle(log)
        if not left:
            return False
    jungle = in_kharazi(dest)
    target = JUNGLE_MOUTH if jungle else Tile(dest.x, dest.z, dest.level)
    yield from _teleport_out(target, log, options)
    if event_signal.pending():
        return False
    fields = {}
    for key in ('use_teleport_catalog', 'policy'):
        if key in options:
            fields[key] = options[key]
    arrived = yield from travel_tirannwn(target, 0 if jungle else radius, tirannwn_stage(), log, fields)
    if not arrived:
        return False
    if not jungle:
        return True
    crossed = yield from walk_across_kharazi(dest, radius, log, options)
    return crossed

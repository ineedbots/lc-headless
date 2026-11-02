"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/jungle.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.legends.areas import JUNGLE_BAND, LQ_ID, LQ_LOC, LQ_NPC, LQ_TILE, in_jungle_band, jungle_section, legends_area
from rs2004.quests.defs.legends.fight import fight
from rs2004.quests.defs.legends.scene import clear_boxes, drive_boxes, drive_to_end, drive_until, held_id, here, modal_text, offer_to, said_any, settle_scene
from rs2004.quests.defs.legends.viyeldi import leave_caves
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['enter_jungle', 'leave_jungle', 'map_jungle', 'get_bullroarer', 'summon_gujuo', 'talk_gujuo', 'talk_gujuo_status']

CHOP_ATTEMPTS = 14
CHOP_MS = 180000


# Why: every plant felled through the band leaves its logs in a pack with no slot to spare, and the reed at the pool fails for want of one.
# Why: The final `inv_add` lands on the crossing tick, so wait before reading the pack count.
def is_logs(name):
    return ((name if name is not None else '')).lower().endswith('logs')


def drop_logs():
    """Drop whatever the band's plants left behind."""
    for pass_ in range(3):
        yield from settle_scene()
        logs = [item for item in inventory.items() if is_logs(item.name)]
        if len(logs) == 0:
            return
        for log in logs:
            log.interact('Drop')
            yield from execution.delay_ticks(1)


# Why: the dense band that seals the Kharazi Jungle is map-blocked ground with a jungle plant standing on each tile, and `chop_jungle` teleports the chopper 2 tiles towards the plant it fells.
# Why: (2816,2940) is the one mainland tile with an unbroken 2-plant column south of it, landing on open jungle at (2816,2936).
def pick_plant(dz):
    """The choppable jungle plant to take next, straight ahead before any diagonal."""
    me = game.tile()
    if not me:
        return None

    def _fn1(l):
        t = l.tile()
        return t.level == me.level and (1 if t.z - me.z > 0 else (-1 if t.z - me.z < 0 else 0)) == dz and abs(t.z - me.z) <= 2 and abs(t.x - me.x) <= 1
    candidates = locs.query().name(LQ_LOC.JUNGLE_BUSH, LQ_LOC.JUNGLE_TREE).action('Chop-down').where(_fn1).results()
    # Why: Diagonal chops move onto blocked ground, so approach jungle plants cardinally.
    ordered = sorted(candidates, key=lambda l: abs(l.tile().x - me.x) * 100 + abs(l.tile().z - me.z))
    return ordered[0] if len(ordered) > 0 else None


def moved_off(before):
    """Whether a chop has teleported the chopper off the row it swung from."""
    now = game.tile()
    return now is not None and before is not None and now.z != before.z


def chop_through_band(dz, done, log):
    deadline = _core.step_time() + CHOP_MS
    # Why: the crossing that succeeds leaves through this condition, so the drop below has to be on its way out too.
    for i in range(CHOP_ATTEMPTS):
        if _core.step_time() >= deadline or done():
            break
        plant = pick_plant(dz)
        if not plant:
            log(f"no choppable jungle plant {('north' if dz > 0 else 'south')} of ({(game.tile().x if game.tile() is not None else None)},{(game.tile().z if game.tile() is not None else None)}) — waiting for a respawn")
            yield from execution.delay_ticks(6)
            continue
        before = game.tile()
        if not (plant.interact('Chop-down')):
            continue
        yield from execution.delay_until(lambda: done() or moved_off(before), 20000)
    yield from drop_logs()
    return done()


# Why: `start_chop_jungle` checks the machete, an axe and the notes before the first swing, and a missing one answers with a message box the walker can't see.
def through_south():
    now = game.tile()
    return (now.z if now is not None else 9999) <= JUNGLE_BAND.south


def through_north():
    now = game.tile()
    return (now.z if now is not None else 0) >= JUNGLE_BAND.north


def enter_jungle(log):
    """Hack south through the dense band into the Kharazi Jungle."""
    if through_south() and here() == 'jungle':
        return True
    if not in_jungle_band(game.tile()):
        # Why: the mouth is a mainland tile, so a leg resumed inside the caves has to climb out of them before it can be walked to.
        _w4 = yield from leave_caves(log)
        if not (_w4):
            return False
        if through_south() and here() == 'jungle':
            return True
        _w5 = yield from traversal.walk_resilient(LQ_TILE.JUNGLE_MOUTH, radius=0, attempts=4, timeout_ms=240000, log=log)
        if not (_w5):
            return False
    yield from settle_scene()
    ok = yield from chop_through_band(-1, through_south, log)
    if not ok:
        log('could not cut through the dense jungle band')
    return ok


def leave_jungle(log):
    """Hack north out of the jungle onto open Karamja."""
    if here() != 'jungle':
        return True
    _c6 = not in_jungle_band(game.tile())
    if _c6:
        _w7 = yield from traversal.walk_resilient(LQ_TILE.JUNGLE_INSIDE, radius=0, attempts=4, timeout_ms=240000, log=log)
        _c6 = not (_w7)
    if _c6:
        return False
    yield from settle_scene()
    _result8 = yield from chop_through_band(1, through_north, log)
    return _result8


MAP_ANCHORS = [
    Record({'section': 'west', 'tile': LQ_TILE.MAP_WEST}),
    Record({'section': 'middle', 'tile': LQ_TILE.MAP_MIDDLE}),
    Record({'section': 'east', 'tile': LQ_TILE.MAP_EAST}),
]
MAPPED = ['neatly add a new section', 'already completed this part']
SHORT = ['additional papyrus', 'additional charcoal', 'need some papyrus and charcoal']
# Why: `stat_random(crafting, 100, 250)` misses often at the quest's own requirement, and each miss prints one of these 4.
MISSED = ['make a mess but are able to rescue', 'snap your stick of charcoal', 'make a mess of the map', 'landing on your charcoal and papyrus']
MAP_ATTEMPTS = 20


# Why: the roll is announced by "You prepare to start mapping this area..." and the result lands a box later, so drive the first box or every attempt times out.
def draw_section(log):
    """One "Complete" on the notes, and what the message box said about it."""
    notes = ([item for item in inventory.items() if item.id == LQ_ID.MAP] or [None])[0]
    if not notes:
        return ('done' if held_id(LQ_ID.MAP_COMPLETE) > 0 else 'short')
    if not (notes.interact('Complete')):
        return 'retry'
    said = ['']

    def answered():
        text = modal_text()
        if said_any(text, MAPPED) or said_any(text, SHORT) or said_any(text, MISSED):
            said[0] = text
            return True
        return held_id(LQ_ID.MAP_COMPLETE) > 0
    yield from drive_until(answered, [], log, 20000)
    yield from clear_boxes()
    if held_id(LQ_ID.MAP_COMPLETE) > 0 or said_any(said[0], MAPPED):
        return 'done'
    if said_any(said[0], SHORT):
        log('out of papyrus or charcoal mid-map')
        return 'short'
    return 'retry'


# Why: the 3 section bits are `%legends_bits` and never reach the client, so the loop visits all 3 every pass and lets an already-drawn section say so.
# Why: the notes turning into the completed copy is the leg's only oracle.
def map_jungle(log):
    """Map all 3 thirds of the jungle."""
    if held_id(LQ_ID.MAP_COMPLETE) > 0:
        return True
    _w10 = yield from enter_jungle(log)
    if not (_w10):
        return False
    for anchor in MAP_ANCHORS:
        if held_id(LQ_ID.MAP_COMPLETE) > 0:
            return True
        _c11 = jungle_section(game.tile()) != anchor.section
        if _c11:
            _w12 = yield from traversal.walk_resilient(anchor.tile, radius=3, attempts=3, timeout_ms=240000, log=log)
            _c11 = not (_w12)
        if _c11:
            return False
        yield from settle_scene()
        drawn = False
        for i in range(MAP_ATTEMPTS):
            if drawn:
                break
            result = yield from draw_section(log)
            if result == 'short':
                return False
            drawn = result == 'done' or held_id(LQ_ID.MAP_COMPLETE) > 0
            yield from execution.delay_ticks(1)
        if not drawn:
            log(f'the {anchor.section} section would not draw')
            return False
        log(f'mapped the {anchor.section} third of the Kharazi Jungle')
    return held_id(LQ_ID.MAP_COMPLETE) > 0


FORESTER_PREFER = ['Yes, go ahead make a copy!', 'What will you give me in return?']


# Why: the forester lives on open Karamja, north of the band, so this leg starts by cutting back out.
def get_bullroarer(log):
    """Trade a copy of the finished map for the bullroarer."""
    if held_id(LQ_ID.BULLROARER) > 0:
        return True
    _w13 = yield from leave_jungle(log)
    if not (_w13):
        return False
    _w14 = yield from traversal.walk_resilient(LQ_TILE.FORESTER, radius=4, attempts=3, timeout_ms=180000, log=log)
    if not (_w14):
        return False
    yield from settle_scene()
    forester = npcs.query().name(LQ_NPC.FORESTER).within(12).nearest()
    if not forester:
        log('no forester in range for the map')
        return False
    _w15 = yield from offer_to(LQ_ID.MAP_COMPLETE, forester, log)
    if not (_w15):
        return False
    # Why: the forester hands the roarer through `~objbox`, and the `inv_add` behind it only runs once the box is clicked; a chat-only driver holds the script shut.
    _result16 = yield from drive_boxes(lambda: held_id(LQ_ID.BULLROARER) > 0, 60000, FORESTER_PREFER, log)
    return _result16


GUJUO_LEASH = 14
# Why: he spawns up to 7 tiles off and walks in, so the wait covers the approach with room over.
GUJUO_APPROACH_MS = 6000


def find_gujuo():
    return npcs.query().name(LQ_NPC.GUJUO).within(GUJUO_LEASH).nearest()


# Why: `bullroarer.rs2` sets the jungle's oomlie birds, wolves and savages on whoever is swinging, and a savage kills a pack with 4 sharks in it while the swinger stands there; rs2b0t's wait neither ate nor hit back.
ROARER_ENEMIES = ['Oomlie Bird', 'Jungle Wolf', 'Jungle Savage']
SWING_WAIT_TICKS = 20
ROARER_FIGHT_MS = 120000


def roarer_enemy():
    return npcs.query().name(*ROARER_ENEMIES).action('Attack').where(lambda npc: npc.targets_me()).within(GUJUO_LEASH).nearest()


def see_off_enemy(log):
    """Kill whatever the noise set on us, without the prayer the blessing rolls against."""
    enemy = roarer_enemy()
    if enemy is None:
        return
    log(f'{enemy.name} answered the bull roarer')
    yield from fight(Record({'npc': enemy.name, 'done': lambda: roarer_enemy() is None, 'ms': ROARER_FIGHT_MS, 'pray': False}), log)


def wait_for_gujuo(log):
    """The wait after a swing, in ticks, since an attacker hits by the tick whatever the clock says."""
    for i in range(SWING_WAIT_TICKS):
        if find_gujuo():
            return
        yield from see_off_enemy(log)
        yield from sustain.run()
        yield from execution.delay_ticks(1)


# Why: every Gujuo conversation ends in `npc_del`, so he's re-summoned for each one.
# Why: the roarer only answers inside the jungle zone, and it carries an 8-tick cooldown of its own.
def summon_gujuo(log):
    """Swing the bullroarer until Gujuo walks out of the trees."""
    if find_gujuo():
        return True
    _w17 = yield from enter_jungle(log)
    if not (_w17):
        return False
    now = game.tile()
    if legends_area(now) == 'jungle' and now.z > 2932:
        walked = yield from traversal.walk_resilient(LQ_TILE.BULLROARER_SPOT, radius=4, attempts=3, timeout_ms=120000, log=log)
        if not walked:
            return False
    for i in range(12):
        if find_gujuo():
            return True
        roarer = ([item for item in inventory.items() if item.id == LQ_ID.BULLROARER] or [None])[0]
        if not roarer:
            log('no bull roarer in the pack')
            return False
        if roarer.interact('Swing'):
            yield from wait_for_gujuo(log)
        yield from execution.delay_ticks(4)
    log('twelve swings and no native answered')
    return False


# Why: Gujuo starts the conversation himself once summoned (`ai_opplayer2`), so opening one is a race the driver has to tolerate.
# Why: half his conversations end themselves, he says goodbye and `npc_del`s, so those have no goal to wait on and `driveUntil` would burn its budget after the chat had closed.
def talk_gujuo(prefer, goal=None, ms=90000, required=None):
    """Summon Gujuo and drive his conversation, to a goal or to its own end."""
    talk = talk_gujuo_status(prefer, goal, ms, required)

    def run(log):
        ended = yield from talk(log)
        return ended == 'goal'
    return run


# Why: A missing topic and no dialogue require different recovery; conflating them repeats a cave trip without changing state.
def talk_gujuo_status(prefer, goal=None, ms=90000, required=None):
    """Talk to Gujuo, reporting which of the 3 ways it ended."""

    def run(log):
        if goal is not None and goal():
            return 'goal'
        # Why: not reaching him and reaching a shaman who says nothing both mean try again where we stand, but they're different failures, and one word for both hides which.
        _w23 = yield from summon_gujuo(log)
        if not (_w23):
            log('never got to Gujuo — the walk in or the summon failed, not the talk')
            return 'nodialog'

        # Why: the roarer leaves him in `opplayer2`, and `[ai_opplayer2,gujuo]` walks him over and opens `gujuo_start` on its own. A Talk-to click sent into that approach sets you walking too, so both move and neither talks.
        def spoke():
            return chat_dialog.is_open() or chat_dialog.can_continue()
        _w24 = yield from execution.delay_until(spoke, GUJUO_APPROACH_MS)
        if not (_w24):
            _v25 = game.tile()
            status = yield from reach.npc_dialog(LQ_NPC.GUJUO, (_v25 if _v25 is not None else LQ_TILE.BULLROARER_SPOT), log=log)
            if status != 'done':
                log('Gujuo never opened a dialogue')
                return 'nodialog'
        # Why: `gujuo_vessel` hands the sketch through `~objbox`, which renders in the main modal and suspends the script until clicked. `driveUntil` clicks the chat modal alone, so the box would stand and the sketch never come.
        if goal is not None:
            ok = yield from drive_boxes(goal, ms, prefer, log)
        else:
            ok = yield from drive_to_end(prefer, log, ms, required)
        return 'goal' if ok else 'nogoal'
    return run

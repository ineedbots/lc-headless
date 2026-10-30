"""Ported from rs2b0t's src/bot/api/ai/quests/defs/hazeelcult.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, reader
from rs2004.geometry import Tile
from rs2004.quests.data import quest_record
from rs2004.quests.journal_text import normalize_journal
from rs2004.quests.engine.types import QuestModule, QuestProgress, has_flag
from rs2004.quests.exec.primitives import goto_npc, is_underground, talk_strict, walk_with_hops
from rs2004.quests.exec.prompts import drive_choice, drive_until, held_id, settle_scene
from rs2004.reach import reach
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = ['HC_STAGE', 'ARMOUR_OBJ', 'parse_hazeel_journal', 'read_hazeel_progress', 'in_hideout', 'at_cave_mouth', 'decide', 'hazeelcult']

QUEST = 'Hazeel Cult'
HC_STAGE = Record({
    'NOT_STARTED': 0,
    'STARTED': 2,
    'SPOKEN_CLIVET': 3,
    'REFUSED_CULT': 4,
    'POURED_POISON': 5,
    'KILLED_ALOMONE': 6,
    'RETURNED_ARMOUR': 7,
    'COMPLETE': 9,
})
ARMOUR_OBJ = 2405
ARMOUR_NAME = 'Carnillean armour'
RAFT_LOC = 2849
CUPBOARD_SHUT = 2850
CUPBOARD_OPEN = 2851
QUEST_BANK = Tile(2655, 3283, 0)
CAVE_MOUTH = Tile(2585, 3233, 0)
SEWER_LANDING = Tile(2570, 9682, 0)
FOREST_TOP = Tile(2587, 3237, 0)
RAFT_IN = Tile(2567, 9680, 0)
RAFT_OUT = Tile(2606, 9692, 0)
ALOMONE_TILE = Tile(2609, 9669, 0)
CUPBOARD = Tile(2573, 3267, 1)
# Why: the cave mouth is a teleport and the hideout has no walking exit, so these 2 are the only crossings the walker may pick itself.
HOPS = [
    Record({'stand': CAVE_MOUTH, 'loc_name': 'Cave entrance', 'op': 'Enter', 'arrive': SEWER_LANDING}),
    Record({'stand': SEWER_LANDING, 'loc_name': 'Stairs', 'op': 'Climb-up', 'arrive': FOREST_TOP}),
]
CERIL_START = Record({
    'npc': 'Ceril Carnillean',
    'anchor': Tile(2565, 3269, 0),
    'leash': 6,
    'prefer': ["what's wrong", 'yes, of course'],
})
# Why: "You're crazy" and "No. I won't do it." both reach `clivet_hazeel_cultist_fool`, which locks the Carnillean side in; "Ok, count me in" can't be undone.
CLIVET = Record({
    'npc': 'Clivet',
    'anchor': Tile(2566, 9682, 0),
    'leash': 10,
    'prefer': ['what do you mean', "you're crazy", "no. i won't do it"],
})
CERIL_RETURN = Record({'npc': 'Ceril Carnillean', 'anchor': Tile(2574, 3268, 1), 'leash': 6, 'prefer': []})
# Why: `_hazeelcult_valve` sets its bit on Turn-left for `sewervalve3` only and Turn-right for the other 4, and `count_correct_valves` counts a prefix, so all 5 must be set before the raft moves.
VALVES = [
    Record({'id': 2844, 'op': 'Turn-right', 'tile': Tile(2562, 3247, 0)}),
    Record({'id': 2845, 'op': 'Turn-right', 'tile': Tile(2572, 3263, 0)}),
    Record({'id': 2846, 'op': 'Turn-left', 'tile': Tile(2585, 3245, 0)}),
    Record({'id': 2847, 'op': 'Turn-right', 'tile': Tile(2597, 3263, 0)}),
    Record({'id': 2848, 'op': 'Turn-right', 'tile': Tile(2609, 3243, 0)}),
]
# Why: `%hazeelcult_valves` is `scope=perm` with no transmit, so where the raft stops is the only oracle; this holds what the last ride proved.
valves_turned = False
EVIL = 'evil'
# Why: the page is cumulative, so the most advanced line wins; the cult-side lines are read only so the module can say why it won't run.
STAGE_LINES = [
    ['quest complete!', HC_STAGE.COMPLETE, False],
    ["i returned the armour, but ceril didn't believe", HC_STAGE.RETURNED_ARMOUR, False],
    ['i found the scroll needed to revive hazeel', HC_STAGE.RETURNED_ARMOUR, True],
    ['i managed to enter the hideout, kill the cult leader', HC_STAGE.KILLED_ALOMONE, False],
    ['told me to find a spell scroll', HC_STAGE.KILLED_ALOMONE, True],
    ['i spoke to clivet and he told me that i had failed', HC_STAGE.POURED_POISON, True],
    ['having decided to assist the cult', HC_STAGE.POURED_POISON, True],
    ['told me the truth about the', HC_STAGE.REFUSED_CULT, True],
    ['he jumped onto a raft and headed into the', HC_STAGE.REFUSED_CULT, False],
    ['he told me a pack of lies about the carnilleans', HC_STAGE.SPOKEN_CLIVET, False],
    ['who were responsible live in a cave', HC_STAGE.STARTED, False],
    ['i can start this quest by talking to', HC_STAGE.NOT_STARTED, False],
]


def parse_hazeel_journal(lines):
    text = normalize_journal(lines)
    hit = ([entry for entry in STAGE_LINES if entry[0] in text] or [None])[0]
    if hit is None:
        return None
    return QuestProgress(hit[1], set(([EVIL] if hit[2] else [])))


def read_hazeel_progress():
    status = quests.status(QUEST)
    if status == 'complete':
        return QuestProgress(HC_STAGE.COMPLETE, set())
    if status == 'not_started':
        return QuestProgress(HC_STAGE.NOT_STARTED, set())
    if status != 'in_progress':
        return None
    _w2 = yield from quests.journal(QUEST)
    progress = parse_hazeel_journal(_w2)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return progress


# Why: both boxes are the walkable components from the baked collision pack, since the 4 sewer islands and the mansion cellar share the mapsquare.
def in_hideout(t):
    """The cult hideout, a pocket whose only way out is the raft beside it."""
    return is_underground(t) and t.x >= 2601 and t.x <= 2612 and t.z >= 9666 and t.z <= 9693


def at_cave_mouth(t):
    """Where the cave entrance drops you: Clivet, the stairs back up, and the raft in."""
    return is_underground(t) and t.x >= 2565 and t.x <= 2571 and t.z >= 9680 and t.z <= 9685


def loc_by_id(id, within=6):
    return locs.query().where(lambda l: l.id == id).within(within).nearest()


def clear_boxes(log):
    """Click through whatever `~mesbox` the last action put on the chat interface."""
    return drive_until(lambda: not chat_dialog.is_open() and not chat_dialog.can_continue(), [], log, 8000)


def board_raft(within, log):
    from_ = game.tile()
    raft = loc_by_id(RAFT_LOC, within)
    if not from_ or not raft:
        log('hazeelcult: no raft within reach')
        return False
    if not (raft.interact('Board')):
        return False
    # Why: with the valves wrong the raft stays put and says so in chat, so where you end up separates a ride from a refusal.
    start = Tile.from_tile(from_)

    def _fn3():
        t = game.tile()
        return t is not None and start.distance_to(t) > 4
    rode = yield from execution.delay_until(_fn3, 10000)
    yield from clear_boxes(log)
    if rode:
        yield from settle_scene()
    return rode


# Why: `Reach.locOp` walks then gives up when the loc starts out of scene, and the 5 valves stand 20 tiles apart, so a leg that bailed there would walk valve to valve and never turn one.
REACH_TRIES = 3


def turn_valve(valve, log):
    for attempt in range(REACH_TRIES):
        # Why: Close the previous valve's result box before using the next box as confirmation.
        yield from clear_boxes(log)
        status = yield from reach.loc_op('Sewer valve', valve.op, valve.tile, lambda: chat_dialog.is_open() or chat_dialog.can_continue(), id=valve.id, within=6, log=log)
        if status == 'done':
            yield from clear_boxes(log)
            return True
        if status == 'unreachable':
            break
    log(f'hazeelcult: the valve at ({valve.tile.x},{valve.tile.z}) would not turn')
    return False


def turn_valves(log):
    for valve in VALVES:
        _w4 = yield from turn_valve(valve, log)
        if not (_w4):
            return False
    log('hazeelcult: all five sewer valves are set')
    return True


def to_hideout(log):
    global valves_turned
    """Ride in, re-setting the valves whenever the raft proves them wrong."""
    here = game.tile()
    if not here:
        return False
    if in_hideout(here):
        return True
    if is_underground(here) and not at_cave_mouth(here):
        log('hazeelcult: stranded on a sewer island — riding back to the cave mouth')
        valves_turned = False
        yield from board_raft(10, log)
        return False
    if not valves_turned:
        if is_underground(here):
            yield from walk_with_hops(CAVE_MOUTH, 3, HOPS, log)
            return False
        _w5 = yield from turn_valves(log)
        if not (_w5):
            return False
        valves_turned = True
    # Why: the cave entrance is a teleport and the client pathfind burns 5 repaths while the scene is unbuilt, so land the hop first and walk the last 3 tiles after it settles.
    _w6 = yield from walk_with_hops(SEWER_LANDING, 5, HOPS, log)
    if not (_w6):
        return False
    yield from settle_scene()
    _w7 = yield from traversal.walk_resilient(RAFT_IN, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w7):
        return False
    _w8 = yield from board_raft(4, log)
    if not (_w8):
        log('hazeelcult: the raft would not move — the sewer valves are wrong')
        valves_turned = False
        return False
    _v9 = game.tile()
    if in_hideout((_v9 if _v9 is not None else SEWER_LANDING)):
        return True
    log('hazeelcult: the raft stopped short of the hideout — re-setting the valves')
    valves_turned = False
    return False


def leave_hideout(log):
    """The raft out is the pocket's only exit, so every leg above ground starts here."""
    here = game.tile()
    if not here or not in_hideout(here):
        return True
    _w10 = yield from traversal.walk_resilient(RAFT_OUT, radius=1, attempts=3, timeout_ms=90000, log=log)
    if not (_w10):
        return False
    log('hazeelcult: riding the raft back out of the hideout')
    _result11 = yield from board_raft(4, log)
    return _result11


def to_surface(log):
    """Climb out of the sewer, so a leg above ground can let `Reach` own its own approach."""
    _w12 = yield from leave_hideout(log)
    if not (_w12):
        return False
    here = game.tile()
    if not here or not is_underground(here):
        return True
    _result13 = yield from walk_with_hops(FOREST_TOP, 3, HOPS, log)
    return _result13


def armour_on_floor():
    return ground_items.query().where(lambda g: g.id == ARMOUR_OBJ).within(16).nearest()


def take_armour(log):
    if held_id(ARMOUR_OBJ) > 0:
        return True
    drop = armour_on_floor()
    if not drop:
        log('hazeelcult: no Carnillean armour on the hideout floor')
        return False
    if not (drop.interact('Take')):
        return False
    _result14 = yield from execution.delay_until(lambda: held_id(ARMOUR_OBJ) > 0, 8000)
    return _result14


# Why: `defeat_alomone_hazeel_cultist` drops the armour on every kill while no copy exists, so a despawned drop is recovered by fighting him again.
def slay_alomone(log):
    _w15 = yield from traversal.walk_resilient(ALOMONE_TILE, radius=4, attempts=3, timeout_ms=90000, log=log)
    if not (_w15):
        return False
    alomone = npcs.query().name('Alomone').action('Attack').within(12).nearest()
    if not alomone:
        log(f'hazeelcult: no Alomone to attack near ({ALOMONE_TILE.x},{ALOMONE_TILE.z})')
        return False
    index = alomone.index
    game.set_combat_style('strength')
    if not (alomone.interact('Attack')):
        return False
    log('hazeelcult: fighting Alomone for the Carnillean armour')
    deadline = _core.step_time() + 90000
    while _core.step_time() < deadline:
        current = ([n for n in npcs.all() if n.index == index and n.name == 'Alomone'] or [None])[0]
        if current is None:
            return True
        # Why: `Sustain.run` pumps the host's eat hook, so a fight held inside one custom step never eats without this.
        yield from sustain.run()
        if game.facing() != ('npc', index):
            if not current.interact('Attack'):
                return False
        yield from execution.delay_ticks(1)
    log('hazeelcult: Alomone outlasted the fight budget')
    return False


def fetch_armour(log):
    if held_id(ARMOUR_OBJ) > 0:
        return True
    _w16 = yield from to_hideout(log)
    if not (_w16):
        return False
    _w17 = yield from take_armour(log)
    if _w17:
        return True
    _w18 = yield from slay_alomone(log)
    if not (_w18):
        return False
    # Why: `ai_queue3` adds the drop a few ticks after the corpse leaves the scene, so the first look at the floor is too early.
    yield from execution.delay_until(lambda: armour_on_floor() is not None, 8000)
    _result19 = yield from take_armour(log)
    return _result19


def chat(stop):
    def _fn20(log):
        _w21 = yield from leave_hideout(log)
        if not (_w21):
            return False
        _w22 = yield from goto_npc(stop, HOPS, log)
        if not (_w22):
            return False
        _result23 = yield from talk_strict(stop.npc, stop.prefer, log)
        return _result23
    return _fn20


ask_ceril = chat(CERIL_START)
refuse_clivet = chat(CLIVET)
# Why: `hazeelcult_fake_complete` opens the reward scroll on a main modal part-way through, so the chat driver returns with Ceril's lines unread; the stage is already 7 by then.
return_armour = chat(CERIL_RETURN)


# Why: every loc query reads empty for a tick after a level change, so the climb and the open take 2 tries, same as the valves.
def open_cupboard(log):
    for attempt in range(REACH_TRIES):
        if loc_by_id(CUPBOARD_OPEN, 6):
            return True
        status = yield from reach.loc_op('Cupboard', 'Open', CUPBOARD, lambda: loc_by_id(CUPBOARD_OPEN, 6) is not None, id=CUPBOARD_SHUT, within=6, log=log)
        if status == 'done':
            return True
        if status == 'unreachable':
            break
        yield from settle_scene()
    return False


def quest_done():
    return quests.status(QUEST) == 'complete'


CHAT_QUIET_TICKS = 4


# Why: the short branch ends in silence, so a plain `driveUntil` on the journal burns its full budget whenever Ceril or Jones is out of range; quiet chat means the short branch.
def drive_to_complete(log):
    deadline = _core.step_time() + 120000
    quiet = 0
    while _core.step_time() < deadline:
        if quest_done():
            return True
        if chat_dialog.is_open() or chat_dialog.can_continue():
            quiet = 0
            yield from drive_choice([], log)
            continue
        quiet += 1
        if quiet >= CHAT_QUIET_TICKS:
            log('hazeelcult: the accusation stopped short — Ceril or Jones was out of earshot')
            return False
        yield from execution.delay_ticks(1)
    return quest_done()


# Why: `oploc1,hazeelcbopen` bails silently unless Ceril and Jones are both inside `npc_find(..., 6, 0)`, so the leg runs again.
def search_cupboard(log):
    _w24 = yield from to_surface(log)
    if not (_w24):
        return False
    _w25 = yield from open_cupboard(log)
    if not (_w25):
        log(f'hazeelcult: no cupboard to open at ({CUPBOARD.x},{CUPBOARD.z},{CUPBOARD.level})')
        return False
    status = yield from reach.loc_op('Cupboard', 'Search', CUPBOARD, lambda: quest_done() or chat_dialog.is_open() or chat_dialog.can_continue(), id=CUPBOARD_OPEN, within=6, log=log)
    if status != 'done':
        return False
    _result26 = yield from drive_to_complete(log)
    return _result26


def custom(name, run):
    return Record({'kind': 'custom', 'name': name, 'run': run})


def holds_armour(snap):
    _v27 = (snap.inv_ids or {}).get(ARMOUR_OBJ)
    return ((_v27 if _v27 is not None else 0)) > 0 or (((ARMOUR_OBJ in (snap.worn_ids or set())) if (ARMOUR_OBJ in (snap.worn_ids or set())) is not None else False))


# Why: `~obj_gettotal` counts the bank too, so a banked suit stops Alomone dropping another and withdrawing is the only way on.
def armour_leg(snap):
    if holds_armour(snap):
        return custom('return the armour to Ceril upstairs', return_armour)
    # Why: no bank is reachable from the pocket, so the drop on the floor beside us comes before any bank question.
    if snap.tile and in_hideout(snap.tile):
        return custom('take the Carnillean armour from the cult hideout', fetch_armour)
    if snap.bank_known != True:
        return Record({'kind': 'scan_bank'})
    _v28 = (snap.bank_ids or {}).get(ARMOUR_OBJ)
    if ((_v28 if _v28 is not None else 0)) > 0:
        return Record({'kind': 'withdraw', 'items': [{'name': ARMOUR_NAME, 'id': ARMOUR_OBJ, 'qty': 1}]})
    return custom('take the Carnillean armour from the cult hideout', fetch_armour)


def decide(snap):
    if snap.journal == 'complete':
        return Record({'kind': 'done'})
    if snap.journal == 'unknown':
        return Record({'kind': 'wait', 'reason': 'quest journal not loaded'})
    progress = snap.progress
    if progress is None:
        return Record({'kind': 'wait', 'reason': 'Hazeel Cult journal stage unavailable'})
    if has_flag(progress, EVIL):
        return Record({'kind': 'wait', 'reason': 'this character joined the cult; the module runs the Carnillean side only'})
    if progress.stage == HC_STAGE.NOT_STARTED:
        return custom('ask Ceril Carnillean about the stolen armour', ask_ceril)
    elif progress.stage in [HC_STAGE.STARTED, HC_STAGE.SPOKEN_CLIVET]:
        return custom('refuse Clivet at the cult cave', refuse_clivet)
    elif progress.stage == HC_STAGE.REFUSED_CULT:
        return custom('take the Carnillean armour from the cult hideout', fetch_armour)
    elif progress.stage == HC_STAGE.KILLED_ALOMONE:
        return armour_leg(snap)
    elif progress.stage == HC_STAGE.RETURNED_ARMOUR:
        return custom("search Jones' cupboard for the evidence", search_cupboard)
    else:
        return Record({'kind': 'wait', 'reason': f'Hazeel Cult stage {progress.stage} is not implemented'})


hazeelcult = QuestModule(
    record=quest_record('hazeelcult'),
    resume_at=lambda tile: in_hideout(tile) or at_cave_mouth(tile),
    bank=QUEST_BANK,
    hops=HOPS,
    food=6,
    tools=[ARMOUR_NAME.lower()],
    read_progress=read_hazeel_progress,
    exit=leave_hideout,
    decide=decide,
)

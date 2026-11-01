"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/caves.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import ground_items, locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.watchtower.areas import WT_CAVES, WT_ITEM, WT_LOC, WT_NIGHTSHADE, WT_NPC, watchtower_area
from rs2004.quests.defs.watchtower.gutanoth import cross_east_gate, leave_east_gate
from rs2004.quests.defs.watchtower.scene import settle_scene
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import talk_choosing_by, talk_strict
from rs2004.traversal import traversal

__all__ = ['next_skavid_cave', 'leave_cave', 'learn_from_scared_skavid', 'learn_word', 'take_nightshade', 'answer_mad_skavid']

SKAVID_REPLIES = {1: 'Nod.', 2: 'Ig.', 3: 'Ar.', 4: 'Cur.'}
WORD_FLAG = {1: 'learned-nod', 2: 'learned-ig', 3: 'learned-ar', 4: 'learned-cur'}
MAD_SKAVID_RULES = [
    Record({'when_line': 'ar cur', 'choose': 'Gor.'}),
    Record({'when_line': 'bidith ig', 'choose': 'Cur.'}),
    Record({'when_line': 'cur tanath', 'choose': 'Bidith.'}),
    Record({'when_line': 'gor nod', 'choose': 'Tanath.'}),
]


def next_skavid_cave(progress):
    """Cave 5 first: the scared skavid is what unlocks talking to the other four."""
    if not has_flag(progress, 'learning-skavid'):
        return 5
    for index in [1, 2, 3, 4]:
        if not has_flag(progress, WORD_FLAG[index]):
            return index
    return 6


def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def loc_near(id, op, within=20):
    return locs.query().where(lambda loc: loc.id == id).action(op).within(within).nearest()


def enter_cave(index, log):
    cave = ([entry for entry in WT_CAVES if entry.index == index] or [None])[0]
    start = game.tile()
    if start and watchtower_area(start) == 'skavidCaves':
        # The 6 caves are separate sealed rooms, so being in one only helps if it's this one; otherwise walk out first.
        if cave.landing.distance_to(start) <= 5:
            return True
        _w1 = yield from leave_cave(log)
        if not (_w1):
            return False
    _w2 = yield from traversal.walk_resilient(cave.stand, radius=1, attempts=3, timeout_ms=300000, log=log)
    if not (_w2):
        return False
    mouth = loc_near(WT_LOC.CAVE_IN[index - 1], 'Enter', 10)
    if not mouth or not (mouth.interact('Enter')):
        log(f'no cave {index} entrance in range')
        return False
    _w3 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'skavidCaves', 12000)
    if not (_w3):
        return False
    yield from settle_scene()
    # Why: p_teleport lands on the landing tile, so anything further out means you were dumped in the dark cave.
    # Why: cave 4's landing is only 9 tiles from it, so the tolerance has to be tight.
    here = game.tile()
    if here and cave.landing.distance_to(here) > 5:
        log(f'landed away from cave {index} — the map or the lit light source is missing')
        return False
    return True


def leave_cave(log):
    if watchtower_area(game.tile()) != 'skavidCaves':
        return True
    exit = locs.query().where(lambda loc: (loc.id in WT_LOC.CAVE_OUT)).action('Leave').within(24).nearest()
    if exit:
        if not (exit.interact('Leave')):
            return False
    else:
        # The dark cave has no ordinary exit, only a climbing rope.
        rope = loc_near(WT_LOC.DARK_CAVE_ESCAPE, 'Climb', 32)
        if not rope or not (rope.interact('Climb')):
            log('no cave exit in range')
            return False
    _w4 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'skavidCaves', 12000)
    if not (_w4):
        return False
    yield from settle_scene()
    return True


def reach_skavid(index, log):
    _w5 = yield from enter_cave(index, log)
    if not (_w5):
        return False
    cave = ([entry for entry in WT_CAVES if entry.index == index] or [None])[0]
    _result6 = yield from traversal.walk_resilient(cave.landing, radius=8, attempts=2, timeout_ms=60000, log=log)
    return _result6


def learn_from_scared_skavid(log):
    _w7 = yield from reach_skavid(5, log)
    if not (_w7):
        return False
    _w8 = yield from talk_strict(WT_NPC.SCARED_SKAVID, ["Okay, okay, I'm not going to hurt you."], log)
    if not (_w8):
        return False
    _result9 = yield from leave_cave(log)
    return _result9


def learn_word(index, log):
    _w10 = yield from reach_skavid(index, log)
    if not (_w10):
        return False
    _w11 = yield from talk_strict(WT_NPC.SKAVID, [SKAVID_REPLIES[index]], log)
    if not (_w11):
        return False
    _result12 = yield from leave_cave(log)
    return _result12


def take_nightshade(log):
    if held_id(WT_ITEM.NIGHTSHADE.id) > 0:
        return True
    # Cave 2's mouth is on the main component; cave 6's sits behind the battlement.
    _w13 = yield from enter_cave(2, log)
    if not (_w13):
        return False
    _w14 = yield from traversal.walk_resilient(WT_NIGHTSHADE.cave2, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w14):
        return False
    plant = ground_items.query().name(WT_ITEM.NIGHTSHADE.name).within(4).nearest()
    if not plant or not (plant.interact('Take')):
        log('no Nightshade on the cave floor — it respawns, so this is worth retrying')
        return False
    _w15 = yield from execution.delay_until(lambda: held_id(WT_ITEM.NIGHTSHADE.id) > 0, 6000)
    if not (_w15):
        return False
    _result16 = yield from leave_cave(log)
    return _result16


def answer_mad_skavid(log):
    # Cave 6 sits on the far side of the gold-bar gate, and the trip is one leg so the crossing state never has to survive a decide() round trip.
    _c17 = watchtower_area(game.tile()) != 'skavidCaves'
    if _c17:
        _w18 = yield from cross_east_gate(log)
        _c17 = not (_w18)
    if _c17:
        return False
    _w19 = yield from reach_skavid(6, log)
    if not (_w19):
        return False
    # He says one of 4 phrases at random, so a wrong guess costs only a retry.
    for attempt in range(5):
        yield from talk_choosing_by(WT_NPC.MAD_SKAVID, MAD_SKAVID_RULES, ["But I've lost it!"], log)
        if held_id(WT_ITEM.CRYSTAL2.id) > 0:
            _w21 = yield from leave_cave(log)
            _c20 = (_w21)
            if not (_c20):
                return _c20
            _result22 = yield from leave_east_gate(log)
            return _result22
        yield from execution.delay_ticks(2)
    # Why: the region beyond the east gate overlaps the battlement side, so decide() can't tell them apart and would aim the escape at a battlement it has no path to; leave under our own steam even on failure.
    log('the mad skavid did not hand over a crystal in five attempts')
    yield from leave_cave(log)
    yield from leave_east_gate(log)
    return False

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/hunter.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.fremenniktrials.areas import FT_ID, SIGLI
from rs2004.quests.defs.fremenniktrials.supplies import combat_kit, held_id
from rs2004.quests.defs.trollstronghold.combat import attackable, fight
from rs2004.quests.engine.types import has_flag
from rs2004.traversal import traversal

__all__ = ['hunter_step', 'narrow', 'around', 'middle']

HERE = 'the draugen is here'
GUIDE = 'the talisman guides you '
# Why: the two-word bearings first, since 'north' is a part of 'north-west'.
BEARINGS = ['north-west', 'south-west', 'north-east', 'south-east', 'north', 'south', 'east', 'west']
DIRECTION = Record({
    'north': Record({'dx': 0, 'dz': 1}),
    'north-east': Record({'dx': 1, 'dz': 1}),
    'east': Record({'dx': 1, 'dz': 0}),
    'south-east': Record({'dx': 1, 'dz': -1}),
    'south': Record({'dx': 0, 'dz': -1}),
    'south-west': Record({'dx': -1, 'dz': -1}),
    'west': Record({'dx': -1, 'dz': 0}),
    'north-west': Record({'dx': -1, 'dz': 1}),
})
LOCATES = 20
# Why: `draugen_locate` compares the 2 coordinates axis by axis, so each bearing is the sign of dx and the sign of dz, 2 independent bisections.
# Why: `spawn_draugen_butterfly` rolls (2688,3572), (2720,3616), (2656,3616) or (2720,3680), each scattered up to 20 tiles by `map_findsquare`, and this box is their union.
# Why: `viking_draugen_safe` wanders off its anchor across the 1000 ticks it lives, so the box covers the province around the 4 spawn squares.
ANCHORS = Record({'xlo': 2600, 'xhi': 2760, 'zlo': 3540, 'zhi': 3720})
SETTLED = 2
# Why: the Draugen wanders, so a box that closed on where it was contradicts itself; reopening around you keeps the evidence and reopening wide finds it after a long drift.
LOCAL = 12


def hunter_step(snap):
    """Sigli's trial: track the invisible Draugen with his talisman, then kill it."""
    if has_flag(snap.progress, 'hunter-done'):
        return None
    if held_id(snap, FT_ID.TALISMAN_CHARGED) > 0:
        return Record({'kind': 'talk', 'stop': SIGLI([])})
    # Why: dressing before the first walk north costs 1 bank trip; dressing after Sigli hands the talisman over costs 2.
    kit = combat_kit(snap)
    if kit:
        return kit
    if not has_flag(snap.progress, 'hunter-started') or held_id(snap, FT_ID.TALISMAN) == 0:
        # Sigli replaces a missing talisman.
        return Record({'kind': 'talk', 'stop': SIGLI(["What's a Draugen?", 'Yes'])})
    return Record({'kind': 'custom', 'name': 'track and kill the Draugen', 'run': hunt})


def last_guide(mark):
    dir = None
    for line in game_messages.since(mark):
        text = line.text.lower()
        at = text.find(GUIDE)
        if at < 0:
            continue
        said = text[at + len(GUIDE):]
        for bearing in BEARINGS:
            if said.startswith(bearing):
                dir = bearing
                break
    return dir


def locate():
    talisman = ([i for i in inventory.items() if i.id == FT_ID.TALISMAN] or [None])[0]
    if not talisman:
        return 'lost'
    mark = game_messages.mark()
    if not (talisman.interact('Locate')):
        return 'lost'
    _w1 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, HERE) or last_guide(mark) is not None, 6000)
    if not (_w1):
        return 'lost'
    if game_messages.saw_since(mark, HERE):
        return 'here'
    _v2 = last_guide(mark)
    return (_v2 if _v2 is not None else 'lost')


def narrow(box, at, dir):
    """Cut the search box down to the side of the character the bearing points to, on each axis; null once the halves cross."""
    sign = DIRECTION.get(dir)
    if not sign:
        return box
    xlo = box.xlo
    xhi = box.xhi
    zlo = box.zlo
    zhi = box.zhi
    if sign.dx > 0:
        xlo = max(xlo, at.x + 1)
    elif sign.dx < 0:
        xhi = min(xhi, at.x - 1)
    else:
        xlo = at.x
        xhi = at.x
    if sign.dz > 0:
        zlo = max(zlo, at.z + 1)
    elif sign.dz < 0:
        zhi = min(zhi, at.z - 1)
    else:
        zlo = at.z
        zhi = at.z
    if xlo > xhi or zlo > zhi:
        return None
    return Record({'xlo': xlo, 'xhi': xhi, 'zlo': zlo, 'zhi': zhi})


def around(at):
    """The box reopened around the character, clamped to the ground the butterfly can be on."""
    return Record({
        'xlo': max(ANCHORS.xlo, at.x - LOCAL),
        'xhi': min(ANCHORS.xhi, at.x + LOCAL),
        'zlo': max(ANCHORS.zlo, at.z - LOCAL),
        'zhi': min(ANCHORS.zhi, at.z + LOCAL),
    })


def middle(box):
    return Tile(round((box.xlo + box.xhi) / 2), round((box.zlo + box.zhi) / 2), 0)


def hunt(log):
    box = ANCHORS
    reopens = 0
    for i in range(LOCATES):
        if inventory.count_by_id(FT_ID.TALISMAN_CHARGED) > 0:
            return True
        reading = yield from locate()
        if reading == 'lost':
            return False
        if reading != 'here':
            at = game.tile()
            if not at:
                return False
            cut = narrow(box, at, reading)
            if not cut:
                _v5 = reopens
                reopens += 1
                box = (around(at) if _v5 % 2 == 0 else ANCHORS)
                continue
            aim = middle(cut)
            if aim.distance_to(at) <= SETTLED:
                _v7 = reopens
                reopens += 1
                box = (around(at) if _v7 % 2 == 0 else ANCHORS)
                continue
            box = cut
            log(f'the talisman points {reading} — aiming for ({aim.x},{aim.z})')
            arrived = yield from traversal.walk_resilient(aim, radius=2, attempts=2, timeout_ms=60000, log=log)
            # Why: half the box is sea and fenced field, so re-aiming at the same unreachable middle reads the same bearing from the same tile forever.
            if not arrived:
                _v9 = game.tile()
                box = around((_v9 if _v9 is not None else at))
            continue
        log('the Draugen has surfaced — fighting it for the talisman charge')
        won = yield from fight(Record({
            'what': 'The Draugen',
            'target': lambda: attackable('The Draugen', 12),
            'won': lambda: inventory.count_by_id(FT_ID.TALISMAN_CHARGED) > 0,
            'protect': 'melee',
            'guard': 600,
        }), log)
        return won
    return inventory.count_by_id(FT_ID.TALISMAN_CHARGED) > 0

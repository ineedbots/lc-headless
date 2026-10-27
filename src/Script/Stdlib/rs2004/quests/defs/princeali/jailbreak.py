"""Ported from rs2b0t's src/bot/api/ai/quests/defs/princeali/jailbreak.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.quests.defs.princeali.areas import BARTENDER, JOE_BEER, NED_ROPE, PA_ITEM, PA_LOC, PA_NPC, PA_TILE
from rs2004.quests.defs.princeali.journal import PRINCE_STAGE
from rs2004.quests.defs.princeali.supplies import from_bank, held_item
from rs2004.quests.defs.princeali.supplies import held
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.traversal import traversal


__all__ = ['source_beers', 'source_ropes', 'decide_jailbreak']

BEERS_NEEDED = 3
ROPES_BEFORE_TIE = 2
ROPES_AFTER_TIE = 1
KELI_BLOCK_RADIUS = 12


def stage_of(snap):
    return (snap.stage if snap.stage is not None else PRINCE_STAGE.PREP_FINISHED)


def source_beers(snap):
    if stage_of(snap) >= PRINCE_STAGE.GUARD_DRUNK or held(snap, PA_ITEM.BEER.id) >= BEERS_NEEDED:
        return None
    _v1 = from_bank(snap, PA_ITEM.BEER, BEERS_NEEDED)
    return (_v1 if _v1 is not None else Record({'kind': 'talk', 'stop': BARTENDER}))


def source_ropes(snap):
    stage = stage_of(snap)
    if stage >= PRINCE_STAGE.SAVED:
        return None
    want = (ROPES_AFTER_TIE if stage >= PRINCE_STAGE.GUARD_DRUNK else ROPES_BEFORE_TIE)
    if held(snap, PA_ITEM.ROPE.id) >= want:
        return None
    _v2 = from_bank(snap, PA_ITEM.ROPE, want)
    return (_v2 if _v2 is not None else Record({'kind': 'talk', 'stop': NED_ROPE}))


def missing_kit(snap):
    absent = []
    if held(snap, PA_ITEM.PRINCE_KEY.id) == 0:
        absent.append(PA_ITEM.PRINCE_KEY.name)
    if held(snap, PA_ITEM.BLOND_WIG.id) == 0:
        absent.append('blond Wig')
    if held(snap, PA_ITEM.PINK_SKIRT.id) == 0:
        absent.append(PA_ITEM.PINK_SKIRT.name)
    if held(snap, PA_ITEM.PASTE.id) == 0:
        absent.append(PA_ITEM.PASTE.name)
    if held(snap, PA_ITEM.ROPE.id) == 0:
        absent.append(PA_ITEM.ROPE.name)
    return (Record({'kind': 'wait', 'reason': f"the break-in needs {', '.join(absent)}"}) if len(absent) > 0 else None)


def decide_jailbreak(snap):
    if stage_of(snap) == PRINCE_STAGE.PREP_FINISHED:
        _v3 = source_beers(snap)
        return (_v3 if _v3 is not None else Record({'kind': 'talk', 'stop': JOE_BEER}))
    _v4 = missing_kit(snap)
    return ((_v4 if _v4 is not None else Record({'kind': 'custom', 'name': 'tie Lady Keli, unlock the cell and free the prince', 'run': break_out})))


def tie_keli(log):
    keli = npcs.query().name(PA_NPC.KELI).within(KELI_BLOCK_RADIUS).nearest()
    if not keli:
        return True
    rope = held_item(PA_ITEM.ROPE.id)
    if not rope:
        log('tieKeli: Lady Keli is back and there is no rope left to tie her with')
        return False
    _w5 = yield from traversal.walk_resilient(keli.tile(), radius=2, attempts=3, timeout_ms=60000, log=log)
    if not (_w5):
        return False
    target = npcs.query().name(PA_NPC.KELI).within(6).nearest()
    if not target or not (rope.use_on(target)):
        return False

    def gone():
        return npcs.query().name(PA_NPC.KELI).within(KELI_BLOCK_RADIUS).nearest() is None

    _result6 = yield from drive_until(gone, [], log, 12000)
    return _result6


def unlock_cell(log):
    def in_cell():
        here = game.tile()
        return here is not None and here.z <= PA_TILE.CELL.z and abs(here.x - PA_TILE.CELL.x) <= 1

    if in_cell():
        return True
    _w7 = yield from traversal.walk_resilient(PA_TILE.DOOR_STAND, radius=0, attempts=4, timeout_ms=90000, log=log)
    if not (_w7):
        return False
    yield from settle_scene()
    key = held_item(PA_ITEM.PRINCE_KEY.id)
    door = locs.query().name(PA_LOC.PRISON_DOOR).within(4).nearest()
    if not key or not door:
        log('unlockCell: no key, or no Prison Door within four tiles of the north stand')
        return False
    if not (key.use_on(door)):
        return False
    _result8 = yield from execution.delay_until(in_cell, 6000)
    return _result8


def break_out(log):
    _w9 = yield from tie_keli(log)
    if not (_w9):
        return False
    _w10 = yield from unlock_cell(log)
    if not (_w10):
        return False
    yield from settle_scene()

    def handed_over():
        return held_item(PA_ITEM.BLOND_WIG.id) is None

    _w11 = yield from talk_strict(PA_NPC.PRINCE, [], log)
    if not (_w11):
        log('breakOut: could not open a dialogue with Prince Ali')
    _result12 = yield from drive_until(handed_over, [], log, 20000)
    return _result12

"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/phoenix.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.heroquest.areas import ALFONSE, CHARLIE, HERO_ID, HERO_NAMED, HERO_NPC, HERO_SHOP, HERO_TILE, STRAVEN_ARMBAND, STRAVEN_TASK, in_side_room
from rs2004.quests.defs.heroquest.doors import cross_side_door_in, enter_kitchen, push_panel, return_to_street
from rs2004.quests.defs.heroquest.journal import HERO_STAGE
from rs2004.quests.defs.heroquest.shops import kit_owned, kit_step, priced
from rs2004.quests.defs.heroquest.state import held_id
from rs2004.quests.defs.shieldofarrav.hideout import enter_hideout, talk_in_hideout
from rs2004.quests.exec.legs import talk_and_close, talk_until
from rs2004.traversal import traversal

__all__ = ['snipe_kit_step', 'snipe_kit_owned', 'talk_to_straven', 'talk_to_alfonse', 'talk_to_charlie', 'reach_arrow_slit', 'snipe_grip', 'hand_in_candlestick', 'phoenix_armband_step']

# Why: the side room is sealed from the mansion by a `snipable_wall`, which carries blockrange=no, so Grip is shootable through it and unreachable by anything else. This branch needs a bow.
SNIPE_KIT = [
    Record({'id': HERO_ID.OAK_LONGBOW, 'name': HERO_NAMED.OAK_LONGBOW, 'qty': 1, 'sources': [priced(HERO_SHOP.LOWE, 1000)]}),
    Record({'id': HERO_ID.STEEL_ARROW, 'name': HERO_NAMED.STEEL_ARROW, 'qty': 150, 'sources': [priced(HERO_SHOP.LOWE, 15000)]}),
]
SNIPE_MS = 180000
SNIPE_RANGE = 9
GROUND_RANGE = 12


def snipe_kit_step(snap):
    """The bow and the arrows: bought, withdrawn, then worn."""
    return kit_step(snap, SNIPE_KIT)


def snipe_kit_owned(snap):
    return kit_owned(snap, SNIPE_KIT)


def talk_to_straven(log):
    return talk_in_hideout(STRAVEN_TASK, STRAVEN_TASK.prefer, log)


def talk_to_alfonse(log):
    return talk_and_close(ALFONSE, ALFONSE.prefer, log)


def talk_to_charlie(log):
    """Charlie is behind the kitchen door, which only opens once Alfonse has heard the password."""
    # Why: the kitchen is a sealed pocket in the baked graph, so walking at Charlie from the restaurant reads `unreachable`; the module crosses the door itself.
    _w3 = yield from enter_kitchen(log)
    if not (_w3):
        return False
    _result4 = yield from talk_and_close(CHARLIE, CHARLIE.prefer, log)
    return _result4


def grip():
    return npcs.query().where(lambda n: n.id == HERO_NPC.GRIP).nearest()


def keyring_on_floor():
    return ground_items.query().where(lambda g: g.id == HERO_ID.GRIP_KEYS).within(GROUND_RANGE).nearest() is not None


# Why: Grip's spawn is 6 tiles from the slit, in bow range and behind 3 walls, so the server drops every attack there. The slit's own row is the only line, and the cabinet walks him onto it.
def grip_on_the_row():
    target = grip()
    here = game.tile()
    tile = (target.tile() if target is not None else None)
    if not target or not tile or not here or tile.level != here.level:
        return None
    if tile.z != HERO_TILE.ARROW_SLIT.z or here.z != HERO_TILE.ARROW_SLIT.z:
        return None
    return (target if abs(tile.x - here.x) <= SNIPE_RANGE else None)


def reach_arrow_slit(log):
    """Kitchen, secret panel, garden, yard, side door, arrow slit."""
    if not in_side_room(game.tile()):
        _w5 = yield from push_panel(log)
        if not (_w5):
            return False
        _w6 = yield from cross_side_door_in(log)
        if not (_w6):
            return False
    _result7 = yield from traversal.walk_resilient(HERO_TILE.ARROW_SLIT, radius=0, attempts=3, timeout_ms=30000, log=log)
    return _result7


# Why: Grip only crosses onto the slit's row while the rival is opening his drinks cabinet, and every route to him is a wall, so this loop waits.
def snipe_grip(log):
    """Shoot Grip through the arrow slit whenever the rival's lure puts him in range."""
    _w8 = yield from reach_arrow_slit(log)
    if not (_w8):
        return False
    deadline = _core.step_time() + SNIPE_MS
    attacking = -1
    swings = 0
    waited = False
    while _core.step_time() < deadline:
        if event_signal.pending():
            log('snipe: yielding to a random event')
            return False
        # Why: the keyring is `obj_addall`ed on death, the one thing this side of the wall can see that proves the kill landed.
        if keyring_on_floor():
            log(f'Grip is down after {swings} shots')
            return True
        yield from sustain.run()
        target = grip_on_the_row()
        if not target:
            if not waited:
                log('waiting for the rival to walk Grip onto the arrow slit row')
                waited = True
            attacking = -1
            yield from execution.delay_ticks(2)
            continue
        if target.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if target.interact('Attack'):
            if swings == 0:
                log('Grip is on the row — shooting through the arrow slit')
            attacking = target.index
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'Grip outlived {SNIPE_MS / 1000}s at the arrow slit ({swings} shots)')
    return False


def hand_in_candlestick(log):
    """Straven is underground in the Varrock hideout, so the cellar ladder comes before the conversation."""
    _w9 = yield from return_to_street(log)
    if not (_w9):
        return False
    _w10 = yield from enter_hideout(log)
    if not (_w10):
        return False
    _result11 = yield from talk_until(STRAVEN_ARMBAND, STRAVEN_ARMBAND.prefer, lambda: inventory.count_by_id(HERO_ID.ARMBAND) > 0, log, 60000)
    return _result11


def phoenix_armband_step(snap, stage):
    """The Phoenix half of the armband, from Straven's task to his reward."""
    if stage == HERO_STAGE.STARTED:
        return Record({'kind': 'custom', 'name': 'ask Straven about the master thief armband', 'run': talk_to_straven})
    elif stage == HERO_STAGE.PHOENIX_SPOKEN:
        # Why: the bow is bought in Varrock, where Straven already stands; after the crossing it costs a return ferry and a walk across 2 kingdoms.
        kit = (None if snipe_kit_owned(snap) else snipe_kit_step(snap))
        if kit:
            return kit
        return Record({'kind': 'custom', 'name': 'give Alfonse the password', 'run': talk_to_alfonse})
    elif stage == HERO_STAGE.PHOENIX_ALFONSE:
        return Record({'kind': 'custom', 'name': 'ask Charlie about the secret door', 'run': talk_to_charlie})
    elif stage == HERO_STAGE.PHOENIX_CHARLIE:
        kit = snipe_kit_step(snap)
        if kit:
            return kit
        return Record({
            'kind': 'custom',
            'cooperative': True,
            'name': 'shoot Grip through the arrow slit',
            'run': snipe_grip,
        })
    elif stage == HERO_STAGE.PHOENIX_KILLED_GRIP:
        if held_id(snap, HERO_ID.CANDLESTICK) == 0:
            return Record({'kind': 'wait', 'cooperative': True, 'reason': 'waiting on the rival to hand over a candlestick'})
        return Record({'kind': 'custom', 'name': 'give Straven the candlestick', 'run': hand_in_candlestick})
    else:
        return None

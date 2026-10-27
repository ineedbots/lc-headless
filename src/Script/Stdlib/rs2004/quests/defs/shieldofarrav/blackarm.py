"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/blackarm.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.exec.prompts import prompt_loc, settle_scene, use_on_loc
from rs2004.quests.defs.shieldofarrav.areas import KATRINE_HANDIN, KATRINE_JOIN, SOA_ID, SOA_LOC, SOA_TILE, TRAMP, in_store_ground, in_weapon_store
from rs2004.quests.defs.shieldofarrav.hideout import climb, enter_black_arm_upper, leave_black_arm_upper, leave_weapon_store, open_container, walk_and_talk
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.defs.shieldofarrav.state import modal_said
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import modals
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.exec.legs import climb, open_container, walk_and_talk
from rs2004.traversal import traversal

__all__ = ['raid_weapon_store', 'take_black_arm_half', 'blackarm_step']

WEAPONSMASTER_NPC = 643
KILL_MS = 90000
MASTER_BLOCK = 10
# Why: the cupboard's lines land as a main modal from `~objbox` / `~mesbox`; the door's "You unlock" is a plain mes and reaches the chat.

CUPBOARD_BARE = 'the cupboard is bare'

UNLOCKED = 'you unlock the door'


def weaponsmaster():
    return npcs.query().where(lambda n: n.id == WEAPONSMASTER_NPC).nearest()


def unlock_store(log):
    """Unlock the store with the key use-on; plain Open always reports it locked."""
    if in_weapon_store(game.tile()):
        return True
    mark = game_messages.mark()

    def inside():
        return in_store_ground(game.tile())

    if inside():
        return True
    _w1 = yield from use_on_loc(SOA_ID.STORE_KEY, Record({'name': 'Door', 'near': SOA_TILE.STORE_DOOR, 'within': 4, 'id': SOA_LOC.STORE_DOOR}), [], lambda: inside() or game_messages.saw_since(mark, UNLOCKED), log)
    if not (_w1):
        log(f"store door refused the key: {' · '.join([m.text for m in game_messages.since(mark)])}")
        return False
    yield from settle_scene()
    return inside()


def clear_weaponsmaster(log):
    """Not aggressive, so nothing happens until we attack; his respawn is 700 ticks, which covers both takes."""
    target = weaponsmaster()
    if not target or target.distance() > MASTER_BLOCK:
        return True
    game.set_combat_style('strength')
    if not (target.interact('Attack')):
        return False
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline:
        yield from sustain.run()
        if event_signal.pending():
            return False
        live = weaponsmaster()
        if not live or live.distance() > MASTER_BLOCK:
            log('the Weaponsmaster is down')
            return True
        yield from execution.delay_ticks(1)
    log(f'the Weaponsmaster outlived {KILL_MS / 1000}s of combat')
    return False


def take_crossbow(spawn, log):
    before = inventory.count_by_id(SOA_ID.CROSSBOW)
    # Why: the fight walks you off the take tile, so every take re-walks to its own spawn first.
    _w2 = yield from traversal.walk_resilient(spawn, radius=1, attempts=3, timeout_ms=30000, log=log)
    if not (_w2):
        return False
    drop = ground_items.query().where(lambda g: g.id == SOA_ID.CROSSBOW).within(3).nearest()
    if not drop:
        log(f'no crossbow on the floor at ({spawn.x},{spawn.z})')
        return False
    if not (drop.interact('Take')):
        return False
    yield from execution.delay_until(lambda: inventory.count_by_id(SOA_ID.CROSSBOW) > before, 6000)
    return inventory.count_by_id(SOA_ID.CROSSBOW) > before


def raid_weapon_store(log):
    if inventory.count_by_id(SOA_ID.CROSSBOW) >= 2:
        _result3 = yield from leave_weapon_store(log)
        return _result3
    if not in_weapon_store(game.tile()):
        _w4 = yield from unlock_store(log)
        if not (_w4):
            return False
        _w5 = yield from climb(SOA_LOC.STORE_LADDER, 'Climb-up', SOA_TILE.STORE_LADDER, SOA_TILE.STORE_LADDER_TOP, log)
        if not (_w5):
            return False
    _w6 = yield from clear_weaponsmaster(log)
    if not (_w6):
        return False
    for spawn in [SOA_TILE.CROSSBOW_WEST, SOA_TILE.CROSSBOW_EAST]:
        if inventory.count_by_id(SOA_ID.CROSSBOW) >= 2:
            break
        _w7 = yield from take_crossbow(spawn, log)
        if not (_w7):
            # Why: one spawn may still be on its 100-tick respawn, so this is a retry.
            log(f'crossbow at ({spawn.x},{spawn.z}) not taken this pass')
        yield from clear_weaponsmaster(log)
    if inventory.count_by_id(SOA_ID.CROSSBOW) < 2:
        return False
    _result8 = yield from leave_weapon_store(log)
    return _result8


def take_black_arm_half(log):
    if inventory.count_by_id(SOA_ID.SHIELD_BLACKARM) > 0:
        yield from leave_black_arm_upper(log)
        return True
    _w9 = yield from enter_black_arm_upper(log)
    if not (_w9):
        log('could not get through the gang door and up the stairs to the cupboard')
        return False
    # Why: the cupboard renders as 2 locs; on the open one Search is op2 and Shut is op1.
    _w10 = yield from open_container('Cupboard', SOA_LOC.CUPBOARD_SHUT, SOA_LOC.CUPBOARD_OPEN, SOA_TILE.CUPBOARD_STAND, log)
    if not (_w10):
        yield from leave_black_arm_upper(log)
        return False
    yield from prompt_loc(Record({
        'name': 'Cupboard',
        'op': 'Search',
        'near': SOA_TILE.CUPBOARD_STAND,
        'id': SOA_LOC.CUPBOARD_OPEN,
        'within': 6,
        'expect': lambda: inventory.count_by_id(SOA_ID.SHIELD_BLACKARM) > 0 or modal_said(CUPBOARD_BARE),
    }), log)
    bare = modal_said(CUPBOARD_BARE)
    yield from modals.close()
    if inventory.count_by_id(SOA_ID.SHIELD_BLACKARM) == 0:
        log(('the cupboard is bare — a half is already held or banked, or the quest is complete' if bare else 'the cupboard search landed nothing'))
        yield from leave_black_arm_upper(log)
        return False
    # Why: the half in the pack is the work; the next pass's early branch retries a failed climb down.
    _w11 = yield from leave_black_arm_upper(log)
    if not (_w11):
        log('half taken, but the climb down did not land — retrying next pass')
    return True


# Why: every conversation goes through Reach; the shared `talk` step's `gotoNpc` approaches on a leash and its crossHops calls a stand 2 tiles off "arrived", which makes the Katrine hand-in flaky.
def say(stop, name):
    return Record({'kind': 'custom', 'name': name, 'run': lambda log: walk_and_talk(stop, stop.prefer, log)})


def blackarm_step(snap):
    _v12 = (snap.progress.stage if snap.progress is not None else None)
    _v13 = (_v12 if _v12 is not None else snap.stage)
    stage = (_v13 if _v13 is not None else SOA_STAGE.NOT_STARTED)
    if stage == SOA_STAGE.NOT_STARTED:
        return say(TRAMP, 'ask the Tramp about the alley')
    elif stage == SOA_STAGE.TRAMP_TOLD:
        return say(KATRINE_JOIN, 'ask Katrine to join the Black Arm Gang')
    elif stage == SOA_STAGE.KATRINE_TASK:
        # Why: the store door is out of the nav graph, so a bot left inside after the raid has no route to Katrine and every path reads unreachable; leave first.
        if in_store_ground(snap.tile) or in_weapon_store(snap.tile):
            return Record({'kind': 'custom', 'name': 'leave the weapon store', 'run': leave_weapon_store})
        if held_id(snap, SOA_ID.CROSSBOW) >= 2:
            return say(KATRINE_HANDIN, 'hand the crossbows to Katrine')
        if held_id(snap, SOA_ID.STORE_KEY) > 0:
            return Record({'kind': 'custom', 'name': 'steal two crossbows from the weapon store', 'run': raid_weapon_store})
        # Why: a key traded over on an earlier run gets banked with everything else, and an unread bank can still hold it.
        if banked_id(snap, SOA_ID.STORE_KEY) > 0:
            return Record({'kind': 'withdraw', 'items': [{'name': 'Key', 'qty': 1, 'id': SOA_ID.STORE_KEY}]})
        # Why: the store door yields only to phoenixkey2, which only Straven issues, so a keyless bot has to be given one.
        return Record({'kind': 'wait', 'reason': 'needs a Phoenix weapon-store key from a partner'})
    elif stage == SOA_STAGE.BLACKARM_JOINED:
        if held_id(snap, SOA_ID.SHIELD_BLACKARM) > 0:
            return Record({'kind': 'wait', 'reason': 'black arm half held — the other half is not this leg'})
        # Why: `[oploc2,blackarmcupboardopen]` counts the bank, so a banked half leaves the cupboard bare for good.
        if banked_id(snap, SOA_ID.SHIELD_BLACKARM) > 0:
            return Record({
                'kind': 'withdraw',
                'items': [{'name': 'Broken shield', 'qty': 1, 'id': SOA_ID.SHIELD_BLACKARM}],
            })
        return Record({'kind': 'custom', 'name': 'search the Black Arm cupboard', 'run': take_black_arm_half})
    else:
        return Record({'kind': 'wait', 'reason': f'black arm leg has nothing for stage {stage}'})

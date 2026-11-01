"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/isafdar.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_LOC, RG_NPC, RG_TILE
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.defs.regicide.pockets import pocket_at, travel_tirannwn
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['walk_to', 'take_summons', 'brief_from_lathas', 'meet_scouts', 'ask_iorwerth', 'ask_tracker', 'follow_tracks', 'kill_soldier', 'enter_camp']

IORWERTH = 'Lord Iorwerth'
TRACKER = 'Elf Tracker'
MESSENGER = 'Kings messenger'
FIGHT_MS = 240000
RENEW_MS = 6000
BAIL_HP = 0.4
SCOUT_IDS = [1186, 1187, 1188]


def walk_to(dest, radius, stage, log):
    """Walk anywhere in Tirannwn, crossing whatever seals the target's pocket off."""
    here = game.tile()
    if here and here.level == dest.level and dest.distance_to(here) <= radius:
        return True
    _result1 = yield from travel_tirannwn(dest, radius, stage, log)
    return _result1


def talk_at(name, near, stage, prefer, log):
    _w2 = yield from walk_to(near, 3, stage, log)
    if not (_w2):
        return False
    yield from settle_scene()
    _w3 = yield from reach.npc_dialog(name, near, log=log)
    if (_w3) != 'done':
        log(f'no dialogue with {name} near ({near.x},{near.z})')
        return False
    _result4 = yield from talk_strict(name, prefer, log)
    return _result4


def find_messenger():
    return npcs.query().where(lambda npc: npc.id == RG_NPC.MESSENGER).within(14).nearest()


# Why: `start_king_messenger_timer` is armed at login and fires 400-1200 ticks later, so the messenger comes to you wherever you stand and there's nowhere to walk to. His `ai_opplayer2` opens the conversation and hands over the scroll before you click anything.
# Why: `start_king_messenger_timer` runs only at login, and only with Underground Pass complete, so a queue that finished the pass in this session waits for nobody. rs2b0t's harness relogs between the quests; a queue has to log in again itself. This departs from rs2b0t.
messenger = Record({'armed': False})


def take_summons(log):
    """Wait for the King's messenger and take his scroll."""
    if held_id(RG_ITEM.SUMMONS.id) > 0:
        return True
    if find_messenger() is None and not chat_dialog.is_open() and not chat_dialog.can_continue():
        if not messenger.armed:
            messenger.armed = True
            log("logging in again, which is what sends the King's messenger")
            _core.relog(0)
            yield from execution.delay_ticks(1)
            return True
        log("waiting for the King's messenger")
        _w5 = yield from execution.delay_until(lambda: find_messenger() is not None or chat_dialog.is_open() or chat_dialog.can_continue(), 180000)
        if not (_w5):
            return False
    _w6 = yield from drive_until(lambda: held_id(RG_ITEM.SUMMONS.id) > 0, [], log, 30000)
    if _w6:
        return True
    # Why: he only opens the dialogue himself once, so after that the scroll is asked for by hand.
    _result7 = yield from talk_strict(MESSENGER, [], log)
    return _result7


def brief_from_lathas(log):
    """King Lathas, upstairs in Ardougne castle, his `regicide_received_message` branch has no choices."""
    _w8 = yield from traversal.walk_resilient(RG_TILE.LATHAS, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w8):
        return False
    yield from settle_scene()
    _result9 = yield from talk_strict('King Lathas', [], log)
    return _result9


# Why: the scout ambush is a `[timer,spawn_idris]` armed by walking into mapsquare 35_49, 35_50 or 36_50, and normal timers only run under `canAccess()`, so this step keeps the quest journal shut while it waits. It must not walk away either, since `spawn_evil_elves` delays whenever you're more than 1 tile from Idris.
def meet_scouts(log):
    """Stand still in the forest until the elf scouts stage their ambush, then hear them out."""

    def elf_near():
        return npcs.query().where(lambda npc: (npc.id in SCOUT_IDS)).within(8).nearest() is not None

    if not chat_dialog.is_open() and not chat_dialog.can_continue() and not elf_near():
        log('waiting in the forest for the elf scouts')
        _w10 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or elf_near(), 90000)
        if not (_w10):
            return False
    # Why: the ambush is one scripted chain: Idris hails, is shot, and the pair who shot him speak, with `p_delay`s between the beats that outlast a dialogue driver's idle gap. The last line queues the elves leaving, so that's the goal.
    _result11 = yield from drive_until(lambda: not elf_near() and not chat_dialog.is_open(), [], log, 120000)
    return _result11


def ask_iorwerth(stage, log):
    return talk_at(IORWERTH, RG_TILE.IORWERTH, stage, [], log)


def ask_tracker(stage, log):
    return talk_at(TRACKER, RG_TILE.TRACKER, stage, [], log)


def follow_tracks(log):
    """The tracks at the west end of the old camp; Follow moves the stage on."""
    _w12 = yield from walk_to(RG_TILE.FOOTPRINTS, 2, RG_STAGE.SHOWN_PENDANT, log)
    if not (_w12):
        return False
    yield from settle_scene()
    tracks = locs.query().where(lambda loc: loc.id == RG_LOC.FOOTPRINTS).action('Follow').within(10).nearest()
    if not tracks or not (tracks.interact('Follow')):
        log('no tracks at the west end of the old camp')
        return False
    yield from execution.delay_ticks(3)
    return True


def soldier_near():
    return npcs.query().where(lambda npc: npc.id == RG_NPC.OLD_CAMP_GUARD or npc.id == RG_NPC.CAMP_GUARD).action('Attack').within(14).nearest()


# Why: the soldier is level 110 with 110 hitpoints, 95 strength and a halberd, against an account this quest only asks 56 Agility of. `Sustain.run()` is not a background task: `Traversal` calls it on every walk and a step that stands still fighting never does, so the fight runs start to finish without eating.
# Why: one `Attack` click isn't enough either. A halberd out-ranges you, so the walk in and every knockback break the interaction off, and an un-renewed fight is a character being hit for free.
def fight_soldier(log):
    """Fight until the soldier is gone, eating every tick and renewing the attack whenever it lapses."""
    log("fighting one of King Tyras's men")
    deadline = _core.step_time() + FIGHT_MS
    renew_at = 0
    while _core.step_time() < deadline:
        target = soldier_near()
        if not target:
            return True
        yield from sustain.run()
        # Why: an empty pack is the one thing this step has to notice for itself: carrying on from here ends the run at a Lumbridge grave with its kit on the far side of the palisade.
        if skills.hp_fraction() < BAIL_HP and inventory.count(RG_ITEM.SHARK.name) == 0:
            log(f'breaking off the fight at {round(skills.hp_fraction() * 100)}% with no food left')
            return False
        if _core.step_time() >= renew_at:
            if not (target.interact('Attack')):
                return False
            renew_at = _core.step_time() + RENEW_MS
        yield from execution.delay_ticks(1)
    return soldier_near() is None


# Why: 2 different soldiers can carry this stage. `spawn_tyras_guard` posts the old camp's one once, latching `^regicide_seen_guard`, while the camp entrance posts a fresh `regicide_tyras_camp_guard` on every crossing attempt, so the entrance is the fallback that always works.
def kill_soldier(log):
    """Kill the soldier that stands between the tracks and Tyras's camp."""
    if soldier_near():
        _result13 = yield from fight_soldier(log)
        return _result13
    stage = RG_STAGE.SPOKEN_TRACKER2
    if pocket_at(game.tile()) != 'old-camp-west':
        _w14 = yield from walk_to(RG_TILE.OLD_CAMP_WEST, 1, stage, log)
        if not (_w14):
            return False
        yield from execution.delay_ticks(4)
        if soldier_near():
            _result15 = yield from fight_soldier(log)
            return _result15
    _w16 = yield from walk_to(RG_TILE.CAMP_ENTRANCE, 1, stage, log)
    if not (_w16):
        return False
    yield from settle_scene()
    crossing = locs.query().where(lambda loc: loc.id == 3998).action('Enter').within(8).nearest()
    if not crossing or not (crossing.interact('Enter')):
        log('no camp crossing to draw the guard out')
        return False
    _w17 = yield from drive_until(lambda: soldier_near() is not None, [], log, 15000)
    if not (_w17):
        return False
    _result18 = yield from fight_soldier(log)
    return _result18


# Why: the stage moves on the crossing itself: `_regicide_cross_over` sets `^regicide_entered_camp` as it puts you down on the far side. Walking on to the king's pavilion is 4 more crossings there and 4 back for a stage already banked.
def enter_camp(log):
    """Squeeze past the camp guard's post, which is what the journal counts as finding the camp."""
    _result19 = yield from walk_to(RG_TILE.CAMP_INSIDE, 1, RG_STAGE.DEFEATED_GUARD, log)
    return _result19


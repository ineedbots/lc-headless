"""Ported from rs2b0t's src/bot/api/ai/quests/defs/biohazard/west.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.biohazard.areas import BIO_ITEM, BIO_LOC, BIO_TILE, SICK_MOURNER_ID
from rs2004.quests.defs.biohazard.gear import held_id, wear
from rs2004.quests.defs.biohazard.travel import enter_hq, loc_by_id, walk_to
from rs2004.quests.exec.prompts import drive_choice, drive_until, settle_scene

__all__ = ['take_rotten_apples', 'poison_the_stew', 'take_doctor_gown', 'take_mourner_key', 'search_the_crate']

# Why: The third choice avoids the fake-doctor branch; all three still end at `~npc_retaliate(0)`.
MOURNER_PREFER = ["There's nothing I can do, it's fatal."]
FIGHT_GUARD = 300
EAT_AT_MISSING = 15
# Why: the key arrives from `queue,defeat_biohazard_mourner`, run after the death animation and `npc_del`, so the corpse is gone for several ticks before the pack changes.
MISSING_TO_WIN = 10


def take_rotten_apples(log):
    _w1 = yield from walk_to(BIO_TILE.ROTTEN_APPLES, 1, log)
    if not (_w1):
        return False
    yield from settle_scene()
    apples = ground_items.query().where(lambda item: item.id == BIO_ITEM.ROTTEN_APPLES.id).within(8).nearest()
    if not apples:
        log(f'no Rotten apples at ({BIO_TILE.ROTTEN_APPLES.x},{BIO_TILE.ROTTEN_APPLES.z}) — waiting for the respawn')
        yield from execution.delay_ticks(4)
        return False
    if not (apples.interact('Take')):
        return False
    _result2 = yield from execution.delay_until(lambda: held_id(BIO_ITEM.ROTTEN_APPLES.id) > 0, 8000)
    return _result2


# Why: the cauldron sits in the headquarters yard, and the only way in that skips the gown-locked building is the Climb-over fence at 2541,3331, a curated transport.
def poison_the_stew(log):
    _w3 = yield from walk_to(BIO_TILE.CAULDRON, 1, log)
    if not (_w3):
        return False
    yield from settle_scene()
    cauldron = loc_by_id(BIO_LOC.CAULDRON, None, 8)
    apples = ([item for item in inventory.items() if item.id == BIO_ITEM.ROTTEN_APPLES.id] or [None])[0]
    if not cauldron or not apples:
        log(f"no {('Rotten apples' if cauldron else 'Cauldron')} for the stew")
        return False
    if not (apples.use_on(cauldron)):
        return False
    _w4 = yield from drive_until(lambda: held_id(BIO_ITEM.ROTTEN_APPLES.id) == 0, [], log, 20000)
    if not (_w4):
        return False
    # Why: the apple dissolves 3 ticks before the stage moves, so returning on the empty slot hands the next decide a journal that still says "fetch rotten apples".
    yield from execution.delay_ticks(5)
    return True


def take_doctor_gown(log):
    """The nurse's cupboard. It hands nothing over while a gown is already banked or worn."""
    _w5 = yield from walk_to(BIO_TILE.NURSE_CUPBOARD, 1, log)
    if not (_w5):
        return False
    yield from settle_scene()
    open = loc_by_id(BIO_LOC.NURSE_CUPBOARD_OPEN, 'Search', 6)
    if open:
        if not (open.interact('Search')):
            return False
        _result6 = yield from drive_until(lambda: held_id(BIO_ITEM.DOCTOR_GOWN.id) > 0, [], log, 10000)
        return _result6
    shut = loc_by_id(BIO_LOC.NURSE_CUPBOARD_SHUT, 'Open', 6)
    if not shut or not (shut.interact('Open')):
        log("no cupboard in the nurse's hut")
        return False
    _result7 = yield from execution.delay_until(lambda: loc_by_id(BIO_LOC.NURSE_CUPBOARD_OPEN, 'Search', 6) is not None, 6000)
    return _result7


def sick_mourner():
    return npcs.query().where(lambda npc: npc.id == SICK_MOURNER_ID).where(lambda npc: not npc.targets_another_player()).within(12).nearest()


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


# Why: the key only drops for the player the mourner is aggressive toward, and `~npc_retaliate` from the doctor dialogue is what sets `%npc_aggressive_player`, so Attack alone may not claim him.
# Why: he respawns 140 ticks after dying, so the talk, the fight and the search are one step.
def fight_for_key(log):
    swings = 0
    attacking = -1
    missing = 0
    reported = -40
    game.set_auto_retaliate(True)
    for i in range(FIGHT_GUARD):
        if event_signal.pending():
            log('mourner fight: yielding to a random event')
            return False
        if held_id(BIO_ITEM.MOURNER_KEY.id) > 0:
            log(f'took the key off the mourner after {swings} attacks')
            return True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        if hungry():
            yield from sustain.run()
            continue
        npc = sick_mourner()
        if not npc:
            missing += 1
            attacking = -1
            if swings > 0 and missing >= MISSING_TO_WIN:
                log('the sick mourner is down but dropped no key — talking to the next one')
                return False
            yield from execution.delay_ticks(1)
            continue
        missing = 0
        if i - reported >= 40:
            reported = i
            log(f"mourner: hp={skills.effective('hitpoints')}/{skills.level('hitpoints')} attacks={swings}" + f' at ({npc.tile().x},{npc.tile().z})')
        if npc.index == attacking and game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        if npc.interact('Attack'):
            attacking = npc.index
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'mourner fight: gave up after {FIGHT_GUARD} ticks ({swings} attacks)')
    return False


def take_mourner_key(log):
    """Get inside, provoke the sick mourner, and take his key."""
    if held_id(BIO_ITEM.MOURNER_KEY.id) > 0:
        return True
    _w9 = yield from wear(BIO_ITEM.DOCTOR_GOWN, log)
    _c8 = not (_w9)
    if not _c8:
        _w10 = yield from enter_hq(log)
        _c8 = not (_w10)
    if _c8:
        return False
    _w11 = yield from walk_to(BIO_TILE.HQ_UPSTAIRS, 2, log)
    if not (_w11):
        return False
    yield from settle_scene()
    npc = sick_mourner()
    if not npc:
        log('no sick Mourner on the headquarters first floor')
        return False
    if not (npc.interact('Talk-to')):
        return False
    # Why: `talkStrict` would re-find "Mourner" by display name and could open a different one; the click is already sent, so this only drives the prompt it raised.
    _w12 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if _w12:
        yield from drive_choice(MOURNER_PREFER, log)
    _result13 = yield from fight_for_key(log)
    return _result13


def search_the_crate(log):
    """Through the locked gate and into the crate Elena's distillator is stored in."""
    _w15 = yield from wear(BIO_ITEM.DOCTOR_GOWN, log)
    _c14 = not (_w15)
    if not _c14:
        _w16 = yield from enter_hq(log)
        _c14 = not (_w16)
    if _c14:
        return False
    if held_id(BIO_ITEM.MOURNER_KEY.id) == 0:
        log('no Key in the pack — the headquarters gate refuses an empty-handed Open')
        return False
    _w17 = yield from walk_to(BIO_TILE.HQ_CRATE, 1, log)
    if not (_w17):
        return False
    yield from settle_scene()
    crate = loc_by_id(BIO_LOC.HQ_CRATE, 'Search', 6)
    if not crate:
        log(f'no Crate offering Search at ({BIO_TILE.HQ_CRATE.x},{BIO_TILE.HQ_CRATE.z},1)')
        return False
    if not (crate.interact('Search')):
        return False
    _result18 = yield from drive_until(lambda: held_id(BIO_ITEM.DISTILLATOR.id) > 0, [], log, 15000)
    return _result18

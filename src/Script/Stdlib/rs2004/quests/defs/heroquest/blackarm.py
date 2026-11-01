"""Ported from rs2b0t's src/bot/api/ai/quests/defs/heroquest/blackarm.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog, modals
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.defs.heroquest.areas import GRIP, HERO_ID, HERO_LOC, HERO_NAMED, HERO_NPC, HERO_SAY, HERO_SHOP, HERO_TILE, KATRINE_ARMBAND, KATRINE_TASK, TROBERT, in_mansion, in_treasure_room
from rs2004.quests.defs.heroquest.doors import cross_treasure_door_in, cross_treasure_door_out, enter_brimhaven_hq, enter_mansion, return_to_street
from rs2004.quests.defs.heroquest.journal import HERO_STAGE
from rs2004.quests.defs.heroquest.partner import hero_handoff_state, should_fetch_key
from rs2004.quests.defs.heroquest.shops import kit_owned, kit_step, priced
from rs2004.quests.defs.heroquest.state import held_id
from rs2004.quests.exec.legs import open_container, talk_and_close, talk_until
from rs2004.quests.exec.prompts import drive_choice, prompt_loc
from rs2004.traversal import traversal

__all__ = ['disguise_step', 'disguise_owned', 'talk_to_trobert', 'ask_grip_for_key', 'lure_grip_and_take_keyring', 'loot_candlesticks', 'hand_in_candlestick', 'blackarm_armband_step', 'blackarm_sealed']

# Why: Garv checks all 3 worn and refuses silently otherwise, and Louie leads because Valaine restocks every 20 000 ticks to his 1 200.
DISGUISE = [
    Record({'id': HERO_ID.BLACK_PLATEBODY, 'name': HERO_NAMED.BLACK_PLATEBODY, 'qty': 1, 'sources': [priced(HERO_SHOP.HORVIK, 4500)]}),
    Record({
    'id': HERO_ID.BLACK_PLATELEGS,
    'name': HERO_NAMED.BLACK_PLATELEGS,
    'qty': 1,
    'sources': [priced(HERO_SHOP.LOUIE, 3000), priced(HERO_SHOP.VALAINE, 30000)],
}),
    Record({'id': HERO_ID.BLACK_FULL_HELM, 'name': HERO_NAMED.BLACK_FULL_HELM, 'qty': 1, 'sources': [priced(HERO_SHOP.VALAINE, 2000)]}),
]
LURE_MS = 150000
LURE_HOLD_MS = 12000
DIALOG_MS = 6000
GROUND_RANGE = 12


def disguise_step(snap):
    """The disguise: bought, withdrawn, then worn."""
    return kit_step(snap, DISGUISE)


def disguise_owned(snap):
    """True once all 3 pieces are somewhere the bot can reach them."""
    return kit_owned(snap, DISGUISE)


def talk_to_trobert(log):
    _w5 = yield from enter_brimhaven_hq(log)
    if not (_w5):
        return False
    _result6 = yield from talk_until(TROBERT, TROBERT.prefer, lambda: inventory.count_by_id(HERO_ID.ID_PAPERS) > 0, log, 60000)
    return _result6


# Why: the first talk takes the papers and only then opens the option tree, so one leg covers the introduction and the key, and Grip re-issues the spare whenever `~obj_gettotal` reads 0.
def ask_grip_for_key(log):
    """Report for duty, then ask for the job that provides the spare key."""
    if inventory.count_by_id(HERO_ID.MISC_KEY) > 0:
        return True
    _w7 = yield from enter_mansion(log)
    if not (_w7):
        return False
    _result8 = yield from talk_until(GRIP, GRIP.prefer, lambda: inventory.count_by_id(HERO_ID.MISC_KEY) > 0, log, 90000)
    return _result8


def keyring_on_floor():
    return ground_items.query().where(lambda g: g.id == HERO_ID.GRIP_KEYS).within(GROUND_RANGE).nearest()


# Why: the rival's shot needs Grip on the arrow slit's own row, so this is the same test the snipe uses; anywhere else on the way is no help.
def grip_on_the_row():
    grip = npcs.query().where(lambda n: n.id == HERO_NPC.GRIP).nearest()
    tile = (grip.tile() if grip is not None else None)
    return not not tile and tile.z == HERO_TILE.GRIP_LURE.z and abs(tile.x - HERO_TILE.GRIP_LURE.x) <= 3


def take_keyring(log):
    drop = keyring_on_floor()
    if not drop:
        return False
    before = inventory.count_by_id(HERO_ID.GRIP_KEYS)
    if not (drop.interact('Take')):
        return False
    took = yield from execution.delay_until(lambda: inventory.count_by_id(HERO_ID.GRIP_KEYS) > before, 8000)
    if took:
        log("took Grip's keyring off the floor")
    return took


# Why: `snipable_wall` (blockrange=no) seals the side room, so the rival shoots Grip through the arrow slit and reaches him only while the drinks cabinet has walked him onto that row.
# Why: `summon_grip` walks him 6 tiles and `npc_setmode(null)` turns him round 6 ticks later, so the loop re-runs the cabinet's Search every pass.
def lure_grip_and_take_keyring(log):
    """Walk Grip to the arrow slit over and over until the rival drops him, then take the keyring."""
    if inventory.count_by_id(HERO_ID.GRIP_KEYS) > 0:
        return True
    _w9 = yield from enter_mansion(log)
    if not (_w9):
        return False
    _w10 = yield from take_keyring(log)
    if _w10:
        return True
    _w11 = yield from traversal.walk_resilient(HERO_TILE.CABINET_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w11):
        return False
    deadline = _core.step_time() + LURE_MS
    lures = 0
    reported = False
    while _core.step_time() < deadline and keyring_on_floor() is None:
        if event_signal.pending():
            log('lure: yielding to a random event')
            return False
        # Why: a Grip already on the row needs no second summon, and re-clicking spends every tick on a dialogue the rival's shot needs.
        if grip_on_the_row():
            yield from execution.delay_until(lambda: keyring_on_floor() is not None or not grip_on_the_row(), LURE_HOLD_MS)
            continue
        # Why: the cabinet is 2 locs, `gripcbshut` becomes `gripcbopen` for 500 ticks, and both run `summon_grip`, one under Open and one under Search.
        cupboard = locs.query().where(lambda l: l.id == HERO_LOC.CABINET_OPEN or l.id == HERO_LOC.CABINET_SHUT).within(8).nearest()
        if not cupboard:
            log(f'lure: no drinks cabinet within eight tiles of ({HERO_TILE.CABINET_STAND.x},{HERO_TILE.CABINET_STAND.z})')
            return False
        op = ('Search' if cupboard.id == HERO_LOC.CABINET_OPEN else 'Open')
        clicked = cupboard.interact(op)
        # Why: `summon_grip` does nothing unless a pirate guard is within 4 tiles, with no dialogue, walk or refusal, so the guard is worth naming when nothing happens.
        guard = npcs.query().where(lambda n: n.id == HERO_NPC.PIRATE_GUARD).within(4).nearest()
        asked = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue() or grip_on_the_row(), DIALOG_MS)
        if chat_dialog.is_open() or chat_dialog.can_continue():
            yield from drive_choice([HERO_SAY.CABINET_PEEK], log)
        on_row = yield from execution.delay_until(lambda: grip_on_the_row() or keyring_on_floor() is not None, LURE_HOLD_MS)
        lures += 1
        if not reported or on_row:
            grip = npcs.query().where(lambda n: n.id == HERO_NPC.GRIP).nearest()
            at = grip.tile() if grip is not None else None
            where = f'{at.x},{at.z}' if at else 'not in scene'
            near = 'near' if guard else 'MISSING'
            log(f'lure {lures}: {op}={clicked} asked={asked} onRow={on_row} guard={near} grip={where} (row z={HERO_TILE.GRIP_LURE.z})')
            reported = True
        yield from modals.close()
    _w12 = yield from take_keyring(log)
    if _w12:
        log(f'Grip dropped his keyring after {lures} lures')
        hero_handoff_state.lure_failures = 0
        return True
    # Why: a rival that never turned up may have died holding the spare key, and Grip only issues another once this bot is empty-handed, so a run of fruitless lures re-opens the fetch.
    hero_handoff_state.lure_failures += 1
    log(f'no keyring after {lures} lures — the rival may not be at the arrow slit yet')
    return False


def loot_candlesticks(log):
    """Grip's keyring opens the treasure room, and the chest inside hands over 2 candlesticks."""
    if inventory.count_by_id(HERO_ID.CANDLESTICK) >= 2:
        _result13 = yield from cross_treasure_door_out(log)
        return _result13
    if not in_treasure_room(game.tile()):
        _w14 = yield from enter_mansion(log)
        if not (_w14):
            return False
        _w15 = yield from traversal.walk_resilient(HERO_TILE.TREASURE_DOOR, radius=2, attempts=3, timeout_ms=120000, log=log)
        if not (_w15):
            return False
        _w16 = yield from cross_treasure_door_in(log)
        if not (_w16):
            return False
    _w17 = yield from open_container('Chest', HERO_LOC.CHEST_SHUT, HERO_LOC.CHEST_OPEN, HERO_TILE.CHEST_STAND, log)
    if not (_w17):
        yield from cross_treasure_door_out(log)
        return False
    yield from prompt_loc(Record({
        'name': 'Chest',
        'op': 'Search',
        'near': HERO_TILE.CHEST_STAND,
        'id': HERO_LOC.CHEST_OPEN,
        'within': 6,
        'expect': lambda: inventory.count_by_id(HERO_ID.CANDLESTICK) > 0,
    }), log)
    yield from modals.close()
    took = inventory.count_by_id(HERO_ID.CANDLESTICK) > 0
    if not took:
        log('the chest handed over nothing — a candlestick is already held or banked')
    # Why: the take is the work; a failed exit is retried for free by the next pass's early branch.
    yield from cross_treasure_door_out(log)
    return took


def hand_in_candlestick(log):
    """Katrine stands above ground in Varrock, but the candlestick is looted inside a sealed pocket."""
    _w18 = yield from return_to_street(log)
    if not (_w18):
        return False
    _result19 = yield from talk_until(KATRINE_ARMBAND, KATRINE_ARMBAND.prefer, lambda: inventory.count_by_id(HERO_ID.ARMBAND) > 0, log, 60000)
    return _result19


def blackarm_armband_step(snap, stage):
    """The Black Arm half of the armband, from Katrine's task to her reward."""
    if stage == HERO_STAGE.STARTED:
        return Record({
            'kind': 'custom',
            'name': 'ask Katrine about the master thief rank',
            'run': lambda log: talk_and_close(KATRINE_TASK, KATRINE_TASK.prefer, log),
        })
    elif stage == HERO_STAGE.BLACKARM_SPOKEN:
        # Why: the disguise is bought in Varrock, where Katrine already stands; after the crossing it costs a return ferry and a walk across 2 kingdoms.
        piece = (None if disguise_owned(snap) else disguise_step(snap))
        if piece:
            return piece
        return Record({'kind': 'custom', 'name': 'say the password at the Brimhaven hideout', 'run': enter_brimhaven_hq})
    elif stage == HERO_STAGE.BLACKARM_HQ:
        return Record({'kind': 'custom', 'name': 'take Hartigen’s papers from Trobert', 'run': talk_to_trobert})
    elif stage == HERO_STAGE.BLACKARM_PAPERS:
        if held_id(snap, HERO_ID.ID_PAPERS) == 0:
            return Record({'kind': 'custom', 'name': 'ask Trobert for a spare set of papers', 'run': talk_to_trobert})
        dressed = disguise_step(snap)
        if dressed:
            return dressed
        return Record({'kind': 'custom', 'name': 'pass Garv as Hartigen the Black Knight', 'run': enter_mansion})
    elif stage == HERO_STAGE.BLACKARM_MANSION:
        return Record({'kind': 'custom', 'name': 'report to Grip as his new deputy', 'run': ask_grip_for_key})
    elif stage == HERO_STAGE.BLACKARM_PAPERS_GIVEN:
        if held_id(snap, HERO_ID.GRIP_KEYS) > 0:
            return Record({'kind': 'custom', 'name': 'open the treasure room and the chest', 'run': loot_candlesticks})
        # Why: Grip re-issues the spare whenever the bot holds none, so a bot that fetches after every trade swaps keys with its rival forever and never lures him onto the slit.
        if held_id(snap, HERO_ID.MISC_KEY) == 0 and should_fetch_key():
            return Record({
                'kind': 'custom',
                'name': 'ask Grip for a job, which hands over his spare key',
                'run': ask_grip_for_key,
            })
        return Record({
            'kind': 'custom',
            'name': 'lure Grip to the arrow slit for the rival',
            'run': lure_grip_and_take_keyring,
        })
    elif stage == HERO_STAGE.BLACKARM_LOOTED:
        if held_id(snap, HERO_ID.CANDLESTICK) == 0:
            return Record({'kind': 'wait', 'reason': 'the chest is looted but no candlestick is carried'})
        return Record({'kind': 'custom', 'name': 'give Katrine the candlestick', 'run': hand_in_candlestick})
    else:
        return None


def blackarm_sealed(snap):
    """Where the Black Arm bot must stand before anything but the armband can run."""
    return in_mansion(snap.tile) or in_treasure_room(snap.tile)

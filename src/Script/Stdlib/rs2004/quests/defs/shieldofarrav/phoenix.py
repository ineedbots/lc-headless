"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shieldofarrav/phoenix.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import banked_id, held_id
from rs2004.quests.exec.prompts import prompt_loc
from rs2004.quests.defs.shieldofarrav.areas import BARAEK, RELDO, SOA_ID, SOA_LOC, SOA_TILE, STRAVEN_HANDIN, STRAVEN_JOIN
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav.hideout import enter_phoenix_inner, leave_hideout, open_container, talk_in_hideout, walk_and_talk
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE
from rs2004.quests.defs.shieldofarrav.state import live_item, modal_said
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import modals
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.quests.exec.legs import open_container, walk_and_talk
from rs2004.traversal import traversal

__all__ = ['take_book', 'read_book', 'kill_jonny', 'join_phoenix_gang', 'hand_in_report', 'take_phoenix_half', 'phoenix_step']

BRIBE_GP = 20
COIN_FLOAT = 500
JONNY_NPC = 645
KILL_MS = 60000
WALK_MS = 120000
# Why: the chest lines land as a main modal from `~objbox` / `~mesbox`, so they never reach the chat.

CHEST_EMPTY = 'the chest is empty'


def take_book(log):
    """Check the bookcase and continue its line and mesbox before waiting for the book."""
    if inventory.count_by_id(SOA_ID.BOOK) > 0:
        return True
    took = yield from prompt_loc(Record({
        'name': 'Bookcase',
        'op': 'Check',
        'near': SOA_TILE.BOOKCASE,
        'id': SOA_LOC.BOOKCASE,
        'within': 6,
        'expect': lambda: inventory.count_by_id(SOA_ID.BOOK) > 0,
        'expect_ms': 15000,
    }), log)
    yield from modals.close()
    if not took and inventory.count_by_id(SOA_ID.BOOK) == 0:
        log('the quest bookcase gave up no book')
        return False
    return True


def read_book(log):
    book = live_item(SOA_ID.BOOK)
    if not book:
        log('no book in the pack to read')
        return False
    if not (book.interact('Read')):
        return False
    yield from execution.delay_ticks(3)
    yield from modals.close()
    return True


def jonny():
    return npcs.query().where(lambda n: n.id == JONNY_NPC).nearest()


def kill_jonny(log):
    """Jonny is level 2 and drops the report unconditionally; his respawn is 74 ticks, so a missed window retries."""
    if inventory.count_by_id(SOA_ID.REPORT) > 0:
        return True
    drop = ground_items.query().where(lambda g: g.id == SOA_ID.REPORT).within(12).nearest()
    if drop:
        mark = game_messages.mark()
        if not (drop.interact('Take')):
            return False
        yield from execution.delay_until(lambda: inventory.count_by_id(SOA_ID.REPORT) > 0 or game_messages.saw_since(mark, CANT_REACH), 6000)
        return inventory.count_by_id(SOA_ID.REPORT) > 0
    target = jonny()
    if not target:
        log('no Jonny the beard in the scene — walking to the Blue Moon Inn')
        _result1 = yield from traversal.walk_resilient(SOA_TILE.JONNY, radius=3, attempts=3, timeout_ms=WALK_MS, log=log)
        return _result1
    game.set_combat_style('strength')
    if not (target.interact('Attack')):
        return False
    deadline = _core.step_time() + KILL_MS
    while _core.step_time() < deadline:
        yield from sustain.run()
        if event_signal.pending():
            return False
        if not jonny():
            log('Jonny the beard died')
            # Why: the report lands as a ground drop, and taking it is the next pass's work.
            return True
        yield from execution.delay_ticks(1)
    log(f'Jonny outlived {KILL_MS / 1000}s of combat')
    return False


def join_phoenix_gang(log):
    _result2 = yield from talk_in_hideout(STRAVEN_JOIN, STRAVEN_JOIN.prefer, log)
    return _result2


def hand_in_report(log):
    """Straven takes the report by dialogue and hands back the weapon-store key; that proves the join."""
    _w3 = yield from talk_in_hideout(STRAVEN_HANDIN, [], log)
    if not (_w3):
        return False
    return inventory.count_by_id(SOA_ID.REPORT) == 0


def take_phoenix_half(log):
    if inventory.count_by_id(SOA_ID.SHIELD_PHOENIX) > 0:
        yield from leave_hideout(log)
        return True
    _w4 = yield from enter_phoenix_inner(log)
    if not (_w4):
        log('could not get through the gang door to the chest')
        return False
    # Why: the chest renders as 2 locs and only the open one carries Search.
    _w5 = yield from open_container('Chest', SOA_LOC.CHEST_SHUT, SOA_LOC.CHEST_OPEN, SOA_TILE.CHEST_STAND, log)
    if not (_w5):
        yield from leave_hideout(log)
        return False
    yield from prompt_loc(Record({
        'name': 'Chest',
        'op': 'Search',
        'near': SOA_TILE.CHEST_STAND,
        'id': SOA_LOC.CHEST_OPEN,
        'within': 6,
        'expect': lambda: inventory.count_by_id(SOA_ID.SHIELD_PHOENIX) > 0 or modal_said(CHEST_EMPTY),
    }), log)
    empty = modal_said(CHEST_EMPTY)
    yield from modals.close()
    if inventory.count_by_id(SOA_ID.SHIELD_PHOENIX) == 0:
        log(('the chest is empty — a half is already held or banked, or the quest is complete' if empty else 'the chest search landed nothing'))
        yield from leave_hideout(log)
        return False
    # Why: the half in the pack is the work; the next pass's early branch retries a failed climb out, and failing here would throw away a half you're holding.
    _w6 = yield from leave_hideout(log)
    if not (_w6):
        log('half taken, but the climb back to the surface did not land — retrying next pass')
    return True


# Why: every conversation goes through Reach; the shared `talk` step's gotoNpc approaches on a leash and calls a stand 2 tiles off "arrived".
def say(stop, name):
    return Record({'kind': 'custom', 'name': name, 'run': lambda log: walk_and_talk(stop, stop.prefer, log)})


def banked_recovery(snap):
    """The half, and the key a partner is owed, when the last bank read holds them and the pack does not."""
    out = []
    if held_id(snap, SOA_ID.SHIELD_PHOENIX) == 0 and banked_id(snap, SOA_ID.SHIELD_PHOENIX) > 0:
        out.append({'name': 'Broken shield', 'qty': 1, 'id': SOA_ID.SHIELD_PHOENIX})
    owed = len(arrav_config.partner.strip()) > 0
    if owed and held_id(snap, SOA_ID.STORE_KEY) == 0 and banked_id(snap, SOA_ID.STORE_KEY) > 0:
        out.append({'name': 'Key', 'qty': 1, 'id': SOA_ID.STORE_KEY})
    return out


def phoenix_step(snap):
    _v7 = (snap.progress.stage if snap.progress is not None else None)
    _v8 = (_v7 if _v7 is not None else snap.stage)
    stage = (_v8 if _v8 is not None else SOA_STAGE.NOT_STARTED)
    _v9 = (snap.progress.flags if snap.progress is not None else None)
    flags = (_v9 if _v9 is not None else set())
    if stage == SOA_STAGE.NOT_STARTED:
        return say(RELDO, 'ask Reldo for a quest')
    elif stage == SOA_STAGE.TOLD_OF_BOOK:
        if held_id(snap, SOA_ID.BOOK) > 0:
            return Record({'kind': 'custom', 'name': 'read The Shield of Arrav', 'run': read_book})
        # Why: 9 other Bookcase locs stand within 4 tiles, and only this one carries Check.
        return Record({'kind': 'custom', 'name': 'check the palace bookcase', 'run': take_book})
    elif stage == SOA_STAGE.READ_BOOK:
        return say(RELDO, 'ask Reldo for a quest')
    elif stage == SOA_STAGE.SENT_TO_BARAEK:
        if held_id(snap, SOA_ID.COINS) < BRIBE_GP:
            return Record({'kind': 'withdraw', 'items': [{'name': 'Coins', 'qty': COIN_FLOAT, 'id': SOA_ID.COINS}]})
        return say(BARAEK, 'bribe Baraek for the hideout')
    elif stage == SOA_STAGE.FIND_STRAVEN:
        return Record({'kind': 'custom', 'name': 'offer Straven your services', 'run': join_phoenix_gang})
    elif stage == SOA_STAGE.KILL_JONNY:
        if held_id(snap, SOA_ID.REPORT) > 0 or ('report-held' in flags):
            return Record({'kind': 'custom', 'name': 'hand the report to Straven', 'run': hand_in_report})
        return Record({'kind': 'custom', 'name': 'kill Jonny the beard for the report', 'run': kill_jonny})
    elif stage == SOA_STAGE.PHOENIX_JOINED:
        # Why: `[oploc1,phoenixopenchest]` and `~obj_gettotal` both count the bank, so a banked half or key is never re-issued and only a withdraw gets it back.
        # Why: the guard reads the pack, so a stale bank read can't make this and a deposit undo each other.
        recover = banked_recovery(snap)
        if len(recover) > 0:
            return Record({'kind': 'withdraw', 'items': recover})
        if held_id(snap, SOA_ID.SHIELD_PHOENIX) > 0:
            return Record({'kind': 'wait', 'reason': 'phoenix half held — the other half is not this leg'})
        return Record({'kind': 'custom', 'name': 'search the Phoenix hideout chest', 'run': take_phoenix_half})
    else:
        return Record({'kind': 'wait', 'reason': f'phoenix leg has nothing for stage {stage}'})

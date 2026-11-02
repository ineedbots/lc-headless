"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/scene.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog, modals
from rs2004.game import game, reader
from rs2004.items import inventory
from rs2004.quests.defs.legends.areas import legends_area
from rs2004.quests.exec.primitives import pick_preferred
from rs2004.quests.exec.prompts import clear_boxes, drive_boxes, drive_choice, drive_until, held_id, loc_near, prompt_loc, settle_scene, use_on_loc
from rs2004.quests.journal_text import normalize_journal
from rs2004.traversal import traversal

__all__ = ['offer_to', 'here', 'drive_to_end', 'modal_text', 'said_any', 'clear_boxes', 'drive_boxes', 'drive_choice', 'drive_until', 'held_id', 'loc_near', 'prompt_loc', 'settle_scene', 'use_on_loc']


# Why: Use-on does not approach the target, so move next to the NPC before sending it.
def offer_to(item_id, npc, log):
    """Offer an item to an npc, having first walked close enough for the offer to land."""
    item = ([i for i in inventory.items() if i.id == item_id] or [None])[0]
    if not item:
        log(f'nothing with id {item_id} in the pack to offer')
        return False
    _w1 = yield from traversal.walk_resilient(npc.tile(), radius=1, attempts=2, timeout_ms=30000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    return item.use_on(npc)


def here():
    """Which of the quest's areas you're standing in right now."""
    return legends_area(game.tile())


# Why: `~mesbox` and `~objbox` are modal boxes, so `GameMessages` never sees them, and half this quest's confirmations arrive that way.
# Why: both the chat and the main modal are read, as the journal and the books use the main one and the boxes use the chat one.
# Why: several conversations here end themselves without landing an item or a tile, Ungadulu collapses, Gujuo walks off, so their only goal is "the chain ran to its end".
# Why: `driveUntil` with a goal that never becomes true burns its budget after the chat has closed, and `driveDialog` guesses the last option when nothing matches.
# Why: a chain can also run to the wrong end: Gujuo greets, chats and says goodbye without offering the rescue, and that ending looks identical to the right one.
# Why: the chat modal shuts for a tick or 2 between a page and the option list behind it, most of a 3-tick silence at 200ms ticks, so a short quiet counter reads Gujuo's chain as ended one option short of the rescue.
ENDED_TICKS = 10
NEVER_OPENED_TICKS = 25


def drive_to_end(prefer, log, ms=45000, required=None):
    """Drive a self-terminating conversation, abandoning when no option matches."""
    deadline = _core.step_time() + ms
    quiet = 0
    # Why: a conversation that never opened hasn't happened, and reporting it as a win feeds the engine's no-progress watchdog a success every pass.
    spoke = False
    took = False
    while _core.step_time() < deadline:
        if chat_dialog.can_continue():
            spoke = True
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            quiet = 0
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            spoke = True
            pick = pick_preferred(options, prefer)
            if not pick:
                log(f"no preferred option in [{' | '.join(options)}]")
                return False
            # Why: a chain that ends without moving the quest on is invisible otherwise, the driver reports the same success either way.
            log(f"chose \"{pick}\" from [{' | '.join(options)}]")
            took = took or pick == required
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            quiet = 0
            continue
        # Why: a `~mesbox` opens no chat widget, so the quiet counter would read a chain suspended on one as ended. `ungadulu_where` finishes on "The Shaman throws himself down on the floor and starts convulsing.", and that page left standing stops the next shaman opening his mouth.
        if modals.is_open():
            spoke = True
            _w2 = yield from modals.close()
            if not (_w2):
                yield from execution.delay_ticks(1)
            quiet = 0
            continue
        if not chat_dialog.is_open():
            quiet += 1
            if quiet >= ENDED_TICKS and spoke:
                if required and not took:
                    log(f'the chain ended without ever offering "{required}"')
                    return False
                return True
            if quiet >= NEVER_OPENED_TICKS:
                log('no dialogue ever opened')
                return False
        yield from execution.delay_ticks(1)
    return spoke and not chat_dialog.is_open()


# Why: `~mesbox` renders in the main modal and the chat driver only clicks the chat one (`ChatDialog.canContinue()` reads `chatContinueComId`), so a box chain from a loc script is readable by `modalText` and dismissable by nothing. The trials are 7 such chains.
def modal_text():
    """Whatever a modal box is currently showing, normalised for matching."""
    return normalize_journal(list(reader.main_modal_texts()) + list(chat_dialog.texts()))


def said_any(text, needles):
    """Whether lower-case text holds any of the needles: rs2b0t's alternations, as pocketpy has no re."""
    return any([needle in text for needle in needles])

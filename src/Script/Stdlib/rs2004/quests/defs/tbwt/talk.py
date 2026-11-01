"""Ported from rs2b0t's src/bot/api/ai/quests/defs/tbwt/talk.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs
from rs2004.items import inventory
from rs2004.quests.exec.primitives import open_dialogue, pick_preferred
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['LONG_GAP', 'CUTSCENE_GAP', 'walk_to', 'drive_fully', 'talk_fully', 'use_on_npc']

LONG_GAP = 16
CUTSCENE_GAP = 34


def walk_to(dest, radius, log):
    return traversal.walk_resilient(dest, radius=radius, attempts=3, timeout_ms=240000, log=log)


# Why: these conversations close the chat interface mid-chain (`if_close; p_delay(N)`) and re-open it several ticks later, and `driveDialog` treats the first of those gaps as the end.
def drive_fully(prefer, log, quiet_ticks=6):
    """Drive a conversation past the scripted gaps to where it stops re-opening; abandons when no preferred option matches."""
    quiet = 0
    for i in range(300):
        if not (quiet < quiet_ticks):
            break
        yield from sustain.run()
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            quiet = 0
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            pick = pick_preferred(options, list(prefer))
            if not pick:
                log(f"no preferred option in [{' | '.join(options)}]")
                return False
            yield from chat_dialog.choose_option(pick)
            quiet = 0
            yield from execution.delay_ticks(1)
            continue
        quiet += 1
        yield from execution.delay_ticks(1)
    return not chat_dialog.is_open()


# Why: these NPCs wander 5 tiles and the first Talk-to after a long walk lands on a tile they've left, so a settle and a second try is cheaper than another step.
def talk_fully(npc, anchor, prefer, log, quiet_ticks=6):
    """Walk to the NPC, open the dialogue, and drive it to the end."""
    _w1 = yield from walk_to(anchor, 4, log)
    if not (_w1):
        return False
    yield from settle_scene()
    _w2 = yield from open_dialogue(npc, log)
    if not (_w2):
        yield from execution.delay_ticks(3)
        _w3 = yield from open_dialogue(npc, log)
        if not (_w3):
            return False
    _result4 = yield from drive_fully(prefer, log, quiet_ticks)
    return _result4


def use_on_npc(item_id, npc, anchor, prefer, log, quiet_ticks=None):
    """Walk to the NPC, use a carried item on them, and drive whatever that raised."""
    if quiet_ticks is None:
        quiet_ticks = LONG_GAP
    _w5 = yield from walk_to(anchor, 4, log)
    if not (_w5):
        return False
    yield from settle_scene()
    # Why: the same wander that swallows a first Talk-to swallows a first use-on, so the click is re-aimed once.
    for attempt in range(2):
        target = npcs.query().name(npc).within(12).nearest()
        item = ([entry for entry in inventory.items() if entry.id == item_id] or [None])[0]
        if not target or not item:
            log(f'no \'{npc}\' in reach, or no item {item_id} in the pack')
            return False
        if not (item.use_on(target)):
            return False
        _w6 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 6000)
        if _w6:
            _result7 = yield from drive_fully(prefer, log, quiet_ticks)
            return _result7
        yield from execution.delay_ticks(3)
    log(f'\'{npc}\' did not answer item {item_id}')
    return False

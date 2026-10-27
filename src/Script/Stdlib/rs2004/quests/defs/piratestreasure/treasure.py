"""Ported from rs2b0t's src/bot/api/ai/quests/defs/piratestreasure/treasure.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import npcs
from rs2004.game import game, reader
from rs2004.interfaces import interfaces
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.piratestreasure.areas import PT_ID, PT_LOC, PT_TILE
from rs2004.quests.exec.prompts import drive_choice, prompt_loc, settle_scene, use_on_loc
from rs2004.traversal import traversal


__all__ = ['collect_rum', 'open_chest', 'read_message', 'dig_treasure']

def held(id):
    return inventory.count_by_id(id)


# Why: `[oploc1,grocerycrate]` returns the rum, then opens a Yes/No prompt that must be continued.
# Why: the `store-job` page also renders while the rum is still in the plantation crate and only an empty back room tells them apart, so a miss crosses to Karamja; a failure would retry forever.
def collect_rum(log):
    """Search Wydin's back-room crate for the shipped rum."""
    if held(PT_ID.RUM) > 0:
        return True
    yield from sustain.run()
    got = yield from prompt_loc(Record({
        'name': 'Crate',
        'op': 'Search',
        'near': PT_TILE.GROCERY_CRATE,
        'within': 6,
        'id': PT_LOC.GROCERY_CRATE,
        'prefer': ['No'],
        'expect': lambda: held(PT_ID.RUM) > 0,
        'expect_ms': 15000,
    }), log)
    if got and held(PT_ID.RUM) > 0:
        return True
    yield from drive_choice(['No'], log)
    log('the back-room crate held no rum — it has not shipped yet, crossing to Karamja')
    yield from traversal.walk_resilient(PT_TILE.BANANA_CRATE, radius=4, attempts=3, timeout_ms=300000, log=log)
    return False


# Why: The chest consumes the key and gives the message in one script, so the message confirms success.
def open_chest(log):
    """Unlock the Blue Moon chest with the key."""
    if held(PT_ID.PIRATE_MESSAGE) > 0:
        return True
    if held(PT_ID.CHEST_KEY) == 0:
        log('no chest key in the pack')
        return False
    yield from sustain.run()
    _result1 = yield from use_on_loc(PT_ID.CHEST_KEY, Record({'name': 'Chest', 'near': PT_TILE.PIRATE_CHEST, 'within': 6, 'id': PT_LOC.PIRATE_CHEST}), [], lambda: held(PT_ID.PIRATE_MESSAGE) > 0, log)
    return _result1


# Why: `~scroll_pirate_message` is an `if_settext` main modal, and leaving it up makes every later journal read come back empty.
def read_message(log):
    """Read the pirate message, then close the scroll it opens."""
    note = ([item for item in inventory.items() if item.id == PT_ID.PIRATE_MESSAGE] or [None])[0]
    if not note:
        log('no pirate message in the pack to read')
        return False
    if not (note.interact('Read')):
        return False
    yield from execution.delay_until(lambda: reader.modals().main != -1, 6000)
    if reader.modals().main != -1:
        _core.close_interfaces()
        yield from execution.delay_ticks(1)
    return True

DUG = 'you dig a hole in the ground'
GARDENER_RANGE = 10


def clear_gardener(log):
    """Clear the gardener if he is inside the dig's refusal radius."""

    def near():
        return npcs.query().where(lambda n: n.id == PT_ID.GARDENER).within(GARDENER_RANGE).nearest()

    first = near()
    if not first:
        log('no gardener within the dig radius')
        return
    log(f'gardener {first.distance()} tiles off — clearing him before the dig')
    game.set_combat_style('strength')
    for attempt in range(6):
        gardener = near()
        if not gardener:
            log('gardener down')
            return
        yield from sustain.run()
        if gardener.interact('Attack'):
            yield from execution.delay_until(lambda: near() is None, 20000)
        else:
            yield from execution.delay_ticks(2)
    log('the gardener would not go down — digging anyway')


# Why: `dig.rs2` aborts on `npc_find(coord, falador_gardener, 10, 0)` and his `maxrange` keeps him permanently inside that radius, so he cannot be waited out.
# Why: proximity is a hint that saves a wasted click; the dig message is the oracle and the pair is retried.
def dig_treasure(log):
    """Dig at the X in Falador park."""
    if held(PT_ID.SPADE) == 0:
        log('no spade in the pack — cannot dig')
        return False
    for attempt in range(4):
        yield from sustain.run()
        _w2 = yield from traversal.walk_resilient(PT_TILE.DIG_SITE, radius=1, attempts=3, timeout_ms=180000, log=log)
        if not (_w2):
            log('could not reach the dig site')
            return False
        yield from settle_scene()
        yield from clear_gardener(log)
        # Why: the attack walks you to the gardener and `spade.rs2` only fires within 1 tile of the X, so digging where the fight ended answers "Nothing interesting happens."
        _w3 = yield from traversal.walk_resilient(PT_TILE.DIG_SITE, radius=0, attempts=3, timeout_ms=60000, log=log)
        if not (_w3):
            log('could not get back onto the dig tile after the gardener')
            continue
        spade = ([item for item in inventory.items() if item.id == PT_ID.SPADE] or [None])[0]
        if not spade:
            return False
        mark = game_messages.mark()
        if not (spade.interact('Dig')):
            continue
        _w4 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, DUG), 8000)
        if _w4:
            # Why: `queue(hunt_quest_complete, 0, 0)` lands 4 ticks after the dig line, so the leg is not finished when the message is.
            yield from execution.delay_ticks(8)
            return True
        log(f"the dig landed nothing — said: [{' | '.join([m.text for m in game_messages.since(mark)])}]")
    return False

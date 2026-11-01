"""Ported from rs2b0t's src/bot/api/ai/quests/defs/regicide/finish.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.defs.regicide.areas import RG_ITEM, RG_LOC, RG_NPC, RG_TILE
from rs2004.quests.defs.regicide.isafdar import walk_to
from rs2004.quests.defs.regicide.journal import RG_STAGE
from rs2004.quests.engine.trace import format_tile
from rs2004.quests.exec.primitives import talk_strict
from rs2004.quests.exec.prompts import drive_until, held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['feed_lazy_guard', 'fire_catapult', 'report_to_iorwerth', 'meet_arianwyn', 'report_to_lathas']

# Why: Arianwyn appears at (2584,3296) only while the message is held, so stop there explicitly before entering the castle.
ARIANWYN_ZONE = Tile(2586, 3299, 0)
# Why: `[zone,0_40_51_24_32]` is the 8x8 square from (2584,3296), so this is a tile off its west edge: near enough that stepping out and back is 2 short walks, far enough that the walk back counts as an entry.
ARIANWYN_OUTSIDE = Tile(2580, 3299, 0)
ARIANWYN_TRIES = 3


def in_arianwyn_zone(tile):
    return tile is not None and tile.x >= 2584 and tile.x <= 2591 and tile.z >= 3296 and tile.z <= 3303


def feed_lazy_guard(log):
    """The cooked rabbit that gets the catapult's guard to look the other way."""
    _w1 = yield from walk_to(RG_TILE.LAZY_GUARD, 3, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w1):
        return False
    yield from settle_scene()
    # Why: 5 NPCs render as "Tyras guard", and only this one takes the rabbit.
    guard = npcs.query().where(lambda npc: npc.id == RG_NPC.LAZY_GUARD).within(10).nearest()
    rabbit = ([item for item in inventory.items() if item.id == RG_ITEM.COOKED_RABBIT.id] or [None])[0]
    if not guard or not rabbit:
        log(f"missing {('the cooked rabbit' if guard else 'the lazy guard')} at the catapult")
        return False
    if not (rabbit.use_on(guard)):
        return False
    _result2 = yield from drive_until(lambda: held_id(RG_ITEM.COOKED_RABBIT.id) == 0, [], log, 30000)
    return _result2


# Why: the firing is a 2-minute cutscene that walks you round the catapult, teleports you into an instanced copy of the camp to watch the tent burn and puts you back at (2183,3185), so the oracle is the bomb leaving the pack.
def fire_catapult(log):
    """The barrel bomb loaded and fired over the trees into King Tyras's tent."""
    _w3 = yield from walk_to(RG_TILE.CATAPULT, 3, RG_STAGE.SPOKEN_IORWERTH2, log)
    if not (_w3):
        return False
    yield from settle_scene()
    catapult = locs.query().where(lambda loc: loc.id == RG_LOC.CATAPULT).within(10).nearest()
    bomb = ([item for item in inventory.items() if item.id == RG_ITEM.BARREL_FUSED.id] or [None])[0]
    if not catapult or not bomb:
        log(f"missing {('the fused barrel bomb' if catapult else 'the catapult')}")
        return False
    if not (bomb.use_on(catapult)):
        return False
    _w4 = yield from drive_until(lambda: held_id(RG_ITEM.BARREL_FUSED.id) == 0, [], log, 30000)
    if not (_w4):
        log('the catapult would not take the bomb')
        return False
    # Why: the cutscene teleports twice and ends with a 3-tick animation lock, so the next leg waits for the forest floor before it starts.
    _result5 = yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 4000, 60000)
    return _result5


def report_to_iorwerth(log):
    """Lord Iorwerth takes the news and hands over the letter for King Lathas."""
    _w6 = yield from walk_to(RG_TILE.IORWERTH, 3, RG_STAGE.KILLED_TYRAS, log)
    if not (_w6):
        return False
    yield from settle_scene()
    _w7 = yield from talk_strict('Lord Iorwerth', [], log)
    if not (_w7):
        return False
    return held_id(RG_ITEM.MESSAGE.id) > 0


def meet_arianwyn(log):
    """Arianwyn's ambush on the Ardougne road, which breaks the seal on the letter."""
    # Why: `[zone,0_40_51_24_32]` queues Arianwyn only while `inv_total(inv, regicide_iorwerth_message) > 0`, so a pack without the letter stands in the zone forever. Say it once, with a reason.
    if held_id(RG_ITEM.MESSAGE.id) == 0:
        log(f'no {RG_ITEM.MESSAGE.name} in the pack — the Ardougne road zone only calls Arianwyn out while the letter is held')
        return False

    def elf_near():
        return npcs.query().where(lambda npc: npc.id == RG_NPC.ARIANWYN).within(8).nearest() is not None

    def showing():
        return chat_dialog.is_open() or chat_dialog.can_continue() or elf_near()

    # Why: `[zone,...]` fires on entry, so a leg already standing in it has nothing to trigger: `walkResilient` at radius 1 returns without moving and the step reports a timeout for a zone it's standing in. Each attempt steps out to the mustering tile first and walks back in.
    for attempt in range(ARIANWYN_TRIES):
        if not (not showing()):
            break
        _c8 = in_arianwyn_zone(game.tile())
        if _c8:
            _w9 = yield from traversal.walk_resilient(ARIANWYN_OUTSIDE, radius=1, attempts=2, timeout_ms=90000, log=log)
            _c8 = not (_w9)
        if _c8:
            log(f'could not step out of the zone at {format_tile(game.tile())} to re-enter it')
            return False
        _w10 = yield from traversal.walk_resilient(ARIANWYN_ZONE, radius=0, attempts=3, timeout_ms=300000, log=log)
        if not (_w10):
            return False
        log(f'waiting on the Ardougne road for Arianwyn at {format_tile(game.tile())}, letter held (entry {attempt + 1}/{ARIANWYN_TRIES})')
        yield from execution.delay_until(showing, 30000)
    if not showing():
        log(f'Arianwyn did not step out after {ARIANWYN_TRIES} entries into the zone at {format_tile(game.tile())}')
        return False
    # Why: `[queue,arianwyn_dialogue]` re-queues itself 16 times with a `p_walk(coord)` between beats, and one beat is an objbox, so the goal is the elf leaving.
    _result11 = yield from drive_until(lambda: not elf_near() and not chat_dialog.is_open(), [], log, 120000)
    return _result11


def report_to_lathas(log):
    """King Lathas takes the letter and pays out."""
    # Why: his reward branch reads the letter out of the pack, so without it the conversation opens, says nothing new and closes, which the step could only report as "no inventory change".
    if held_id(RG_ITEM.MESSAGE.id) == 0:
        log(f'no {RG_ITEM.MESSAGE.name} in the pack — King Lathas pays out on the letter, so there is nothing to hand him')
        return False
    _w12 = yield from traversal.walk_resilient(RG_TILE.LATHAS, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w12):
        return False
    yield from settle_scene()
    _result13 = yield from talk_strict('King Lathas', [], log)
    return _result13


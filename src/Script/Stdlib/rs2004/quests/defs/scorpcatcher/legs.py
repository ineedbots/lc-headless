"""Ported from rs2b0t's src/bot/api/ai/quests/defs/scorpcatcher/legs.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.quests.barcrawl.run_barcrawl import ensure_barcrawl
from rs2004.quests.defs.scorpcatcher.antipoison import cure_poison, poison_mark, stock_antipoison
from rs2004.quests.defs.scorpcatcher.areas import ABBOT, EVERY_CAGE, SCORPION_NPC, SC_ID, SC_TILE, SEER, caught_in
from rs2004.quests.defs.scorpcatcher.dungeon import cross_secret_wall, enter_deep_dungeon, leave_deep_dungeon
from rs2004.quests.exec.primitives import goto_npc, open_dialogue, pick_preferred, talk_through
from rs2004.quests.exec.prompts import drive_until, settle_scene
from rs2004.quests.journal_text import normalize_journal
from rs2004.traversal import traversal

__all__ = ['ask_the_seer', 'CATCH_LEG']

WALK_MS = 300000
CATCH_MS = 10000
CLIMB_MS = 8000
SEER_MS = 45000
HINT_GIVEN = 'see if you can find that scorpion'


# Why: `seer_looking_glass` runs `if_close` then 3 `mes` lines a `p_delay(3)` apart before reopening chat, and the shared driver calls a dialogue over after 1.5s shut.
# Why: it then reports success with the hint ungiven, so the leg re-walks to Seers' Village and bails at the same gap for as long as the engine retries.
def ask_the_seer(log):
    """Ask a Seer where the first scorpion is, sitting through the looking-glass pauses."""
    _w1 = yield from goto_npc(SEER, [], log)
    if not (_w1):
        return False
    _w2 = yield from open_dialogue(SEER.npc, log)
    if not (_w2):
        return False
    heard = False
    deadline = _core.step_time() + SEER_MS
    while _core.step_time() < deadline:
        texts = chat_dialog.texts()
        if len(texts) > 0 and HINT_GIVEN in normalize_journal(texts):
            heard = True
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            continue
        options = chat_dialog.options()
        if len(options) > 0:
            pick = pick_preferred(options, SEER.prefer)
            if not pick:
                log(f"scorpcatcher: the Seer offered [{' | '.join(options)}] and none of it asks about the scorpions")
                return False
            yield from chat_dialog.choose_option(pick)
            yield from execution.delay_ticks(2)
            continue
        if heard and not chat_dialog.is_open():
            break
        yield from execution.delay_ticks(1)
    log(('scorpcatcher: the Seer has placed the first scorpion' if heard else 'scorpcatcher: the Seer never got as far as the hint'))
    return heard


def held_cage_id():
    """The cage in the pack, whichever of the 8 it is."""
    cage = ([item for item in inventory.items() if item.id in EVERY_CAGE] or [None])[0]
    return cage.id if cage is not None else None


# Why: all 3 scorpions render "Kharid Scorpion" and the cage's own name never changes, so both sides of the use are addressed by id.
def cage_scorpion(key, log):
    cage_id = held_cage_id()
    if cage_id is None:
        log('scorpcatcher: no scorpion cage in the pack to catch with')
        return False
    if (key in caught_in(cage_id)):
        return True
    yield from settle_scene()
    npc_id = SCORPION_NPC[key]
    scorpion = npcs.query().where(lambda npc: npc.id == npc_id).within(10).nearest()
    cage = ([item for item in inventory.items() if item.id == cage_id] or [None])[0]
    if not scorpion or not cage:
        log(f'scorpcatcher: no Kharid Scorpion {npc_id} within 10 tiles')
        return False
    # Why: a scorpion with no `wanderrange` drifts 5 tiles (in the monastery through a door), and a use-on queued against a walk the server can't make sits silent until its 10s runs out.
    # Why: the walk is unconditional since tile distance counts through walls, so adjacent doesn't mean reachable.
    _w3 = yield from traversal.walk_resilient(scorpion.tile(), radius=1, attempts=2, timeout_ms=60000, log=log)
    if not (_w3):
        log(f'scorpcatcher: could not reach the {key.upper()} scorpion at ({scorpion.tile().x},{scorpion.tile().z})')
        return False
    target = npcs.query().where(lambda npc: npc.id == npc_id).within(10).nearest()
    if not target or not (cage.use_on(target)):
        log(f'scorpcatcher: the {key.upper()} scorpion refused the cage')
        return False

    # Why: the catch swaps the cage for a heavier obj, so the id changing is the only proof it landed.
    def _fn4():
        now = held_cage_id()
        return now is not None and (key in caught_in(now))
    caught = yield from drive_until(_fn4, [], log, CATCH_MS)
    log((f'scorpcatcher: caught the {key.upper()} scorpion' if caught else f'scorpcatcher: the cage never closed on the {key.upper()} scorpion — it has wandered off'))
    return caught


def catch_outpost_scorpion(log):
    """Barbarian Outpost: the barcrawl opens the gate, then the scorpion is in Ivor's hut."""
    _w5 = yield from leave_deep_dungeon(log)
    if not (_w5):
        return False
    _w6 = yield from ensure_barcrawl(log)
    if not (_w6):
        return False
    _w7 = yield from traversal.walk_resilient(SC_TILE.OUTPOST_HUT, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w7):
        log("scorpcatcher: could not get into Ivor's hut at the Barbarian Outpost")
        return False
    _result8 = yield from cage_scorpion('b', log)
    return _result8


def catch_taverley_scorpion(log):
    """Taverley: the dusty key, the dragon corridor, then the wall by the 2 coffins."""
    yield from stock_antipoison(log)
    mark = poison_mark()
    _w9 = yield from enter_deep_dungeon(log)
    if not (_w9):
        return False
    _w10 = yield from cross_secret_wall(True, log)
    if not (_w10):
        return False
    _w11 = yield from cage_scorpion('a', log)
    if not (_w11):
        return False
    _w12 = yield from cross_secret_wall(False, log)
    if not (_w12):
        return False
    _w13 = yield from leave_deep_dungeon(log)
    if not (_w13):
        return False
    yield from cure_poison(mark, log)
    return True


def upstairs():
    at = game.tile()
    return at is not None and at.level == 1 and at.x >= 3040 and at.x <= 3062 and at.z >= 3480 and at.z <= 3495


# Why: `oploc1,monasteryladder` refuses anyone outside the order, and a refused climb is a mesbox the walker reads as a quest lock, which blacklists the ladder for the rest of the session.
def join_the_order(log):
    _w14 = yield from traversal.walk_resilient(SC_TILE.ABBOT, radius=3, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w14):
        return False
    yield from execution.delay_ticks(2)
    log('scorpcatcher: asking Abbot Langley to join the order')
    _result15 = yield from talk_through(ABBOT.npc, ABBOT.prefer, log)
    return _result15


def climb_to_the_robes(log):
    _w16 = yield from traversal.walk_resilient(SC_TILE.MONASTERY_LADDER, radius=1, attempts=3, timeout_ms=WALK_MS, log=log)
    if not (_w16):
        return False
    yield from settle_scene()
    ladder = locs.query().where(lambda loc: loc.id == SC_ID.MONASTERY_LADDER).action('Climb-up').within(5).nearest()
    if not ladder or not (ladder.interact('Climb-up')):
        log('scorpcatcher: no monastery ladder to climb')
        return False
    _w17 = yield from drive_until(upstairs, [], log, CLIMB_MS)
    if not (_w17):
        log('scorpcatcher: the monastery ladder did not let us up')
        return False
    yield from settle_scene()
    return True


def catch_monastery_scorpion(log):
    """The monastery: join the order, climb, and the scorpion is by the robes on the table."""
    _w18 = yield from leave_deep_dungeon(log)
    if not (_w18):
        return False
    if not upstairs():
        _w19 = yield from join_the_order(log)
        if not (_w19):
            return False
        _w20 = yield from climb_to_the_robes(log)
        if not (_w20):
            return False
    _w21 = yield from traversal.walk_resilient(SC_TILE.MONASTERY_ROOM, radius=2, attempts=3, timeout_ms=90000, log=log)
    if not (_w21):
        return False
    _result22 = yield from cage_scorpion('c', log)
    return _result22


CATCH_LEG = {'a': catch_taverley_scorpion, 'b': catch_outpost_scorpion, 'c': catch_monastery_scorpion}

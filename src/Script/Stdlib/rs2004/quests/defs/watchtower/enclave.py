"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/enclave.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.entities import ground_items, locs, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_LOC, WT_NPC, WT_TILE, watchtower_area
from rs2004.quests.defs.watchtower.loadout import edible_names
from rs2004.quests.defs.watchtower.scene import settle_scene
from rs2004.quests.exec.primitives import drive_dialog
from rs2004.traversal import traversal

__all__ = ['enter_enclave', 'leave_enclave', 'dissolve_shamans', 'mine_dalgroth', 'search_shaman_robe']

def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def loc_near(id, op, within=10):
    return locs.query().where(lambda loc: loc.id == id).action(op).within(within).nearest()


def enter_enclave(log):
    """Every entry burns one nightshade; the guard is distracted only for the run past."""
    if event_signal.pending():
        return False
    game.set_auto_retaliate(False)
    if watchtower_area(game.tile()) == 'enclave':
        return True
    if held_id(WT_ITEM.NIGHTSHADE.id) == 0:
        log('no Nightshade — the enclave guard cannot be distracted')
        return False
    _w1 = yield from traversal.walk_resilient(WT_TILE.ENCLAVE_GUARD, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w1):
        return False
    guard = npcs.query().name(WT_NPC.ENCLAVE_GUARD).nearest()
    shade = ([item for item in inventory.items() if item.id == WT_ITEM.NIGHTSHADE.id] or [None])[0]
    if not guard or not shade or not (shade.use_on(guard)):
        log('could not use Nightshade on the enclave guard')
        return False
    # Why: drive the dialogue the nightshade opened and never start a fresh one, as both of this guard's own conversation options make him attack.
    _w2 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
    if _w2:
        yield from drive_dialog([], log)
    _w3 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'enclave', 15000)
    if not (_w3):
        return False
    yield from settle_scene()
    return True


def leave_enclave(log):
    if watchtower_area(game.tile()) != 'enclave':
        return True
    _w4 = yield from traversal.walk_resilient(WT_TILE.ENCLAVE_EXIT, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w4):
        return False
    cave = loc_near(WT_LOC.ENCLAVE_CAVE, 'Enter')
    if not cave or not (cave.interact('Enter')):
        log('no enclave exit cave in range')
        return False
    _w5 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'enclave', 15000)
    if not (_w5):
        return False
    yield from settle_scene()
    return True


def safe_to_continue(log):
    if event_signal.pending():
        return False
    if skills.effective('hitpoints') < skills.level('hitpoints') * 0.6:
        yield from sustain.run()
    if event_signal.pending():
        return False
    foods = set(edible_names())
    food = sum([item.count for item in [item for item in inventory.items() if (((item.name.lower() if item.name is not None else None) if (item.name.lower() if item.name is not None else None) is not None else '') in foods)]])
    if food >= 2 and inventory.free() >= 2 and skills.effective('hitpoints') >= skills.level('hitpoints') * 0.6:
        return True
    log('enclave reserve exhausted; retreating for food or inventory space')
    yield from leave_enclave(log)
    return False


def dissolve_shamans(log):
    _c7 = event_signal.pending()
    if not _c7:
        _w8 = yield from safe_to_continue(log)
        _c7 = not (_w8)
    _c6 = _c7
    if not _c6:
        _w9 = yield from enter_enclave(log)
        _c6 = not (_w9)
    if _c6:
        return False
    for spot in WT_TILE.SHAMANS:
        _w10 = yield from safe_to_continue(log)
        if not (_w10) or held_id(WT_ITEM.MAGIC_OGRE_POTION.id) == 0:
            return False
        _w11 = yield from traversal.walk_resilient(spot, radius=2, attempts=2, timeout_ms=90000, log=log)
        if not (_w11):
            if event_signal.pending():
                return False
            continue
        _w12 = yield from safe_to_continue(log)
        if not (_w12):
            return False
        shaman = npcs.query().name(WT_NPC.SHAMAN).where(lambda npc: npc.distance() <= 4).nearest()
        potion = ([item for item in inventory.items() if item.id == WT_ITEM.MAGIC_OGRE_POTION.id] or [None])[0]
        if not shaman or not potion:
            continue
        mark = game_messages.mark()
        if not (potion.use_on(shaman)):
            return False
        _w13 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, 'the ogre dissolves into spirit form'), 8000)
        if not (_w13):
            return False
        if event_signal.pending():
            return False
        _w14 = yield from execution.delay_until(lambda: chat_dialog.is_open() or chat_dialog.can_continue(), 8000)
        if _w14:
            yield from drive_dialog([], log)
        if event_signal.pending():
            return False
        execution.note_progress()
        return True
    log('no reachable ogre shaman dissolved')
    return False


def mine_dalgroth(log):
    if held_id(WT_ITEM.CRYSTAL4.id) > 0:
        return True
    _w16 = yield from safe_to_continue(log)
    _c15 = not (_w16)
    if not _c15:
        _w17 = yield from enter_enclave(log)
        _c15 = not (_w17)
    if _c15:
        return False
    _w18 = yield from traversal.walk_resilient(WT_TILE.ROCK_OF_DALGROTH, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w18):
        return False
    _w19 = yield from safe_to_continue(log)
    if not (_w19):
        return False
    rock = loc_near(WT_LOC.ROCK_OF_DALGROTH, 'Mine')
    if not rock or not (rock.interact('Mine')):
        log('no Rock of Dalgroth in range, or no pickaxe carried')
        return False
    _result20 = yield from execution.delay_until(lambda: held_id(WT_ITEM.CRYSTAL4.id) > 0, 20000)
    return _result20


def search_shaman_robe(log):
    if held_id(WT_ITEM.CRYSTAL3.id) > 0:
        return True
    _w22 = yield from safe_to_continue(log)
    _c21 = not (_w22)
    if not _c21:
        _w23 = yield from enter_enclave(log)
        _c21 = not (_w23)
    if _c21:
        return False
    _w24 = yield from traversal.walk_resilient(WT_TILE.SHAMAN_ROBE, radius=2, attempts=3, timeout_ms=180000, log=log)
    if not (_w24):
        return False
    _w25 = yield from safe_to_continue(log)
    if not (_w25):
        return False
    if held_id(WT_ITEM.SHAMAN_ROBE.id) == 0:
        robe = ground_items.query().name(WT_ITEM.SHAMAN_ROBE.name).within(4).nearest()
        if not robe or not (robe.interact('Take')):
            log('no shaman robe on the enclave floor')
            return False
        _w26 = yield from execution.delay_until(lambda: held_id(WT_ITEM.SHAMAN_ROBE.id) > 0, 6000)
        if not (_w26):
            return False
    carried = ([item for item in inventory.items() if item.id == WT_ITEM.SHAMAN_ROBE.id] or [None])[0]
    if not carried or not (carried.interact('Search')):
        return False
    _result27 = yield from execution.delay_until(lambda: held_id(WT_ITEM.CRYSTAL3.id) > 0, 8000)
    return _result27

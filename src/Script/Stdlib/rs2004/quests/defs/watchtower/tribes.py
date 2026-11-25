"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/tribes.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game, skills
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.navigation import reachability
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_LOC, WT_NPC, WT_TILE, watchtower_area
from rs2004.quests.defs.watchtower.journal import read_watchtower_progress
from rs2004.quests.defs.watchtower.scene import settle_scene
from rs2004.quests.exec.primitives import talk_strict, talk_through
from rs2004.quests.engine.types import has_flag
from rs2004.quests.prayer import prayer_upkeep
from rs2004.reach import reach
from rs2004.traversal import traversal

__all__ = ['JANGERBERRY_TARGET', 'talk_to_og', 'leave_toban_camp', 'open_toban_chest', 'talk_to_toban', 'leave_grew_island', 'talk_to_grew', 'pick_jangerberries', 'kill_gorad']

JANGERBERRY_TARGET = 2


def held_id(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


def loc_near(id, op, within=8):
    return locs.query().where(lambda loc: loc.id == id).action(op).within(within).nearest()


def talk_to_og(log):
    _w1 = yield from reach.npc_dialog(WT_NPC.OG, WT_TILE.OG, log=log)
    if (_w1) != 'done':
        return False
    # The unmatched option here is "I have come to kill you."
    _result2 = yield from talk_strict(WT_NPC.OG, [
        'I seek entrance to the city of ogres.',
        'I have your gold.',
        'I have lost the key!',
        'I have lost the relic part you gave me.',
    ], log)
    return _result2


def enter_toban_camp(log):
    if watchtower_area(game.tile()) == 'tobanCamp':
        return True
    _w3 = yield from traversal.walk_resilient(WT_TILE.TOBAN_CAVE, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w3):
        return False
    cave = loc_near(WT_LOC.TOBAN_CAVE, 'Enter')
    if not cave or not (cave.interact('Enter')):
        log('no Toban cave entrance in range')
        return False
    _w4 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'tobanCamp', 15000)
    if not (_w4):
        return False
    yield from settle_scene()
    # The tunnel opens a player dialogue, not Toban's conversation. Reach must
    # see it closed before deciding whether it has reached the wandering NPC.
    if chat_dialog.can_continue():
        yield from chat_dialog.continue_()
        closed = yield from execution.delay_until(lambda: not chat_dialog.is_open(), 5000)
        if not closed:
            return False
    return True


def leave_toban_camp(log):
    if watchtower_area(game.tile()) != 'tobanCamp':
        return True
    _w5 = yield from traversal.walk_resilient(WT_TILE.TOBAN_LADDER, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w5):
        return False
    ladder = loc_near(WT_LOC.TOBAN_LADDER_DOWN, 'Climb-down', 6)
    if not ladder or not (ladder.interact('Climb-down')):
        log("no ladder out of Toban's camp in range")
        return False
    _w6 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'tobanCamp', 15000)
    if not (_w6):
        return False
    yield from settle_scene()
    return True


def open_toban_chest(log):
    if held_id(WT_ITEM.STOLEN_GOLD.id) > 0:
        return True
    _w7 = yield from enter_toban_camp(log)
    if not (_w7):
        return False
    _w8 = yield from traversal.walk_resilient(WT_TILE.TOBAN_CHEST, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w8):
        return False
    chest = locs.query().where(lambda loc: loc.id == WT_LOC.TOBAN_CHEST).within(6).nearest()
    key = ([item for item in inventory.items() if item.id == WT_ITEM.TOBAN_KEY.id] or [None])[0]
    if not chest or not key:
        log("no chest, or no key, at Toban's camp")
        return False
    # op1 eats the key; using the key on the chest keeps it for a second opening.
    if not (key.use_on(chest)):
        return False
    _result9 = yield from execution.delay_until(lambda: held_id(WT_ITEM.STOLEN_GOLD.id) > 0, 8000)
    return _result9


def talk_to_toban(log):
    _w10 = yield from enter_toban_camp(log)
    if not (_w10):
        return False
    # A newly loaded camp can have scenery before Toban's NPC arrives.
    # Finish the approach here instead of letting area recovery take us out.
    status = 'retry'
    for attempt in range(3):
        yield from sustain.run()
        status = yield from reach.npc_dialog(WT_NPC.TOBAN, WT_TILE.TOBAN, log=log)
        if status != 'retry':
            break
        yield from execution.delay_ticks(2)
    if status != 'done':
        return False
    # The unmatched option here is "Die, creature!"
    _result12 = yield from talk_strict(WT_NPC.TOBAN, [
        'I seek entrance to the city of ogres.',
        'I could do something for you...',
        "I can't find the relic part you gave me.",
    ], log)
    return _result12


def swing_to_grew_island(log):
    if watchtower_area(game.tile()) == 'grewIsland':
        return True
    _w13 = yield from traversal.walk_resilient(WT_TILE.ROPESWING_STAND, radius=2, attempts=3, timeout_ms=300000, log=log)
    if not (_w13):
        return False
    tree = locs.query().where(lambda loc: loc.id == WT_LOC.ROPESWING_NOROPE).within(6).nearest()
    rope = ([item for item in inventory.items() if item.id == WT_ITEM.ROPE.id] or [None])[0]
    if not tree or not rope:
        log('no rope, or no swing tree, at the Grew crossing')
        return False
    if not (rope.use_on(tree)):
        return False
    _w14 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) == 'grewIsland', 15000)
    if not (_w14):
        return False
    yield from settle_scene()
    return True


def leave_grew_island(log):
    if watchtower_area(game.tile()) != 'grewIsland':
        return True
    _w15 = yield from traversal.walk_resilient(WT_TILE.GREW_EXIT_STAND, radius=1, attempts=3, timeout_ms=60000, log=log)
    if not (_w15):
        return False
    swing = loc_near(WT_LOC.ROPESWING, 'Swing-on', 6)
    if not swing or not (swing.interact('Swing-on')):
        log('no Grew-island rope swing in range')
        return False
    _w16 = yield from execution.delay_until(lambda: watchtower_area(game.tile()) != 'grewIsland', 15000)
    if not (_w16):
        return False
    yield from settle_scene()
    return True


def talk_to_grew(log):
    _w17 = yield from swing_to_grew_island(log)
    if not (_w17):
        return False
    deadline = _core.step_time() + 240000
    initial = None
    want = 'helped-grew' if held_id(WT_ITEM.OGRE_TOOTH.id) > 0 else 'spoken-grew'
    before_part = held_id(WT_ITEM.RELIC_PART2.id)
    before_crystal = held_id(WT_ITEM.CRYSTAL1.id)
    while _core.step_time() < deadline:
        stand = grew_dialogue_stand()
        if stand is None:
            return False
        if game.tile() != stand:
            walked = yield from traversal.walk_resilient(stand, radius=0, attempts=1, timeout_ms=15000, log=log)
            if not walked:
                return False
        quiet = yield from quiet_grew_island(deadline, log)
        if not quiet:
            return False
        if initial is None:
            initial = yield from read_watchtower_progress()
            if initial is None:
                yield from execution.delay_ticks(2)
                continue
        game.set_auto_retaliate(False)
        status = yield from reach.npc_dialog(WT_NPC.GREW, stand, log=log)
        if status == 'done':
            # The unmatched option here is "You will have to kill me first."
            yield from talk_strict(WT_NPC.GREW, [
                "Don't eat me; I can help you.",
                "I've lost the relic part you gave me.",
                "I've lost the crystal you gave me.",
            ], log)
            if event_signal.pending() or skills.effective('hitpoints') <= 0:
                return False
            # Attacks close dialogue boxes too. Only the quest's state proves
            # that the conversation reached its useful end.
            if not chat_dialog.is_open():
                progress = yield from read_watchtower_progress()
                if has_flag(initial, 'helped-grew'):
                    if held_id(WT_ITEM.RELIC_PART2.id) > before_part or held_id(WT_ITEM.CRYSTAL1.id) > before_crystal:
                        return True
                elif has_flag(progress, want):
                    return True
        log('Grew conversation did not finish; clearing attackers and retrying on the island')
        yield from execution.delay_ticks(2)
    log('Grew conversation exceeded its four-minute island budget')
    return False


def distance_from_npc(tile, npc):
    at = npc.tile()
    return max(0, at.x - tile.x, tile.x - at.x - npc.size + 1, at.z - tile.z, tile.z - at.z - npc.size + 1)


def grew_dialogue_stand():
    """Use the reachable side of Grew furthest from the island's other ogres."""
    grew = npcs.query().name(WT_NPC.GREW).nearest()
    if grew is None:
        return WT_TILE.GREW
    at = grew.tile()
    ogres = npcs.query().name('Ogre').within(16).where(lambda npc: watchtower_area(npc.tile()) == 'grewIsland').results()
    candidates = []
    for offset in range(grew.size):
        candidates.extend([Tile(at.x - 1, at.z + offset, at.level), Tile(at.x + grew.size, at.z + offset, at.level),
                           Tile(at.x + offset, at.z - 1, at.level), Tile(at.x + offset, at.z + grew.size, at.level)])
    candidates = [tile for tile in candidates if watchtower_area(tile) == 'grewIsland' and reachability.can_reach(tile)
                  and not any([distance_from_npc(tile, npc) == 0 for npc in ogres])]
    if not candidates:
        return None
    return max(candidates, key=lambda tile: (min([distance_from_npc(tile, npc) for npc in ogres]) if ogres else 16,
                                           -tile.distance_to(game.tile()), tile.x, tile.z))


def quiet_grew_island(deadline, log):
    """Defeat only ogres attacking us before opening a conversation."""
    target_index = None
    while _core.step_time() < deadline:
        if event_signal.pending() or skills.effective('hitpoints') <= 0 or watchtower_area(game.tile()) != 'grewIsland':
            return False
        if skills.effective('hitpoints') < skills.level('hitpoints') * 0.4 and not any(['Eat' in item.actions() for item in inventory.items()]):
            log('leaving Grew dialogue retry: low hitpoints and no food')
            return False
        yield from sustain.run()
        yield from prayer_upkeep()
        # Hold the safer dialogue tile; chasing an attacker would put us back
        # amongst the respawns. Let it approach before returning its attacks.
        ogre = npcs.query().name('Ogre').action('Attack').within(12).where(lambda npc: npc.targets_me() and distance_from_npc(game.tile(), npc) <= 1 and not (npc.max_health > 0 and npc.health == 0)).nearest()
        if ogre is None:
            if not game.in_combat():
                return True
        else:
            if ogre.index != target_index:
                target_index = ogre.index
                log(f'clearing aggressive island Ogre {target_index} before talking to Grew')
            if game.facing() != ('npc', ogre.index):
                ogre.interact('Attack')
        yield from execution.delay_ticks(1)
    return False


def pick_jangerberries(log):
    if held_id(WT_ITEM.JANGERBERRIES.id) >= JANGERBERRY_TARGET:
        return True
    _w20 = yield from swing_to_grew_island(log)
    if not (_w20):
        return False
    for spot in WT_TILE.JANGERBERRIES:
        if held_id(WT_ITEM.JANGERBERRIES.id) >= JANGERBERRY_TARGET:
            return True
        _w21 = yield from traversal.walk_resilient(spot, radius=1, attempts=2, timeout_ms=45000, log=log)
        if not (_w21):
            continue
        berry = ground_items.query().name(WT_ITEM.JANGERBERRIES.name).within(3).nearest()
        if not berry:
            continue
        before = held_id(WT_ITEM.JANGERBERRIES.id)
        if berry.interact('Take'):
            yield from execution.delay_until(lambda: held_id(WT_ITEM.JANGERBERRIES.id) > before, 5000)
    return held_id(WT_ITEM.JANGERBERRIES.id) > 0


def kill_gorad(log):
    if held_id(WT_ITEM.OGRE_TOOTH.id) > 0:
        return True
    if inventory.free() == 0:
        log('no free slot — Gorad drops nothing into a full pack')
        return False
    _w22 = yield from enter_toban_camp(log)
    if not (_w22):
        return False
    _w23 = yield from reach.npc_dialog(WT_NPC.GORAD, WT_TILE.GORAD, log=log)
    if (_w23) != 'done':
        return False
    _w24 = yield from talk_through(WT_NPC.GORAD, ["I don't know who you are."], log)
    if not (_w24):
        return False
    _result25 = yield from fight_gorad(log)
    return _result25


# Why: once Grew has asked for the tooth, the talk ends in Gorad's npc_retaliate, so an account without
# auto-retaliate stands still under his hits; and sustain is call-driven, so a bare wait never eats (live: died at 99).
def fight_gorad(log):
    """Swing at Gorad and eat until his tooth lands, for up to four minutes."""
    for i in range(400):
        if held_id(WT_ITEM.OGRE_TOOTH.id) > 0:
            return True
        yield from sustain.run()
        gorad = npcs.query().name(WT_NPC.GORAD).action('Attack').within(10).nearest()
        if gorad and game.facing() != ('npc', gorad.index) and gorad.interact('Attack'):
            yield from execution.delay_ticks(2)
        yield from execution.delay_ticks(1)
    log('Gorad outlasted his fight window')
    return held_id(WT_ITEM.OGRE_TOOTH.id) > 0

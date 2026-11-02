"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/totem.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game
from rs2004.quests.defs.legends.areas import EVIL_TOTEMS, FERTILE_SOILS, LQ_ID, LQ_LOC, LQ_LOC_ID, LQ_NPC
from rs2004.quests.defs.legends.fight import fight
from rs2004.quests.defs.legends.jungle import enter_jungle, talk_gujuo
from rs2004.quests.defs.legends.scene import clear_boxes, drive_until, held_id, modal_text, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['grow_totem_pole', 'replace_evil_totem', 'take_gilded_totem', 'ask_for_more_seeds']

PLANT_ATTEMPTS = 3
GROW_MS = 90000


def nearest_of(tiles):
    here = game.tile()
    if not here:
        return tiles[0]
    return (sorted(list(tiles), key=lambda a: a.distance_to(here)) or [None])[0]


def tree_at(id, near):
    return locs.query().where(lambda l: l.id == id and l.tile().distance_to(near) <= 6).nearest()


def axe_on(id, name, near, next_, log):
    if tree_at(next_, near):
        return True
    _result1 = yield from use_on_loc(LQ_ID.RUNE_AXE, Record({'name': name, 'near': near, 'within': 8, 'id': id}), [], lambda: tree_at(next_, near) is not None, log)
    return _result1


# Why: every stage of the tree reverts to a rotten one 51 ticks after it grows, so planting, watering, felling, trimming and carving can't be 5 decide ticks.
# Why: the chain is one step whose oracle is the totem pole in the pack.
def grow_totem_pole(log):
    """Grow a Yommi tree from a germinated seed and carve it into a totem pole."""
    if held_id(LQ_ID.TOTEM_POLE) > 0:
        return True
    _w2 = yield from enter_jungle(log)
    if not (_w2):
        return False
    if held_id(LQ_ID.RUNE_AXE) == 0:
        log('no rune axe in the pack — nothing weaker will touch a Yommi tree')
        return False
    soil = nearest_of(FERTILE_SOILS)
    _w3 = yield from traversal.walk_resilient(soil, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w3):
        return False
    yield from settle_scene()
    for attempt in range(PLANT_ATTEMPTS):
        if tree_at(LQ_LOC_ID.YOMMI_SAPLING, soil) or tree_at(LQ_LOC_ID.YOMMI_ADULT, soil):
            break
        if held_id(LQ_ID.YOMMI_SEEDS_GERM) == 0:
            log('no germinated Yommi seeds left to plant')
            return False
        if held_id(LQ_ID.GOLD_BOWL_BLESSED_PURE) == 0:
            log('the planting is refused without sacred water in hand to feed the tree')
            return False
        yield from use_on_loc(LQ_ID.YOMMI_SEEDS_GERM, Record({'name': LQ_LOC.FERTILE_SOIL, 'near': soil, 'within': 8, 'id': LQ_LOC_ID.FERTILE_SOIL}), [], lambda: tree_at(LQ_LOC_ID.YOMMI_SAPLING, soil) is not None or ('withers and dies' in modal_text()), log)
        yield from clear_boxes()
    if tree_at(LQ_LOC_ID.YOMMI_SAPLING, soil):
        watered = yield from use_on_loc(LQ_ID.GOLD_BOWL_BLESSED_PURE, Record({'name': LQ_LOC.YOMMI_SAPLING, 'near': soil, 'within': 8, 'id': LQ_LOC_ID.YOMMI_SAPLING}), [], lambda: tree_at(LQ_LOC_ID.YOMMI_ADULT, soil) is not None, log)
        if not watered:
            log('the sapling would not take the sacred water')
            return False
    _w4 = yield from execution.delay_until(lambda: tree_at(LQ_LOC_ID.YOMMI_ADULT, soil) is not None, GROW_MS)
    if not (_w4):
        log('no adult Yommi tree grew on the soil')
        return False
    _w5 = yield from axe_on(LQ_LOC_ID.YOMMI_ADULT, LQ_LOC.YOMMI_ADULT, soil, LQ_LOC_ID.YOMMI_FELLED, log)
    if not (_w5):
        return False
    _w6 = yield from axe_on(LQ_LOC_ID.YOMMI_FELLED, LQ_LOC.YOMMI_FELLED, soil, LQ_LOC_ID.YOMMI_TRIMMED, log)
    if not (_w6):
        return False
    _w7 = yield from axe_on(LQ_LOC_ID.YOMMI_TRIMMED, LQ_LOC.YOMMI_TRIMMED, soil, LQ_LOC_ID.YOMMI_TOTEM, log)
    if not (_w7):
        return False
    carved = tree_at(LQ_LOC_ID.YOMMI_TOTEM, soil)
    if not carved or not (carved.interact('Lift')):
        log('the carved totem would not lift')
        return False
    _result8 = yield from execution.delay_until(lambda: held_id(LQ_ID.TOTEM_POLE) > 0, 12000)
    return _result8


TOTEM_FIGHT_MS = 420000


# Why: the first time the new pole touches an evil one the demon comes out, and the second time, after he's dead, swaps them.
def replace_evil_totem(log):
    """Put the new pole on an evil totem, fighting whatever comes out of it."""
    if held_id(LQ_ID.TOTEM_POLE) == 0:
        return True
    _w9 = yield from enter_jungle(log)
    if not (_w9):
        return False
    totem = nearest_of(EVIL_TOTEMS)
    _w10 = yield from traversal.walk_resilient(totem, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w10):
        return False
    yield from settle_scene()

    def enemy_near(name):
        return npcs.query().name(name).action('Attack').within(14).exists()

    for attempt in range(6):
        if held_id(LQ_ID.TOTEM_POLE) == 0:
            return True
        if not enemy_near(LQ_NPC.NEZIKCHENED):
            yield from use_on_loc(LQ_ID.TOTEM_POLE, Record({'name': LQ_LOC.TOTEM_POLE, 'near': totem, 'within': 8, 'id': LQ_LOC_ID.EVIL_TOTEM}), [], lambda: held_id(LQ_ID.TOTEM_POLE) == 0 or enemy_near(LQ_NPC.NEZIKCHENED), log)
            yield from clear_boxes()
        if held_id(LQ_ID.TOTEM_POLE) == 0:
            return True
        # Why: with Viyeldi alive the demon comes alone; kill whatever is swinging.
        for name in [LQ_NPC.SAN_TOJALON, LQ_NPC.IRVIG_SENAY, LQ_NPC.RANALPH_DEVERE, LQ_NPC.NEZIKCHENED]:
            if enemy_near(name):
                yield from fight(Record({'npc': name, 'done': lambda: not enemy_near(name), 'ms': TOTEM_FIGHT_MS}), log)
        yield from execution.delay_ticks(4)
    log('the evil totem would not take the new pole')
    return False


GIFT_PREFER = ['Ok thanks for your help.', 'Do you have any news?']
take_gilded_totem = talk_gujuo(GIFT_PREFER, lambda: held_id(LQ_ID.GILDED_TOTEM) > 0, 120000)
SEEDS_AGAIN_PREFER = ['I need more Yommi tree seeds.', 'Ok, thanks...']


def ask_for_more_seeds(log):
    """Ask Ungadulu for a fresh set of seeds after the last one withered."""
    if held_id(LQ_ID.YOMMI_SEEDS) > 0 or held_id(LQ_ID.YOMMI_SEEDS_GERM) > 0:
        return True
    shaman = npcs.query().name(LQ_NPC.UNGADULU).within(12).nearest()
    if not shaman:
        log('Ungadulu is not in range for more seeds')
        return False
    if not (shaman.interact('Talk-to')):
        return False
    _result11 = yield from drive_until(lambda: held_id(LQ_ID.YOMMI_SEEDS) > 0, SEEDS_AGAIN_PREFER, log, 90000)
    return _result11

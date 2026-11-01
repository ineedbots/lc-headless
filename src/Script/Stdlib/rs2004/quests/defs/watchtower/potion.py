"""Ported from rs2b0t's src/bot/api/ai/quests/defs/watchtower/potion.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.entities import npcs
from rs2004.items import inventory
from rs2004.quests.defs.watchtower.areas import WT_ITEM, WT_NPC
from rs2004.quests.defs.watchtower.journal import WATCHTOWER_STAGE
from rs2004.quests.defs.watchtower.tower import climb_to_wizard
from rs2004.quests.exec.primitives import drive_dialog

__all__ = ['grind_bat_bones', 'brew_ogre_potion', 'infuse_potion']

def item(id):
    _v1 = ([entry for entry in inventory.items() if entry.id == id] or [None])[0]
    return (_v1 if _v1 is not None else None)


def held_id(id):
    return sum([entry.count for entry in [entry for entry in inventory.items() if entry.id == id]])


def combine(use_id, onto_id, produces_id, log):
    source = item(use_id)
    target = item(onto_id)
    if not source or not target:
        log(f'cannot combine {use_id} with {onto_id} — one of them is missing')
        return False
    if not (source.use_on(target)):
        return False
    _result2 = yield from execution.delay_until(lambda: held_id(produces_id) > 0, 8000)
    return _result2


def grind_bat_bones(log):
    if held_id(WT_ITEM.GROUND_BAT_BONES.id) > 0:
        return True
    _result3 = yield from combine(WT_ITEM.PESTLE.id, WT_ITEM.BAT_BONES.id, WT_ITEM.GROUND_BAT_BONES.id, log)
    return _result3


def brew_ogre_potion(log):
    """Guam, then jangerberries, then ground bat bones. Any other pairing calls potion_explosion: both items are destroyed and it costs 5 damage."""
    if held_id(WT_ITEM.OGRE_POTION.id) > 0:
        return True
    if held_id(WT_ITEM.GUAM_VIAL.id) == 0 and held_id(WT_ITEM.GUAM_JANGER_VIAL.id) == 0:
        _w4 = yield from combine(WT_ITEM.GUAM_LEAF.id, WT_ITEM.VIAL_WATER.id, WT_ITEM.GUAM_VIAL.id, log)
        if not (_w4):
            return False
    if held_id(WT_ITEM.GUAM_JANGER_VIAL.id) == 0:
        _w5 = yield from combine(WT_ITEM.JANGERBERRIES.id, WT_ITEM.GUAM_VIAL.id, WT_ITEM.GUAM_JANGER_VIAL.id, log)
        if not (_w5):
            return False
    _result6 = yield from combine(WT_ITEM.GROUND_BAT_BONES.id, WT_ITEM.GUAM_JANGER_VIAL.id, WT_ITEM.OGRE_POTION.id, log)
    return _result6


def infuse_potion(log):
    _w7 = yield from climb_to_wizard(WATCHTOWER_STAGE.LEARNED_POTION, log)
    if not (_w7):
        return False
    potion = item(WT_ITEM.OGRE_POTION.id)
    wizard = npcs.query().name(WT_NPC.WIZARD).nearest()
    if not potion or not wizard or not (potion.use_on(wizard)):
        return False
    yield from drive_dialog([], log)
    _result8 = yield from execution.delay_until(lambda: held_id(WT_ITEM.MAGIC_OGRE_POTION.id) > 0, 15000)
    return _result8

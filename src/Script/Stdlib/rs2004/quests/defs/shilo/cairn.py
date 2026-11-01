"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/cairn.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.items import inventory
from rs2004.quests.defs.shilo.areas import SV_ITEM, SV_LOC, SV_TILE
from rs2004.quests.defs.shilo.journal import SHILO_QUEST
from rs2004.quests.defs.shilo.scene import drive_until, held_id, here, prompt_loc, settle_scene, use_on_loc
from rs2004.tabs import quests

__all__ = ['leave_bervirius_tomb', 'search_bervirius_dolmen', 'craft_bone_beads', 'craft_dead_beads', 'craft_bone_key', 'deliver_corpse']

YES_CRAWL = ['Yes Please, I can think of nothing nicer!']
YES_NOTES = ["Yes, I'll make some notes."]


def enter_bervirius_tomb(log):
    """Crawling in needs the tattered scroll read; the pack routes over the log bridge."""
    if here() == 'berviriusTomb':
        return True
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.WELL_STACKED_ROCKS,
        'op': 'Search',
        'near': SV_TILE.WELL_STACKED_ROCKS,
        'prefer': YES_CRAWL,
        'expect': lambda: here() == 'berviriusTomb',
    }), log)
    if ok:
        yield from settle_scene()
    return ok


def leave_bervirius_tomb(log):
    if here() != 'berviriusTomb':
        return True
    ok = yield from prompt_loc(Record({
        'name': SV_LOC.HANDHOLDS,
        'op': 'Climb',
        'near': SV_TILE.HANDHOLDS,
        'expect': lambda: here() != 'berviriusTomb',
    }), log)
    if ok:
        yield from settle_scene()
    return ok


# Why: The first search gives three items and sets `used_dolmen_paper`; later searches request papyrus and charcoal.
def search_bervirius_dolmen(log):
    """Search the Bervirius dolmen."""
    if held_id(SV_ITEM.SWORD_POMMEL.id) > 0 or held_id(SV_ITEM.BONE_BEADS.id) > 0 or held_id(SV_ITEM.DEAD_BEADS.id) > 0:
        return True
    _w1 = yield from enter_bervirius_tomb(log)
    if not (_w1):
        return False
    _result2 = yield from prompt_loc(Record({
        'name': SV_LOC.BERVIRIUS_DOLMEN,
        'op': 'Search',
        'near': SV_TILE.BERVIRIUS_DOLMEN,
        'prefer': YES_NOTES,
        'expect': lambda: held_id(SV_ITEM.SWORD_POMMEL.id) > 0,
    }), log)
    return _result2


def use_item_on_item(source_id, target_id, want, log):
    if held_id(want) > 0:
        return True
    source = ([item for item in inventory.items() if item.id == source_id] or [None])[0]
    target = ([item for item in inventory.items() if item.id == target_id] or [None])[0]
    if not source or not target:
        log(f'missing {source_id} or {target_id} for the craft')
        return False
    if not (source.use_on(target)):
        return False
    _result3 = yield from drive_until(lambda: held_id(want) > 0, [], log)
    return _result3


def craft_bone_beads(log):
    return use_item_on_item(SV_ITEM.CHISEL.id, SV_ITEM.SWORD_POMMEL.id, SV_ITEM.BONE_BEADS.id, log)


def craft_dead_beads(log):
    """Refused until the crumpled scroll has been read, whatever the Crafting level."""
    return use_item_on_item(SV_ITEM.BRONZE_WIRE.id, SV_ITEM.BONE_BEADS.id, SV_ITEM.DEAD_BEADS.id, log)


def craft_bone_key(log):
    """Refused until the carved doors have been searched, whatever the Crafting level."""
    return use_item_on_item(SV_ITEM.CHISEL.id, SV_ITEM.BONE_SHARD.id, SV_ITEM.BONE_KEY.id, log)


def deliver_corpse(log):
    """The quest ends by laying Rashiliyia beside her son on the Bervirius dolmen."""
    _w4 = yield from enter_bervirius_tomb(log)
    if not (_w4):
        return False
    _result5 = yield from use_on_loc(SV_ITEM.RASH_CORPSE.id, Record({'name': SV_LOC.BERVIRIUS_DOLMEN, 'near': SV_TILE.BERVIRIUS_DOLMEN}), [], lambda: quests.status(SHILO_QUEST) == 'complete', log)
    return _result5

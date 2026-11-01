"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/cook.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import reader
from rs2004.items import inventory
from rs2004.quests.defs.chompybird.areas import CB_ID, CB_LOC_ID, CB_NAME, CB_NPC, CB_TILE
from rs2004.quests.defs.chompybird.arrows import walk_to
from rs2004.quests.defs.chompybird.dialogue import box_text, clear_box, talk_boxes
from rs2004.quests.defs.chompybird.supplies import held_id
from rs2004.quests.exec.prompts import settle_scene

__all__ = ['cook_state', 'seasoning_step', 'ask_kids', 'cook_chompy']

def held(id):
    return inventory.count_by_id(id)


cook_state = Record({'kids_asked': False})
# Why: Rantz rolls his own flavour when the carcass is shown and the kids roll theirs when asked, and none of the 3 is on the wire, so all 6 candidates are carried.
# Why: the order is the round trip east of Rantz and then west of him, since taking them in pairs alternates across 300 tiles of Feldip.
SEASONINGS = [
    Record({'id': CB_ID.POTATO, 'name': CB_NAME.POTATO, 'loc': 312, 'tile': CB_TILE.POTATO}),
    Record({'id': CB_ID.CABBAGE, 'name': CB_NAME.CABBAGE, 'loc': 1161, 'tile': CB_TILE.CABBAGE}),
    Record({'id': CB_ID.EQUA, 'name': CB_NAME.EQUA, 'tile': CB_TILE.EQUA}),
    Record({'id': CB_ID.ONION, 'name': CB_NAME.ONION, 'loc': 3366, 'tile': CB_TILE.ONION}),
    Record({'id': CB_ID.TOMATO, 'name': CB_NAME.TOMATO, 'tile': CB_TILE.TOMATO}),
    Record({'id': CB_ID.DOOGLE, 'name': CB_NAME.DOOGLE, 'tile': CB_TILE.DOOGLE}),
]


# Why: the cabbage loc carries no `name=`, so the client menu reads "null" and a name query finds nothing; every patch matches by loc id.
def pick_patch(loc_id, name, item_id, tile):
    """Pick one vegetable off its patch."""

    def pick(log):
        patch_id = loc_id
        crop = item_id
        walked = yield from walk_to(tile, 4, log)
        if not walked:
            return False
        yield from settle_scene()
        patch = locs.query().where(lambda l: l.id == patch_id).action('Pick').within(10).nearest()
        if not patch:
            log(f'no {name} patch in reach of ({tile.x},{tile.z})')
            return False
        before = held(crop)
        if not (patch.interact('Pick')):
            return False
        picked = yield from execution.delay_until(lambda: held(crop) > before, 10000)
        return picked
    return pick


def seasoning_step(snap):
    """The next seasoning to fetch, or null once all 6 are carried."""
    missing = ([s for s in SEASONINGS if held_id(snap, s.id) == 0] or [None])[0]
    if not missing:
        return None
    if missing.loc is not None:
        return Record({
            'kind': 'custom',
            'name': f'pick a {missing.name.lower()}',
            'run': pick_patch(missing.loc, missing.name, missing.id, missing.tile),
        })
    return Record({'kind': 'grab_ground', 'item': missing.name, 'anchor': missing.tile, 'wait_if_missing': True})


def ask_kids(log):
    """Ask both children what they want on the chompy; that sets their varbits."""
    for npc in [CB_NPC.BUGS, CB_NPC.FYCIE]:
        _w4 = yield from walk_to((CB_TILE.BUGS if npc == CB_NPC.BUGS else CB_TILE.FYCIE), 4, log)
        if not (_w4):
            return False
        yield from settle_scene()
        _w5 = yield from talk_boxes(npc, Record({'ms': 30000}), log)
        if not (_w5):
            log(f'{npc} did not answer')
            return False
    cook_state.kids_asked = True
    return True


def needs_kids(text):
    return 'what bugs wants' in text or 'what fycie wants' in text


def needs_ingredients(text):
    return "don't have all the ingredients" in text


# Why: the spit is 6 locs sharing one display name and only the empty one carries the `oplocu` a raw chompy needs.
def cook_chompy(log):
    """Roast the chompy with all 3 seasonings on the ogre spit."""
    if held(CB_ID.SEASONED_CHOMPY) > 0:
        return True
    _w6 = yield from walk_to(CB_TILE.SPIT, 2, log)
    if not (_w6):
        return False
    yield from settle_scene()
    yield from clear_box()
    spit = locs.query().where(lambda l: l.id == CB_LOC_ID.SPIT_EMPTY).within(8).nearest()
    chompy = ([i for i in inventory.items() if i.id == CB_ID.RAW_CHOMPY] or [None])[0]
    if not spit or not chompy:
        log(('no Raw chompy to roast' if spit else 'the ogre spit-roast is still busy'))
        return False
    if not (chompy.use_on(spit)):
        return False
    settled = yield from execution.delay_until(lambda: held(CB_ID.SEASONED_CHOMPY) > 0 or held(CB_ID.RUINED_CHOMPY) > 0 or (reader.modals().main != -1 and (needs_kids(box_text()) or needs_ingredients(box_text()))), 25000)
    if reader.modals().main != -1 and needs_kids(box_text()):
        log('the spit wants the kids asked first')
        cook_state.kids_asked = False
    yield from clear_box()
    if held(CB_ID.RUINED_CHOMPY) > 0 and held(CB_ID.SEASONED_CHOMPY) == 0:
        log('the chompy burnt — another bird is needed')
        ruined = ([i for i in inventory.items() if i.id == CB_ID.RUINED_CHOMPY] or [None])[0]
        if ruined is not None:
            ruined.interact('Drop')
    return settled and held(CB_ID.SEASONED_CHOMPY) > 0

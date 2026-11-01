"""Ported from rs2b0t's src/bot/api/ai/quests/defs/fremenniktrials/bard.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.messages import game_messages
from rs2004.quests.defs.fremenniktrials.areas import ASKELADDEN, FT_ID, FT_LOC, FT_TILE, LALLI, OLAF, on_stage, past_backstage
from rs2004.quests.defs.fremenniktrials.supplies import combine, gather_axe, gather_knife, gather_shark, held_id, talk_until, walk_to
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.primitives import drive_dialog, talk_through
from rs2004.quests.exec.prompts import settle_scene, use_on_loc
from rs2004.reach import reach

__all__ = ['reset_bard_latch', 'bard_step']

TRIAL_WON = "completed the Bard's Trial"
# Why: Askeladden only parts with a pet rock once Lalli has named him, and no journal line separates those 2 states.
# Why: the latch is process state; a fresh session re-asks Lalli, which the content treats as a no-op.
lalli_asked = False


def reset_bard_latch():
    global lalli_asked
    lalli_asked = False


def bard_step(snap):
    """Olaf's trial: cut the musical tree, carve and string a lyre, have Fossegrimen enchant it, then play it on the longhall stage."""
    if has_flag(snap.progress, 'bard-done'):
        return None
    if not has_flag(snap.progress, 'bard-started'):
        return Record({'kind': 'talk', 'stop': OLAF(['Yes'])})
    if held_id(snap, FT_ID.ENCHANTED_LYRE) > 0:
        return Record({'kind': 'custom', 'name': 'play the lyre on the longhall stage', 'run': perform})
    if held_id(snap, FT_ID.LYRE) > 0:
        _v1 = gather_shark(snap)
        return (_v1 if _v1 is not None else Record({'kind': 'custom', 'name': 'offer the shark to Fossegrimen', 'run': offer_shark}))
    if held_id(snap, FT_ID.UNSTRUNG_LYRE) > 0 and held_id(snap, FT_ID.GOLDEN_WOOL) > 0:
        return combine(FT_ID.GOLDEN_WOOL, FT_ID.UNSTRUNG_LYRE, FT_ID.LYRE, 'string the lyre with golden wool')
    if held_id(snap, FT_ID.GOLDEN_FLEECE) > 0:
        return Record({'kind': 'custom', 'name': 'spin the fleece at the Seers spinning wheel', 'run': spin_fleece})
    if held_id(snap, FT_ID.UNSTRUNG_LYRE) == 0:
        if held_id(snap, FT_ID.BRANCH) > 0:
            _v2 = gather_knife(snap)
            return (_v2 if _v2 is not None else combine(FT_ID.KNIFE, FT_ID.BRANCH, FT_ID.UNSTRUNG_LYRE, 'carve the branch into an unstrung lyre'))
        _v3 = gather_axe(snap)
        return (_v3 if _v3 is not None else Record({
            'kind': 'pick_loc',
            'loc': 'Swaying tree',
            'op': 'Cut-branch',
            'item': 'Branch',
            'anchor': FT_TILE.MUSICAL_TREE,
        }))
    return fleece_step(snap)


# Why: Lalli only trades the fleece for a bowl of stone soup, and the stone is Askeladden's pet rock.
def fleece_step(snap):
    if held_id(snap, FT_ID.PET_ROCK) == 0:
        if not lalli_asked:
            return Record({'kind': 'custom', 'name': 'ask Lalli who traded him the wool', 'run': ask_lalli})
        return Record({'kind': 'custom', 'name': 'take a pet rock from Askeladden', 'run': take_pet_rock})
    for crop in SOUP_CROPS:
        if not (crop.name.lower() in snap.inv):
            return Record({'kind': 'pick_loc', 'loc': crop.name, 'op': 'Pick', 'item': crop.name, 'anchor': crop.patch})
    return Record({'kind': 'custom', 'name': 'cook stone soup and take the golden fleece', 'run': stone_soup})


def ask_lalli(log):
    global lalli_asked
    _w4 = yield from walk_to(LALLI([]).anchor, 2, log)
    if not (_w4):
        return False
    _w5 = yield from talk_through('Lalli', ['Other human?'], log)
    if not (_w5):
        return False
    lalli_asked = True
    return True


def take_pet_rock(log):
    global lalli_asked
    got = yield from talk_until('Askeladden', ASKELADDEN([]).anchor, [], lambda: inventory.count_by_id(FT_ID.PET_ROCK) > 0, log, 45000)
    if not got:
        log('Askeladden kept his rocks — going back to Lalli first')
        lalli_asked = False
    return got


SOUP_CROPS = [
    Record({'id': FT_ID.CABBAGE, 'name': 'Cabbage', 'patch': FT_TILE.CABBAGE_PATCH}),
    Record({'id': FT_ID.POTATO, 'name': 'Potato', 'patch': FT_TILE.POTATO_PATCH}),
    Record({'id': FT_ID.ONION, 'name': 'Onion', 'patch': FT_TILE.ONION_PATCH}),
]
SOUP = [Record({'id': FT_ID.PET_ROCK, 'name': 'Pet rock'})] + list([(Record({'id': crop.id, 'name': crop.name})) for crop in SOUP_CROPS])


def stone_soup(log):
    for part in SOUP:
        if inventory.count_by_id(part.id) == 0:
            continue
        dropped = yield from use_on_loc(part.id, Record({'name': "Lalli's Stew", 'near': FT_TILE.TROLL_CAULDRON, 'id': FT_LOC.TROLL_CAULDRON}), [], lambda: inventory.count_by_id(part.id) == 0, log)
        if not dropped:
            log(f'the cauldron would not take the {part.name}')
            return False
    _result6 = yield from talk_until('Lalli', FT_TILE.TROLL_CAULDRON, [], lambda: inventory.count_by_id(FT_ID.GOLDEN_FLEECE) > 0, log, 45000)
    return _result6


# Why: Rellekka's own wheel refuses anyone who isn't a Fremennik yet, so the fleece is spun in Seers' Village.
def spin_fleece(log):
    _w7 = yield from walk_to(FT_TILE.SPINNING_WHEEL, 2, log)
    if not (_w7):
        return False
    yield from settle_scene()
    wheel = locs.query().name('Spinning wheel').within(8).nearest()
    fleece = ([i for i in inventory.items() if i.id == FT_ID.GOLDEN_FLEECE] or [None])[0]
    if not wheel or not fleece:
        log('no spinning wheel or no fleece in range')
        return False
    if not (fleece.use_on(wheel)):
        return False
    _result8 = yield from execution.delay_until(lambda: inventory.count_by_id(FT_ID.GOLDEN_WOOL) > 0, 10000)
    return _result8


def offer_shark(log):
    _result9 = yield from use_on_loc(FT_ID.RAW_SHARK, Record({'name': 'Strange altar', 'near': FT_TILE.LAKE_ALTAR, 'id': FT_LOC.LAKE_ALTAR}), [], lambda: inventory.count_by_id(FT_ID.ENCHANTED_LYRE) > 0, log)
    return _result9


# Why: the door tile is the loc's own tile, so the approach stops beside it and the first Open lands before the walk has settled.
def open_backstage(log):
    for i in range(3):
        yield from settle_scene()
        opened = yield from reach.loc_op('Door', 'Open', FT_TILE.BACKSTAGE_DOOR, lambda: past_backstage(game.tile()), id=FT_LOC.BACKSTAGE_DOOR, log=log)
        if opened == 'done' or past_backstage(game.tile()):
            return True
    return False


def perform(log):
    if not on_stage(game.tile()):
        # Why: the approach walk can land west of the door already, and clicking Open from there fails a crossing that's done.
        if not past_backstage(game.tile()):
            _w10 = yield from open_backstage(log)
            if not (_w10):
                log('the bouncer would not let the lyre past')
                return False
            # Why: the door queues the bouncer's line, and an open chat modal swallows the walk onto the stage.
            yield from drive_dialog([], log)
        _w11 = yield from walk_to(FT_TILE.STAGE, 1, log)
        if not (_w11):
            return False
    yield from settle_scene()
    lyre = ([i for i in inventory.items() if i.id == FT_ID.ENCHANTED_LYRE] or [None])[0]
    if not lyre:
        return False
    mark = game_messages.mark()
    if not (lyre.interact('Play')):
        return False
    # Why: the performance is 4 verses of `say` with 3-tick gaps, and the vote lands only on the last one.
    _result12 = yield from execution.delay_until(lambda: game_messages.saw_since(mark, TRIAL_WON), 60000)
    return _result12

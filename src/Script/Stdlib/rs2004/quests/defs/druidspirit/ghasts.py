"""Ported from rs2b0t's src/bot/api/ai/quests/defs/druidspirit/ghasts.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs, npcs
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.druidspirit.areas import NS_ID, NS_TILE
from rs2004.quests.defs.druidspirit.camp import pickable, stand_beside
from rs2004.quests.exec.prompts import held_id, settle_scene
from rs2004.traversal import traversal

__all__ = ['bloom_with_sickle', 'fill_pouch', 'kill_ghast']

GHAST = 'Ghast'
POUCH_ITEMS = [NS_ID.PEAR, NS_ID.STEM, NS_ID.FUNGI]


def harvest_held():
    return sum([held_id(id) for id in POUCH_ITEMS])


# Why: `Cast Bloom` affects one random loc within eight tiles, so cast beside a valid target until one blooms.
def bloom_with_sickle(log):
    """Bloom and harvest until the pouch has 3 items to eat."""
    if skills.level('prayer') > 0 and skills.effective('prayer') == 0:
        log('no prayer points left — the blessed sickle cannot bloom')
        return False
    for cycle in range(12):
        if not (harvest_held() < 3):
            break
        ready = pickable()
        if ready:
            before = harvest_held()
            loc = locs.query().name(ready.name).action(ready.op).within(10).nearest()
            if loc and (loc.interact(ready.op)):
                yield from execution.delay_until(lambda: harvest_held() > before, 6000)
            continue
        _w1 = yield from stand_beside(log)
        if not (_w1):
            return False
        sickle = ([i for i in inventory.items() if i.id == NS_ID.SICKLE_BLESSED] or [None])[0]
        if not sickle:
            log('no Silver sickle(b) held')
            return False
        if not (sickle.interact('Cast Bloom')):
            return False
        yield from execution.delay_until(lambda: pickable() is not None, 6000)
    return harvest_held() >= 3


def fill_pouch(log):
    """3 blossomed items into the pouch."""
    if harvest_held() < 3:
        log(f'only {harvest_held()} harvest item(s) held — the pouch takes three')
        return False
    pouch = ([i for i in inventory.items() if i.id == NS_ID.POUCH_EMPTY or i.id == NS_ID.POUCH] or [None])[0]
    if not pouch:
        log('no druid pouch held')
        return False
    before = held_id(NS_ID.POUCH)
    if not (pouch.interact('Fill')):
        return False
    _result2 = yield from execution.delay_until(lambda: held_id(NS_ID.POUCH) > before, 6000)
    return _result2


# Why: a ghast is invisible until a pouch charge is spent on it, and `Attack` is refused outright below the pouch stage.
# Why: the pouch use is an `opnpcu` only refused while something else has you in combat, so the loop pops the ghast itself.
def kill_ghast(log):
    """Pop one invisible ghast with the pouch and kill what appears."""
    if held_id(NS_ID.POUCH) == 0:
        log('no charged druid pouch — nothing can make a ghast visible')
        return False

    def visible():
        return npcs.query().name(GHAST).action('Attack').within(12).nearest()

    if not visible():
        hidden = npcs.query().name(GHAST).within(12).nearest()
        if not hidden:
            _w3 = yield from traversal.walk_resilient(NS_TILE.GHAST_HUNT, radius=3, attempts=3, timeout_ms=180000, log=log)
            if not (_w3):
                return False
            yield from settle_scene()
            log('no ghast in the scene — moving through the swamp until one hunts')
            return False
        pouch = ([i for i in inventory.items() if i.id == NS_ID.POUCH] or [None])[0]
        if not pouch or not (pouch.use_on(hidden)):
            return False
        _w4 = yield from execution.delay_until(lambda: visible() is not None, 8000)
        if not (_w4):
            log('the pouch charge did not make a ghast visible')
            return False
    ghast = visible()
    if not ghast:
        return False
    index = ghast.index
    if not (ghast.interact('Attack')):
        return False
    _w5 = yield from execution.delay_until(lambda: game.in_combat(), 6000)
    if not (_w5):
        return False
    _result6 = yield from execution.delay_until(lambda: not any([n.index == index for n in npcs.all()]), 90000)
    return _result6

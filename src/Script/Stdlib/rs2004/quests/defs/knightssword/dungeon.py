"""Ported from rs2b0t's src/bot/api/ai/quests/defs/knightssword/dungeon.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.mining import QUEST_ROCK_TYPES
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import locs
from rs2004.game import game
from rs2004.items import inventory
from rs2004.navigation import navigator
from rs2004.quests.defs.knightssword.areas import BLURITE_ROCKS, KS_ID, KS_TILE
from rs2004.quests.exec.primitives import is_underground
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal


__all__ = ['mine_blurite']

BLURITE_IDS = set(QUEST_ROCK_TYPES.get('Blurite'))
MINE_ATTEMPTS = 30


def nearest_reachable_rock(log):
    """The rocks sit past the ice warriors in a cave the crow distance doesn't describe, so the pick is a pathfind."""
    here = game.tile()
    if not here:
        return None
    for rock in sorted(list(BLURITE_ROCKS), key=lambda a: a.distance_to(here)):
        if (navigator.find_path(here, rock)).ok:
            return rock
    log('no blurite rock answered a path')
    return None
    if False:
        yield


def run(log):
    here = game.tile()
    if not here or not is_underground(here):
        _w1 = yield from traversal.walk_resilient(KS_TILE.LADDER_BOTTOM, radius=4, attempts=4, timeout_ms=360000, log=log)
        if not (_w1):
            log('could not get down into the Asgarnian Ice Dungeon')
            return False
        yield from settle_scene()
    rock = yield from nearest_reachable_rock(log)
    if not rock:
        return False
    for i in range(MINE_ATTEMPTS):
        # Sustain only runs where a step calls it, and this step takes hits.
        yield from sustain.run()
        if inventory.count_by_id(KS_ID.BLURITE_ORE) > 0:
            return True
        target = locs.query().where(lambda l: (l.id in BLURITE_IDS)).action('Mine').within(12).nearest()
        if not target:
            _w2 = yield from traversal.walk_resilient(rock, radius=2, attempts=2, timeout_ms=180000, log=log)
            if not (_w2):
                return False
            yield from settle_scene()
            continue
        target.interact('Mine')
        # A hit can interrupt the swing. Keep eating and retry after one bronze-pick cycle.
        for tick in range(12):
            yield from sustain.run()
            if inventory.count_by_id(KS_ID.BLURITE_ORE) > 0:
                return True
            yield from execution.delay_ticks(1)
    log('never landed a blurite ore')
    return False


# Why: an ice warrior landing a hit makes the bot swing back with auto-retaliate on, and the swing cancels the mine.
# Why: the trip is one ore and out, so no reflex is wanted.
def mine_blurite(log):
    """Mine one blurite ore and leave."""
    if inventory.count_by_id(KS_ID.BLURITE_ORE) > 0:
        return True
    game.set_auto_retaliate(False)
    try:
        _result3 = yield from run(log)
    except Exception as e:
        game.set_auto_retaliate(True)
        raise e

    game.set_auto_retaliate(True)

    return _result3

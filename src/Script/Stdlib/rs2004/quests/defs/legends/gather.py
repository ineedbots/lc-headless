"""Ported from rs2b0t's src/bot/api/ai/quests/defs/legends/gather.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.items import inventory
from rs2004.quests.defs.legends.areas import GEM_CUTS, LQ_ID, LQ_TILE
from rs2004.quests.defs.legends.scene import held_id, prompt_loc, settle_scene, use_on_loc
from rs2004.traversal import traversal

__all__ = ['mine_gem', 'smelt_gold_bar', 'BRAVERY_HERBS', 'pick_herb', 'identify_herb']

GEM_ROCK_ID = 2111
MINE_MS = 240000


def uncut_held():
    return sum([held_id(gem.uncut) for gem in GEM_CUTS])


# Why: the rock rolls one of 7 gems, opal 60/128 down to diamond 4/128, so waiting for a named uncut gem times out on nearly every swing.
# Why: Any uncut gem confirms one mining attempt; `decide()` handles the remaining types.
def mine_gem(log):
    """Mine the Shilo gem rocks until one more uncut gem is in the pack."""
    before = uncut_held()
    _w1 = yield from traversal.walk_resilient(LQ_TILE.GEM_ROCKS, radius=3, attempts=3, timeout_ms=240000, log=log)
    if not (_w1):
        return False
    yield from settle_scene()
    deadline = _core.step_time() + MINE_MS
    while _core.step_time() < deadline:
        if uncut_held() > before:
            return True
        rock = locs.query().where(lambda l: l.id == GEM_ROCK_ID).action('Mine').within(10).nearest()
        if not rock:
            # Every rock is depleted; they come back on a 200-tick respawn.
            yield from execution.delay_ticks(10)
            continue
        if rock.interact('Mine'):
            yield from execution.delay_until(lambda: uncut_held() > before, 20000)
        yield from execution.delay_ticks(1)
    log('no gem in four minutes at the Shilo rocks')
    return False


def smelt_gold_bar(log):
    """Smelt one gold ore into a bar at the East Ardougne furnace."""
    before = held_id(LQ_ID.GOLD_BAR)
    if held_id(LQ_ID.GOLD_ORE) == 0:
        log('no gold ore to smelt')
        return False
    _w2 = yield from traversal.walk_resilient(LQ_TILE.FURNACE, radius=3, attempts=3, timeout_ms=180000, log=log)
    if not (_w2):
        return False
    yield from settle_scene()
    # Why: the furnace's own Smelt op opens the bar-picker interface and waits, so the ore goes on the furnace and smelts where it lands.
    _result3 = yield from use_on_loc(LQ_ID.GOLD_ORE, Record({'name': 'Furnace', 'near': LQ_TILE.FURNACE, 'within': 10}), [], lambda: held_id(LQ_ID.GOLD_BAR) > before, log)
    return _result3


BRAVERY_HERBS = [
    Record({
    'unid_id': LQ_ID.UNID_SNAKE_WEED,
    'id': LQ_ID.SNAKE_WEED,
    'name': 'Snake weed',
    'loc': 'Marshy jungle vine',
    'stand': LQ_TILE.SNAKE_WEED,
}),
    Record({
    'unid_id': LQ_ID.UNID_ARDRIGAL,
    'id': LQ_ID.ARDRIGAL,
    'name': 'Ardrigal',
    'loc': 'Palm tree',
    'stand': LQ_TILE.ARDRIGAL,
}),
]


def has_item(id):
    return lambda: held_id(id) > 0


def pick_herb(herb):
    """Search a herb's own loc until the unid is in the pack."""

    def run(log):
        if held_id(herb.id) > 0 or held_id(herb.unid_id) > 0:
            return True
        picked = yield from prompt_loc(Record({'name': herb.loc, 'op': 'Search', 'near': herb.stand, 'expect': has_item(herb.unid_id)}), log)
        return picked
    return run


def identify_herb(herb):
    def run(log):
        if held_id(herb.id) > 0:
            return True
        unid = ([item for item in inventory.items() if item.id == herb.unid_id] or [None])[0]
        if not unid:
            log(f'no unidentified {herb.name} in the pack')
            return False
        if not (unid.interact('Identify')):
            return False
        known = yield from execution.delay_until(has_item(herb.id), 6000)
        return known
    return run

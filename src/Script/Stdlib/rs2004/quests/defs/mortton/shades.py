"""Ported from rs2b0t's src/bot/api/ai/quests/defs/mortton/shades.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.catalogs.tasks import sustain
from rs2004.entities import ground_items, npcs
from rs2004.execution import event_signal
from rs2004.game import game, skills
from rs2004.items import inventory
from rs2004.quests.defs.mortton.areas import SM_ID, SM_NPC_ID, SM_TILE
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['REMAINS_WANTED', 'hunt_shade']

REMAINS_WANTED = 5
SEARCH_RADIUS = 15
LOOT_RADIUS = 12
EAT_AT_MISSING = 12
FIGHT_GUARD = 220
# Why: a Loar Shadow becomes a Loar Shade once attacked, keeping its index, so the pair is one target.
SHADE_IDS = [SM_NPC_ID.SHADOW, SM_NPC_ID.SHADE]


def hungry():
    max_ = skills.level('hitpoints')
    return max_ > 0 and skills.effective('hitpoints') <= max_ - EAT_AT_MISSING


def target():
    return npcs.query().where(lambda n: (n.id in SHADE_IDS)).action('Attack').where(lambda n: not n.targets_another_player()).within(SEARCH_RADIUS).nearest()


def remains_on_floor():
    return ground_items.query().where(lambda g: g.id == SM_ID.REMAINS).within(LOOT_RADIUS).nearest()


def loot():
    """Take one set of remains off the floor."""
    drop = remains_on_floor()
    if not drop:
        return False
    before = inventory.count_by_id(SM_ID.REMAINS)
    if not (drop.interact('Take')):
        return False
    _result1 = yield from execution.delay_until(lambda: inventory.count_by_id(SM_ID.REMAINS) > before, 6000)
    return _result1


# Why: the kill and the loot are one step, since `decide` cannot see the floor and a set of remains left there is a sixth shade to kill.
def hunt_shade(log):
    """Kill one shade and pocket what it leaves."""
    _w2 = yield from loot()
    if _w2:
        return True
    shade = target()
    if not shade:
        _w3 = yield from traversal.walk_resilient(SM_TILE.TOWN, radius=4, attempts=3, timeout_ms=180000, log=log)
        if not (_w3):
            return False
        yield from settle_scene()
        shade = target()
        if not shade:
            log('no Loar Shadow in the streets yet — they respawn on their own timer')
            yield from execution.delay_ticks(4)
            return False
    game.set_auto_retaliate(True)
    index = shade.index
    swings = 0
    last_tick = -1
    for i in range(FIGHT_GUARD):
        if event_signal.pending():
            log('yielding to a random event mid-shade')
            return False
        now = game.tick()
        if now == last_tick:
            yield from execution.delay_ticks(1)
            continue
        last_tick = now
        if not any([n.index == index for n in npcs.all()]):
            # The corpse drops on the tile it sank on; give the server a tick to place it.
            yield from execution.delay_ticks(1)
            _w4 = yield from loot()
            return (_w4) or swings > 0
        if hungry():
            yield from sustain.run()
            continue
        if game.in_combat():
            yield from execution.delay_ticks(1)
            continue
        live = ([n for n in npcs.all() if n.index == index] or [None])[0]
        if live and (live.interact('Attack')):
            swings += 1
        yield from execution.delay_ticks(1)
    log(f'gave up on Loar Shadow {index} after {swings} attacks')
    return False

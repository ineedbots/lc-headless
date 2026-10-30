"""Ported from rs2b0t's src/bot/api/ai/quests/defs/witchshouse/patrol.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import npcs
from rs2004.execution import event_signal
from rs2004.game import direct_navigator, game, reader
from rs2004.geometry import Tile
from rs2004.traversal import traversal
from rs2004.quests.defs.witchshouse.areas import in_garden, WH_TILE
from rs2004.quests.engine.types import QuestModule, QuestProgress
from rs2004.quests.data import quest_record

__all__ = ['GARDEN_ENTRY', 'FOUNTAIN_STAND', 'sheltered', 'garden_legs', 'observe_witch', 'safe_crossing', 'walk_garden', 'GARDEN_SHED']

GARDEN_ENTRY = Tile(2901, 3465, 0)
FOUNTAIN_STAND = Tile(2911, 3469, 0)
SOUTH_HEDGES = set([2903, 2907, 2908, 2909, 2915, 2916, 2917, 2923, 2924, 2925, 2929, 2930, 2931])
MOVEMENT_GRACE = 4
SNAPSHOT_GRACE = 2
NORTH_HEDGES = set([2912, 2913, 2914, 2919, 2920, 2921, 2926, 2927, 2928, 2932])


def sheltered(tile):
    return tile.level == 0 and (tile.z >= 3467 or (tile.x == 2901 and tile.z >= 3460 and tile.z <= 3465) or (tile.x == 2933 and tile.z == 3463) or (tile.z == 3460 and (tile.x in SOUTH_HEDGES)) or (tile.z == 3466 and (tile.x in NORTH_HEDGES)))


ROUTE = [GARDEN_ENTRY]
for x, z in [[2901, 3460], [2933, 3460], [2933, 3466], [2912, 3466], [2912, 3467], [2911, 3467], [2911, 3469]]:
    while (ROUTE[-1] if len(ROUTE) > 0 else None).x != x or (ROUTE[-1] if len(ROUTE) > 0 else None).z != z:
        last = (ROUTE[-1] if len(ROUTE) > 0 else None)
        ROUTE.append(Tile(last.x + (1 if x - last.x > 0 else (-1 if x - last.x < 0 else 0)), last.z + (1 if z - last.z > 0 else (-1 if z - last.z < 0 else 0)), 0))


def position():
    return game.tile()


def same(a, b):
    return not not a and a.level == b.level and a.x == b.x and a.z == b.z


def garden_legs(from_, to):
    index = ([_i for _i, tile in enumerate(ROUTE) if same(from_, tile)] or [-1])[0]
    end = ([_i for _i, tile in enumerate(ROUTE) if same(to, tile)] or [-1])[0]
    if index < 0 or end < 0:
        return None
    direction = (1 if end - index > 0 else (-1 if end - index < 0 else 0))
    legs = []
    while index != end:
        leg = [ROUTE[index]]
        covered = sheltered(ROUTE[index]) and sheltered(ROUTE[index + direction])
        while True:
            index += direction
            leg.append(ROUTE[index])
            if not (index != end and ((sheltered(ROUTE[index + direction]) if covered else not sheltered(ROUTE[index])))):
                break
        legs.append(leg)
    return legs


def observe_witch(previous, tile, tick):
    if not tile or tile.level != 0 or tile.z != 3463 or tile.x < 2904 or tile.x > 2930:
        return None
    direction = 0
    if previous and tick == previous.tick + 1:
        dx = tile.x - previous.tile.x
        if abs(dx) == 1:
            direction = (1 if dx > 0 else (-1 if dx < 0 else 0))
    return Record({'tile': tile, 'tick': tick, 'direction': direction})


def safe_crossing(leg, witch):
    if all([sheltered(_x) for _x in leg]):
        return True
    if not (witch.direction if witch is not None else None):
        return False
    x = witch.tile.x
    direction = witch.direction
    low = x
    high = x
    for tick in range(len(leg) + MOVEMENT_GRACE + SNAPSHOT_GRACE):
        if x == 2904:
            direction = 1
        if x == 2930:
            direction = -1
        x += direction
        low = min(low, x)
        high = max(high, x)
    return all([sheltered(tile) or tile.x < low - 3 or tile.x > high + 3 for tile in leg])


def walk_garden(destination, log):
    if not in_garden(position()):
        _w1 = yield from traversal.walk_resilient(GARDEN_ENTRY, radius=0, attempts=2, timeout_ms=180000, log=log)
        if not (_w1):
            return False
    here = position()
    if not here:
        return False
    if here.z >= 3467 and here.x >= 2908 and here.x <= 2912 and not any([same(here, tile) for tile in ROUTE]):
        _w2 = yield from direct_navigator.walk_to(FOUNTAIN_STAND, 0, 10000)
        if not (_w2):
            return False
        here = position()
    legs = here and garden_legs(here, destination)
    if not legs:
        log('outside the guarded garden corridor')
        return False
    for leg in legs:
        end = (leg[-1] if len(leg) > 0 else None)
        if all([sheltered(_x) for _x in leg]):
            _w3 = yield from direct_navigator.walk_to(end, 0, 10000)
            if not (_w3):
                return False
            continue
        ready = False
        observation = None
        for tick in range(120):
            if event_signal.pending() or not same(position(), leg[0]):
                return False
            witch_npc = ([npc for npc in npcs.all() if npc.id == 896] or [None])[0]
            witch = witch_npc.network_tile() if witch_npc is not None else None
            observation = observe_witch(observation, witch, game.tick())
            if safe_crossing(leg, observation):
                ready = True
                break
            if not sheltered(leg[0]):
                return False
            if tick == 0:
                log(f'waiting behind the hedge at {leg[0].x},{leg[0].z}')
            yield from execution.delay_ticks(1)
        if not ready:
            return False
        if not (direct_navigator.walk(end)):
            return False
        previous = position()
        stalled = 0
        budget = len(leg) + MOVEMENT_GRACE
        tick = 0
        while tick < budget and not same(position(), end):
            tick += 1
            yield from execution.delay_ticks(1)
            current = position()
            if not current or not in_garden(current):
                return False
            stalled = (stalled + 1 if previous and same(current, previous) else 0)
            previous = current
            if stalled < 2 or (same(current, leg[0]) and tick < 2):
                continue
            cover = (Tile(current.x, current.z, current.level) if sheltered(current) else (sorted([_x for _x in leg if sheltered(_x)], key=lambda a: a.distance_to(current)) or [None])[0])
            if not cover or not (direct_navigator.walk(cover)):
                return False
            yield from execution.delay_until_ticks(lambda: same(position(), cover), budget - tick - 1)
            log(f'garden crossing stalled at {current.x},{current.z}; returning to cover at {cover.x},{cover.z}')
            return False
        if not same(position(), end):
            stopped = position()
            if stopped and in_garden(stopped):
                direct_navigator.walk(stopped)
            return False
    return same(position(), destination)


GARDEN_SHED = WH_TILE.SHED_DOOR

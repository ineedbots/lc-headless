"""Ported from rs2b0t's src/bot/api/ai/quests/defs/dragonslayer/maze.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.tasks import sustain
from rs2004.execution import event_signal
from rs2004.catalogs.record import Record
from rs2004.quests.defs.dragonslayer.areas import DS_ID
from rs2004.entities import ground_items, locs, npcs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.traversal import traversal

__all__ = ['MAZE_NPC', 'MAZE_LEGS', 'maze_scene_loaded', 'held_by_id', 'in_maze', 'leg_from_position', 'loot_chest', 'door_crossed', 'leave_maze', 'MazeRun']

# Why: the route is the shortest path the baked collision pack admits from the front door to the chest, with each coloured door opened in key order.
# Why: locs go by exact tile and NPCs by exact id: 6 decoy Giant rats share the one that drops the red key, and 11 unclimbable "Ladder"s share a name with the 3 that work.
# Why: `open_and_close_door` teleports you through and eats the key, so a leg is done when the key is gone and you've landed on the far side.
MAZE_NPC = Record({'GIANT_RAT': 748, 'GHOST': 749, 'SKELETON': 750, 'ZOMBIE': 751, 'DEMON': 752, 'MELZAR': 753})
MAZE_LEGS = [
    Record({
    'kind': 'door',
    'what': 'the front door',
    'stand': Tile(2941, 3248, 0),
    'door': Tile(2941, 3248, 0),
    'key_id': DS_ID.MAZE_KEY,
    'land': Tile(2940, 3248, 0),
}),
    Record({
    'kind': 'kill',
    'what': 'the giant rat',
    'npc_id': MAZE_NPC.GIANT_RAT,
    'at': Tile(2930, 3252, 0),
    'key_id': DS_ID.RED_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the red door',
    'stand': Tile(2926, 3253, 0),
    'door': Tile(2926, 3253, 0),
    'key_id': DS_ID.RED_KEY,
    'land': Tile(2925, 3253, 0),
}),
    Record({
    'kind': 'climb',
    'what': 'the ladder to the first floor',
    'stand': Tile(2927, 3256, 0),
    'ladder': Tile(2928, 3256, 0),
    'op': 'Climb-up',
    'land': Tile(2928, 3256, 1),
}),
    Record({
    'kind': 'kill',
    'what': 'the ghost',
    'npc_id': MAZE_NPC.GHOST,
    'at': Tile(2929, 3249, 1),
    'key_id': DS_ID.ORANGE_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the orange door',
    'stand': Tile(2930, 3253, 1),
    'door': Tile(2931, 3253, 1),
    'key_id': DS_ID.ORANGE_KEY,
    'land': Tile(2931, 3253, 1),
}),
    Record({
    'kind': 'climb',
    'what': 'the ladder to the second floor',
    'stand': Tile(2933, 3254, 1),
    'ladder': Tile(2934, 3254, 1),
    'op': 'Climb-up',
    'land': Tile(2934, 3254, 2),
}),
    Record({
    'kind': 'kill',
    'what': 'the skeleton',
    'npc_id': MAZE_NPC.SKELETON,
    'at': Tile(2923, 3251, 2),
    'key_id': DS_ID.YELLOW_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the yellow door',
    'stand': Tile(2924, 3250, 2),
    'door': Tile(2924, 3249, 2),
    'key_id': DS_ID.YELLOW_KEY,
    'land': Tile(2924, 3249, 2),
}),
    Record({
    'kind': 'climb',
    'what': 'the ladder back to the first floor',
    'stand': Tile(2939, 3240, 2),
    'ladder': Tile(2940, 3240, 2),
    'op': 'Climb-down',
    'land': Tile(2940, 3240, 1),
}),
    Record({
    'kind': 'climb',
    'what': 'the ladder back to the ground floor',
    'stand': Tile(2938, 3240, 1),
    'ladder': Tile(2937, 3240, 1),
    'op': 'Climb-down',
    'land': Tile(2937, 3240, 0),
}),
    Record({
    'kind': 'climb',
    'what': 'the ladder to the basement',
    'stand': Tile(2933, 3240, 0),
    'ladder': Tile(2932, 3240, 0),
    'op': 'Climb-down',
    'land': Tile(2933, 9640, 0),
}),
    Record({
    'kind': 'kill',
    'what': 'the zombie',
    'npc_id': MAZE_NPC.ZOMBIE,
    'at': Tile(2932, 9642, 0),
    'key_id': DS_ID.BLUE_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the blue door',
    'stand': Tile(2931, 9643, 0),
    'door': Tile(2931, 9643, 0),
    'key_id': DS_ID.BLUE_KEY,
    'land': Tile(2930, 9643, 0),
}),
    Record({
    'kind': 'kill',
    'what': 'Melzar the mad',
    'npc_id': MAZE_NPC.MELZAR,
    'at': Tile(2929, 9649, 0),
    'key_id': DS_ID.MAGENTA_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the magenta door',
    'stand': Tile(2929, 9651, 0),
    'door': Tile(2929, 9652, 0),
    'key_id': DS_ID.MAGENTA_KEY,
    'land': Tile(2929, 9652, 0),
}),
    Record({
    'kind': 'kill',
    'what': 'the lesser demon',
    'npc_id': MAZE_NPC.DEMON,
    'at': Tile(2936, 9650, 0),
    'key_id': DS_ID.GREEN_KEY,
}),
    Record({
    'kind': 'door',
    'what': 'the green door',
    'stand': Tile(2936, 9655, 0),
    'door': Tile(2936, 9655, 0),
    'key_id': DS_ID.GREEN_KEY,
    'land': Tile(2936, 9656, 0),
}),
    Record({'kind': 'chest', 'what': 'the map chest', 'stand': Tile(2935, 9656, 0)}),
]


def walk(to, log, radius=1):
    return traversal.walk_resilient(to, radius=radius, attempts=3, timeout_ms=120000, log=log)


def maze_scene_loaded():
    """Locs read blank for about a tick after a level change."""
    return execution.delay_until(lambda: locs.query().within(10).exists(), 6000)


def held_by_id(id):
    return inventory.count_by_id(id) > 0


KEY_IDS = [
    DS_ID.MAZE_KEY,
    DS_ID.RED_KEY,
    DS_ID.ORANGE_KEY,
    DS_ID.YELLOW_KEY,
    DS_ID.BLUE_KEY,
    DS_ID.MAGENTA_KEY,
    DS_ID.GREEN_KEY,
]


# Why: the east bound stops at 2940 since the front door on 2941 is the doorstep outside; including it makes the bot walk straight back in after leaving.
def in_maze(t):
    """True while standing anywhere inside the maze, on any of its four floors."""
    if not t:
        return False
    upstairs = t.x >= 2920 and t.x <= 2940 and t.z >= 3236 and t.z <= 3262
    basement = t.x >= 2915 and t.x <= 2945 and t.z >= 9630 and t.z <= 9665
    return upstairs or basement


def leg_from_position(t):
    """Route index from position alone, to pick up an interrupted run; within a run the index is carried forward."""
    # Why: Apply floor tests only inside the building; the Dwarven Mine shares the basement z-range.
    if not in_maze(t):
        return 0
    if t.z >= 9600:
        return 12
    if t.level == 2:
        return 7
    if t.level == 1:
        return 4
    # Ground-floor entrance hall and the separate second-floor landing pocket.
    if t.z <= 3242 and t.x >= 2929:
        return 11
    return (1 if in_maze(t) else 0)


def take_key(key_id, log):
    drop = ground_items.query().where(lambda g: g.id == key_id).within(14).nearest()
    if not drop:
        return False
    log('picking the key up off the floor')
    _c1 = drop.distance() > 1
    if _c1:
        _w2 = yield from walk(drop.tile(), log, 1)
        _c1 = not (_w2)
    if _c1:
        return False
    if not (drop.interact('Take')):
        return False
    _result3 = yield from execution.delay_until(lambda: held_by_id(key_id), 6000)
    return _result3


def kill_for(leg, log):
    if held_by_id(leg.key_id):
        return True
    _w4 = yield from take_key(leg.key_id, log)
    if _w4:
        return True

    def find():
        npc_id = leg.npc_id
        return npcs.query().where(lambda n: n.id == npc_id).action('Attack').nearest()

    _c5 = not find()
    if _c5:
        _w6 = yield from walk(leg.at, log, 3)
        _c5 = not (_w6)
    if _c5:
        return False
    yield from maze_scene_loaded()
    target = find()
    if not target:
        log(f'no {leg.what} in the scene — it may still be respawning')
        yield from execution.delay_ticks(3)
        return False
    _c7 = target.distance() > 8
    if _c7:
        _w8 = yield from walk(target.tile(), log, 2)
        _c7 = not (_w8)
    if _c7:
        return False
    log(f'killing {leg.what} for its key')
    if not (target.interact('Attack')):
        return False
    deadline = _core.step_time() + 60000
    attacked_at = game.tick()
    while _core.step_time() < deadline:
        if event_signal.pending():
            return False
        before_upkeep = game.tick()
        yield from sustain.run()
        if held_by_id(leg.key_id) or not target.valid():
            break
        # Melzar's cabbage spell stops our attack while he keeps targeting us. Re-send at a bounded cadence,
        # leaving any tick spent on food or prayer to upkeep.
        now = game.tick()
        if now == before_upkeep and now - attacked_at >= 8:
            live = find()
            if live is None:
                break
            live.interact('Attack')
            attacked_at = now
        yield from execution.delay_ticks(1)
    if held_by_id(leg.key_id):
        return True
    # The key drops where it died, which is rarely underfoot.
    _result9 = yield from take_key(leg.key_id, log)
    return _result9


def loc_at(name, tile):
    def _fn10(l):
        t = l.tile()
        return t.x == tile.x and t.z == tile.z and t.level == tile.level
    return locs.query().name(name).where(_fn10).first()


def open_door(leg, log):
    key = ([i for i in inventory.items() if i.id == leg.key_id] or [None])[0]
    if not key:
        return False
    _w11 = yield from walk(leg.stand, log, 0)
    if not (_w11):
        return False
    _w12 = yield from maze_scene_loaded()
    if not (_w12):
        return False
    door = loc_at('Door', leg.door)
    if not door:
        log(f'{leg.what} is not in the scene yet')
        return False
    log(f'unlocking {leg.what}')
    if not (key.use_on(door)):
        return False
    # The coloured doors eat their key as they swing; the front door doesn't, so landing on the far side is the signal both share.
    _result13 = yield from execution.delay_until(lambda: not held_by_id(leg.key_id) or on_tile(leg.land), 10000)
    return _result13


def climb(leg, log):
    _w14 = yield from walk(leg.stand, log, 0)
    if not (_w14):
        return False
    _w15 = yield from maze_scene_loaded()
    if not (_w15):
        return False
    ladder = loc_at('Ladder', leg.ladder)
    if not ladder:
        log(f'{leg.what} is not in the scene')
        return False
    log(f'taking {leg.what}')
    if not (ladder.interact(leg.op)):
        return False

    def _fn17():
        t = game.tile()
        return t is not None and t.level == leg.land.level and abs(t.z - leg.land.z) < 100
    _result16 = yield from execution.delay_until(_fn17, 8000)
    return _result16


def loot_chest(map_id, log):
    """Both map chests are two-stage locs: Open swaps in a loc whose first option is Search, and only Search hands over the piece."""
    shut = locs.query().name('Chest').action('Open').within(5).nearest()
    if shut:
        log('opening the chest')
        if not (shut.interact('Open')):
            return False
        yield from execution.delay_until(lambda: locs.query().name('Chest').action('Search').within(5).exists(), 6000)
    open = locs.query().name('Chest').action('Search').within(5).nearest()
    if not open or not (open.interact('Search')):
        return False
    _result18 = yield from execution.delay_until(lambda: inventory.count_by_id(map_id) > 0, 10000)
    return _result18


def on_tile(t):
    here = game.tile()
    return here is not None and here.x == t.x and here.z == t.z and here.level == t.level


# Why: the front door's `oplocu` never calls `inv_del`, so the maze key says nothing about which side we're on; coloured keys are deleted as their door swings.
def door_crossed(leg, here, holds_key):
    """Whether a door leg has been crossed."""
    if leg.key_id == DS_ID.MAZE_KEY:
        return in_maze(here) and here.x < leg.door.x
    return not holds_key


def leg_done(leg, here):
    """Has this leg already been walked past?"""
    if leg.kind == 'kill':
        return held_by_id(leg.key_id)
    elif leg.kind == 'door':
        return door_crossed(leg, here, held_by_id(leg.key_id))
    elif leg.kind == 'climb':
        return here.level == leg.land.level and abs(here.z - leg.land.z) < 100
    elif leg.kind == 'chest':
        return held_by_id(DS_ID.MAP_MELZAR)


# Why: the maze is one-way, so the only way out of the chest room is the north-east cellar ladder, the inside-only `funexit` door, then the front door, which the unconsumed maze key still opens.
def leave_maze(log):
    """Walk the one route out of the maze."""
    here = game.tile()
    if not here or not in_maze(here):
        return True
    if here.z >= 9000:
        _w20 = yield from walk(Tile(2938, 9657, 0), log, 0)
        _c19 = not (_w20)
        if not _c19:
            _w21 = yield from maze_scene_loaded()
            _c19 = not (_w21)
        if _c19:
            return False
        ladder = loc_at('Ladder', Tile(2939, 9657, 0))
        if not ladder:
            log('no cellar ladder out of the basement')
            return False
        log('climbing out of the cellar')
        if not (ladder.interact('Climb-up')):
            return False
        _result22 = yield from execution.delay_until(lambda: (((game.tile().z if game.tile() is not None else None) if (game.tile().z if game.tile() is not None else None) is not None else 9999)) < 9000, 8000)
        return _result22
    # The exit door drops into the pocket the entrance hall opens onto.
    if here.z > 3251 and here.x > 2937:
        _w24 = yield from walk(Tile(2938, 3252, 0), log, 0)
        _c23 = not (_w24)
        if not _c23:
            _w25 = yield from maze_scene_loaded()
            _c23 = not (_w25)
        if _c23:
            return False
        door = loc_at('Door', Tile(2938, 3252, 0))
        if not door:
            log('no exit door in the scene')
            return False
        log('opening the one-way exit door')
        if not (door.interact('Open')):
            return False
        _result26 = yield from execution.delay_until(lambda: (((game.tile().x if game.tile() is not None else None) if (game.tile().x if game.tile() is not None else None) is not None else 9999)) <= 2937, 8000)
        return _result26
    front = MAZE_LEGS[0]
    if front.kind != 'door':
        return False
    _w28 = yield from walk(front.land, log, 0)
    _c27 = not (_w28)
    if not _c27:
        _w29 = yield from maze_scene_loaded()
        _c27 = not (_w29)
    if _c27:
        return False
    key = ([i for i in inventory.items() if i.id == DS_ID.MAZE_KEY] or [None])[0]
    door = loc_at('Door', front.door)
    if not key or not door:
        log('cannot re-open the front door from the inside')
        return False
    log('letting myself back out of the front door')
    if not (key.use_on(door)):
        return False
    _result30 = yield from execution.delay_until(lambda: not in_maze(game.tile()), 8000)
    return _result30


class MazeRun:
    _index = -1

    def step(self, log):
        """Runs one leg per call; the engine loop drives it to the chest."""
        if held_by_id(DS_ID.MAP_MELZAR):
            return True
        here = game.tile()
        if not here:
            return False
        # Why: a coloured key exists only between its kill and its door, so it re-syncs the route; the maze key is kept for the quest and isn't a marker.
        key_leg = ([_i for _i, l in enumerate(MAZE_LEGS) if l.kind == 'door' and l.key_id != DS_ID.MAZE_KEY and held_by_id(l.key_id)] or [-1])[0]
        if not in_maze(here):
            self._index = 0
        elif key_leg >= 0:
            self._index = key_leg
        else:
            if self._index < 0:
                self._index = leg_from_position(here)
                log(f'picking the maze up at leg {self._index}')
        while self._index < len(MAZE_LEGS) and leg_done(MAZE_LEGS[self._index], here):
            self._index += 1
        if self._index >= len(MAZE_LEGS):
            return held_by_id(DS_ID.MAP_MELZAR)
        leg = MAZE_LEGS[self._index]
        if leg.kind == 'kill':
            _result31 = yield from kill_for(leg, log)
            return _result31
        elif leg.kind == 'door':
            _result32 = yield from open_door(leg, log)
            return _result32
        elif leg.kind == 'climb':
            _result33 = yield from climb(leg, log)
            return _result33
        elif leg.kind == 'chest':
            _w35 = yield from walk(leg.stand, log, 1)
            _c34 = not (_w35)
            if not _c34:
                _w36 = yield from maze_scene_loaded()
                _c34 = not (_w36)
            if _c34:
                return False
            _result37 = yield from loot_chest(DS_ID.MAP_MELZAR, log)
            return _result37

    @staticmethod
    def key_ids():
        """Keys are worthless outside the maze and squat pack slots."""
        return KEY_IDS

"""JiveKBD's way into the lair and out of it: rs2b0t's scripts/JiveKBD/entry.ts (MIT, see thirdparty/rs2b0t).

The host is the bot, with what rs2004.hunting.supply needs and last_dose_tick (None before the first) and
drink_antipoison() (with yield from, False with none in the pack)."""

from bots.jivekbd.logic import dose_due
from rs2004.hunting.supply import escape_runes_for, teleport_out, wait_fed

# The wilderness walk is 369 tiles of path, most of it at walking pace once the run energy goes.
WALK_MS = 600000
HOP_MS = 8000
PLAYER_RADIUS = 15


def _say(h):
    return lambda m: h.log(f'  {m}')


def _within(t, radius):
    me = game.tile()
    return me is not None and me.level == t.level and t.distance_to(me) <= radius


# Why: another player near the ladder is the one hazard the run can't handle, so it's named in the log where the
# operator will look.
def _warn_of_players(h, where):
    me = players.local()
    names = [p.name or '?' for p in players.query().within(PLAYER_RADIUS).results() if p.index != me.index]
    if len(names) > 0:
        h.log(f"WARNING: {len(names)} player(s) within {PLAYER_RADIUS} tiles at the {where}: {', '.join(names)}")


# Why: the walker's arrival accepts the closest reachable point, and a lever is legal only from its own tile, so the
# stand is read back before the op goes.
def _use_stop(h, stop, what, status, arrived):
    """Stands at the stop and sends its op; True once arrived() holds."""
    if not _within(stop.tile, stop.radius):
        h.set_status(f'walking to the {what}')
        yield from traversal.walk_resilient(stop.tile, radius=stop.radius, attempts=4, timeout_ms=WALK_MS, log=_say(h))
    if not _within(stop.tile, stop.radius):
        h.log(f'could not stand at the {what} ({stop.tile.x},{stop.tile.z}). Retrying.')
        return False
    yield from execution.delay_ticks(2)
    wanted = stop.loc_id
    loc = locs.query().where(lambda l: l.id == wanted).within(3).nearest()
    if loc is None:
        h.log(f'the {what} is not in the scene yet. Retrying.')
        return False
    h.set_status(status)
    mark = game_messages.mark()
    if not loc.interact(stop.op):
        h.log(f'the {what} refused the {stop.op}. Retrying.')
        return False
    through = yield from wait_fed(lambda: arrived() or game_messages.saw_since(mark, CANT_REACH), HOP_MS)
    if not through:
        h.log(f'the {what} did not take us through. Retrying.')
        return False
    if not arrived():
        here = game.tile()
        where = f'{here.x},{here.z}' if here is not None else '?'
        h.log(f'the server could not reach the {what} from {where}. Retrying.')
        return False
    return True


# Why: the poison spiders spawn on the tiles round the lever, so the dose goes down on the surface where nothing
# bites, inside its own window.
def enter_kbd_lair(h, site, route):
    """Walks the wilderness to the Lava Maze ladder, climbs down and pulls the lever into the lair. Use with
    yield from."""
    if site.in_area(game.tile()):
        return True
    if not route.in_dungeon(game.tile()):
        if not _within(route.ladder.tile, route.ladder.radius):
            h.set_status('walking to the Lava Maze ladder')
            yield from traversal.walk_resilient(route.ladder.tile, radius=route.ladder.radius, attempts=4, timeout_ms=WALK_MS, log=_say(h))
        if not _within(route.ladder.tile, route.ladder.radius):
            h.log('the walk to the Lava Maze ladder stopped short. Retrying.')
            return False
        _warn_of_players(h, 'ladder')
        if dose_due(h.last_dose_tick, game.tick()):
            drank = yield from h.drink_antipoison()
            if drank:
                h.log('drank a Superantipoison before the lever spiders')
            else:
                h.log('WARNING: no Superantipoison to drink before the lever spiders. Going in uncured.')
        down = yield from _use_stop(h, route.ladder, 'ladder', 'climbing down into the Lava Maze dungeon', lambda: route.in_dungeon(game.tile()))
        if not down:
            return False
        h.log('down the ladder into the Lava Maze dungeon')
    inside = yield from _use_stop(h, route.lever, 'lever', 'pulling the lever into the lair', lambda: site.in_area(game.tile()))
    if not inside:
        return False
    h.log('inside the King Black Dragon lair')
    return True


# Why: the dungeon is level-42 wilderness where no teleport fires, and the lair two tiles away isn't, so a trip that
# starts by the lever goes in before it goes home.
def leave_kbd_lair(h, site, route):
    """Teleports home from the lair, or pulls the exit lever and climbs out when the cast won't fire. Use with
    yield from."""
    if route.in_dungeon(game.tile()):
        inside = yield from _use_stop(h, route.lever, 'lever', 'pulling the lever into the lair to teleport', lambda: site.in_area(game.tile()))
        if not inside:
            return False
    if not site.in_area(game.tile()):
        return True
    why = yield from teleport_out(h, site)
    if why is None:
        return True
    h.log(f'the {escape_runes_for(site.escape_teleport_id).label} will not fire ({why}). Walking out by the exit lever and the ladder instead.')
    out = yield from _use_stop(h, route.out_lever, 'exit lever', 'pulling the exit lever', lambda: route.in_dungeon(game.tile()))
    if not out:
        return False
    up = yield from _use_stop(h, route.up_ladder, 'ladder', 'climbing out of the Lava Maze dungeon', lambda: not route.in_dungeon(game.tile()))
    if not up:
        return False
    _warn_of_players(h, 'ladder')
    h.log('out of the Lava Maze dungeon on foot. Walking to the bank.')
    return True

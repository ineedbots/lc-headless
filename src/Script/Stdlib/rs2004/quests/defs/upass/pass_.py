"""Ported from rs2b0t's src/bot/api/ai/quests/defs/upass/pass.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.entities import locs
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.messages import CANT_REACH, game_messages
from rs2004.navigation import navigator, reachability
from rs2004.quests.defs.upass.areas import CAVERN_LINKS, PLATFORM_LINKS, UP_ITEM, UP_LOC
from rs2004.quests.defs.upass.cross import cross_once
from rs2004.quests.defs.upass.doors import MUD_CAGE, door_stands, mud_cell_door
from rs2004.quests.defs.upass.rank import order_seams
from rs2004.quests.defs.upass.spent import spend_from, spent_here, spent_state_here
from rs2004.quests.defs.upass.stand import by_side_that_lands
from rs2004.quests.defs.upass.verdict import said_since, verdict_since
from rs2004.quests.exec.prompts import settle_scene
from rs2004.traversal import traversal

__all__ = ['travel_to']

# Why: every seam is a scripted obstacle on a tile the collision pack marks blocked, so `walkResilient` past one reports "unreachable" (a component report over the seam endpoints fails 10 of 14 anchors). Movement here is walk the pocket, cross one obstacle, repeat.
# Why: The pass has 16 measured pockets separated by scripted crossings; only the main level-1 landing reaches both wall tunnels on foot.
# Why: the 2 locked cages roll `stat_random(thieving, ...)` and a fail leaves you where you were, so one send is one roll.
LOCK_TRIES = 5
# Why: the rockslide, ledge, stone bridges and collapsed bridge each roll agility and drop you short on a fail (the ledge into a rat pit for 5), so one roll can't spend the obstacle.
ROLL_TRIES = 4
# Why: Tunnel doors teleport by angle to distant landings, so rank them by landing rather than door position.
TUNNEL_TO_RAILINGS = Tile(2401, 9610, 0)
TUNNEL_TO_UNICORN = Tile(2376, 9610, 0)
TUNNEL_TO_FIRST_CAVERN = Tile(2371, 9666, 0)
# Why: `@upass_area_2_3_entrance` picks one of 3 ends on the door's angle and on `%upass >= ^upass_killed_unicorn`, which the journal can't report because stages 3 and 4 print the same page. So a door is worth its best end, and the crossing test says where it landed.
TUNNEL_ENDS = [TUNNEL_TO_FIRST_CAVERN, TUNNEL_TO_RAILINGS, TUNNEL_TO_UNICORN]


def tunnel_landing(at):
    return TUNNEL_ENDS


# Why: Only the cage at (2393,9655) reaches the southbound mud; from inside a cell, select its own door back to the corridor.
def in_cage_corridor():
    return reachability.can_reach(MUD_CAGE, adjacent_ok=False, max_steps=REACH.max_steps)


def cage_worth_taking(dest, from_, at):
    return (at.x == MUD_CAGE.x and at.z == MUD_CAGE.z) or not in_cage_corridor()


# Why: ordered by how often the route meets them, so the nearest-first search below settles quickly.
HOP_KINDS = [
    Record({'loc': UP_LOC.ROCKSLIDE, 'op': 'Climb-over', 'tries': ROLL_TRIES}),
    Record({'loc': UP_LOC.ROCK_BRIDGE, 'op': 'Cross', 'tries': ROLL_TRIES}),
    Record({
    'loc': UP_LOC.LEDGE,
    'op': 'Cross',
    'tries': ROLL_TRIES,
    'group': 8,
    'stands': lambda at: [Tile(at.x + 1, at.z, at.level)],
}),
    Record({'loc': UP_LOC.PIPE_AREA1, 'op': 'Squeeze-through'}),
    Record({'loc': UP_LOC.PIPE_AREA2, 'op': 'Squeeze-through'}),
    Record({'loc': UP_LOC.COLLAPSED_A, 'op': 'Cross', 'tries': ROLL_TRIES}),
    Record({'loc': UP_LOC.COLLAPSED_B, 'op': 'Cross', 'tries': ROLL_TRIES}),
    Record({'loc': UP_LOC.ROCKSWING_BACK, 'op': 'Swing-on', 'tries': ROLL_TRIES}),
    Record({'loc': UP_LOC.UNICORN_DOOR_L, 'op': 'Pass-through', 'landing': tunnel_landing}),
    Record({'loc': UP_LOC.UNICORN_DOOR_R, 'op': 'Pass-through', 'landing': tunnel_landing}),
    Record({
    'loc': UP_LOC.RAILINGS_LOCKED,
    'op': 'Pick-lock',
    'tries': LOCK_TRIES,
    'landing': mud_cell_door,
    'stands': door_stands,
    'when': cage_worth_taking,
}),
    Record({'loc': UP_LOC.RAILINGS_HARD, 'op': 'Pick-lock', 'tries': LOCK_TRIES, 'stands': door_stands}),
]
# Why: 2 locs that look like seams. `upass_swampbubbles1`'s Cross drops you in the crevasse at (2485,9649) for 15% hp, and `caverockpile` climbs back out to (2482,9715) behind the bridge and the grid. Neither gets you forward.
# Why: `cavewalltunnel_upass_tocells` has an Enter with no script; it's the scenery the mud dig drops you beside, so crossing it wastes the hop.
HOP_TIMEOUT_MS = 12000
CROSS_TIMEOUT_MS = 10000
# Why: what a silent op gets. 3 ticks covers a teleport door end to end, and nothing in the pass moves you later than that without saying so first.
QUIET_MS = 1800
# Why: Cover approach, arrival delay, roll, and the 60-cycle movement/loc merge; successful crossings resolve much sooner.
CROSS_SETTLE_MS = 5000
MAX_HOPS = 24
MIN_GAIN = 3
# Why: the seam out of a pocket can sit right across it, the rope swing is 20 tiles from where the bridge lands, so the search covers the pocket. The gain threshold and the spent set hold off drift.
HOP_SEARCH = 32
# Why: Server op pathing can reach slightly beyond the client flood; larger radii cross into another pocket and produce reach failures.
SERVER_PATH_RANGE = 8
# Why: the pockets wind, so a 30-tile obstacle is past the flood's default 400 steps.
REACH = Record({'adjacent_ok': True, 'max_steps': 2000})
NO_TELEPORTS = {'use_teleports': False}


def here():
    return game.tile()


def chebyshev(a, b):
    return max(abs(a.x - b.x), abs(a.z - b.z))


# Why: the op-click walks you first, so wait for 2 still ticks before judging anything. The crossing's forced move comes after that.
# Why: `spoke` is the op's verdict in the chatbox and it beats the tile: the script says what it did before it moves anyone, and a refusal never moves anyone. Without it a refused obstacle paid 6 ticks here plus the crossing timeout.
def settle_walk(spoke=None):
    if spoke is None:
        spoke = lambda: False
    # Why: 2 still ticks are also true before the walk starts, so wait for the first move or a verdict, or every first attempt is judged on the start tile.
    start = here()

    def _fn1():
        now = here()
        return spoke() or (now is not None and start is not None and (now.x != start.x or now.z != start.z))
    yield from execution.delay_until_ticks(_fn1, 6)
    last = here()
    still = 0
    deadline = _core.step_time() + HOP_TIMEOUT_MS
    while _core.step_time() < deadline:
        yield from execution.delay_ticks(1)
        now = here()
        if spoke():
            return now
        if now and last and now.x == last.x and now.z == last.z and now.level == last.level:
            still += 1
            if still >= 2:
                return now
        else:
            still = 0
        last = now
    return here()


def held(id):
    return sum([item.count for item in [item for item in inventory.items() if item.id == id]])


# Why: a seam's own tile is blocked and the flood can refuse it outright where the near side is a single walkable column, so any cardinal neighbour answering is enough.
def seam_reachable(at):
    if reachability.can_reach(at, True):
        return True
    return any([reachability.can_reach(Tile(at.x + dx, at.z + dz, at.level), True) for dx, dz in [[1, 0], [-1, 0], [0, 1], [0, -1]]])


# Why: where a kind names its stands, those tiles are the test. `[oploc1,upass_ledge]` refuses every tile west of the column, so 5 of the ledge's 6 locs can only be stood beside from another pocket, and a reachable neighbour there means nothing.
def seam_open(loc):
    at = loc.tile()
    _fn3 = getattr(kind_of(loc), 'stands', None)
    named = (_fn3(at) if _fn3 is not None else None)
    if named is not None and len(named) > 0:
        return any([reachability.can_reach(tile, adjacent_ok=False, max_steps=REACH.max_steps) for tile in named])
    return seam_reachable(at)


# Why: wider than the hop search. The main cavern's exit is a collapsed bridge 43 tiles off, and the one inside 32 belongs to a pocket this one can't reach.
SWEEP_SEARCH = 52


def seams_in_scene(within=None):
    """Every seam loc in the scene, worth crossing or not, for the stuck-pocket log."""
    if within is None:
        within = HOP_SEARCH
    found = []
    for kind in HOP_KINDS:
        found.extend(list(locs.query().where(lambda loc: loc.id == kind.loc).action(kind.op).within(within).results()))
    for seam in USE_SEAMS:
        found.extend(list(locs.query().where(lambda loc: (loc.id in seam.locs)).within(within).results()))
    return found


# Why: "no obstacle makes progress" doesn't say whether the seam is out of the scene, under the gain threshold or behind a wall, and a pocket the route can't leave costs the run.
def report_stuck(dest, from_, log):
    mine = chebyshev(from_, dest)

    def _fn5(loc):
        at = loc.tile()
        return f'{loc.id}@{at.x},{at.z}L{at.level}' + f" gain{mine - chebyshev(at, dest)}{str(('' if seam_reachable(at) else ' walled'))}"
    seams = ' '.join([_fn5(_x) for _x in seams_in_scene(SWEEP_SEARCH)[0:12]])
    log(f'pass:   seams in reach of ({from_.x},{from_.z}): {seams}')
    # Why: a seam missing from the scene and one the vocabulary doesn't name look the same from outside, and the second is the likelier bug, so list everything operable.
    # Why: one line: the harness surfaces a bounded number of log lines per tick, so 24 of them arrive as a count.
    nearby = [loc for loc in locs.query().within(20).results() if len(loc.actions()) > 0]
    listed = ' '.join([f"{loc.id}@{loc.tile().x},{loc.tile().z}L{loc.tile().level}[{'|'.join(loc.actions())}]" for loc in nearby[0:24]])
    log(f'pass:   {len(nearby)} op-bearing within 20 of ({from_.x},{from_.z}): {listed}')


# Why: a ground-decor seam sits on a blocked tile, so the server's path for the op-click dead-ends with "I can't reach that!" and the script never runs. `inOperableDistance` is `reachedEntity || reachedObj`, which a cardinal neighbour satisfies, so walk there before sending the op.
# Why: the client's walkability for that tile disagrees with the server on a bridge structure, so it can't short-circuit the walk.
def stand_beside(at, dest, note, skip=0, named=None):
    if named is None:
        named = []
    me = here()

    def on(tile):
        return me is not None and me.x == tile.x and me.z == tile.z and me.level == tile.level

    # Why: a railing is only used from its own tile or the tile across its edge. A tile off its row sets `~check_axis_locactive` false and the script teleports you onto the door's tile without opening it.
    if len(named) > 0:
        if skip == 0 and any([on(_x) for _x in named]):
            return 'stood'
    elif skip == 0 and me and me.level == at.level and chebyshev(me, at) <= 1:
        return 'stood'
    elif skip == 0 and me and me.level == at.level and chebyshev(me, at) <= 4 and reachability.can_reach(Tile(at.x, at.z, at.level), True):
        return 'stood'
    # Why: the flood and the walker disagree on single tiles: the ledge's east neighbour at z 9643 floods as reachable and the walker says "unreachable beyond (2375,9644)".
    # Why: `reached` can still refuse from a side the walk reaches because a cavern wall is between them, so a retry takes the next side.
    # Why: adjacency is to the loc's footprint. A collapsed bridge is 3 tiles long, so its stand is 3 out from the origin and a ring of 1 finds only chasm.
    ring = []
    for d in range(1, 4 + 1):
        ring.extend([[d, 0], [-d, 0], [0, d], [0, -d]])
    # Why: a 4-sided door puts you out opposite the side you used it from, so the stand decides the landing. Nearest-first took the cage at (2380,9619) from the east every time when south opens toward the unicorn area. Rank stands by where they land and tie-break on the seam's distance.
    near_me = by_side_that_lands(at, dest, me)
    candidates = (list(named) if len(named) > 0 else [Tile(at.x + dx, at.z + dz, at.level) for dx, dz in ring])

    # Why: `adjacentOk` accepts tiles you can only get next to and a radius-0 walk then refuses them, but strict alone throws away the rope swing's stand. So strict first, loose behind, and the walk radius follows the list.
    # Why: named stands keep their given order, the door's own tile before the tile across it, because that order says which way the crossing goes and only one is ever reachable.
    def rank(list_):
        return list_ if len(named) > 0 else sorted(list_, key=near_me)

    strict = rank([tile for tile in candidates if reachability.can_reach(tile, adjacent_ok=False, max_steps=REACH.max_steps)])
    loose = rank([tile for tile in [tile for tile in candidates if not any([s.x == tile.x and s.z == tile.z for s in strict])] if reachability.can_reach(tile, True)])
    sides = list(strict) + list(loose)
    if len(sides) == 0:
        # Why: never for a named stand. Server-pathing to a railing picks any side, and every side but 2 sets `~check_axis_locactive` false and teleports you onto the door without opening it. A door with both tiles out of reach is in another cell.
        if len(named) > 0:
            note(f'neither tile of the door at {at.x},{at.z} is reachable — it belongs to another cell')
            return 'no'
        # Why: a seam whose approach the pack calls blocked has no reachable ring (the pipe into the railings is operated from a tile no flood will stand on). Close in, send the op and let the server path; a refusal comes back in words. Far off it's another pocket and the click wouldn't send.
        if me is not None and me.level == at.level and chebyshev(me, at) <= SERVER_PATH_RANGE:
            note(f'no stand beside {at.x},{at.z} the flood will take — sending the op from ({me.x},{me.z}) and letting the server path')
            return 'from-range'
        # Why: "nowhere to stand" has 3 causes: the ring is off the loaded scene, the scene calls it all blocked, or the flood can't get there from this pocket. The counts tell them apart.
        in_scene = len([tile for tile in candidates if reachability.probeable(tile)])
        walkable = len([tile for tile in candidates if reachability.walkable(tile)])
        note(f'nowhere to stand beside {at.x},{at.z} ({len(candidates)} ring, {in_scene} in scene, {walkable} walkable, 0 reachable)')
        return 'no'
    pick = sides[skip % len(sides)]
    exact = skip % len(sides) < len(strict)
    # Why: the ring is cardinal because `reachRectangle` takes nothing else, and radius 1 lands on the diagonal next to it, where the op answers "You can't do that from here."
    # Why: walkResilient logs a dozen lines a walk; the caller keeps one.
    _w8 = yield from traversal.walk_resilient(pick, radius=(0 if exact else 1), attempts=1, timeout_ms=20000)
    if _w8:
        note(f'stood@{(here().x if here() is not None else None)},{(here().z if here() is not None else None)}')
        return 'stood'
    note(f'could not stand at {pick.x},{pick.z}')
    return 'no'


def hops_toward(dest, from_):
    """Obstacles in the scene: the ones worth a walk first, everything else behind the item-uses."""
    found = []
    jumps = []
    filtered = 0
    mine = chebyshev(from_, dest)
    for kind in HOP_KINDS:
        all_ = locs.query().where(lambda loc: loc.id == kind.loc and (kind.below is None or loc.tile().z < kind.below)).action(kind.op).within(HOP_SEARCH).results()
        at_dest_level = Tile(from_.x, from_.z, dest.level)
        # Why: a seam struck off by its kind's `when` is invisible later, so a fully filtered pocket would read as a scene with no seams. The count tells them apart.
        kept = [loc for loc in all_ if not kind.when or kind.when(dest, at_dest_level, loc.tile())]
        filtered += len(all_) - len(kept)
        for loc in kept:
            # Why: a telejump whose best end lands by the destination leads however far off its door stands, and one whose ends are all worse goes to the back. The route to the railings needs one of each, in that order.
            # Why: a landing you're already standing on isn't a gain. The cage into the mud cell lands in that cell, so from inside it would lead the list and take you back out.
            ends = kind.landing(loc.tile()) if kind.landing is not None else []
            lands = [tile for tile in ends if chebyshev(tile, from_) > MIN_GAIN]
            best = (None if len(lands) == 0 else min([chebyshev(tile, dest) for tile in lands]))
            ((jumps if best is not None and best + MIN_GAIN <= mine else found)).append(loc)

    # Why: sorting by the obstacle's distance to the target is what encodes "forward".
    # Why: "any obstacle closer than I am" picks marginal ones that cross sideways and drift the route 20 tiles the wrong way.
    # Why: an obstacle in the scene may not be walkable from this pocket. The second cavern's stone bridges sit behind its locked cages and closer to the target, 18 seconds each to prove unreachable; the scene's collision flags answer that for free.
    # Why: a seam can be the only way on while further from the target than you are: the pipe into the boulder's pocket is 16 tiles from the boulder with you 14 away on the wrong side. So gain is a preference, seams that gain come first and the rest follow, and `spent` stops the circles.
    # Why: the scene's verdict orders too: it called a bridge 140 tiles of walking away "walled off" and dropped it. The only hard filter is whether the loc is in the scene.
    def by_distance(loc):
        return chebyshev(loc.tile(), dest)

    def gains(loc):
        return chebyshev(loc.tile(), dest) + MIN_GAIN <= mine

    def open(loc):
        return seam_open(loc)

    # Why: a telejump is the map's own transition; the door that lands beside the railings is 59 tiles from them, so every gain test ranks it last.
    # Why: reachability outranks gain among the rest, see `rank.ts`. At (2375,9644) the mud pocket's only exit is the ledge beside you, which gains nothing by straight line and sat behind 7 walled bridges and 10 cages in another cell.
    # Why: a telejump leads on where it lands, unless this pocket can't walk to it. The 2 unicorn tunnels are 21 tiles the wrong way and walled off from the mud pocket.
    ordered = order_seams(found, lambda loc: (Record({'gains': gains(loc), 'open': open(loc)})), lambda loc: chebyshev(loc.tile(), dest))
    return Record({
        'leading': list(sorted([_x for _x in jumps if open(_x)], key=by_distance)) + list([loc for loc in ordered if gains(loc) and open(loc)]),
        'trailing': list([loc for loc in ordered if not (gains(loc) and open(loc))]) + list(sorted([loc for loc in jumps if not open(loc)], key=by_distance)),
        'filtered': filtered,
    })


# Why: a leg that stops moving has to say what it was choosing between; every silent `continue` below reads from outside as the module doing nothing.
def tag(loc, dest, mine, state):
    at = loc.tile()
    gain = mine - chebyshev(at, dest)
    return f"{loc.id}@{at.x},{at.z}{str(('+' if gain >= 0 else ''))}{gain}" + (('' if state == 'fresh' else f':{state}')) + (('' if seam_reachable(at) else ':walled'))


# Why: one line: the harness surfaces a bounded number of log lines per poll, so 20 of them arrive as the last one.
def shortlist(name, list_, dest, mine, state):
    if len(list_) == 0:
        return f'{name} none'
    shown = ' '.join([tag(loc, dest, mine, state(loc)) for loc in list_[0:6]])
    return f"{name} {shown}{str((f' +{len(list_) - 6}' if len(list_) > 6 else ''))}"


# Why: Use the collision navigator for route checks; `walkResilient` can spend nine seconds and move the player while probing.
def pack_route(from_, to):
    return navigator.find_path(from_, to, policy=NO_TELEPORTS).ok


# Why: a seam's own tile is blocked so a route to it never reports ok; its cardinal neighbours are what a walk can reach.
def pack_route_beside(from_, at):
    return any([pack_route(from_, Tile(at.x + dx, at.z + dz, at.level)) for dx, dz in [[1, 0], [-1, 0], [0, 1], [0, -1]]])


def kind_of(loc):
    _v16 = ([k for k in HOP_KINDS if k.loc == loc.id] or [None])[0]
    return (_v16 if _v16 is not None else None)


# Why: one key for the freshness filter and the spend. The ledge is 6 locs collapsed by `group`, and keying the two differently made a ledge spent from one loc read fresh on the next.
def seam_key(loc):
    at = loc.tile()
    span = (kind_of(loc).group if kind_of(loc) is not None else None)
    return (f'{loc.id}@{at.x},{at.z}' if span is None else f'{loc.id}@{(at.x // span)},{(at.z // span)}')


def try_hops(list_, dest, from_, log, spent):
    """Cross one obstacle toward `dest`. Returns false when none makes progress. Why: the test is distance to `dest`, since the op-click walks you before its script resolves and a tile change is usually the approach. A failed roll leaves you where you were, so the locks get their retries."""
    # Why: the 2 silent `continue`s below can skip every candidate before an op is sent, which from outside looks like the step never ran, so they're counted.
    skipped = []
    for obstacle in list_:
        at = obstacle.tile()
        key = seam_key(obstacle)
        # Why: a stand you can still walk to is on this side of the seam, so skip seams spent from this pocket and keep the one that let you in.
        if spent_here(spent, key, lambda tile: reachability.can_reach(Tile(tile.x, tile.z, tile.level), adjacent_ok=False, max_steps=REACH.max_steps)):
            skipped.append(f'{obstacle.id}@{at.x},{at.z}:spent-here')
            continue
        kind = kind_of(obstacle)
        if not kind:
            skipped.append(f'{obstacle.id}@{at.x},{at.z}:no-vocabulary')
            continue
        op = kind.op
        now = from_
        # Why: every one of these refuses in words: "You can't do that from here", "I can't reach that!", "The rock is being used". "did not cross" alone hides which.
        mark = game_messages.mark()
        # Why: one line per attempt: the harness surfaces a bounded number of log lines per tick, so 4 tries plus walks would arrive as the last one.
        trace = []
        stood = False
        # Why: the tile the op was sent from is the side the seam is spent on, and the one the far side can't walk to.
        stand = None
        # Why: an op sent from range walks you before its script runs and the approach alone clears any distance test, so measure the crossing from where that walk stopped.
        origin = from_
        _fn17 = getattr(kind, 'stands', None)
        _v18 = (_fn17(at) if _fn17 is not None else None)
        named = (_v18 if _v18 is not None else [])
        # Why: `~open_and_close_door2` teleports you 1 tile across the edge, and the 2-tile floor only exists to tell a crossing from the approach walk. A named stand has no approach, so 1 tile is the floor there and `left` carries the rest.
        moved = (1 if len(named) > 0 else 2)
        for attempt in range(((kind.tries if kind.tries is not None else 1))):
            placed = yield from stand_beside(obstacle.tile(), dest, lambda m: trace.append(m), attempt, named)
            if placed == 'no':
                break
            stood = True
            _v19 = here()
            stand = (_v19 if _v19 is not None else stand)
            # Why: the walk to the stand isn't the crossing either; a ring tile 14 tiles off clears every distance test on its own.
            origin = (stand if stand is not None else from_)
            from_range = placed == 'from-range'
            # Why: a seam is often a row of identical locs (the ledge is 6) and the one picked isn't the one you end up beside. `reachRectangle` takes a cardinal side only, and `nearest()` can't tell diagonal from cardinal at distance 1, so the server answered "I can't reach that!".
            # Why: never for a named stand. A railing's stand is the door's own tile and the cage's other door is 1 tile off, so "whatever is cardinal" sends the op at the north door from the south one, which opens nothing.
            me = here()
            cardinal = (None if me is None or len(named) > 0 else ([loc for loc in locs.query().where(lambda loc: loc.id == obstacle.id).action(op).within(2).results() if abs(loc.tile().x - me.x) + abs(loc.tile().z - me.z) == 1] or [None])[0])
            adjacent = (cardinal if cardinal is not None else obstacle)
            if not (adjacent.interact(op)):
                trace.append('the op would not send')
                break
            # Why: the chatbox beats the tile: the script speaks in the tick the op resolves, then moves you. Waiting on the tile alone cost a refused obstacle 6 ticks plus the crossing timeout.
            _w20 = yield from settle_walk(lambda: verdict_since(mark) is not None)
            _v21 = (_w20)
            now = (_v21 if _v21 is not None else now)
            said = verdict_since(mark)
            # Why: a refusal from range is the server's path search saying no, and a second identical click can't change it; the retries are for skill rolls.
            ranged_refusal = from_range and game_messages.saw_since(mark, CANT_REACH)
            if from_range:
                origin = now
                stand = now
                trace.append(f'walked@{now.x},{now.z}')
            trace.append(f"try{attempt + 1}@{now.x},{now.z}{str(('' if said is None else f':{said}'))}")
            if chebyshev(now, origin) >= moved:
                break
            # Why: "You can't do that from here" is the server refusing the side, and every cooldown in the pass refuses for 3 to 15 ticks. Neither improves by waiting, so move to the next seam.
            if said == 'refused' or ranged_refusal:
                break
            # Why: a failed roll leaves you where you were, so the next try goes out this tick with no empty crossing timeout first.
            if said == 'failed':
                continue
            # Why: the walk can stop while the script is still running: the locked cages roll thieving over a 2-tick delay, and the pipes run 2 exactmoves and a telejump. An announced crossing gets the script's own time and ends once you've moved far enough; a silent op gets a short look.
            yield from execution.delay_until(lambda: chebyshev((here() if here() is not None else origin), origin) >= moved, (CROSS_TIMEOUT_MS if said == 'crossing' else QUIET_MS))
            _v24 = here()
            now = (_v24 if _v24 is not None else now)
            trace.append(f'then@{now.x},{now.z}')
            if chebyshev(now, origin) >= moved:
                break
        yield from settle_scene()
        # Why: 2 tiles isn't proof for a door: the slave cages stand on the corridor they open off, so walking round one clears any distance test. A crossing leaves the pocket (`~open_and_close_door2` shuts behind you, a ledge or bridge puts a chasm in the way), so the stand has to be somewhere you can no longer walk to.
        # Why: can't ask while the crossing is running. `~agility_exactmove` merges the seam into the player for the animation and `locChangeUnchecked` calls `collision.delLoc` for the 60-cycle window, the 2 ticks `settleScene` waits, so a flood then walks straight through the seam's tile. Poll: a crossing turns the answer true when the loc comes back, a failure runs the window out.
        # Why: only a crossing is worth polling for. A refusal or failed roll leaves you on the near side by its own account, so one look answers it.
        stand_tile = (None if stand is None else Tile(stand.x, stand.z, stand.level))

        def gone():
            return not reachability.can_reach(stand_tile, adjacent_ok=False, max_steps=REACH.max_steps)

        settle = (CROSS_SETTLE_MS if verdict_since(mark) == 'crossing' else (QUIET_MS if verdict_since(mark) is None else 0))
        # Why: `settle` runs before the veto below because a crossing in flight has to land before the stand can be judged.
        _c25 = stand_tile is None
        if not _c25:
            if settle == 0:
                _c26 = gone()
            else:
                _w27 = yield from execution.delay_until(gone, settle)
                _c26 = _w27
            _c25 = (_c26)
        left = _c25
        # Why: the crossing lands during that window, so a log that stops at the last try can't tell an approach from a late crossing.
        _v28 = here()
        settled = (_v28 if _v28 is not None else now)
        if chebyshev(settled, now) > 0:
            trace.append(f'settled@{settled.x},{settled.z}')
        now = settled
        # Why: a crossing counts when the script ran. The bridge out of the main cavern lands 84 tiles from the witch's cat from 78 away, and the log says "you manage to cross safely".
        # Why: 2 tiles because the op-click walks you before the script resolves, and a 1-tile drift toward the obstacle is the approach.
        # Why: a failed roll can move you without crossing: the ledge's failure is `p_exactmove(coord, coord + (-1,0))` into the rat pit, 1 tile west into a pocket the stand can't walk back to, which clears both tests. The script's verdict outranks anything measured after.
        verdict = verdict_since(mark)
        if verdict == 'failed' or verdict == 'refused' or chebyshev(now, origin) < moved or not left:
            # Why: a seam you couldn't stand beside is one you were in the wrong pocket for; spending it there blocks the crossing once the route gets you 3 tiles from it.
            if stood and stand:
                spend_from(spent, key, stand)
            said = said_since(mark, 6) or 'nothing'
            log(f'pass: {op} {(obstacle.name if obstacle.name is not None else obstacle.id)} at ({obstacle.tile().x},{obstacle.tile().z})' + f' did not cross toward ({dest.x},{dest.z}) from ({from_.x},{from_.z})' + f" — {' | '.join(trace)} — it said: {said}")
            continue
        # Why: a crossing is spent whether it helped or not, because nothing here can tell which side is useful until the far side is walked, but only from the side it was crossed from or the pocket it leads into has no way out.
        if stand:
            spend_from(spent, key, stand)
        log(f'pass: {op} {(obstacle.name if obstacle.name is not None else obstacle.id)} at ({obstacle.tile().x},{obstacle.tile().z}) → ({now.x},{now.z})' + f' — crossed, {chebyshev(now, origin)} tiles from the stand and it is behind us now')
        return True
    if len(skipped) > 0:
        listed = ' '.join(skipped[0:8])
        log(f'pass: skipped {len(skipped)} of {len(list_)} without sending an op — {listed}')
    return False


def hop_toward(dest, log, spent):
    from_ = here()
    if not from_:
        return False
    _o29 = hops_toward(dest, from_)
    leading = _o29.leading
    trailing = _o29.trailing
    filtered = _o29.filtered

    def state(loc):
        return spent_state_here(spent, seam_key(loc), lambda tile: reachability.can_reach(Tile(tile.x, tile.z, tile.level), adjacent_ok=False, max_steps=REACH.max_steps))

    def fresh(list_):
        return [loc for loc in list_ if state(loc) == 'fresh']

    mine = chebyshev(from_, dest)
    back = [loc for loc in list(leading) + list(trailing) if state(loc) == 'elsewhere']
    # Why: the shortlist before anything is tried, so a quiet leg says what it chose between. The filtered count covers seams a kind's `when` removed, or an emptied list looks like a pocket with no seams.
    log(f'pass: at ({from_.x},{from_.z}) → ({dest.x},{dest.z}) d{mine} —' + f" {shortlist('lead', fresh(leading), dest, mine, state)}" + f" | {shortlist('trail', fresh(trailing), dest, mine, state)}" + f" | {shortlist('back', back, dest, mine, state)}" + ((f' | {filtered} not for this journey' if filtered > 0 else '')))
    _w30 = yield from try_hops(fresh(leading), dest, from_, log, spent)
    if _w30:
        return True
    # Why: the rope swing and spade dig are each the only way out of their pocket, and a walled-off seam costs a second of floods to disprove, so item-uses go ahead of seams nothing can reach.
    _w31 = yield from use_seam_toward(dest, log)
    if _w31:
        return True
    _w32 = yield from try_hops(fresh(trailing), dest, from_, log, spent)
    if _w32:
        return True
    # Why: the way back goes last. A pocket with nothing fresh is a dead end and backing out is the only move; one with anything fresh spends that first, or the route swings between 2 sides of one bridge.
    if len(back) > 0:
        log(f'pass: nothing fresh at ({from_.x},{from_.z}) — backing out over {len(back)} crossing(s) already used')
    _result33 = yield from try_hops(back, dest, from_, log, spent)
    return _result33


# Why: 2 seams are item-uses and both are the only way out of their pocket: the swing east off the bridge shelf onto the grid, and the spade dig south out of the slave cages. They share the vocabulary so the search can pick them.
USE_SEAMS = [
    Record({
    'item': UP_ITEM.ROPE,
    'locs': [UP_LOC.ROCKSWING, UP_LOC.ROCKSWING_ANCHOR],
    'consumes': True,
    'stand': Tile(2462, 9699, 0),
    'landing': Tile(2466, 9699, 0),
    'label': 'rope swing',
}),
    Record({
    'item': UP_ITEM.SPADE,
    'locs': [UP_LOC.MUD_DIG],
    'consumes': False,
    'landing': Tile(2392, 9646, 0),
    'label': 'mud dig',
}),
]


def use_seam_toward(dest, log):
    from_ = here()
    if not from_:
        return False
    # Why: 4 silent `continue`s sit between a carried rope and the swing, so say which one passed on it.
    passed = []
    for seam in USE_SEAMS:
        item = ([inv for inv in inventory.items() if inv.id == seam.item.id] or [None])[0]
        if not item:
            continue
        target = locs.query().where(lambda loc: (loc.id in seam.locs)).within(HOP_SEARCH).nearest()
        if not target:
            passed.append(f'{seam.label}: no loc within {HOP_SEARCH}')
            continue
        lands = (seam.landing if seam.landing is not None else target.tile())
        if chebyshev(lands, dest) + MIN_GAIN > chebyshev(from_, dest):
            passed.append(f'{seam.label}@{target.tile().x},{target.tile().z}: lands ({lands.x},{lands.z}), no nearer than d{chebyshev(from_, dest)}')
            continue
        if not seam_reachable(target.tile()):
            passed.append(f'{seam.label}@{target.tile().x},{target.tile().z}: walled off')
            continue
        _c34 = seam.stand
        if _c34:
            _w35 = yield from traversal.walk_resilient(seam.stand, radius=0, attempts=1, timeout_ms=20000)
            _c34 = not (_w35)
        if _c34:
            log(f'pass: could not stand at ({seam.stand.x},{seam.stand.z}) for the {seam.label}')
            continue
        # Why: the op-click walks you to the loc before the use resolves, so "the tile changed" would fire on the walk.
        mark = game_messages.mark()
        before = held(seam.item.id)
        if not (item.use_on(target)):
            continue
        # Why: `%upass_rockswing_used` is a 5-tick cooldown answered by a `~mesbox`, which holds a main modal open and never takes the rope, so waiting on the pack alone burns the full 12 seconds. The refusal is in the chatbox on tick 1.
        _c36 = seam.consumes
        if _c36:
            _w37 = yield from execution.delay_until(lambda: held(seam.item.id) < before or verdict_since(mark) == 'refused', HOP_TIMEOUT_MS)
            _c36 = not (_w37)
        if _c36:
            continue
        if verdict_since(mark) == 'refused' or verdict_since(mark) == 'failed':
            log(f"pass: the {seam.label} refused — {said_since(mark, 3)}")
            continue
        _w38 = yield from settle_walk(lambda: verdict_since(mark) is not None)
        _v39 = (_w38)
        staged = (_v39 if _v39 is not None else from_)
        if chebyshev(staged, dest) + MIN_GAIN > chebyshev(from_, dest):
            yield from execution.delay_until(lambda: chebyshev((here() if here() is not None else from_), from_) >= 2, (CROSS_TIMEOUT_MS if verdict_since(mark) == 'crossing' else QUIET_MS))
        yield from settle_scene()
        _v40 = here()
        now = (_v40 if _v40 is not None else from_)
        # Why: a failed swing spends the rope and drops you in the swamp below, which is no progress.
        if chebyshev(now, from_) < 2:
            log(f'pass: the {seam.label} did not cross toward ({dest.x},{dest.z}) — now at ({now.x},{now.z})')
            continue
        log(f'pass: {seam.label} → ({now.x},{now.z})')
        return True
    if len(passed) > 0:
        log(f"pass: item seams carried but not taken — {'; '.join(passed)}")
    return False


# Why: an op-click can only name a loc in the client's build area, which follows you, so a seam across the pocket is invisible. The mud pocket's only exit is a ledge 18 tiles west while its target lies south, so walking toward the target never sees it. When nothing crosses, sweep the pocket.
# Why: the probe has to land inside the pocket, which is rarely square, so each direction tries falling distances and the furthest walkable one wins.
SWEEP_STEPS = [20, 14, 9, 5]
SWEEP_DIRS = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [-1, 1], [1, -1], [1, 1]]


# Why: the map can't say which platform pocket anything is in at runtime, but the navigator answers "can I walk there" in a millisecond, so your pocket is the side tile you can reach and the target's is the side tile that reaches it.
def links_for(level):
    return (PLATFORM_LINKS if level == 1 else CAVERN_LINKS)


def platform_pocket(from_):
    for link in links_for(from_.level):
        for side in [link.a, link.b]:
            if pack_route(from_, side.tile):
                return side.pocket
    return None


def pocket_of_target(dest):
    for link in links_for(dest.level):
        for side in [link.a, link.b]:
            if pack_route(side.tile, dest):
                return side.pocket
    return None


def platform_step(from_, dest, log):
    """The tile to stand on for the next crossing along the shortest chain of bridges toward `dest`."""
    here = platform_pocket(from_)
    goal = pocket_of_target(dest)
    if here is None or goal is None or here == goal:
        # Why: 3 answers all return null, and "not on the baked graph" and "already in the target's pocket" want opposite things from the caller.
        log(f"pass: no baked route — standing in {(here if here is not None else 'a pocket the graph does not name')}," + f" target in {(goal if goal is not None else 'a pocket the graph does not name')}{str((' (same pocket, walk it)' if here is not None and here == goal else ''))}")
        return None
    # Breadth-first over the bridge graph, so the first crossing is the first step of a shortest chain.
    links = links_for(dest.level)
    seen = set([here])
    frontier = []
    for link in links:
        for side, far in [[link.a, link.b], [link.b, link.a]]:
            if side.pocket == here and not (far.pocket in seen):
                seen.add(far.pocket)
                frontier.append(Record({'pocket': far.pocket, 'first': side.tile}))
    while len(frontier) > 0:
        hit = ([f for f in frontier if f.pocket == goal] or [None])[0]
        if hit:
            log(f'pass: platform route {here} → {goal}, standing at ({hit.first.x},{hit.first.z})')
            return hit.first
        next_ = []
        for step in frontier:
            for link in links:
                for side, far in [[link.a, link.b], [link.b, link.a]]:
                    if side.pocket == step.pocket and not (far.pocket in seen):
                        seen.add(far.pocket)
                        next_.append(Record({'pocket': far.pocket, 'first': step.first}))
        frontier = next_
    log(f'pass: no chain of bridges from {here} to {goal}')
    return None


# Why: on the platforms the solved route is the authority. The free search alternates between the cat and the witch's door, and since the spent set is keyed by destination every switch wipes the memory of used crossings.
def cross_by_route(from_, dest, log):
    stand = platform_step(from_, dest, log)
    if not stand:
        return False
    if not pack_route(from_, stand):
        log(f'pass: no route to the crossing tile ({stand.x},{stand.z}) from ({from_.x},{from_.z})')
        return False
    _w42 = yield from traversal.walk_resilient(stand, radius=0, attempts=2, timeout_ms=60000)
    if not (_w42):
        log(f'pass: could not reach the crossing tile ({stand.x},{stand.z})')
        return False
    on_platforms = dest.level == 1
    op = ('Cross' if on_platforms else 'Climb-over')
    bridge = locs.query().where(lambda loc: ((loc.id == UP_LOC.COLLAPSED_A or loc.id == UP_LOC.COLLAPSED_B if on_platforms else loc.id == UP_LOC.ROCKSLIDE))).action(op).within(6).nearest()
    if not bridge:
        log(f'pass: no bridge within reach of the crossing tile ({stand.x},{stand.z})')
        return False
    _v43 = here()
    before = (_v43 if _v43 is not None else from_)
    if not (bridge.interact(op)):
        return False
    _w44 = yield from settle_walk()
    _v45 = (_w44)
    after = (_v45 if _v45 is not None else before)

    def _fn46():
        t = here()
        return t is not None and chebyshev(t, before) >= 2
    yield from execution.delay_until(_fn46, CROSS_TIMEOUT_MS)
    yield from settle_scene()
    _v47 = here()
    now = (_v47 if _v47 is not None else after)
    if chebyshev(now, before) < 2:
        log(f'pass: the routed bridge at ({bridge.tile().x},{bridge.tile().z}) did not carry anyone')
        return False
    log(f'pass: routed across ({bridge.tile().x},{bridge.tile().z}) → ({now.x},{now.z})')
    return True


def sweep_probes(from_):
    """The furthest walkable tile in each direction."""
    probes = []
    for dx, dz in SWEEP_DIRS:
        for step in SWEEP_STEPS:
            tile = Tile(from_.x + dx * step, from_.z + dz * step, from_.level)
            if chebyshev(tile, from_) > 3 and reachability.can_reach(tile, True):
                probes.append(tile)
                break
    return probes


def sweep_pocket(dest, log, spent):
    """Walk to the pocket's edge in each direction, looking for a crossing that was out of sight."""
    from_ = here()
    if not from_:
        return False
    # Why: a compass probe follows where the pocket extends, which in the main cavern is a corridor away from the bridge 15 tiles north. Walking at a seam the scene can see but not reach carries the build area to it.
    # Why: the client's flood called the collapsed bridge walled off from 29 tiles inside the same pocket, which the collision pack says is one walk, so every seam in the scene gets walked at with the budget of that walk.
    skipped = 0
    for loc in sorted(seams_in_scene(SWEEP_SEARCH), key=lambda a: chebyshev(a.tile(), dest)):
        _v48 = here()
        if not pack_route_beside((_v48 if _v48 is not None else from_), loc.tile()):
            skipped += 1
            continue
        _w50 = yield from traversal.walk_resilient(loc.tile(), radius=8, attempts=2, timeout_ms=60000)
        if not (_w50):
            continue
        log(f'pass: closed on {(loc.name if loc.name is not None else loc.id)} at ({loc.tile().x},{loc.tile().z}) — now at ({(here().x if here() is not None else None)},{(here().z if here() is not None else None)})')
        _w51 = yield from hop_toward(dest, log, spent)
        if _w51:
            return True
    # Why: the crossing off a platform can be 140 tiles off, past any scene, so known bridge placements get walked at too, nearest the target first. The walker refuses other components in a second each.
    if skipped > 0:
        log(f'pass: {skipped} seam(s) in the scene the pack has no route to from ({(here().x if here() is not None else None)},{(here().z if here() is not None else None)}) — not walked at')
    probes = sorted(sweep_probes(from_), key=lambda a: chebyshev(a, dest))
    log(f'pass: sweeping {len(probes)} edge(s) of the pocket at ({from_.x},{from_.z})')
    for probe in probes:
        _w53 = yield from traversal.walk_resilient(probe, radius=4, attempts=1, timeout_ms=30000, log=log)
        if not (_w53):
            continue
        log(f'pass: swept to ({(here().x if here() is not None else None)},{(here().z if here() is not None else None)}) looking for a crossing out of sight')
        _w54 = yield from hop_toward(dest, log, spent)
        if _w54:
            return True
    return False


# Why: `spent` outlives one call: each decide cycle starts a fresh `travelTo` and a seam that led nowhere last cycle is nearest again this cycle. Dropped once the destination is reached or changes.
spent_by_dest = {}


def travel_to(dest, radius, log):
    dest_key = f'{dest.x},{dest.z},{dest.level}'
    if not (dest_key in spent_by_dest):
        spent_by_dest.clear()
        spent_by_dest[dest_key] = {}
    spent = spent_by_dest.get(dest_key)
    # Why: once the navigator says there's no route, asking again costs a full walk timeout per obstacle; only a crossing changes the answer.
    nav_worth_trying = True
    start = here()
    log(f'pass: leg to ({dest.x},{dest.z},{dest.level}) r{radius} from ({(start.x if start is not None else None)},{(start.z if start is not None else None)}) — {len(spent)} seam(s) already spent this leg')
    for hop in range(MAX_HOPS):
        at = here()
        if at and at.level == dest.level and dest.distance_to(at) <= radius:
            spent_by_dest.pop(dest_key, None)
            log(f'pass: arrived at ({at.x},{at.z}), within {radius} of ({dest.x},{dest.z}) after {hop} crossing(s)')
            return True
        # Why: 24 hops can run before the cap, and without the number a repeating log can't be told from a loop that isn't advancing.
        log(f'pass: hop {hop + 1}/{MAX_HOPS} at ({(at.x if at is not None else None)},{(at.z if at is not None else None)}), d{(chebyshev(at, dest) if at else -1)} to go' + f" — {('walking it first' if nav_worth_trying else 'the pack has no route, crossing instead')}")
        if nav_worth_trying:
            _w55 = yield from traversal.walk_resilient(dest, radius=radius, attempts=1, timeout_ms=60000, log=log)
            if _w55:
                log(f'pass: walked the rest of the way to ({dest.x},{dest.z})')
                return True
            nav_worth_trying = False
        # Why: the derived route first. Every crossing has a fixed stand and landing that `tools/nav/upass-areas.ts` reads off the map and scripts, so the area you stand in names the action. The free search below stays for legs that aren't loc ops: the fire arrow, the spiked grid, the orb corridor.
        if at and at.level == dest.level:
            took = yield from cross_once(dest, log)
            if took == 'crossed':
                _v56 = here()
                nav_worth_trying = pack_route((_v56 if _v56 is not None else at), dest)
                continue
            if took == 'same':
                continue
            # Why: stepping back onto the graph can end in the destination's own pocket, and the free search below would then take a tunnel door beside the target rather than walk to it. This departs from rs2b0t.
            now = here()
            if now is not None and (now.x != at.x or now.z != at.z):
                nav_worth_trying = pack_route(now, dest)
                if nav_worth_trying:
                    continue
        # Why: the platforms first because their route is solved.
        _c57 = at and at.level == dest.level
        if _c57:
            _w58 = yield from cross_by_route(at, dest, log)
            _c57 = (_w58)
        if _c57:
            _v59 = here()
            nav_worth_trying = pack_route((_v59 if _v59 is not None else at), dest)
            continue
        _w61 = yield from hop_toward(dest, log, spent)
        _c60 = not (_w61)
        if _c60:
            _w62 = yield from sweep_pocket(dest, log, spent)
            _c60 = not (_w62)
        if _c60:
            stuck = here()
            log(f'pass: STUCK on hop {hop + 1} at ({(stuck.x if stuck is not None else None)},{(stuck.z if stuck is not None else None)}) — nothing in the shortlist crossed and the pocket sweep found nothing new toward ({dest.x},{dest.z})')
            if stuck:
                report_stuck(dest, stuck, log)
            return False
        # Why: a crossing only changes the answer when it was the last seam, so ask the pack (a millisecond) before the walk (9 seconds).
        _v63 = here()
        _v64 = (_v63 if _v63 is not None else at)
        nav_worth_trying = pack_route((_v64 if _v64 is not None else dest), dest)
    log(f'pass: STUCK — {MAX_HOPS} crossings made without reaching ({dest.x},{dest.z}); still at ({(here().x if here() is not None else None)},{(here().z if here() is not None else None)}), {len(spent)} seam(s) spent')
    return False


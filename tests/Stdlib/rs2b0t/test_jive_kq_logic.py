"""rs2b0t's test/scripts: jivekq.test.ts, jivekq-loadout.test.ts, jivekq-search.test.ts and jivekq-stats.test.ts
(MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect. The other jivekq tests stub the client under
the bot; their pure parts are these."""

from rs2004.catalogs import Record
from bots.jivekq.loadout import trip_pack
from bots.jivekq.party import Party, parse_roster
from bots.jivekq.policy import QueenTracker, Supplies, combat_formation, combat_mode, combat_tile, known_dead, lure_tile, queen_phase, retreat_reason
from bots.jivekq.search import QueenSearch, QueenSighting, approach_queen, pull_queen
from bots.jivekq.stats import CombatStats

NAMES = ['one', 'two', 'three', 'four']


def pt(x, z, level=0):
    return {'x': x, 'z': z, 'level': level}


def member(name, trip=1, stage='surface', tile=None, ready=True, session=None, **extra):
    m = {'name': name, 'session': session or name, 'trip': trip, 'stage': stage, 'tile': tile or pt(3226, 3108), 'ready': ready}
    for k, v in extra.items():
        m[k] = v
    return m


def party(self_name='one', session=None, log=None):
    return Party(NAMES, self_name, session or self_name, log)


def all_receive(p, now, **extra):
    for name in NAMES:
        p.receive(member(name, **extra), now)


def spread(tiles):
    for a in tiles:
        for b in tiles:
            if a is not b:
                expect(max(abs(a.x - b.x), abs(a.z - b.z))).to_be_greater_than(5)


def queen(id, health, total=255):
    return Record({'id': id, 'health': health, 'total_health': total})


# policy


def rock_in_the_way():
    tiles = combat_formation(Tile(3476, 9502, 0), 5, 'ranged', lambda p: not (p.x >= 3482 and p.x <= 3485 and p.z == 9502))
    expect(tiles).not_.to_be_null()
    expect(tiles[1]).to_equal(pt(3481, 9502))
    spread(tiles)


def adaptive_cross():
    tiles = combat_formation(Tile(100, 100, 0), 5, 'ranged', lambda p: not (p.x == 106 or p.z == 106))
    expect(tiles).not_.to_be_null()
    spread(tiles)


test('a central rock cannot leave the east ranger trying to stand inside it', rock_in_the_way)
test('adaptive cross never shortens two adjacent arms into splash range', adaptive_cross)
test('an impossible formation is reported instead of walking into a blocked tile forever',
     lambda: expect(combat_formation(Tile(100, 100, 0), 5, 'ranged', lambda p: False)).to_be_null())


# party


def three_cannot_release():
    p = party()
    for name in NAMES[0:3]:
        p.receive(member(name), 100)
    expect(p.release('surface', 1, 100)).to_be_null()


def leader_releases():
    p = party()
    all_receive(p, 100)
    expect(p.release('surface', 1, 100).sessions).to_equal(NAMES)
    p.receive(member('four', tile=pt(3308, 3120)), 101)
    expect(p.release('surface', 1, 101)).to_be_null()


def stale_unready_wrong_trip():
    for override in [{'ready': False}, {'trip': 2}, {'stage': 'bank'}]:
        p = party()
        all_receive(p, 100)
        p.receive(member('four', **override), 100)
        expect(p.release('surface', 1, 100)).to_be_null()
    p = party()
    all_receive(p, 100)
    expect(p.release('surface', 1, 20000)).to_be_null()


def release_survives_descent():
    leader = party('one')
    follower = party('four')
    for name in NAMES:
        leader.receive(member(name), 100)
        follower.receive(member(name), 100)
    release = leader.release('surface', 1, 100)
    follower.receive(member('one', stage='upper', tile=pt(3483, 9510, 2)), 110)
    follower.accept(release.to_message(), 110)
    expect(follower.released('surface', 1, 500)).to_be(True)
    expect(follower.released('surface', 2, 500)).to_be(False)
    expect(follower.released('surface', 1, 20000)).to_be(False)


def old_session_and_garbage():
    p = party('four', 'new-session')
    p.accept({'stage': 'surface', 'trip': 1, 'sessions': NAMES, 'at': 100}, 100)
    expect(p.released('surface', 1, 500)).to_be(False)
    for value in [None, {}, {'name': 'intruder'}, {'name': 'one', 'tile': None}]:
        p.receive(value, 100)
    expect(p.members(100)).to_equal([])


def abort_on_retreat():
    p = party()
    all_receive(p, 100, stage='fight')
    expect(p.unsafe(1, 100)).to_be(False)
    p.receive(member('four', stage='retreat'), 101)
    expect(p.unsafe(1, 101)).to_be(True)
    expect(p.unsafe(1, 20000)).to_be(True)


def restock_keeps_fight():
    p = party()
    all_receive(p, 100, stage='fight')
    p.receive(member('two', stage='retreat', ready=False, restocking=True), 101)
    expect(p.unsafe(1, 101)).to_be(False)
    p.receive(member('two', stage='bank', ready=False, restocking=True), 102)
    expect(p.unsafe(1, 102)).to_be(False)
    p.receive(member('two', stage='bank', ready=True, restocking=True), 103)
    expect(p.unsafe(1, 103)).to_be(False)
    expect(p.release('bank', 2, 103)).to_be_null()
    expect(p.release('upper', 1, 103)).to_be_null()


def restock_hides_nothing():
    p = party()
    all_receive(p, 100, stage='fight')
    p.receive(member('two', stage='bank', ready=True, restocking=True), 101)
    expect(p.unsafe(1, 7000)).to_be(True)
    p.receive(member('two', stage='bank', ready=False, restocking=False, reason='paused'), 102)
    expect(p.unsafe(1, 102)).to_be(True)
    p.receive(member('two', stage='bank', ready=True, restocking=True), 103)
    expect(p.unsafe(1, 103)).to_be(True)


def retreat_cancels_release():
    p = party()
    all_receive(p, 100)
    p.accept(p.release('surface', 1, 100), 100)
    p.receive(member('four', stage='retreat'), 200)
    expect(p.released('surface', 1, 200)).to_be(False)
    p.receive(member('four'), 300)
    expect(p.release('surface', 1, 300)).to_be_null()


def restarted_peer():
    p = party()
    all_receive(p, 100)
    p.accept(p.release('surface', 1, 100), 100)
    p.receive(member('four', session='restarted'), 200)
    expect(p.released('surface', 1, 200)).to_be(False)


def bank_regroup():
    leader = party('one')
    restarted = party('four', 'four-new')
    for name in NAMES:
        m = member(name, stage='bank', tile=pt(3308, 3120), trip=0 if name == 'four' else 4, session='four-new' if name == 'four' else name)
        leader.receive(m, 100)
        restarted.receive(m, 100)
    release = leader.release('bank', 5, 100)
    expect(release).not_.to_be_null()
    restarted.accept(release.to_message(), 100)
    expect(restarted.departure(0, 100)).to_be(5)
    expect(restarted.departure(5, 100)).to_be_null()


def roster_rules():
    expect(parse_roster(' One, TWO, three, four ')).to_equal(NAMES)
    expect(lambda: parse_roster('one,two,three')).to_throw()
    expect(lambda: parse_roster('one,ONE,three,four')).to_throw()
    expect(parse_roster('kq_one, KQ  two,three,four')[0:2]).to_equal(['kq one', 'kq two'])


describe('KQ party', lambda: [
    test('requires four distinct normalized accounts', roster_rules),
    test('three accounts cannot release the entrance', three_cannot_release),
    test('only the leader releases four ready accounts physically at the entrance', leader_releases),
    test('stale, unready and wrong-trip members block release', stale_unready_wrong_trip),
    test('a release survives the leader descending before followers read it', release_survives_descent),
    test('rejects releases for a previous client session and malformed traffic', old_session_and_garbage),
    test('missing, paused and retreating peers abort a fight', abort_on_retreat),
    test('a supplied team keeps fighting while one member escapes and prepares at the bank', restock_keeps_fight),
    test('restocking does not hide a paused or disconnected member', restock_hides_nothing),
    test('a retreat cancels an already-issued descent release', retreat_cancels_release),
    test('a restarted peer cannot use an old release', restarted_peer),
    test('bank regrouping assigns a common next trip to a restarted client', bank_regroup),
])


# combat policy


def stale_zero_bar():
    t = QueenTracker()
    expect(t.observe(queen(1158, 0), 0)[0]).to_be(True)
    expect(t.observe(queen(1160, 0), 0)[0]).to_be(False)
    expect(t.observe(None, 0)[1]).to_be(False)
    t.observe(queen(1160, 180), 0)
    expect(t.observe(queen(1160, 0), 0)[0]).to_be(True)
    expect(t.observe(None, 0)[1]).to_be(True)
    expect(t.observe(None, 0)[1]).to_be(False)


def ranged_cross():
    tiles = [combat_tile(Tile(3488, 9496, 0), 5, slot, 'ranged') for slot in range(4)]
    expect(tiles).to_equal([pt(3482, 9496), pt(3494, 9496), pt(3488, 9502), pt(3488, 9490)])
    spread(tiles)


def respawn_counts():
    t = QueenTracker()
    for _ in range(2):
        t.observe(queen(1158, 255), 0)
        t.observe(queen(1158, 0), 0)
        expect(t.observe(queen(1160, 0), 0)[0]).to_be(False)
        t.observe(queen(1160, 160), 0)
        t.observe(queen(1160, 0), 0)
        expect(t.observe(None, 0)[1]).to_be(True)


def healthy(hp=80, food=10, prayer=40, prayer_doses=4, escape=True, arrows=100):
    return retreat_reason(Supplies(hp=hp, food=food, prayer=prayer, prayer_doses=prayer_doses, escape=escape, arrows=arrows))


describe('KQ combat policy', lambda: [
    test('selects mace crush and bow rapid even though ranged labels are not exposed', lambda: [
        expect(combat_mode('melee', [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Controlled)'), (3, '(Defensive)')])).to_be(1),
        expect(combat_mode('ranged', [(0, '(Accurate)'), (1, '(Rapid)'), (3, '(Longrange)')])).to_be(1),
        expect(combat_mode('ranged', [])).to_be(1),
        expect(combat_mode('melee', None)).to_be_null(),
    ]),
    test('the flying form inherits a stale zero health bar and must still be attacked', stale_zero_bar),
    test('an unobserved health bar does not prevent the first attack', lambda: [
        expect(known_dead(0, 0)).to_be(False),
        expect(known_dead(0, 255)).to_be(True),
        expect(known_dead(10, 255)).to_be(False),
    ]),
    test('the corpse between forms is not a living queen or a kill', lambda: [
        expect(queen_phase(1158)).to_be('melee'),
        expect(queen_phase(1159)).to_be_null(),
        expect(queen_phase(1160)).to_be('ranged'),
    ]),
    test('four players occupy the cardinal edges of the queen footprint',
         lambda: expect([combat_tile(Tile(3488, 9496, 0), 5, slot, 'melee') for slot in range(4)]).to_equal([pt(3485, 9496), pt(3491, 9496), pt(3488, 9499), pt(3488, 9493)])),
    test('ranged cross keeps every player outside the others five-tile splash radius', ranged_cross),
    test('counts another flying queen after respawn without leaving the chamber', respawn_counts),
    test('low HP heals in place; exhausted supplies still require a return', lambda: [
        expect(healthy()).to_be_null(),
        expect(healthy(hp=31)).to_be_null(),
        expect(healthy(hp=1)).to_be_null(),
        expect(healthy(food=0)).to_be_truthy(),
        expect(healthy(prayer=8, prayer_doses=0)).to_be_truthy(),
        expect(healthy(escape=False)).to_be_truthy(),
        expect(healthy(arrows=0)).to_be_truthy(),
    ]),
])


def respawn_clears_kill():
    t = QueenTracker()
    t.observe(queen(1158, 255), 1000)
    t.observe(queen(1160, 200), 5000)
    t.observe(queen(1160, 0), 9000)
    t.observe(None, 10000)
    expect(t.killed_at).to_be(10000)
    expect(t.last_kill_ms).to_be(9000)
    t.observe(queen(1158, 255), 70000)
    expect(t.killed_at).to_be(0)
    t.observe(queen(1160, 200), 75000)
    t.observe(queen(1160, 0), 79000)
    expect(t.observe(None, 80000)[1]).to_be(True)
    expect(t.last_kill_ms).to_be(10000)


def reports_changes():
    messages = []
    p = party(log=lambda m: messages.append(m))
    p.receive(member('two'), 100)
    expect(messages).to_have_length(1)
    p.receive(member('two', tile=pt(3227, 3108)), 200)
    expect(messages).to_have_length(1)
    p.receive(member('two', stage='retreat', ready=False, reason='food reserve reached'), 300)
    expect(messages[-1]).to_contain('food reserve reached')
    expect(messages[-1]).to_contain('two')


def one_release_message():
    messages = []
    p = party(log=lambda m: messages.append(m))
    release = {'stage': 'surface', 'trip': 1, 'sessions': NAMES, 'at': 100}
    p.accept(release, 100)
    p.accept(release, 200)
    expect(messages).to_have_length(1)
    expect(messages[0]).to_contain('surface')
    expect(p.messages).to_equal(messages)


def lure_range():
    for x in range(3464, 3511):
        q = Tile(x, 9498, 0)
        target = lure_tile(q)
        expect(max(abs(target.x - q.x), abs(target.z - q.z)) - 2).to_be_greater_than(15)


test('a respawn clears the prior kill time so the next kill can be counted in the same trip', respawn_clears_kill)
test('team communication reports changes without logging every heartbeat', reports_changes)
test('repeated release broadcasts produce one visible message', one_release_message)
test("lure anchors start beyond either form's attack range", lure_range)


# loot coordination

LOOT_TILE = pt(3477, 9493)
CHAINBODY = {'id': 1113, 'name': 'Rune chainbody', 'tile': LOOT_TILE, 'collecting': False}
ARROWS = {'id': 892, 'name': 'Rune arrow', 'tile': LOOT_TILE, 'collecting': False}


def claim(base, **changes):
    c = {}
    for k, v in base.items():
        c[k] = v
    for k, v in changes.items():
        c[k] = v
    return c


def visible(name, loot='chainbody', **extra):
    """A teammate in the fight on the loot tile, claiming the Rune chainbody unless told another claim or None."""
    m = member(name, stage='fight', tile=LOOT_TILE, **extra)
    if loot is not None:
        m['loot'] = CHAINBODY if loot == 'chainbody' else loot
    return m


def first_viewer_wins():
    p = party()
    for name in NAMES:
        p.receive(visible(name), 100)
    expect(p.loot_collector(1, 100).name).to_be('one')
    p.receive(visible('three', claim(CHAINBODY, collecting=True)), 101)
    expect(p.loot_collector(1, 101).name).to_be('three')
    expect(any(['three collecting Rune chainbody' in m for m in p.messages])).to_be(True)


def stale_collectors():
    p = party('two')
    p.receive(visible('one', claim(CHAINBODY, collecting=True)), 100)
    p.receive(visible('two'), 6200)
    expect(p.loot_collector(1, 6200).name).to_be('two')
    p.receive(visible('one', claim(CHAINBODY, collecting=True)), 6201)
    expect(p.loot_collector(1, 6201).name).to_be('one')
    p.receive(visible('one', stage='retreat', ready=False, restocking=True), 6202)
    expect(p.loot_collector(1, 6202).name).to_be('two')
    expect(p.loot_collector(2, 6202)).to_be_null()


def valuables_preempt_arrows():
    p = party()
    for name in NAMES:
        p.receive(visible(name, ARROWS), 100)
    expect(p.loot_collector(1, 100).name).to_be('one')
    p.receive(visible('three', claim(ARROWS, collecting=True)), 101)
    expect(p.loot_collector(1, 101).name).to_be('three')
    p.receive(visible('two', {'id': 565, 'name': 'Blood rune', 'tile': LOOT_TILE, 'collecting': False}), 102)
    expect(p.loot_collector(1, 102).name).to_be('two')


def private_candidate():
    p = party('three')
    for name in NAMES:
        p.receive(visible(name, CHAINBODY if name == 'three' else None), 100)
    expect(p.loot_collector(1, 100).name).to_be('three')
    p.receive(visible('three', None), 101)
    expect(p.loot_collector(1, 101)).to_be_null()
    expect(p.messages[-1]).to_contain('released loot claim')


def bad_claims():
    p = party()
    for change in [{'id': -1}, {'name': 'Iron arrow'}, {'tile': pt(3308, 3120)}, {'collecting': 'yes'}]:
        p.receive(visible('one', claim(CHAINBODY, **change)), 100)
        expect(p.loot_collector(1, 100)).to_be_null()
    p.receive(visible('visitor'), 100)
    expect(p.loot_collector(1, 100)).to_be_null()


describe('KQ loot coordination', lambda: [
    test('the first eligible viewer wins simultaneous candidates, while an active collector keeps its target', first_viewer_wins),
    test('stale and restocking collectors release the election to a fresh candidate', stale_collectors),
    test('valuable candidates preempt active arrow collectors while Rune arrows still elect one viewer', valuables_preempt_arrows),
    test('a private visible candidate does not assign an unseen drop to the leader', private_candidate),
    test('malformed, other-arrow and outside-room claims cannot take the election', bad_claims),
])


# loadout


def full_packs():
    for slot in range(4):
        pack = {}
        for id, count in trip_pack(slot):
            pack[id] = count
        for id in [2436, 2440, 2442]:
            expect(pack.get(id)).to_be(1)
        expect(pack.get(2552)).to_be(1)
        expect(pack.get(556)).to_be(5)
        expect(pack.get(563)).to_be(1)
        expect(557 in pack).to_be(False)
        expect(sum([1 if id in [1854, 556, 563] else count for id, count in pack.items()])).to_be(28)
        expect(995 in pack).to_be(False)


def ropes_for_the_leader():
    leader = dict(trip_pack(0))
    expect(leader.get(954)).to_be(2)
    expect(leader.get(385)).to_be(14)
    for slot in range(1, 4):
        pack = dict(trip_pack(slot))
        expect(954 in pack).to_be(False)
        expect(pack.get(385)).to_be(16)


test('all four carry super potions and a dueling ring in a full inventory', full_packs)
test('only the leader carries ropes and followers fill those slots with sharks', ropes_for_the_leader)


# search

QUEEN = Tile(3478, 9510, 0)
HERE = Tile(3508, 9493, 0)


def always(p):
    return True


def approach_from_sighting():
    target = QueenSearch().next(HERE, QueenSighting(1160, QUEEN, 1000, False), 1100, always)
    expect(max(abs(target.x - QUEEN.x), abs(target.z - QUEEN.z))).to_be(6)
    expect(target.x).to_be_less_than(HERE.x)


def circuit():
    search = QueenSearch()
    tile = HERE
    visited = set()
    for i in range(6):
        tile = search.next(tile, None, 1000 + i * 1000, always)
        visited.add(f'{tile.x},{tile.z}')
    expect(len(visited)).to_be(6)


def blocked_waypoint():
    search = QueenSearch()
    usable = lambda p: not (p.x == 3488 and p.z == 9496)
    first = search.next(HERE, None, 1000, usable)
    expect(first).not_.to_equal(pt(3488, 9496))
    expect(search.next(HERE, None, 9001, usable)).not_.to_equal(first)


def pull_beyond_range():
    for phase in ['melee', 'ranged']:
        target = pull_queen(QUEEN, phase, lambda p: p.z == QUEEN.z - 2, lambda a, b: True, always)
        expect(target.x).to_be(QUEEN.x)
        expect(target.z).to_be(QUEEN.z - 2 - (18 if phase == 'melee' else 13))


def stalled_pull():
    a = pull_queen(QUEEN, 'ranged', always, lambda f, t: True, always, 0)
    b = pull_queen(QUEEN, 'ranged', always, lambda f, t: True, always, 1)
    expect(a).not_.to_be_null()
    expect(b).not_.to_be_null()
    expect(a).not_.to_equal(b)


def sighting_keeps_time():
    p = party()
    seen = {'id': 1160, 'tile': pt(QUEEN.x, QUEEN.z), 'at': 1000, 'engaged': True}
    m = member('two', stage='fight', tile=pt(HERE.x, HERE.z), queen=seen)
    p.receive(m, 2000)
    expect(p.members(2000)[0].queen).to_equal(seen)
    p.receive(m, 10000)
    expect(p.members(10000)[0].queen).to_be_undefined()


def bad_sightings():
    for seen in [{'id': 1, 'tile': pt(QUEEN.x, QUEEN.z), 'at': 1000, 'engaged': False},
                 {'id': 1160, 'tile': pt(QUEEN.x, QUEEN.z, 2), 'at': 1000, 'engaged': False},
                 {'id': 1160, 'tile': pt(QUEEN.x, QUEEN.z), 'at': 5000, 'engaged': False},
                 {'id': 1160, 'tile': pt(QUEEN.x, QUEEN.z), 'at': 1000, 'engaged': 'true'}]:
        p = party()
        p.receive(member('two', stage='fight', tile=pt(HERE.x, HERE.z), queen=seen), 1000)
        expect(p.members(1000)[0].queen).to_be_undefined()


describe('KQ queen search', lambda: [
    test('a lost queen is approached from the most recent sighting', approach_from_sighting),
    test('an old sighting cannot keep the search pinned to an empty position',
         lambda: expect(QueenSearch().next(HERE, QueenSighting(1160, QUEEN, 1000, False), 10000, always)).to_equal(pt(3488, 9496))),
    test('reaching an empty waypoint continues a circuit of distinct chamber positions', circuit),
    test('an unreachable waypoint uses nearby accessible ground and a stalled step advances', blocked_waypoint),
    test('a search with no accessible floor does not issue a wall destination', lambda: [
        expect(QueenSearch().next(HERE, None, 1000, lambda p: False)).to_be_null(),
        expect(approach_queen(QUEEN, HERE, lambda p: False)).to_be_null(),
    ]),
    test('approach tiles stay outside the queen footprint and obey reachability', lambda: [
        expect(approach_queen(QUEEN, HERE, lambda p: p.x < QUEEN.x).x).to_be_less_than(QUEEN.x),
        expect(max(abs(approach_queen(QUEEN, HERE, lambda p: p.x < QUEEN.x).x - QUEEN.x), abs(approach_queen(QUEEN, HERE, lambda p: p.x < QUEEN.x).z - QUEEN.z))).to_be(6),
    ]),
    test('a pull goes beyond attack range along a valid body route to an open cross', pull_beyond_range),
    test('a narrow blocked body route cannot be used even when the player can stand at its end', lambda: [
        expect(pull_queen(QUEEN, 'ranged', always, lambda f, t: False, always)).to_be_null(),
        expect(pull_queen(QUEEN, 'ranged', lambda p: p.x > QUEEN.x, lambda f, t: t.x > f.x, always)).to_equal(pt(QUEEN.x + 14, QUEEN.z)),
    ]),
    test('a stalled pull tries a different open direction', stalled_pull),
    test('party messages preserve the observation time instead of refreshing old sightings', sighting_keeps_time),
    test('malformed, wrong-floor and future queen reports cannot direct the party', bad_sightings),
])


# stats


def dps_with_eating():
    s = CombatStats()
    s.observe(0, 1000, False)
    s.observe(1000, 1000, True)
    s.observe(3000, 1040, True)
    s.observe(6000, 1040, False)
    expect(s.damage).to_be(10)
    expect(s.fighting_ms).to_be(5000)
    expect(s.dps()).to_be(2)


def dps_undiluted():
    s = CombatStats()
    s.observe(0, 1000, True)
    s.observe(2000, 1040, False)
    s.observe(30000, 1080, False)
    s.observe(60000, 1080, True)
    s.observe(62000, 1120, False)
    expect(s.damage).to_be(20)
    expect(s.fighting_ms).to_be(4000)
    expect(s.dps()).to_be(5)


def dps_never_negative():
    s = CombatStats()
    expect(s.dps()).to_be(0)
    s.observe(1000, 1000, True)
    s.observe(2000, 100, True)
    expect(s.damage).to_be(0)
    expect(s.dps()).to_be(0)


describe('KQ combat stats', lambda: [
    test('DPS counts direct damage and includes time spent eating during the fight', dps_with_eating),
    test('banking, respawn waits and paused time do not dilute combat DPS', dps_undiluted),
    test('XP resets and a newly started script cannot create negative damage or infinite DPS', dps_never_negative),
])

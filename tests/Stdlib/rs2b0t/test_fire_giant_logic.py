"""rs2b0t's test/scripts/FireGiant/FireGiantLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test
and expect. projectiles.test.ts stubs the client's facades, which pocketpy can't; the registry test reads the bot's
own definition instead."""

from bots.firegiant.logic import AP_RANGE, BARREL_EXIT, DEFAULT_MELEE_TILE, DEFAULT_SAFESPOT, DEFAULT_SAFESPOT_FALLBACK, ESCAPE_TELES
from bots.firegiant.logic import EXIT_OPTIONS, LEDGE, POST_ROCK, RAFT_STAND, ROCK_TILE, ROPE_THROW_STAND, THROW_ZONE, WASHED_OUT
from bots.firegiant.logic import attack_range_for, east_first_key, leg_for, loot_wait_ms, room_of, same_room, taken_by_another
import bots.fire_giant as fire_giant


def at(x, z, level=0):
    return Tile(x, z, level)


def cheb(x, z, spot):
    return max(abs(x - spot.x), abs(z - spot.z))


describe('leg_for', lambda: [
    test('anywhere underground is InDungeon', lambda: [
        expect(leg_for(at(2575, 9861))).to_be('InDungeon'),
        expect(leg_for(at(2568, 9893))).to_be('InDungeon'),
    ]),
    test('the exact ledge tile is AtLedge', lambda: expect(leg_for(at(LEDGE.x, LEDGE.z))).to_be('AtLedge')),
    test('the post-rock landing and the tree stand are both PastRock', lambda: [
        expect(leg_for(at(POST_ROCK.x, POST_ROCK.z))).to_be('PastRock'),
        expect(leg_for(at(2512, 3466))).to_be('PastRock'),
    ]),
    test('the engine throw zone is AtLanding, inclusive at every edge', lambda: [
        expect(leg_for(at(2512, 3481))).to_be('AtLanding'),
        expect(leg_for(at(2510, 3476))).to_be('AtLanding'),
        expect(leg_for(at(2514, 3481))).to_be('AtLanding'),
        expect(leg_for(at(2509, 3478))).not_.to_be('AtLanding'),
        expect(leg_for(at(2512, 3482))).not_.to_be('AtLanding'),
    ]),
    test('the shared failure coord is WashedOut', lambda: [
        expect(leg_for(at(WASHED_OUT.x, WASHED_OUT.z))).to_be('WashedOut'),
        expect(leg_for(at(WASHED_OUT.x + 4, WASHED_OUT.z - 4))).to_be('WashedOut'),
    ]),
    test('near the raft is AtRaft', lambda: [
        expect(leg_for(at(RAFT_STAND.x, RAFT_STAND.z))).to_be('AtRaft'),
        expect(leg_for(at(RAFT_STAND.x + 3, RAFT_STAND.z + 3))).to_be('AtRaft'),
    ]),
    test('everything else, and an unknown position, is Surface', lambda: [
        expect(leg_for(at(2725, 3491))).to_be('Surface'),
        expect(leg_for(None)).to_be('Surface'),
    ]),
    test('AtLedge wins over PastRock even though the ledge is close to the rock', lambda: expect(leg_for(at(2511, 3463))).to_be('AtLedge')),
])

# Why: the landing tile passes the engine's inzone check but sits 13 tiles from the rock, past aplocu range, so the
# throw stand must satisfy both zone and op reachability.
describe('ROPE_THROW_STAND', lambda: [
    test('is inside the engine throw zone', lambda: [
        expect(ROPE_THROW_STAND.x).to_be_greater_than_or_equal(THROW_ZONE.min_x),
        expect(ROPE_THROW_STAND.x).to_be_less_than_or_equal(THROW_ZONE.max_x),
        expect(ROPE_THROW_STAND.z).to_be_greater_than_or_equal(THROW_ZONE.min_z),
        expect(ROPE_THROW_STAND.z).to_be_less_than_or_equal(THROW_ZONE.max_z),
    ]),
    test('is north of the rock — the engine refuses coordz(you) <= coordz(rock)', lambda: expect(ROPE_THROW_STAND.z).to_be_greater_than(ROCK_TILE.z)),
    test('is within aplocu range of the rock', lambda: expect(cheb(ROPE_THROW_STAND.x, ROPE_THROW_STAND.z, ROCK_TILE)).to_be_less_than_or_equal(AP_RANGE)),
    test('the raft landing is NOT a legal throw stand — it is out of ap range', lambda: expect(cheb(2512, 3481, ROCK_TILE)).to_be_greater_than(AP_RANGE)),
    test('standing on it still resolves to the AtLanding leg', lambda: expect(leg_for(at(ROPE_THROW_STAND.x, ROPE_THROW_STAND.z))).to_be('AtLanding')),
])

WEST_SPAWNS = [(2562, 9886), (2565, 9887), (2568, 9889)]
EAST_SPAWNS = [(2573, 9895), (2575, 9891), (2577, 9890), (2577, 9897), (2578, 9895), (2580, 9890), (2581, 9895)]


def no_east_spawn_in_the_safespot_room():
    near = [(x, z) for x, z in EAST_SPAWNS if cheb(x, z, DEFAULT_SAFESPOT) <= 10]
    expect(len(near)).to_be_greater_than(0)
    for x, z in near:
        expect(room_of(at(x, z))).not_.to_be(room_of(DEFAULT_SAFESPOT))


# Why: the nearest east-room giant (2573,9895, d=5) outranks two of the three west-room ones, so distance alone can't
# keep the bot in its own room.
describe('room_of', lambda: [
    test('the three west-room spawns are west', lambda: [expect(room_of(at(x, z))).to_be('west') for x, z in WEST_SPAWNS]),
    test('the seven east-room spawns are east', lambda: [expect(room_of(at(x, z))).to_be('east') for x, z in EAST_SPAWNS]),
    test('the default safespot is in the west room with its giants', lambda: expect(room_of(DEFAULT_SAFESPOT)).to_be('west')),
    test('the default melee anchor is in the east room', lambda: expect(room_of(DEFAULT_MELEE_TILE)).to_be('east')),
    test('tiles outside both rooms are null, so the caller falls back to radius', lambda: [
        expect(room_of(at(2575, 9861))).to_be_null(),
        expect(room_of(None)).to_be_null(),
    ]),
    test('no east spawn is within the safespot room, however close', no_east_spawn_in_the_safespot_room),
])

WEST_SPOT = at(2568, 9892)
CENTRE_ANCHOR = at(2575, 9893)
WEST_DROP = at(2565, 9887)
CENTRE_DROP = at(2578, 9895)

# Why: crossing to the next chamber for another player's drop abandons the safespot for the round trip.
describe('same_room', lambda: [
    test('a drop in our own chamber counts', lambda: [
        expect(same_room(WEST_SPOT, WEST_DROP)).to_be(True),
        expect(same_room(CENTRE_ANCHOR, CENTRE_DROP)).to_be(True),
    ]),
    test('a drop in the other chamber does not, from either side', lambda: [
        expect(same_room(WEST_SPOT, CENTRE_DROP)).to_be(False),
        expect(same_room(CENTRE_ANCHOR, WEST_DROP)).to_be(False),
    ]),
    test('a near drop across the divide is still excluded — distance cannot decide this', lambda: [
        expect(cheb(2573, 9895, WEST_SPOT)).to_be_less_than(10),
        expect(same_room(WEST_SPOT, at(2573, 9895))).to_be(False),
    ]),
    test('an anchor outside both chambers accepts anything, so nothing is stranded', lambda: [
        expect(same_room(at(2575, 9861), WEST_DROP)).to_be(True),
        expect(same_room(None, CENTRE_DROP)).to_be(True),
    ]),
])


def in_bow_range(spot):
    return [(x, z) for x, z in WEST_SPAWNS if cheb(x, z, spot) <= attack_range_for('range')]


# Why: 2568,9893 is melee-proof, so it's the tile to drop back to whenever a giant reaches the forward spot.
describe('safespot tiers', lambda: [
    test('the forward spot is 2568,9892 and the fallback is 2568,9893', lambda: [
        expect([DEFAULT_SAFESPOT.x, DEFAULT_SAFESPOT.z, DEFAULT_SAFESPOT.level]).to_equal([2568, 9892, 0]),
        expect([DEFAULT_SAFESPOT_FALLBACK.x, DEFAULT_SAFESPOT_FALLBACK.z, DEFAULT_SAFESPOT_FALLBACK.level]).to_equal([2568, 9893, 0]),
    ]),
    test('they are distinct tiles, or the retreat is a no-op', lambda: expect(DEFAULT_SAFESPOT.equals(DEFAULT_SAFESPOT_FALLBACK)).to_be(False)),
    test('both tiers sit in the west room, so room-gated targeting survives a retreat', lambda: [
        expect(room_of(DEFAULT_SAFESPOT)).to_be('west'),
        expect(room_of(DEFAULT_SAFESPOT_FALLBACK)).to_be('west'),
    ]),
    test('the fallback keeps the west giants inside bow range', lambda: expect(len(in_bow_range(DEFAULT_SAFESPOT_FALLBACK))).to_be_greater_than(0)),
])

# Why: a click beyond weapon range makes the server walk you off the safespot, and ReturnToSafespot drags you back
# before the shot leaves.
describe('attack_range_for', lambda: [
    test('bow reaches 7, magic 10, melee 1', lambda: [
        expect(attack_range_for('range')).to_be(7),
        expect(attack_range_for('mage')).to_be(10),
        expect(attack_range_for('melee')).to_be(1),
    ]),
    test('an unknown style falls back to adjacency rather than a long walk', lambda: expect(attack_range_for('sailing')).to_be(1)),
    test('is shorter than FIELD_RADIUS, so some in-field giants must be leashed first', lambda: expect(attack_range_for('range')).to_be_less_than(10)),
    test('the west giants sit inside bow range of the safespot', lambda: expect(len(in_bow_range(DEFAULT_SAFESPOT))).to_be(len(WEST_SPAWNS))),
])


def order(gs):
    ranked = sorted(gs, key=lambda g: east_first_key(g[0], g[1]))
    return [g[0] for g in ranked]


# The west giants wander up to 3 tiles, so the westmost can read as nearest while a wall blocks line of sight.
# Distance ordering picks it, can't hit it, and the bot dances.
describe('east_first_key', lambda: [
    test('orders the three west giants east to west regardless of distance', lambda: expect(order([(2562, 2), (2568, 9), (2565, 5)])).to_equal([2568, 2565, 2562])),
    test('the westmost giant is never picked first even when it is closest', lambda: expect(order([(2562, 1), (2568, 8)])[0]).to_be(2568)),
    test('equal x falls back to nearest', lambda: expect(sorted([(2568, 7), (2568, 3)], key=lambda g: east_first_key(g[0], g[1]))[0][1]).to_be(3)),
    test('is a stable total order — sorting twice is idempotent', lambda: expect(order([(x, 0) for x in order([(2565, 4), (2568, 6), (2562, 1)])])).to_equal([2568, 2565, 2562])),
])


def e(is_ours=False, in_combat=False, targets_me=False, targets_another=False):
    return taken_by_another(is_ours, in_combat, targets_me, targets_another)


# A giant another player is fighting isn't ours to take: its loot and kill go to them, and diving on it wastes the trip.
describe('taken_by_another', lambda: [
    test('a giant facing another player is taken', lambda: expect(e(targets_another=True)).to_be(True)),
    test('a giant in combat with nobody visible is taken — faceEntity clears between attacks', lambda: expect(e(in_combat=True)).to_be(True)),
    test('a giant in combat with US is not taken', lambda: expect(e(in_combat=True, targets_me=True)).to_be(False)),
    test('an idle giant is free', lambda: expect(e()).to_be(False)),
    test('our own target is never taken, however its faceEntity flickers', lambda: [
        expect(e(is_ours=True, in_combat=True, targets_another=True)).to_be(False),
        expect(e(is_ours=True, in_combat=True, targets_me=False)).to_be(False),
    ]),
])

# The dungeon does have a walk out, the exit door to the ledge and then the barrel. It needs no runes, magic level or
# quest, so it's the default.
describe('EXIT_OPTIONS', lambda: [
    test('the free barrel walk-out is first and is the default', lambda: expect(EXIT_OPTIONS[0]).to_be(BARREL_EXIT)),
    test('the teleports remain selectable alongside it', lambda: [
        expect(EXIT_OPTIONS).to_contain('Camelot'),
        expect(EXIT_OPTIONS).to_contain('Ardougne'),
        expect(len(EXIT_OPTIONS)).to_be(5),
    ]),
])

# Why: Take walks to the drop first, so a flat short wait reports failure while the pickup is still in flight.
describe('loot_wait_ms', lambda: [
    test('an adjacent drop still gets a usable minimum', lambda: expect(loot_wait_ms(0)).to_be_greater_than_or_equal(1000)),
    test('it grows with distance, so a far corpse is not called a failure', lambda: expect(loot_wait_ms(8)).to_be_greater_than(loot_wait_ms(1))),
    # 10 tiles is the field radius; walking that is seconds, not one tick.
    test('a drop at the edge of the field allows for the whole walk', lambda: expect(loot_wait_ms(10)).to_be_greater_than_or_equal(5000)),
    test('a negative distance cannot shorten the wait', lambda: expect(loot_wait_ms(-5)).to_be(loot_wait_ms(0))),
])


def every_tele():
    for key, tele in ESCAPE_TELES.items():
        expect(tele.name).to_be(key)
        expect(tele.level).to_be_greater_than(0)
        expect(len(tele.runes)).to_be_greater_than(0)
        expect(tele.bank.level).to_be(0)


def ardougne_runes():
    runes = {}
    for rune, count in ESCAPE_TELES['Ardougne'].runes:
        runes[rune] = count
    expect(runes['Law rune']).to_be(2)
    expect(runes['Water rune']).to_be(2)


describe('ESCAPE_TELES', lambda: [
    test('every entry carries a name, level, runes, and a paired bank', every_tele),
    test('Camelot is the documented default pairing', lambda: [
        expect(ESCAPE_TELES['Camelot'].level).to_be(45),
        expect(ESCAPE_TELES['Camelot'].bank.x).to_be(2725),
        expect(ESCAPE_TELES['Camelot'].bank.z).to_be(3491),
    ]),
    test('Ardougne costs 2 law and 2 water', ardougne_runes),
])

describe('registry', lambda: [
    test('FireGiant registers under Combat with its settings schema', lambda: [
        expect(fire_giant.BOT.category).to_be('Combat'),
        expect(fire_giant.SETTINGS['escape_tele'].default).to_be(BARREL_EXIT),
        expect(fire_giant.SETTINGS['combat_style'].options).to_equal(['melee', 'mage', 'range']),
    ]),
])

test('ranged attacks respect thrown weapon reach at the safespot', lambda: [
    expect(attack_range_for('range', 'Rune dart')).to_be(3),
    expect(attack_range_for('range', 'Rune knife')).to_be(3),
    expect(attack_range_for('range', 'Rune javelin')).to_be(5),
    expect(attack_range_for('range', 'Rune thrownaxe')).to_be(4),
    expect(attack_range_for('range', 'Crossbow')).to_be(10),
])

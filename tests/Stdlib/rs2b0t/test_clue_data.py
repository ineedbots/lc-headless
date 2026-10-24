"""rs2b0t's test/api/ai/clues: cluelogic.test.ts, hardClueKit.test.ts, packPlan.test.ts, toolAcquire.test.ts,
data/toolAcquire.test.ts and talk-anchors.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect."""

from rs2004.catalogs import Record
from rs2004.clues.data import CLUE_DB, TALK_ANCHORS, identify_step
from rs2004.clues.plan import COORD_TOOL_SLOTS, TELEPORT_CASTS, TRAIL_FOOD_CAP, GuardianRangedLoadout, HardKitSnapshot, casket_reward_slots
from rs2004.clues.plan import hard_clue_kit, hard_trail_food_target, superanti_doses, teleport_rune_target, trail_food_target, weapon_needed
from rs2004.clues.tools import KOJO, MURPHY, PROFESSOR, SPADE_NAME, SPADE_SPAWNS, TRIO, next_coord_tool, trail_kit

# ClueLogic

SEARCH = {'obj': 'trail_clue_easy_simple001', 'id': 100, 'type': 'search', 'coord': Tile(1, 2, 0)}
DIG = {'obj': 'trail_clue_easy_map001', 'id': 200, 'type': 'dig', 'casket_obj': 'map001_casket', 'casket_id': 201, 'coord': Tile(3, 4, 0)}
DB = {100: SEARCH, 200: DIG}
CASKETS = {201: 'map001_casket'}
OPEN = {'type': 'open-casket', 'casket_obj': 'map001_casket', 'casket_id': 201}

test('a held casket beats a held clue (clue listed first still yields open-casket)', lambda: expect(identify_step([100, 201], DB, CASKETS)).to_equal(OPEN))
test('a held casket yields an open-casket step', lambda: expect(identify_step([201], DB, CASKETS)).to_equal(OPEN))
test('a held clue yields its row', lambda: [
    expect(identify_step([100], DB, CASKETS)).to_be(SEARCH),
    expect(identify_step([200], DB, CASKETS)).to_be(DIG),
])
test('unknown ids yield None', lambda: expect(identify_step([999, 888], DB, CASKETS)).to_be_null())
test('empty held ids yield None', lambda: expect(identify_step([], DB, CASKETS)).to_be_null())

# hardClueKit


def item(id, count, name=None):
    return Record({'id': id, 'count': count, 'name': name})


READY = [item(1231, 1), item(185, 1), item(385, 15)]


def kit(items=None, attack=60, lost_city=True, ranged=None):
    return HardKitSnapshot(attack, lost_city, items if items is not None else READY, ranged)


def ranged_kit():
    ranged = GuardianRangedLoadout('Magic shortbow', 'Rune arrow', 500, 1)
    items = [item(861, 1, 'Magic shortbow'), item(892, 20, 'Rune arrow')] + READY[1:]

    def without(id):
        return kit([i for i in items if i.id != id], 1, False, ranged)

    expect(hard_clue_kit(kit(items, 1, False, ranged))).to_be('ready')
    expect(hard_clue_kit(without(892))).to_be('ammo')
    expect(hard_clue_kit(without(861))).to_be('weapon')
    expect(hard_clue_kit(without(385))).to_be('sharks')


describe('hard_clue_kit', lambda: [
    test('rejects a kit missing an item', lambda: [expect(hard_clue_kit(kit([i for i in READY if i.id != id]))).not_.to_be('ready') for id in [1231, 185, 385]]),
    test('rejects fourteen Sharks and accepts fifteen', lambda: [
        expect(hard_clue_kit(kit(READY[0:2] + [item(385, 14)]))).to_be('sharks'),
        expect(hard_clue_kit(kit())).to_be('ready'),
    ]),
    test('accepts every Superantipoison dose', lambda: [expect(hard_clue_kit(kit([READY[0], item(id, 1), READY[2]]))).to_be('ready') for id in [2448, 181, 183, 185]]),
    test('does not substitute ordinary antipoison', lambda: [
        expect(superanti_doses([item(2446, 1)])).to_be(0),
        expect(superanti_doses([item(2448, 1), item(181, 1), item(183, 1), item(185, 1)])).to_be(10),
    ]),
    test('requires Attack 60 and Lost City', lambda: [
        expect(hard_clue_kit(kit(attack=59))).to_be('attack'),
        expect(hard_clue_kit(kit(lost_city=False))).to_be('lost-city'),
    ]),
    test('allows either dragon dagger and the dragon longsword', lambda: [
        expect(hard_clue_kit(kit([item(1215, 1)] + READY[1:]))).to_be('ready'),
        expect(hard_clue_kit(kit([item(1305, 1)] + READY[1:]))).to_be('ready'),
    ]),
    test('rejects unsupported weapons and zero-count guardian weapons', lambda: [
        expect(hard_clue_kit(kit([item(1333, 1)] + READY[1:]))).not_.to_be('ready'),
        expect(hard_clue_kit(kit([item(1305, 0)] + READY[1:]))).not_.to_be('ready'),
    ]),
    test('a ranged hard-clue kit needs its configured bow and ammo, without melee unlocks', ranged_kit),
    test('reserves the mandatory thirteen slots without lowering the minimum', lambda: [
        expect(hard_trail_food_target(0, 15, 0)).to_be(15),
        expect(hard_trail_food_target(0, 21, 1)).to_be(15),
        expect(hard_trail_food_target(0, 14, 0)).to_be_null(),
    ]),
])

# packPlan


def food(host_want=20, held_food=0, free_slots=22, reserve_slots=0):
    return trail_food_target(host_want, held_food, free_slots, reserve_slots)


describe('trail_food_target', lambda: [
    test('caps a grind-sized request down to trail size', lambda: expect(food(host_want=20)).to_be(TRAIL_FOOD_CAP)),
    test('a host asking for less than the cap still gets what it asked for', lambda: expect(food(host_want=6)).to_be(6)),
    test('never takes slots the coord tools still need', lambda: expect(food(free_slots=5, reserve_slots=COORD_TOOL_SLOTS)).to_be(2)),
    test('a pack with no room takes no food', lambda: [
        expect(food(free_slots=0)).to_be(0),
        expect(food(free_slots=2, reserve_slots=COORD_TOOL_SLOTS)).to_be(0),
    ]),
    test('food already held counts toward the target rather than being re-bought', lambda: [
        expect(food(held_food=8, free_slots=0)).to_be(8),
        expect(food(held_food=12, free_slots=0)).to_be(TRAIL_FOOD_CAP),
    ]),
    # A hard coord clue aboard: clue, spade, trio and coins are 6 of 28.
    test('the whole point: a 20-food host leaves room for the 5 teleport runes', lambda: expect(22 - food(host_want=20, free_slots=22)).to_be_greater_than_or_equal(5)),
])

describe('weapon_needed', lambda: [
    test('not needed when it is already worn (the duplicate-weapon bug)', lambda: expect(weapon_needed('Rune scimitar', False, True)).to_be(False)),
    test('not needed when it is already in the pack', lambda: expect(weapon_needed('Rune scimitar', True, False)).to_be(False)),
    test('needed when the account has none', lambda: expect(weapon_needed('Rune scimitar', False, False)).to_be(True)),
    test('a host with no weapon never withdraws one', lambda: expect(weapon_needed('', False, False)).to_be(False)),
])

describe('casket_reward_slots', lambda: [
    test('covers the worst roll of each tier', lambda: [
        expect(casket_reward_slots('trail_clue_easy_map001_casket')).to_be(4),
        expect(casket_reward_slots('trail_clue_medium_sextant004_casket')).to_be(5),
        expect(casket_reward_slots('trail_clue_hard_sextant001_casket')).to_be(6),
    ]),
    test('an unrecognised casket still reserves the easy-tier minimum', lambda: expect(casket_reward_slots('mystery_casket')).to_be(4)),
])

describe('teleport_rune_target', lambda: [
    test('a trail carries twenty casts of each teleport it can make', lambda: [
        expect(TELEPORT_CASTS).to_be(20),
        expect(teleport_rune_target(1)).to_be(20),
        expect(teleport_rune_target(3)).to_be(60),
    ]),
    # Why: runes stack, so tripling the cast budget costs the pack nothing and the food target does not move.
    test('the bigger budget still leaves the same room for food', lambda: expect(food(free_slots=22)).to_be(TRAIL_FOOD_CAP)),
    test('a teleport that burns no runes asks for none', lambda: expect(teleport_rune_target(0)).to_be(0)),
])

# toolAcquire

describe('trail_kit', lambda: [
    test('non-coord scroll still packs the full standard kit', lambda: expect(trail_kit(2853)).to_equal(['Spade', 'Sextant', 'Watch', 'Chart'])),
    test('coordinate scroll packs the same kit', lambda: expect(trail_kit(2801)).to_equal(['Spade', 'Sextant', 'Watch', 'Chart'])),
    test('per-clue row items ride along (2811 falls-ledge rope)', lambda: expect(trail_kit(2811)).to_equal(['Spade', 'Sextant', 'Watch', 'Chart', 'Rope'])),
    test('the spade is fixed: there is only one digging item', lambda: expect(trail_kit(2853)[0]).to_be(SPADE_NAME)),
    test('no scroll (casket-only hold) needs nothing', lambda: expect(trail_kit(None)).to_equal([])),
])

describe('next_coord_tool (item-keyed chain order)', lambda: [
    test('nothing held: sextant first', lambda: expect(next_coord_tool(False, False, False)).to_be('sextant')),
    test('sextant held, no watch: watch', lambda: expect(next_coord_tool(True, False, False)).to_be('watch')),
    test('sextant and watch held, no chart: chart', lambda: expect(next_coord_tool(True, True, False)).to_be('chart')),
    test('all three held: None (done)', lambda: expect(next_coord_tool(True, True, True)).to_be_null()),
    test('strict order: a held watch without a sextant still asks for the sextant first', lambda: expect(next_coord_tool(False, True, False)).to_be('sextant')),
])

describe('tool data sanity', lambda: [
    test('two spade spawns, Ardougne and Falador, far apart', lambda: [
        expect(len(SPADE_SPAWNS)).to_be(2),
        expect(max(abs(SPADE_SPAWNS[0].x - SPADE_SPAWNS[1].x), abs(SPADE_SPAWNS[0].z - SPADE_SPAWNS[1].z))).to_be_greater_than(300),
    ]),
    test('trio and spade names', lambda: [expect(TRIO).to_equal(['Sextant', 'Watch', 'Chart']), expect(SPADE_NAME).to_be('Spade')]),
    test('three NPC stops with distinct anchors and a Treasure-Trails preference', lambda: [
        expect(len(set([f'{s.anchor.x},{s.anchor.z}' for s in [PROFESSOR, MURPHY, KOJO]]))).to_be(3),
        expect(' '.join(PROFESSOR.prefer).lower()).to_contain('treasure'),
    ]),
])

# talk-anchors

TALK_ROWS = [row for row in CLUE_DB.values() if row['type'] == 'talk']

test('CLUE_DB has talk clues (guards against a vacuous pass)', lambda: expect(len(TALK_ROWS)).to_be_greater_than(0))
test('every talk clue in CLUE_DB has a TALK_ANCHORS entry', lambda: expect([row['id'] for row in TALK_ROWS if row['id'] not in TALK_ANCHORS]).to_equal([]))

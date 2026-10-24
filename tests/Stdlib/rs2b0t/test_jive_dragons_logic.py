"""rs2b0t's test/scripts/JiveDragons/logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. rs2b0t's JiveDragons logic is rs2004.hunting's, so these test the framework; the option bags its functions
took are positional here."""

from rs2004.catalogs import Record
from rs2004.hunting import ANTIFIRE_MARGIN_TICKS, ANTIFIRE_TICKS, POTION_PROTECTS, PROTECT_FROM_MELEE, SAFESPOT_BLIND_MS, SHIELD_ABSORBS
from rs2004.hunting import antifire_due, antifire_lapsed, attack_range_for, body_origin, chase_mode, engage_range_for, gap_to, hold_due
from rs2004.hunting import hurt_on_spot, is_clue_obj, keep_doses, key_status, loot_halts, loot_reach, nearest_spot, next_approach_index
from rs2004.hunting import next_safespot, note_sighting, prayer_for, prayer_sip_due, retreat_aim, retreat_due, settled, shield_gate, style_gate
from rs2004.hunting import wants_drop


def at(x, z):
    return Record({'x': x, 'z': z})


def item(id, name):
    return Record({'id': id, 'name': name})


def loot_filter(bank_common=False, solve_clues=False, bury_bones=False):
    return Record({'loot': set(['dragonhide']), 'bank_common': bank_common, 'solve_clues': solve_clues, 'bury_bones': bury_bones,
                   'bone_name': 'Dragon bones'})


def hurt(in_lair=True, on_safespot=False, hp_frac=0.42, retreat_hp=0.5, has_food=True, spots=3):
    return retreat_due(in_lair, on_safespot, hp_frac, retreat_hp, has_food, spots)


SPOTS = [at(2901, 9809), at(2900, 9809), at(2901, 9810)]
ANCHOR = at(2900, 9808)
HERE = at(2857, 9780)

describe('next_safespot', lambda: [
    test('holds the current tile while nothing is wrong', lambda: expect(next_safespot(0, 3, False, 0)).to_be(0)),
    test('a hit on the safespot rotates to the next tile', lambda: expect(next_safespot(0, 3, True, 0)).to_be(1)),
    test('going blind for the full window rotates too', lambda: [
        expect(next_safespot(0, 3, False, SAFESPOT_BLIND_MS)).to_be(1),
        expect(next_safespot(0, 3, False, SAFESPOT_BLIND_MS - 1)).to_be(0),
    ]),
    test('rotation wraps rather than running off the end', lambda: expect(next_safespot(2, 3, True, 0)).to_be(0)),
    test('a single-tile site never rotates', lambda: expect(next_safespot(0, 1, True, 0)).to_be(0)),
])

describe('retreat_due', lambda: [
    test('off the safespot and under the line, the run walks out of the fire', lambda: expect(hurt()).to_be(True)),
    test('the tile the run already stands on is the one it would walk to', lambda: expect(hurt(on_safespot=True)).to_be(False)),
    test('the line is exclusive, so a run sitting on it keeps fighting', lambda: [
        expect(hurt(hp_frac=0.5)).to_be(False),
        expect(hurt(hp_frac=0.49)).to_be(True),
    ]),
    test('a 0 setting turns it off at every hp, and with an empty pack too', lambda: [
        expect(hurt(hp_frac=0.01, retreat_hp=0)).to_be(False),
        expect(hurt(hp_frac=0.01, retreat_hp=0, has_food=False)).to_be(False),
    ]),
    test('an empty pack walks out of the fire at any hp, since nothing heals in the lair', lambda: [
        expect(hurt(has_food=False, hp_frac=0.99)).to_be(True),
        expect(hurt(has_food=False, hp_frac=0.05)).to_be(True),
    ]),
    test('an empty pack on the safespot has arrived, so the bank run gets the loop',
         lambda: expect(hurt(has_food=False, on_safespot=True, hp_frac=0.99)).to_be(False)),
    test('outside the lair, and at a site with no safespots, there is nowhere to run to', lambda: [
        expect(hurt(in_lair=False)).to_be(False),
        expect(hurt(spots=0)).to_be(False),
    ]),
])

describe('hold_due', lambda: [
    test('a stocked run walks back to the fight tile wherever it is standing', lambda: [
        expect(hold_due(True, True)).to_be(True),
        expect(hold_due(False, True)).to_be(True),
    ]),
    test('an empty pack on a safespot stays put, so melee cannot shuttle to its anchor and back', lambda: expect(hold_due(True, False)).to_be(False)),
    test('an empty pack off every safespot still walks, since the retreat is the walk', lambda: expect(hold_due(False, False)).to_be(True)),
])

describe('nearest_spot', lambda: [
    test('the tile the live run died on is six tiles from the spot it picks', lambda: expect(nearest_spot(at(2898, 9803), SPOTS)).to_be(0)),
    test('a tile west of the ladder picks the western spot', lambda: expect(nearest_spot(at(2896, 9809), SPOTS)).to_be(1)),
    test('distance is Chebyshev, so a diagonal counts as one step', lambda: expect(nearest_spot(at(2902, 9811), SPOTS)).to_be(2)),
    test('a tie goes to the earlier spot', lambda: expect(nearest_spot(at(2900, 9810), SPOTS)).to_be(0)),
    test('standing on one picks that one', lambda: expect(nearest_spot(SPOTS[1], SPOTS)).to_be(1)),
])

describe('retreat_aim', lambda: [
    test('a fresh retreat runs at the nearest spot and names the one after it', lambda: expect(retreat_aim(None, ANCHOR, SPOTS)).to_equal((0, 1))),
    test('a retry from the same tile keeps the rotation rather than picking the failed spot again', lambda: [
        expect(nearest_spot(ANCHOR, SPOTS)).to_be(0),
        expect(retreat_aim(1, ANCHOR, SPOTS)).to_equal((1, 2)),
        expect(retreat_aim(2, ANCHOR, SPOTS)).to_equal((2, 0)),
    ]),
    test('spot 0 is a rotation like any other, not an absent one', lambda: expect(retreat_aim(0, at(2896, 9809), SPOTS)).to_equal((0, 1))),
    test('a one-spot site has nowhere to rotate to', lambda: expect(retreat_aim(None, ANCHOR, SPOTS[0:1])).to_equal((0, 0))),
])

describe('shield_gate', lambda: [
    test('melee without the shield is refused, naming where to get one', lambda: expect(shield_gate('melee', False, False)).to_contain('Duke Horacio')),
    test('melee with the shield passes', lambda: expect(shield_gate('melee', False, True)).to_be_null()),
    test('a safespot is fire-proof, so mage and range never need it', lambda: [
        expect(shield_gate('mage', False, False)).to_be_null(),
        expect(shield_gate('range', False, False)).to_be_null(),
    ]),
    test('a site that breathes at range wants the shield whatever the style', lambda: [
        expect(shield_gate('mage', True, False)).to_contain('metal dragons'),
        expect(shield_gate('mage', True, True)).to_be_null(),
        expect(shield_gate('melee', True, False)).to_contain('metal dragons'),
    ]),
])

describe('style_gate', lambda: [
    test('range is refused where the shield is worn, since a bow takes both hands', lambda: [
        expect(style_gate('range', True)).to_contain('both hands'),
        expect(style_gate('range', False)).to_be_null(),
        expect(style_gate('mage', True)).to_be_null(),
        expect(style_gate('melee', True)).to_be_null(),
    ]),
])

describe('antifire', lambda: [
    test('a dose is due on the first pass inside the lair and again as the last one lapses', lambda: [
        expect(antifire_due(True, 100, 0)).to_be(True),
        expect(antifire_due(True, 100, 100 + ANTIFIRE_TICKS)).to_be(False),
        expect(antifire_due(True, 100 + ANTIFIRE_TICKS - ANTIFIRE_MARGIN_TICKS, 100 + ANTIFIRE_TICKS)).to_be(True),
    ]),
    test('never outside the lair', lambda: expect(antifire_due(False, 100, 0)).to_be(False)),
    test('a shield line with no potion line after it means the dose lapsed', lambda: [
        expect(antifire_lapsed(True, False)).to_be(True),
        expect(antifire_lapsed(True, True)).to_be(False),
        expect(antifire_lapsed(False, False)).to_be(False),
    ]),
    # The patterns are lower-case substrings, which game_messages matches case-insensitively.
    test('the lines match what metal_dragon.rs2 prints', lambda: [
        expect('Your shield absorbs most of the dragon fire!'.lower()).to_contain(SHIELD_ABSORBS),
        expect("Your potion protects you from the heat of the dragon's breath!".lower()).to_contain(POTION_PROTECTS),
    ]),
])

describe('next_approach_index', lambda: [
    test('the landing starts at the first stop', lambda: expect(next_approach_index([at(2691, 9564), at(2649, 9562), at(2698, 9500)], at(2713, 9564))).to_be(0)),
    test('a bot already past the stones carries on from the pipe rather than recrossing them',
         lambda: expect(next_approach_index([at(2691, 9564), at(2649, 9562), at(2698, 9500)], at(2697, 9458))).to_be(2)),
])

describe('attack_range_for', lambda: [
    test('melee is adjacency, a bow is 7 and a staff is 10', lambda: [
        expect(attack_range_for('melee')).to_be(1),
        expect(attack_range_for('range')).to_be(7),
        expect(attack_range_for('mage')).to_be(10),
    ]),
])

describe('engage_range_for', lambda: [
    test('a safespot style clicks one tile inside its range, since a body on the edge is one wander step from out of it', lambda: [
        expect(engage_range_for('range')).to_be(6),
        expect(engage_range_for('mage')).to_be(9),
    ]),
    test('melee has no edge to keep off, the leash brings the body to the anchor', lambda: expect(engage_range_for('melee')).to_be(1)),
])

# Why: the engine measures range between the closest tiles of the two footprints, and the client reports a body at
# its centre tile.
describe('gap_to', lambda: [
    test('a size-3 body reported nine tiles off has its near face eight away, past a bow', lambda: [
        expect(gap_to(at(2856, 9786), at(2858, 9777), 3)).to_be(8),
        expect(gap_to(at(2856, 9786), at(2858, 9777), 3)).to_be_greater_than(attack_range_for('range')),
    ]),
    test('a size-4 dragon reads two closer on its north and east faces and three on its south and west', lambda: [
        expect(gap_to(at(2901, 9809), at(2899, 9804), 4)).to_be(4),
        expect(gap_to(at(2895, 9800), at(2899, 9804), 4)).to_be(2),
    ]),
    test('a tile beside or inside the footprint reads as adjacent or zero', lambda: [
        expect(gap_to(at(2900, 9808), at(2899, 9804), 4)).to_be(3),
        expect(gap_to(at(2898, 9806), at(2899, 9804), 4)).to_be(1),
        expect(gap_to(at(2898, 9803), at(2899, 9804), 4)).to_be(0),
    ]),
    test('a size-1 body is plain Chebyshev', lambda: expect(gap_to(at(10, 10), at(13, 8), 1)).to_be(3)),
])

describe('key_status', lambda: [
    test('held beats banked beats a fetch', lambda: [
        expect(key_status(1, 3)).to_be('held'),
        expect(key_status(0, 3)).to_be('bank'),
        expect(key_status(0, 0)).to_be('fetch'),
    ]),
])

describe('wants_drop', lambda: [
    test('a ticked name is taken and an unticked one is left', lambda: [
        expect(wants_drop(item(1753, 'Dragonhide'), loot_filter())).to_be(True),
        expect(wants_drop(item(314, 'Feather'), loot_filter())).to_be(False),
    ]),
    test('unticking the bones box does not stop a burial run collecting them', lambda: [
        expect(wants_drop(item(532, 'Dragon bones'), loot_filter())).to_be(False),
        expect(wants_drop(item(532, 'Dragon bones'), loot_filter(bury_bones=True))).to_be(True),
    ]),
    test('clues are matched by id, since every hard trail displays the same name', lambda: [
        expect(is_clue_obj(2722)).to_be(True),
        expect(is_clue_obj(2714)).to_be(True),
        expect(is_clue_obj(995)).to_be(False),
        expect(wants_drop(item(2722, 'Clue scroll'), loot_filter())).to_be(False),
        expect(wants_drop(item(2722, 'Clue scroll'), loot_filter(solve_clues=True))).to_be(True),
    ]),
    test('the common-loot box takes a gem the loot list never mentions', lambda: [
        expect(wants_drop(item(1623, 'Uncut sapphire'), loot_filter())).to_be(False),
        expect(wants_drop(item(1623, 'Uncut sapphire'), loot_filter(bank_common=True))).to_be(True),
    ]),
    test('an unnamed ground item is never wanted', lambda: expect(wants_drop(item(4, None), loot_filter())).to_be(False)),
])

# Why: the client reports an npc at the tile under the centre of its footprint, and the engine measures sight to the
# south-west corner.
describe('body_origin', lambda: [
    test('a size-3 body starts one tile south-west of the reported tile, a size-4 body two', lambda: [
        expect(body_origin(at(2860, 9782), 3)).to_equal({'x': 2859, 'z': 9781}),
        expect(body_origin(at(2899, 9804), 4)).to_equal({'x': 2897, 'z': 9802}),
    ]),
    test('a size-1 or size-2 body reads from its reported tile or one below it', lambda: [
        expect(body_origin(at(10, 10), 1)).to_equal({'x': 10, 'z': 10}),
        expect(body_origin(at(10, 10), 2)).to_equal({'x': 9, 'z': 9}),
    ]),
])


def holding_tile():
    s = note_sighting(None, HERE, 1000)
    s = note_sighting(s, HERE, 1600)
    first = settled(s, 1600, 1200)
    s = note_sighting(s, HERE, 2200)
    return [expect(first).to_be(False), expect(settled(s, 2200, 1200)).to_be(True)]


def stepping():
    s = note_sighting(None, HERE, 1000)
    s = note_sighting(s, HERE, 2200)
    before = settled(s, 2200, 1200)
    s = note_sighting(s, at(2858, 9780), 2800)
    return [expect(before).to_be(True), expect(settled(s, 2800, 1200)).to_be(False), expect(settled(s, 4000, 1200)).to_be(True)]


# Why: a wandering body steps a tile a tick, and the fourth demon run was walked off the tile by the two clicks it
# sent at bodies still on the move.
describe('sightings', lambda: [
    test('a body just sighted has not settled', lambda: [
        expect(settled(note_sighting(None, HERE, 1000), 1000, 1200)).to_be(False),
        expect(settled(None, 5000, 1200)).to_be(False),
    ]),
    test('a body holding its tile settles once the window has passed', holding_tile),
    test('a step restarts the window', stepping),
])

describe('loot_halts', lambda: [
    test('under the retreat line the burst stops, on it the burst runs', lambda: [
        expect(loot_halts(0.49, 0.3, 0.5)).to_be(True),
        expect(loot_halts(0.5, 0.3, 0.5)).to_be(False),
    ]),
    test('with the retreat off, the panic line is the floor', lambda: [
        expect(loot_halts(0.4, 0.3, 0)).to_be(False),
        expect(loot_halts(0.29, 0.3, 0)).to_be(True),
    ]),
])

describe('hurt_on_spot', lambda: [
    test('hp falling on the tile is a bad tile when nothing hits from range', lambda: expect(hurt_on_spot(False, True, 80, 70)).to_be(True)),
    test('the same drop on a ranged-threat site is expected', lambda: expect(hurt_on_spot(True, True, 80, 70)).to_be(False)),
    test('off the tile, a first reading, or steady hp never counts', lambda: [
        expect(hurt_on_spot(False, False, 80, 70)).to_be(False),
        expect(hurt_on_spot(False, True, -1, 70)).to_be(False),
        expect(hurt_on_spot(False, True, 70, 70)).to_be(False),
    ]),
])

BOOSTS = ['Super attack(3)', 'Super attack(2)']
ANTI = ['Superantipoison(4)', 'Superantipoison(3)']

# Why: the key stop deposits everything off the keep list before the first full bank trip, so a dose left off it is
# banked and the walk in is unprotected, which is what let poison chip the run on the safespot.
describe('keep_doses', lambda: [
    test('keeps the antipoison alongside the boosts on a site that carries one', lambda: expect(keep_doses(BOOSTS, ANTI, True)).to_equal(BOOSTS + ANTI)),
    test('keeps only the boosts where the site carries no antipoison', lambda: expect(keep_doses(BOOSTS, ANTI, False)).to_equal(BOOSTS)),
    test('a run carrying neither keeps nothing extra', lambda: expect(keep_doses([], ANTI, False)).to_equal([])),
])

describe('loot_reach', lambda: [
    test('a fire-at-range site walks fourteen tiles for a drop, a melee-proof pocket ten', lambda: [
        expect(loot_reach(True)).to_be(14),
        expect(loot_reach(False)).to_be(10),
    ]),
])

describe('melee on a fire-at-range site', lambda: [
    test('chases, since the dragons stop at range and never close; every other pairing holds its tile', lambda: [
        expect(chase_mode('melee', True)).to_be(True),
        expect(chase_mode('melee', False)).to_be(False),
        expect(chase_mode('mage', True)).to_be(False),
        expect(chase_mode('range', True)).to_be(False),
    ]),
    test('prays Protect from Melee there and nowhere else', lambda: [
        expect(prayer_for('melee', True)).to_be(PROTECT_FROM_MELEE),
        expect(prayer_for('melee', False)).to_be_null(),
        expect(prayer_for('mage', True)).to_be_null(),
    ]),
    test('sips under the floor or under the fraction of the level, whichever is higher', lambda: [
        expect(prayer_sip_due(8, 43)).to_be(True),
        expect(prayer_sip_due(9, 43)).to_be(False),
        expect(prayer_sip_due(14, 99)).to_be(True),
        expect(prayer_sip_due(15, 99)).to_be(False),
        expect(prayer_sip_due(0, 0)).to_be(False),
    ]),
])

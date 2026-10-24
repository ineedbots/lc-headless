"""rs2b0t's test/scripts/JiveDragons: sites.test.ts and enclave-targets.test.ts (MIT, see thirdparty/rs2b0t), on
spec.py's describe, test and expect. The sites are rs2004.hunting's. sites.test.ts's pack-gated derivations need
rs2b0t's own tools, and its escape-teleport checks are in nav/, beside the walker's data."""

from rs2004.catalogs import Record
from rs2004.hunting import BRIMHAVEN_IRON, BRIMHAVEN_STEEL, DRAGON_SITES, GUTANOTH_BLUE, MAX_STANDS, SITE_OPTIONS, STAND_SITE_KEYS, TAVERLEY_BLUE
from rs2004.hunting import enclave_targets, hunt_names, needs_shield, site_for, stand_for


def t(x, z, level=0):
    return Record({'x': x, 'z': z, 'level': level})


def xz(tiles):
    return [[p.x, p.z] for p in tiles]


def inside(site, cases):
    """cases: (x, z, level, expected) rows."""
    return [expect(site.in_area(t(x, z, level))).to_be(want) for x, z, level, want in cases]


BLUE = DRAGON_SITES.get('taverley-blue')
BLACK = DRAGON_SITES.get('taverley-black')
HEROES = DRAGON_SITES.get('heroes-blue')
ENCLAVE = DRAGON_SITES.get('gutanoth-blue')
IRON = DRAGON_SITES.get('brimhaven-iron')
STEEL = DRAGON_SITES.get('brimhaven-steel')


def every_option_resolves():
    expect(SITE_OPTIONS).to_equal(['taverley-blue', 'taverley-black', 'heroes-blue', 'gutanoth-blue', 'brimhaven-iron', 'brimhaven-steel'])
    for key in SITE_OPTIONS:
        expect(site_for(key).key).to_be(key)


def blue_tiles():
    s = BLUE
    expect(xz(s.safespots)).to_equal([[2901, 9809], [2904, 9808], [2901, 9810]])
    expect([s.melee_anchor.x, s.melee_anchor.z]).to_equal([2900, 9808])
    expect(xz(s.approach)).to_equal([[2911, 9809]])
    expect(s.gate).to_match_object({'loc_id': 2623, 'op': 'Open'})
    expect([s.gate.outside.x, s.gate.outside.z]).to_equal([2924, 9803])
    expect([s.gate.inside.x, s.gate.inside.z]).to_equal([2923, 9803])
    expect(s.key_item).to_equal({'name': 'Dusty key', 'id': 1590})
    expect([s.bank.x, s.bank.z, s.bank.level]).to_equal([2946, 3369, 0])
    expect([s.walk_out.x, s.walk_out.z, s.walk_out.level]).to_equal([2884, 3398, 0])
    expect(s.escape_teleport_id).to_be('falador')
    expect(s.target).to_be('Blue dragon')
    expect(s.bones).to_be('Dragon bones')
    expect(all([p.level == 0 for p in s.safespots])).to_be(True)


def anchor_off_spawns(site, spawns, west, east):
    a = site.melee_anchor
    for x, z in spawns:
        expect(a.x >= x - west and a.x <= x + east and a.z >= z - west and a.z <= z + east).to_be(False)


describe('DRAGON_SITES', lambda: [
    test("the two Taverley sites, the Heroes' Guild pen, the Enclave and the two Brimhaven rooms are the entries, and every option resolves",
         every_option_resolves),
    test('an unknown key falls back to Taverley rather than throwing', lambda: expect(site_for('nope').key).to_be('taverley-blue')),
    test('the blue site preserves its tiles except for the requested second safespot', blue_tiles),
    test('the melee anchor stands outside every adult spawn footprint', lambda: anchor_off_spawns(BLUE, [[2897, 9797], [2899, 9802], [2904, 9802]], 0, 3)),
    test('in_area holds inside the lair and rejects the entrance corridor', lambda: [
        inside(BLUE, [(2901, 9809, 0, True), (2923, 9803, 0, True), (2884, 9798, 0, False), (2924, 9803, 0, False), (2901, 3809, 0, False)]),
        expect(BLUE.in_area(None)).to_be(False),
    ]),
    test('every edge of the lair box is pinned from both sides', lambda: inside(BLUE, [
        (2888, 9800, 0, True), (2887, 9800, 0, False), (2923, 9800, 0, True), (2924, 9800, 0, False),
        (2900, 9769, 0, True), (2900, 9768, 0, False), (2900, 9816, 0, True), (2900, 9817, 0, False),
    ])),
    test('a tile on another plane is outside the lair', lambda: expect(BLUE.in_area(t(2901, 9809, 1))).to_be(False)),
])

describe('the Taverley black dragons', lambda: [
    # Why: derived by tools/nav/jive-safespots.ts --target black, the same probe the blue tiles came from.
    test('stand in the corridor south of the room, off every tile a dragon reaches', lambda: [
        expect(xz(BLACK.safespots)).to_equal([[2836, 9817], [2835, 9817], [2834, 9817]]),
        expect([BLACK.melee_anchor.x, BLACK.melee_anchor.z]).to_equal([2835, 9818]),
        expect(all([p.level == 0 for p in BLACK.safespots])).to_be(True),
    ]),
    test('take the gate, the key, the bank and the way out from the blue site, since they share a dungeon', lambda: [
        expect(BLACK.gate).to_equal(TAVERLEY_BLUE.gate),
        expect(BLACK.key_item).to_equal(TAVERLEY_BLUE.key_item),
        expect(BLACK.bank).to_equal(TAVERLEY_BLUE.bank),
        expect(BLACK.escape_teleport_id).to_be(TAVERLEY_BLUE.escape_teleport_id),
        expect(BLACK.walk_out).to_equal(TAVERLEY_BLUE.walk_out),
    ]),
    test('carry their own target, loot list, food and poison kit', lambda: [
        expect(BLACK.target).to_be('Black dragon'),
        expect(BLACK.bones).to_be('Dragon bones'),
        expect(BLACK.loot_setting).to_be('loot_black'),
        expect(BLACK.food).to_be('Shark'),
        expect(BLACK.antipoison).to_be(True),
        expect(TAVERLEY_BLUE.loot_setting).to_be_undefined(),
        expect(TAVERLEY_BLUE.antipoison).to_be_undefined(),
    ]),
    # Why: the dragons only breathe from melee reach on this content, so a melee-proof tile is breath-proof and the
    # site needs no ranged-threat flag.
    test('are not a ranged threat, the same as the blues', lambda: expect(BLACK.ranged_threat).to_be_undefined()),
    test('cover both spawns, the walk in and the blue lair, but never the surface', lambda: [
        inside(BLACK, [(2829, 9826, 0, True), (2835, 9824, 0, True), (2836, 9817, 0, True), (2911, 9809, 0, True), (2946, 3369, 0, False)]),
        expect(BLACK.in_area(None)).to_be(False),
    ]),
    test('the blue area stays its own, so the two sites do not swap lairs', lambda: expect(TAVERLEY_BLUE.in_area(t(2829, 9826))).to_be(False)),
])


def heroes_area():
    s = HEROES
    inside(s, [(2908, 9905, 0, True), (2892, 9908, 0, True), (2892, 3508, 0, False), (2908, 9905, 1, False)])
    for p in s.safespots:
        expect(s.in_area(p)).to_be(True)
    expect(s.in_area(None)).to_be(False)


describe("the Heroes' Guild blue dragon", lambda: [
    test('takes no key and no gate, since the cellar ladder is the whole way in', lambda: [
        expect(HEROES.key_item).to_be_null(),
        expect(HEROES.gate).to_be_null(),
        expect([[p.x, p.z, p.level] for p in HEROES.approach]).to_equal([[2892, 9908, 0]]),
    ]),
    # Why: derived by tools/nav/jive-safespots.ts --target heroes, which rebuilds collision off the engine loc configs
    # so the `blockrange=no` railing stops reading as opaque.
    test('stands off the pen, on tiles that keep the whole wander area in sight', lambda: [
        expect(xz(HEROES.safespots)).to_equal([[2905, 9909], [2906, 9911], [2907, 9911]]),
        expect([HEROES.melee_anchor.x, HEROES.melee_anchor.z]).to_equal([2909, 9910]),
        expect(all([p.level == 0 for p in HEROES.safespots])).to_be(True),
    ]),
    test('shares the blue drop table and the Falador bank and escape', lambda: [
        expect(HEROES.target).to_be(TAVERLEY_BLUE.target),
        expect(HEROES.bones).to_be('Dragon bones'),
        expect(HEROES.loot_setting).to_be_undefined(),
        expect(HEROES.bank).to_equal(TAVERLEY_BLUE.bank),
        expect(HEROES.escape_teleport_id).to_be('falador'),
    ]),
    test('walks out past the guild doors, not to a tile still inside them', lambda: [
        expect([HEROES.walk_out.x, HEROES.walk_out.z, HEROES.walk_out.level]).to_equal([2904, 3510, 0]),
        expect(HEROES.in_area(HEROES.walk_out)).to_be(False),
    ]),
    # Why: the dragon only breathes out of ai_opplayer2, which needs melee reach, so a fenced-off stand is
    # breath-proof and the site needs no ranged-threat flag.
    test('is not a ranged threat, and carries no poison kit', lambda: [
        expect(HEROES.ranged_threat).to_be_undefined(),
        expect(HEROES.antipoison).to_be_undefined(),
    ]),
    test('covers the spawn, the pen and the ladder landing, and never the guild above it', heroes_area),
    test('every edge of the cellar box is pinned from both sides', lambda: inside(HEROES, [
        (2886, 9900, 0, True), (2885, 9900, 0, False), (2942, 9900, 0, True), (2943, 9900, 0, False),
        (2900, 9883, 0, True), (2900, 9882, 0, False), (2900, 9917, 0, True), (2900, 9918, 0, False),
    ])),
    test('the Taverley lair stays its own, so the two blue sites do not swap rooms', lambda: [
        expect(TAVERLEY_BLUE.in_area(t(2908, 9905))).to_be(False),
        expect(HEROES.in_area(t(2901, 9809))).to_be(False),
    ]),
])


def enclave_stands_labelled():
    s = ENCLAVE
    expect(s.stands).to_have_length(6)
    for st in s.stands:
        expect(st.tiles).to_have_length(3)
        # rs2b0t matches /dragon at \d{4},\d{4}/; pocketpy has no re, so the label's tail is read as the two numbers.
        tail = st.label.split('dragon at ')[-1].split(',')
        digits = len([c for c in ''.join(tail) if c in '0123456789'])
        expect(len(tail) == 2 and len(tail[0]) == 4 and len(tail[1]) == 4 and digits == 8).to_be(True)
        for p in st.tiles:
            expect(s.in_area(p)).to_be(True)
        expect(s.in_area(st.anchor)).to_be(True)


# Why: a stand that sees a sliver of its dragon's wander takes no kills, which is what the first pass at the south
# stand did on a live run.
def enclave_stands_aim():
    spawns = [[2590, 9461], [2568, 9437], [2579, 9445], [2592, 9431], [2604, 9443], [2609, 9459]]
    for i, st in enumerate(ENCLAVE.stands):
        x, z = spawns[i]
        expect(st.label).to_contain(f'{x},{z}')
        # The body is 4 wide, so a tile within 14 of the spawn corner is inside a 10 cast of some of it.
        expect(min([max(abs(p.x - x), abs(p.z - z)) for p in st.tiles])).to_be_less_than_or_equal(14)


def enclave_stands_distinct():
    seen = set()
    for st in ENCLAVE.stands:
        for p in st.tiles:
            key = f'{p.x},{p.z}'
            expect(key in seen).to_be(False)
            seen.add(key)


def enclave_areas():
    s = ENCLAVE
    for p in s.safespots:
        expect(s.in_area(p)).to_be(True)
    expect(s.in_area(s.melee_anchor)).to_be(True)
    expect(s.in_area(s.exit.stand)).to_be(True)
    expect(s.in_area(s.talk_gate.stand)).to_be(False)
    expect(s.in_area(s.walk_out)).to_be(False)
    expect(s.in_area(None)).to_be(False)


# Why: the guard is an npc with a two-option chat rather than a door, and nothing walks out of the cave, so this site
# is the one that exercises talk_gate and exit.
describe("the Gu'Tanoth Enclave blue dragons", lambda: [
    test('the way in is the guard conversation, not a gate or a key', lambda: [
        expect(ENCLAVE.gate).to_be_null(),
        expect(ENCLAVE.key_item).to_be_null(),
        expect(ENCLAVE.talk_gate).to_match_object({'npc': 'Enclave guard', 'op': 'Talk-to', 'choose': 'I want to go in there'}),
        expect([ENCLAVE.talk_gate.stand.x, ENCLAVE.talk_gate.stand.z]).to_equal([2508, 3038]),
    ]),
    test('the way out is the cave loc, since no route leaves the Enclave on foot', lambda: [
        expect(ENCLAVE.exit).to_match_object({'loc_id': 2813, 'op': 'Enter'}),
        expect([ENCLAVE.exit.stand.x, ENCLAVE.exit.stand.z]).to_equal([2597, 9468]),
        expect([ENCLAVE.walk_out.x, ENCLAVE.walk_out.z]).to_equal([2540, 3054]),
    ]),
    test('it banks at Yanille and escapes on the Watchtower spell the quest already covers', lambda: [
        expect([ENCLAVE.bank.x, ENCLAVE.bank.z, ENCLAVE.bank.level]).to_equal([2612, 3092, 0]),
        expect(ENCLAVE.escape_teleport_id).to_be('watchtower'),
    ]),
    # Why: the stand is melee-proof but the cave is not range-proof, and a soak took 8 and 13 off it with one adult
    # up, so a hit there must not read as a bad tile.
    test('a hit on the stand is the room, not the tile', lambda: expect(ENCLAVE.ranged_threat).to_be(True)),
    test('it hunts blue dragons for dragon bones, off its own merged chip list', lambda: [
        expect(ENCLAVE.target).to_be('Blue dragon'),
        expect(ENCLAVE.bones).to_be('Dragon bones'),
        expect(ENCLAVE.loot_setting).to_be('loot_enclave'),
    ]),
    # Why: a stand is idle while its dragon respawns, and the cave puts a greater demon inside a cast of stand 1, so
    # the idle time goes on that.
    test('and fills the respawn downtime with the cave greater demons', lambda: [
        expect(ENCLAVE.also_hunt).to_equal(['Greater demon']),
        expect(hunt_names(ENCLAVE)).to_equal(['Blue dragon', 'Greater demon']),
    ]),
    # Why: the cave holds six dragons and which one is worth camping depends on what else is in the room, so the
    # stands are numbered and the operator picks one.
    test('it carries six numbered stands, one per dragon in the cave', enclave_stands_labelled),
    test('every stand looks at its own dragon and sits clear of the rest of the cave', enclave_stands_aim),
    test('no two stands share a tile, so a number picks a place rather than a shade of one', enclave_stands_distinct),
    test('stand 1 is what the site fights from by default, since it is the one with a live proof', lambda: [
        expect(ENCLAVE.safespots).to_equal(ENCLAVE.stands[0].tiles),
        expect(ENCLAVE.melee_anchor).to_equal(ENCLAVE.stands[0].anchor),
    ]),
    test('the stand and the anchor sit in the cave, and the guard does not', enclave_areas),
    test('every edge of the cave box is pinned from both sides', lambda: inside(ENCLAVE, [
        (2560, 9440, 0, True), (2559, 9440, 0, False), (2623, 9440, 0, True), (2624, 9440, 0, False),
        (2590, 9408, 0, True), (2590, 9407, 0, False), (2590, 9471, 0, True), (2590, 9472, 0, False), (2585, 9468, 1, False),
    ])),
    test('the melee anchor stands outside every adult spawn footprint',
         lambda: anchor_off_spawns(ENCLAVE, [[2568, 9437], [2579, 9445], [2590, 9461], [2592, 9431], [2604, 9443], [2609, 9459]], 3, 3)),
])


def clamps():
    s = ENCLAVE.stands
    expect(stand_for(ENCLAVE, 0)).to_be(s[0])
    expect(stand_for(ENCLAVE, -4)).to_be(s[0])
    expect(stand_for(ENCLAVE, 99)).to_be(s[5])
    expect(stand_for(ENCLAVE, 2.7)).to_be(s[1])


def no_stands():
    expect(TAVERLEY_BLUE.stands).to_be_undefined()
    for n in [1, 4, 99]:
        stand = stand_for(TAVERLEY_BLUE, n)
        expect(stand.tiles).to_equal(TAVERLEY_BLUE.safespots)
        expect(stand.anchor).to_equal(TAVERLEY_BLUE.melee_anchor)


# Why: the number comes off a settings box, so a typo or an old profile must land on a stand rather than throw.
describe('stand_for', lambda: [
    test('picks the numbered stand, 1-based', lambda: [
        expect(stand_for(ENCLAVE, 1)).to_be(ENCLAVE.stands[0]),
        expect(stand_for(ENCLAVE, 3)).to_be(ENCLAVE.stands[2]),
        expect(stand_for(ENCLAVE, 6)).to_be(ENCLAVE.stands[5]),
    ]),
    test('clamps a number past either end rather than throwing', clamps),
    test('a site that names no stands answers with its own tiles, whatever the number', no_stands),
])


def no_filler():
    for key in ['taverley-blue', 'taverley-black', 'heroes-blue']:
        site = DRAGON_SITES.get(key)
        expect(site.also_hunt).to_be_undefined()
        expect(hunt_names(site)).to_equal([site.target])


# Why: the target has to come first, or a site that fills downtime would take the filler while its own target is up.
describe('hunt_names', lambda: [
    test('puts the site target first and the filler after it', lambda: expect(hunt_names(ENCLAVE)[0]).to_be('Blue dragon')),
    test('a site that fills no downtime hunts its target and nothing else', no_filler),
])


def breathes_at_range():
    for s in [IRON, STEEL]:
        expect(s.fire_at_range).to_be(True)
        expect(s.ranged_threat).to_be(True)
        expect(s.antifire).to_be(True)
        expect(s.axe).to_be(True)
        expect(needs_shield(s, 'mage')).to_be(True)
        expect(needs_shield(s, 'melee')).to_be(True)
    expect(needs_shield(TAVERLEY_BLUE, 'mage')).to_be(False)
    expect(needs_shield(TAVERLEY_BLUE, 'melee')).to_be(True)


def whole_dungeon():
    for s in [IRON, STEEL]:
        inside(s, [(2713, 9564, 0, True), (2697, 9458, 0, True), (2745, 3152, 0, False), (2697, 9458, 2, False)])


describe('the Brimhaven Dungeon metal dragons', lambda: [
    # The fee lines are lower-case substrings, which game_messages matches case-insensitively.
    test('pay Saniboch and take the entrance tree, with no key and no door', lambda: [
        expect(IRON.key_item).to_be_null(),
        expect(IRON.gate).to_be_null(),
        expect(IRON.fee_gate).to_match_object({'npc': 'Saniboch', 'op': 'Pay', 'coins': 875, 'entrance': {'loc_id': 5083, 'op': 'Enter'}}),
        expect('You pay Saniboch 875 coins.'.lower()).to_contain(IRON.fee_gate.paid_line),
        expect('You have already given me lots of nice coins, you may go in.'.lower()).to_contain(IRON.fee_gate.prepaid_line),
        expect(IRON.coins).to_be_greater_than_or_equal(875 + 60),
        expect(STEEL.fee_gate).to_be(IRON.fee_gate),
    ]),
    test('breathe at range, so every style wears the shield and the trip carries antifire and an axe', breathes_at_range),
    test('leave by the exit loc, teleport to Ardougne and bank at the east booth', lambda: [
        expect(IRON.exit).to_match_object({'loc_id': 5084, 'op': 'leave'}),
        expect([IRON.exit.stand.x, IRON.exit.stand.z]).to_equal([2713, 9564]),
        expect(IRON.escape_teleport_id).to_be('ardougne'),
        expect([IRON.bank.x, IRON.bank.z]).to_equal([2655, 3283]),
    ]),
    test("iron and steel finish whichever of the two bites, so each is the other's filler", lambda: [
        expect(hunt_names(IRON)).to_equal(['Iron dragon', 'Steel dragon']),
        expect(IRON.food_per_trip).to_be(8),
    ]),
    test('the approach runs one stop per obstacle from the landing to the pipe',
         lambda: expect(xz(IRON.approach)).to_equal([[2691, 9564], [2649, 9562], [2672, 9499], [2682, 9506], [2698, 9500], [2698, 9492]])),
    test('the whole dungeon is the area, so the landing never reads as outside and the surface always does', whole_dungeon),
    test('iron carries two open camps and steel one, and the picker knows which sites have several', lambda: [
        expect(len(IRON.stands)).to_be(2),
        expect(len(STEEL.stands)).to_be(1),
        expect(IRON.safespots).to_be(IRON.stands[0].tiles),
        expect(stand_for(IRON, 9).label).to_be(IRON.stands[1].label),
        expect(stand_for(STEEL, 3).tiles).to_be(STEEL.stands[0].tiles),
        expect(STAND_SITE_KEYS).to_equal(['gutanoth-blue', 'brimhaven-iron']),
        expect(MAX_STANDS).to_be(6),
    ]),
    test('steel is the iron site with its own target, stands and loot chips', lambda: [
        expect(STEEL.target).to_be('Steel dragon'),
        expect(STEEL.loot_setting).to_be('loot_steel'),
        expect(IRON.loot_setting).to_be('loot_iron'),
        expect(STEEL.bank).to_be(IRON.bank),
        expect(hunt_names(STEEL)).to_equal(['Steel dragon', 'Iron dragon']),
    ]),
])


def modes_round_trip():
    demons = enclave_targets(GUTANOTH_BLUE, 'demons')
    site = enclave_targets(demons, 'both')
    expect(hunt_names(site)).to_equal(['Blue dragon', 'Greater demon'])
    expect(site.bones).to_be('Dragon bones')


def unknown_modes():
    for mode in [None, '', 'unknown']:
        expect(hunt_names(enclave_targets(GUTANOTH_BLUE, mode))).to_equal(['Blue dragon', 'Greater demon'])


def shared_site_untouched():
    demons = enclave_targets(GUTANOTH_BLUE, 'demons')
    dragons = enclave_targets(demons, 'dragons')
    expect(hunt_names(GUTANOTH_BLUE)).to_equal(['Blue dragon', 'Greater demon'])
    expect(hunt_names(demons)).to_equal(['Greater demon'])
    expect(hunt_names(dragons)).to_equal(['Blue dragon'])


def keeps_the_rest():
    stand = stand_for(GUTANOTH_BLUE, 3)
    source = GUTANOTH_BLUE.with_changes(safespots=stand.tiles, melee_anchor=stand.anchor)
    for mode in ['dragons', 'demons', 'both']:
        site = enclave_targets(source, mode)
        for field in ['key', 'label', 'safespots', 'melee_anchor', 'talk_gate', 'exit', 'bank', 'escape_teleport_id', 'loot_setting', 'stands', 'ranged_threat']:
            expect(getattr(site, field)).to_equal(getattr(source, field))
        expect(site.in_area(stand.tiles[0])).to_be(True)
        expect(needs_shield(site, 'melee')).to_be(True)
        expect(needs_shield(site, 'mage')).to_be(False)
        expect(needs_shield(site, 'range')).to_be(False)


def other_sites_untouched():
    for site in [s for s in DRAGON_SITES.values() if s.key != 'gutanoth-blue']:
        for mode in ['dragons', 'demons', 'both']:
            expect(enclave_targets(site, mode)).to_be(site)


describe('enclave_targets', lambda: [
    test('dragon-only mode excludes greater demons', lambda: [
        expect(hunt_names(enclave_targets(GUTANOTH_BLUE, 'dragons'))).to_equal(['Blue dragon']),
        expect(enclave_targets(GUTANOTH_BLUE, 'dragons').bones).to_be('Dragon bones'),
        expect(enclave_targets(GUTANOTH_BLUE, 'dragons').also_hunt).to_be_undefined(),
    ]),
    test('demon-only mode excludes blue dragons and uses ashes', lambda: [
        expect(hunt_names(enclave_targets(GUTANOTH_BLUE, 'demons'))).to_equal(['Greater demon']),
        expect(enclave_targets(GUTANOTH_BLUE, 'demons').bones).to_be('Ashes'),
        expect(enclave_targets(GUTANOTH_BLUE, 'demons').also_hunt).to_be_undefined(),
    ]),
    test('both mode restores dragons first and greater demons as filler', modes_round_trip),
    test('missing and unknown saved modes preserve both targets', unknown_modes),
    test('changing mode does not change another run or the shared site', shared_site_untouched),
    test('preserves the selected stand, transport, loot setting and shield behavior', keeps_the_rest),
    test('does not apply Enclave targets to another site', other_sites_untouched),
])

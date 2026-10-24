"""rs2b0t's test/scripts/JiveDragons/settings.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect."""

from rs2004.catalogs import drop_db
from rs2004.hunting import TAVERLEY_BLUE
from bots.jive_dragons import SETTINGS, site_tile

ELSEWHERE = Tile(3200, 3200, 0)
BRIMHAVEN = {'key': 'site', 'any_of': ['brimhaven-iron', 'brimhaven-steel']}


def untouched_default():
    expect(SETTINGS['safespot1'].default.equals(TAVERLEY_BLUE.safespots[0])).to_be(True)
    bag = SettingsBag({'safespot1': SETTINGS['safespot1'].default})
    expect(site_tile(bag, 'safespot1', ELSEWHERE)).to_be(ELSEWHERE)


def anchor_and_bank():
    bag = SettingsBag({'melee_tile': SETTINGS['melee_tile'].default, 'bank_tile': Tile(3013, 3355, 0)})
    expect(site_tile(bag, 'melee_tile', ELSEWHERE)).to_be(ELSEWHERE)
    expect(site_tile(bag, 'bank_tile', ELSEWHERE).equals(Tile(3013, 3355, 0))).to_be(True)


def metal_chips():
    for key, bar in [('loot_iron', 'Iron bar'), ('loot_steel', 'Steel bar')]:
        chosen = SETTINGS[key].default
        expect(chosen).to_contain(bar)
        expect(chosen).to_contain('Dragon bones')
        expect(chosen).to_contain('Coins')
        expect(chosen).not_.to_contain('Bolts')
        expect(chosen).not_.to_contain('Curry')


describe('JiveDragons loot defaults', lambda: [
    test('Coins and Bass are offered but start unticked', lambda: [
        expect(SETTINGS['loot'].options).to_contain('Coins'),
        expect(SETTINGS['loot'].options).to_contain('Bass'),
        expect(SETTINGS['loot'].default).not_.to_contain('Coins'),
        expect(SETTINGS['loot'].default).not_.to_contain('Bass'),
    ]),
    test('the drops worth the walk are still on by default', lambda: [
        expect(SETTINGS['loot'].default).to_contain('Dragon bones'),
        expect(SETTINGS['loot'].default).to_contain('Dragonhide'),
    ]),
    test('no arrow is on the blue dragon table, so a range run only gets its own back by name',
         lambda: expect(any(['arrow' in n.lower() for n in drop_db().get('Blue dragon')])).to_be(False)),
])

describe('JiveDragons leave_via', lambda: [
    test('the teleport and the gate walk are the only ways out, the teleport by default', lambda: [
        expect(SETTINGS['leave_via'].options).to_equal(['teleport', 'walk']),
        expect(SETTINGS['leave_via'].default).to_be('teleport'),
    ]),
])

describe('JiveDragons site tiles', lambda: [
    test('the schema default is Taverley, so an untouched setting hands the tile back to the site', untouched_default),
    test('a tile moved off the default is the one that applies',
         lambda: expect(site_tile(SettingsBag({'safespot1': Tile(2905, 9812, 0)}), 'safespot1', ELSEWHERE).equals(Tile(2905, 9812, 0))).to_be(True)),
    test('a site carrying more safespots than the panel has keys for keeps its own', lambda: expect(site_tile(SettingsBag({}), None, ELSEWHERE)).to_be(ELSEWHERE)),
    test('the melee anchor and the bank stand read the same way', anchor_and_bank),
])

# Why: a SettingDef's options are a fixed list with no hook onto another key's value, so each table is its own
# setting and the site chooses which one is shown.
describe('the black dragon chips', lambda: [
    test('are their own setting, shown for the black site and hidden for either blue one', lambda: [
        expect(SETTINGS['loot'].show_if).to_equal({'key': 'site', 'any_of': ['taverley-blue', 'heroes-blue']}),
        expect(SETTINGS['loot_black'].show_if).to_equal({'key': 'site', 'any_of': ['taverley-black']}),
    ]),
    test('offer the black dragon table, not the blue one', lambda: [
        expect(SETTINGS['loot_black'].options).to_equal(drop_db().get('Black dragon')),
        expect(SETTINGS['loot_black'].options).to_contain('Dragon med helm'),
        expect(SETTINGS['loot_black'].options).not_.to_contain('Bass'),
        expect(SETTINGS['loot'].options).not_.to_contain('Dragon med helm'),
    ]),
    test('start with the hides and the bones ticked and the junk clear', lambda: [
        expect(SETTINGS['loot_black'].default).to_contain('Dragonhide'),
        expect(SETTINGS['loot_black'].default).to_contain('Dragon bones'),
        expect(SETTINGS['loot_black'].default).not_.to_contain('Coins'),
        expect(SETTINGS['loot_black'].default).not_.to_contain('Chocolate cake'),
    ]),
    test('rune arrows are on the black table, so a range run gets its own ammo back by name', lambda: expect(drop_db().get('Black dragon')).to_contain('Rune arrow')),
])

describe('the ranged supplies', lambda: [
    test('the ranging potion is a ranged option, off by default since it is an extra cost', lambda: [
        expect(SETTINGS['ranging_potion'].default).to_be(False),
        expect(SETTINGS['ranging_potion'].show_if).to_equal({'key': 'combat_style', 'any_of': ['range']}),
    ]),
    test('the antipoison is offered on the black site only, one flask by default', lambda: [
        expect(SETTINGS['antipoison_doses'].default).to_be(1),
        expect(SETTINGS['antipoison_doses'].min).to_be(0),
        expect(SETTINGS['antipoison_doses'].show_if).to_equal({'key': 'site', 'any_of': ['taverley-black']}),
    ]),
    test('rune arrows are among the ammo the panel offers', lambda: expect(SETTINGS['ammo'].options).to_contain('Rune arrow')),
])

describe('JiveDragons Brimhaven settings', lambda: [
    test('the iron and steel chips carry the bars, the bones and the coins ticked, and the bolts and curry not', metal_chips),
    test('the antifire flask count and the axe show for the Brimhaven sites only', lambda: [
        expect(SETTINGS['antifire_doses'].show_if).to_equal(BRIMHAVEN),
        expect(SETTINGS['axe'].show_if).to_equal(BRIMHAVEN),
        expect(SETTINGS['axe'].options).to_contain('Rune axe'),
        expect(SETTINGS['axe'].default).to_be('Rune axe'),
    ]),
    test('the stand picker shows for every site with several stands and reaches the biggest', lambda: [
        expect(SETTINGS['stand'].show_if).to_equal({'key': 'site', 'any_of': ['gutanoth-blue', 'brimhaven-iron']}),
        expect(SETTINGS['stand'].max).to_be(6),
    ]),
])

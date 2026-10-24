"""rs2b0t's test/api/bank/bankSortRank.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record


from rs2004.banksort import UNRANKED, rank_within


def item(name, id=1):
    return Record({'slot': 0, 'id': id, 'name': name, 'cost': 1})


def ascending(category, names):
    """Asserts the names rank strictly ascending in the order given, and that none of them fell through."""
    ranks = [rank_within(category, item(name)) for name in names]
    _flat1 = []
    for i, name in enumerate(names):
        _flat1.extend(([f'{names[i - 1]} ({ranks[i - 1]}) >= {name} ({ranks[i]})'] if i > 0 and ranks[i - 1] >= ranks[i] else []))
    gaps = _flat1
    expect(Record({
        'category': category,
        'gaps': gaps,
        'fell_through': [_ for i, _ in enumerate(names) if ranks[i] == UNRANKED],
    })).to_equal(Record({'category': category, 'gaps': [], 'fell_through': []}))


def _fn2():
    def _fn3():
        ascending('oresBarsGems', [
        'Copper ore',
        'Tin ore',
        'Iron ore',
        'Silver ore',
        'Coal',
        'Gold ore',
        'Mithril ore',
        'Adamantite ore',
        'Runite ore',
    ])
    test('ores run copper to rune, with coal at its mining level', _fn3)

    def _fn4():
        ascending('oresBarsGems', [
        'Bronze bar',
        'Iron bar',
        'Silver bar',
        'Steel bar',
        'Gold bar',
        'Mithril bar',
        'Adamantite bar',
        'Runite bar',
    ])
    test('bars run bronze to rune, with silver at its smithing level', _fn4)

    def _fn5():
        expect(rank_within('oresBarsGems', item('Runite ore'))).to_be_less_than(rank_within('oresBarsGems', item('Bronze bar')))
    test('every ore outranks every bar', _fn5)

    def _fn6():
        ascending('oresBarsGems', [
        'Half of a key',
        'Crystal key',
        'Dragonstone',
        'Diamond',
        'Ruby',
        'Emerald',
        'Sapphire',
        'Uncut dragonstone',
        'Uncut diamond',
        'Uncut ruby',
        'Uncut emerald',
        'Uncut sapphire',
    ])
    test('keys head the gem block, cut gems follow, uncut gems last', _fn6)

    def _fn7():
        expect(rank_within('oresBarsGems', item('Runite bar'))).to_be_less_than(rank_within('oresBarsGems', item('Half of a key')))
    test('bars come before the keys and gems', _fn7)

    def _fn8():
        expect(rank_within('oresBarsGems', item('Uncut opal'))).to_be(UNRANKED)
        expect(rank_within('oresBarsGems', item('Jade'))).to_be(UNRANKED)
    test('a gem the table does not name is unranked', _fn8)

    def _fn9():
        ascending('weapons', [
        'Dragon dagger',
        'Rune scimitar',
        'Adamant scimitar',
        'Mithril scimitar',
        'Black scimitar',
        'Steel scimitar',
        'Iron scimitar',
        'Bronze scimitar',
    ])
    test('weapons run dragon down to bronze', _fn9)

    def _fn10():
        ascending('weapons', [
        'Magic longbow',
        'Magic shortbow',
        'Yew longbow',
        'Yew shortbow',
        'Maple longbow',
        'Maple shortbow',
        'Willow longbow',
        'Willow shortbow',
        'Oak longbow',
        'Oak shortbow',
        'Longbow',
        'Shortbow',
    ])
    test('bows run magic down to plain, longbow before shortbow', _fn10)

    def _fn11():
        expect(rank_within('weapons', item('Bronze scimitar'))).to_be_less_than(rank_within('weapons', item('Magic longbow')))
    test('every metal weapon outranks every bow', _fn11)

    def _fn12():
        expect(rank_within('weapons', item('Abyssal whip'))).to_be(UNRANKED)
        expect(rank_within('weapons', item('Staff of air'))).to_be(UNRANKED)
    test('a weapon with no tier in its name is unranked', _fn12)

    def _fn13():
        ascending('ammunition', ['Rune arrow', 'Adamant arrow', 'Mithril arrow', 'Steel arrow', 'Iron arrow', 'Bronze arrow'])
    test('arrows run rune down to bronze', _fn13)

    def _fn14():
        expect(rank_within('ammunition', item('Ice arrow'))).to_be(UNRANKED)
        expect(rank_within('ammunition', item('Ogre arrow'))).to_be(UNRANKED)
    test('ammunition the table does not name is unranked', _fn14)

    def _fn15():
        ascending('runes', [
        'Blood rune',
        'Death rune',
        'Soul rune',
        'Chaos rune',
        'Mind rune',
        'Body rune',
        'Nature rune',
        'Cosmic rune',
        'Law rune',
        'Air rune',
        'Earth rune',
        'Water rune',
        'Fire rune',
        'Rune essence',
    ])
    test('runes run combat, then utility, then elemental', _fn15)

    def _fn16():
        ascending('logs', ['Logs', 'Achey tree logs', 'Oak logs', 'Willow logs', 'Maple logs', 'Yew logs', 'Magic logs'])
    test('logs run in woodcutting order', _fn16)

    def _fn17():
        expect(rank_within('logs', item('Plank'))).to_be(UNRANKED)
    test('a plank is not a log the table names', _fn17)

    def _fn18():
        ascending('herbs', [
        'Guam leaf',
        'Snake weed',
        'Ardrigal',
        'Sito foil',
        'Volencia moss',
        'Rogues purse',
        'Marrentill',
        'Tarromin',
        'Harralander',
        'Ranarr weed',
        'Toadflax',
        'Irit leaf',
        'Avantoe',
        'Kwuarm',
        'Snapdragon',
        'Cadantine',
        'Lantadyme',
        'Dwarf weed',
        'Torstol',
    ])
    test('clean herbs run in identify order', _fn18)

    def _fn19():
        unids = [
        ['guam', 199],
        ['snake weed', 1525],
        ['marrentill', 201],
        ['ranarr', 207],
        ['toadflax', 3049],
        ['irit', 209],
        ['snapdragon', 3051],
        ['cadantine', 215],
        ['lantadyme', 2485],
        ['torstol', 219],
    ]
        ranks = [rank_within('herbs', item('Herb', id)) for _, id in unids]
        for i in range(1, len(ranks)):
            if ranks[i - 1] >= ranks[i]:
                raise RuntimeError(f'unid {unids[i - 1][0]} ({ranks[i - 1]}) should rank before {unids[i][0]} ({ranks[i]})')
    test('unidentified herbs are ranked by id, because every one of them is named Herb', _fn19)

    def _fn21():
        expect(rank_within('herbs', item('Herb', 200))).to_be(rank_within('herbs', item('Herb', 199)))
        expect(rank_within('herbs', item('Herb', 2486))).to_be(rank_within('herbs', item('Herb', 2485)))
    test('a noted unidentified herb ranks with its unnoted twin', _fn21)

    def _fn22():
        expect(rank_within('herbs', item('Torstol'))).to_be_less_than(rank_within('herbs', item('Herb', 199)))
    test('every clean herb outranks every unidentified one', _fn22)

    def _fn23():
        expect(rank_within('supplies', item('Feather'))).to_be(UNRANKED)
        expect(rank_within('tools', item('Rune pickaxe'))).to_be(UNRANKED)
        expect(rank_within('junk', item('Bones'))).to_be(UNRANKED)
    test('a category with no table ranks everything the same', _fn23)

    def _fn24():
        expect(rank_within('runes', item(None, 4242))).to_be(UNRANKED)
        expect(rank_within('food', item(None, 4242))).to_be(UNRANKED)
        expect(rank_within('potions', item(None, 4242))).to_be(UNRANKED)
        expect(rank_within('rangedArmour', item(None, 4242))).to_be(UNRANKED)
    test('a null name never throws', _fn24)

    def _fn25():
        expect(rank_within('oresBarsGems', item('Copper ore', 437))).to_be(rank_within('oresBarsGems', item('Copper ore', 436)))
    test('a noted item ranks with its unnoted twin, because they share a name', _fn25)


describe('rankWithin', _fn2)


def _fn26():
    def _fn27():
        ascending('ammunition', [
        'Rune arrow',
        'Adamant arrow',
        'Mithril arrow',
        'Steel arrow',
        'Iron arrow',
        'Bronze arrow',
        'Rune arrowtips',
        'Adamant arrowtips',
        'Mithril arrowtips',
        'Steel arrowtips',
        'Iron arrowtips',
        'Bronze arrowtips',
    ])
    test('arrows and arrowtips form separate blocks instead of sharing ranks', _fn27)

    def _fn28():
        expect(rank_within('ammunition', item('Bronze arrow(p)'))).to_be(rank_within('ammunition', item('Bronze arrow')))
        expect(rank_within('ammunition', item('Bronze arrowtips'))).not_.to_be(rank_within('ammunition', item('Bronze arrow')))
    test('a poisoned arrow ranks with its plain twin, an arrowtip does not', _fn28)

    def _fn29():
        ascending('ammunition', [
        'Rune arrow',
        'Rune arrowtips',
        'Headless arrow',
        'Barbed bolts',
        'Bolts',
        'Opal bolttips',
        'Rune dart',
        'Bronze dart',
        'Rune dart tip',
        'Bronze dart tip',
        'Rune javelin',
        'Rune knife',
        'Rune thrownaxe',
        'Cannonball',
    ])
    test('bolts, darts, dart tips, javelins, knives and thrownaxes each get their own block', _fn29)

    def _fn30():
        expect(rank_within('ammunition', item('Rune dart'))).to_be_less_than(rank_within('ammunition', item('Bronze dart')))
        expect(rank_within('ammunition', item('Bronze dart'))).to_be_less_than(rank_within('ammunition', item('Rune dart tip')))
    test('a dart tip does not steal the dart rank', _fn30)

    def _fn31():
        ascending('food', [
        'Manta ray',
        'Shark',
        'Swordfish',
        'Bass',
        'Lobster',
        'Tuna',
        'Salmon',
        'Pike',
        'Cod',
        'Trout',
        'Mackerel',
        'Herring',
        'Sardine',
        'Anchovies',
        'Shrimps',
        'Cake',
        'Meat pie',
        'Stew',
        'Bread',
        'Cooked chicken',
        'Cooked meat',
        'Raw shark',
        'Raw lobster',
        'Burnt shark',
    ])
    test('food runs best first by cooking level, raw behind cooked, burnt last', _fn31)

    def _fn32():
        expect(rank_within('food', item('Meat pie'))).to_be_less_than(rank_within('food', item('Cooked meat')))
    test('a meat pie is not filed as meat', _fn32)

    def _fn33():
        ascending('potions', [
        'Super attack(4)',
        'Super attack(3)',
        'Super attack(2)',
        'Super attack(1)',
        'Super strength(4)',
        'Super defence(4)',
        'Attack potion(4)',
        'Attack potion(1)',
        'Strength potion(4)',
        'Defence potion(3)',
        'Ranging potion(4)',
        'Magic potion(4)',
        'Zamorak potion(4)',
        'Prayer potion(4)',
        'Super restore(4)',
        'Restore potion(4)',
        'Superantipoison(4)',
        'Antipoison(4)',
        'Antifire potion(4)',
        'Super energy(4)',
        'Energy potion(4)',
        'Agility potion(4)',
        'Fishing potion(4)',
    ])
    test('potions keep their doses together, strongest dose first', _fn33)

    def _fn34():
        expect(rank_within('potions', item('Vial'))).to_be(UNRANKED)
        expect(rank_within('potions', item('Vial of water'))).to_be(UNRANKED)
    test('an undosed potion item is unranked rather than mis-dosed', _fn34)

    def _fn35():
        ascending('armour', [
        'Dragon platebody',
        'Rune platebody',
        'Adamant platebody',
        'Mithril platebody',
        'Black platebody',
        'Steel platebody',
        'Iron platebody',
        'Bronze platebody',
    ])
    test('melee armour runs dragon to bronze', _fn35)

    def _fn36():
        body = [['black', 2503], ['red', 2501], ['blue', 2499], ['green', 1135]]
        ranks = [rank_within('rangedArmour', item('Dragonhide body', id)) for _, id in body]
        _flat39 = []
        for i, colour in enumerate(body):
            _flat39.extend(([f'{body[i - 1][0]} >= {colour}'] if i > 0 and ranks[i - 1] >= ranks[i] else []))
        gaps = _flat39
        expect(gaps).to_equal([])
    test('dragonhide runs black to green by id, because all four colours share one name', _fn36)

    def _fn40():
        expect(rank_within('rangedArmour', item('Dragonhide body', 2504))).to_be(rank_within('rangedArmour', item('Dragonhide body', 2503)))
    test('a noted dragonhide body ranks with its unnoted twin', _fn40)

    def _fn41():
        expect(rank_within('rangedArmour', item('Dragonhide chaps', 2497))).to_be_less_than(rank_within('rangedArmour', item('Studded body')))
        expect(rank_within('rangedArmour', item('Studded body'))).to_be_less_than(rank_within('rangedArmour', item('Leather body')))
    test('dragonhide outranks studded, which outranks leather', _fn41)

    def _fn42():
        ascending('staves', [
        'Mystic lava staff',
        'Mystic fire staff',
        'Mystic air staff',
        'Lava battlestaff',
        'Fire battlestaff',
        'Air battlestaff',
        'Battlestaff',
        'Staff of saradomin',
        'Staff of iban',
        'Staff of fire',
        'Staff of air',
        'Magic staff',
        'Dramen staff',
        'Staff',
    ])
    test('staves run mystic, battlestaff, god, elemental, then plain', _fn42)


describe('rankWithin, tiers added for the second pass', _fn26)


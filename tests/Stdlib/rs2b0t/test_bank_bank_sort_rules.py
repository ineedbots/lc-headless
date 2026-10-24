"""rs2b0t's test/api/bank/bankSortRules.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record


from rs2004.banksort import CATEGORY_ORDER, category_of, is_unmatched


def item(id, name, cost=1):
    return Record({'slot': 0, 'id': id, 'name': name, 'cost': cost})


def _fn1():
    # Why: the strange plant's fruit is an edible, so it belongs beside the sharks rather than in the junk run at the far end of the bank.
    def _fn2():
        expect(category_of(item(464, 'Strange fruit'))).to_be('food')
    test('Strange fruit sits with the food', _fn2)

    def _fn3():
        expect(category_of(item(995, 'Coins'))).to_be('coins')
        expect(category_of(item(617, 'Coins'))).not_.to_be('coins')
    test('coins are matched by id, never by name', _fn3)

    def _fn4():
        for id in [554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 1436]:
            expect(category_of(item(id, 'whatever'))).to_be('runes')
    test('runes are matched by id', _fn4)

    def _fn5():
        expect(category_of(item(892, 'Rune arrow'))).to_be('ammunition')
        expect(category_of(item(9143, 'Mithril bolts'))).to_be('ammunition')
        expect(category_of(item(811, 'Rune dart'))).to_be('ammunition')
        expect(category_of(item(868, 'Rune knife'))).to_be('ammunition')
    test('ammunition beats the weapon rule for arrows', _fn5)

    def _fn6():
        expect(category_of(item(1333, 'Rune scimitar'))).to_be('weapons')
        expect(category_of(item(861, 'Magic shortbow'))).to_be('weapons')
        expect(category_of(item(1127, 'Rune platebody'))).to_be('armour')
        expect(category_of(item(1201, 'Rune kiteshield'))).to_be('armour')
        expect(category_of(item(1163, 'Rune full helm'))).to_be('armour')
    test('weapons and armour split', _fn6)

    def _fn7():
        expect(category_of(item(199, 'Herb'))).to_be('herbs')
        expect(is_unmatched(item(199, 'Herb'))).to_be(False)
        expect(category_of(item(3049, 'Herb'))).to_be('herbs')
    test('an unidentified herb is a herb, even though every one of them is named Herb', _fn7)

    def _fn8():
        for name in ['Lantadyme', 'Snapdragon', 'Snake weed', 'Ardrigal', 'Sito foil', 'Volencia moss', 'Rogues purse']:
            expect(Record({'name': name, 'category': category_of(item(1, name))})).to_equal(Record({'name': name, 'category': 'herbs'}))
    test('the herbs the table used to miss', _fn8)

    def _fn9():
        expect(category_of(item(985, 'Half of a key'))).to_be('oresBarsGems')
        expect(category_of(item(989, 'Crystal key'))).to_be('oresBarsGems')
        expect(is_unmatched(item(989, 'Crystal key'))).to_be(False)
    test('keys that open a dragonstone chest file with the gems', _fn9)

    def _fn10():
        expect(category_of(item(432, 'Chest key'))).to_be('junk')
        expect(category_of(item(1590, 'Dusty key'))).to_be('junk')
    test('a quest key is still junk, not a gem', _fn10)

    def _fn11():
        expect(category_of(item(385, 'Shark'))).to_be('food')
        expect(category_of(item(379, 'Lobster'))).to_be('food')
        expect(category_of(item(2434, 'Prayer potion(4)'))).to_be('potions')
        expect(category_of(item(229, 'Vial'))).to_be('potions')
        expect(category_of(item(207, 'Grimy ranarr weed'))).to_be('herbs')
        expect(category_of(item(261, 'Clean ranarr weed'))).to_be('herbs')
    test('food, potions and herbs', _fn11)

    def _fn12():
        expect(category_of(item(371, 'Swordfish'))).to_be('food')
        expect(category_of(item(373, 'Raw swordfish'))).to_be('food')
        expect(category_of(item(1289, 'Rune longsword'))).to_be('weapons')
        expect(category_of(item(1319, 'Rune 2h sword'))).to_be('weapons')
    test('a swordfish is food, not a sword', _fn12)

    def _fn13():
        bases = [
        'Super attack',
        'Super strength',
        'Super defence',
        'Super energy',
        'Super restore',
        'Attack potion',
        'Strength potion',
        'Defence potion',
        'Ranging potion',
        'Magic potion',
        'Prayer potion',
        'Restore potion',
        'Zamorak potion',
        'Antipoison',
        'Superantipoison',
        'Antifire potion',
        'Energy potion',
        'Agility potion',
        'Fishing potion',
    ]
        _flat14 = []
        for base in bases:
            _flat14.extend([name for name in [f'{base}({dose})' for dose in [4, 3, 2, 1]] if category_of(item(1, name)) != 'potions'])
        strays = _flat14
        expect(strays).to_equal([])
    test('every dosed potion in the game files as a potion', _fn13)

    def _fn15():
        fish = [
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
    ]
        strays = [name for name in fish if category_of(item(1, name)) != 'food']
        expect(strays).to_equal([])
    test('every cooked fish files as food', _fn15)

    def _fn16():
        for name in [
        'Staff',
        'Magic staff',
        'Staff of air',
        'Battlestaff',
        'Fire battlestaff',
        'Mystic fire staff',
        'Staff of iban',
    ]:
            expect(Record({'name': name, 'category': category_of(item(1, name))})).to_equal(Record({'name': name, 'category': 'staves'}))
        expect(category_of(item(1333, 'Rune scimitar'))).to_be('weapons')
    test('staves file apart from weapons', _fn16)

    def _fn17():
        for name in ['Dragonhide body', 'Dragonhide chaps', 'Dragon vambraces', 'Studded body', 'Leather body', 'Coif']:
            expect(Record({'name': name, 'category': category_of(item(1, name))})).to_equal(Record({'name': name, 'category': 'rangedArmour'}))
        expect(category_of(item(1127, 'Rune platebody'))).to_be('armour')
        expect(category_of(item(1747, 'Dragonhide'))).to_be('supplies')
        expect(category_of(item(1741, 'Leather'))).to_be('supplies')
        expect(category_of(item(1743, 'Hard leather'))).to_be('supplies')
    test('dragonhide files apart from melee armour, raw hide stays a supply', _fn17)

    def _fn18():
        expect(category_of(item(447, 'Mithril ore'))).to_be('oresBarsGems')
        expect(category_of(item(2361, 'Adamantite bar'))).to_be('oresBarsGems')
        expect(category_of(item(1615, 'Uncut dragonstone'))).to_be('oresBarsGems')
        expect(category_of(item(1513, 'Magic logs'))).to_be('logs')
        expect(category_of(item(314, 'Feather'))).to_be('supplies')
        expect(category_of(item(1747, 'Black dragonhide'))).to_be('supplies')
        expect(category_of(item(1359, 'Rune axe'))).to_be('tools')
        expect(category_of(item(1275, 'Rune pickaxe'))).to_be('tools')
        expect(category_of(item(590, 'Tinderbox'))).to_be('tools')
    test('materials, logs, supplies and tools', _fn18)

    def _fn19():
        expect(category_of(item(1777, 'Bow string'))).to_be('supplies')
        expect(category_of(item(1779, 'Bowstring'))).to_be('supplies')
        expect(category_of(item(841, 'Shortbow'))).to_be('weapons')
    test('a bowstring is a supply, not a bow', _fn19)

    def _fn20():
        expect(category_of(item(1613, 'Uncut topaz'))).to_be('oresBarsGems')
    test('a topaz is a gem, not a top', _fn20)

    def _fn21():
        expect(category_of(item(1129, 'Leather body'))).to_be('rangedArmour')
        expect(category_of(item(1095, 'Leather chaps'))).to_be('rangedArmour')
        expect(category_of(item(1741, 'Cowhide'))).to_be('supplies')
    test('hide armour is armour, raw hide is a supply', _fn21)

    def _fn22():
        expect(category_of(item(440, 'Iron ore'))).to_be('oresBarsGems')
        expect(category_of(item(2349, 'Bronze bar'))).to_be('oresBarsGems')
        expect(category_of(item(453, 'Coal'))).to_be('oresBarsGems')
        expect(category_of(item(1, 'Storeroom key'))).to_be('junk')
        expect(category_of(item(2, 'Barrel'))).to_be('junk')
        expect(category_of(item(3, 'Barcrawl card'))).to_be('junk')
    test('short material words do not match inside longer ones', _fn22)

    def _fn23():
        expect(category_of(item(4, 'Golden bowl'))).to_be('junk')
        expect(category_of(item(841, 'Shortbow'))).to_be('weapons')
        expect(category_of(item(837, 'Crossbow'))).to_be('weapons')
    test('a bowl is not a bow', _fn23)

    def _fn24():
        expect(category_of(item(2, 'Cannonball'))).to_be('ammunition')
    test('cannonballs are ammunition', _fn24)

    def _fn25():
        expect(category_of(item(301, 'Lobster pot'))).to_be('tools')
        expect(category_of(item(379, 'Lobster'))).to_be('food')
    test('a lobster pot is a tool, a lobster is food', _fn25)

    def _fn26():
        expect(category_of(item(1712, 'Amulet of glory'))).to_be('jewellery')
        expect(category_of(item(2552, 'Ring of dueling(8)'))).to_be('jewellery')
    test('jewellery', _fn26)

    def _fn27():
        stray = item(31337, 'Some unheard of thing')
        expect(category_of(stray)).to_be('junk')
        expect(is_unmatched(stray)).to_be(True)
    test('anything no rule matches falls to junk and is flagged', _fn27)

    def _fn28():
        bones = item(526, 'Bones')
        expect(category_of(bones)).to_be('junk')
        expect(is_unmatched(bones)).to_be(False)
    test('an explicit junk entry is junk but is not unmatched', _fn28)

    def _fn29():
        expect(category_of(Record({'slot': 0, 'id': 4242, 'name': None, 'cost': 0}))).to_be('junk')
    test('a null name never throws', _fn29)

    def _fn30():
        expect(len(set(CATEGORY_ORDER))).to_be(len(CATEGORY_ORDER))
        expect(len(CATEGORY_ORDER)).to_be(19)
        expect(CATEGORY_ORDER[0]).to_be('coins')
        expect(CATEGORY_ORDER[len(CATEGORY_ORDER) - 1]).to_be('junk')
    test('CATEGORY_ORDER lists every category exactly once, coins first and junk last', _fn30)


describe('categoryOf', _fn1)


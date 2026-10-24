"""rs2b0t's test/api/combat: meleeWeapons.test.ts, food-notes.test.ts and special.test.ts (MIT, see
thirdparty/rs2b0t), on spec.py's describe, test and expect. combatStyleLogic.test.ts is in tests/Stdlib's
test_catalog_shared.py, and the other combat tests beside it."""

from rs2004.catalogs import Record, best_melee_weapon, food_count, known_melee_weapon

BANK = ['Rune scimitar', 'Dragon longsword', 'Rune sword', 'Adamant scimitar', 'Shark', 'Dragon dagger(p)']


def item(name, noted, count=1):
    return Record({'name': name, 'noted': noted, 'count': count})


describe('best_melee_weapon', lambda: [
    test('the highest tier wins, and stab first for a target soft to stab', lambda: expect(best_melee_weapon(BANK, 99, True)).to_be('Dragon longsword')),
    test('the scimitar leads its tier elsewhere', lambda: [
        expect(best_melee_weapon(['Rune scimitar', 'Rune longsword', 'Rune sword'], 99, False)).to_be('Rune scimitar'),
        expect(best_melee_weapon(['Rune longsword', 'Rune sword'], 99, False)).to_be('Rune sword'),
    ]),
    test('a tier above the Attack level is skipped', lambda: [
        expect(best_melee_weapon(BANK, 59, True)).to_be('Rune sword'),
        expect(best_melee_weapon(BANK, 39, True)).to_be('Adamant scimitar'),
    ]),
    test('a weapon a wield refused is skipped, whatever its tier',
         lambda: expect(best_melee_weapon(BANK, 99, True, set(['Dragon longsword']))).to_be('Dragon dagger(p)')),
    test('names match whatever their case, and nothing wieldable is None', lambda: [
        expect(best_melee_weapon(['rune scimitar'], 99, False)).to_be('Rune scimitar'),
        expect(best_melee_weapon(['Shark', 'Coins'], 99, False)).to_be_null(),
    ]),
])

describe('known_melee_weapon', lambda: [
    test('finds the one melee weapon in a worn list', lambda: [
        expect(known_melee_weapon(['Rune full helm', 'Rune scimitar', 'Dragonfire shield'])).to_be('Rune scimitar'),
        expect(known_melee_weapon(['Rune full helm'])).to_be_null(),
    ]),
])


def noted_food(name):
    items = [item(name, True, 100), item(name, False, 1)]
    return [expect(food_count(items, name)).to_be(1), expect(food_count(items[0:1], name)).to_be(0)]


describe('food_count', lambda: [
    test('noted Lobster does not count as edible food', lambda: noted_food('Lobster')),
    test('noted Shark does not count as edible food', lambda: noted_food('Shark')),
    test('partial foods still count without Eat actions in the bank view',
         lambda: expect(food_count([item('Cake', True), item('2/3 cake', False), item('Slice of cake', False)], 'Cake')).to_be(2)),
])

describe('weapon specials', lambda: [
    test('a weapon without a special has no cost', lambda: [
        expect(special.cost('Rune scimitar')).to_be_null(),
        expect(special.cost('Staff of fire')).to_be_null(),
        expect(special.cost('')).to_be_null(),
    ]),
    test('cost lookup ignores case and padding', lambda: [
        expect(special.cost('Dragon dagger')).to_be(250),
        expect(special.cost('  dragon DAGGER(p) ')).to_be(250),
        expect(special.cost('Magic shortbow')).to_be(350),
        expect(special.cost('Rune thrownaxe')).to_be(100),
    ]),
    test('every special is affordable on a full bar',
         lambda: [expect(special.cost(w)).to_be_less_than_or_equal(SA_MAX_ENERGY) for w in ['Dragon dagger', 'Dragon halberd', 'Magic longbow', 'Rune claws']]),
])

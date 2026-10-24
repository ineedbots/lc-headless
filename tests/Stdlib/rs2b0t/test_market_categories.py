"""rs2b0t's test/api/market/categories.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import CATEGORIES, build_catalog, category_of, is_popular, shelves


def rec(id, name, over=None):
    if over is None:
        over = Record({})
    _merged1 = {}
    for _k, _v in {
        'id': id,
        'name': name,
        'cost': 1,
        'stackable': False,
        'members': False,
        'equippable': False,
        'certlink': -1,
        'certtemplate': -1,
    }.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged1[_k] = _v
    return Record(_merged1)


def shelf(name, slot=None, consumable=None):
    return category_of(Record({'name': name, 'equippable': slot is not None}), Record({'slot': slot, 'consumable': consumable}))


def _fn2():
    def _fn3():
        expect(shelf('Nature rune')).to_be('Runes')
        expect(shelf('Iron ore')).to_be('Ores')
        expect(shelf('Steel bar')).to_be('Bars')
        expect(shelf('Yew logs')).to_be('Logs')
        expect(shelf('Logs')).to_be('Logs')
        expect(shelf('Maple longbow')).to_be('Bows')
        expect(shelf('Rune arrow')).to_be('Arrows')
        expect(shelf('Big bones')).to_be('Bones')
        expect(shelf('Ranarr seed')).to_be('Seeds')
        expect(shelf('Green dragonhide')).to_be('Hides')
    test('the obvious shelves read off the name', _fn3)

    # Why: "Rune scimitar" and "Nature rune" both carry the word, and only the ending tells them apart.
    def _fn4():
        expect(shelf('Rune scimitar', 'righthand')).to_be('Weapons')
        expect(shelf('Rune platebody', 'torso')).to_be('Armour')
        expect(shelf('Nature rune')).to_be('Runes')
    test('a rune weapon is not a rune', _fn4)

    def _fn5():
        expect(shelf('Chocolate bar')).to_be('Food')
        expect(shelf('Bronze bar')).to_be('Bars')
    test('the one bar you eat is food', _fn5)

    def _fn6():
        expect(shelf('Bow string')).not_.to_be('Bows')
        expect(shelf('Bowl')).not_.to_be('Bows')
        expect(shelf('Shortbow')).to_be('Bows')
    test('bow string and bowl are not bows', _fn6)

    def _fn7():
        expect(shelf('Attack potion(3)')).to_be('Potions')
        expect(shelf('Strength potion')).to_be('Potions')
    test('potions shelve on their dose suffix as well as the word', _fn7)

    def _fn8():
        expect(shelf('Grimy ranarr')).to_be('Herbs')
        expect(shelf('Guam leaf')).to_be('Herbs')
        expect(shelf('Eye of newt')).to_be('Herblore')
        expect(shelf('Vial of water')).to_be('Herblore')
    test('herbs and their secondaries stay apart', _fn8)

    def _fn9():
        expect(shelf('Uncut ruby')).to_be('Gems')
        expect(shelf('Diamond')).to_be('Gems')
    test('gems shelve cut or uncut', _fn9)

    # Why: the stone names the jewellery cut from it, and those belong with the other jewellery.
    def _fn10():
        expect(shelf('Sapphire ring', 'ring')).to_be('Jewellery')
        expect(shelf('Diamond amulet', 'front')).to_be('Jewellery')
        expect(shelf('Ruby necklace', 'front')).to_be('Jewellery')
    test('what a gem is set into is jewellery, not a gem', _fn10)

    def _fn11():
        expect(shelf('Lobster', None, 'eat')).to_be('Food')
        expect(shelf('Raw shrimps')).to_be('Food')
        expect(shelf('Burnt fish')).to_be('Food')
    test('what you eat shelves as food, however it is named', _fn11)

    def _fn12():
        expect(shelf('Lobster pot')).to_be('Tools')
        expect(shelf('Fly fishing rod')).to_be('Tools')
        expect(shelf('Tinderbox')).to_be('Tools')
    test('fishing and farming gear is tools, not other', _fn12)

    def _fn13():
        expect(shelf('Amulet of strength', 'front')).to_be('Jewellery')
        expect(shelf('Adamant kiteshield', 'lefthand')).to_be('Armour')
        expect(shelf('Mystery thing')).to_be('Other')
    test('a slot decides what the name cannot', _fn13)


describe('categoryOf', _fn2)


def _fn14():
    def _fn15():
        cat = build_catalog([
        rec(440, 'Iron ore'),
        rec(441, 'Iron ore', Record({'stackable': True, 'certlink': 440, 'certtemplate': 799})),
        rec(561, 'Nature rune', Record({'stackable': True})),
        rec(1515, 'Yew logs'),
        rec(9999, 'Mystery thing'),
    ])
        out = shelves(cat)
        expect([r.id for r in out.get('Ores')]).to_equal([440])
        expect([r.id for r in out.get('Runes')]).to_equal([561])
        expect([r.id for r in out.get('Logs')]).to_equal([1515])
        expect([r.id for r in out.get('Other')]).to_equal([9999])
        # Why: Popular overlays the others, so only the exclusive shelves add up to the catalogue.
        exclusive = [out[name] for name in out if name != 'Popular']
        total = sum([len(list_) for list_ in exclusive])
        expect(total).to_be(len(cat.items))
    test('every item lands on exactly one shelf, and notes are left off', _fn15)

    def _fn18():
        out = shelves(build_catalog([
        rec(882, 'Bronze arrow', Record({'stackable': True})),
        rec(883, 'Bronze arrow', Record({'stackable': True, 'stack_variant': True})),
        rec(884, 'Bronze arrow', Record({'stackable': True, 'stack_variant': True})),
    ]))
        expect([r.id for r in out.get('Arrows')]).to_equal([882])
    test('a stackable shows once, not once per pile size', _fn18)

    def _fn19():
        out = shelves(build_catalog([rec(440, 'Iron ore')]))
        expect(list(list(out.keys()))).to_equal(list(CATEGORIES))
    test('every shelf is present even when empty, so the list of them is stable', _fn19)


describe('shelves', _fn14)


def _fn20():
    def pop(name, slot=None):
        return is_popular(Record({'name': name, 'equippable': slot is not None}), Record({'slot': slot}))

    def _fn21():
        expect(pop('Nature rune')).to_be(True)
        expect(pop('Iron ore')).to_be(True)
        expect(pop('Steel bar')).to_be(True)
        expect(pop('Rune arrow')).to_be(True)
        expect(pop('Grimy ranarr')).to_be(True)
        expect(pop('Uncut ruby')).to_be(True)
    test('whole shelves people stock by the load are on it', _fn21)

    def _fn22():
        for name in [
        'Rune platebody',
        'Rune scimitar',
        'Lobster',
        'Raw shark',
        'Feather',
        'Flax',
        'Bow string',
        'Rune essence',
        'Crystal key',
        'Half of a key',
        'Amulet of glory(4)',
    ]:
            expect(pop(name)).to_be(True)
    test('the named stock is on it', _fn22)

    # Why: the 3-dose is the one that trades, so the others stay addable by hand instead of filling the shelf.
    def _fn23():
        expect(pop('Super attack(3)')).to_be(True)
        expect(pop('Prayer potion(3)')).to_be(True)
        expect(pop('Superantipoison(3)')).to_be(True)
        expect(pop('Super attack(4)')).to_be(False)
        expect(pop('Prayer potion(1)')).to_be(False)
    test('potions are the 3-dose only', _fn23)

    # Why: "arrows" means the metal line people buy by the thousand, not everything the shelf holds.
    def _fn24():
        expect(pop('Rune arrow')).to_be(True)
        expect(pop('Bronze arrow')).to_be(True)
        expect(pop('Barbed bolts')).to_be(False)
        expect(pop('Black dart')).to_be(False)
        expect(pop('Rune javelin')).to_be(False)
        expect(pop('Rune arrowtips')).to_be(False)
        expect(pop('Arrow shaft')).to_be(False)
    test('only the standard arrows ride in on the ammunition, not the rest of the shelf', _fn24)

    def _fn25():
        expect(pop('Uncut ruby')).to_be(True)
        expect(pop('Ruby ring', 'ring')).to_be(False)
    test('a gem is popular but a ring cut from one is not', _fn25)

    def _fn26():
        expect(pop('Yew logs')).to_be(False)
        expect(pop('Adamant platebody', 'torso')).to_be(False)
        expect(pop('Swamp tar')).to_be(False)
    test('everything else is left off', _fn26)

    def _fn27():
        out = shelves(build_catalog([rec(561, 'Nature rune', Record({'stackable': True}))]))
        expect([r.id for r in out.get('Runes')]).to_equal([561])
        expect([r.id for r in out.get('Popular')]).to_equal([561])
    test('an item on Popular keeps the shelf it belongs to', _fn27)


describe('the Popular shelf', _fn20)


"""The market's generated tables against the real cache: every id they name is an obj with the name they give
it, and the live catalog built from reader.obj_catalog() resolves what players type. rs2b0t checks its tables
against the content pack's obj.pack instead (tools/items/gen-*.ts --check). On spec.py's describe, test and
expect."""

from rs2004.market import ITEM_ALIASES, MARKET_PRICES, NAME_COLLISIONS, NAME_SYNONYMS, UNTRADEABLE_IDS
from rs2004.market import client_name, display_name, live_catalog, noted_id, resolve_by_name, shelf_of, unnoted_id

# MARKET_PRICES' sets have made-up ids from here.
SET_IDS_FROM = 1000000
# Where this cache names an obj otherwise than the rs2b2t content rs2b0t's tables come from: the holy books'
# torn pages carry their god's letter, "Cowhide" is one word, and the Mort Myre shells and the toad batta have
# their later names. The tables key on ids, so only the labels differ.
RENAMED_IDS = set([1739, 2221, 2255, 3327, 3337, 3345, 3355] + list(range(3827, 3839)))


def _name(id):
    kind = reader.item_type(id)
    return kind.name if kind is not None else None


def _fn1():
    def _fn2():
        wrong = [(p['id'], p['name'], _name(p['id'])) for p in MARKET_PRICES if p['id'] < SET_IDS_FROM and p['id'] not in RENAMED_IDS and _name(p['id']) != p['name']]
        expect(wrong).to_equal([])
    test('every priced item is the obj it names', _fn2)

    def _fn3():
        wrong = []
        for group in NAME_COLLISIONS:
            for member in group['objs']:
                if member['id'] not in RENAMED_IDS and _name(member['id']) != group['name']:
                    wrong.append((member['id'], group['name'], _name(member['id'])))
        expect(wrong).to_equal([])
    test('every collision group shares the name it is filed under', _fn3)

    def _fn4():
        for id in ITEM_ALIASES:
            expect(_name(id) is not None, f'#{id}').to_be(True)
        for id in UNTRADEABLE_IDS:
            expect(reader.item_type(id) is not None, f'#{id}').to_be(True)
    test('every alias and untradeable id is an obj', _fn4)


describe('the market tables', _fn1)


def _fn5():
    def _fn6():
        cat = live_catalog()
        expect(len(cat.items)).to_be_greater_than(1000)
        iron = reader.item_ids('Iron ore')
        expect(unnoted_id(cat, noted_id(cat, 440))).to_be(440)
        expect(440 in iron).to_be(True)
        expect(shelf_of(cat.by_id[440])).to_be('Ores')
    test('the live catalog holds the cache, notes linked', _fn6)

    def _fn7():
        cat = live_catalog()
        expect([r.id for r in resolve_by_name(cat, 'iron ore')]).to_equal([440])
        expect([r.id for r in resolve_by_name(cat, 'blue dhide')]).to_equal([1751])
        expect([r.id for r in resolve_by_name(cat, 'loop half of key')]).to_equal([987])
        expect([r.id for r in resolve_by_name(cat, 'maple longbow')]).to_equal([851])
        expect([r.id for r in resolve_by_name(cat, 'maple longbow u')]).to_equal([62])
        expect(display_name(cat, 1751)).to_be('Blue dragonhide')
        expect(client_name(cat, 1751)).to_be('Dragonhide')
    test('what players type resolves to the cache objs', _fn7)

    def _fn8():
        cat = live_catalog()
        # The coins' pile models repeat its name and aren't items of their own.
        expect(len([r for r in cat.items if r.name == 'Coins'])).to_be(1)
        expect(len(NAME_SYNONYMS)).to_be_greater_than(0)
    test('pile-size models stay off the shelf', _fn8)


describe('the live catalog', _fn5)

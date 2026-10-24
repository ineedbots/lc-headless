"""rs2b0t's test/api/market/catalog.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import build_catalog, client_name, display_name, noted_id, resolve_by_name, search_catalog, unnoted_id


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


RECORDS = [
    rec(440, 'Iron ore', Record({'cost': 17})),
    rec(441, 'Iron ore', Record({'certlink': 440, 'certtemplate': 799, 'stackable': True})),
    rec(851, 'Maple longbow', Record({'cost': 640, 'equippable': True})),
    rec(852, 'Maple longbow', Record({'certlink': 851, 'certtemplate': 799, 'stackable': True})),
    rec(62, 'Maple longbow', Record({'cost': 320})),
    rec(63, 'Maple longbow', Record({'certlink': 62, 'certtemplate': 799, 'stackable': True})),
    rec(995, 'Coins', Record({'stackable': True})),
]
CAT = build_catalog(RECORDS)


def _fn2():
    def _fn3():
        expect([r.id for r in CAT.items]).to_equal([995, 440, 62, 851])
    test('items holds only unnoted entries, name-sorted', _fn3)

    def _fn4():
        expect(CAT.noted_of.get(440)).to_be(441)
        expect(CAT.unnoted_of.get(441)).to_be(440)
    test('maps both directions', _fn4)

    def _fn5():
        expect((CAT.by_id.get(441).stackable if CAT.by_id.get(441) is not None else None)).to_be(True)
    test('byId keeps noted entries too', _fn5)


describe('buildCatalog', _fn2)


def _fn6():
    def _fn7():
        expect(unnoted_id(CAT, 441)).to_be(440)
        expect(unnoted_id(CAT, 440)).to_be(440)
    test('unnotedId collapses a note onto its item', _fn7)

    def _fn8():
        expect(unnoted_id(CAT, 9999)).to_be(9999)
    test('unnotedId passes an unknown id through', _fn8)

    def _fn9():
        expect(noted_id(CAT, 440)).to_be(441)
        expect(noted_id(CAT, 995)).to_be_null()
    test('notedId returns null for an item with no note form', _fn9)


describe('unnotedId / notedId', _fn6)


def _fn10():
    def _fn11():
        expect(sorted([r.id for r in search_catalog(CAT, 'maple')], key=lambda a: a)).to_equal([62, 851])
    test('substring match, case-insensitive, unnoted only', _fn11)

    def _fn12():
        expect(search_catalog(CAT, '', 2)).to_have_length(2)
    test('empty query returns everything up to the limit', _fn12)


describe('searchCatalog', _fn10)


def _fn13():
    # Why: bows share names with unstrung variants; only the strung item is wearable.
    def _fn14():
        expect([r.id for r in resolve_by_name(CAT, 'maple longbow')]).to_equal([851])
    test('a bare bow name is the strung one', _fn14)

    def _fn15():
        expect([r.id for r in resolve_by_name(CAT, 'maple longbow u')]).to_equal([62])
        expect([r.id for r in resolve_by_name(CAT, 'Maple Longbow U')]).to_equal([62])
    test('a trailing u is the unstrung one', _fn15)

    def _fn16():
        expect([r.id for r in resolve_by_name(CAT, 'maple longbow (u)')]).to_equal([62])
    test('a name written with (u) reaches the unstrung one too', _fn16)

    # Why: people ask for "1k maple longbows", and the item is called "Maple longbow".
    def _fn17():
        expect([r.id for r in resolve_by_name(CAT, 'maple longbows')]).to_equal([851])
        expect([r.id for r in resolve_by_name(CAT, 'maple longbows u')]).to_equal([62])
        expect([r.id for r in resolve_by_name(CAT, 'iron ores')]).to_equal([440])
    test('a plural still finds the item', _fn17)

    def _fn18():
        expect([r.id for r in resolve_by_name(CAT, 'coins')]).to_equal([995])
    test('a name that genuinely ends in s is not stripped', _fn18)

    def _fn19():
        expect([r.id for r in resolve_by_name(CAT, 'maple')]).to_equal([851])
    test('a partial name still narrows to the strung one', _fn19)

    def _fn20():
        expect([r.id for r in resolve_by_name(CAT, 'iron ore')]).to_equal([440])
    test('a name with no collision is unaffected by the rule', _fn20)

    # Why: ignore a narrowing suffix when no colliding pair exists.
    def _fn21():
        expect([r.id for r in resolve_by_name(CAT, 'iron ore u')]).to_equal([440])
    test('a trailing u on an item with no unstrung twin still finds it', _fn21)

    def _fn22():
        expect(resolve_by_name(CAT, 'dragon claws')).to_equal([])
    test('no match returns empty', _fn22)

    # Why: the id stays as an escape hatch for collisions the wear rule cannot split.
    def _fn23():
        expect([r.id for r in resolve_by_name(CAT, '#851')]).to_equal([851])
        expect([r.id for r in resolve_by_name(CAT, ' #62 ')]).to_equal([62])
    test('#id picks one item outright', _fn23)

    def _fn24():
        expect(resolve_by_name(CAT, '#99999')).to_equal([])
    test('#id for something not in the catalog returns empty', _fn24)

    def _fn25():
        expect(resolve_by_name(CAT, '#441')).to_equal([])
    test('a noted id is not addressable, since rows key on the unnoted one', _fn25)

    def _fn26():
        expect(resolve_by_name(CAT, '  ')).to_equal([])
    test('an empty query matches nothing', _fn26)


describe('resolveByName', _fn13)
# Why: the live client only sees display names, so these ids are taken from the content pack.
ALIASED = [rec(985, 'Half of a key'), rec(987, 'Half of a key'), rec(1747, 'Dragonhide'), rec(1749, 'Dragonhide'), rec(1751, 'Dragonhide'), rec(1753, 'Dragonhide'), rec(1135, 'Dragonhide body', Record({'equippable': True})), rec(2499, 'Dragonhide body', Record({'equippable': True})), rec(2501, 'Dragonhide body', Record({'equippable': True})), rec(2503, 'Dragonhide body', Record({'equippable': True})), rec(1007, 'Cape', Record({'equippable': True})), rec(1021, 'Cape', Record({'equippable': True})), rec(1675, 'Sapphire amulet'), rec(1694, 'Sapphire amulet', Record({'equippable': True})), rec(249, 'Guam leaf'), rec(199, 'Herb'), rec(201, 'Herb')] + list(RECORDS)
ALIAS_CAT = build_catalog(ALIASED)


def ids(query):
    return [r.id for r in resolve_by_name(ALIAS_CAT, query)]


def _fn27():
    def _fn28():
        expect(display_name(ALIAS_CAT, 1753)).to_be('Green dragonhide')
        expect(display_name(ALIAS_CAT, 1751)).to_be('Blue dragonhide')
        expect(display_name(ALIAS_CAT, 987)).to_be('Loop half of key')
        expect(display_name(ALIAS_CAT, 985)).to_be('Tooth half of key')
        expect(display_name(ALIAS_CAT, 62)).to_be('Maple longbow (u)')
    test('a name the content repeats gets the word that separates it', _fn28)

    def _fn29():
        expect(display_name(ALIAS_CAT, 440)).to_be('Iron ore')
        expect(display_name(ALIAS_CAT, 851)).to_be('Maple longbow')
    test('a name nothing shares is left alone', _fn29)

    def _fn30():
        expect(display_name(ALIAS_CAT, 9999)).to_be('item 9999')
    test('an id the catalog has never heard of still reads as something', _fn30)


describe('displayName', _fn27)


def _fn31():
    def _fn32():
        expect(ids('loop half of key')).to_equal([987])
        expect(ids('tooth half of key')).to_equal([985])
        # Why: the display name carries an "a" the player's own words for it do not.
        expect(ids('loop half of a key')).to_equal([987])
        expect(ids('tooth half of a key')).to_equal([985])
    test('the key halves answer to their halves', _fn32)

    def _fn33():
        expect(sorted(ids('half of a key'), key=lambda a: a)).to_equal([985, 987])
    test('the bare key name stays ambiguous, so the shop can ask which', _fn33)

    def _fn34():
        expect(ids('green dragonhide')).to_equal([1753])
        expect(ids('blue dragonhide')).to_equal([1751])
        expect(ids('red dragonhide')).to_equal([1749])
        expect(ids('black dragonhide')).to_equal([1747])
    test('dragonhide answers to a colour', _fn34)

    def _fn35():
        expect(sorted(ids('dragonhide'), key=lambda a: a)).to_equal([1747, 1749, 1751, 1753])
    test('bare dragonhide is ambiguous across every colour', _fn35)

    def _fn36():
        expect(ids('green dragonhide body')).to_equal([1135])
        expect(ids('black dragonhide body')).to_equal([2503])
    test('green is the bare member of the body family and still answers to green', _fn36)

    def _fn37():
        expect(ids('blue dhide')).to_equal([1751])
        expect(ids('black d hide')).to_equal([1747])
        expect(ids('green dhide body')).to_equal([1135])
        expect(ids('red d body')).to_equal([2501])
    test('shorthand stands in for the display name', _fn37)

    def _fn38():
        expect(ids('red cape')).to_equal([1007])
        expect(ids('blue cape')).to_equal([1021])
    test('capes answer to their colour', _fn38)

    def _fn39():
        expect(ids('maple longbow unstrung')).to_equal([62])
        expect(ids('maple longbow (u)')).to_equal([62])
        expect(ids('maple longbow')).to_equal([851])
    test('bows answer to unstrung as well as the u suffix', _fn39)

    def _fn40():
        expect(ids('sapphire amulet u')).to_equal([1675])
        expect(ids('strung sapphire amulet')).to_equal([1694])
    test('amulets split on strung and unstrung', _fn40)

    # Why: an exact display name must beat an alias within the `Herb` group.
    def _fn41():
        expect(ids('guam leaf')).to_equal([249])
        expect(ids('guam herb')).to_equal([199])
    test('a plain name wins over an alias word inside it', _fn41)

    def _fn42():
        expect(resolve_by_name(ALIAS_CAT, 'green', exact_only=True)).to_equal([])
        expect(resolve_by_name(ALIAS_CAT, 'blue', exact_only=True)).to_equal([])
    test('a colour on its own names nothing', _fn42)

    def _fn43():
        expect([r.id for r in search_catalog(ALIAS_CAT, 'loop half')]).to_equal([987])
        expect(sorted([r.id for r in search_catalog(ALIAS_CAT, 'dhide body')], key=lambda a: a)).to_equal([1135, 2499, 2501, 2503])
    test('an alias label is searchable from the panel', _fn43)


describe('resolveByName with aliases', _fn31)


# Why: trade actions need the pack's display name, not the shop label.
def _fn44():
    def _fn45():
        expect(client_name(ALIAS_CAT, 1751)).to_be('Dragonhide')
        expect(display_name(ALIAS_CAT, 1751)).to_be('Blue dragonhide')
        expect(client_name(ALIAS_CAT, 987)).to_be('Half of a key')
        expect(display_name(ALIAS_CAT, 987)).to_be('Loop half of key')
    test('is what the client calls the obj, whatever the shop calls it', _fn45)

    def _fn46():
        expect(client_name(ALIAS_CAT, 9999)).to_be_undefined()
    test('is undefined for an id the client never sent, so a caller refuses rather than clicks', _fn46)

    def _fn47():
        expect(client_name(ALIAS_CAT, 440)).to_be('Iron ore')
        expect(display_name(ALIAS_CAT, 440)).to_be('Iron ore')
    test('an unaliased obj reads the same either way', _fn47)


describe('clientName', _fn44)


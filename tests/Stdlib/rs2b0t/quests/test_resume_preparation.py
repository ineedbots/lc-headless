"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/engine/resumePreparation.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.engine.resume_preparation import resume_preparation

def module_for(id='imp', extra=None):
    if extra is None:
        extra = Record({})
    _merged1 = {}
    for _k, _v in {
        'record': Record({'id': id, 'name': id, 'quest_points': 1, 'requirements': Record({}), 'items': []}),
        'decide': lambda *_args: (Record({'kind': 'done'})),
    }.items():
        _merged1[_k] = _v
    for _k, _v in (extra._fields if isinstance(extra, Record) else extra).items():
        _merged1[_k] = _v
    return (Record(_merged1))


def snap(extra=None):
    if extra is None:
        extra = Record({})
    _merged2 = {}
    for _k, _v in {
        'journal': 'in_progress',
        'inv': {},
        'worn': set(['rune platebody']),
        'worn_ids': set([1127]),
        'no_progress': 0,
        'bank_coins': 0,
        'free_slots': 0,
    }.items():
        _merged2[_k] = _v
    for _k, _v in (extra._fields if isinstance(extra, Record) else extra).items():
        _merged2[_k] = _v
    return QuestSnapshot(**_merged2)


def item(id, name, count=1, noted=False):
    return (Record({'id': id, 'name': name, 'count': count, 'noted': noted}))


def essence():
    return [item(1436, 'Rune essence') for _ in range(28)]


def _fn3():
    def _fn4():
        expect(resume_preparation(module_for(), snap(), essence(), 'Trout')).to_equal(Record({'keep_ids': [], 'caps': []}))
    test('clears a full essence pack without confusing essence with spell runes', _fn4)

    def _fn5():
        for journal in ['not_started', 'unknown', 'complete']:
            expect(resume_preparation(module_for(), snap(Record({'journal': journal})), essence(), 'Trout')).to_be_null()
        expect(resume_preparation(module_for(), snap(Record({'free_slots': 5})), essence(), 'Trout')).to_be_null()
        expect(resume_preparation(module_for(), snap(Record({'free_slots': None})), essence(), 'Trout')).to_be_null()
    test('does not prepare an unstarted, unread, completed or roomy pack', _fn5)

    def _fn6():
        inventory = [
        item(779, 'Crest part'),
        item(780, 'Crest part'),
        item(781, 'Crest part'),
        item(446, "'perfect' gold ore"),
        item(2365, "'perfect' gold bar"),
        item(623, 'Sword pommel'),
        item(609, 'Rashiliya corpse'),
        item(610, 'Zadimus corpse'),
        item(605, 'Bone key'),
        item(1436, 'Rune essence'),
    ]
        expect(resume_preparation(module_for(), snap(), inventory, None)).to_equal(Record({'keep_ids': [779, 780, 781, 446, 2365, 623, 609, 610, 605], 'caps': []}))
    test('preserves exact quest objects sharing display names and single-copy intermediates', _fn6)

    def _fn7(id, supplies, keep_ids):
        expect(resume_preparation(module_for(id), snap(), list(supplies) + [item(1436, 'Rune essence')], None)).to_equal(Record({'keep_ids': keep_ids, 'caps': []}))
    test_each([
        [
        'tbwt',
        [item(3157, 'Karambwan vessel'), item(3159, 'Karambwan vessel'), item(3125, 'Jogre bones')],
        [3157, 3159, 3125],
    ],
        ['upass', [item(942, 'Lit arrows', 10), item(1035, 'Zamorak monk top')], [942, 1035]],
        ['legends', [item(727, 'Hollow reed'), item(975, 'Machete')], [727, 975]],
        [
        'hero',
        [item(1586, 'Miscellaneous key'), item(1577, "Pete's candlestick"), item(97, 'Unfinished potion')],
        [1586, 1577, 97],
    ],
    ])('preserves %s tradeable quest supplies', _fn7)

    def _fn8():
        inventory = [
        item(995, 'Coins', 300),
        item(556, 'Air rune', 500),
        item(560, 'Death rune', 50),
        item(177, 'Antipoison(2)'),
        item(139, 'Prayer potion(3)'),
        item(946, 'Knife'),
        item(1436, 'Rune essence'),
    ]
        expect(resume_preparation(module_for('imp', Record({'tools': ['Knife']})), snap(), inventory, None)).to_equal(Record({'keep_ids': [995, 556, 560, 177, 139, 946], 'caps': []}))
    test('keeps coins, spell runes, potions and normalized declared tools', _fn8)

    def _fn9():
        inventory = [item(333, 'Trout') for _ in range(28)]
        expect(resume_preparation(module_for(), snap(), inventory, 'Trout')).to_equal(Record({'keep_ids': [333], 'caps': [Record({'id': 333, 'qty': 8})]}))
    test('aggregates food slots and leaves room in a full food pack', _fn9)

    def _fn10():
        inventory = [item(333, 'Trout', 8), item(379, 'Lobster', 20)]
        module = module_for('imp', Record({'sustain': Record({'foods': ['Lobster'], 'eat_below_hp': 0.5})}))
        expect(resume_preparation(module, snap(), inventory, 'Trout')).to_equal(Record({'keep_ids': [333, 379], 'caps': [Record({'id': 379, 'qty': 0})]}))
    test('limits mixed survival food to a shared allowance', _fn10)

    def _fn11():
        inventory = [item(386, 'Shark', 1000, True), item(385, 'Shark', 8)]
        expect(resume_preparation(module_for(), snap(), inventory, 'Shark')).to_equal(Record({'keep_ids': [385], 'caps': []}))
    test('deposits noted food in bulk without consuming the unnoted food allowance', _fn11)

    def _fn12():
        inventory = [item(385, 'Shark', 20), item(386, 'Shark', 1000, True)]
        expect(resume_preparation(module_for(), snap(), inventory, 'Shark')).to_equal(Record({'keep_ids': [385], 'caps': [Record({'id': 385, 'qty': 8})]}))
    test('caps only unnoted surplus when food display names collide', _fn12)

    def _fn13():
        module = module_for('death', Record({'tools': ['pickaxe']}))
        inventory = [item(2310, 'Bread', 1000, True), item(1266, 'Bronze pickaxe', 20, True)]
        expect(resume_preparation(module, snap(), inventory, 'Bread')).to_equal(Record({'keep_ids': [], 'caps': []}))
    test('does not preserve noted quest materials or tools', _fn13)

    def _fn14():
        inventory = [item(1333, 'Rune scimitar') for _ in range(28)]
        expect(resume_preparation(module_for(), snap(), inventory, None)).to_equal(Record({'keep_ids': [1333], 'caps': [Record({'id': 1333, 'qty': 1})]}))
    test('banks duplicate physical spare equipment while keeping one usable copy', _fn14)

    def _fn15():
        equipment = [item(1333, 'Rune scimitar') for _ in range(28)]
        expect(resume_preparation(module_for('imp', Record({'tools': ['scimitar']})), snap(), equipment, None)).to_be_null()
        module = module_for()
        module.record.items = [Record({'name': 'Rune scimitar', 'qty': 2, 'kind': 'mustHave'})]
        expect(resume_preparation(module, snap(), equipment, None)).to_be_null()
        disguise = [item(1125, 'Black platebody') for _ in range(28)]
        expect(resume_preparation(module_for('hero'), snap(), disguise, None)).to_be_null()
        staffs = [item(1409, 'Staff of iban') for _ in range(28)]
        expect(resume_preparation(module_for(), snap(), staffs, None)).to_be_null()
    test('keeps equipment required by quest IDs, tools and declared materials', _fn15)

    def _fn16():
        inventory = [item(882, 'Bronze arrow', 1000), item(806, 'Bronze dart', 1000), item(1436, 'Rune essence')]
        expect(resume_preparation(module_for(), snap(), inventory, None)).to_equal(Record({'keep_ids': [882, 806], 'caps': []}))
    test('does not mistake stacked ammunition and thrown weapons for duplicate gear slots', _fn16)

    def _fn17():
        death = [item(2309, 'Bread', 10), item(333, 'Trout', 10), item(1436, 'Rune essence')]
        expect(resume_preparation(module_for('death'), snap(), death, 'Trout')).to_equal(Record({'keep_ids': [2309, 333], 'caps': []}))
        module = module_for('crest')
        module.record.items = [Record({'name': 'Swordfish', 'qty': 1, 'kind': 'acquirable'})]
        expect(resume_preparation(module, snap(), [item(373, 'Swordfish', 12), item(1436, 'Rune essence')], 'Swordfish')).to_equal(Record({'keep_ids': [373], 'caps': [Record({'id': 373, 'qty': 1})]}))
    test('preserves required Death Plateau hand-in food and caps surplus Family Crest ingredients', _fn17)

    def _fn18(quest, id, name, qty):
        expect(resume_preparation(module_for(quest), snap(), [item(id, name) for _ in range(28)], name)).to_equal(Record({'keep_ids': [id], 'caps': [Record({'id': id, 'qty': qty})]}))
        expect(resume_preparation(module_for(quest), snap(), [item(id, name, qty - 1), item(1436, 'Rune essence')], name)).to_equal(Record({'keep_ids': ([id] if qty > 1 else []), 'caps': []}))
    test_each([['death', 333, 'Trout', 10], ['death', 2309, 'Bread', 10], ['crest', 373, 'Swordfish', 1]])('makes room in a full %s material-food pack', _fn18)

    def _fn19():
        module = module_for('death')
        module.record.items = [Record({'name': 'Trout', 'qty': 12, 'kind': 'acquirable'})]
        expect(resume_preparation(module, snap(), [item(333, 'Trout', 28)], 'Trout')).to_equal(Record({'keep_ids': [333], 'caps': [Record({'id': 333, 'qty': 12})]}))
    test('honors declared food quantities above the material minimum', _fn19)

    def _fn20(id):
        inventory = [item(id, 'Golden bowl')] + list(essence()[1:])
        expect(resume_preparation(module_for('legends'), snap(), inventory, 'Trout')).to_be_null()
        expect(resume_preparation(module_for('legends'), snap({'inv_ids': {id: 1}}), essence(), 'Trout')).to_be_null()
    test_each([723, 724, 725, 726])('does not send a filled Legends bowl %i to the bank', _fn20)

    def _fn21(quest, id, name):
        expect(resume_preparation(module_for(quest), snap(), [item(id, name, 12), item(1436, 'Rune essence')], name)).to_equal(Record({'keep_ids': [id], 'caps': [Record({'id': id, 'qty': 1})] if quest == 'tbwt' else []}))
    test_each([['eadgar', 2116, 'Pineapple chunks'], ['tbwt', 1963, 'Banana']])('does not trim %s quest materials selected as food', _fn21)

    def _fn22():
        state = snap()
        inventory = [item(995, 'Coins', 100), item(605, 'Bone key'), item(99999, None)]
        before = repr(Record({'state': state, 'inventory': inventory}))
        expect(resume_preparation(module_for(), state, inventory, 'Trout')).to_be_null()
        expect(repr(Record({'state': state, 'inventory': inventory}))).to_equal(before)
    test('returns no work for protected-only packs and does not change equipment or snapshots', _fn22)


describe('resumePreparation', _fn3)

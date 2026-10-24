"""rs2b0t's test/scripts/JiveMarketDumper/logic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import build_catalog
from bots.jive_market_dumper import COINS, PACK, TRADE_SLOTS, accept_action, decide, dumpables, held_with_offer, plan_pile


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


IRON = 440
IRON_NOTE = 441
YEW = 1515
YEW_NOTE = 1516
SCIM = 1333
ARROW = 892
CAPE = 1019
CAT = build_catalog([
    rec(IRON, 'Iron ore'),
    rec(IRON_NOTE, 'Iron ore', Record({'certlink': IRON, 'certtemplate': 799, 'stackable': True})),
    rec(YEW, 'Yew logs'),
    rec(YEW_NOTE, 'Yew logs', Record({'certlink': YEW, 'certtemplate': 799, 'stackable': True})),
    rec(COINS, 'Coins', Record({'stackable': True})),
    rec(SCIM, 'Rune scimitar'),
    rec(ARROW, 'Rune arrow', Record({'stackable': True})),
    rec(CAPE, 'Cape'),
])


def _fn2():
    def _fn3():
        list_ = dumpables([Record({'id': YEW, 'count': 500}), Record({'id': IRON, 'count': 1000}), Record({'id': SCIM, 'count': 2})], CAT)
        expect([[d.display_name, d.count] for d in list_]).to_equal([['Iron ore', 1000], ['Rune scimitar', 2], ['Yew logs', 500]])
    test('takes every tradeable item, whatever the maker pays for it', _fn3)

    def _fn4():
        expect([d.display_name for d in dumpables([Record({'id': COINS, 'count': 50000}), Record({'id': YEW, 'count': 1})], CAT)]).to_equal(['Yew logs'])
    test('leaves coins and anything the engine will not trade', _fn4)

    def _fn5():
        list_ = dumpables([Record({'id': IRON_NOTE, 'count': 50}), Record({'id': IRON, 'count': 2})], CAT)
        expect(list_).to_equal([Record({
        'id': IRON,
        'name': 'Iron ore',
        'display_name': 'Iron ore',
        'noted_id': IRON_NOTE,
        'stackable': False,
        'count': 52,
    })])
    test('folds a noted bank row onto its item and says what a note-mode withdrawal lands as', _fn5)

    def _fn6():
        expect((dumpables([Record({'id': SCIM, 'count': 3})], CAT) or [None])[0]).to_match_object(Record({'id': SCIM, 'noted_id': None, 'stackable': False, 'count': 3}))
    test('an item with no noted form still goes, one slot a unit', _fn6)

    def _fn7():
        expect((dumpables([Record({'id': ARROW, 'count': 5000})], CAT) or [None])[0]).to_match_object(Record({'id': ARROW, 'stackable': True, 'count': 5000}))
    test('reports what stacks, so the pile can give a stack one slot rather than one a unit', _fn7)


describe('dumpables', _fn2)


def _fn8():
    yews = Record({
        'id': YEW,
        'name': 'Yew logs',
        'display_name': 'Yew logs',
        'noted_id': YEW_NOTE,
        'stackable': False,
        'count': 500,
    })
    iron = Record({
        'id': IRON,
        'name': 'Iron ore',
        'display_name': 'Iron ore',
        'noted_id': IRON_NOTE,
        'stackable': False,
        'count': 1000,
    })
    scims = Record({
        'id': SCIM,
        'name': 'Rune scimitar',
        'display_name': 'Rune scimitar',
        'noted_id': None,
        'stackable': False,
        'count': 40,
    })
    # Why: a stackable has no noted form because it already stacks, so a slot a unit would cap a 5,000 stack at twenty and leave the rest banked forever.
    arrows = Record({
        'id': ARROW,
        'name': 'Rune arrow',
        'display_name': 'Rune arrow',
        'noted_id': None,
        'stackable': True,
        'count': 5000,
    })

    def _fn9():
        expect(plan_pile([yews, iron])).to_equal([yews, iron])
    test('a noted stack is one slot however deep, so a whole bank of them rides in one trip', _fn9)

    def _fn10():
        _merged11 = {}
        for _k, _v in (scims._fields if isinstance(scims, Record) else scims).items():
            _merged11[_k] = _v
        for _k, _v in {'count': 6}.items():
            _merged11[_k] = _v
        expect(plan_pile([scims], 6)).to_equal([Record(_merged11)])
        _merged12 = {}
        for _k, _v in (scims._fields if isinstance(scims, Record) else scims).items():
            _merged12[_k] = _v
        for _k, _v in {'count': 3}.items():
            _merged12[_k] = _v
        expect(plan_pile([yews, scims], 4)).to_equal([yews, Record(_merged12)])
    test('an unnotable item takes a slot a unit and is cut to what fits', _fn10)

    # Why: the maker has to have room for every slot it is handed, and it keeps only a few free beside its coin float, so a trip stops well short of a full pack.
    def _fn13():
        many = [Record({'id': 3000 + i, 'name': f'Thing {i}', 'display_name': f'Thing {i}', 'noted_id': 4000 + i, 'stackable': False, 'count': 1}) for i in range(40)]
        expect(TRADE_SLOTS).to_be(20)
        expect(TRADE_SLOTS).to_be_less_than(PACK)
        expect(plan_pile(many)).to_have_length(TRADE_SLOTS)
        _merged14 = {}
        for _k, _v in (scims._fields if isinstance(scims, Record) else scims).items():
            _merged14[_k] = _v
        for _k, _v in {'count': TRADE_SLOTS}.items():
            _merged14[_k] = _v
        expect(plan_pile([scims])).to_equal([Record(_merged14)])
    test('stops at twenty slots by default, short of the pack', _fn13)

    def _fn15():
        expect(plan_pile([arrows])).to_equal([arrows])
        expect(plan_pile([arrows], 1)).to_equal([arrows])
    test('a stackable rides whole in one slot, however deep the stack', _fn15)

    def _fn16():
        many = [Record({'id': 9000 + i, 'name': f'Rune {i}', 'display_name': f'Rune {i}', 'noted_id': None, 'stackable': True, 'count': 5000}) for i in range(20)]
        expect(plan_pile(many)).to_have_length(20)
        expect(all([l.count == 5000 for l in plan_pile(many)])).to_be(True)
    test('twenty stackable kinds all fit, where twenty unnotable units would fill the trip alone', _fn16)

    def _fn20():
        expect(plan_pile([yews], 0)).to_equal([])
    test('takes nothing with no room', _fn20)


describe('planPile', _fn8)


def _fn21():
    def _fn22():
        expect(decide(Record({'trade_active': True, 'pile': 0}))).to_equal(Record({'kind': 'trade'}))
        expect(decide(Record({'trade_active': False, 'pile': 3}))).to_equal(Record({'kind': 'approach'}))
        expect(decide(Record({'trade_active': False, 'pile': 0}))).to_equal(Record({'kind': 'bank'}))
    test('owns an open window first, then goes to the maker with a pile, then banks', _fn22)


describe('decide', _fn21)


# Why: the offer screen shuts a tick before the confirm opens, so one dead frame is the handover and the window is only gone once it stays dead.
def _fn23():
    def _fn24():
        expect(accept_action(Record({'on_offer': True, 'on_confirm': False, 'dead_ticks': 0}))).to_be('accept')
        expect(accept_action(Record({'on_offer': False, 'on_confirm': True, 'dead_ticks': 0}))).to_be('accept')
    test('accepts whichever screen is up', _fn24)

    def _fn25():
        expect(accept_action(Record({'on_offer': False, 'on_confirm': False, 'dead_ticks': 1}))).to_be('wait')
        expect(accept_action(Record({'on_offer': False, 'on_confirm': False, 'dead_ticks': 3}))).to_be('wait')
    test('waits out the dead frames between the two screens rather than calling the trade over', _fn25)

    def _fn26():
        expect(accept_action(Record({'on_offer': False, 'on_confirm': False, 'dead_ticks': 4}))).to_be('done')
        expect(accept_action(Record({'on_offer': False, 'on_confirm': False, 'dead_ticks': 9}), 8)).to_be('done')
    test('past the grace the window really is gone', _fn26)


describe('acceptAction', _fn23)


# Why: the pack view hides what is staked, so a pile read from the pack alone reads as empty mid-window and the trade gets declined for nothing.
def _fn27():
    def _fn28():
        expect(held_with_offer([Record({'id': IRON_NOTE, 'count': 5})], [Record({'id': IRON_NOTE, 'count': 300})])).to_equal([Record({'id': IRON_NOTE, 'count': 305})])
    test('adds what is already staked to what the pack still holds', _fn28)

    def _fn29():
        expect(held_with_offer([], [Record({'id': YEW_NOTE, 'count': 347}), Record({'id': IRON_NOTE, 'count': 3})])).to_equal([Record({'id': YEW_NOTE, 'count': 347}), Record({'id': IRON_NOTE, 'count': 3})])
    test('counts a staked line the pack no longer shows at all', _fn29)

    def _fn30():
        expect(held_with_offer([], [Record({'id': SCIM, 'count': 1}), Record({'id': SCIM, 'count': 1})])).to_equal([Record({'id': SCIM, 'count': 2})])
    test('a non-stackable stakes as count-1 slots, which sum', _fn30)

    def _fn31():
        expect(held_with_offer([Record({'id': IRON, 'count': 2})], [])).to_equal([Record({'id': IRON, 'count': 2})])
    test('an empty window is just the pack', _fn31)


describe('heldWithOffer', _fn27)


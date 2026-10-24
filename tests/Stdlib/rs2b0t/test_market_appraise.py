"""rs2b0t's test/api/market/appraise.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import appraise, build_catalog, describe_appraisal


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
COINS = 995
MIND = 558
AIR = 556
SCIM = 1333
JUNK = 1127
CAT = build_catalog([
    rec(IRON, 'Iron ore'),
    rec(IRON_NOTE, 'Iron ore', Record({'certlink': IRON, 'certtemplate': 799, 'stackable': True})),
    rec(COINS, 'Coins', Record({'stackable': True})),
    rec(MIND, 'Mind rune', Record({'stackable': True})),
    rec(AIR, 'Air rune', Record({'stackable': True})),
    rec(SCIM, 'Rune scimitar'),
    rec(JUNK, 'Rune platebody'),
])
BOOK = Record({
    'name': 'demo',
    'margin': 20,
    'max_trade_value': 100000,
    'rows': [
    Record({'id': IRON, 'mid': 20, 'cap': 1000, 'buying': True, 'selling': True}),
    Record({'id': MIND, 'mid': 4, 'cap': 100000, 'buying': True, 'selling': True}),
    Record({'id': AIR, 'mid': 3, 'cap': 100000, 'buying': True, 'selling': True}),
    Record({'id': SCIM, 'mid': 15000, 'cap': 20, 'buying': True, 'selling': True}),
],
})


class Desk:
    def __init__(self, have, held, purse):
        self.have = have
        self.held_counts = held
        self.purse = purse

    def available(self, id):
        return self.have.get(id, 0)

    def held(self, id):
        return self.held_counts.get(id, 0)


def make_desk(have=None, held=None, purse=1000000):
    return Desk(have if have is not None else {}, held if held is not None else {}, purse)


def look(their_offer, desk=None, intent=None, book=None):
    return appraise(book if book is not None else BOOK, CAT, desk if desk is not None else make_desk(), COINS, their_offer, intent)


def pairs(counts):
    """A Map spread as rs2b0t's tests read it: [[id, count], ...]."""
    return [[id, counts[id]] for id in counts]


def with_book(field, value):
    fields = {}
    for k in BOOK.keys():
        fields[k] = BOOK.get(k)
    fields[field] = value
    return Record(fields)


def with_row(id, field, value):
    rows = []
    for r in BOOK.rows:
        if r.id == id:
            fields = {}
            for k in r.keys():
                fields[k] = r.get(k)
            fields[field] = value
            rows.append(Record(fields))
        else:
            rows.append(r)
    return with_book('rows', rows)


def item(id, name, count):
    return Record({'id': id, 'name': name, 'count': count})


def _fn2():
    def _fn3():
        a = look([item(IRON, 'Iron ore', 100)])
        expect(a.kind).to_be('buy')
        expect(pairs(a.owe)).to_equal([[COINS, 1800]])
        expect(pairs(a.want)).to_equal([[IRON, 100]])
        expect(a.total).to_be(1800)
    test('a single stack', _fn3)

    # Why: the customer's example, and the reason the window has to be priced rather than quoted.
    def _fn4():
        a = look([item(MIND, 'Mind rune', 500), item(AIR, 'Air rune', 300), item(SCIM, 'Rune scimitar', 1)])
        expect(a.total).to_be(500 * 3 + 300 * 2 + 13500)
        expect(pairs(a.owe)).to_equal([[COINS, a.total]])
        expect(a.lines).to_have_length(3)
    test('a mixed pile is one bill', _fn4)

    def _fn5():
        a = look([item(IRON, 'Iron ore', 40), item(IRON_NOTE, 'Iron ore', 60)])
        expect(a.lines).to_have_length(1)
        expect(a.lines[0].count).to_be(100)
    test('noted and unnoted of one row merge', _fn5)

    def _fn6():
        side = [item(MIND, 'Mind rune', 500), item(SCIM, 'Rune scimitar', 1)]
        expect(look(side)).to_equal(look(side))
    test('running the same beat twice changes nothing', _fn6)

    def _fn7():
        a = look([])
        expect(a.kind).to_be('nothing')
        expect(len(a.owe)).to_be(0)
    test('an empty side owes nothing', _fn7)


describe('buying: the bot prices what is in front of it', _fn2)


def _fn8():
    # Why: both sides hand over their window at confirm, so ignoring coins costs the customer them.
    def _fn9():
        a = look([item(IRON, 'Iron ore', 100), item(COINS, 'Coins', 500)])
        expect(a.total).to_be(1800)
        expect(a.ignored).to_contain_equal(Record({'name': 'coins', 'count': 500}))
    test('coins are excluded from the bill and called out', _fn9)

    def _fn10():
        a = look([item(IRON, 'Iron ore', 100), item(COINS, 'Coins', 500)])
        expect(describe_appraisal(a)).to_be('Iron ore x100 = 1,800. 500 coins: not counted, keep them. Total 1,800gp.')
    test('the description tells the customer to take them back', _fn10)

    def _fn11():
        expect(look([item(COINS, 'Coins', 5000)]).kind).to_be('nothing')
    test('coins alone with no intent buy nothing', _fn11)


describe('buying: coins are ignored and named', _fn8)


def _fn12():
    def _fn13():
        a = look([item(IRON, 'Iron ore', 10), item(JUNK, 'Rune platebody', 1)])
        expect(a.total).to_be(180)
        expect(a.ignored).to_contain_equal(Record({'name': 'Rune platebody', 'count': 1}))
    test('an unpriced item is ignored and named', _fn13)

    def _fn14():
        a = look([item(IRON, 'Iron ore', 100)], desk=make_desk(held={IRON: 950}))
        expect(a.lines[0].count).to_be(50)
        expect(a.ignored).to_contain_equal(Record({'name': 'Iron ore', 'count': 50}))
    test('units past the cap are ignored', _fn14)

    def _fn15():
        a = look([item(IRON, 'Iron ore', 100)], desk=make_desk(held={IRON: 1000}))
        expect(a.kind).to_be('nothing')
    test('a full cap takes nothing of that row', _fn15)

    def _fn16():
        off = with_row(IRON, 'buying', False)
        expect(look([item(IRON, 'Iron ore', 10)], book=off).kind).to_be('nothing')
    test('a row switched off for buying is ignored', _fn16)


describe('buying: what it will not take', _fn12)


def _fn22():
    pile = [item(SCIM, 'Rune scimitar', 1), item(IRON, 'Iron ore', 100)]
    tight = with_book('max_trade_value', 5000)

    # Why: the window cannot say which units of a stack it is paying for, so the shop bids its ceiling for the pile as it stands.
    def _fn24():
        a = look(pile, desk=make_desk(purse=5000))
        expect(a.kind).to_be('buy')
        expect(a.total).to_be(5000)
        expect(pairs(a.owe)).to_equal([[COINS, 5000]])
        expect(pairs(a.want)).to_equal([[SCIM, 1], [IRON, 100]])
        expect(a.ignored).to_equal([])
        expect(a.note).to_be('max I can offer is 5,000gp per trade')
    test('a thin purse bids the purse for the pile', _fn24)

    def _fn25():
        a = look(pile, book=tight)
        expect(a.total).to_be(5000)
        expect(pairs(a.owe)).to_equal([[COINS, 5000]])
        expect(a.note).to_be('max I can offer is 5,000gp per trade')
    test('the per-trade cap bids the cap the same way', _fn25)

    def _fn26():
        a = look(pile, book=tight)
        expect([l.value for l in a.lines]).to_equal([13500, 1800])
    test('the lines still say what the pile is worth', _fn26)

    def _fn27():
        a = look(pile, book=tight, desk=make_desk(purse=2000))
        expect(a.total).to_be(2000)
        expect(a.note).to_be('max I can offer is 2,000gp per trade')
    test('the tighter of purse and cap is the ceiling', _fn27)

    def _fn28():
        a = look(pile)
        expect(a.total).to_be(15300)
        expect(a.note).to_be_null()
    test('under the ceiling the deal is the full value', _fn28)

    def _fn29():
        expect(look([item(IRON, 'Iron ore', 100)], desk=make_desk(purse=0)).kind).to_be('nothing')
    test('an empty purse buys nothing at all', _fn29)


describe('buying: it never offers more than it has', _fn22)


def _fn30():
    intent = Record({'item_id': IRON, 'max_qty': 100})
    stocked = make_desk(have={IRON: 5000})

    # Why: the deal is fixed by what they asked for. Nothing in the window changes the price or the quantity.
    def _fn31():
        a = look([item(COINS, 'Coins', 2200)], intent=intent, desk=stocked)
        expect(a.kind).to_be('sell')
        expect(pairs(a.owe)).to_equal([[IRON, 100]])
        expect(pairs(a.want)).to_equal([[COINS, 2200]])
        expect(a.total).to_be(2200)
    test('the quantity comes from the request, not from their coins', _fn31)

    def _fn32():
        a = look([item(COINS, 'Coins', 1100)], intent=intent, desk=stocked)
        expect(pairs(a.owe)).to_equal([[IRON, 100]])
        expect(pairs(a.want)).to_equal([[COINS, 2200]])
    test('short money is not a smaller deal, it is the same deal unpaid', _fn32)

    def _fn33():
        a = look([], intent=intent, desk=stocked)
        expect(pairs(a.owe)).to_equal([[IRON, 100]])
        expect(pairs(a.want)).to_equal([[COINS, 2200]])
    test('no coins yet is still the same deal', _fn33)

    def _fn34():
        a = look([item(COINS, 'Coins', 2210)], intent=intent, desk=stocked)
        expect(pairs(a.want)).to_equal([[COINS, 2200]])
        expect(a.ignored).to_contain_equal(Record({'name': 'coins', 'count': 10}))
    test('the remainder above the price is named, not pocketed quietly', _fn34)

    def _fn35():
        a = look([item(COINS, 'Coins', 2200)], intent=intent, desk=make_desk(have={IRON: 30}))
        expect(pairs(a.owe)).to_equal([[IRON, 30]])
        expect(pairs(a.want)).to_equal([[COINS, 660]])
    test('it never hands over more than it holds', _fn35)

    def _fn36():
        a = look([item(COINS, 'Coins', 2200)], intent=intent, desk=make_desk())
        expect(a.kind).to_be('nothing')
        expect(a.note).to_contain('out of')
    test('out of stock is nothing at all', _fn36)

    def _fn37():
        a = look([item(COINS, 'Coins', 2200), item(JUNK, 'Rune platebody', 1)], intent=intent, desk=stocked)
        expect(pairs(a.owe)).to_equal([[IRON, 100]])
        expect(a.ignored).to_contain_equal(Record({'name': 'Rune platebody', 'count': 1}))
    test('goods on their side during a sale are ignored and named', _fn37)

    def _fn38():
        off = with_row(IRON, 'selling', False)
        a = look([item(COINS, 'Coins', 2200)], intent=intent, desk=stocked, book=off)
        expect(a.kind).to_be('nothing')
        expect(a.note).to_contain("don't sell")
    test('a row switched off for selling mid-window stops the sale', _fn38)


describe('selling: the customer named x, it costs y, they owe x * y', _fn30)


def _fn44():
    def _fn45():
        expect(describe_appraisal(look([item(IRON, 'Iron ore', 100)]))).to_be('Iron ore x100 = 1,800. Total 1,800gp.')
    test('a plain purchase', _fn45)

    def _fn46():
        a = look([item(SCIM, 'Rune scimitar', 1)], book=with_book('max_trade_value', 5000))
        expect(describe_appraisal(a)).to_be('max I can offer is 5,000gp per trade. Rune scimitar x1 = 13,500. Total 5,000gp.')
    test('a capped purchase says the cap, the value and what it pays', _fn46)

    # Why: two priced lines already run past the chat limit, so a note at the end is a note nobody reads.
    def _fn48():
        a = look([item(SCIM, 'Rune scimitar', 1), item(IRON, 'Iron ore', 100)], book=with_book('max_trade_value', 5000))
        line = describe_appraisal(a)
        expect(line).to_start_with('max I can offer is 5,000gp per trade. ')
        expect(len(line)).to_be(80)
    test('the note leads, so the cap survives the chat limit', _fn48)

    def _fn50():
        a = look([item(COINS, 'Coins', 660)], intent=Record({'item_id': IRON, 'max_qty': 100}), desk=make_desk(have={IRON: 30}))
        expect(describe_appraisal(a)).to_be('that is all the Iron ore I have. Iron ore x30 = 660. You owe 660gp.')
    test('a short sale leads with why it is short', _fn50)

    # Why: an empty window is when a customer is most likely to be lost, so it teaches rather than shrugs.
    def _fn51():
        expect(describe_appraisal(look([]))).to_be('Put items in and I price them as you go. To buy, say what you want first.')
    test('an empty window explains how to use the shop', _fn51)

    def _fn52():
        a = look([
        item(MIND, 'Mind rune', 500),
        item(AIR, 'Air rune', 300),
        item(SCIM, 'Rune scimitar', 1),
        item(JUNK, 'Rune platebody', 1),
        item(COINS, 'Coins', 900),
    ])
        expect(len(describe_appraisal(a))).to_be_less_than_or_equal(80)
    test('every line fits the chat limit', _fn52)


describe('describeAppraisal', _fn44)


def _fn53():
    # Why: the shop has already staked what it is selling, so the goods are named and left alone rather than
    # Why: turning the window into a purchase that ignores the coins.
    def _fn54():
        a = look([
        Record({'id': JUNK, 'name': 'Rune platebody', 'count': 1}),
        Record({'id': COINS, 'name': 'Coins', 'count': 500}),
    ], desk=make_desk(have={IRON: 100}), intent=Record({'item_id': IRON, 'max_qty': 100}))
        expect(a.kind).to_be('sell')
        expect(a.owe.get(IRON)).to_be(100)
        expect(a.want.get(COINS)).to_be(2200)
        expect(any([i.name == 'Rune platebody' for i in a.ignored])).to_be(True)
    test('stays a sale, names the goods it will not count, and still wants the coins', _fn54)

    def _fn55():
        line = describe_appraisal(look([], desk=make_desk(have={IRON: 100}), intent=Record({'item_id': IRON, 'max_qty': 100})))
        expect(line).to_contain('You owe')
    test('the line names what they owe, so the ask for coins is in it', _fn55)

    def _fn56():
        line = describe_appraisal(look([Record({'id': IRON, 'name': 'Iron ore', 'count': 100})]))
        expect(line).to_contain('Total')
        expect(line).not_.to_contain('You owe')
    test('a purchase still reads as a total, since the shop is the one paying', _fn56)


describe('a sale when the customer puts goods up instead of coins', _fn53)


"""rs2b0t's test/api/market/chatProtocol.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import CHAT_LIMIT, format_ambiguous, format_gp, format_price_list, parse_command, parse_count, truncate_chat


def _fn1():
    def _fn2():
        expect(parse_count('100')).to_be(100)
        expect(parse_count('1')).to_be(1)
    test('plain integers', _fn2)

    def _fn3():
        expect(parse_count('1k')).to_be(1000)
        expect(parse_count('2K')).to_be(2000)
        expect(parse_count('1m')).to_be(1000000)
    test('k and m suffixes', _fn3)

    def _fn4():
        expect(parse_count('all')).to_be('all')
        expect(parse_count('ALL')).to_be('all')
    test('all', _fn4)

    def _fn5():
        expect(parse_count('0')).to_be_null()
        expect(parse_count('-5')).to_be_null()
        expect(parse_count('me')).to_be_null()
        expect(parse_count('')).to_be_null()
        expect(parse_count('1.5')).to_be_null()
    test('rejects zero, negatives and words', _fn5)


describe('parseCount', _fn1)


def _fn6():
    def _fn7():
        expect(parse_command('buy 100 iron ore')).to_equal(Record({'kind': 'quoteSell', 'qty': 100, 'query': 'iron ore', 'qty_implied': False}))
    test('buy is the player buying, so the bot sells', _fn7)

    def _fn8():
        expect(parse_command('sell 100 iron ore')).to_equal(Record({'kind': 'quoteBuy', 'qty': 100, 'query': 'iron ore', 'qty_implied': False}))
    test('sell is the player selling, so the bot buys', _fn8)

    def _fn9():
        expect(parse_command('  BUY 1k Iron Ore ')).to_equal(Record({'kind': 'quoteSell', 'qty': 1000, 'query': 'Iron Ore', 'qty_implied': False}))
    test('case and surrounding whitespace do not matter', _fn9)

    def _fn10():
        expect(parse_command('prices')).to_equal(Record({'kind': 'prices'}))
        expect(parse_command('buying')).to_equal(Record({'kind': 'buying'}))
        expect(parse_command('selling')).to_equal(Record({'kind': 'selling'}))
    test('bare list commands', _fn10)

    def _fn11():
        for word in ['list', 'book', 'rates', 'stock', 'prices']:
            expect(parse_command(word)).to_equal(Record({'kind': 'prices'}))
    test('several words ask for the book', _fn11)

    # Why: the engine broadcasts "prices" as "****es" after chat filtering.
    def _fn12():
        expect(parse_command('****es')).to_equal(Record({'kind': 'prices'}))
    test('the censored form of prices still asks for the book', _fn12)

    def _fn13():
        expect(parse_command('****')).to_equal(Record({'kind': 'none'}))
        expect(parse_command('***')).to_equal(Record({'kind': 'none'}))
    test('stars alone are not a command', _fn13)

    # Why: omitted counts default to one before catalog resolution.
    def _fn14():
        expect(parse_command('buying rune scimitar')).to_equal(Record({'kind': 'quoteSell', 'qty': 1, 'query': 'rune scimitar', 'qty_implied': True}))
        expect(parse_command('buy rune scimitar')).to_equal(Record({'kind': 'quoteSell', 'qty': 1, 'query': 'rune scimitar', 'qty_implied': True}))
        expect(parse_command('selling rune scimitar')).to_equal(Record({'kind': 'quoteBuy', 'qty': 1, 'query': 'rune scimitar', 'qty_implied': True}))
    test('a missing count means one of them', _fn14)

    def _fn15():
        expect(parse_command('buying 1 rune scimitar')).to_equal(Record({'kind': 'quoteSell', 'qty': 1, 'query': 'rune scimitar', 'qty_implied': False}))
    test('a stated count of one is the same request, minus the guess', _fn15)

    def _fn16():
        expect(parse_command('buy me a beer')).to_equal(Record({'kind': 'quoteSell', 'qty': 1, 'query': 'me a beer', 'qty_implied': True}))
    test('ordinary chat opening with a keyword still parses, and is flagged as a guess', _fn16)

    def _fn17():
        expect(parse_command('buy 0 iron ore')).to_equal(Record({'kind': 'quoteSell', 'qty': 1, 'query': '0 iron ore', 'qty_implied': True}))
    test('a count of zero is not a count, so the words carry the request', _fn17)

    def _fn18():
        expect(parse_command('buy 100')).to_equal(Record({'kind': 'none'}))
    test('a keyword with a count but no item is not a command', _fn18)

    def _fn19():
        expect(parse_command('i want to buy 100 iron ore')).to_equal(Record({'kind': 'none'}))
    test('a keyword that is not leading is not a command', _fn19)

    def _fn20():
        expect(parse_command('')).to_equal(Record({'kind': 'none'}))
        expect(parse_command('!!!')).to_equal(Record({'kind': 'none'}))
    test('empty and punctuation-only lines are not commands', _fn20)

    def _fn21():
        expect(parse_command('prices are too high')).to_equal(Record({'kind': 'none'}))
    test('a list keyword with trailing words is not a command', _fn21)

    def _fn22():
        expect(parse_command('sell all iron ore')).to_equal(Record({'kind': 'quoteBuy', 'qty': 'all', 'query': 'iron ore', 'qty_implied': False}))
    test('all is carried through as a count', _fn22)

    # Why: this is how a person says it out loud, and a shop that only takes "buy" reads as broken.
    def _fn23():
        expect(parse_command('buying 1k maple longbows')).to_equal(Record({'kind': 'quoteSell', 'qty': 1000, 'query': 'maple longbows', 'qty_implied': False}))
        expect(parse_command('selling 500 iron ore')).to_equal(Record({'kind': 'quoteBuy', 'qty': 500, 'query': 'iron ore', 'qty_implied': False}))
    test('buying N x is the same as buy N x', _fn23)

    def _fn24():
        expect(parse_command('buying')).to_equal(Record({'kind': 'buying'}))
        expect(parse_command('selling')).to_equal(Record({'kind': 'selling'}))
    test('a bare buying or selling is still the price list', _fn24)

    # Why: players reach for a slash out of habit.
    def _fn25():
        expect(parse_command('/prices')).to_equal(Record({'kind': 'prices'}))
        expect(parse_command('/help')).to_equal(Record({'kind': 'help'}))
        expect(parse_command('/buy 100 iron ore')).to_equal(Record({'kind': 'quoteSell', 'qty': 100, 'query': 'iron ore', 'qty_implied': False}))
    test('a leading slash is accepted on any command', _fn25)

    def _fn26():
        for word in ['help', 'commands', 'shop']:
            expect(parse_command(word)).to_equal(Record({'kind': 'help'}))
    test('help has a few spellings and they all land', _fn26)

    # Why: keep the escape command short enough to use when the shop stops responding.
    def _fn27():
        expect(parse_command('reset')).to_equal(Record({'kind': 'reset'}))
        expect(parse_command('RESET')).to_equal(Record({'kind': 'reset'}))
        expect(parse_command('/reset')).to_equal(Record({'kind': 'reset'}))
        expect(parse_command('unstick')).to_equal(Record({'kind': 'reset'}))
    test('reset is a command, by either name', _fn27)

    def _fn28():
        expect(parse_command('reset please')).to_equal(Record({'kind': 'none'}))
        expect(parse_command('Resetting. Trade me again in a moment.')).to_equal(Record({'kind': 'none'}))
    test('reset with anything after it is ordinary chat', _fn28)

    def _fn29():
        expect(parse_command('/')).to_equal(Record({'kind': 'none'}))
    test('a slash on its own is not a command', _fn29)


describe('parseCommand', _fn6)


def _fn30():
    def _fn31():
        expect(format_gp(2000)).to_be('2,000')
        expect(format_gp(17)).to_be('17')
    test('formatGp groups thousands', _fn31)

    def _fn32():
        expect(format_ambiguous([
        Record({'name': 'Maple longbow', 'id': 851, 'base': 'Maple longbow', 'word': None}),
        Record({'name': 'Yew longbow', 'id': 855, 'base': 'Yew longbow', 'word': None}),
    ])).to_be("2 matches: 'Maple longbow', 'Yew longbow'. Which?")
    test('ambiguous reply lists the names it can fit', _fn32)

    def _fn33():
        many = [Record({'name': f'Rune platebody {i}', 'id': i, 'base': f'Rune platebody {i}', 'word': None}) for i in range(12)]
        line = format_ambiguous(many)
        expect(len(line)).to_be_less_than_or_equal(CHAT_LIMIT)
        expect(line).to_contain('12 matches')
        expect(line).to_contain('more')
    test('a reply too long for the chat limit says how many it left out', _fn33)

    # Why: four objs are literally "Dragonhide", so listing that name four times tells the player nothing.
    def _fn34():
        expect(format_ambiguous([
        Record({'name': 'Green dragonhide', 'id': 1753, 'base': 'Dragonhide', 'word': 'green'}),
        Record({'name': 'Blue dragonhide', 'id': 1751, 'base': 'Dragonhide', 'word': 'blue'}),
        Record({'name': 'Red dragonhide', 'id': 1749, 'base': 'Dragonhide', 'word': 'red'}),
        Record({'name': 'Black dragonhide', 'id': 1747, 'base': 'Dragonhide', 'word': 'black'}),
    ])).to_be("4 matches: green, blue, red, black 'Dragonhide'. Which?")
    test('one repeated name is answered with the words that separate it', _fn34)

    def _fn35():
        expect(format_ambiguous([
        Record({'name': 'Tooth half of key', 'id': 985, 'base': 'Half of a key', 'word': 'tooth'}),
        Record({'name': 'Loop half of key', 'id': 987, 'base': 'Half of a key', 'word': 'loop'}),
    ])).to_be("2 matches: tooth, loop 'Half of a key'. Which?")
    test('the key halves name their halves', _fn35)

    # Why: nothing separates a pair the content never named apart, so the id is the only answer left.
    def _fn36():
        expect(format_ambiguous([
        Record({'name': 'Half of a key', 'id': 985, 'base': 'Half of a key', 'word': None}),
        Record({'name': 'Half of a key', 'id': 987, 'base': 'Half of a key', 'word': None}),
    ])).to_be("2 matches: 'Half of a key' #985, 'Half of a key' #987. Which?")
    test('names that read the same with no word are tagged with their id', _fn36)

    def _fn37():
        entries = [Record({'name': f'Item number {i}', 'buy': 10, 'sell': 20}) for i in range(12)]
        lines = format_price_list(entries, 'both')
        expect(len(lines)).to_be_greater_than(1)
        for line in lines:
            expect(len(line)).to_be_less_than_or_equal(CHAT_LIMIT)
    test('price list chunks into lines under the chat limit', _fn37)

    def _fn38():
        expect(format_price_list([Record({'name': 'Iron ore', 'buy': 14, 'sell': 20})], 'buy')).to_equal(['Iron ore 14'])
        expect(format_price_list([Record({'name': 'Iron ore', 'buy': 14, 'sell': 20})], 'sell')).to_equal(['Iron ore 20'])
    test('price list shows one side when asked', _fn38)

    def _fn39():
        expect(format_price_list([], 'both')).to_equal([])
    test('an empty price list produces no lines', _fn39)

    def _fn40():
        expect(truncate_chat(('x' * 200))).to_have_length(CHAT_LIMIT)
        expect(truncate_chat('short')).to_be('short')
    test('truncateChat cuts to the game limit', _fn40)


describe('formatting', _fn30)


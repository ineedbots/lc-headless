"""rs2b0t's test/api/market/chatEcho.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Its half that packs each line with the webclient's WordPack and back is left out: the Python side has no
WordPack."""

from rs2004.catalogs import Record
from rs2004.market import HELP_LINES, appraise, build_catalog, describe_appraisal, format_ambiguous, format_gp, format_price_list, parse_command


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


CAT = build_catalog([rec(440, 'Iron ore'), rec(995, 'Coins', Record({'stackable': True})), rec(1127, 'Rune platebody')])
BOOK = Record({
    'name': 'seers',
    'margin': 20,
    'max_trade_value': 100000,
    'rows': [Record({'id': 440, 'mid': 20, 'cap': 1000, 'buying': True, 'selling': True})],
})
class Desk:
    purse = 100000

    def available(self, id):
        return 500

    def held(self, id):
        return 0


DESK = Desk()


def priced(their_offer, intent=None):
    return describe_appraisal(appraise(BOOK, CAT, DESK, 995, their_offer, intent))


EVERY_REPLY = ['Nothing listed right now.'] + list(format_price_list([Record({'name': 'Iron ore', 'buy': 18, 'sell': 22}), Record({'name': 'Yew logs', 'buy': 288, 'sell': 352})], 'both')) + list(format_price_list([Record({'name': 'Iron ore', 'buy': 18, 'sell': 22})], 'buy')) + list(format_price_list([Record({'name': 'Iron ore', 'buy': 18, 'sell': 22})], 'sell')) + ["I don't sell 'dragon claws'.", format_ambiguous([
    Record({'name': 'Maple longbow', 'id': 851, 'base': 'Maple longbow', 'word': None}),
    Record({'name': 'Maple longbow (u)', 'id': 62, 'base': 'Maple longbow', 'word': 'u'}),
]), format_ambiguous([
    Record({'name': 'Green dragonhide', 'id': 1753, 'base': 'Dragonhide', 'word': 'green'}),
    Record({'name': 'Blue dragonhide', 'id': 1751, 'base': 'Dragonhide', 'word': 'blue'}),
]), 'I am out of stock right now.', '100 x Iron ore = 2,200gp (22ea). Trade me.', 'Just trade me and put it up. I price what I see.', '100 x Iron ore = 2,200gp (22ea). Give me a moment.', 'Got your Iron ore Elliott. Trade me.', 'Resetting. Trade me again in a moment.', 'Already reset. Ask again in 10m.', 'Elliott, I could only get 60 x Iron ore. Trade me.', 'Elliott, I could not get your Iron ore. Ask me again.', 'I have no Iron ore right now.'] + list(HELP_LINES) + ['Put items in and I price them as you go. To buy, say what you want first.', '100 x Iron ore = 2,200gp. Put that up.', 'Fetching your Iron ore, one moment.', priced([Record({'id': 440, 'name': 'Iron ore', 'count': 100})]), priced([Record({'id': 440, 'name': 'Iron ore', 'count': 100}), Record({'id': 995, 'name': 'Coins', 'count': 500})]), priced([Record({'id': 1127, 'name': 'Rune platebody', 'count': 1})]), priced([]), priced([Record({'id': 995, 'name': 'Coins', 'count': 2200})], Record({'item_id': 440, 'max_qty': 100})), priced([Record({'id': 995, 'name': 'Coins', 'count': 5})], Record({'item_id': 440, 'max_qty': 100})), 'Thanks Elliott. Pleasure doing business.', 'Trading: ' + format_price_list([Record({'name': 'Iron ore', 'buy': 18, 'sell': 22})], 'both')[0], 'Trade declined: too many changes in one trade. Ask again in 15s.', 'Trade declined: the confirm screen changed. Ask again in 15s.', 'Trade declined. Ask again in 15s.', 'Trade closed. Ask again in 15s.', 'That did not open. Trade me again.', 'Fetching your Iron ore, one moment.', 'Elliott, stand next to me.']


# Why: two MarketMakers at one bank hear each other. If any reply parsed as a command they would quote
# Why: each other forever, and the pair would flood the chat until both were muted.
def ignores(line):
    def run():
        expect(parse_command(line)).to_equal(Record({'kind': 'none'}))
    return run


def _fn2():
    for line in EVERY_REPLY:
        test('ignores its own line: ' + line[0:46], ignores(line))


describe('no reply the bot can emit is a command', _fn2)


def _fn4():
    def _fn5():
        expect(parse_command('Quote first, e.g. "buy 100 iron ore".')).to_equal(Record({'kind': 'none'}))
        expect(parse_command('anyone selling 100 iron ore?')).to_equal(Record({'kind': 'none'}))
        expect(parse_command('he said buy 100 iron ore')).to_equal(Record({'kind': 'none'}))
    test('a command quoted inside a sentence is not a command', _fn5)


describe('the keyword has to lead', _fn4)

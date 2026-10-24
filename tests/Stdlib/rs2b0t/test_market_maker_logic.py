"""rs2b0t's test/scripts/marketMakerLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from rs2004.market import build_catalog
from bots.marketmaker.logic import Desk, RateLimiter, advertise_due, bank_before_serving, buy_owes_settle, deal_line, deal_of
from bots.marketmaker.logic import deal_totals, decide_beat, float_shortfall, fresh_chat_lines, listed_rows, resolve_quote, settle_due
from bots.marketmaker.logic import settle_runs, should_settle, side_signature, trade_is_stalled, window_candidates

IRON = 440
COINS = 995


def intent(customer, at_ms=0, over=None):
    if over is None:
        over = Record({})
    _merged1 = {}
    for _k, _v in {'customer': customer, 'item_id': IRON, 'max_qty': 100, 'asked_at_ms': at_ms}.items():
        _merged1[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged1[_k] = _v
    return Record(_merged1)


def window_at(over=None):
    if over is None:
        over = Record({})
    _merged2 = {}
    for _k, _v in {
        'customer': 'alice',
        'opened_at_ms': 0,
        'still_beats': 3,
        're_offers': 0,
        'last_sig': '440x100',
        'saw_open': True,
        'accepted': None,
        'waited': 0,
    }.items():
        _merged2[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged2[_k] = _v
    return Record(_merged2)


desk = None


def _fn3():
    global desk
    desk = Desk(8)


before_each(_fn3)


def _fn4():
    def _fn5():
        desk.remember(intent('alice', 0))
        expect((desk.intent_for('alice', 30000, 60000).max_qty if desk.intent_for('alice', 30000, 60000) is not None else None)).to_be(100)
        expect(desk.intent_for('alice', 61000, 60000)).to_be_null()
    test('a live intent comes back until it expires', _fn5)

    def _fn6():
        desk.remember(intent('alice', 0))
        expect(desk.intent_for('Alice', 0, 60000)).not_.to_be_null()
    test('lookup is case-insensitive, since the client capitalises names', _fn6)

    def _fn7():
        desk.remember(intent('alice', 0))
        desk.remember(intent('alice', 5000, Record({'max_qty': 50})))
        expect((desk.intent_for('alice', 5000, 60000).max_qty if desk.intent_for('alice', 5000, 60000) is not None else None)).to_be(50)
        expect(desk.intent_count()).to_be(1)
    test('asking again replaces rather than stacking', _fn7)

    # Why: an unbounded map is a memory griefing vector for anyone with throwaway names.
    def _fn8():
        for i in range(10):
            desk.remember(intent(f'p{i}', i))
        expect(desk.intent_count()).to_be(8)
        expect(desk.intent_for('p0', 10, 60000)).to_be_null()
    test('the book is capped, dropping the oldest', _fn8)

    def _fn9():
        desk.remember(intent('alice', 0))
        desk.remember(intent('bob', 50000))
        desk.prune_intents(60001, 60000)
        expect(desk.intent_count()).to_be(1)
    test('pruning drops what has expired', _fn9)

    def _fn10():
        desk.remember(intent('alice', 0))
        desk.remember(intent('bob', 1000))
        expect((desk.next_intent(2000, 60000).customer if desk.next_intent(2000, 60000) is not None else None)).to_be('alice')
        desk.forget('alice')
        expect((desk.next_intent(2000, 60000).customer if desk.next_intent(2000, 60000) is not None else None)).to_be('bob')
    test('nextIntent is the oldest live one, which is whose goods get fetched', _fn10)

    def _fn11():
        desk.remember(intent('alice', 0))
        expect(desk.next_intent(90000, 60000)).to_be_null()
    test('nextIntent skips expired ones', _fn11)


describe('intents are a request, not a promise', _fn4)


def _fn12():
    def _fn13():
        expect(desk.current()).to_be_null()
    test('nothing is open until a window is', _fn13)

    def _fn14():
        w = desk.open('alice', 1000)
        expect(w.customer).to_be('alice')
        expect(w.still_beats).to_be(0)
        expect(w.re_offers).to_be(0)
        expect(desk.current()).to_be(w)
    test('opening names the customer and zeroes the counters', _fn14)

    # Why: asking for a window is not the same as getting one. A request sent as a modal closes opens
    # Why: it on their client alone, and the bot would otherwise hold a window it cannot see.
    def _fn15():
        expect(desk.open('alice', 0).saw_open).to_be(False)
    test('a fresh window has not been seen open yet', _fn15)

    def _fn16():
        desk.open('alice', 0)
        desk.close()
        expect(desk.current()).to_be_null()
    test('closing clears it', _fn16)

    # Why: the transaction sits under one deadline, so nothing can hold the counter open.
    def _fn17():
        desk.open('alice', 1000)
        expect(desk.expired(60000, 90000)).to_be(False)
        expect(desk.expired(92000, 90000)).to_be(True)
    test('a window goes stale past its deadline', _fn17)

    def _fn18():
        expect(desk.expired(999999, 1)).to_be(False)
    test('a closed desk is never expired', _fn18)


describe('one window at a time', _fn12)


def _fn19():
    def _fn20():
        desk.cool('mallory', 60000)
        expect(desk.on_cooldown('mallory', 59000)).to_be(True)
        expect(desk.on_cooldown('mallory', 60001)).to_be(False)
    test('a cooled customer is ignored until the deadline', _fn20)

    def _fn21():
        desk.cool('Mallory', 60000)
        expect(desk.on_cooldown('mallory', 0)).to_be(True)
    test('cooling is case-insensitive', _fn21)

    def _fn22():
        expect(desk.on_cooldown('alice', 999999)).to_be(False)
    test('an uncooled customer is never blocked', _fn22)


describe('cooldowns punish the staller', _fn19)


def _fn23():
    base = Record({
        'still_beats_needed': 3,
        're_offer_cap': 12,
        'wait_cap': 25,
        'owe_matched': False,
        'want_matched': True,
        'owe_anything': True,
        'owe_fixed': False,
    })

    # Why: one customer sitting on an open window blocks every customer behind them, so waiting is capped.
    def _fn24():
        _merged25 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged25[_k] = _v
        for _k, _v in {
        'their_sig': '440x100',
        'window': window_at(Record({'waited': 24})),
        'want_matched': False,
        'owe_matched': True,
    }.items():
            _merged25[_k] = _v
        patient = decide_beat(Record(_merged25))
        expect(patient.do).to_be('wait')
        _merged26 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged26[_k] = _v
        for _k, _v in {
        'their_sig': '440x100',
        'window': window_at(Record({'waited': 25})),
        'want_matched': False,
        'owe_matched': True,
    }.items():
            _merged26[_k] = _v
        done = decide_beat(Record(_merged26))
        expect(done).to_equal(Record({'do': 'give-up', 'reason': 'you left your side up too long'}))
    test('waiting is given up on once the customer has sat on it long enough', _fn24)

    def _fn27():
        _merged28 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged28[_k] = _v
        for _k, _v in {
        'their_sig': '440x100',
        'window': window_at(Record({'waited': 999})),
        'owe_matched': True,
        'want_matched': True,
    }.items():
            _merged28[_k] = _v
        beat = decide_beat(Record(_merged28))
        expect(beat).to_equal(Record({'do': 'accept'}))
    test('the cap never turns a settleable trade away', _fn27)

    def _fn29():
        _merged30 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged30[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(Record({'waited': 999})), 'owe_matched': False}.items():
            _merged30[_k] = _v
        beat = decide_beat(Record(_merged30))
        expect(beat.do).to_be('offer')
    test('the cap does not stop the shop putting its own side up', _fn29)

    # Why: any change resets both accepts, so acting on a moving side means neither ever settles.
    def _fn31():
        _merged32 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged32[_k] = _v
        for _k, _v in {'their_sig': '440x150', 'window': window_at(), 'owe_matched': True}.items():
            _merged32[_k] = _v
        beat = decide_beat(Record(_merged32))
        expect(beat).to_equal(Record({'do': 'wait', 'reason': 'their side moved'}))
    test('a side that just moved is always waited on', _fn31)

    def _fn33():
        _merged34 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged34[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(Record({'still_beats': 2}))}.items():
            _merged34[_k] = _v
        beat = decide_beat(Record(_merged34))
        expect(beat.do).to_be('wait')
    test('a still side that has not settled long enough waits', _fn33)

    def _fn35():
        _merged36 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged36[_k] = _v
        for _k, _v in {'their_sig': '', 'window': window_at(Record({'last_sig': ''})), 'owe_anything': False}.items():
            _merged36[_k] = _v
        beat = decide_beat(Record(_merged36))
        expect(beat).to_equal(Record({'do': 'wait', 'reason': 'nothing to trade yet'}))
    test('an empty window waits rather than accepting nothing', _fn35)

    def _fn37():
        _merged38 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged38[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at()}.items():
            _merged38[_k] = _v
        beat = decide_beat(Record(_merged38))
        expect(beat.do).to_be('offer')
    test('a settled side the bot has not matched gets an offer', _fn37)

    def _fn39():
        _merged40 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged40[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(), 'owe_matched': True}.items():
            _merged40[_k] = _v
        beat = decide_beat(Record(_merged40))
        expect(beat).to_equal(Record({'do': 'accept'}))
    test('a settled side the bot has matched is accepted', _fn39)

    # Why: each re-offer costs clicks and resets both accepts, so a patient toggler could waste the window.
    def _fn41():
        _merged42 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged42[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(Record({'re_offers': 12}))}.items():
            _merged42[_k] = _v
        beat = decide_beat(Record(_merged42))
        expect(beat.do).to_be('give-up')
    test('past the re-offer cap it gives up rather than keep paying', _fn41)

    def _fn43():
        _merged44 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged44[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(Record({'re_offers': 99})), 'owe_matched': True}.items():
            _merged44[_k] = _v
        beat = decide_beat(Record(_merged44))
        expect(beat).to_equal(Record({'do': 'accept'}))
    test('the cap does not fire on a window it has already matched', _fn43)

    # Why: a sale is x * y = z, so short money is not a smaller deal, it is not the deal.
    def _fn45():
        _merged46 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged46[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(), 'owe_matched': True, 'want_matched': False}.items():
            _merged46[_k] = _v
        beat = decide_beat(Record(_merged46))
        expect(beat).to_equal(Record({'do': 'wait', 'reason': 'their side is not the deal yet'}))
    test('their side not being the deal waits rather than accepting', _fn45)

    # Why: this is the steady-state claim. Nothing changing means nothing happens.
    def _fn47():
        _merged48 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged48[_k] = _v
        for _k, _v in {'their_sig': '440x100', 'window': window_at(), 'owe_matched': True}.items():
            _merged48[_k] = _v
        input = Record(_merged48)
        expect(decide_beat(input)).to_equal(decide_beat(input))
    test('a beat that repeats with no change decides the same thing twice', _fn47)


describe('decideBeat', _fn23)


def _fn49():
    def _fn50():
        expect(side_signature({_k: _v for _k, _v in [[440, 10], [995, 5]]})).to_be(side_signature({_k: _v for _k, _v in [[995, 5], [440, 10]]}))
    test('order does not matter', _fn50)

    def _fn51():
        expect(side_signature({_k: _v for _k, _v in [[440, 10]]})).not_.to_be(side_signature({_k: _v for _k, _v in [[440, 11]]}))
    test('a count change changes the signature', _fn51)

    def _fn52():
        expect(side_signature({})).to_be('')
    test('empty is stable', _fn52)


describe('sideSignature', _fn49)


def _fn53():
    def _fn54():
        rl = RateLimiter(3, 10000, 30000)
        expect(rl.allow('alice', 0)).to_be(True)
        expect(rl.allow('alice', 1000)).to_be(True)
        expect(rl.allow('alice', 2000)).to_be(True)
    test('allows up to the cap inside the window', _fn54)

    def _fn55():
        rl = RateLimiter(3, 10000, 30000)
        for i in range(3):
            rl.allow('alice', i * 100)
        expect(rl.allow('alice', 400)).to_be(False)
        expect(rl.allow('alice', 20000)).to_be(False)
        expect(rl.allow('alice', 30401)).to_be(True)
    test('the next one trips the penalty', _fn55)

    def _fn56():
        rl = RateLimiter(3, 10000, 30000)
        t = 0
        while t < 200000:
            expect(rl.allow('alice', t)).to_be(True)
            t += 5000
    test('the window slides, so a steady talker is never penalised', _fn56)

    def _fn57():
        rl = RateLimiter(2, 10000, 30000)
        rl.allow('mallory', 0)
        rl.allow('mallory', 1)
        expect(rl.allow('mallory', 2)).to_be(False)
        expect(rl.allow('alice', 2)).to_be(True)
    test('one player flooding does not limit another', _fn57)

    def _fn58():
        rl = RateLimiter(1, 10000, 30000)
        rl.allow('Mallory', 0)
        expect(rl.allow('mallory', 1)).to_be(False)
    test('names are matched case-insensitively', _fn58)


describe('RateLimiter', _fn53)


def _fn59():
    def _fn60():
        expect(advertise_due(0, 59000, 60)).to_be(False)
        expect(advertise_due(0, 60000, 60)).to_be(True)
    test('fires once the interval has elapsed', _fn60)

    def _fn61():
        expect(advertise_due(0, 999999, 0)).to_be(False)
    test('zero seconds turns advertising off', _fn61)


describe('advertiseDue', _fn59)


# Why: a reset is what an operator reaches for when the shop is wedged, so it owes a bank trip whatever the pack looks like, and the trip deposits everything.
def _fn62():
    def _fn63():
        expect(settle_due(2, 0, 50000, False)).to_be(True)
        expect(settle_due(20, 60000, 50000, False)).to_be(True)
        expect(settle_due(20, 1000, 50000, False)).to_be(False)
    test('is owed on no room or takings over the float, as before', _fn63)

    def _fn64():
        expect(settle_due(28, 0, 50000, True)).to_be(True)
        expect(settle_due(20, 1000, 50000, True)).to_be(True)
    test('a reset owes one whatever the pack holds, empty included', _fn64)


describe('settleDue', _fn62)


# Why: a sale's goods are fetched for one customer, and a window opened with anyone else meanwhile takes their stock into the same pack.
def _fn65():
    def _fn66():
        expect(window_candidates(['Bob', 'alice', 'Carol'], 'Alice')).to_equal(['alice'])
        expect(window_candidates(['Bob', 'Carol'], 'Alice')).to_equal([])
    test('with a sale live only its customer may open, whatever the queue order', _fn66)

    def _fn67():
        expect(window_candidates(['Bob', 'Alice'], None)).to_equal(['Bob', 'Alice'])
    test('with no sale live the queue is served in order', _fn67)


describe('windowCandidates', _fn65)


# Why: what the shop buys goes to the bank before the next customer, so the trade that put coins out is the one that owes the trip.
def _fn68():
    coins = 995

    def _fn69():
        expect(buy_owes_settle({_k: _v for _k, _v in [[coins, 500]]}, coins)).to_be(True)
    test('a trade where the shop paid coins owes a bank trip', _fn69)

    def _fn70():
        expect(buy_owes_settle({_k: _v for _k, _v in [[440, 100]]}, coins)).to_be(False)
        expect(buy_owes_settle({}, coins)).to_be(False)
    test('a sale, where only goods went out, owes none', _fn70)


describe('buyOwesSettle', _fn68)


# Why: OpenWindow runs above Settle, so a queue of customers dumping goods kept it opening windows on a pack with no room and the shop never reached the bank.
def _fn71():
    def _fn72():
        expect(bank_before_serving(2, 0, 50000, True)).to_be(True)
    test('holds the next window while the pack has no room for what comes in', _fn72)

    def _fn73():
        expect(bank_before_serving(20, 60000, 50000, True)).to_be(True)
    test('holds it while the takings are over the float, which is the other reason to bank', _fn73)

    def _fn74():
        expect(bank_before_serving(20, 1000, 50000, True)).to_be(False)
    test('serves on as normal with room and coins in hand', _fn74)

    # Why: the shop is worth more open than shut, so a bank it cannot reach must not stop it trading.
    def _fn75():
        expect(bank_before_serving(0, 90000, 50000, False)).to_be(False)
    test('serves on while the bank is backed off, however full it is', _fn75)

    def _fn76():
        expect(bank_before_serving(28, 0, 50000, True, True)).to_be(True)
        expect(bank_before_serving(28, 0, 50000, False, True)).to_be(False)
    test('a reset holds the next window too, so its bank trip is not starved by the queue', _fn76)


describe('bankBeforeServing', _fn71)


def _fn77():
    def _fn78():
        expect(should_settle(2, 0, 50000)).to_be(True)
    test('true when free slots run low', _fn78)

    def _fn79():
        expect(should_settle(20, 60000, 50000)).to_be(True)
    test('true when pack coins pass the float', _fn79)

    def _fn80():
        expect(should_settle(20, 1000, 50000)).to_be(False)
    test('false otherwise', _fn80)


describe('shouldSettle', _fn77)


# Why: Settle used to ask for the raw float, and a bank that could not fill it left that true on every loop, so the shop stood at the booth banking and re-withdrawing one stack instead of trading.
def _fn81():
    def _fn82():
        expect(float_shortfall(0, 500000, 200000)).to_be(200000)
        expect(float_shortfall(50000, 500000, 200000)).to_be(150000)
    test('the gap to the float when the bank can cover it', _fn82)

    def _fn83():
        expect(float_shortfall(200000, 500000, 200000)).to_be(0)
        expect(float_shortfall(260000, 500000, 200000)).to_be(0)
    test('nothing to fetch once the pack is at the float', _fn83)

    def _fn84():
        expect(float_shortfall(0, 50000, 200000)).to_be(50000)
    test('a bank short of the float is asked only for what it has', _fn84)

    def _fn85():
        expect(float_shortfall(50000, 0, 200000)).to_be(0)
        expect(float_shortfall(0, 0, 200000)).to_be(0)
    test('nothing left to fetch, so the trip is not worth making again', _fn85)


describe('floatShortfall', _fn81)


# Why: the shop reports standing still as progress so the wedge check does not restart a healthy stall, and a trade window is part of that. ServeWindow outranks Listen and only Listen calls dropExpired, so the engagement timeout cannot fire while the window is open: without this a customer who opens the confirm screen and walks away holds the shop for ever and nothing rescues it.
def _fn86():
    def _fn87():
        expect(trade_is_stalled(False, False, False)).to_be(False)
        expect(trade_is_stalled(False, True, True)).to_be(False)
    test('no trade is not a stalled one', _fn87)

    def _fn88():
        expect(trade_is_stalled(True, True, False)).to_be(False)
    test('a live window inside its deadline is the shop working', _fn88)

    def _fn89():
        expect(trade_is_stalled(True, True, True)).to_be(True)
    test('past the deadline, nobody is advancing it', _fn89)

    def _fn90():
        expect(trade_is_stalled(True, False, False)).to_be(True)
    test('a trade the desk has let go of is orphaned', _fn90)


describe('tradeIsStalled', _fn86)


def _fn91():
    def _fn92():
        expect(fresh_chat_lines([], ['c', 'b', 'a'])).to_equal([])
    test('an empty mark primes without replaying history', _fn92)

    def _fn93():
        expect(fresh_chat_lines(['b', 'a'], ['b', 'a'])).to_equal([])
    test('no change means nothing fresh', _fn93)

    def _fn94():
        expect(fresh_chat_lines(['b', 'a'], ['c', 'b', 'a'])).to_equal(['c'])
    test('one new line comes back', _fn94)

    def _fn95():
        expect(fresh_chat_lines(['a'], ['d', 'c', 'b', 'a'])).to_equal(['b', 'c', 'd'])
    test('several new lines come back oldest-first', _fn95)

    # Why: repeating yourself is what a customer does the moment the shop looks like it ignored them.
    def _fn96():
        expect(fresh_chat_lines(['buy', 'x'], ['buy', 'buy', 'x'])).to_equal(['buy'])
    test('a verbatim repeat is heard again', _fn96)

    def _fn97():
        prev = ['x']
        heard = []
        for i in range(1, 3 + 1):
            now = ['buy'] * i + ['x']
            heard.append(*fresh_chat_lines(prev, now))
            prev = now
        expect(heard).to_equal(['buy', 'buy', 'buy'])
    test('the same line three times over is heard three times', _fn97)

    def _fn98():
        expect(fresh_chat_lines(['c', 'b', 'a'], ['e', 'd', 'c', 'b'])).to_equal(['d', 'e'])
    test('lines that fell off the end of the buffer do not replay everything', _fn98)

    def _fn99():
        expect(fresh_chat_lines(['a'], ['z', 'y'])).to_equal(['y', 'z'])
    test('a buffer with no overlap at all is treated as entirely new', _fn99)


describe('freshChatLines', _fn91)


def _fn100():
    def _fn101():
        expect(side_signature({_k: _v for _k, _v in [[COINS, 2200]]})).to_be('995x2200')
    test('sideSignature carries coins like any other id', _fn101)


describe('the coin id is never assumed', _fn100)


def rec(id, name, over=None):
    if over is None:
        over = Record({})
    _merged102 = {}
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
        _merged102[_k] = _v
    for _k, _v in (over._fields if isinstance(over, Record) else over).items():
        _merged102[_k] = _v
    return Record(_merged102)


# Why: the strung bow is the equippable one, and that flag is the only thing separating the pair by name.
QUOTE_CAT = build_catalog([
    rec(440, 'Iron ore'),
    rec(1333, 'Rune scimitar', Record({'equippable': True})),
    rec(851, 'Maple longbow', Record({'equippable': True})),
    rec(62, 'Maple longbow'),
    rec(853, 'Yew longbow', Record({'equippable': True})),
    rec(1515, 'Yew logs'),
])
QUOTE_BOOK = Record({
    'name': 'demo',
    'margin': 20,
    'max_trade_value': 500000,
    'rows': [
    Record({'id': 440, 'mid': 20, 'cap': 5000, 'buying': True, 'selling': True}),
    Record({'id': 1333, 'mid': 15000, 'cap': 20, 'buying': True, 'selling': True}),
    Record({'id': 851, 'mid': 640, 'cap': 500, 'buying': True, 'selling': True}),
    Record({'id': 62, 'mid': 320, 'cap': 500, 'buying': True, 'selling': True}),
    Record({'id': 853, 'mid': 800, 'cap': 500, 'buying': True, 'selling': True}),
    Record({'id': 1515, 'mid': 320, 'cap': 2000, 'buying': True, 'selling': False}),
],
})


def quote(query, qty_implied, side='selling'):
    return resolve_quote(Record({'cat': QUOTE_CAT, 'book': QUOTE_BOOK, 'query': query, 'side': side, 'qty_implied': qty_implied}))


def _fn103():
    # Why: an order the shop can never fill keeps Restock going back to the bank, and Restock at the bank is
    # Why: what stopped it banking anything, so cutting the order is what breaks the loop.
    def _fn104():
        desk.remember(intent('alice', 0, Record({'max_qty': 100})))
        desk.limit_to('alice', 40)
        expect((desk.intent_for('alice', 0, 90000).max_qty if desk.intent_for('alice', 0, 90000) is not None else None)).to_be(40)
    test('cuts an order down to what actually arrived', _fn104)

    def _fn105():
        desk.remember(intent('alice', 0, Record({'max_qty': 100})))
        desk.limit_to('alice', 500)
        expect((desk.intent_for('alice', 0, 90000).max_qty if desk.intent_for('alice', 0, 90000) is not None else None)).to_be(100)
    test('never raises an order, so nobody gets more than they asked for', _fn105)

    def _fn106():
        desk.remember(intent('alice', 0, Record({'max_qty': 100})))
        desk.limit_to('alice', 0)
        expect((desk.intent_for('alice', 0, 90000).max_qty if desk.intent_for('alice', 0, 90000) is not None else None)).to_be(100)
    test('nothing arriving leaves the order alone, for the miss count to deal with', _fn106)

    def _fn107():
        expect(lambda: desk.limit_to('nobody', 5)).not_.to_throw()
    test('a customer with no order is not a crash', _fn107)


describe('Desk.limitTo', _fn103)


def _fn108():
    def _fn109():
        desk.remember(intent('alice'))
        desk.cool('bob', 10000)
        desk.open('carol', 0)
        desk.clear()
        expect(desk.intent_for('alice', 0, 90000)).to_be_null()
        expect(desk.on_cooldown('bob', 0)).to_be(False)
        expect(desk.current()).to_be_null()
        expect(desk.intent_count()).to_be(0)
    test('drops intents, cooldowns and the window together', _fn109)

    def _fn110():
        expect(lambda: desk.clear()).not_.to_throw()
        expect(desk.intent_count()).to_be(0)
    test('clearing an empty desk is not an error', _fn110)


describe('Desk.clear', _fn108)


def _fn111():
    def _fn112():
        expect(quote('rune scimitar', True)).to_equal(Record({'kind': 'hit', 'id': 1333, 'name': 'Rune scimitar'}))
    test('an exact name lands with no count given', _fn112)

    def _fn113():
        expect(quote('rune scimitar', False)).to_equal(Record({'kind': 'hit', 'id': 1333, 'name': 'Rune scimitar'}))
    test('the same name lands when the count was given', _fn113)

    # Why: without this every sentence opening with "buy" would draw a reply, and a shop that answers passing chat gets muted.
    def _fn114():
        expect(quote('me a beer', True)).to_equal(Record({'kind': 'miss', 'answer': False}))
    test('ordinary chat with no count is a miss the shop does not answer', _fn114)

    def _fn115():
        expect(quote('dragon claws', False)).to_equal(Record({'kind': 'miss', 'answer': True}))
    test('a named item the shop does not stock is answered when the count was given', _fn115)

    # Why: a partial name is a typo worth answering when a count says the line was meant as a request, and a guess otherwise.
    def _fn116():
        expect(quote('scimitar', False)).to_equal(Record({'kind': 'hit', 'id': 1333, 'name': 'Rune scimitar'}))
        expect(quote('scimitar', True)).to_equal(Record({'kind': 'miss', 'answer': False}))
    test('a partial name only resolves when the count was given', _fn116)

    def _fn117():
        expect(quote('maple longbow', True)).to_equal(Record({'kind': 'hit', 'id': 851, 'name': 'Maple longbow'}))
        expect(quote('maple longbow u', True)).to_equal(Record({'kind': 'hit', 'id': 62, 'name': 'Maple longbow (u)'}))
    test('the bow pair splits on the u suffix with no count given', _fn117)

    def _fn118():
        target = quote('longbow', False)
        if target.kind != 'ambiguous':
            raise RuntimeError(f'expected ambiguous, got {target.kind}')
        expect(sorted([c.id for c in target.candidates], key=lambda a: a)).to_equal([62, 851, 853])
        expect(quote('longbow', True)).to_equal(Record({'kind': 'miss', 'answer': False}))
    test('a partial name matching several is ambiguous, and only reachable with a count', _fn118)

    def _fn119():
        expect(quote('yew logs', True)).to_equal(Record({'kind': 'miss', 'answer': False}))
        expect(quote('yew logs', True, 'buying')).to_equal(Record({'kind': 'hit', 'id': 1515, 'name': 'Yew logs'}))
    test('a row the shop will not sell is a miss on the selling side', _fn119)

    def _fn120():
        expect(quote('coins', False)).to_equal(Record({'kind': 'miss', 'answer': True}))
    test('an item outside the book is a miss on both sides', _fn120)


describe('resolveQuote', _fn111)


def deal_of_fields(o):
    return deal_of(o['give'], o['get'], o['coin_id'], o['customer'], o['at_ms'])


def _fn121():
    coins = 995

    def _fn122():
        deal = deal_of_fields(Obj({
        'give': {_k: _v for _k, _v in [[coins, 2200]]},
        'get': {_k: _v for _k, _v in [[440, 100]]},
        'coin_id': coins,
        'customer': 'Elliott',
        'at_ms': 1000,
    }))
        expect(deal).to_equal(Record({
        'at_ms': 1000,
        'customer': 'Elliott',
        'kind': 'bought',
        'item_id': 440,
        'count': 100,
        'gp': -2200,
        'mixed': False,
    }))
    test("coins on the shop's side means it bought", _fn122)

    def _fn123():
        deal = deal_of_fields(Obj({
        'give': {_k: _v for _k, _v in [[1333, 2]]},
        'get': {_k: _v for _k, _v in [[coins, 33000]]},
        'coin_id': coins,
        'customer': 'Elliott',
        'at_ms': 2000,
    }))
        expect(deal).to_equal(Record({
        'at_ms': 2000,
        'customer': 'Elliott',
        'kind': 'sold',
        'item_id': 1333,
        'count': 2,
        'gp': 33000,
        'mixed': False,
    }))
    test('coins on their side means it sold', _fn123)

    def _fn124():
        deal = deal_of_fields(Obj({
        'give': {_k: _v for _k, _v in [[coins, 5000]]},
        'get': {_k: _v for _k, _v in [[440, 100], [1515, 300]]},
        'coin_id': coins,
        'customer': 'Elliott',
        'at_ms': 3000,
    }))
        expect((deal.item_id if deal is not None else None)).to_be(1515)
        expect((deal.count if deal is not None else None)).to_be(300)
        expect((deal.mixed if deal is not None else None)).to_be(True)
    test('a mixed pile reports the biggest line and flags the rest', _fn124)

    # Why: a window that settled with coins on both sides and no goods is not a deal worth a line.
    def _fn125():
        expect(deal_of_fields(Obj({
        'give': {_k: _v for _k, _v in [[coins, 10]]},
        'get': {_k: _v for _k, _v in [[coins, 10]]},
        'coin_id': coins,
        'customer': 'a',
        'at_ms': 0,
    }))).to_be_null()
    test('coins for coins is not a deal', _fn125)


describe('dealOf', _fn121)


def _fn126():
    def _fn127():
        deals = [
        Record({'at_ms': 1, 'customer': 'a', 'kind': 'sold', 'item_id': 1, 'count': 1, 'gp': 500, 'mixed': False}),
        Record({'at_ms': 2, 'customer': 'b', 'kind': 'bought', 'item_id': 2, 'count': 1, 'gp': -200, 'mixed': False}),
        Record({'at_ms': 3, 'customer': 'c', 'kind': 'sold', 'item_id': 3, 'count': 1, 'gp': 100, 'mixed': False}),
    ]
        expect(deal_totals(deals)).to_equal(Record({'count': 3, 'net': 400, 'sold': 2, 'bought': 1}))
    test('nets the money and counts each way', _fn127)

    def _fn128():
        expect(deal_totals([])).to_equal(Record({'count': 0, 'net': 0, 'sold': 0, 'bought': 0}))
    test('no deals is a zero net, not a gap', _fn128)


describe('dealTotals', _fn126)


def _fn129():
    def _fn130():
        short = deal_line(Record({
        'clock': '14:32:06',
        'customer': 'Bob',
        'kind': 'sold',
        'count': 100,
        'item': 'Iron ore',
        'gp': 2200,
        'mixed': False,
    }))
        long = deal_line(Record({
        'clock': '14:31:41',
        'customer': 'Averylongname',
        'kind': 'bought',
        'count': 20,
        'item': 'Rune scimitar',
        'gp': -13500,
        'mixed': False,
    }))
        # Why: the money column is right-aligned, so it is the ends that line up, not where each number starts.
        expect(len(short)).to_be(len(long))
        expect(short.endswith('+2,200')).to_be(True)
        expect(long.endswith('-13,500')).to_be(True)
    test('columns line up whatever the name length', _fn130)

    def _fn131():
        expect(deal_line(Record({
        'clock': '00:00:00',
        'customer': 'a',
        'kind': 'bought',
        'count': 300,
        'item': 'Yew logs',
        'gp': -5000,
        'mixed': True,
    }))).to_contain('+more')
    test('a mixed pile says so', _fn131)

    def _fn132():
        expect(deal_line(Record({'clock': '00:00:00', 'customer': 'a', 'kind': 'sold', 'count': 1, 'item': 'X', 'gp': 10, 'mixed': False}))).to_contain('+10')
        expect(deal_line(Record({
        'clock': '00:00:00',
        'customer': 'a',
        'kind': 'bought',
        'count': 1,
        'item': 'X',
        'gp': -10,
        'mixed': False,
    }))).to_contain('-10')
    test('money carries its sign either way', _fn132)


describe('dealLine', _fn129)


def _fn133():
    BOOK = Record({
        'name': 'shelf',
        'margin': 20,
        'max_trade_value': 500000,
        'rows': [
        Record({'id': 440, 'mid': 20, 'cap': 5000, 'buying': True, 'selling': True}),
        Record({'id': 1515, 'mid': 320, 'cap': 2000, 'buying': True, 'selling': False}),
        Record({'id': 851, 'mid': 640, 'cap': 500, 'buying': False, 'selling': True}),
    ],
    })

    def rows(side, stock):
        return listed_rows(Record({'book': BOOK, 'side': side, 'stocked': lambda id: stock.get(str(id), 0)}))

    def _fn134():
        expect([r.id for r in rows('both', Record({'440': 900})).rows]).to_equal([440])
    test('a row the shop holds none of is not listed', _fn134)

    # Why: the operator chose to gate the buy side too, so the shop stops advertising what it wants while empty.
    def _fn135():
        expect([r.id for r in rows('buy', Record({'440': 900})).rows]).to_equal([440])
        expect([r.id for r in rows('buy', Record({'1515': 12})).rows]).to_equal([1515])
        expect(rows('buy', Record({})).rows).to_equal([])
    test('the gate applies to the buy side as well as the sell side', _fn135)

    def _fn136():
        stock = Record({'440': 900, '1515': 12, '851': 3})
        expect([r.id for r in rows('buy', stock).rows]).to_equal([440, 1515])
        expect([r.id for r in rows('sell', stock).rows]).to_equal([440, 851])
        expect([r.id for r in rows('both', stock).rows]).to_equal([440, 1515, 851])
    test('each side still filters on which way the row trades', _fn136)

    # Why: a shop that has sold out reads as broken unless it says so, and the two causes need different answers.
    def _fn137():
        expect(rows('both', Record({})).empty).to_be('no-stock')
        _merged138 = {}
        for _k, _v in (BOOK._fields if isinstance(BOOK, Record) else BOOK).items():
            _merged138[_k] = _v
        for _k, _v in {'rows': []}.items():
            _merged138[_k] = _v
        expect(listed_rows(Record({'book': Record(_merged138), 'side': 'both', 'stocked': lambda id: 0})).empty).to_be('no-book')
        expect(rows('both', Record({'440': 1})).empty).to_be_null()
    test('an empty book and an empty shelf are told apart', _fn137)

    def _fn139():
        expect([r.id for r in rows('sell', Record({'851': 40})).rows]).to_equal([851])
    test('bank stock counts, so a row the shop would fetch is still listed', _fn139)


describe('listedRows', _fn133)


# Why: what a sale owes is the customer's own request, which nothing on their side of the window changes, so making them watch an empty side settle before the goods go up is delay and nothing else.
def _fn140():
    base = Record({
        'still_beats_needed': 3,
        're_offer_cap': 12,
        'wait_cap': 25,
        'want_matched': False,
        'owe_anything': True,
        'owe_fixed': True,
        'owe_matched': False,
    })

    def _fn141():
        _merged142 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged142[_k] = _v
        for _k, _v in {'their_sig': '995x1', 'window': window_at(Record({'still_beats': 0, 'last_sig': ''}))}.items():
            _merged142[_k] = _v
        beat = decide_beat(Record(_merged142))
        expect(beat).to_equal(Record({'do': 'offer', 'reason': 'the goods asked for do not depend on their side'}))
    test('offers on the first beat, before their side has settled or paid', _fn141)

    def _fn143():
        _merged144 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged144[_k] = _v
        for _k, _v in {'their_sig': '995x7', 'window': window_at(Record({'last_sig': '995x1', 'still_beats': 0}))}.items():
            _merged144[_k] = _v
        beat = decide_beat(Record(_merged144))
        expect(beat.do).to_be('offer')
    test('offers while their side is still moving', _fn143)

    def _fn145():
        _merged146 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged146[_k] = _v
        for _k, _v in {
        'their_sig': '995x1',
        'window': window_at(Record({'still_beats': 9, 'last_sig': '995x1'})),
        'owe_matched': True,
    }.items():
            _merged146[_k] = _v
        beat = decide_beat(Record(_merged146))
        expect(beat).to_equal(Record({'do': 'wait', 'reason': 'their side is not the deal yet'}))
    test('once the goods are up it settles and waits on the money like any other trade', _fn145)

    def _fn147():
        _merged148 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged148[_k] = _v
        for _k, _v in {
        'their_sig': '995x1',
        'window': window_at(Record({'still_beats': 9, 'last_sig': '995x1'})),
        'owe_matched': True,
        'want_matched': True,
    }.items():
            _merged148[_k] = _v
        beat = decide_beat(Record(_merged148))
        expect(beat).to_equal(Record({'do': 'accept'}))
    test('and accepts once the money is the deal', _fn147)

    def _fn149():
        _merged150 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged150[_k] = _v
        for _k, _v in {'their_sig': '995x1', 'window': window_at(Record({'re_offers': 12}))}.items():
            _merged150[_k] = _v
        beat = decide_beat(Record(_merged150))
        expect(beat).to_equal(Record({'do': 'give-up', 'reason': 'too many changes in one trade'}))
    test('a customer who keeps changing their side still runs out of re-offers', _fn149)

    # Why: a purchase owes what is on their side, so putting coins up against a side still moving is what the settle wait is for.
    def _fn151():
        _merged152 = {}
        for _k, _v in (base._fields if isinstance(base, Record) else base).items():
            _merged152[_k] = _v
        for _k, _v in {
        'owe_fixed': False,
        'their_sig': '440x10',
        'window': window_at(Record({'last_sig': '440x9', 'still_beats': 0})),
    }.items():
            _merged152[_k] = _v
        beat = decide_beat(Record(_merged152))
        expect(beat).to_equal(Record({'do': 'wait', 'reason': 'their side moved'}))
    test('a purchase still waits for their side to settle', _fn151)


describe('a sale puts its goods up straight away', _fn140)


# Why: the customer who bought the cap and asked again had the goods fetched and no window, with the takings over the float holding every window and the live order holding Settle.
def _fn153():
    def _fn154():
        expect(settle_runs(True, False, True)).to_be(True)
        expect(settle_runs(True, False, False)).to_be(True)
    test('a due trip runs whether or not an order is live', _fn154)

    def _fn155():
        expect(settle_runs(False, True, True)).to_be(False)
        expect(settle_runs(False, True, False)).to_be(True)
    test('a float top-up alone waits for the live order', _fn155)

    def _fn156():
        expect(settle_runs(False, False, False)).to_be(False)
    test('nothing owed, nothing runs', _fn156)

    def _fn157():
        expect(settle_runs(settle_due(20, 5000000, 200000, False), False, True)).to_be(True)
    test('takings over the float after a cap-sized sale make the trip due with the next order live', _fn157)


describe('settleRuns', _fn153)


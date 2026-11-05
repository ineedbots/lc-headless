"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerMarket.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from rs2004.market.catalog import reset_live_catalog
from rs2004.events import events, Event
from bots.account_leveler.market import SeersAxeBuyer

def _fn1(*_args, **_kwargs):
    restore_all()
    reset_live_catalog()
after_each(_fn1)

def scenario():
    state = Record({'stage': 'none', 'coins': 30000, 'axes': 0, 'chats': [], 'price': 18000, 'partner': 'seers market', 'seller': 'seers market', 'response': '1 x Rune axe = 18,000gp (18,000ea). Trade me.', 'theirs': [Record({'id': 1360, 'name': 'Rune axe', 'count': 1})], 'mine': [], 'confirm_theirs': None, 'confirm_mine': None, 'available': True, 'open': True, 'complete': True, 'accepts': 0, 'offers': [], 'walks': 0, 'messages': 0, 'delays': 0})
    spy_on(game, 'scene_ready').mock_return_value(True)
    spy_on(game, 'in_combat').mock_return_value(False)
    spy_on(game, 'tile').mock_return_value(Tile(2725, 3491, 0))
    spy_on(event_signal, 'pending').mock_return_value(False)
    spy_on(inventory, 'free').mock_return_value(4)
    spy_on(inventory, 'count_by_id').mock_implementation(lambda id: (state.coins if id == 995 else (state.axes if id == 1360 else 0)))
    spy_on(players, 'query').mock_implementation(lambda: MarketPlayers(state))
    spy_on(reader, 'obj_catalog').mock_return_value([Record({'id': 1359, 'name': 'Rune axe', 'cost': 12800, 'stackable': False, 'members': False, 'equippable': True, 'certlink': -1, 'certtemplate': -1}), Record({'id': 1360, 'name': 'Rune axe', 'cost': 12800, 'stackable': True, 'members': False, 'equippable': False, 'certlink': 1359, 'certtemplate': 799})])

    def _fn2(*_args, **_kwargs):
        state.messages += 1
        if state.response:
            _emit_quote(state)
        return True
    spy_on(chat, 'say').mock_implementation(_fn2)

    def _fn3(*_args, **_kwargs):
        state.walks += 1
        return True
        if False:
            yield
    spy_on(traversal, 'walk_resilient').mock_implementation(_fn3)

    def _fn4(*_args, **_kwargs):
        state.delays += 1
        if False:
            yield
    spy_on(execution, 'delay').mock_implementation(_fn4)

    def _fn5(condition, *_args, **_kwargs):
        return condition()
        if False:
            yield
    spy_on(execution, 'delay_until').mock_implementation(_fn5)
    spy_on(trade, 'active').mock_implementation(lambda: state.stage != 'none')
    spy_on(trade, 'on_offer_screen').mock_implementation(lambda: state.stage == 'offer')
    spy_on(trade, 'on_confirm_screen').mock_implementation(lambda: state.stage == 'confirm')
    spy_on(trade, 'partner').mock_implementation(lambda: state.partner)
    spy_on(trade, 'my_offer').mock_implementation(lambda: (state.confirm_mine if state.stage == 'confirm' and state.confirm_mine is not None else state.mine))
    spy_on(trade, 'their_offer').mock_implementation(lambda: (state.confirm_theirs if state.stage == 'confirm' and state.confirm_theirs is not None else state.theirs))
    spy_on(trade, 'confirm_ready').mock_return_value(True)

    def _fn6(*_args, **_kwargs):
        if state.open:
            state.stage = 'offer'
        return True
    spy_on(trade, 'request').mock_implementation(_fn6)

    def _fn7(_item, count, *_args, **_kwargs):
        state.offers.append(count)
        state.mine = [Record({'id': 995, 'name': 'Coins', 'count': count})]
        return True
        if False:
            yield
    spy_on(trade, 'offer').mock_implementation(_fn7)

    def _fn8():
        state.accepts += 1
        if state.stage == 'offer':
            state.stage = 'confirm'
        elif state.complete:
            state.stage = 'none'
            state.coins -= state.price
            state.axes += 1
        return True
    spy_on(trade, 'accept').mock_implementation(_fn8)

    def _fn9():
        state.stage = 'none'
    spy_on(trade, 'decline').mock_implementation(_fn9)
    return Record({'state': state, 'buyer': SeersAxeBuyer(), 'buy': Record({'item': 'Rune axe', 'max_price': 20000, 'world': 1})})

def _fn10(*_args, **_kwargs):
    _o11 = scenario()
    state = _o11.state
    buyer = _o11.buyer
    buy = _o11.buy
    _w12 = yield from buyer.buy(buy)
    expect(_w12).to_be(True)
    expect(state.offers).to_equal([18000])
    expect(state.accepts).to_be(2)
    expect(state.axes).to_be(1)
    expect(state.coins).to_be(12000)
    _w13 = yield from buyer.buy(buy)
    expect(_w13).to_be(False)
    expect(state.messages).to_be(1)
test('buys one authenticated noted axe at the quoted price and checks the receipt', _fn10)

def _fn14(reason, *_args, **_kwargs):
    _o15 = scenario()
    state = _o15.state
    buyer = _o15.buyer
    buy = _o15.buy
    if reason == 'absent':
        state.available = False
    if reason == 'sold out':
        state.response = 'I have no Rune axe right now.'
    if reason == 'silent':
        state.response = ''
    if reason == 'busy':
        state.open = False
    if reason == 'world':
        buy.world = 2
    if reason == 'budget':
        buy.max_price = 17000
    if reason == 'reserve':
        state.coins = 18100
    if reason == 'foreign quote':
        state.seller = 'another seller'
    if reason == 'stale quote':
        state.chats.append(Record({'type': 2, 'username': state.seller, 'text': state.response}))
        state.response = ''
    _w16 = yield from buyer.buy(buy)
    expect(_w16).to_be(False)
    expect(state.offers).to_equal([])
    expect(state.accepts).to_be(0)
    expect(state.delays).to_be_less_than_or_equal(100)
    expect(state.walks).to_be_less_than_or_equal(1)
    if reason == 'world':
        expect(state.messages).to_be(0)
test_each(['absent', 'sold out', 'silent', 'busy', 'world', 'budget', 'reserve', 'foreign quote', 'stale quote'])('optional market miss continues without spending: %s', _fn14)

def _fn17(change, *_args, **_kwargs):
    _o18 = scenario()
    state = _o18.state
    buyer = _o18.buyer
    buy = _o18.buy
    if change == 'partner':
        state.partner = 'another seller'
    if change == 'wrong item':
        state.theirs = [Record({'id': 1351, 'name': 'Rune axe', 'count': 1})]
    if change == 'extra item':
        state.theirs.append(Record({'id': 1351, 'name': 'Bronze axe', 'count': 1}))
    if change == 'extra quantity':
        state.theirs[0].count = 2
    if change == 'confirm item':
        state.confirm_theirs = [Record({'id': 1351, 'name': 'Rune axe', 'count': 1})]
    if change == 'confirm coins':
        state.confirm_mine = [Record({'id': 995, 'name': 'Coins', 'count': 20000})]
    if change == 'empty confirm':
        state.confirm_theirs = []
    _w19 = yield from buyer.buy(buy)
    expect(_w19).to_be(False)
    expect(state.accepts).to_be_less_than(2)
    expect(state.coins).to_be(30000)
    expect(state.stage).to_be('none')
test_each(['partner', 'wrong item', 'extra item', 'extra quantity', 'confirm item', 'confirm coins', 'empty confirm'])('rejects a changed or incorrect trade: %s', _fn17)

def _fn20(*_args, **_kwargs):
    _o21 = scenario()
    state = _o21.state
    buyer = _o21.buyer
    buy = _o21.buy
    state.complete = False
    _w22 = yield from buyer.buy(buy)
    expect(_w22).to_be(False)
    expect(state.delays).to_be_less_than_or_equal(100)
    expect(state.stage).to_be('none')
    _w23 = yield from buyer.buy(buy)
    expect(_w23).to_be(False)
    expect(state.messages).to_be(1)
test('a seller that never confirms times out and is not retried', _fn20)

def _fn24(*_args, **_kwargs):
    _o25 = scenario()
    state = _o25.state
    buyer = _o25.buyer
    buy = _o25.buy

    def _fn26(*_args, **_kwargs):
        state.coins -= 100
        return True
        if False:
            yield
    spy_on(traversal, 'walk_resilient').mock_implementation(_fn26)
    _w27 = yield from buyer.buy(buy)
    expect(_w27).to_be(True)
    expect(state.coins).to_be(11900)
test('travel costs do not invalidate the verified trade receipt', _fn24)

def _fn28(*_args, **_kwargs):
    _o29 = scenario()
    state = _o29.state
    buyer = _o29.buyer
    buy = _o29.buy

    def _fn30():
        state.stage = 'none'
        return True
        if False:
            yield
    spy_on(trade, 'accept').mock_implementation(_fn30)
    _w31 = yield from buyer.buy(buy)
    expect(_w31).to_be(False)
    expect(state.axes).to_be(0)
    expect(state.coins).to_be(30000)
test('a closed trade without an item receipt is not reported as a purchase', _fn28)

def _fn32(*_args, **_kwargs):
    _o33 = scenario()
    state = _o33.state
    buyer = _o33.buyer
    buy = _o33.buy
    spy_on(event_signal, 'pending').mock_implementation(lambda: len(state.mine) > 0)
    _w34 = yield from buyer.buy(buy)
    expect(_w34).to_be(False)
    expect(state.accepts).to_be(0)
    expect(state.stage).to_be('none')
test('an event during the trade returns the coins without accepting', _fn32)

def _fn35(*_args, **_kwargs):
    _o36 = scenario()
    state = _o36.state
    buyer = _o36.buyer
    buy = _o36.buy
    state.chats.append(Record({'type': 2, 'username': state.seller, 'text': state.response}))
    _w37 = yield from buyer.buy(buy)
    expect(_w37).to_be(True)
test('a new quote identical to an older chat line is still eligible', _fn35)

class MarketPlayers:

    def __init__(self, state):
        self.state = state

    def name(self, value):
        return self

    def within(self, value):
        return self

    def first(self):
        return self.state.available

def resolved_wait(value):
    if False:
        yield
    return value

def _emit_quote(state):
    message = Event({'type': 'public', 'username': state.seller, 'text': state.response})
    for callback in events.subscribers('chat_message'):
        callback(message)

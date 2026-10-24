# Dumps a bank on a running MarketMaker: withdraws every tradeable item as notes, puts the pile up in one window
# and takes whatever the maker bids, banking the coins between trips: rs2b0t's JiveMarketDumper (MIT, see
# thirdparty/rs2b0t). It needs no price book, and stops when the bank is empty or the maker turns down all that's
# left.

import time

from rs2004.catalogs import ContinueDialog, Record, names_match
from rs2004.market import client_name, display_name, format_gp, live_catalog, noted_id, tradeable, unnoted_id

# logic.ts

COINS = 995
PACK = 28
# Why: the engine gives a trade only what the receiver has room for, one slot per stackable kind and per non-stackable unit, and the maker keeps a few free beside the coin float its own pack carries, so a trip that filled the pack would be refused space it cannot get.
TRADE_SLOTS = 20


# Why: no price book and no valuation, the maker prices what it sees and whatever it will not pay for rides along; the only things held back are coins and what the engine refuses to trade.
def dumpables(items, cat):
    """Everything in these items a trade window can carry, noted rows folded onto their item, in name order."""
    counts = {}
    for item in items:
        id = unnoted_id(cat, item.id)
        if id == COINS or not tradeable(id):
            continue
        counts[id] = counts.get(id, 0) + max(1, item.count)
    out = []
    for id in counts:
        count = counts[id]
        name = client_name(cat, id)
        if name is None:
            continue
        out.append(Record({
            'id': id,
            'name': name,
            'display_name': display_name(cat, id),
            'noted_id': noted_id(cat, id),
            'stackable': cat.by_id.get(id) is not None and cat.by_id.get(id).stackable is True,
            'count': count,
        }))
    out.sort(key=lambda d: d.display_name.lower())
    return out


# Why: a stackable has no noted form because it already stacks, so keying the slot cost off the noted id alone charged a 5,000 stack 5,000 slots and capped it at the trip size.
def slots_for(d):
    """Slots a line takes in the window: one for anything that stacks or notes, one per unit otherwise."""
    return (1 if d.stackable or d.noted_id is not None else d.count)


# Why: a noted or stacked line is one slot however deep, so most banks go in a trip or two; only an item that is neither costs a slot a unit and is cut to what is left.
def _with_count(d, count):
    fields = {}
    for key in d.keys():
        fields[key] = d.get(key)
    fields['count'] = count
    return Record(fields)


def plan_pile(list_, slots=20):
    """The lines one trip carries, filling `slots` trade slots from the top of the list."""
    out = []
    room = slots
    for d in list_:
        if room < 1:
            break
        if slots_for(d) == 1:
            out.append(_with_count(d, d.count))
            room -= 1
            continue
        n = min(d.count, room)
        out.append(_with_count(d, n))
        room -= n
    return out


def decide(state):
    """One step per loop: an open window is owned first, a loaded pack goes to the maker, an empty one goes to the bank."""
    if state.trade_active:
        return Record({'kind': 'trade'})
    return (Record({'kind': 'approach'}) if state.pile > 0 else Record({'kind': 'bank'}))


# Why: the offer screen shuts a tick before the confirm opens, so a single read of "no window" is the handover rather than the end, and treating it as the end leaves the confirm unaccepted and the goods staked.
def accept_action(view, grace_ticks=3):
    """What to do with a trade being accepted, from the screens up and how long neither has been."""
    if view.on_offer or view.on_confirm:
        return 'accept'
    return ('done' if view.dead_ticks > grace_ticks else 'wait')


# Why: an offered item leaves the pack view, so a pile read from the pack alone reads as empty mid-window; the two sides together are what is still ours to sell.
def held_with_offer(pack, offer):
    """The customer's own goods during a window: the pack plus what is already staked."""
    total = {}
    for item in list(pack) + list(offer):
        total[item.id] = total.get(item.id, 0) + max(1, item.count)
    return [Record({'id': id, 'count': total[id]}) for id in total]

# JiveMarketDumper.ts

BOOTH = {'name': 'Bank booth', 'op': 'Use-quickly'}
CATALOG_WAIT_MS = 15000
WALK_MS = 120000
WINDOW_WAIT_MS = 40000
BUSY_PAUSE_MS = 3000
OFFER_SETTLE_MS = 5000
OFFER_WAIT_MS = 20000
STABLE_POLLS = 3
POLL_MS = 500
HANDOVER_TICKS = 3
ACCEPT_STEPS = 30
ACCEPT_STEP_MS = 900
COINS_LAND_MS = 5000
MAKER_MISSES = 10
TOP_LINES = 3
NEAREST_BANK = 'Nearest'


# Why: the maker stands at a bank of its own choosing and the nearest one to wherever the dumper started is not always that bank, so the operator names it and the run walks there.
def bank_choice(name):
    """The bank a setting names, or null for the nearest one."""
    want = name.strip().lower()
    if want == '' or want == NEAREST_BANK.lower():
        return None
    for b in BANK_LOCATIONS:
        if b['name'].lower() == want:
            return b
    return None


SETTINGS = {
    'maker': SettingDef('string', '', 'Maker name', help='the player running MarketMaker; start this script standing beside it, at its bank'),
    'bank': SettingDef('string', NEAREST_BANK, 'Bank', options=[NEAREST_BANK] + [b['name'] for b in BANK_LOCATIONS], help="where the takings go between trips. Pick the maker's own bank, since the nearest one to where this starts is not always the one it stands at"),
}


def now_ms():
    return time.time() * 1000


def _tile(dict_tile):
    return Tile(dict_tile['x'], dict_tile['z'], dict_tile['level'])


class JiveMarketDumper(TaskBot):
    loop_delay = 600

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self._status = 'starting'
        self._cat = None
        self._bank = None
        self._bank_tile = None
        self._bank_name = 'the bank'
        self._started_at = time.time()
        self._sold_by_name = {}
        self._last_bank = []
        self.trades = 0
        self.gp = 0
        # Rows the maker wouldn't take at any price, so the next pile is a different one.
        self.refused = set()
        self.maker = self.settings.str('maker', '').strip()
        if self.maker == '':
            bot.request_finish('[dumper] no maker named in the settings')
            return
        loaded = yield from execution.delay_until(lambda: len(live_catalog().items) > 0, CATALOG_WAIT_MS)
        if not loaded:
            bot.request_finish('[dumper] the item catalogue never loaded')
            return
        self._cat = live_catalog()
        resolved = yield from self._resolve_bank()
        if not resolved:
            return
        banked = yield from self._bank_the_pack()
        if not banked:
            return
        self.log(f'[dumper] dumping the bank to {self.maker}, whatever it pays, banking at {self._bank_name}')
        self.add(ContinueDialog(), Sell(self), Approach(self), Restock(self))

    def _resolve_bank(self):
        here = game.tile()
        if not here:
            return False
        named = self.settings.str('bank', NEAREST_BANK)
        chosen = bank_choice(named)
        if chosen is None:
            chosen = nearest_bank(here)
        if chosen is None:
            bot.request_finish('[dumper] no reachable bank')
            return False
        self._bank = chosen
        self._bank_tile = _tile(chosen['tile'])
        self._bank_name = chosen['name']
        if self._bank_tile.level == here.level and self._bank_tile.distance_to(here) <= 6:
            return True
        self.set_status(f'walking to {self._bank_name}')
        arrived = yield from traversal.walk_resilient(self._bank_tile, radius=3, attempts=4, timeout_ms=WALK_MS, log=lambda m: self.log(f'  {m}'))
        if not arrived:
            bot.request_finish(f'[dumper] the walk to {self._bank_name} failed')
            return False
        return True

    # Why: a pack the run starts with is the operator's own goods rather than a planned pile, and `decide` reads any loaded pack as one and walks it to the maker; banking it first also means the first pile is planned off everything banked.
    def _bank_the_pack(self):
        if inventory.used() == 0:
            return True
        had = inventory.used()
        self.set_status('banking what the pack came with')
        opened = yield from self.open_bank()
        if not opened:
            bot.request_finish(f'[dumper] could not open {self._bank_name} to bank the {had} slot(s) the pack started with')
            return False
        yield from bank.deposit_all_matching(lambda name, id: True)
        emptied = yield from execution.delay_until(lambda: inventory.used() == 0, 5000)
        if not emptied:
            bot.request_finish(f'[dumper] {inventory.used()} slot(s) of the pack would not go into the bank')
            return False
        self.log(f'[dumper] banked the {had} slot(s) the pack started with')
        yield from bank.close()
        return True

    def recovery_anchor(self):
        return self._bank_tile

    def set_status(self, s):
        self._status = s

    def open_bank(self):
        if bank.is_open():
            return True
        self.set_status('opening the bank')
        opened = yield from open_bank_access(self._bank, BOOTH, lambda m: self.log(f'  {m}'))
        if opened:
            return True
        self.log('[dumper] could not open the bank, will retry')
        return False

    def dumpable(self, items):
        """What a trade window could carry among these, less the rows the maker has already turned down."""
        return ([] if self._cat is None else [d for d in dumpables(items, self._cat) if not (d.id in self.refused)])

    # Why: an offered item leaves the pack view, so mid-window the pile has to count what is already staked or it reads as empty and a good trade gets declined for nothing.
    def pack_pile(self):
        pack = [(Record({'id': i.id, 'count': i.count})) for i in inventory.items()]
        mine = (held_with_offer(pack, [(Record({'id': o.id, 'count': o.count})) for o in trade.my_offer()]) if trade.active() else pack)
        return self.dumpable(mine)

    def step(self):
        return decide(Record({'trade_active': trade.active(), 'pile': len(self.pack_pile())}))

    def maker_near(self):
        here = game.tile()
        player = players.query().where(lambda p: names_match((p.name if p.name is not None else ''), self.maker)).nearest()
        if not here or not player:
            return None
        tile = player.tile()
        return Record({'tile': tile, 'distance': max(abs(tile.x - here.x), abs(tile.z - here.z))})

    def busy_since(self, mark):
        """The engine's "busy at the moment" refusals since the mark."""
        return len([m for m in game_messages.since(mark) if 'busy at the moment' in (m.text or '').lower()])

    def refuse(self, lines):
        for line in lines:
            self.refused.add(line.id)
        self.log(f"[dumper] {self.maker} would not take {', '.join([l.display_name for l in lines])}, leaving {('it' if len(lines) == 1 else 'them')} banked")

    def note_bank(self, list_):
        self._last_bank = list_

    def note_sale(self, lines, gp):
        self.trades += 1
        self.gp += gp
        for l in lines:
            self._sold_by_name[l.display_name] = self._sold_by_name.get(l.display_name, 0) + l.count

    def on_progress_report(self):
        minutes = int((time.time() - self._started_at) / 60)
        top = sorted(list(self._sold_by_name.keys()), key=lambda name: -self._sold_by_name[name])[:TOP_LINES]
        return {'Status': self._status, 'Runtime': f'{minutes}m', 'Maker': self.maker, 'Trades': self.trades, 'Taken': f'{format_gp(self.gp)}gp',
                'Refused': len(self.refused), 'Banked rows': len(self._last_bank), 'Top': ', '.join([f'{n} x{self._sold_by_name[n]}' for n in top]) or '—'}


# Why: everything goes in, coins included, so the payment lands in the bank and the withdrawal always starts from an empty pack; notes, since the maker keeps four slots free and its pack is also its coin float.
class Restock(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.step().kind == 'bank'

    def execute(self):
        bot = self._bot
        opened = yield from bot.open_bank()
        if not opened:
            return
        bot.set_status('banking the takings')
        if inventory.used() > 0:
            yield from bank.deposit_all_matching(lambda name, id: True)
            yield from execution.delay_ticks(1)
        listed = yield from execution.delay_until(lambda: bank.is_open() and bank.loaded(), 5000)
        if not listed:
            bot.log(('[dumper] the bank list has not filled in, retrying' if bank.is_open() else '[dumper] the bank window closed, retrying'))
            return
        yield from bank.set_note_mode(True)
        list_ = bot.dumpable([(Record({'id': i.id, 'count': i.count})) for i in bank.items()])
        bot.note_bank(list_)
        pile = plan_pile(list_, TRADE_SLOTS)
        if len(pile) == 0:
            yield from bank.close()
            bot.set_status('stopped')
            bot.request_finish((f'[dumper] the bank holds nothing tradeable; {bot.trades} trade(s) took {format_gp(bot.gp)}gp' if len(bot.refused) == 0 else f'[dumper] all that is left is {len(bot.refused)} kind(s) {bot.maker} would not take; {bot.trades} trade(s) took {format_gp(bot.gp)}gp'))
            return
        for line in pile:
            if not bank.is_open() or not bank.loaded():
                bot.log('[dumper] the bank window closed mid-withdrawal, retrying')
                return
            bot.set_status(f'withdrawing {line.count} {line.display_name}')
            took = yield from bank.withdraw_x_by_id(line.id, line.count, line.noted_id if line.noted_id is not None else line.id)
            if not took:
                bot.log(f'[dumper] could not withdraw {line.count} {line.display_name}, retrying')
                return
        closed = yield from bank.close()
        if not closed:
            bot.log('[dumper] the bank would not close, retrying')
            return
        bot.log(f'[dumper] took {describe(pile)}')


# Why: a "Trade with" click clears the pending action and shuts a window that opened the same tick, so one request gets one long wait, and only a refusal from the engine earns another.
class Approach(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot
        self._misses = 0

    def validate(self):
        return self._bot.step().kind == 'approach'

    def execute(self):
        bot = self._bot
        near = bot.maker_near()
        if not near:
            self._misses += 1
            if self._misses >= MAKER_MISSES:
                bot.set_status('stopped')
                bot.request_finish(f'[dumper] {bot.maker} is not in sight; start this beside the maker')
                return
            bot.set_status(f'looking for {bot.maker}')
            yield from execution.delay_ticks(2)
            return
        self._misses = 0
        if near.distance > 2:
            bot.set_status(f'walking to {bot.maker}')
            yield from traversal.walk_resilient(near.tile, radius=1, attempts=3, timeout_ms=WALK_MS, log=lambda m: bot.log(f'  {m}'))
            return
        here = game.tile()
        if here and near.distance == 0:
            yield from traversal.walk_resilient(Tile(here.x + 1, here.z, here.level), radius=0, attempts=2, timeout_ms=20000, log=lambda m: bot.log(f'  {m}'))
            return
        yield from modals.close_if_open()
        mark = game_messages.mark()
        bot.set_status(f'asking {bot.maker} to trade')
        if not (trade.request(bot.maker)):
            bot.log(f'[dumper] {bot.maker} is not in the scene to click')
            yield from execution.delay_ticks(2)
            return
        answered = yield from execution.delay_until(lambda: trade.on_offer_screen() or bot.busy_since(mark) > 0, WINDOW_WAIT_MS)
        if not trade.on_offer_screen():
            bot.log((f'[dumper] {bot.maker} is busy at the bank, asking again shortly' if answered else f'[dumper] {bot.maker} did not open the window, asking again'))
            yield from execution.delay(BUSY_PAUSE_MS)


def _staked(pile):
    """Every line of the pile shows in our offer."""
    for line in pile:
        id = line.noted_id if line.noted_id is not None else line.id
        if sum([max(1, o.count) for o in trade.my_offer() if o.id == id]) < line.count:
            return False
    return True


def describe(lines):
    return ' + '.join([f'{l.count} {l.display_name}' for l in lines])


def coins_on(offer):
    return sum([max(1, o.count) for o in offer if o.id == COINS])


# Why: the maker prices what it sees and pays what it carries, so every line goes up and whatever it bids is taken; only a pile it will not pay for at all is pulled back, since it never completes a trade it owes nothing on.
class Sell(Task):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def validate(self):
        return self._bot.step().kind == 'trade'

    def execute(self):
        bot = self._bot
        coins_before = inventory.count_by_id(COINS)
        pile = bot.pack_pile()
        if len(pile) == 0:
            bot.log('[dumper] nothing left to offer, closing the window')
            yield from trade.decline()
            return
        put = yield from self._put_up(pile)
        if not put:
            return
        bot.set_status(f'waiting on {bot.maker}')
        offered = yield from self._await_offer()
        if not trade.active():
            bot.log(f'[dumper] {bot.maker} closed the window without paying')
            bot.refuse(pile)
            return
        if offered <= 0:
            bot.log(f'[dumper] {bot.maker} put up nothing for {describe(pile)}')
            bot.refuse(pile)
            yield from trade.decline()
            return
        yield from self._accept(pile, coins_before, offered)

    def _put_up(self, pile):
        self._bot.set_status(f'offering {describe(pile)}')
        for line in pile:
            id = (line.noted_id if line.noted_id is not None else line.id)
            n = min(line.count, inventory.count_by_id(id))
            if n < 1:
                continue
            put = yield from trade.offer(line.name, n, lambda i: i.id == id)
            if not put:
                self._bot.log(f'[dumper] could not put up {n} {line.display_name}')
                return False

        shown = yield from execution.delay_until(lambda: not trade.active() or _staked(pile), OFFER_SETTLE_MS)
        if not shown:
            self._bot.log('[dumper] the offer never showed every line, retrying')
            return False
        return trade.active()

    def _await_offer(self):
        """The coins the maker settles on, or zero when it puts up nothing for the pile."""
        deadline = now_ms() + OFFER_WAIT_MS
        coins = 0
        stable = 0
        while trade.active() and now_ms() < deadline:
            now = coins_on(trade.their_offer())
            stable = (stable + 1 if now > 0 and now == coins else 0)
            coins = now
            if stable >= STABLE_POLLS:
                return coins
            yield from execution.delay(POLL_MS)
        return coins

    def _accept(self, pile, coins_before, offered):
        bot = self._bot
        bot.set_status(f'accepting {format_gp(offered)}gp')
        dead = 0
        saw_confirm = False
        for step in range(ACCEPT_STEPS):
            view = Record({'on_offer': trade.on_offer_screen(), 'on_confirm': trade.on_confirm_screen(), 'dead_ticks': dead})
            saw_confirm = saw_confirm or view.on_confirm
            action = accept_action(view, HANDOVER_TICKS)
            if action == 'done':
                break
            if action == 'wait':
                dead += 1
                yield from execution.delay_ticks(1)
                continue
            dead = 0
            trade.accept()
            yield from execution.delay(ACCEPT_STEP_MS)
        if trade.active():
            bot.log('[dumper] the trade never closed, walking out of it')
            yield from trade.decline()
            return
        # Why: the pack shows the payment only once the window is gone, so the coins are waited for rather than read on the next tick.
        yield from execution.delay_until(lambda: inventory.count_by_id(COINS) > coins_before, COINS_LAND_MS)
        gp = inventory.count_by_id(COINS) - coins_before
        if gp <= 0:
            never = '' if saw_confirm else f', and {bot.maker} never reached the confirm screen'
            bot.log(f'[dumper] the window closed with no coins paid{never}')
            return
        bot.note_sale(pile, gp)
        bot.log(f'[dumper] dumped {describe(pile)} for {format_gp(gp)}gp')


BOT = define_bot(
    name='JiveMarketDumper',
    create=JiveMarketDumper,
    description='Dumps a bank to a running MarketMaker: withdraws every tradeable item as notes, puts the pile up in one window and takes whatever the maker bids, banking the coins between trips. It needs no price book, since anything the maker will not pay for rides along with what it does. Stops when the bank is empty or the maker turns down all that is left.',
    category='Money making',
    tags=['trading', 'bank', 'market', 'afk'],
    settings_schema=SETTINGS,
)

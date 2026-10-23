# A master stands at the nature (or air) altar crafting the essence runners trade it; runners bank essence, un-note
# it at Shilo's general store on the nature route, and carry it to the master: rs2b0t's NatureCrafter (MIT, see
# thirdparty/rs2b0t). The mode and partner names come from the settings.

import math
import time

from rs2004.catalogs import ContinueDialog

ESSENCE = 'Rune essence'
# Unnoted essence; the bank-note variant has a different id.
ESSENCE_ID = 1436
COINS_ID = 995
RUINS = 'Mysterious ruins'
ALTAR_NAME = 'Altar'
ALTAR_OP = 'Craft-rune'
PORTAL_NAME = 'Portal'
PORTAL_OP = 'Use'
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
TEMPLE_Z = 4000
TRADE_REQ_TEXT = 'wishes to trade with you'
COINS = 'Coins'
LADDER = 'Ladder'
CLIMB_UP = 'Climb-up'
CLIMB_DOWN = 'Climb-down'
AGGRO_SHAKE_TICKS = 5
SHAKE_COOLDOWN_MS = 60000
BANK_BACKOFF_MS = 300000
PICKUP_BLOCK_MS = 120000

TRADE_CAP = 25
TRADE_ADJACENT = 2
RUNNER_ASK_MS = 1800
MASTER_HANDSHAKE_MS = 3000
BUY_ONLY_STOCK = 30
LOW_COINS = 1000
PICKUP_RANGE = 20
STORE_PASSES = 6
# Enough above LOW_COINS for fares and a buy-back, so it doesn't loop between the bank and the boat.
MIN_COIN_TARGET = 3000
ESSENCE_NAME = 'rune essence'
COINS_NAME = 'coins'
EVENT_HELD = ['strange box', 'lamp']
# Off the direct line through the jungle spiders.
SPIDER_SAFE = Tile(2790, 3094, 0)


class RuneRoute:
    def __init__(self, talisman, rune, level, ruins, runner_bank, master_bank, unnote_npc=None, unnote_tile=None):
        self.talisman = talisman
        self.rune = rune
        self.level = level
        self.ruins = ruins
        self.runner_bank = runner_bank
        self.master_bank = master_bank
        # The store that un-notes essence, on routes that carry it noted.
        self.unnote_npc = unnote_npc
        self.unnote_tile = unnote_tile


RUNES = {
    'Nature runes': RuneRoute('Nature talisman', 'Nature rune', 44, Tile(2865, 3022, 0), Tile(2655, 3283, 0), Tile(2852, 2954, 0), 'Jiminua', Tile(2767, 3122, 0)),
    'Air runes': RuneRoute('Air talisman', 'Air rune', 1, Tile(2983, 3288, 0), Tile(3013, 3355, 0), Tile(3013, 3355, 0)),
}
RUNE_OPTIONS = list(RUNES)
DEFAULT_RUNE = 'Nature runes'

SETTINGS = {
    'rune': SettingDef('string', DEFAULT_RUNE, 'Rune', options=RUNE_OPTIONS,
                       help='which rune the pair crafts. Nature = Ardougne bank + ship + Jiminua un-noting; Air = Falador East bank, straight there and back'),
    'mode': SettingDef('string', 'Master', 'Mode', options=['Master', 'Runner'],
                       help='Master crafts at the altar and takes essence from runners; Runner ferries essence to the master'),
    'partner': SettingDef('string', '', 'Partner name(s)', help='Master: runner name(s) to accept essence from, comma-separated. Runner: the master to deliver to.'),
    'bank_every': SettingDef('number', 60, 'Bank everything every N minutes (0 = never)', 0,
                             help="Master: walks to the bank on this timer and deposits everything except the talisman — banks the runes and clears out whatever random events have left in the pack. Air banks at Falador East; the nature master's nearest bank is the quest-gated Shilo Village one, so it may not be reachable"),
    'withdraw_ess': SettingDef('number', 0, 'Essence per restock (0 = default)', 0,
                               help='Runner: essence withdrawn per bank restock. 0 = the full bank stack when noting (nature), or one trade-load (air)'),
    'withdraw_coins': SettingDef('number', 10000, 'Coins target at restock', 0,
                                 help='Runner: top coins up to this at each restock (boat fares + shop buy-backs). Unused by air.'),
    'stay_in_altar': SettingDef('boolean', False, 'Stay in the altar', help='Master and runner wait and trade inside the altar. Runners need a nature talisman.'),
}


# The pure decisions, kept apart from the game so they can be tested without a client.

def coin_target_for(setting):
    return max(MIN_COIN_TARGET, math.floor(setting) or 0)


def plan_store_step(stock, noted, unnoted):
    """The store's next step toward one trade of unnoted essence: ('done', 0), ('buy', n) or ('sell', n)."""
    need = TRADE_CAP - unnoted
    if need <= 0:
        return ('done', 0)
    if stock > BUY_ONLY_STOCK:
        return ('buy', need)
    to_sell = min(noted, max(0, need - stock))
    if to_sell > 0:
        return ('sell', to_sell)
    if stock > 0:
        return ('buy', min(need, stock))
    return ('done', 0)


def offer_count(unnoted):
    return max(0, min(TRADE_CAP, unnoted))


def keep_names(talisman, product_rune):
    """Coins, essence and the talisman; the master keeps the rune it crafts too. A nameless slot is litter."""
    keep = [ESSENCE_NAME, COINS_NAME, talisman.lower()]
    if product_rune:
        keep.append(product_rune.lower())
    return keep


def is_event_held(name):
    return name is not None and name.lower() in EVENT_HELD


def is_litter(name, keep):
    if is_event_held(name):
        return False
    if name is None or name.strip() == '':
        return True
    return name.lower() not in keep


def is_droppable_litter(name, keep, actions):
    return is_litter(name, keep) and len([a for a in actions if a.lower() == 'drop']) > 0


def is_near(a, b, radius):
    return max(abs(a.x - b.x), abs(a.z - b.z)) <= radius


def spider_safe_via(here, dest, store, ruins):
    """Whether to go by SPIDER_SAFE rather than the direct line through the jungle spiders."""
    if not is_near(dest, store, 3) and not is_near(dest, ruins, 3):
        return False
    if here is not None and is_near(here, dest, 3):
        return False
    return here is None or not is_near(here, SPIDER_SAFE, 3)


def master_offer_decision(who, is_partner, their_essence, runner_waiting):
    """The master's offer-screen policy: 'decline', 'accept' or 'wait'. A blank header can still be a runner's offer."""
    if who is not None and not is_partner:
        return 'decline'
    if their_essence > 0 and (is_partner or runner_waiting):
        return 'accept'
    return 'wait'


def trade_window_is_for(partner_header, clicked):
    """Whether the open trade is with the player last clicked; a blank header still is."""
    if not partner_header:
        return True
    return partner_header.lower() == clicked.lower()


def master_pick_trade_target(asked, asked_at, last_accept_at, asked_in_range, hold_until, now):
    """The requester, when its request is newer than the last accept; a second Trade-with click closes the window."""
    if now < hold_until or not asked or not asked_in_range or asked_at <= last_accept_at:
        return None
    return asked


def runner_should_request_trade(trade_active, last_request_at, now):
    """Runners ask again on an interval; clicking every tick cancels the open window and every other runner's request."""
    return not trade_active and now - last_request_at >= RUNNER_ASK_MS


def runner_may_leave_altar(trade_active, unnoted):
    return not trade_active and unnoted == 0


def runner_should_walk_to_meet(master_visible, already_meeting, temple, stay_in_altar):
    if stay_in_altar and not temple:
        return True
    if master_visible or already_meeting:
        return False
    return not temple


def master_should_exit_temple(temple, ess, stay_in_altar, bank_due):
    if not temple or ess > 0:
        return False
    return not stay_in_altar or bank_due


def master_should_enter_altar(temple, ess, stay_in_altar, bank_due):
    if temple:
        return False
    if ess > 0:
        return True
    # Why: staying in the altar with a bank trip due used to take the portal out and go straight back in with the
    # talisman, never reaching the bank.
    return stay_in_altar and not bank_due


# The short route only: one trade window's load, so there's no second round trip to the altar.
def short_route_withdraw(per_setting, banked, room):
    want = min(per_setting, TRADE_CAP) if per_setting > 0 else TRADE_CAP
    return max(0, min(want, banked, room if room > 0 else TRADE_CAP))


def now_ms():
    return time.time() * 1000


def in_temple():
    t = game.tile()
    return t is not None and t.z > TEMPLE_Z


def ess_count():
    return inventory.count(ESSENCE)


def noted_essence():
    return sum([i.count for i in inventory.items() if (i.name or '').lower() == ESSENCE.lower() and i.id != ESSENCE_ID])


def unnoted_essence():
    return sum([i.count for i in inventory.items() if i.id == ESSENCE_ID])


def offer_ess(items):
    return sum([max(1, o.count) for o in items if (o.name or '').lower() == ESSENCE.lower()])


def trade_snap():
    screen = 'confirm' if trade.on_confirm_screen() else ('offer' if trade.on_offer_screen() else ('open' if trade.active() else 'closed'))
    return f"{screen} with={trade.partner() or '-'} mine={offer_ess(trade.my_offer())} theirs={offer_ess(trade.their_offer())} unnoted={unnoted_essence()}"


def enter_altar(bot):
    """Use with yield from."""
    yield from bot.walk_to(bot.conf.ruins, 1)
    ruins = locs.query().name(RUINS).nearest()
    talisman = inventory.first(bot.conf.talisman)
    if ruins is None or talisman is None:
        yield from execution.delay_ticks(2)
        return False
    bot.log(f'using the {bot.conf.talisman} on the mysterious ruins')
    if not talisman.use_on(ruins):
        yield from execution.delay_ticks(2)
        return False
    entered = yield from execution.delay_until(in_temple, 10000)
    if entered:
        bot.log('entered the altar')
    return entered


# Why: the craft locks the player for a moment, so a tight loop clicks the portal and Use fires as soon as it clears.
def portal_out(bot):
    """Use with yield from."""
    bot.status = 'taking the portal out'
    bot.log('taking the portal back to the ruins')
    for _ in range(15):
        if not in_temple():
            break
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            continue
        portal = locs.query().name(PORTAL_NAME).action(PORTAL_OP).nearest()
        if portal is not None:
            portal.interact(PORTAL_OP)
        yield from execution.delay_ticks(1)
    if not in_temple():
        bot.log('back at the mysterious ruins')


class DropLitter(Task):
    def __init__(self, bot, keep_product_rune):
        Task.__init__(self, label='drop litter')
        self.bot = bot
        self.keep_product_rune = keep_product_rune

    def droppable(self):
        keep = self.bot.keep_list(self.keep_product_rune)
        return [i for i in inventory.items() if is_droppable_litter(i.name, keep, i.actions())]

    def validate(self):
        return not trade.active() and not shop.is_open() and not bank.is_open() and len(self.droppable()) > 0

    def execute(self):
        bot = self.bot
        bot.status = 'dropping random-event junk'
        for _ in range(28):
            items = self.droppable()
            if len(items) == 0:
                break
            item = items[0]
            bot.say(f"dropping {item.name or f'item#{item.id}'}")
            before = inventory.used()
            if not item.interact('Drop'):
                yield from execution.delay_ticks(1)
                return
            yield from execution.delay_until(lambda: inventory.used() < before, 3000)


# Master: the talisman, the runes it crafts and the essence it works are all it should hold; the rest is
# random-event litter.
class HandleOpenTrade(Task):
    def __init__(self, bot):
        Task.__init__(self, label='handle open trade')
        self.bot = bot
        self.last_wait = ''
        self.awaiting_confirm = False

    def validate(self):
        on = trade.active() or self.awaiting_confirm
        if not on:
            self.bot.set_trade_hot(False)
        return on

    def execute(self):
        bot = self.bot
        bot.set_trade_hot(True)
        if trade.on_confirm_screen():
            self.awaiting_confirm = True
            bot.status = 'confirming the essence trade'
            bot.say(f'confirm-accept {trade_snap()}')
            before = ess_count()
            trade.accept()
            if not trade.active() and ess_count() > before:
                bot.count_trade(ess_count() - before)
                bot.say(f'received {ess_count() - before} essence {trade_snap()}')
                self.awaiting_confirm = False
            return
        if trade.on_offer_screen():
            yield from self.drive_offer_screen()
            return
        if self.awaiting_confirm:
            got = ess_count()
            if got > 0:
                bot.count_trade(got)
                bot.say(f'received {got} essence {trade_snap()}')
            else:
                bot.say(f'handshake dropped {trade_snap()}')
            self.awaiting_confirm = False

    def drive_offer_screen(self):
        """Use with yield from."""
        bot = self.bot
        who = trade.partner()
        their_essence = offer_ess(trade.their_offer())
        waiting = bot.last_requester is not None or bot.adjacent_runner() is not None
        decision = master_offer_decision(who, bot.is_partner(who), their_essence, waiting)
        if decision == 'decline':
            bot.status = f'declining trade from {who}'
            bot.say(f'decline stranger {trade_snap()}')
            yield from trade.decline()
            self.awaiting_confirm = False
            return False
        if decision == 'wait':
            bot.status = f'waiting for {who} to offer essence' if who else 'reading trade partner'
            key = f"{who}:{their_essence}:{bot.last_requester or ''}"
            if key != self.last_wait:
                self.last_wait = key
                bot.say(f"offer-wait {trade_snap()} asked={bot.last_requester or '-'}")
            yield from execution.delay_ticks(1)
            return False
        offered = trade.my_offer()
        precious = [n.lower() for n in [bot.conf.talisman, bot.conf.rune, ESSENCE]]
        if len([o for o in offered if (o.name or '').lower() in precious]) > 0:
            bot.say(f"decline safety mine=[{','.join([o.name or '?' for o in offered])}] {trade_snap()}")
            yield from trade.decline()
            self.awaiting_confirm = False
            return False
        self.last_wait = ''
        self.awaiting_confirm = True
        bot.status = f"accepting {their_essence} essence from {who or 'runner'}"
        bot.say(f'offer-accept {their_essence} ess {trade_snap()}')
        trade.accept()
        return True


class CraftNatures(Task):
    def __init__(self, bot):
        Task.__init__(self, label='craft natures')
        self.bot = bot

    def validate(self):
        return in_temple() and ess_count() > 0

    def execute(self):
        bot = self.bot
        altar = locs.query().name(ALTAR_NAME).action(ALTAR_OP).nearest()
        if altar is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = 'crafting runes'
        before = ess_count()
        bot.log(f'crafting {before} essence at the altar')
        if not altar.interact(ALTAR_OP):
            yield from execution.delay_ticks(2)
            return
        yield from execution.delay_until(lambda: ess_count() == 0, 8000)
        made = before - ess_count()
        bot.crafted += made
        bot.log(f'crafted {made} {bot.conf.rune}s')
        if not bot.stay_in_altar:
            yield from portal_out(bot)


class ExitTemple(Task):
    def __init__(self, bot):
        Task.__init__(self, label='exit temple')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return master_should_exit_temple(in_temple(), ess_count(), bot.stay_in_altar, bot.bank_trip_due())

    def execute(self):
        if self.bot.bank_trip_due():
            self.bot.log('taking the portal — bank trip due')
        yield from portal_out(self.bot)


class EnterAltar(Task):
    def __init__(self, bot):
        Task.__init__(self, label='enter altar')
        self.bot = bot
        self.fails = 0

    def validate(self):
        bot = self.bot
        return master_should_enter_altar(in_temple(), ess_count(), bot.stay_in_altar, bot.bank_trip_due())

    def execute(self):
        bot = self.bot
        bot.status = 'entering the altar to craft' if ess_count() > 0 else 'entering the altar to wait'
        entered = yield from enter_altar(bot)
        if entered:
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= 3:
            bot.request_finish("NatureCrafter: the talisman didn't teleport into the altar")


# Why: a bank trip on a timer, depositing everything, banks the runes and whatever random events dropped in the
# pack at once, which is simpler than working out which litter can be traded or dropped.
class BankEverything(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank everything')
        self.bot = bot
        self.backoff_until = 0

    def validate(self):
        return self.bot.bank_trip_due() and not in_temple() and ess_count() == 0 and not trade.active() and now_ms() >= self.backoff_until

    def execute(self):
        bot = self.bot
        conf = bot.conf
        bot.mark_bank_done()
        bot.status = 'banking everything'
        bot.log(f'{round(bot.bank_ms / 60000)}min bank trip — {inventory.count(conf.rune)} {conf.rune}s and anything else in the pack')
        # A short timeout, so a quest-gated bank out of reach fails fast rather than after the default 240s.
        reached = yield from traversal.walk_resilient(conf.master_bank, radius=3, attempts=2, timeout_ms=30000, log=lambda m: bot.log(f'  {m}'))
        opened = False
        if reached:
            opened = yield from bank.open_booth(conf.master_bank, BOOTH_NAME, BOOTH_OP)
            if not opened:
                opened = yield from bank.open_nearest(BOOTH_NAME, BOOTH_OP)
        if not opened:
            bot.log('NatureCrafter: bank unreachable (Shilo Village quest?) — holding runes (they stack) and continuing to serve runners')
            self.backoff_until = now_ms() + BANK_BACKOFF_MS
            yield from bot.walk_to(conf.ruins, 1)
            return
        made = inventory.count(conf.rune)
        before = inventory.used()
        yield from bank.deposit_all_matching(deposit_all_except([conf.talisman]))
        yield from execution.delay_ticks(1)
        bot.log(f'banked {made} {conf.rune}s, cleared {before - inventory.used()} slot(s); back to the altar')
        yield from bot.walk_to(conf.ruins, 1)


class AcceptRunner(Task):
    def __init__(self, bot):
        Task.__init__(self, label='accept runner')
        self.bot = bot
        self.next_click_at = 0

    def validate(self):
        bot = self.bot
        return (ess_count() == 0 and not trade.active() and now_ms() >= self.next_click_at and bot.trade_target() is not None
                and (bot.stay_in_altar or not in_temple()))

    def execute(self):
        bot = self.bot
        name = bot.trade_target()
        if not name:
            return
        nearest = bot.adjacent_runner()
        named = bot.runner_named(name, 20)
        bot.status = f"accepting {name}'s trade"
        bot.say(f"Trade-with '{name}' asked={bot.last_requester or '-'} nearest={nearest.name if nearest is not None else '-'} d={named.distance() if named is not None else '-'} {trade_snap()}")
        self.next_click_at = now_ms() + MASTER_HANDSHAKE_MS
        bot.mark_handshake_started()
        trade.request(name)
        yield from execution.delay_ticks(1)
        if trade.active() and not trade_window_is_for(trade.partner(), name):
            self.next_click_at = now_ms() + 3000
            bot.say(f'window is with someone else wanted={name} {trade_snap()}')
            return
        opened = yield from execution.delay_until(lambda: trade.active() and trade_window_is_for(trade.partner(), name), 4000)
        bot.say(f'window opened {trade_snap()}' if opened else f'window did not open {trade_snap()}')


class WaitForRunner(Task):
    def __init__(self, bot):
        Task.__init__(self, label='wait for runner')
        self.bot = bot

    def validate(self):
        return ess_count() == 0 and (self.bot.stay_in_altar or not in_temple())

    def execute(self):
        bot = self.bot
        if bot.nearest_partner() is not None or bot.last_requester is not None:
            bot.status = 'runner in sight — standing for the trade'
            yield from execution.delay_ticks(1)
            return
        if bot.stay_in_altar and in_temple():
            bot.status = 'waiting for a runner in the altar'
            yield from execution.delay_ticks(1)
            return
        bot.status = 'waiting for a runner at the ruins'
        here = game.tile()
        ruins = bot.conf.ruins
        if here is not None and ruins.distance_to(here) > 1:
            yield from traversal.walk_resilient(ruins, radius=1, attempts=1, timeout_ms=8000, log=lambda m: bot.log(f'  {m}'))
            return
        yield from execution.delay_ticks(1)


def current_level():
    t = game.tile()
    return t.level if t is not None else 0


# Jungle spiders chase the runner all the way to the store; up the ladder next to Jiminua and straight back down
# drops them.
def shake_aggro_on_ladder(bot):
    """Use with yield from."""
    ground = current_level()
    up = locs.query().name(LADDER).action(CLIMB_UP).nearest()
    if up is None:
        return
    bot.status = 'shaking the jungle spiders off on the ladder'
    climbed = up.interact(CLIMB_UP)
    if climbed:
        climbed = yield from execution.delay_until(lambda: current_level() != ground, 10000)
    if not climbed:
        bot.log('could not climb the store ladder — carrying on')
        return
    yield from execution.delay_ticks(AGGRO_SHAKE_TICKS)
    for _ in range(3):
        # Locs read empty for a tick after a level change, so this may take another try.
        down = locs.query().name(LADDER).action(CLIMB_DOWN).nearest()
        if down is not None and down.interact(CLIMB_DOWN):
            back = yield from execution.delay_until(lambda: current_level() == ground, 10000)
            if back:
                bot.log('waited out the spiders upstairs and came back down')
                yield from execution.delay_ticks(1)
                return
        yield from execution.delay_ticks(2)
    bot.log('stuck up the store ladder — the walker will bring us back down')


# It opens through Talk-to and the first dialogue option, not a Trade option.
def open_unnote_shop(name):
    """Use with yield from."""
    if shop.is_open():
        return True
    # The scene reads empty for a tick or two after the ladder; blank isn't absent.
    yield from execution.delay_until(lambda: npcs.query().name(name).nearest() is not None, 5000)
    npc = npcs.query().name(name).nearest()
    if npc is None:
        return False
    npc.interact('Talk-to')
    for _ in range(10):
        if shop.is_open():
            break
        if len(chat_dialog.options()) > 0:
            yield from chat_dialog.choose_option()
        elif chat_dialog.can_continue():
            yield from chat_dialog.continue_()
        yield from execution.delay_ticks(1)
    return shop.is_open()


# Runner: owns the loop while a trade is open, and until the pack settles after it closes.
class DriveTrade(Task):
    def __init__(self, bot):
        Task.__init__(self, label='drive trade')
        self.bot = bot
        self.pending = 0
        self.before_unnoted = 0
        self.settling = False
        self.settle_from_tick = -1

    def validate(self):
        on = trade.active() or self.settling
        if not on:
            self.bot.set_trade_hot(False)
        return on

    def execute(self):
        bot = self.bot
        bot.set_trade_hot(True)
        if trade.on_confirm_screen():
            self.settling = True
            self.settle_from_tick = -1
            bot.status = 'confirming the trade'
            bot.say(f'confirm-accept {trade_snap()}')
            trade.accept()
            return
        if trade.on_offer_screen():
            if len(trade.my_offer()) > 0:
                bot.status = 'accepting the offer'
                bot.say(f'offer-accept {trade_snap()}')
                trade.accept()
                return
            held = unnoted_essence()
            n = offer_count(held)
            if n <= 0:
                if len(trade.their_offer()) > 0:
                    bot.status = 'taking items back from the master'
                    trade.accept()
                return
            self.pending = n
            self.before_unnoted = held
            self.settling = True
            self.settle_from_tick = -1
            bot.status = 'offering essence'
            bot.say(f'offering {n} ess {trade_snap()}')
            if held <= TRADE_CAP:
                trade.offer_all(ESSENCE, lambda i: i.id == ESSENCE_ID)
            else:
                yield from trade.offer(ESSENCE, n, lambda i: i.id == ESSENCE_ID)
            return
        if self.settling:
            self.finish_settle()

    def reset(self):
        self.pending = 0
        self.settling = False
        self.before_unnoted = 0
        self.settle_from_tick = -1
        self.bot.set_trade_hot(False)

    def finish_settle(self):
        bot = self.bot
        if unnoted_essence() > 0:
            bot.say(f'trade bounced ess back pending={self.pending} before={self.before_unnoted} {trade_snap()}')
            self.reset()
            return
        if self.settle_from_tick < 0:
            self.settle_from_tick = game.tick()
            return
        if game.tick() - self.settle_from_tick < 2:
            return
        if self.pending > 0:
            bot.count_delivery(self.before_unnoted)
            bot.say(f'delivered {self.before_unnoted} ess {trade_snap()}')
        self.reset()


class GoBankPark(Task):
    def __init__(self, bot):
        Task.__init__(self, label='go bank park')
        self.bot = bot

    def validate(self):
        return self.bot.go_bank and not trade.active()

    def execute(self):
        bot = self.bot
        here = game.tile()
        if here is None or bot.conf.runner_bank.distance_to(here) > 4:
            bot.status = 'Go bank: walking to the bank'
            yield from bot.walk_to(bot.conf.runner_bank, 3)
            return
        bot.status = 'parked at the bank — run gobank again to resume'
        yield from execution.delay_ticks(2)


def ground_runner_supplies():
    return ground_items.query().where(lambda g: g.id == COINS_ID or ((g.name or '').lower() == ESSENCE.lower() and g.id != ESSENCE_ID)).within(PICKUP_RANGE).nearest()


class PickupRunnerSupplies(Task):
    def __init__(self, bot):
        Task.__init__(self, label='pickup runner supplies')
        self.bot = bot
        self.fails = 0
        self.blocked_until = 0

    def validate(self):
        return not in_temple() and unnoted_essence() == 0 and not trade.active() and now_ms() >= self.blocked_until and ground_runner_supplies() is not None

    def execute(self):
        bot = self.bot
        drop = ground_runner_supplies()
        if drop is None:
            return
        label = 'coins' if drop.id == COINS_ID else 'noted essence'
        drop_id = drop.id

        def count():
            return sum([i.count for i in inventory.items() if i.id == drop_id])

        bot.status = f'picking up dropped {label}'
        bot.log(f'{label} on the ground ({drop.count}), picking it up')
        before = count()
        if drop.interact('Take'):
            yield from execution.delay_until(lambda: count() > before, 8000)
        if count() > before:
            bot.log(f'picked up {count() - before} {label}')
            self.fails = 0
            return
        # A stack it can't reach or pick up mustn't starve deliveries forever.
        self.fails += 1
        if self.fails >= 3:
            bot.log('could not pick the stack up (full pack? out of reach), ignoring it for a while')
            self.fails = 0
            self.blocked_until = now_ms() + PICKUP_BLOCK_MS
        yield from execution.delay_ticks(2)


class DeliverEssence(Task):
    def __init__(self, bot):
        Task.__init__(self, label='deliver essence')
        self.bot = bot
        self.meeting = False
        self.last_req_key = ''
        self.last_req_at = 0

    def validate(self):
        if unnoted_essence() == 0:
            self.meeting = False
            return False
        return not trade.active()

    def execute(self):
        bot = self.bot
        master_name = bot.partners[0] if len(bot.partners) > 0 else None
        if bot.stay_in_altar and not in_temple():
            bot.status = 'entering the altar to deliver'
            entered = yield from enter_altar(bot)
            if not entered:
                bot.log('could not enter the altar — retrying')
            return
        master = bot.nearest_partner()
        if master is not None:
            self.meeting = True
        if runner_should_walk_to_meet(master is not None, self.meeting, in_temple(), bot.stay_in_altar):
            bot.status = f'walking to {master_name}'
            yield from bot.walk_to(bot.conf.ruins, 2)
            return
        if master is None:
            bot.status = f'waiting for {master_name} — holding the essence'
            yield from execution.delay_ticks(1)
            return
        if not runner_should_request_trade(trade.active(), self.last_req_at, now_ms()):
            yield from execution.delay_ticks(1)
            return
        bot.status = f'requesting a trade with {master.name}'
        key = f'{master.name}:{master.distance()}:{unnoted_essence()}'
        if key != self.last_req_key or now_ms() - self.last_req_at > 8000:
            self.last_req_key = key
            bot.say(f"Trade-with '{master.name}' d={master.distance()} {trade_snap()}")
        self.last_req_at = now_ms()
        trade.request(master.name or '')
        if trade.active():
            bot.set_trade_hot(True)
            return
        yield from execution.delay_ticks(1)


class ExitAltarForRestock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='exit altar for restock')
        self.bot = bot

    def validate(self):
        return self.bot.stay_in_altar and in_temple() and runner_may_leave_altar(trade.active(), unnoted_essence())

    def execute(self):
        self.bot.say(f'leaving altar after delivery {trade_snap()}')
        yield from portal_out(self.bot)
        self.bot.load_delivered = False


def shop_ess_stock():
    for s in shop.stock():
        if (s.name or '').lower() == ESSENCE.lower():
            return s.count
    return 0


class UnNoteEssence(Task):
    def __init__(self, bot):
        Task.__init__(self, label='un-note essence')
        self.bot = bot
        self.last_shake_at = 0

    def validate(self):
        return (self.bot.conf.unnote_npc is not None and not in_temple() and not trade.active() and noted_essence() > 0 and unnoted_essence() == 0
                and inventory.count(COINS) >= LOW_COINS)

    def execute(self):
        bot = self.bot
        conf = bot.conf
        bot.status = 'topping up unnoted essence at the store'
        yield from bot.walk_to(conf.unnote_tile, 3)
        # One ladder trip per arrival; a store visit tried again doesn't climb again.
        if now_ms() - self.last_shake_at > SHAKE_COOLDOWN_MS:
            yield from shake_aggro_on_ladder(bot)
            self.last_shake_at = now_ms()
        opened = yield from open_unnote_shop(conf.unnote_npc)
        if not opened:
            bot.log(f"couldn't open {conf.unnote_npc}'s store — retrying")
            return
        for _ in range(STORE_PASSES):
            stock = shop_ess_stock()
            op, n = plan_store_step(stock, noted_essence(), unnoted_essence())
            if op == 'done':
                break
            noted_before = noted_essence()
            unnoted_before = unnoted_essence()
            if op == 'sell':
                bot.log(f'selling {n} noted essence to {conf.unnote_npc} (stock {stock})')
                yield from shop.sell(ESSENCE, n, lambda i: i.id != ESSENCE_ID)
            else:
                bot.log(f'buying {n} essence from stock ({stock} in the shop)')
                yield from shop.buy(ESSENCE, n)
            if noted_essence() == noted_before and unnoted_essence() == unnoted_before:
                bot.log('store pass made no progress (out of coins or raced) — leaving with what we have')
                break
        yield from shop.close()
        bot.log(f'store visit done: {unnoted_essence()} unnoted held (noted left: {noted_essence()})')


class BankRestock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank restock')
        self.bot = bot
        self.empty_reads = 0

    # Coins only matter on the noting route, for fares and buy-backs; the short route spends none.
    def validate(self):
        return ess_count() == 0 or (self.bot.conf.unnote_npc is not None and inventory.count(COINS) < LOW_COINS)

    def execute(self):
        bot = self.bot
        conf = bot.conf
        bot.status = 'restocking at the bank'
        yield from bot.walk_to(conf.runner_bank, 3)
        opened = yield from bank.open_booth(conf.runner_bank, BOOTH_NAME, BOOTH_OP)
        if not opened:
            opened = yield from bank.open_nearest(BOOTH_NAME, BOOTH_OP)
        if not opened:
            bot.log('could not open the bank — retrying')
            return
        yield from bank.set_note_mode(False)
        # Random events hand out items that take the slots essence needs, so anything unrelated goes.
        keep = [ESSENCE]
        if conf.unnote_npc:
            keep.append(COINS)
        if bot.stay_in_altar:
            keep.append(conf.talisman)
        before = inventory.used()
        yield from bank.deposit_all_matching(deposit_all_except(keep))
        if inventory.used() < before:
            bot.log(f'banked {before - inventory.used()} slot(s) of random-event litter')
        # Blank isn't empty: the list reads [] for a moment after opening and after a deposit, and one stale read
        # here used to stop a runner with thousands of essence banked.
        yield from execution.delay_until(bank.loaded, 3000)
        if conf.unnote_npc:
            need_coins = bot.coins_target - inventory.count(COINS)
            if need_coins > 0 and bank.count(COINS) > 0:
                yield from bank.withdraw_x(COINS, min(need_coins, bank.count(COINS)))
            if inventory.count(COINS) < LOW_COINS and bank.loaded():
                bot.request_finish('NatureCrafter runner: out of coins (bank + pack) for fares and buy-backs')
                return
        banked = bank.count(ESSENCE)
        if banked == 0:
            # It believes an empty bank only after three restocks read it empty.
            self.empty_reads += 1
            if ess_count() == 0 and self.empty_reads >= 3:
                bot.request_finish('NatureCrafter runner: out of Rune essence in the bank (three reads)')
            return
        self.empty_reads = 0
        per = bot.ess_per
        if not conf.unnote_npc:
            yield from bank.withdraw_x(ESSENCE, short_route_withdraw(per, banked, inventory.free()))
            yield from execution.delay_until(lambda: ess_count() > 0, 3000)
            bot.log(f'withdrew {ess_count()} unnoted essence for the run')
            return
        want = min(per, banked) if per > 0 else banked
        yield from bank.set_note_mode(True)
        yield from bank.withdraw_x(ESSENCE, want)
        yield from execution.delay_until(lambda: ess_count() > 0, 3000)
        yield from bank.set_note_mode(False)
        bot.log(f"withdrew {ess_count()} essence ({'noted' if noted_essence() > 0 else 'unnoted'}) + coins topped to {inventory.count(COINS)}")


class NatureCrafter(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.go_bank = False
        self.crafted = 0
        self.received = 0
        self.trades = 0
        self.last_requester = None
        self.last_ask_at = 0
        self.last_accept_at = 0
        self.handshake_hold_until = 0
        self.load_delivered = False
        self.status = 'starting'
        self.started_at = time.time()
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        s = self.settings
        self.mode = s.str('mode', 'Master')
        self.rune = s.str('rune', DEFAULT_RUNE)
        self.conf = RUNES.get(self.rune) or RUNES[DEFAULT_RUNE]
        self.partners = [p.strip() for p in s.str('partner', '').split(',') if p.strip()]
        self.bank_ms = max(0, s.num('bank_every', 60)) * 60000
        self.ess_per = max(0, s.num('withdraw_ess', 0))
        self.coins_target = coin_target_for(s.num('withdraw_coins', 10000))
        self.stay_in_altar = s.bool('stay_in_altar', False)
        self.next_bank_at = now_ms() + self.bank_ms
        self.xp_at_start = skills.xp('runecraft')
        # Why: rs2b0t's paint has a Go bank button that parks a runner at the bank; this is its command.
        self.command('gobank', self.toggle_go_bank, help='park the runner at the bank, or resume')
        if len(self.partners) == 0:
            who = 'the runner needs the master name' if self.mode == 'Runner' else 'the master only trades with configured runners'
            self.log(f'NatureCrafter: no partner names set — {who}. Stopping.')
            raise RuntimeError('NatureCrafter: no partner configured')
        conf = self.conf
        if self.mode == 'Runner':
            if self.stay_in_altar:
                yield from execution.delay_until(lambda: inventory.first(conf.talisman) is not None, 3000)
                if inventory.first(conf.talisman) is None:
                    self.request_finish('NatureCrafter runner: stay-in-altar needs a talisman in the pack')
                    return
            route = f'via the bank + ship + {conf.unnote_npc}' if conf.unnote_npc else 'straight from the bank (unnoted)'
            staying = ', staying in the altar' if self.stay_in_altar else ''
            self.log(f"NatureCrafter runner starting — ferrying essence for {self.rune} to [{', '.join(self.partners)}] {route}{staying}")
            tasks = [DriveTrade(self), ContinueDialog(), DropLitter(self, False), GoBankPark(self)]
            if conf.unnote_npc:
                tasks.append(PickupRunnerSupplies(self))
            tasks.extend([DeliverEssence(self), ExitAltarForRestock(self)])
            if conf.unnote_npc:
                tasks.append(UnNoteEssence(self))
            tasks.append(BankRestock(self))
            self.add(*tasks)
            return
        if skills.level('runecraft') < conf.level:
            self.log(f"NatureCrafter: Runecrafting {conf.level} required for {self.rune} (have {skills.level('runecraft')}) — stopping.")
            raise RuntimeError('NatureCrafter: runecrafting level too low')
        self.on('chat_message', self.heard)
        banking_note = f'banking everything every {round(self.bank_ms / 60000)}min' if self.bank_ms > 0 else 'never banking'
        staying = ', staying in the altar' if self.stay_in_altar else ''
        self.log(f"NatureCrafter master starting — {self.rune} at {conf.ruins}, accepting essence from [{', '.join(self.partners)}], {banking_note}{staying}")
        self.add(HandleOpenTrade(self), ContinueDialog(), DropLitter(self, True), CraftNatures(self), AcceptRunner(self), ExitTemple(self), BankEverything(self),
                 EnterAltar(self), WaitForRunner(self))

    def heard(self, e):
        if e.type != 'trade_request' or not e.username or TRADE_REQ_TEXT not in (e.text or '').lower() or not self.is_partner(e.username):
            return
        stale = self.last_ask_at <= self.last_accept_at
        if (self.last_requester or '').lower() != e.username.lower() or stale:
            self.say(f'trade-ask from {e.username}')
        self.last_requester = e.username
        self.last_ask_at = now_ms()

    def toggle_go_bank(self, cmd):
        self.go_bank = not self.go_bank
        self.log('Go bank pressed — heading to the bank to park' if self.go_bank else 'Resume pressed — back to the loop')

    def say(self, msg):
        self.log(f"{'runner' if self.mode == 'Runner' else 'master'}: {msg}")

    # A trade is driven every frame while it's open.
    def set_trade_hot(self, on):
        self.loop_cadence = {'kind': 'frame'} if on else None

    def keep_list(self, keep_product_rune):
        return keep_names(self.conf.talisman, self.conf.rune if keep_product_rune else None)

    def count_trade(self, essence):
        self.trades += 1
        self.received += essence

    def count_delivery(self, essence):
        self.count_trade(essence)
        self.load_delivered = True

    def bank_trip_due(self):
        return self.bank_ms > 0 and now_ms() >= self.next_bank_at

    def mark_bank_done(self):
        self.next_bank_at = now_ms() + self.bank_ms

    def is_partner(self, name):
        return name is not None and len([p for p in self.partners if p.lower() == name.lower()]) > 0

    def nearest_partner(self):
        return players.query().name(*self.partners).nearest()

    def adjacent_runner(self):
        return players.query().name(*self.partners).within(TRADE_ADJACENT).nearest()

    def runner_named(self, name, within):
        return players.query().name(name).within(within).nearest()

    def mark_handshake_started(self):
        self.last_accept_at = now_ms()
        self.handshake_hold_until = now_ms() + MASTER_HANDSHAKE_MS

    def trade_target(self):
        asked = self.last_requester
        asked_here = asked is not None and self.runner_named(asked, TRADE_ADJACENT) is not None
        return master_pick_trade_target(asked, self.last_ask_at, self.last_accept_at, asked_here, self.handshake_hold_until, now_ms())

    def walk_to(self, dest, radius=2):
        """Use with yield from."""
        here = game.tile()
        if here is not None and dest.distance_to(here) <= radius:
            return
        store = self.conf.unnote_tile
        if store is not None and spider_safe_via(here, dest, store, self.conf.ruins):
            self.log(f'via spider-safe tile {SPIDER_SAFE.x},{SPIDER_SAFE.z}')
            yield from traversal.walk_resilient(SPIDER_SAFE, radius=3, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))
        yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))

    def on_progress_report(self):
        if self.mode == 'Runner':
            return {'Status': self.status, 'Mode': 'Runner', 'To': ', '.join(self.partners), 'Delivered': self.received, 'Trades': self.trades,
                    'Unnoted': unnoted_essence(), 'Noted': noted_essence(), 'Coins': inventory.count(COINS)}
        return {'Status': self.status, 'Mode': 'Master', 'Crafted': self.crafted, 'Received': self.received, 'Trades': self.trades,
                'Runecraft xp': skills.xp('runecraft') - self.xp_at_start, 'Pack ess': ess_count()}


BOT = define_bot(
    name='NatureCrafter',
    create=NatureCrafter,
    description='Master Nature Crafter — a master stands at the nature altar (Karamja), takes essence from configured runners via trade, and crafts natures; runners bank essence at Ardougne, un-note it at the general store, and ship it to the master. Mode + partner name(s) via settings',
    category='Runecrafting',
    tags=['runecrafting', 'nature', 'trade', 'master', 'runner', 'karamja'],
    settings_schema=SETTINGS,
)

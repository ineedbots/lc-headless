# Crafts air or earth runes from banked essence, solo or as a team: a runner ferries essence into the altar and
# trades it to a Mule Recipient camped beside the altar: rs2b0t's RuneCrafter (MIT, see thirdparty/rs2b0t).

import time

from rs2004.catalogs import ContinueDialog

ESSENCE = 'Rune essence'
# Unnoted essence; the bank-note variant has a different id.
ESSENCE_ID = 1436
RUINS = 'Mysterious ruins'
ALTAR_NAME = 'Altar'
ALTAR_OP = 'Craft-rune'
PORTAL_NAME = 'Portal'
PORTAL_OP = 'Use'
BOOTH_NAME = 'Bank booth'
BOOTH_OP = 'Use-quickly'
# Altar temples sit around z 4800; the overworld is below 4000.
TEMPLE_Z = 4000
MAX_BANK_FAILS = 6
MAX_ENTER_FAILS = 3
# The Mule Recipient holds a talisman and one stacking rune slot, so 26 slots take essence.
TRADE_LOAD = 26
# A trade nobody puts essence into is declined after this.
EMPTY_TRADE_MS = 20000
# Trading a player walks to them, so the recipient only answers a runner that already came to it.
ADJACENT = 2
# The runner lands at the temple's entrance, a walk from the altar.
TEMPLE_RANGE = 30
# The recipient camps this close to the altar, so every runner finds it there.
ALTAR_PARK = 2


class RuneType:
    def __init__(self, talisman, rune, level, ruins, bank):
        self.talisman = talisman
        self.rune = rune
        self.level = level
        # The Mysterious ruins: walk here and use the talisman.
        self.ruins = ruins
        self.bank = bank


RUNES = {
    'Air runes': RuneType('Air talisman', 'Air rune', 1, Tile(2988, 3294, 0), Tile(3013, 3355, 0)),
    'Earth runes': RuneType('Earth talisman', 'Earth rune', 9, Tile(3303, 3477, 0), Tile(3253, 3420, 0)),
}
RUNE_OPTIONS = list(RUNES)
MODE_SOLO = 'Solo'
MODE_RUNNER = 'Runner'
MODE_RECIPIENT = 'Mule Recipient'
MODES = [MODE_SOLO, MODE_RUNNER, MODE_RECIPIENT]

SETTINGS = {
    'rune': SettingDef('string', 'Air runes', 'Rune', options=RUNE_OPTIONS,
                       help='which rune to craft — Air is the ruins south of Falador (Falador East bank), Earth is north-east of Varrock (Varrock East bank)'),
    'mode': SettingDef('string', MODE_SOLO, 'Mode', options=MODES,
                       help='Solo banks its own essence. A Runner needs its own talisman: it banks essence, enters the altar and hands the load over inside. The Mule Recipient camps next to the altar and never leaves — it takes every essence trade and crafts between them'),
    'partner': SettingDef('string', '', 'Trade essence to (IGN)', help='the Mule Recipient this runner delivers essence to',
                          show_if={'key': 'mode', 'any_of': [MODE_RUNNER]}),
}


def in_temple():
    here = game.tile()
    return here is not None and here.z > TEMPLE_Z


# Only unnoted essence counts; notes can't be crafted or handed on.
def ess_count():
    return sum([i.count for i in inventory.items() if i.id == ESSENCE_ID])


# Everything else, nameless cache misses included, takes an essence slot and is junk.
def pack_junk(keep):
    kept = [k.lower() for k in keep]
    return [i for i in inventory.items() if (i.name or '').lower() not in kept]


# Chat names may use non-breaking spaces or underscores where entities use spaces.
def clean_name(s):
    return s.lower().replace(' ', ' ').replace('_', ' ').strip()


def same_name(a, b):
    return clean_name(a) == clean_name(b)


def player_named(name, within):
    return players.query().where(lambda p: p.name is not None and same_name(p.name, name)).within(within).nearest()


def item_label(i):
    return f"{i.name or 'unnamed'}#{i.id}"


# Why: a short or over load makes a runner deliver 1 essence and waste a trade slot the recipient could have spent
# on a full delivery.
def runner_loaded(bot):
    """The pack holds the altar's talisman and one recipient load."""
    return inventory.contains(bot.cfg.talisman) and ess_count() == TRADE_LOAD and len(pack_junk([bot.cfg.talisman, ESSENCE])) == 0


def altar_loc():
    return locs.query().name(ALTAR_NAME).action(ALTAR_OP).nearest()


def open_bank(bot):
    """Use with yield from."""
    def log(m):
        bot.log(f'  {m}')

    yield from bot.walk_to(bot.cfg.bank, 3)
    opened = yield from bank.open_booth(bot.cfg.bank, BOOTH_NAME, BOOTH_OP)
    if not opened:
        opened = yield from bank.open_nearest(BOOTH_NAME, BOOTH_OP)
    if opened:
        bot.bank_fails = 0
        return True
    bot.bank_fails += 1
    if bot.bank_fails >= MAX_BANK_FAILS:
        bot.request_finish("RuneCrafter: couldn't reach the bank — start nearer it")
        return False
    log('could not open the bank — will retry')
    return False


def clean_pack(bot, keep):
    """Deposits everything off the keep list, then proves it worked: a stack that won't deposit shrinks every load
    from then on, so it stops the script instead. Use with yield from."""
    kept = [k.lower() for k in keep]
    matches = lambda name, *_args: name.lower() not in kept
    yield from bank.set_note_mode(False)
    yield from bank.deposit_all_matching(matches)
    yield from execution.delay_ticks(1)
    if len(pack_junk(keep)) > 0:
        # One more pass before calling it stuck: a click that landed late still shows in the side pack.
        yield from bank.deposit_all_matching(matches)
        yield from execution.delay_until(lambda: len(pack_junk(keep)) == 0, 2500)
    left = pack_junk(keep)
    if len(left) > 0:
        bot.request_finish(f"RuneCrafter: {len(left)} item(s) would not deposit ({', '.join([item_label(i) for i in left])}) — the pack must hold only {' + '.join(keep)}")
        return False
    return True


def ensure_talisman(bot):
    """Use with yield from."""
    talisman = bot.cfg.talisman
    if inventory.contains(talisman):
        return True
    # Blank isn't empty: the bank's list reads [] for a moment after it opens.
    yield from execution.delay_until(bank.loaded, 3000)
    found = [i for i in bank.items() if (i.name or '').lower() == talisman.lower()]
    if len(found) == 0:
        bot.request_finish(f'RuneCrafter: no {talisman} in the bank or pack')
        return False
    ops = found[0].actions()
    op = withdraw_op(ops, '1') or withdraw_op(ops, 'any') or 'Withdraw-1'
    bank.withdraw(talisman, op)
    landed = yield from execution.delay_until(lambda: inventory.contains(talisman), 3000)
    if not landed:
        bot.request_finish(f'RuneCrafter: the {talisman} withdraw never landed')
        return False
    bot.log(f'withdrew a {talisman}')
    return True


def take_portal(bot):
    portal = locs.query().name(PORTAL_NAME).action(PORTAL_OP).nearest()
    if portal is not None:
        portal.interact(PORTAL_OP)


class Craft(Task):
    def __init__(self, bot, then_exit):
        Task.__init__(self, label='craft')
        self.bot = bot
        self.then_exit = then_exit

    def validate(self):
        return in_temple() and ess_count() > 0

    def execute(self):
        bot = self.bot
        altar = altar_loc()
        if altar is None:
            # The scene is still syncing after the teleport.
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
        bot.log(f'crafted {made} {bot.cfg.rune}s')
        # The recipient lives here, parked at the altar.
        if not self.then_exit:
            return
        # Why: the craft locks the player for a moment and pops a level-up, so a tight loop closes any dialog and
        # clicks the portal every tick, and the Use fires as soon as the lock clears.
        bot.status = 'taking the portal out'
        bot.log('taking the portal back to the ruins')
        for _ in range(15):
            if not in_temple():
                break
            if chat_dialog.can_continue():
                yield from chat_dialog.continue_()
                continue
            take_portal(bot)
            yield from execution.delay_ticks(1)
        if not in_temple():
            bot.log('back at the mysterious ruins')


class Exit(Task):
    def __init__(self, bot):
        Task.__init__(self, label='exit')
        self.bot = bot

    def validate(self):
        return in_temple() and ess_count() == 0

    def execute(self):
        bot = self.bot
        portal = locs.query().name(PORTAL_NAME).action(PORTAL_OP).nearest()
        if portal is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = 'taking the portal out'
        bot.log('taking the portal back to the ruins')
        if not portal.interact(PORTAL_OP):
            yield from execution.delay_ticks(2)
            return
        out = yield from execution.delay_until(lambda: not in_temple(), 15000)
        if out:
            bot.log('back at the mysterious ruins')


class BankTrip(Task):
    def __init__(self, bot):
        Task.__init__(self, label='bank trip')
        self.bot = bot

    def validate(self):
        return not in_temple() and ess_count() == 0

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        bot.log('heading to the bank')
        opened = yield from open_bank(bot)
        if not opened:
            return
        made_runes = inventory.count(bot.cfg.rune)
        cleaned = yield from clean_pack(bot, [bot.cfg.talisman])
        if not cleaned:
            return
        bot.trips += 1
        if made_runes > 0:
            bot.log(f'deposited {made_runes} {bot.cfg.rune}s')
        has_talisman = yield from ensure_talisman(bot)
        if not has_talisman:
            return
        if bank.count(ESSENCE) == 0:
            bot.request_finish('RuneCrafter: out of Rune essence in the bank')
            return
        ess = [i for i in bank.items() if (i.name or '').lower() == ESSENCE.lower()]
        op = (withdraw_op(ess[0].actions(), 'all') if len(ess) > 0 else None) or 'Withdraw-All'
        bank.withdraw(ESSENCE, op)
        yield from execution.delay_until(lambda: ess_count() > 0 or bank.count(ESSENCE) == 0, 4000)
        bot.log(f'withdrew {ess_count()} rune essence (trip {bot.trips})')


# Solo and Runner enter with a load of essence; the recipient enters once and stays.
class Enter(Task):
    def __init__(self, bot, ready):
        Task.__init__(self, label='enter')
        self.bot = bot
        self.ready = ready
        self.fails = 0

    def validate(self):
        return not in_temple() and self.ready()

    def execute(self):
        bot = self.bot
        bot.status = 'heading to the ruins'
        bot.log('heading to the mysterious ruins')
        yield from bot.walk_to(bot.cfg.ruins, 1)
        ruins = locs.query().name(RUINS).nearest()
        talisman = inventory.first(bot.cfg.talisman)
        if talisman is None:
            bot.request_finish(f"RuneCrafter: no {bot.cfg.talisman} in the pack — the altar can't be entered without one")
            return
        if ruins is None:
            yield from execution.delay_ticks(2)
            return
        bot.status = 'entering the altar'
        bot.log(f'using the {bot.cfg.talisman} on the mysterious ruins')
        if not talisman.use_on(ruins):
            yield from execution.delay_ticks(2)
            return
        entered = yield from execution.delay_until(in_temple, 10000)
        if entered:
            bot.log('entered the altar')
            self.fails = 0
            return
        self.fails += 1
        if self.fails >= MAX_ENTER_FAILS:
            bot.request_finish("RuneCrafter: the talisman didn't teleport into the altar")


# Runner: owns the loop while a trade is open, and never moves, since moving closes it.
class RunnerTrade(Task):
    def __init__(self, bot):
        Task.__init__(self, label='runner trade')
        self.bot = bot
        self.before = 0

    def validate(self):
        return trade.active()

    def execute(self):
        bot = self.bot
        if trade.on_confirm_screen():
            bot.status = 'confirming the delivery'
            trade.accept()
            closed = yield from execution.delay_until(lambda: not trade.active(), 3000)
            if closed:
                delivered = self.before - ess_count()
                if delivered > 0:
                    bot.count_trade(delivered)
                    bot.log(f'delivered {delivered} essence to {bot.partner}')
                self.before = 0
            return
        if len(trade.my_offer()) == 0:
            held = ess_count()
            if held <= 0:
                yield from execution.delay_ticks(1)
                return
            self.before = held
            bot.status = 'offering essence'
            if held <= TRADE_LOAD:
                trade.offer_all(ESSENCE, lambda i: i.id == ESSENCE_ID)
            else:
                # An over-stocked pack: the recipient only has TRADE_LOAD free slots, and more blocks the trade.
                yield from trade.offer(ESSENCE, TRADE_LOAD, lambda i: i.id == ESSENCE_ID)
        else:
            bot.status = 'accepting the delivery'
            trade.accept()


# Runner: inside the altar with a load. The recipient is parked at the altar, so it walks there.
class RunnerDeliver(Task):
    def __init__(self, bot):
        Task.__init__(self, label='runner deliver')
        self.bot = bot

    def validate(self):
        return in_temple() and ess_count() > 0 and not trade.active()

    def execute(self):
        bot = self.bot
        partner = bot.partner
        master = player_named(partner, TEMPLE_RANGE)
        if master is None:
            bot.status = f'looking for {partner} at the altar'
            altar = altar_loc()
            if altar is not None:
                yield from direct_navigator.walk_to(altar.tile(), ALTAR_PARK + 1, 10000)
            yield from execution.delay_ticks(2)
            return
        # Why: a busy recipient drops the request server-side, and answering the runner's latest request is how the
        # recipient opens the trade, so it keeps asking.
        bot.status = f'delivering to {partner}'
        bot.log(f'requesting a trade with {master.name}')
        trade.request(master.name or partner)
        yield from execution.delay_until(trade.active, 4000)


class RunnerRestock(Task):
    def __init__(self, bot):
        Task.__init__(self, label='runner restock')
        self.bot = bot
        self.empty_reads = 0
        # One withdraw per run, so a drained bank doesn't shuttle the same short load forever.
        self.stocked = False

    def validate(self):
        if ess_count() == 0:
            self.stocked = False
        return not in_temple() and not trade.active() and not self.stocked and not runner_loaded(self.bot)

    def execute(self):
        bot = self.bot
        bot.status = 'restocking essence'
        opened = yield from open_bank(bot)
        if not opened:
            return
        # Why: only the talisman stays; junk, the noted essence the bank hands back, and leftovers from the last
        # delivery all go, so the run starts on one full load instead of a dribble the recipient waited for.
        cleaned = yield from clean_pack(bot, [bot.cfg.talisman])
        if not cleaned:
            return
        has_talisman = yield from ensure_talisman(bot)
        if not has_talisman:
            return
        # Blank isn't empty: the list reads [] for a moment after opening, so it believes it on the third read.
        yield from execution.delay_until(bank.loaded, 3000)
        banked = bank.count(ESSENCE)
        if banked == 0:
            self.empty_reads += 1
            if self.empty_reads >= 3:
                bot.request_finish('RuneCrafter: out of Rune essence in the bank (three reads)')
            return
        self.empty_reads = 0
        yield from bank.withdraw_x(ESSENCE, min(TRADE_LOAD, banked, inventory.free()))
        # A withdraw that never landed retries.
        self.stocked = yield from execution.delay_until(lambda: ess_count() > 0, 3000)
        bot.trips += 1
        bot.log(f'withdrew {ess_count()} essence (bank run {bot.trips})')


# Mule Recipient: takes whatever essence an open trade offers, giving nothing away.
class MuleTakeTrade(Task):
    def __init__(self, bot):
        Task.__init__(self, label='mule take trade')
        self.bot = bot
        self.opened_at = 0

    def validate(self):
        if not trade.active():
            self.opened_at = 0
            return False
        if self.opened_at == 0:
            self.opened_at = time.time()
        return True

    def execute(self):
        bot = self.bot
        # Anything recorded before this trade opened is stale now.
        bot.take_requester()
        if trade.on_confirm_screen():
            bot.status = 'confirming the essence trade'
            before = ess_count()
            trade.accept()
            closed = yield from execution.delay_until(lambda: not trade.active(), 3000)
            if closed and ess_count() > before:
                bot.count_trade(ess_count() - before)
                bot.log(f'received {ess_count() - before} essence')
            return
        if len(trade.my_offer()) > 0:
            bot.log('safety: something is in MY trade offer — declining so nothing is given away')
            yield from trade.decline()
            return
        theirs = sum([max(1, o.count) for o in trade.their_offer() if (o.name or '').lower() == ESSENCE.lower()])
        if theirs <= 0:
            if (time.time() - self.opened_at) * 1000 > EMPTY_TRADE_MS:
                bot.log('trade partner never offered essence — declining so waiting runners get served')
                yield from trade.decline()
                return
            bot.status = 'waiting for the essence offer'
            yield from execution.delay_ticks(1)
            return
        if theirs > inventory.free():
            # Junk in the pack, from a random event: the window has to close before MuleDropJunk can drop it.
            bot.log(f"can't fit {theirs} essence ({inventory.free()} slots free) — declining so the pack can be cleared first")
            yield from trade.decline()
            return
        bot.status = f'accepting {theirs} essence'
        trade.accept()


class MuleAnswerRequest(Task):
    def __init__(self, bot):
        Task.__init__(self, label='mule answer request')
        self.bot = bot

    def validate(self):
        return in_temple() and not trade.active() and self.bot.last_requester is not None

    def execute(self):
        bot = self.bot
        name = bot.take_requester()
        if not name:
            return
        # Never chases: trading walks to the target, and a recipient that wanders off the altar is one every other
        # runner then has to hunt for.
        came = yield from execution.delay_until(lambda: player_named(name, ADJACENT) is not None, 1800)
        runner = player_named(name, ADJACENT) if came else None
        if runner is None:
            bot.log(f"'{name}' asked to trade but never reached the altar — waiting for the next request")
            return
        # Trading the requester back is what opens the window: both sides trade each other.
        bot.status = f"answering {runner.name}'s trade request"
        bot.log(f"answering {runner.name}'s trade request")
        trade.request(runner.name or name)
        yield from execution.delay_until(trade.active, 4000)


# Why: a random event hands the recipient an item, and that one slot decides whether a 26-essence delivery fits or
# every trade is declined. The junk goes on the floor, since leaving for a bank strands every runner at the altar.
class MuleDropJunk(Task):
    """Drops the recipient's junk that would block a full delivery."""

    def __init__(self, bot):
        Task.__init__(self, label='mule drop junk')
        self.bot = bot

    # Essence is payload, and a delivery can land between two loops.
    def junk(self):
        return pack_junk(self.bot.mule_keep() + [ESSENCE])

    def validate(self):
        return in_temple() and not trade.active() and len(self.junk()) > 0

    def execute(self):
        bot = self.bot
        bot.status = 'dropping random-event junk'
        for _ in range(28):
            junk = self.junk()
            if len(junk) == 0:
                break
            item = junk[0]
            bot.log(f"dropping {item.name or f'item#{item.id}'} — it blocks a full essence delivery")
            before = inventory.used()
            if not item.interact('Drop'):
                yield from execution.delay_ticks(1)
                return
            yield from execution.delay_until(lambda: inventory.used() < before, 3000)
        left = self.junk()
        # Junk that won't drop would loop here while runners pile up outside.
        if len(left) > 0:
            bot.request_finish(f"RuneCrafter: could not drop {', '.join([item_label(i) for i in left])} — it keeps blocking essence deliveries")


# Banks anything besides the talisman and runes before a 26-essence trade.
class MulePrepare(Task):
    def __init__(self, bot):
        Task.__init__(self, label='mule prepare')
        self.bot = bot

    def validate(self):
        bot = self.bot
        return not in_temple() and not trade.active() and ess_count() == 0 and (len(pack_junk(bot.mule_keep())) > 0 or not inventory.contains(bot.cfg.talisman))

    def execute(self):
        bot = self.bot
        bot.status = 'cleaning the pack at the bank'
        bot.log('bank trip — the pack needs just the talisman (+ the rune stack) to take trades')
        opened = yield from open_bank(bot)
        if not opened:
            return
        cleaned = yield from clean_pack(bot, bot.mule_keep())
        if not cleaned:
            return
        has_talisman = yield from ensure_talisman(bot)
        if not has_talisman:
            return
        bot.log('pack is clean — heading back to the altar')


# The recipient stays at the altar; runners come to it.
class MuleWait(Task):
    def __init__(self, bot):
        Task.__init__(self, label='mule wait')
        self.bot = bot

    def validate(self):
        return in_temple() and ess_count() == 0

    def execute(self):
        bot = self.bot
        altar = altar_loc()
        if altar is not None and altar.distance() > ALTAR_PARK:
            bot.status = 'parking at the altar'
            bot.log('taking up station next to the altar')
            yield from direct_navigator.walk_to(altar.tile(), ALTAR_PARK, 15000)
            return
        bot.status = 'waiting for a trade request'
        yield from execution.delay_ticks(2)


class RuneCrafter(TaskBot):
    def on_start(self):
        self.loop_delay = 600
        self.last_requester = None
        self.trips = 0
        self.crafted = 0
        self.trades = 0
        self.moved = 0
        self.bank_fails = 0
        self.status = 'starting'
        self.started_at = time.time()
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.choice = self.settings.str('rune', 'Air runes')
        self.cfg = RUNES.get(self.choice) or RUNES['Air runes']
        self.mode = self.settings.str('mode', MODE_SOLO)
        self.partner = self.settings.str('partner', '').strip()
        self.xp_at_start = skills.xp('runecraft')

        if self.mode == MODE_RUNNER:
            if not self.partner:
                self.log("RuneCrafter: Runner mode needs the Mule Recipient's name in settings. Stopping.")
                raise ValueError('RuneCrafter: no trade partner configured')
            self.log(f"RuneCrafter runner starting — ferrying essence from {self.cfg.bank} into the {self.choice} altar for '{self.partner}' (needs an {self.cfg.talisman})")
            self.add(ContinueDialog(), RunnerTrade(self), RunnerDeliver(self), Exit(self), RunnerRestock(self), Enter(self, lambda: ess_count() > 0))
            return

        if skills.level('runecraft') < self.cfg.level:
            self.log(f"RuneCrafter: Runecrafting {self.cfg.level} required for {self.choice} (have {skills.level('runecraft')}) — stopping.")
            raise ValueError('RuneCrafter: runecrafting level too low')

        if self.mode == MODE_RECIPIENT:
            self.on('chat_message', self.heard)
            self.log(f'RuneCrafter mule recipient starting — camping inside the {self.choice} altar, crafting whatever essence gets traded in')
            self.add(ContinueDialog(), MuleTakeTrade(self), Craft(self, False), MuleDropJunk(self), MuleAnswerRequest(self), MuleWait(self), MulePrepare(self), Enter(self, lambda: True))
            return

        self.log(f'RuneCrafter starting — {self.choice}, ruins {self.cfg.ruins}, bank {self.cfg.bank}')
        self.add(ContinueDialog(), Craft(self, True), Exit(self), BankTrip(self), Enter(self, lambda: ess_count() > 0))

    def heard(self, e):
        # The most recent wins: that runner is still waiting.
        if e.type == 'trade_request' and e.username:
            self.last_requester = e.username

    def count_trade(self, essence):
        self.trades += 1
        self.moved += essence

    def take_requester(self):
        name = self.last_requester
        self.last_requester = None
        return name

    # The recipient keeps the runes it crafts (one stack); everyone else banks them.
    def mule_keep(self):
        return [self.cfg.talisman, self.cfg.rune]

    def walk_to(self, dest, radius=2):
        """Use with yield from."""
        here = game.tile()
        if here is not None and dest.distance_to(here) <= radius:
            return
        yield from traversal.walk_resilient(dest, radius=radius, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))

    def on_progress_report(self):
        if self.mode == MODE_RUNNER:
            return {'Status': self.status, 'To': self.partner, 'Bank runs': self.trips, 'Delivered': self.moved, 'Trades': self.trades, 'Pack ess': ess_count()}
        minutes = (time.time() - self.started_at) / 60
        gained = skills.xp('runecraft') - self.xp_at_start
        report = {'Status': self.status, 'Mode': self.mode, 'RC lvl': skills.level('runecraft'), 'Runecraft xp': gained,
                  'XP/hr': f'{gained / minutes * 60 / 1000:.1f}k' if minutes > 0.5 else '—', self.choice: self.crafted, 'Pack ess': ess_count()}
        if self.mode == MODE_SOLO:
            report['Trips'] = self.trips
        else:
            report['Ess in'] = self.moved
        return report


BOT = define_bot(
    name='RuneCrafter',
    create=RuneCrafter,
    description='AIO Runecrafting (Air/Earth) — Solo banks its own essence and crafts at the altar; a Runner needs its own talisman and carries a full 26-essence load into the altar; the Mule Recipient camps next to the altar, never leaves, and crafts between the deliveries runners bring it',
    category='Runecrafting',
    tags=['runecrafting', 'banking', 'trade', 'runner', 'mule', 'afk'],
    settings_schema=SETTINGS,
)

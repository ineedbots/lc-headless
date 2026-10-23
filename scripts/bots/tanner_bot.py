# Tans hides at Al Kharid: banks them, tans the load in one click at the Tanner, and every Nth trip keeps a slot
# free to buy out Dommik's thread. rs2b0t's TannerBot (MIT, see thirdparty/rs2b0t).

TANNER_NAME = 'Tanner'
TANNER_STAND = Tile(3277, 3191, 0)
BANK_STAND = Tile(3269, 3167, 0)
DOMMIK_NAME = 'Dommik'
# A street tile; the shop's interaction walks the last steps indoors.
DOMMIK_STAND = Tile(3316, 3192, 0)
COINS = 'Coins'
# The tanner's interface and its "tan all" buttons, by the 289 cache's numbering, as rs2b0t has them.
TANNER_IF = 679


class TanMode:
    def __init__(self, hide_id, hide_label, product_id, product_label, tan_all_com):
        self.hide_id = hide_id
        self.hide_label = hide_label
        self.product_id = product_id
        self.product_label = product_label
        self.tan_all_com = tan_all_com


# Dragonhides share a display name, so the bot goes by ids, and its log by names.
TAN_MODES = {
    'Soft leather': TanMode(1739, 'Cow hide', 1741, 'Leather', 8686),
    'Hard leather': TanMode(1739, 'Cow hide', 1743, 'Hard leather', 8690),
    'Green dragonhide': TanMode(1753, 'Green dragonhide', 1745, 'Green d-leather', 8695),
    'Blue dragonhide': TanMode(1751, 'Blue dragonhide', 2505, 'Blue d-leather', 8700),
    'Red dragonhide': TanMode(1749, 'Red dragonhide', 2507, 'Red d-leather', 8705),
    'Black dragonhide': TanMode(1747, 'Black dragonhide', 2509, 'Black d-leather', 8710),
}

SETTINGS = {
    'hide_type': SettingDef('string', 'Soft leather', 'What to tan', options=list(TAN_MODES.keys()), help='soft/hard leather come from cowhides; the dragonhide rows tan that colour of hide'),
    'buy_thread': SettingDef('boolean', True, 'Buy thread at Dommik?', help="every Nth run, keep a slot free and buy out Dommik's thread on the way back"),
    'thread_every_runs': SettingDef('number', 5, 'Thread run every N trips', 1, 50),
    'thread_qty': SettingDef('number', 100, 'Thread to buy (stacks)', 1, 1000),
    'coins_per_trip': SettingDef('number', 2000, 'Coins to top up to', 1, 100000, help='tanning is charged per hide, so the bot keeps a coin float in the pack'),
}


class TannerBot(LoopingBot):
    loop_delay = 600

    def on_start(self):
        s = self.settings
        self.mode_label = s.str('hide_type', 'Soft leather')
        self.mode = TAN_MODES.get(self.mode_label, TAN_MODES['Soft leather'])
        self.buy_thread = s.bool('buy_thread', True)
        self.thread_every = s.num('thread_every_runs', 5)
        self.thread_qty = s.num('thread_qty', 100)
        self.coin_float = s.num('coins_per_trip', 2000)
        self.runs = 0
        self.tanned = 0
        self.thread = 0
        self.status = 'starting'
        thread = f', thread every {self.thread_every} runs' if self.buy_thread else ''
        self.log(f'TannerBot; {self.mode_label}: {self.mode.hide_label} -> {self.mode.product_label}{thread}')

    def loop(self):
        thread_run = self.buy_thread and self.runs > 0 and self.runs % self.thread_every == 0
        banked = yield from self.bank_leg(thread_run)
        if not banked:
            return
        tanned = yield from self.tan_leg()
        if not tanned:
            return
        if thread_run:
            yield from self.thread_leg()
        self.runs += 1

    def walk_to(self, dest, what):
        here = game.tile()
        if here is not None and max(abs(here.x - dest.x), abs(here.z - dest.z)) <= 4:
            return True
        self.status = f'walking to {what}'
        arrived = yield from traversal.walk_resilient(dest, radius=3, attempts=2, timeout_ms=45000, log=lambda m: self.log(f'  {m}'))
        return arrived

    def bank_leg(self, thread_run):
        arrived = yield from self.walk_to(BANK_STAND, 'the bank')
        if not arrived:
            return False
        self.status = 'banking'
        opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open the bank; retrying')
            return False

        yield from bank.deposit_all_matching(lambda name, id: name.lower() != COINS.lower())
        if inventory.count(COINS) < self.coin_float / 2 and bank.count(COINS) > 0:
            yield from bank.withdraw_x(COINS, self.coin_float)
        if inventory.count(COINS) == 0:
            self.request_finish('out of coins; the tanner charges per hide')
            return False

        # A thread run keeps a slot back so the stack has somewhere to land.
        free = backpack_capacity() - inventory.used() - (1 if thread_run else 0)
        withdrawn = yield from bank.withdraw_x_by_id(self.mode.hide_id, free)
        if not withdrawn:
            banked = bank.count_by_id(self.mode.hide_id)
            if banked > 0:
                self.log(f'{banked} {self.mode.hide_label} still in the bank; withdrawal failed, retrying.')
            else:
                self.log(f'{self.mode.hide_label} not currently visible in the bank; waiting.')
            return False

        yield from bank.close()
        return inventory.count_by_id(self.mode.hide_id) > 0

    def tan_leg(self):
        arrived = yield from self.walk_to(TANNER_STAND, 'the tanner')
        if not arrived:
            return False
        tanner = npcs.query().name(TANNER_NAME).nearest()
        if tanner is None:
            self.log(f'no {TANNER_NAME} nearby')
            return False

        mode = self.mode
        self.status = f'tanning {inventory.count_by_id(mode.hide_id)} {mode.hide_label}'
        # Trade opens the tanning interface with no dialogue to click through.
        if not tanner.interact('Trade'):
            return False
        opened = yield from execution.delay_until(lambda: reader.main_modal() == TANNER_IF, 5000)
        if not opened:
            self.log('tanner interface did not open; retrying')
            return False

        interfaces.click(mode.tan_all_com)
        done = yield from execution.delay_until(lambda: inventory.count_by_id(mode.hide_id) == 0, 6000)
        made = inventory.count_by_id(mode.product_id)
        yield from modals.close()
        yield from execution.delay_until(lambda: reader.main_modal() != TANNER_IF, 3000)
        if not done:
            self.log(f'only part of the load tanned ({inventory.count_by_id(mode.hide_id)} {mode.hide_label} left); check coins')
        self.tanned += made
        self.log(f'tanned {made} {mode.product_label}')
        return True

    def thread_leg(self):
        arrived = yield from self.walk_to(DOMMIK_STAND, 'Dommik')
        if not arrived:
            return
        self.status = 'buying thread'
        opened = yield from shop.open(DOMMIK_NAME)
        if not opened:
            self.log("could not open Dommik's shop; skipping the thread run")
            return
        bought = yield from shop.buy('Thread', self.thread_qty)
        self.thread += bought
        self.log(f'bought {bought} thread')
        yield from shop.close()

    def on_progress_report(self):
        return {'Status': self.status, 'Runs': self.runs, 'Tanned': self.tanned, 'Thread': self.thread, 'Coins': inventory.count(COINS)}


BOT = define_bot(
    name='TannerBot',
    create=TannerBot,
    description="Al Kharid tanning loop — banks hides, tans the full load in one click at the Tanner, and every Nth trip keeps a slot free to buy out Dommik's thread",
    category='Crafting',
    tags=['alkharid', 'leather', 'dragonhide', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

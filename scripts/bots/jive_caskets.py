# Opens ordinary loot caskets at a bank: withdraws a backpack of them, opens five at a time, banks everything
# and repeats until the bank has none. Clue and quest caskets stay banked. Start at a bank. rs2b0t's JiveCaskets
# (MIT, see thirdparty/rs2b0t).

# Caskets opened in one go.
BATCH = 5


class JiveCaskets(TaskBot):
    loop_delay = 100

    def on_start(self):
        self.opened = 0
        self.failures = 0
        self.done = False
        self.status = 'starting'
        self.started_tick = game.tick()
        self.log('JiveCaskets: opening ordinary caskets and banking all loot')
        self.add(Task(lambda: not self.done and game.ingame(), self.run, 'Open caskets'))

    def finish(self, reason):
        self.done = True
        self.status = reason
        self.log(f'{reason}; opened {self.opened} caskets')
        self.request_finish(reason)

    def run(self):
        caskets = [i for i in inventory.items() if i.id == RANDOM_EVENT_CASKET_ID and not i.noted][0:BATCH]
        if len(caskets) > 0:
            if bank.is_open():
                self.status = 'closing bank'
                yield from bank.close()
                return
            self.status = 'opening caskets'
            before = inventory.count_by_id(RANDOM_EVENT_CASKET_ID)
            sent = 0
            for casket in caskets:
                if casket.interact('Open'):
                    sent += 1
            if sent > 0:
                yield from execution.delay_until_ticks(lambda: inventory.count_by_id(RANDOM_EVENT_CASKET_ID) <= before - sent, 3)
            opened = before - inventory.count_by_id(RANDOM_EVENT_CASKET_ID)
            if opened > 0:
                self.opened += opened
                self.failures = 0
            else:
                self.failures += 1
                if self.failures >= 3:
                    self.finish('could not open a casket after three attempts')
            return

        self.status = 'banking loot'
        opened = yield from banking.open(log=self.log)
        if not opened:
            return
        ready = yield from bank.wait_ready()
        if not ready:
            return
        ready = yield from bank.backpack_ready()
        if not ready:
            return
        yield from bank.deposit_inventory()
        if inventory.used() > 0:
            return

        if bank.count_by_id(RANDOM_EVENT_CASKET_ID) == 0:
            closed = yield from bank.close()
            if closed:
                self.finish('bank has no more caskets')
            return

        self.status = 'withdrawing caskets'
        yield from bank.set_note_mode(False)
        withdrawn = yield from bank.withdraw_load(RANDOM_EVENT_CASKET_ID)
        if not withdrawn:
            return
        yield from bank.close()

    def on_progress_report(self):
        hours = (game.tick() - self.started_tick) * 0.6 / 3600
        return {'Status': self.status, 'Opened': self.opened, 'Caskets/hr': round(self.opened / hours) if hours > 0 else 0}


BOT = define_bot(
    name='JiveCaskets',
    create=JiveCaskets,
    description='Opens ordinary loot caskets at the bank. Withdraws a full inventory, opens up to five caskets at a time, deposits all inventory items and repeats until the bank is out of caskets. Start at a bank. Clue and quest caskets are left banked.',
    category='Utility',
    tags=['caskets', 'banking', 'loot', 'members'],
)

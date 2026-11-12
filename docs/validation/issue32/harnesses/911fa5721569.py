import _core
from bots.fisher import Fisher, SETTINGS

class Harness(Fisher):
    def request_finish(self, reason=''):
        self.log('ACCEPT_FINISH ' + str(reason))
        if getattr(self, 'ready', False):
            self.log('ACCEPT_FINAL ticks=' + str(game.tick()-self.start_tick) + ' ms=' + str(_core.step_time()-self.start_ms) + ' report=' + str(self.on_progress_report()))
        Fisher.request_finish(self, reason)

    def on_start(self):
        self.bind_log(None)
        self.on('tick', self.sample)
        self.on('chat_message', self.message)
        self.ready = False
        self.last_sample = -100
        for item in inventory.items():
            item.interact('Drop')
            yield from execution.delay_ticks(1)
        for command in ['speed 600', 'setvar tutorial 1000'] + ['setstat fishing 99', 'setstat fletching 99', 'setstat woodcutting 99', 'setstat hitpoints 99', 'setstat defence 99', 'tele 0,42,54,16,19', 'give fly_fishing_rod 1', 'give feather 10000', 'give bronze_axe 1']:
            if command == 'SEED_BANK':
                opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
                if not opened:
                    raise RuntimeError('scratch bank seed failed')
                yield from bank.deposit_all_matching(lambda name, id: True)
                yield from bank.close()
                continue
            chat.command(command)
            yield from execution.delay_ticks(2)
        while chat_dialog.can_continue():
            chat_dialog.continue_()
            yield from execution.delay_ticks(1)
        self.start_tick = game.tick()
        self.start_ms = _core.step_time()
        self.start_xp = skills.xp('fishing')
        self.ready = True
        self.log('ACCEPT_START ' + str(game.tile()) + ' inv=' + str([(i.id, i.count) for i in inventory.items()]))
        yield from Fisher.on_start(self)
        from bots.gathering.three_tick import acquire_kit
        acquired = yield from acquire_kit(self)
        self.log('ACCEPT_ACQUIRED ' + str(acquired) + ' inv=' + str([(i.id, i.count) for i in inventory.items()]))
        self.request_finish('ground acquisition completed')

    def message(self, event):
        if event.type == 'game':
            self.log('SERVER ' + event.text)

    def sample(self, tick):
        if not self.ready:
            return
        elapsed = game.tick() - self.start_tick
        if elapsed - self.last_sample >= 20:
            self.last_sample = elapsed
            self.log('ACCEPT_SAMPLE ticks=' + str(elapsed) + ' ms=' + str(_core.step_time()-self.start_ms) + ' tile=' + str(game.tile()) + ' xp=' + str(skills.xp('fishing')-self.start_xp) + ' report=' + str(self.on_progress_report()) + ' inv=' + str([(i.id, i.count) for i in inventory.items()]))
        if elapsed >= 600:
            self.request_finish('ACCEPT_LIMIT 600 ticks')

BOT = define_bot(name='Fisher', create=Harness, settings_schema=SETTINGS)

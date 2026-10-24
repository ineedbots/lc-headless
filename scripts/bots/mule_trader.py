# Withdraws a load of a noted item and trades it to one player, over and over: rs2b0t's MuleTrader (MIT, see
# thirdparty/rs2b0t). With a location set it walks there first when it's more than 50 tiles off.

NO_LOCATION = Tile(0, 0, -1)

SETTINGS = {
    'target_player': SettingDef('string', 'ineedbots', 'Target player', help='Display name of the player to trade noted essence to'),
    'target_item': SettingDef('string', 'Rune essence', 'Target item', help='Display name of the item to trade'),
    'target_location': SettingDef('tile', NO_LOCATION, 'Location'),
}


class MuleTrader(LoopingBot):
    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame(), 0)
        self.target_player = self.settings.str('target_player', 'ineedbots')
        self.target_item = self.settings.str('target_item', 'Rune essence')
        self.target_location = self.settings.tile('target_location', NO_LOCATION)
        self.trades = 0
        self.log(f"Mule started — target: {self.target_player or '(none)'} - item: {self.target_item or '(none)'}")

    def loop(self):
        if not self.target_item:
            self.log('No target item set')
            yield from execution.delay_ticks(5)
            return

        if self.target_location.level != -1:
            here = game.tile()
            if here is not None and self.target_location.distance_to(here) > 50:
                yield from traversal.walk_resilient(self.target_location, radius=3, attempts=6, timeout_ms=240000, log=lambda m: self.log(f'  {m}'))
                yield from execution.delay_ticks(5)

        # The bank, first.
        if not bank.is_open():
            opened = yield from banking.open(prefer_nearby=True, log=self.log)
            if not opened:
                self.log('Could not open bank')
                yield from execution.delay_ticks(2)
                return
            yield from bank.wait_ready(6000)
            return

        # Everything else in, then a load of the item, noted.
        if inventory.used() > 0:
            yield from bank.deposit_inventory()
            yield from execution.delay_until(lambda: inventory.used() == 0, 4000)
        yield from bank.set_note_mode(True)
        yield from execution.delay_ticks(1)

        if not inventory.contains(self.target_item) and bank.count(self.target_item) <= 0:
            self.log('No item in bank left')
            yield from execution.delay_ticks(10)
            raise RuntimeError('No items left')
        if bank.count(self.target_item) > 0:
            yield from bank.withdraw_load(self.target_item)
        yield from execution.delay_until(lambda: inventory.contains(self.target_item), 3000)
        if inventory.contains(self.target_item):
            yield from self.trade_to_player()

    def trade_to_player(self):
        # The bank closes first, so the trade screen can open.
        if bank.is_open():
            yield from bank.close(3000)
            yield from execution.delay_ticks(1)
        if not self.target_player:
            self.log('No target player set')
            yield from execution.delay_ticks(5)
            return
        if players.query().name(self.target_player).nearest() is None:
            self.log(f'Player not found: {self.target_player}')
            yield from execution.delay_ticks(5)
            return

        if not trade.active():
            trade.request(self.target_player)
            opened = yield from execution.delay_until(lambda: trade.on_offer_screen() or trade.on_confirm_screen(), 5000)
            if not opened:
                self.log('Trade window did not open')
                return

        if trade.on_offer_screen():
            if inventory.count(self.target_item) > 0:
                trade.offer_all(self.target_item)
                yield from execution.delay_ticks(1)
            trade.accept()
            yield from execution.delay_until(lambda: trade.on_confirm_screen(), 3000)

        if trade.on_confirm_screen():
            trade.accept()
            yield from execution.delay_until(lambda: not trade.active(), 3000)
            execution.note_progress()
            self.trades += 1
            self.log('Trade complete')

    def on_stop(self, reason):
        self.log('Stopped')

    def on_progress_report(self):
        return {'Target': self.target_player, 'Item': self.target_item, 'Trades': self.trades}


BOT = define_bot(
    name='MuleTrader',
    create=MuleTrader,
    description='Withdraws noted item and trades it to a player',
    category='Other',
    tags=['trade', 'bank'],
    settings_schema=SETTINGS,
)

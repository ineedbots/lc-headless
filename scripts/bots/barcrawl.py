"""Ported from rs2b0t's src/bot/scripts/Barcrawl/Barcrawl.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.exec.steps import open_bank_leg
from rs2004.quests.barcrawl.barcrawl_logic import BARCRAWL_CARD, BARCRAWL_GP, BARS, COINS
from rs2004.quests.barcrawl.run_barcrawl import ensure_barcrawl, read_card

__all__ = ['Barcrawl']

# Why: the tour is a miniquest of its own. It opens the Barbarian Outpost gate and gates Barbarian Training.
# Why: it is runnable on its own as well as from Horror from the Deep, which calls the same driver in {@link ../quests/barcrawl/RunBarcrawl.js}.
class Barcrawl(LoopingBot):
    """Alfred Grimhand's Barcrawl, standalone."""
    loop_delay = 600
    _status = 'starting'
    _signed = 0
    _failures = 0

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.log(f'Barcrawl — {len(BARS)} bars, about {BARCRAWL_GP}gp of drinks')

    def loop(self):
        if not game.ingame():
            return 1200
        yield from self._refresh_signed()
        # Why: the tour crosses the map and the priciest bars are furthest from a booth, so the coins come before the walk.
        _c1 = inventory.count(COINS) < BARCRAWL_GP
        if _c1:
            _w2 = yield from self._top_up_coins()
            _c1 = not (_w2)
        if _c1:
            self._status = 'out of coins'
            self.request_finish('not enough coins for the tour and none in the bank')
            return
        self._status = 'touring'

        def _fn3(signed, total):
            self._signed = signed
        _w4 = yield from ensure_barcrawl(lambda m: self.log(m), _fn3)
        if _w4:
            self._status = 'complete'
            self.request_finish('barcrawl complete — the outpost gate will open')
            return
        # Why: `ensureBarcrawl` returns false for a cut-short conversation as well as a broken tour, and a random event is enough to cause the first.
        self._failures += 1
        if self._failures >= 3:
            self._status = 'gave up'
            self.request_finish('the barcrawl made no progress in three passes')
            return
        self.log(f'barcrawl pass failed ({self._failures}/3) — retrying')
        return 3000

    def _refresh_signed(self):
        """How many lines are green, for the paint. Silent when there is no card."""
        if inventory.count(BARCRAWL_CARD) == 0:
            return
        progress = yield from read_card()
        if progress:
            self._signed = len(BARS) - len(progress.remaining)

    def _top_up_coins(self):
        self._status = 'banking'
        _w5 = yield from open_bank_leg('barcrawl: no known bank', None, lambda m: self.log(m))
        if not (_w5):
            return False
        yield from bank.set_note_mode(False)
        # Four tours' worth: the walk back to a booth costs more than the coins.
        yield from bank.withdraw_x(COINS, BARCRAWL_GP * 4)
        yield from modals.close()
        return inventory.count(COINS) >= BARCRAWL_GP

    def on_progress_report(self):
        return {'Status': self._status, 'Bars signed': f'{self._signed}/{len(BARS)}',
                'Coins': inventory.count(COINS), 'Failures': self._failures}



BOT = define_bot(
    name='Barcrawl',
    description="Alfred Grimhand's Barcrawl — banks for the drinks, gets the card from the outpost guard, tours all ten bars nearest-first and hands it back in (opens the Barbarian Outpost gate)",
    category='Quest',
    tags=['miniquest', 'barcrawl', 'barbarian outpost', 'gate'],
    create=Barcrawl,
)

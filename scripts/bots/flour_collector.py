"""Fill pots at Sinclair Mansion: rs2b0t's FlourCollector (MIT, see thirdparty/rs2b0t)."""
from rs2004.quests.defs.murder.areas import MURDER_LOC, MURDER_NAME, MURDER_OBJ, MURDER_TILE


class FlourCollector(LoopingBot):
    def on_start(self):
        self.filled = 0
        self.status = 'starting'
        ready = yield from execution.delay_until(lambda: quests.status(MURDER_NAME) != 'unknown', 10000)
        if not ready:
            self.request_finish('could not read Murder Mystery status')
            return
        if quests.status(MURDER_NAME) == 'not_started':
            self.request_finish('start Murder Mystery to get permission to use the flour barrel')

    def loop(self):
        if inventory.count_by_id(MURDER_OBJ.POT) == 0:
            yield from self.restock()
            return
        if bank.is_open():
            closed = yield from bank.close()
            if not closed:
                return
        self.status = 'filling pots at Sinclair Mansion'
        before = inventory.count_by_id(MURDER_OBJ.POT_FLOUR)
        yield from reach.loc_op('Barrel of flour', 'Take From', MURDER_TILE.FLOUR_BARREL,
                               lambda: inventory.count_by_id(MURDER_OBJ.POT_FLOUR) > before,
                               id=MURDER_LOC.FLOUR_BARREL, within=6,
                               refused=lambda text: "guards' permission" in text.lower() or 'something to put the flour in' in text.lower(),
                               log=self.log)
        self.filled += max(0, inventory.count_by_id(MURDER_OBJ.POT_FLOUR) - before)

    def restock(self):
        self.status = 'banking at Seers'
        opened = yield from banking.open(stand=MURDER_TILE.BANK, log=self.log)
        if not opened:
            return False
        try:
            ready = yield from execution.delay_until(lambda: bank.ready(), 5000)
            if ready:
                yield from bank.deposit_all_matching(lambda name, id: id != MURDER_OBJ.POT)
                count = bank.count_by_id(MURDER_OBJ.POT)
                if count == 0:
                    self.status = 'out of empty pots'
                    self.request_finish('bank is out of empty pots')
                else:
                    yield from bank.set_note_mode(False)
                    yield from bank.withdraw_x_by_id(MURDER_OBJ.POT, min(count, inventory.free()))
        except Exception as error:
            yield from bank.close()
            raise error
        yield from bank.close()
        return True

    def recovery_anchor(self):
        return MURDER_TILE.FLOUR_BARREL

    def on_progress_report(self):
        return {'Status': self.status, 'Filled': self.filled, 'Pots left': inventory.count_by_id(MURDER_OBJ.POT)}


BOT = define_bot(name='FlourCollector', create=FlourCollector, description='Fills banked empty pots at Sinclair Mansion and banks the flour at Seers. Requires Murder Mystery started.', category='Cooking', tags=['flour', 'supplies', 'banking', 'members'])

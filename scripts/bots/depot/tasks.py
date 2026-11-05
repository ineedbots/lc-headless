"""MuleDepot bank, movement and trade tasks, adapted from rs2b0t #878 (MIT)."""

import _core

from rs2004 import execution
from rs2004.bank import bank, open_bank_access
from rs2004.items import inventory
from rs2004.game import game
from rs2004.trade import trade
from rs2004.traversal import traversal
from rs2004.catalogs import Record
from rs2004.catalogs.partner import stable_closed_poll
from rs2004.market.catalog import live_catalog, noted_id
from bots.depot.logic import bank_choice, is_giver_role, line_key, plan_withdrawal


class DepotBank:
    def __init__(self, bot):
        self.bot = bot
        self.empty_reads = 0
        self.missing_reads = {}
        self.client = None

    def validate(self):
        bot = self.bot
        if trade.active():
            return False
        if bank.is_open():
            return True
        if bot.role in ['Client', 'Supermule']:
            return inventory.used() > 0
        if bot.role == 'Supplier':
            return bot.current_batch() is not None and (bool(bot.shortfall()) or inventory.used() == 0)
        listed = [n.lower() for n in bot.items]
        return inventory.used() == 0 or any([(i.name or '').lower() not in listed for i in inventory.items()])

    def open(self):
        bot = self.bot
        reached = yield from traversal.walk_resilient(bot.bank_tile, radius=3, attempts=3, timeout_ms=120000)
        if not reached:
            return False
        destination = bank_choice(bot.settings.str('bank', 'Seers'))
        opened = yield from open_bank_access(destination, {'name': 'Bank booth', 'op': 'Use-quickly'})
        if not opened:
            return False
        ready = yield from bank.wait_ready(8000)
        return ready

    def execute(self):
        bot = self.bot
        bot.status = 'banking'
        opened = yield from self.open()
        if not opened:
            yield from execution.delay_ticks(2)
            return
        try:
            if bot.role in ['Supermule', 'Client']:
                yield from bank.deposit_all_matching(lambda name, id: True)
            elif bot.role == 'Mule':
                yield from self.dump()
            else:
                yield from self.supply()
        except Exception:
            yield from bank.close()
            raise
        yield from bank.close()

    def dump(self):
        bot = self.bot
        names = [n.lower() for n in bot.items]
        yield from bank.deposit_all_matching(lambda name, id: (name or '').lower() not in names)
        if inventory.used() > 0:
            return
        plan = plan_withdrawal(bot.items, bank.items(), inventory.free())
        if not plan:
            self.empty_reads += 1
            if self.empty_reads >= 3:
                bot.request_finish('MuleDepot: dump list exhausted after three bank reads')
            return
        self.empty_reads = 0
        yield from bank.set_note_mode(True)
        for line in plan:
            note = noted_id(live_catalog(), line.id)
            landed = note if note is not None else line.id
            before = inventory.count_by_id(landed)
            if not bank.withdraw_by_id(line.id, 'Withdraw All'):
                return
            changed = yield from execution.delay_until(lambda: inventory.count_by_id(landed) > before, 5000)
            if not changed:
                return

    def supply(self):
        bot = self.bot
        batch = bot.current_batch()
        if batch is None:
            return
        if self.client != bot.current_client():
            self.client = bot.current_client()
            self.missing_reads = {}
        keys = [line.name.lower() for line in batch.lines if line.id < 0]
        catalog = live_catalog()
        ids = [line.id for line in batch.lines if line.id >= 0]
        notes = [noted_id(catalog, id) for id in ids]
        yield from bank.deposit_all_matching(lambda name, id: (name or '').lower() not in keys and id not in ids and id not in notes)
        yield from bank.set_note_mode(True)
        for line in bot.shortfall():
            rows = [r for r in bank.items() if r.id == line.id] if line.id >= 0 else [r for r in bank.items() if (r.name or '').lower() == line.name.lower()]
            before = bot.held(line)
            for row in rows:
                note = noted_id(catalog, row.id)
                yield from bank.withdraw_x_by_id(row.id, min(line.quantity, row.count), lands_as_id=note if note is not None else row.id)
                if bot.held(line) > before:
                    break
            if bot.held(line) <= before:
                key = line_key(line)
                self.missing_reads[key] = self.missing_reads.get(key, 0) + 1
                if self.missing_reads[key] >= 3:
                    bot.unavailable.add(key)
                    bot.log(f'MuleDepot: bank cannot supply {line.quantity} {line.name or str(line.id)}')
            else:
                self.missing_reads[line_key(line)] = 0
        if not bot.shortfall() and inventory.used() == 0:
            bot.advance_batch()


class DepotTrade:
    def __init__(self, bot):
        self.bot = bot
        self.partner = None
        self.before = None
        self.opened_at = None
        self.confirmed = False
        self.closed = stable_closed_poll()

    def validate(self):
        return trade.active() or self.before is not None

    def reset(self):
        self.partner = None
        self.before = None
        self.opened_at = None
        self.confirmed = False
        self.closed = stable_closed_poll()

    def execute(self):
        bot = self.bot
        if self.before is None:
            self.before = bot.pack_units()
            self.opened_at = _core.step_time()
        if not trade.active():
            if not self.closed():
                yield from execution.delay_ticks(1)
                return
            moved = self.before - bot.pack_units() if is_giver_role(bot.role) else bot.pack_units() - self.before
            expected = sum([l.quantity for l in bot.pending]) if bot.role == 'Supplier' else 1
            if self.confirmed and moved >= expected and moved > 0:
                bot.transfers += 1
                bot.units += moved
                bot.asker = None
                if bot.role == 'Supplier':
                    bot.advance_batch()
                bot.log(f'MuleDepot: transfer {bot.transfers}, {moved} units')
            else:
                bot.log('MuleDepot: trade closed without a confirmed transfer; retrying')
            self.reset()
            return
        self.closed()
        who = trade.partner()
        if who is not None:
            self.partner = who
        if self.partner is not None and not bot.accepts(self.partner):
            yield from trade.decline()
            return
        if self.partner is None:
            if _core.step_time() - self.opened_at >= 3000:
                yield from trade.decline()
            else:
                yield from execution.delay_ticks(1)
            return
        bot.status = f'trading with {self.partner}'
        if _core.step_time() - self.opened_at >= 30000:
            yield from trade.decline()
            return
        if trade.on_confirm_screen():
            if not self.confirmed:
                self.confirmed = trade.accept()
            yield from execution.delay_ticks(1)
            return
        if is_giver_role(bot.role):
            if not trade.my_offer():
                if bot.role == 'Supplier':
                    if bot.shortfall():
                        yield from trade.decline()
                        return
                    bot.pending = [Record({'id': l.id, 'name': l.name, 'quantity': min(l.quantity, bot.held(l))}) for l in bot.current_batch().lines if bot.held(l) > 0]
                    for line in bot.pending:
                        candidates = [i for i in inventory.items() if i.id == line.id or i.id == noted_id(live_catalog(), line.id)] if line.id >= 0 else [i for i in inventory.items() if (i.name or '').lower() == line.name.lower()]
                        if not candidates:
                            yield from trade.decline()
                            return
                        item = candidates[0]
                        offered = yield from trade.offer(item.name, line.quantity, lambda i: i.id == item.id)
                        if not offered:
                            yield from trade.decline()
                            return
                else:
                    for name in bot.items:
                        if inventory.count(name) > 0:
                            trade.offer_all(name)
                return
            trade.accept()
        elif trade.their_offer():
            trade.accept()
        yield from execution.delay_ticks(1)


class DepotMove:
    def __init__(self, bot):
        self.bot = bot
        self.stalls = 0

    def validate(self):
        return not trade.active()

    def execute(self):
        bot = self.bot
        target = bot.target()
        here = game.tile()
        if here is None:
            yield from execution.delay_ticks(1)
            return
        if bot.bank_tile.distance_to(here) > 12:
            bot.status = 'returning to depot'
            yield from traversal.walk_resilient(bot.bank_tile, radius=3, attempts=3, timeout_ms=120000)
            return
        ready = inventory.used() > 0 if is_giver_role(bot.role) else inventory.used() == 0
        if not ready or target is None or (bot.role == 'Supplier' and bot.shortfall()):
            yield from execution.delay_ticks(2)
            return
        if target.distance() > 12:
            yield from execution.delay_ticks(2)
            return
        if target.distance() > 2 and self.stalls < 3:
            before = target.distance()
            yield from traversal.walk_resilient(target.tile(), radius=2, attempts=1, timeout_ms=15000)
            live = bot.target()
            self.stalls = self.stalls + 1 if live is not None and live.distance() >= before else 0
            return
        if _core.step_time() - bot.last_request >= 3000:
            bot.last_request = _core.step_time()
            bot.cursor = (bot.cursor + 1) % len(bot.partners)
            trade.request(target.name)
        yield from execution.delay_ticks(1)


class DepotWait:
    def __init__(self, bot):
        self.bot = bot

    def validate(self):
        return True

    def execute(self):
        self.bot.status = 'waiting for a partner'
        yield from execution.delay_ticks(2)

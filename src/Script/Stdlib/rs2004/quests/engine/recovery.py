"""Bank reset and loadout restoration from rs2b0t's engine/recovery.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.bank import bank
from rs2004.catalogs.record import Record
from rs2004.game import game
from rs2004.items import equipment, inventory
from rs2004.quests.engine.resume_preparation import resume_preparation
from rs2004.quests.exec.steps import execute_step, open_bank_leg


class LiveResetPort:
    def inventory(self):
        return inventory.items() if game.scene_ready() else None

    def equipment(self):
        return equipment.items()

    def tile(self):
        return game.tile()

    def in_combat(self):
        return game.in_combat()

    def open_bank(self, module, log):
        if bank.is_open():
            ready = yield from bank.backpack_ready(log=log)
            return ready
        ready = yield from open_bank_leg('recovery: no reachable bank', None if module.bank == 'nearest' else module.bank, log)
        return ready

    def close_bank(self):
        return bank.close()

    def bank_inventory(self):
        ready = yield from bank.backpack_ready()
        return inventory.items() if ready else None

    def deposit_all(self):
        return bank.deposit_all_matching(lambda name, id: True)

    def unequip(self, id):
        worn = [item for item in equipment.items() if item.id == id]
        if not worn:
            return True
        if not worn[0].interact('Remove'):
            return False
        result = yield from execution.delay_until(lambda: not any([item.id == id for item in equipment.items()]), 3000)
        return result

    def withdraw(self, id, qty):
        yield from bank.set_note_mode(False)
        result = yield from bank.withdraw_x_by_id(id, qty)
        return result

    def equip(self, id):
        item = [item for item in inventory.items() if item.id == id]
        if not item:
            return False
        ops = [op for op in item[0].actions() if op.lower() in ['wield', 'wear', 'equip']]
        if not ops or not item[0].interact(ops[0]):
            return False
        result = yield from execution.delay_until(lambda: any([item.id == id for item in equipment.items()]), 3000)
        return result

    def run_step(self, step, module, log):
        return execute_step(step, module.hops or [], log)


def totals(items):
    counts = {}
    for item in items:
        if item.count <= 0:
            continue
        if item.id not in counts:
            counts[item.id] = Record({'id': item.id, 'name': item.name, 'count': 0, 'noted': item.noted})
        counts[item.id].count += item.count
    return list(counts.values())


def count(items, id):
    return sum([item.count for item in items if item.id == id])


class QuestBankReset:
    def __init__(self, food=None, port=None):
        self.port = port if port is not None else LiveResetPort()
        self.food = food
        self.saved = None
        self.banked = False
        self.restoring = False
        self.reason = ''

    @property
    def pending(self):
        return self.saved is not None

    @property
    def supplies(self):
        return [Record({'item': item.name or f'#{item.id}', 'id': item.id, 'count': item.count}) for item in totals(self.saved.inventory + self.saved.equipment)] if self.saved else []

    def fail(self, reason, log):
        self.reason = reason
        log(f'recovery: {reason}')
        return False

    def tick(self, module, snap, log):
        prepared = yield from self.prepare(module, snap, log)
        if not prepared:
            return False
        restored = yield from self.restore(log)
        return restored

    def prepare(self, module, snap, log):
        if self.saved and self.saved.module.record.id != module.record.id:
            return self.fail('restore the previous quest loadout before switching quests', log)
        if self.banked:
            return True
        if self.port.in_combat():
            return self.fail('leave combat before resetting the loadout', log)
        if self.saved is None:
            items = self.port.inventory()
            if items is None:
                return self.fail('waiting for a complete inventory snapshot', log)
            if any([item.id in [431, 723, 724, 725, 726] and item.count > 0 for item in items]):
                return self.fail('deliver the rum or finish the filled Legends bowl step before a bank reset', log)
            tile = self.port.tile()
            if tile is None:
                return self.fail('waiting for a known tile before retreating', log)
            step = module.recover(tile) if module.recover else None
            if step is not None:
                recovered = yield from self.port.run_step(step, module, log)
                if not recovered:
                    return self.fail('quest recovery has not reached a safe bank route', log)
            tile = self.port.tile()
            needs_exit = tile is not None and (module.resume_at(tile) if module.resume_at else tile.z >= 6400 or tile.level > 0)
            if needs_exit and module.exit:
                exited = yield from module.exit(log)
                if not exited:
                    return self.fail('quest exit has not reached a safe bank route', log)
            tile = self.port.tile()
            if tile is None or (module.resume_at is not None and module.resume_at(tile)):
                return self.fail('this quest area needs an explicit safe exit before banking', log)
            items = self.port.inventory()
            if items is None:
                return self.fail('waiting for a complete inventory snapshot after retreating', log)
            plan = resume_preparation(module, snap.with_fields({'journal': 'in_progress', 'free_slots': 0}), items, self.food)
            keep = set(plan.keep_ids) if plan is not None else None
            caps = {item.id: item.qty for item in plan.caps} if plan is not None else {}
            saved = []
            for item in totals(items):
                qty = min(item.count, caps.get(item.id, item.count))
                if item.id != 995 and (keep is None or item.id in keep) and qty > 0:
                    saved.append(Record({'id': item.id, 'name': item.name, 'count': qty, 'noted': item.noted}))
            self.saved = Record({'module': module, 'inventory': saved, 'equipment': totals(self.port.equipment())})
        cleared = yield from self.clear_loadout(module, log)
        if cleared:
            self.banked = True
            self.reason = ''
        return cleared

    def restore(self, log):
        saved = self.saved
        if saved is None:
            return True
        if self.port.in_combat():
            return self.fail('leave combat before restoring the quest loadout', log)
        if not self.restoring:
            cleared = yield from self.clear_loadout(saved.module, log)
            if not cleared:
                return False
            self.restoring = True
        for item in saved.equipment:
            missing = item.count - count(self.port.equipment(), item.id)
            if missing <= 0:
                continue
            opened = yield from self.port.open_bank(saved.module, log)
            items = yield from self.port.bank_inventory() if opened else empty_snapshot()
            if items is None:
                return self.fail('cannot reopen the bank to restore equipment', log)
            draw = missing - count(items, item.id)
            if draw > 0:
                drawn = yield from self.port.withdraw(item.id, draw)
                if not drawn:
                    return self.fail(f'cannot restore equipped item {item.id}; check the bank', log)
            closed = yield from self.port.close_bank()
            equipped = yield from self.port.equip(item.id) if closed else failed()
            if not equipped or count(self.port.equipment(), item.id) < item.count:
                return self.fail(f'could not re-equip item {item.id}', log)
        opened = yield from self.port.open_bank(saved.module, log)
        if not opened:
            return self.fail('cannot reopen the bank to restore quest items', log)
        for item in saved.inventory:
            items = yield from self.port.bank_inventory()
            if items is None:
                return self.fail('waiting for the bank backpack before restoring quest items', log)
            missing = item.count - count(items, item.id)
            if missing > 0:
                drawn = yield from self.port.withdraw(item.id, missing)
                if not drawn:
                    return self.fail(f'cannot restore quest item {item.id}; check the bank', log)
        items = yield from self.port.bank_inventory()
        if items is None or any([count(items, item.id) < item.count for item in saved.inventory]):
            return self.fail('quest inventory restoration is incomplete', log)
        if any([count(self.port.equipment(), item.id) < item.count for item in saved.equipment]):
            return self.fail('quest equipment restoration is incomplete', log)
        closed = yield from self.port.close_bank()
        if not closed:
            return self.fail('could not close the bank after restoring the loadout', log)
        self.saved = None
        self.banked = False
        self.restoring = False
        self.reason = ''
        return True

    def clear_loadout(self, module, log):
        opened = yield from self.port.open_bank(module, log)
        if not opened:
            return self.fail('cannot reach a bank for the loadout reset', log)
        items = yield from self.port.bank_inventory()
        if items is None:
            return self.fail('waiting for the bank backpack before depositing', log)
        yield from self.port.deposit_all()
        items = yield from self.port.bank_inventory()
        if items is None or any([item.count > 0 for item in items]):
            return self.fail('the bank backpack still contains items after depositing', log)
        closed = yield from self.port.close_bank()
        if not closed:
            return self.fail('could not close the bank to remove equipment', log)
        for item in self.port.equipment():
            removed = yield from self.port.unequip(item.id)
            if not removed:
                return self.fail(f'could not remove equipped item {item.id}', log)
        if any([item.count > 0 for item in self.port.equipment()]):
            return self.fail('equipment is still worn after removal', log)
        opened = yield from self.port.open_bank(module, log)
        items = yield from self.port.bank_inventory() if opened else empty_snapshot()
        if items is None:
            return self.fail('cannot reopen the bank to deposit equipment', log)
        yield from self.port.deposit_all()
        items = yield from self.port.bank_inventory()
        if items is None or any([item.count > 0 for item in items]):
            return self.fail('the bank backpack still contains removed equipment', log)
        return True


def empty_snapshot():
    yield from ()
    return None


def failed():
    yield from ()
    return False

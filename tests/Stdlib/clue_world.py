"""A trail's client boundary with delayed bank and equipment acknowledgements."""

from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class ClueWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.bank_open = True
        self.bank_ready = True
        self.accept_bank = True
        self.accept_equip = True
        self.stock = []
        self.bank_actions = []
        self.equipment = FakeModule(items=lambda: self.worn, contains=self.wears,
                                    equip=self.equip, unequip=self.unequip)
        self.bank = FakeModule(is_open=lambda: self.bank_open, ready=lambda: self.bank_open and self.bank_ready,
            loaded=lambda: self.bank_ready, items=lambda: self.stock,
            count=lambda n: sum([i.count for i in self.stock if i.name.lower() == n.lower()]),
            count_by_id=lambda id: sum([i.count for i in self.stock if i.id == id]),
            withdraw=self.withdraw, withdraw_by_id=self.withdraw_id, withdraw_x=self.withdraw_x,
            deposit_all_matching=self.deposit_matching, wait_ready=lambda: self.reply(self.bank_ready),
            close=self.close_bank, open_nearest=lambda *a: self.open(),
            open_npc_access=lambda *a: self.open(), open_nearest_access=lambda *a: self.open())

    def install(self, module):
        QuestWorld.install(self, module)
        for name, value in [('bank', self.bank), ('equipment', self.equipment)]:
            if hasattr(module, name):
                self.patch(module, name, value)

    def wears(self, name):
        return any([i.name.lower() == name.lower() for i in self.worn])

    def equip(self, name):
        yield from self.reply()
        item = self.first(name)
        if self.accept_equip and item is not None:
            self.pack.remove(item)
            item.slot = 3
            self.worn.append(item)
            return True
        return False

    def unequip(self, name):
        yield from self.reply()
        matches = [i for i in self.worn if i.name == name]
        if self.accept_equip and matches:
            self.worn.remove(matches[0])
            self.pack.append(matches[0])
            return True
        return False

    def open(self):
        yield from self.reply()
        self.bank_open = self.accept_bank
        return self.accept_bank

    def close_bank(self):
        yield from self.reply()
        if self.accept_bank:
            self.bank_open = False
        return self.accept_bank

    def withdraw_id(self, id, op):
        row = ([i for i in self.stock if i.id == id] or [None])[0]
        return False if row is None else self.withdraw(row.name, op)

    def withdraw(self, name, op):
        self.bank_actions.append((name, op))
        count = 10 if op == 'Withdraw 10' else (5 if op == 'Withdraw 5' else 1)
        if not self.accept_bank:
            return False
        self.effects.append(lambda: self.transfer(name, count))
        return True

    def transfer(self, name, count):
        row = ([i for i in self.stock if i.name.lower() == name.lower() and i.count > 0] or [None])[0]
        if row is not None:
            moved = min(row.count, count)
            row.count -= moved
            self.hold(row.name, moved, row.id)

    def withdraw_x(self, name, count):
        self.bank_actions.append((name, count))
        yield from self.reply()
        if self.accept_bank and self.respond:
            self.transfer(name, count)
        return self.accept_bank

    def deposit_matching(self, predicate):
        yield from self.reply()
        if self.accept_bank:
            deposited = [i for i in self.pack if predicate(i.name, i.id)]
            self.pack = [i for i in self.pack if i not in deposited]
            self.stock += deposited
        return self.accept_bank

    def bank_item(self, name, count=1, id=1):
        item = QuestObject(self, name, id)
        item.count = count
        item.noted = False
        self.stock.append(item)
        return item

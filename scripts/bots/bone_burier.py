# Withdraws bones from the nearest bank and buries them, until the bank has none: rs2b0t's BoneBurier (MIT, see
# thirdparty/rs2b0t).

SETTINGS = {
    'bone_name': SettingDef('string', 'Bones', 'Bone name (exact)', help='the exact bank item to withdraw and bury, e.g. Bones, Big bones, or Dragon bones'),
}


class BoneBurier(LoopingBot):
    loop_delay = 600

    def on_start(self):
        self.bone_name = self.settings.str('bone_name', 'Bones').strip() or 'Bones'
        self.burials = 0
        self.trips = 0
        self.status = 'starting'
        self.xp_start = skills.xp('prayer')
        self.bank_exhausted = False
        self.empty_bank_reads = 0
        self.log(f"BoneBurier; withdrawing and burying exact item '{self.bone_name}'")

    def loop(self):
        if inventory.count(self.bone_name) > 0:
            yield from self.bury_one()
            return
        yield from self.restock()

    def on_progress_report(self):
        return {
            'Status': self.status,
            'Buried': self.burials,
            'Trips': self.trips,
            'Prayer xp': skills.xp('prayer') - self.xp_start,
            'Pack': inventory.count(self.bone_name),
        }

    def bury_one(self):
        if bank.is_open():
            closed = yield from bank.close(3000)
            if not closed:
                self.log('bank did not close; retrying')
                return

        bones = inventory.first(self.bone_name)
        if bones is None:
            return

        self.status = f'burying {self.bone_name}'
        before = inventory.count(self.bone_name)
        if not bones.interact('Bury'):
            self.request_finish(f"'{self.bone_name}' has no Bury action (ops: [{', '.join(bones.actions())}])")
            return

        name = self.bone_name
        buried = yield from execution.delay_until(lambda: inventory.count(name) < before, 3000)
        if buried:
            self.burials += before - inventory.count(self.bone_name)
        else:
            self.log(f"burying '{self.bone_name}' made no progress; retrying")

    def restock(self):
        if self.bank_exhausted:
            yield from self.finish_complete()
            return

        self.status = 'opening nearest bank'
        opened = yield from banking.bank_nearest(lambda name: True, common_junk=False, log=lambda m: self.log(f'  {m}'))
        if not opened:
            self.log('could not open a bank; retrying')
            return
        loaded = yield from execution.delay_until(lambda: bank.loaded(), 3000)
        if not loaded:
            self.empty_bank_reads += 1
            if self.empty_bank_reads >= 3:
                self.log(f"bank stayed empty; no exact item '{self.bone_name}' remains.")
                yield from self.finish_complete()
                return
            self.log('bank contents are not ready; retrying')
            return
        self.empty_bank_reads = 0

        yield from bank.set_note_mode(False)
        wanted = self.bone_name.lower()
        banked = [item for item in bank.items() if item.name is not None and item.name.lower() == wanted]
        if len(banked) == 0:
            yield from self.finish_complete()
            return
        item = banked[0]

        ops = item.actions()
        op = withdraw_op(ops, 'all') or withdraw_op(ops, '10') or withdraw_op(ops, '1')
        if op is None:
            self.status = 'withdraw failed'
            self.request_finish(f"'{item.name}' has no usable Withdraw action")
            return

        self.status = f'withdrawing {item.name}'
        name = self.bone_name
        before = inventory.count(name)
        banked_before = bank.count(item.name)
        if not bank.withdraw(item.name, op):
            self.log(f"could not {op} '{item.name}'; retrying")
            return
        landed = yield from execution.delay_until(lambda: inventory.count(name) > before, 4000)
        if landed:
            withdrawn = inventory.count(name) - before
            self.bank_exhausted = withdrawn >= banked_before
            self.trips += 1
            self.log(f'bank trip {self.trips}: withdrew {withdrawn} {item.name}')
        else:
            self.log(f"withdrawal of '{item.name}' made no progress; retrying")

    def finish_complete(self):
        self.status = 'complete'
        if bank.is_open():
            yield from bank.close()
        self.request_finish(f"bank is out of exact item '{self.bone_name}'; complete.")


BOT = define_bot(
    name='BoneBurier',
    create=BoneBurier,
    description='Bank-standing Prayer trainer — withdraws full loads of an exact bone name and buries them until the bank is empty',
    category='Prayer',
    tags=['prayer', 'bones', 'banking', 'afk'],
    settings_schema=SETTINGS,
)

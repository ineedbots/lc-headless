"""Bank reset keeps its snapshot through refusals and unacknowledged changes."""

from rs2004.catalogs.record import Record
import rs2004.quests.engine.recovery as recovery
from rs2004.quests.engine.recovery import QuestBankReset, totals, empty_snapshot, failed, LiveResetPort
from rs2004.quests.engine.types import QuestModule, QuestSnapshot
from rs2004.quests.types import QuestRecord, QuestItem


def item(id, count=1):
    return Record({'id': id, 'name': 'Item', 'count': count, 'noted': False})


class Port:
    def __init__(self):
        self.pack = [item(42)]
        self.worn = [item(43)]
        self.position = Tile(3093, 3243)
        self.combat = False
        self.calls = {}
        self.fault = ''
        self.at = 1
        self.effect = False

    def hit(self, name):
        self.calls[name] = self.calls.get(name, 0) + 1
        return self.fault == name and self.calls[name] == self.at

    def inventory(self):
        return None if self.hit('inventory') else self.pack

    def equipment(self):
        return self.worn

    def tile(self):
        return self.position

    def in_combat(self):
        return self.combat

    def open_bank(self, module, log):
        yield from ()
        return not self.hit('open')

    def close_bank(self):
        yield from ()
        return not self.hit('close')

    def bank_inventory(self):
        yield from ()
        return None if self.hit('snapshot') else self.pack

    def deposit_all(self):
        if not self.hit('deposit'):
            self.pack = []
        yield from ()
        return True

    def unequip(self, id):
        yield from ()
        if self.hit('remove'):
            return self.effect
        self.worn = []
        self.pack.append(item(id))
        return True

    def withdraw(self, id, qty):
        yield from ()
        if self.hit('withdraw'):
            return self.effect
        self.pack.append(item(id, qty))
        return True

    def equip(self, id):
        yield from ()
        if self.hit('equip'):
            return False
        self.worn = [item(id)]
        self.pack = [i for i in self.pack if i.id != id]
        return True

    def run_step(self, step, module, log):
        yield from ()
        return not self.hit('step')


def setup():
    port = Port()
    reset = QuestBankReset(port=port)
    module = QuestModule(record=QuestRecord(id='imp', items=[QuestItem('Item')]))
    return port, reset, module


def prepare(reset, module):
    return run_wait(reset.prepare(module, QuestSnapshot(), lambda text: None))


def restore(reset):
    return run_wait(reset.restore(lambda text: None))


def unsafe_prepare():
    port, reset, module = setup()
    port.combat = True
    expect(prepare(reset, module)).to_be(False)
    port.combat = False
    port.fault = 'inventory'
    expect(prepare(reset, module)).to_be(False)
    port.fault = ''
    port.position = None
    expect(prepare(reset, module)).to_be(False)
    port.position = Tile(3093, 3243)
    module.recover = lambda tile: Record({'kind': 'wait'})
    port.fault = 'step'
    expect(prepare(reset, module)).to_be(False)
    port.fault = ''
    module.resume_at = lambda tile: True
    module.exit = lambda log: failed()
    expect(prepare(reset, module)).to_be(False)
    module.exit = None
    expect(prepare(reset, module)).to_be(False)
    module.resume_at = None
    port.fault = 'inventory'
    port.at = port.calls['inventory'] + 2
    expect(prepare(reset, module)).to_be(False)
    port.fault = ''
    expect(prepare(reset, module)).to_be(True)
    expect(prepare(reset, QuestModule(record=QuestRecord(id='other')))).to_be(False)
    expect(prepare(reset, module)).to_be(True)
    expect(len(reset.supplies)).to_be(2)
    port.combat = True
    expect(restore(reset)).to_be(False)
    port.combat = False
    expect(restore(reset)).to_be(True)
    expect(restore(reset)).to_be(True)
    expect(reset.supplies).to_equal([])
    expect(totals([item(1, 0), item(2), item(2, 2)])[0].count).to_be(3)
    expect(run_wait(empty_snapshot())).to_be(None)


test('unsafe retreat and missing snapshots preserve the pending recovery', unsafe_prepare)


def clear_refusals():
    cases = [('open', 1, False), ('snapshot', 1, False), ('deposit', 1, False), ('close', 1, False), ('remove', 1, False), ('remove', 1, True), ('open', 2, False), ('deposit', 2, False)]
    for fault, at, effect in cases:
        port, reset, module = setup()
        port.fault, port.at, port.effect = fault, at, effect
        expect(prepare(reset, module)).to_be(False)
        expect(reset.pending).to_be(True)
        expect(reset.banked).to_be(False)
        expect(bool(reset.reason)).to_be(True)
        port.fault = ''
        expect(prepare(reset, module)).to_be(True)
        expect(restore(reset)).to_be(True)


test('deposit and equipment refusals can be retried without replacing the saved loadout', clear_refusals)


def restore_refusals():
    cases = [('open', 1, False), ('open', 3, False), ('withdraw', 1, False), ('close', 2, False), ('equip', 1, False), ('open', 4, False), ('snapshot', 6, False), ('withdraw', 2, False), ('withdraw', 2, True), ('close', 3, False)]
    for fault, at, effect in cases:
        port, reset, module = setup()
        expect(prepare(reset, module)).to_be(True)
        port.calls = {}
        port.fault, port.at, port.effect = fault, at, effect
        result = restore(reset)
        if result:
            raise AssertionError('restore unexpectedly succeeded: ' + fault + ':' + str(at))
        expect(reset.pending).to_be(True)
        port.fault = ''
        expect(restore(reset)).to_be(True)
        expect(reset.pending).to_be(False)
    port, reset, module = setup()
    expect(run_wait(reset.tick(module, QuestSnapshot(), lambda text: None))).to_be(True)


test('restore acknowledgements retain an exact-ID snapshot until the complete loadout is back', restore_refusals)


def result(value):
    yield from ()
    return value


class Wearable:
    id = 43

    def __init__(self, state):
        self.state = state
        self.allowed = True
        self.ops = ['Wear']

    def actions(self):
        return self.ops

    def interact(self, action):
        if not self.allowed:
            return False
        self.state[0] = action != 'Remove'
        return True


def native_adapter():
    scene = Scene()
    state = [True]
    wearable = Wearable(state)
    spy_on(recovery.game, 'scene_ready', impl=lambda: True)
    spy_on(recovery.inventory, 'items', impl=lambda: [wearable])
    spy_on(recovery.equipment, 'items', impl=lambda: [wearable] if state[0] else [])
    spy_on(recovery.execution, 'delay_until', impl=lambda predicate, timeout: result(predicate()))
    spy_on(recovery.bank, 'is_open', impl=lambda: True)
    spy_on(recovery.bank, 'backpack_ready', impl=lambda log=None: result(True))
    spy_on(recovery.bank, 'close', impl=lambda: result(True))
    spy_on(recovery.bank, 'set_note_mode', impl=lambda wanted: result(True))
    spy_on(recovery.bank, 'withdraw_x_by_id', impl=lambda id, count: result(id == 43 and count == 1))
    spy_on(recovery.bank, 'deposit_all_matching', impl=lambda predicate: result(predicate('Weapon', 43)))
    port = LiveResetPort()
    module = QuestModule(record=QuestRecord(id='imp'))
    expect(port.inventory()).to_equal([wearable])
    expect(port.equipment()).to_equal([wearable])
    expect(port.tile()).to_equal(recovery.game.tile())
    expect(port.in_combat()).to_be(False)
    expect(run_wait(port.open_bank(module, scene.log))).to_be(True)
    expect(run_wait(port.bank_inventory())).to_equal([wearable])
    expect(run_wait(port.deposit_all())).to_be(True)
    wearable.allowed = False
    expect(run_wait(port.unequip(43))).to_be(False)
    wearable.allowed = True
    expect(run_wait(port.unequip(43))).to_be(True)
    expect(run_wait(port.unequip(43))).to_be(True)
    expect(run_wait(port.withdraw(43, 1))).to_be(True)
    wearable.ops = []
    expect(run_wait(port.equip(43))).to_be(False)
    wearable.ops = ['Wear']
    expect(run_wait(port.equip(43))).to_be(True)
    expect(run_wait(port.equip(99))).to_be(False)
    expect(run_wait(port.close_bank())).to_be(True)
    spy_on(recovery.bank, 'is_open', impl=lambda: False)
    spy_on(recovery, 'open_bank_leg', impl=lambda reason, anchor, log: result(anchor is None))
    expect(run_wait(port.open_bank(module, scene.log))).to_be(True)
    spy_on(recovery, 'execute_step', impl=lambda step, hops, log: result(True))
    expect(run_wait(port.run_step(Record({'kind': 'wait'}), module, scene.log))).to_be(True)
    spy_on(recovery.bank, 'backpack_ready', impl=lambda log=None: result(False))
    expect(run_wait(port.bank_inventory())).to_be(None)
    spy_on(recovery.game, 'scene_ready', impl=lambda: False)
    expect(port.inventory()).to_be(None)


test('native reset adapters acknowledge exact equipment IDs and complete backpack snapshots', native_adapter)

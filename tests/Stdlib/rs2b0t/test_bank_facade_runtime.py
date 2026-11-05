"""rs2b0t bank-chest, bank-id and bank-transfer scenarios (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.bank import bank, banking
from rs2004.game import game
from rs2004.geometry import Tile
from rs2004.items import InvItem


def held(id=199, count=1, slot=0, ops=None):
    item = InvItem()
    item.id = id
    item.count = count
    item.slot = slot
    item.name = 'Herb'
    item.noted = False
    item.com = BANK
    item._button = True
    item._ops = ['Withdraw-1', 'Withdraw-5', 'Withdraw-10', 'Withdraw-All', 'Withdraw-X'] if ops is None else ops
    return item


class BankWorld(Scene):
    def __init__(self):
        Scene.__init__(self, Tile(3308, 3120))
        self.open = True
        self.ready = True
        self.stock = [held(count=100)]
        self.clicks = []
        self.answers = []
        self.advance = None
        self.on_click = None
        self.on_answer = None
        spy_on(bank, 'root', returns=5292)
        spy_on(_core, 'get_main_modal', impl=lambda: 5292 if self.open else -1)
        spy_on(_core, 'has_inventory', impl=lambda com: self.ready)
        spy_on(bank, 'items', impl=lambda: list(self.stock) if self.open else [])
        spy_on(bank, 'side_items', impl=lambda: list(self.pack) if self.open else [])
        spy_on(_core, 'inv_button', impl=self.click)
        spy_on(_core, 'is_count_dialog_open', returns=True)
        spy_on(_core, 'answer_count', impl=self.answer)
        spy_on(execution, 'delay_until', impl=self.wait)

    def click(self, item, op):
        self.clicks.append((item.id, item.slot, op))
        return self.on_click(item, op) if self.on_click is not None else False

    def answer(self, count):
        self.answers.append(count)
        return self.on_answer(count) if self.on_answer is not None else False

    def wait(self, condition, timeout_ms=6000):
        deadline = self.clock + timeout_ms
        while not condition() and self.clock < deadline:
            self.clock += 20
            if self.advance is not None:
                self.advance()
        return condition()
        yield

    def fill(self, id, count):
        self.pack = [held(id, 1, n) for n in range(count)]


def exact_fixed(quantity, noted):
    world = BankWorld()
    world.stock = [held(293, 20), held(298, 20, 1)]

    def click(item, op):
        world.fill(299 if noted else 298, quantity)
        return True

    world.on_click = click
    lands = 299 if noted else None
    expect(run_wait(bank.withdraw_x_by_id(298, quantity, lands))).to_be(True)
    expect(world.clicks).to_equal([(298, 1, [1, 5, 10].index(quantity) + 1)])
    expect(world.answers).to_equal([])


test_each([[1, False], [5, False], [10, False], [1, True], [5, True], [10, True]])(
    'fixed quantity %s selects the exact colliding item ID, noted=%s', exact_fixed)


def clamp_and_x(preset):
    world = BankWorld()
    world.stock = [held(298, 5, ops=['Withdraw-1', 'Withdraw-5' if preset else None, None, None, 'Withdraw-X'])]

    def click(item, op):
        if op == 2:
            world.fill(298, 5)
        return True

    def answer(count):
        world.fill(298, count)
        return True

    world.on_click = click
    world.on_answer = answer
    expect(run_wait(bank.withdraw_x_by_id(298, 100))).to_be(True)
    expect(world.clicks[0][2]).to_be(2 if preset else 5)
    expect(world.answers).to_equal([] if preset else [5])


test_each([False, True])('clamps to stock before selecting a fixed quantity or X, preset=%s', clamp_and_x)


def wrong_id_or_missing_arrival(noted, expected_note):
    world = BankWorld()
    world.stock = [held(298, 10)]

    def click(item, op):
        world.fill(299 if noted else 293, 1)
        return True

    world.on_click = click
    expect(run_wait(bank.withdraw_x_by_id(298, 1, 299 if expected_note else None))).to_be(noted and expected_note)


test_each([[False, False], [True, False], [True, True]])(
    'withdraw confirmation requires the exact landed ID, noted=%s expected_note=%s', wrong_id_or_missing_arrival)


def colliding_counts():
    world = BankWorld()
    world.stock = [held(293, 2), held(298, 3, 1), held(293, 4, 2)]
    world.on_click = lambda item, op: True
    expect(bank.count_by_id(293)).to_be(6)
    expect(bank.count_by_id(298)).to_be(3)
    expect(bank.withdraw_by_id(298)).to_be(True)
    expect(bank.withdraw_by_id(999)).to_be(False)
    expect(run_wait(bank.withdraw_x_by_id(999, 1))).to_be(False)
    expect(world.clicks).to_equal([(298, 1, 1)])


test('counts and clicks by ID even when different items share a display name', colliding_counts)


def arbitrary_quantity():
    world = BankWorld()
    world.on_click = lambda item, op: True

    def answer(count):
        world.fill(199, count)
        return True

    world.on_answer = answer
    expect(run_wait(bank.withdraw_x('Herb', 40))).to_be(True)
    expect(world.clicks).to_equal([(199, 0, 5)])
    expect(world.answers).to_equal([40])


test('a non-preset quantity uses a single Withdraw-X click and exact count answer', arbitrary_quantity)


def load_waits_for_pack(use_all):
    world = BankWorld()
    world.stock = [held(201, 100), held(199, 28, 1, None if use_all else [None, None, None, None, 'Withdraw-X'])]

    def advance():
        world.fill(199, 28 if world.clock >= 60 else 1)

    def click(item, op):
        world.stock = [held(201, 100)]
        if use_all:
            world.advance = advance
        return True

    def answer(count):
        expect(count).to_be(28)
        world.advance = advance
        return True

    world.on_click = click
    world.on_answer = answer
    expect(run_wait(bank.withdraw_load(199))).to_be(True)
    expect(world.clicks).to_equal([(199, 1, 4 if use_all else 5)])
    expect(len(world.pack)).to_be(28)
    expect(world.clock).to_be(60)


test_each([True, False])('load withdrawal waits for the complete backpack via All or X, All=%s', load_waits_for_pack)


def load_needs_arrival():
    world = BankWorld()

    def click(item, op):
        world.stock = []
        return True

    world.on_click = click
    expect(run_wait(bank.withdraw_load('Herb'))).to_be(False)
    expect(world.pack).to_equal([])


test('a bank stock update alone cannot acknowledge a load withdrawal', load_needs_arrival)


def full_or_missing(full):
    world = BankWorld()
    if full:
        world.fill(249, 28)
    expect(run_wait(bank.withdraw_load('Herb' if full else 'Missing'))).to_be(full)
    expect(world.clicks).to_equal([])


test_each([False, True])('load skips a missing item or an already full pack, full=%s', full_or_missing)


def deposit_last_item():
    world = BankWorld()
    world.pack = [held(249, 1, n, ['Deposit-1', None, None, 'Deposit-All']) for n in range(28)]

    def advance():
        world.pack = []

    def click(item, op):
        expect(op).to_be(4)
        world.advance = advance
        return True

    world.on_click = click
    run_wait(bank.deposit_inventory())
    expect(world.pack).to_equal([])
    expect(world.clock).to_be(20)
    expect(len(world.clicks)).to_be(1)


test('depositing the last stack returns on its acknowledgement without an empty-pack timeout', deposit_last_item)


def empty_snapshot(loaded):
    world = BankWorld()
    world.ready = loaded

    def advance():
        world.ready = world.clock >= 100

    world.advance = advance
    run_wait(bank.deposit_inventory())
    expect(world.clock).to_be(0 if loaded else 100)
    expect(world.clicks).to_equal([])


test_each([True, False])('empty deposits wait only for an unloaded snapshot, loaded=%s', empty_snapshot)


def withdrawal_readiness(available):
    world = BankWorld()
    world.ready = False

    def advance():
        if available and world.clock >= 100:
            world.ready = True
            world.fill(199, 3)

    def landed():
        world.fill(199, 4)

    def click(item, op):
        expect(world.ready).to_be(True)
        world.advance = landed
        return True

    world.advance = advance
    world.on_click = click
    expect(run_wait(bank.withdraw_x_by_id(199, 1))).to_be(available)
    expect(len(world.clicks)).to_be(1 if available else 0)
    if available:
        expect(len(world.pack)).to_be(4)
        expect(world.clock).to_be(120)


test_each([True, False])('withdrawal waits for side readiness before measuring inventory, available=%s', withdrawal_readiness)


def delayed_backpack():
    world = BankWorld()
    world.ready = False

    def advance():
        if world.clock >= 1600:
            world.ready = True
            world.fill(249, 1)

    world.advance = advance
    expect(run_wait(bank.backpack_ready())).to_be(True)
    expect(world.clock).to_be(1600)


test('backpack readiness tolerates delayed side inventory contents', delayed_backpack)


def chest_access(mode):
    scene = Scene(Tile(3381, 3269))
    opened = [mode == 'already open']
    clicked = []
    spy_on(bank, 'is_open', returns=False)

    def open_chest(op):
        clicked.append(op)
        opened[0] = mode != 'never opens'
        return True

    scene.loc('Closed chest', ['Open'], effect=open_chest)
    scene.loc('Open chest', ['Bank', 'Shut'] if opened[0] else [])

    scene.locs[1]._fields['actions'] = lambda: ['Bank', 'Shut'] if opened[0] else []

    def delegate(name, op):
        expect(name).to_be('Open chest')
        expect(op).to_be('Bank')
        return True
        yield

    delegated = spy_on(bank, 'open_nearest', impl=delegate)
    access = {'name': 'Open chest', 'op': 'Bank', 'open_first': {'name': 'Closed chest', 'op': 'Open'}}
    expect(run_wait(bank.open_nearest_access(access))).to_be(mode != 'never opens')
    expect(clicked).to_equal([] if mode == 'already open' else ['Open'] * (3 if mode == 'never opens' else 1))
    expect(len(delegated.calls)).to_be(0 if mode == 'never opens' else 1)


test_each(['closed', 'already open', 'never opens'])('configured bank chest access: %s', chest_access)



def casket_matching():
    from rs2004.bank import deposit_matcher
    world = BankWorld()
    world.pack = [held(2714, 1), held(405, 1, 1)]
    for item in world.pack:
        item.name = 'Casket'
        item._ops = ['Deposit-1', None, None, 'Deposit-All', None]

    def click(item, op):
        world.pack = [i for i in world.pack if i.id != item.id]
        return True

    world.on_click = click
    run_wait(bank.deposit_all_matching(deposit_matcher(lambda name: False, True)))
    expect([row[0] for row in world.clicks]).to_equal([405])
    expect([item.id for item in world.pack]).to_equal([2714])


test('common deposit matching distinguishes reward and clue caskets by id', casket_matching)


def configured_banking(name):
    import rs2004.bank as bank_module
    from rs2004.traversal import traversal
    point = Tile(3382, 3269) if name == 'Duel Arena' else Tile(3308, 3120)
    scene = Scene(point)
    access = {'name': 'Shantay chest', 'op': 'Open'} if name == 'Shantay Pass' else {
        'name': 'Open chest', 'op': 'Bank', 'openFirst': {'name': 'Closed chest', 'op': 'Open'}}
    row = {'name': name, 'tile': {'x': point.x, 'z': point.z, 'level': 0}, 'access': access}
    patch(bank_module, 'nearest_bank', lambda tile: row)
    patch(bank_module, 'nearest_bank_reachable', lambda tile, navigator: row)
    patch(bank_module, 'locked_bank_at', lambda tile: None)
    spy_on(bank, 'is_open', returns=False)
    spy_on(traversal, 'walk_resilient', impl=lambda *args, **opts: result(True))
    opened = spy_on(bank, 'open_nearest_access', impl=lambda access: result(True))
    deposited = spy_on(bank, 'deposit_all_matching', impl=lambda matcher: result(True))
    if name == 'Duel Arena':
        expect(run_wait(banking.bank_nearest(lambda item: 'ore' in item))).to_be(True)
        expect(len(deposited.calls)).to_be(1)
    else:
        expect(run_wait(banking.open(stand=point))).to_be(True)
    expect(len(opened.calls)).to_be(1)
    expect(opened.calls[0][0]['name']).to_be(access['name'])
    expect(opened.calls[0][0]['op']).to_be(access['op'])
    if name == 'Duel Arena':
        expect(opened.calls[0][0]['open_first']).to_equal({'name': 'Closed chest', 'op': 'Open'})


def result(value):
    return value
    yield


test_each(['Duel Arena', 'Shantay Pass'])('bank trips preserve configured object access: %s', configured_banking)


def chest_continue():
    from rs2004.dialogue import chat_dialog
    scene = Scene(Tile(3308, 3120))
    state = [False, False, False]
    interactions = []

    def interact(op):
        expect(state[2]).to_be(False)
        interactions.append(op)
        state[1] = True
        return True

    def resume():
        state[1] = False
        state[2] = True
        return True
        yield

    def wait(condition, timeout_ms=6000):
        if not condition() and state[2]:
            state[2] = False
            state[0] = True
        return condition()
        yield

    scene.loc('Shantay chest', ['Open'], effect=interact, dist=1)
    spy_on(bank, 'is_open', impl=lambda: state[0])
    spy_on(chat_dialog, 'can_continue', impl=lambda: state[1])
    spy_on(chat_dialog, 'continue_', impl=resume)
    spy_on(execution, 'delay_until', impl=wait)
    expect(run_wait(bank.open_nearest('Shantay chest', 'Open'))).to_be(True)
    expect(interactions).to_equal(['Open'])


test('object banking resumes Continue without canceling a pending bank open', chest_continue)

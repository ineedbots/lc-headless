"""Ported from rs2b0t's src/bot/../../test/scripts/accountLevelerVials.test.ts (MIT, see thirdparty/rs2b0t)."""
from bots.account_leveler.record import Record
from bots.account_leveler.vials import fill_supply_vials, VIAL_FOUNTAIN
after_each(lambda *_args: restore_all())

class TestVial:

    def __init__(self, state, slot):
        self.state = state
        self.slot = slot

    @property
    def id(self):
        return self.state.pack[self.slot].id

    @property
    def noted(self):
        return self.state.pack[self.slot].noted

    def use_on(self, target):
        return self.state.use()

class FountainQuery:

    def name(self, name):
        return self

    def within(self, radius):
        return self

    def nearest(self):
        return VIAL_FOUNTAIN

def fixture():
    state = Record({'pack': [Record({'id': 229, 'noted': False}) for slot in range(3)]})
    spy_on(inventory, 'items').mock_implementation(lambda: [TestVial(state, slot) for slot in range(len(state.pack))])
    spy_on(inventory, 'count_by_id').mock_implementation(lambda id: len([item for item in state.pack if item.id == id]))
    spy_on(locs, 'query').mock_implementation(lambda: FountainQuery())
    walk = spy_on(traversal, 'walk_resilient').mock_implementation(lambda *args, **kwargs: resolved_wait(True))
    wait = spy_on(execution, 'delay_until').mock_implementation(instant_until)
    ticks = spy_on(execution, 'delay_ticks').mock_implementation(lambda *args, **kwargs: resolved_wait(None))

    def use():
        for item in state.pack:
            if item.id == 229:
                item.id = 227
                break
        return True
    use_spy = Spy(use)
    state.use = use_spy
    return Record({'pack': state.pack, 'walk': walk, 'wait': wait, 'ticks': ticks, 'use': use_spy})

def _fn4(*_args, **_kwargs):
    f = fixture()
    _w5 = yield from fill_supply_vials(2, lambda *_args: None)
    expect(_w5).to_be(True)
    expect([item.id for item in f.pack]).to_equal([227, 227, 229])
    expect(f.walk.calls[0][0]).to_be(VIAL_FOUNTAIN)
    expect(len(f.use.calls)).to_be(2)
    expect(len(f.ticks.calls)).to_be(2)
test('fills exactly the requested vials and waits between protected operations', _fn4)

def _fn6(failure, *_args, **_kwargs):
    f = fixture()

    def _fn7(*_args, **_kwargs):
        if failure == 'empty disappears':
            f.pack.pop()
        if failure == 'water appears':
            f.pack.append(Record({'id': 227, 'noted': False}))
        return True
    f.use.mock_implementation(_fn7)
    _w10 = yield from fill_supply_vials(3, lambda *_args: None)
    expect(_w10).to_be(False)
    expect(len(f.use.calls)).to_be(1)
    expect(len(f.wait.calls)).to_be_greater_than(0)
test_each(['no change', 'empty disappears', 'water appears'])('filling stops on %s instead of claiming success', _fn6)

def _fn11(*_args, **_kwargs):
    f = fixture()
    f.walk.mock_implementation(lambda *args, **kwargs: resolved_wait(False))
    _w12 = yield from fill_supply_vials(3, lambda *_args: None)
    expect(_w12).to_be(False)
    expect(len(f.use.calls)).to_be(0)
test('unreachable fountain does not attempt item use', _fn11)

def _fn13(*_args, **_kwargs):
    f = fixture()
    for item in f.pack:
        item.noted = True
    _w14 = yield from fill_supply_vials(3, lambda *_args: None)
    expect(_w14).to_be(False)
    expect(len(f.use.calls)).to_be(0)
test('noted vials are never used on the fountain', _fn13)

def resolved_wait(value):
    if False:
        yield
    return value

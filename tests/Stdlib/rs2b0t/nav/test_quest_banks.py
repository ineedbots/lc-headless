"""rs2b0t's test/api/ai/quests/quest-banks.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Over the quests ported so far: a check that names a quest not yet in the list waits for the phase that ports it."""

from rs2004.quests.defs import QUEST_DEFS
from rs2004.traversal import bank_locations

BANK_KEYS = set([f"{b['tile']['x']},{b['tile']['z']},{b['tile']['level']}" for b in bank_locations()])

MODULES = [d.module() for d in QUEST_DEFS]


def module_for(id):
    for m in MODULES:
        if m.record.id == id:
            return m
    return None


# The quests that name a bank. The rest ask for whichever one is nearest.
PINNED = [m for m in MODULES if m.bank is not None and m.bank != 'nearest']


def _fn1():
    def _fn2():
        missing = [m.record.id for m in MODULES if m.bank is None]
        expect(missing).to_equal([])
    test('every implemented quest declares a bank, or asks for the nearest', _fn2)

    def _fn3():
        for m in PINNED:
            tile = m.bank
            if f'{tile.x},{tile.z},{tile.level}' not in BANK_KEYS:
                raise AssertionError(f'{m.record.id} → ({tile.x},{tile.z},{tile.level}) is not a known bank')
    test('every pinned quest bank is a real known BANK_LOCATIONS tile', _fn3)

    def _fn4():
        for m in PINNED:
            expect(m.bank.level).to_be(0)
    test('every pinned quest bank is level 0', _fn4)


describe('per-quest provisioning bank', _fn1)


# Why: a free quest is fought at low level against low-level things, and the pack pays for food it never eats with
# slots the quest items need. Dragon Slayer keeps its ration, since Elvarg is the one free fight that earns it.
FREE_WITH_FOOD = ['blackknight', 'demon', 'haunted', 'gobdip', 'squire', 'hunt', 'blackarmgang', 'vampire']


def _fn5():
    def _fn6():
        for id in FREE_WITH_FOOD:
            module = module_for(id)
            if module is not None and module.food is not None:
                raise AssertionError(f'{id} still asks for food')
    test('none of the free quests carries a food float, Dragon Slayer aside', _fn6)

    def _fn7():
        ds = module_for('dragon')
        if ds is not None:
            expect(ds.food).to_be_greater_than(0)
    test('Dragon Slayer keeps its ration', _fn7)


describe('food on the free quests', _fn5)


# Why: a members quest earns its float by fighting or by eating on the walk, and these three do neither: no grind, no
# combat step and no sustain list, so the withdrawal was slots the quest never used. The ones that do fight, and the two
# that carry a documented traversal ration, keep theirs.
def _fn8():
    def _fn9():
        for id in ['cog', 'totem', 'seaslug']:
            module = module_for(id)
            if module is not None:
                expect(module.food).to_be_undefined()
                expect(module.sustain).to_be_undefined()
    test('a quest that neither fights nor eats carries no float', _fn9)

    def _fn10():
        for id in ['arena', 'ball', 'grail', 'ikov', 'priestperil']:
            module = module_for(id)
            if module is not None:
                expect(module.food).to_be_greater_than(0)
    test('the ones that fight keep theirs', _fn10)

    def _fn11():
        for id in ['mcannon', 'fishingcompo']:
            module = module_for(id)
            if module is not None:
                expect(module.food).to_be_greater_than(0)
                expect(module.sustain).to_be_defined()
    test('the ones that eat on the walk keep theirs', _fn11)


describe('food on the members quests', _fn8)

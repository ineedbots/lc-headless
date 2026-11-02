"""Ported from rs2b0t's test/api/ai/quests/defs/legends-bless.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.legends.shaman import bless_prayer_floor, needs_dose

def miss_chance(points):
    """`gujuo_bless_bowl`'s roll: `stat_random(prayer, 80, 250)`, where true is the miss."""
    value = ((80 * (99 - points)) // 98) + ((250 * (points - 1)) // 98) + 1
    return value / 256


# Why: each prayer point adds about 1.73 to the failure roll.
def _fn1():
    expect(miss_chance(42)).to_be_less_than(miss_chance(70))
    expect(miss_chance(70)).to_be_less_than(miss_chance(99))


test('the trance only gets harder as prayer rises', _fn1)


# Why: 42 is both Gujuo's minimum and the best success chance.
def _fn2():
    expect(bless_prayer_floor()).to_be(42)
    expect(miss_chance(bless_prayer_floor())).to_be_less_than(miss_chance(43))


test('the floor is the gate itself, whatever the bar can hold', _fn2)


# Why: the stat block can lag a miss, so waiting would waste a second throw.
def _fn3():
    expect(needs_dose('missed', 42)).to_be(True)
    expect(needs_dose('missed', 37)).to_be(True)


test('a miss is counted rather than waited for', _fn3)


# Why: Gujuo's refusal is authoritative when the stat block lags.
def _fn4():
    expect(needs_dose('refused', 99)).to_be(True)


test('a refusal is believed over the stat block', _fn4)


# Why: extra prayer above the five-point cost only worsens the odds.
def _fn5():
    expect(needs_dose('missed', 99)).to_be(False)
    expect(needs_dose('quiet', 20)).to_be(False)


test('a miss with room to spare does not drink', _fn5)

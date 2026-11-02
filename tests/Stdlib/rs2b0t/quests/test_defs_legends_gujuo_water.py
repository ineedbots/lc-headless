"""Ported from rs2b0t's test/api/ai/quests/defs/legends-gujuo-water.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.legends.shaman import water_talk_answer

# Why: the caves set `asked_ungadulu_where`, which is what `gujuo_pure_water` gates on, so they are the answer to a menu without the topic on it, and the only such answer.
def _fn1():
    expect(water_talk_answer('nogoal')).to_be('caves')


test('a menu without the topic sends the run to Ungadulu', _fn1)


# Why: no dialogue says nothing about the bit, so do not infer that the topic is missing.
def _fn2():
    expect(water_talk_answer('nodialog')).to_be('retry')


test('a shaman who never spoke is asked again, not answered with a walk', _fn2)


def _fn3():
    expect(water_talk_answer('goal')).to_be('done')


test('the sketch in the pack ends the step', _fn3)

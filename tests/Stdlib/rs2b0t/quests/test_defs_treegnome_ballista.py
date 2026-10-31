"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/treegnome-ballista.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.quests.defs.treegnome.stronghold import coordinate_choice

OPTIONS = ['0001', '0002', '0003', '0004', '0005']


def asked(header):
    return [f'@dbl@{header}'] + list(OPTIONS)


def _fn1():
    # Why: the three prompts render the same five options, so the header text is the only thing that tells them apart.
    def _fn2():
        expect(coordinate_choice(asked('Enter the height-coordinate of the stronghold'), OPTIONS)).to_be('0004')
    test('answers 4 for the height', _fn2)

    def _fn3():
        expect(coordinate_choice(asked('Enter the x-coordinate of the stronghold'), OPTIONS)).to_be('0003')
    test('answers 3 for the x', _fn3)

    def _fn4():
        expect(coordinate_choice(asked('Enter the y-coordinate of the stronghold'), OPTIONS)).to_be('0005')
    test('answers 5 for the y', _fn4)

    def _fn5():
        expect(coordinate_choice(['Would you like to fire?'], ['Yes', 'No'])).to_be_null()
    test('refuses to guess when no header names a coordinate', _fn5)


describe('ballista coordinates', _fn1)

"""rs2b0t's test/api/ai/clues/bankAccess.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and
expect. It reads the walker's bank list, so it runs with the real cache."""

from rs2004.clues.bank_access import open_clue_bank


def chest():
    spy_on(game, 'tile', lambda: Tile(3382, 3269, 0))
    opened = []
    spy_on(bank, 'open_nearest', lambda *args: instant_until(lambda: False))

    def access(a):
        opened.append(a['name'])
        return True
        yield

    spy_on(bank, 'open_nearest_access', access)
    expect(run_wait(open_clue_bank())).to_be(True)
    expect(opened).to_equal(['Open chest'])


test('the Duel Arena return opens the chest instead of searching for a booth', chest)

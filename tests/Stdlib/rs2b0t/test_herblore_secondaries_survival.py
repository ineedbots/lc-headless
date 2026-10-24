"""rs2b0t's test/scripts/HerbloreSecondaries/survival.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe,
test and expect. Its second test runs the bot's on_start against stubbed facades; only the eating rule is here."""

from bots.herblore_secondaries import should_eat

test('low-level collectors eat at six HP even when a lobster would overheal', lambda: [
    expect(should_eat(6, 10, 12, 9, 19, False)).to_be(True),
    expect(should_eat(10, 10, 12, 9, 19, False)).to_be(False),
])
